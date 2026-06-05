"""
배포 에이전트 - SSH 기반 Docker 배포 오케스트레이터.

단계: PreCheck → Build → Transfer → Deploy → HealthCheck
실패 시 auto_rollback=True이면 Rollback 단계를 수행한다.
진행 상황은 asyncio.Queue를 통해 WebSocket 라우터에 전달된다.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import aiosqlite

from aidevops.agents.deployment import health_checker, ssh_deployer
from aidevops.config import settings
from aidevops.models.deployment import DeployOptions

logger = logging.getLogger("aidevops.deployment_agent")

# deployment_id → asyncio.Queue (WebSocket 라우터와 공유)
_deploy_queues: dict[str, asyncio.Queue] = {}


def get_queue(deployment_id: str) -> asyncio.Queue | None:
    return _deploy_queues.get(deployment_id)


def create_queue(deployment_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _deploy_queues[deployment_id] = q
    return q


def remove_queue(deployment_id: str) -> None:
    _deploy_queues.pop(deployment_id, None)


# ──────────────────────────────────────────────
# 이벤트 헬퍼
# ──────────────────────────────────────────────

async def _emit(queue: asyncio.Queue, event: str, data: dict[str, Any]) -> None:
    await queue.put({"event": event, "data": data})


async def _step_start(queue: asyncio.Queue, step: str) -> None:
    await _emit(queue, "step_start", {"step": step})


async def _step_log(queue: asyncio.Queue, step: str, line: str) -> None:
    await _emit(queue, "log", {"step": step, "line": line})


async def _step_done(queue: asyncio.Queue, step: str, duration: float) -> None:
    await _emit(queue, "step_done", {"step": step, "duration_sec": round(duration, 1)})


async def _step_fail(queue: asyncio.Queue, step: str, error: str) -> None:
    await _emit(queue, "step_fail", {"step": step, "error": error})


# ──────────────────────────────────────────────
# DB 헬퍼
# ──────────────────────────────────────────────

async def _update_deployment(db: aiosqlite.Connection, deployment_id: str, **kwargs) -> None:
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [deployment_id]
    await db.execute(f"UPDATE deployments SET {sets} WHERE id = ?", values)
    await db.commit()


async def _upsert_step(
    db: aiosqlite.Connection,
    deployment_id: str,
    step_name: str,
    status: str,
    duration_sec: float | None = None,
    log_output: str = "",
) -> None:
    cursor = await db.execute(
        "SELECT id FROM deploy_steps WHERE deployment_id = ? AND name = ?",
        (deployment_id, step_name),
    )
    row = await cursor.fetchone()
    if row:
        await db.execute(
            "UPDATE deploy_steps SET status=?, duration_sec=?, log_output=? WHERE id=?",
            (status, duration_sec, log_output, row["id"]),
        )
    else:
        import uuid
        await db.execute(
            "INSERT INTO deploy_steps (id, deployment_id, name, status, duration_sec, log_output) VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), deployment_id, step_name, status, duration_sec, log_output),
        )
    await db.commit()


# ──────────────────────────────────────────────
# 메인 배포 로직
# ──────────────────────────────────────────────

async def run_deployment(
    deployment_id: str,
    project_id: str,
    server_id: str,
    strategy: str,
    options: DeployOptions,
    queue: asyncio.Queue,
) -> None:
    """배포를 실행하는 백그라운드 태스크 진입점."""
    logger.info("[DEPLOY LOOP] %s", type(asyncio.get_running_loop()).__name__)
    from aidevops.db.database import get_db

    try:
        async for db in get_db():
            await _run(db, deployment_id, project_id, server_id, strategy, options, queue)
            break
    except Exception as exc:
        logger.exception("run_deployment 예외 (deployment_id=%s): %s", deployment_id, exc)
        # DB 업데이트 시도 (실패해도 무시)
        try:
            from aidevops.db.database import get_db_context
            async with get_db_context() as db:
                await _update_deployment(db, deployment_id, status="failed", error_message=str(exc))
        except Exception:
            pass
        # WebSocket에 실패 이벤트 전달
        await queue.put({"event": "deploy_failed", "data": {"error": f"내부 오류: {exc}"}})
        await queue.put(None)


async def _run(
    db: aiosqlite.Connection,
    deployment_id: str,
    project_id: str,
    server_id: str,
    strategy: str,
    options: DeployOptions,
    queue: asyncio.Queue,
) -> None:
    async def emit_log(step: str, line: str) -> None:
        await _step_log(queue, step, line)
        logger.debug("[%s] %s: %s", deployment_id, step, line)

    # ── 프로젝트 정보 로드 ──────────────────────────
    cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    project = await cursor.fetchone()
    if not project:
        await _update_deployment(db, deployment_id, status="failed", error_message="Project not found")
        await _emit(queue, "deploy_failed", {"error": "Project not found"})
        await queue.put(None)
        return

    cursor = await db.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
    server = await cursor.fetchone()
    if not server:
        await _update_deployment(db, deployment_id, status="failed", error_message="Server not found")
        await _emit(queue, "deploy_failed", {"error": "Server not found"})
        await queue.put(None)
        return

    project_path = Path(project["path"])
    remote_app_dir = options.remote_app_dir or f"/app/{project['name']}"
    compose_file = project_path / "docker-compose.yml"
    conn = None
    image_name = f"aidevops-{project_id[:8]}"

    # ── 자격증명 복호화 ────────────────────────────
    from aidevops.security.credential_vault import decrypt
    ssh_host = server["host"]
    ssh_port = int(server["port"])
    ssh_user = server["username"]
    cred_id = server["credential_id"]

    private_key: str | None = None
    password: str | None = None

    if cred_id:
        cursor = await db.execute("SELECT * FROM credentials WHERE id = ?", (cred_id,))
        cred = await cursor.fetchone()
        if cred:
            raw = decrypt(cred["encrypted_value"])
            if cred["type"] == "ssh_private_key":
                private_key = raw
            else:
                password = raw

    # ══════════════════════════════════════════════
    # STEP 1: PreCheck
    # ══════════════════════════════════════════════
    step = "precheck"
    t0 = time.monotonic()
    await _step_start(queue, step)
    await _upsert_step(db, deployment_id, step, "running")
    logs: list[str] = []

    try:
        # Windows에서 SelectorEventLoop 체크 — subprocess 미지원
        import sys as _sys
        if _sys.platform == "win32" and not isinstance(asyncio.get_running_loop(), asyncio.ProactorEventLoop):
            raise RuntimeError(
                "Core Engine이 SelectorEventLoop에서 실행 중입니다.\n"
                "Core Engine을 완전히 종료한 후 재시작하세요."
            )

        # local_build: 로컬 Docker 및 Dockerfile 확인
        if strategy == "local_build":
            dockerfile = project_path / "Dockerfile"
            if not dockerfile.exists():
                raise RuntimeError(
                    f"Dockerfile이 없습니다: {dockerfile}\n"
                    "먼저 Docker 탭에서 Dockerfile을 생성하거나 직접 추가하세요."
                )
            local_docker = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(local_docker.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                local_docker.kill()
                raise RuntimeError(
                    "로컬 Docker 응답 없음 (10초 초과). Docker Desktop이 실행 중인지 확인하세요."
                )
            if local_docker.returncode != 0:
                raise RuntimeError(
                    "로컬 머신에 Docker가 설치되어 있지 않거나 실행 중이지 않습니다.\n"
                    "Docker Desktop을 설치하고 실행한 후 다시 시도하세요."
                )
            await emit_log(step, "로컬 Docker 확인 완료")
            logs.append("로컬 Docker 확인 완료")

        conn = await ssh_deployer.connect(ssh_host, ssh_port, ssh_user, private_key=private_key, password=password)
        await emit_log(step, f"SSH 연결 성공: {ssh_user}@{ssh_host}:{ssh_port}")
        logs.append(f"SSH 연결 성공: {ssh_user}@{ssh_host}:{ssh_port}")

        docker_ok, docker_err = await ssh_deployer.check_docker(conn)
        if not docker_ok:
            raise RuntimeError(docker_err)
        await emit_log(step, "Docker 확인 완료")
        logs.append("Docker 확인 완료")

        free_mb = await ssh_deployer.check_disk_space(conn)
        await emit_log(step, f"남은 디스크 공간: {free_mb} MB")
        logs.append(f"남은 디스크 공간: {free_mb} MB")
        if 0 < free_mb < 500:
            raise RuntimeError(f"디스크 공간 부족: {free_mb} MB")

        await ssh_deployer.ensure_remote_dir(conn, remote_app_dir)
        await emit_log(step, f"원격 디렉토리 확인: {remote_app_dir}")
        logs.append(f"원격 디렉토리 확인: {remote_app_dir}")

    except Exception as exc:
        error_msg = str(exc) or f"{type(exc).__name__} (메시지 없음)"
        dur = time.monotonic() - t0
        await _upsert_step(db, deployment_id, step, "failed", dur, "\n".join(logs))
        await _update_deployment(db, deployment_id, status="failed", error_message=error_msg)
        await _step_fail(queue, step, error_msg)
        await _emit(queue, "deploy_failed", {"error": error_msg})
        await queue.put(None)
        if conn:
            conn.close()
        return

    dur = time.monotonic() - t0
    await _upsert_step(db, deployment_id, step, "done", dur, "\n".join(logs))
    await _step_done(queue, step, dur)

    # ══════════════════════════════════════════════
    # STEP 2: Build (로컬 docker build)
    # ══════════════════════════════════════════════
    step = "build"
    t0 = time.monotonic()
    await _step_start(queue, step)
    await _upsert_step(db, deployment_id, step, "running")
    logs = []

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-t", image_name, str(project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            logs.append(line)
            await emit_log(step, line)
        await proc.wait()
        if proc.returncode != 0:
            tail = [l for l in logs[-20:] if l.strip()][-5:]
            detail = "\n".join(tail) if tail else ""
            raise RuntimeError(
                f"docker build 실패 (exit {proc.returncode})" + (f"\n{detail}" if detail else "")
            )
        await emit_log(step, f"이미지 빌드 완료: {image_name}")
        logs.append(f"이미지 빌드 완료: {image_name}")

    except Exception as exc:
        error_msg = str(exc) or f"{type(exc).__name__} (메시지 없음)"
        dur = time.monotonic() - t0
        await _upsert_step(db, deployment_id, step, "failed", dur, "\n".join(logs))
        await _update_deployment(db, deployment_id, status="failed", error_message=error_msg)
        await _step_fail(queue, step, error_msg)
        await _emit(queue, "deploy_failed", {"error": error_msg})
        await queue.put(None)
        conn.close()
        return

    dur = time.monotonic() - t0
    await _upsert_step(db, deployment_id, step, "done", dur, "\n".join(logs))
    await _step_done(queue, step, dur)

    # ══════════════════════════════════════════════
    # STEP 3: Transfer (docker save → SFTP → docker load)
    # ══════════════════════════════════════════════
    step = "transfer"
    t0 = time.monotonic()
    await _step_start(queue, step)
    await _upsert_step(db, deployment_id, step, "running")
    logs = []

    tar_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tf:
            tar_path = tf.name

        await emit_log(step, f"이미지 저장 중: {tar_path}")
        save_proc = await asyncio.create_subprocess_exec(
            "docker", "save", "-o", tar_path, image_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr_data = await save_proc.communicate()
        if save_proc.returncode != 0:
            raise RuntimeError(f"docker save 실패: {stderr_data.decode('utf-8', errors='replace')}")
        logs.append(f"이미지 저장 완료: {tar_path}")
        await emit_log(step, "이미지 저장 완료")

        remote_tar = f"{remote_app_dir}/{image_name}.tar"
        await ssh_deployer.upload_file(conn, tar_path, remote_tar)
        await emit_log(step, f"SFTP 전송 완료: {remote_tar}")
        logs.append(f"SFTP 전송 완료: {remote_tar}")

        result = await ssh_deployer.run(conn, f"docker load -i {remote_tar}")
        if result.exit_status != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"docker load 실패 (exit {result.exit_status})" + (f"\n{detail}" if detail else ""))
        await emit_log(step, result.stdout.strip())
        logs.append(result.stdout.strip())

        await ssh_deployer.run(conn, f"rm -f {remote_tar}")
        await emit_log(step, "임시 tar 파일 삭제 완료")
        logs.append("임시 tar 파일 삭제 완료")

        # compose 파일 전송 — build: 섹션을 로드된 이미지명으로 교체
        if compose_file.exists():
            import re as _re
            compose_text = compose_file.read_text(encoding="utf-8")
            # build: ... 블록을 image: {image_name} 으로 교체
            patched = _re.sub(
                r"(\s+)build:\s*\n(?:\s+\S.*\n)*",
                lambda m: f"{m.group(1)}image: {image_name}\n",
                compose_text,
            )
            remote_compose = f"{remote_app_dir}/docker-compose.yml"
            await ssh_deployer.upload_bytes(conn, patched.encode("utf-8"), remote_compose)
            await emit_log(step, f"docker-compose.yml 전송 완료 (image: {image_name})")
            logs.append(f"docker-compose.yml 전송 완료")

        os.unlink(tar_path)
        tar_path = None

    except Exception as exc:
        if tar_path and os.path.exists(tar_path):
            os.unlink(tar_path)
        error_msg = str(exc) or f"{type(exc).__name__} (메시지 없음)"
        dur = time.monotonic() - t0
        await _upsert_step(db, deployment_id, step, "failed", dur, "\n".join(logs))
        await _update_deployment(db, deployment_id, status="failed", error_message=error_msg)
        await _step_fail(queue, step, error_msg)
        await _emit(queue, "deploy_failed", {"error": error_msg})
        await queue.put(None)
        conn.close()
        return

    dur = time.monotonic() - t0
    await _upsert_step(db, deployment_id, step, "done", dur, "\n".join(logs))
    await _step_done(queue, step, dur)

    # ══════════════════════════════════════════════
    # STEP 4: Deploy (docker compose up)
    # ══════════════════════════════════════════════
    step = "deploy"
    t0 = time.monotonic()
    await _step_start(queue, step)
    await _upsert_step(db, deployment_id, step, "running")
    logs = []

    previous_image: str | None = None  # rollback용
    compose_cmd = "docker compose"  # fallback; get_docker_compose_cmd로 덮어씀

    try:
        compose_cmd = await ssh_deployer.get_docker_compose_cmd(conn)

        # 현재 실행중인 이미지 ID 기록 (rollback 대비)
        prev_result = await ssh_deployer.run(
            conn,
            f"cd {remote_app_dir} && docker ps -q --filter label=com.docker.compose.project 2>/dev/null | head -1",
        )
        previous_image = prev_result.stdout.strip() or None

        result = await ssh_deployer.run(
            conn, f"cd {remote_app_dir} && {compose_cmd} up -d --pull missing --no-build 2>&1"
        )
        for line in (result.stdout or "").splitlines():
            logs.append(line)
            await emit_log(step, line)
        if result.exit_status != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            raise RuntimeError("docker compose up 실패\n" + "\n".join(detail[-5:]))

    except Exception as exc:
        error_msg = str(exc) or f"{type(exc).__name__} (메시지 없음)"
        dur = time.monotonic() - t0
        await _upsert_step(db, deployment_id, step, "failed", dur, "\n".join(logs))
        await _update_deployment(db, deployment_id, status="failed", error_message=error_msg)
        await _step_fail(queue, step, error_msg)
        await _emit(queue, "deploy_failed", {"error": error_msg})
        if options.auto_rollback:
            await _do_rollback(db, deployment_id, conn, remote_app_dir, compose_cmd, queue, logs)
        else:
            await queue.put(None)
            conn.close()
        return

    dur = time.monotonic() - t0
    await _upsert_step(db, deployment_id, step, "done", dur, "\n".join(logs))
    await _step_done(queue, step, dur)

    # ══════════════════════════════════════════════
    # STEP 5: HealthCheck
    # ══════════════════════════════════════════════
    step = "healthcheck"
    t0 = time.monotonic()
    await _step_start(queue, step)
    await _upsert_step(db, deployment_id, step, "running")
    logs = []

    health_url = options.health_check_url

    if not health_url:
        await emit_log(step, "헬스체크 URL이 설정되지 않아 건너뜁니다.")
        logs.append("헬스체크 URL 없음 — 스킵")
        dur = time.monotonic() - t0
        await _upsert_step(db, deployment_id, step, "done", dur, "\n".join(logs))
        await _step_done(queue, step, dur)
    else:
        passed = await health_checker.wait_for_health(health_url, timeout=options.health_check_timeout)

        if not passed:
            error = f"헬스 체크 실패: {health_url} ({options.health_check_timeout}초 초과)"
            dur = time.monotonic() - t0
            await _upsert_step(db, deployment_id, step, "failed", dur, "\n".join(logs))
            await _update_deployment(db, deployment_id, status="failed", error_message=error)
            await _step_fail(queue, step, error)
            await _emit(queue, "deploy_failed", {"error": error})
            if options.auto_rollback:
                compose_cmd = await ssh_deployer.get_docker_compose_cmd(conn)
                await _do_rollback(db, deployment_id, conn, remote_app_dir, compose_cmd, queue, [])
            else:
                await queue.put(None)
                conn.close()
            return

        await emit_log(step, "헬스 체크 통과")
        logs.append("헬스 체크 통과")
        dur = time.monotonic() - t0
        await _upsert_step(db, deployment_id, step, "done", dur, "\n".join(logs))
        await _step_done(queue, step, dur)

    # ── 배포 완료 ───────────────────────────────────
    from datetime import datetime, timezone

    # 헬스체크 URL이 없으면 서버 IP + 스캔된 포트로 서비스 URL 추론
    if not health_url:
        cursor2 = await db.execute(
            "SELECT ps.framework FROM project_scans ps WHERE ps.project_id = ? ORDER BY ps.scanned_at DESC LIMIT 1",
            (project_id,),
        )
        scan_row = await cursor2.fetchone()
        fw = (scan_row["framework"] or "").lower() if scan_row else ""
        _FW_PORTS = {
            "springboot": 8080, "quarkus": 8080, "micronaut": 8080,
            "express": 3000, "fastify": 3000, "nestjs": 3000, "nextjs": 3000,
            "fastapi": 8000, "django": 8000, "flask": 5000,
            "gin": 8080, "echo": 8080,
        }
        inferred_port = _FW_PORTS.get(fw, 8080)
        health_url = f"http://{ssh_host}:{inferred_port}"

    finished = datetime.now(timezone.utc).isoformat()
    await _update_deployment(
        db, deployment_id,
        status="success",
        finished_at=finished,
        service_url=health_url,
    )
    await _emit(queue, "deploy_done", {"service_url": health_url, "finished_at": finished})
    await queue.put(None)  # WebSocket 종료 신호
    conn.close()


async def _do_rollback(
    db: aiosqlite.Connection,
    deployment_id: str,
    conn,
    remote_app_dir: str,
    compose_cmd: str,
    queue: asyncio.Queue,
    parent_logs: list[str],
) -> None:
    step = "rollback"
    t0 = time.monotonic()
    await _step_start(queue, step)
    await _upsert_step(db, deployment_id, step, "running")
    logs: list[str] = []

    try:
        async for line in ssh_deployer.stream_run(
            conn, f"cd {remote_app_dir} && {compose_cmd} down 2>&1"
        ):
            logs.append(line)
            await _step_log(queue, step, line)
    except Exception as exc:
        logger.error("Rollback failed: %s", exc)

    dur = time.monotonic() - t0
    await _upsert_step(db, deployment_id, step, "done", dur, "\n".join(logs))
    await _step_done(queue, step, dur)
    await queue.put(None)
    conn.close()
