"""
asyncssh 기반 SSH 유틸리티.
연결, 명령 실행, 파일 전송을 제공한다.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from pathlib import Path

import asyncssh

logger = logging.getLogger("aidevops.ssh")


async def connect(
    host: str,
    port: int,
    username: str,
    private_key: str | None = None,
    password: str | None = None,
) -> asyncssh.SSHClientConnection:
    """SSH 연결을 맺고 반환한다."""
    connect_kwargs: dict = {
        "host": host,
        "port": port,
        "username": username,
        "known_hosts": None,      # MVP: 호스트 검증 생략
        "connect_timeout": 15,
    }
    if private_key:
        key = asyncssh.import_private_key(private_key)
        connect_kwargs["client_keys"] = [key]
    elif password:
        connect_kwargs["password"] = password
    else:
        raise ValueError("private_key 또는 password 중 하나가 필요합니다")

    return await asyncssh.connect(**connect_kwargs)


async def run(
    conn: asyncssh.SSHClientConnection,
    command: str,
    check: bool = False,
) -> asyncssh.SSHCompletedProcess:
    """
    명령을 실행하고 결과를 반환한다.
    check=True이면 exit code != 0 시 예외를 발생시킨다.
    """
    result = await conn.run(command, check=check)
    return result


async def stream_run(
    conn: asyncssh.SSHClientConnection,
    command: str,
) -> AsyncGenerator[str, None]:
    """
    명령을 실행하고 출력을 한 줄씩 yield한다.
    """
    async with conn.create_process(command) as proc:
        async for line in proc.stdout:
            yield line.rstrip("\n")
        # stderr도 포함
        async for line in proc.stderr:
            yield f"[stderr] {line.rstrip(chr(10))}"
        await proc.wait()


async def upload_file(
    conn: asyncssh.SSHClientConnection,
    local_path: str | Path,
    remote_path: str,
) -> None:
    """로컬 파일을 원격 경로로 업로드한다."""
    async with conn.start_sftp_client() as sftp:
        await sftp.put(str(local_path), remote_path)


async def upload_bytes(
    conn: asyncssh.SSHClientConnection,
    data: bytes,
    remote_path: str,
) -> None:
    """bytes 데이터를 원격 파일로 저장한다."""
    async with conn.start_sftp_client() as sftp:
        async with sftp.open(remote_path, "wb") as f:
            await f.write(data)


async def ensure_remote_dir(
    conn: asyncssh.SSHClientConnection,
    remote_dir: str,
) -> None:
    """원격 디렉토리가 없으면 생성한다."""
    await run(conn, f"mkdir -p {remote_dir}")


async def check_disk_space(
    conn: asyncssh.SSHClientConnection,
    path: str = "/",
) -> int:
    """경로의 남은 디스크 공간(MB)을 반환한다."""
    result = await run(conn, f"df -BM {path} | tail -1 | awk '{{print $4}}'")
    mb_str = result.stdout.strip().rstrip("M")
    try:
        return int(mb_str)
    except ValueError:
        return -1


async def check_docker(conn: asyncssh.SSHClientConnection) -> tuple[bool, str]:
    """서버에 Docker가 설치되어 있고 데몬이 실행 중인지 확인한다.
    Returns (ok, error_message)."""
    # 바이너리 존재 확인
    bin_result = await run(conn, "docker --version 2>/dev/null")
    if bin_result.exit_status != 0:
        return False, "Docker가 설치되어 있지 않습니다"
    # 데몬 접근 확인
    daemon_result = await run(conn, "docker info 2>&1")
    if daemon_result.exit_status != 0:
        detail = daemon_result.stdout.strip().splitlines()[-1] if daemon_result.stdout.strip() else ""
        return False, f"Docker 데몬에 접근할 수 없습니다: {detail}"
    return True, ""


async def get_docker_compose_cmd(conn: asyncssh.SSHClientConnection) -> str:
    """docker compose 또는 docker-compose 명령어를 반환한다."""
    result = await run(conn, "docker compose version 2>/dev/null")
    if result.exit_status == 0:
        return "docker compose"
    return "docker-compose"
