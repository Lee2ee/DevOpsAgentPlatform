"""
장애 분석 REST 엔드포인트.

POST /analyze            → 배포 ID 또는 로그 직접 입력으로 분석 실행
GET  /analyze/{id}       → 분석 결과 조회
POST /analyze/{id}/patch → 패치 제안 생성
POST /analyze/{id}/apply → 패치 적용 (로컬 파일에 직접 쓰기)
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aidevops.analyzer import failure_analyzer, patch_generator
from aidevops.analyzer.log_collector import (
    collect_compose_logs,
    collect_container_logs,
)
from aidevops.agents.deployment import ssh_deployer
from aidevops.db.database import get_db
from aidevops.security.audit_logger import log as audit_log
from aidevops.security.credential_vault import decrypt

router = APIRouter(prefix="/analyze", tags=["analyze"])


# ──────────────────────────────────────────────
# Request / Response 모델
# ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    deployment_id: str | None = None   # 배포 ID로 서버/로그 자동 수집
    log_text: str | None = None        # 또는 직접 로그 입력
    use_ai: bool = True


class DetectedErrorOut(BaseModel):
    name: str
    severity: str
    category: str
    suggestion: str
    matched_lines: list[str]


class AnalyzeResponse(BaseModel):
    analysis_id: str
    overall_severity: str
    detected_errors: list[DetectedErrorOut]
    ai_summary: str
    analyzed_at: str


class PatchOut(BaseModel):
    id: str
    file_path: str
    description: str
    diff_content: str
    confidence: float
    applied: bool


class PatchRequest(BaseModel):
    use_ai: bool = True


class ApplyPatchRequest(BaseModel):
    patch_id: str


# ──────────────────────────────────────────────
# 공통 헬퍼
# ──────────────────────────────────────────────

async def _get_ai_provider(db: aiosqlite.Connection):
    """현재 설정된 AI 프로바이더 인스턴스를 반환한다."""
    cursor = await db.execute(
        "SELECT value_json FROM app_config WHERE key = 'ai_provider'"
    )
    row = await cursor.fetchone()
    if not row:
        return None
    cfg = json.loads(row["value_json"])

    provider_type = cfg.get("provider", "ollama")
    if provider_type == "ollama":
        from aidevops.ai.ollama_provider import OllamaProvider
        return OllamaProvider(
            base_url=cfg.get("base_url", "http://localhost:11434"),
            model=cfg.get("model", "qwen2.5-coder:7b"),
        )
    return None


async def _collect_logs_from_deployment(
    db: aiosqlite.Connection, deployment_id: str
) -> str:
    """배포 정보를 이용해 원격 서버에서 로그를 수집한다."""
    cursor = await db.execute("SELECT * FROM deployments WHERE id = ?", (deployment_id,))
    dep = await cursor.fetchone()
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")

    cursor = await db.execute("SELECT * FROM servers WHERE id = ?", (dep["server_id"],))
    server = await cursor.fetchone()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    private_key: str | None = None
    password: str | None = None
    if server["credential_id"]:
        cursor = await db.execute(
            "SELECT * FROM credentials WHERE id = ?", (server["credential_id"],)
        )
        cred = await cursor.fetchone()
        if cred:
            raw = decrypt(cred["encrypted_value"])
            if cred["type"] == "ssh_private_key":
                private_key = raw
            else:
                password = raw

    try:
        conn = await ssh_deployer.connect(
            server["host"], int(server["port"]), server["username"],
            private_key=private_key, password=password,
        )
        # deployments 테이블에서 project name 기반으로 app_dir 추론
        cursor = await db.execute(
            "SELECT p.name FROM projects p JOIN deployments d ON d.project_id = p.id WHERE d.id = ?",
            (deployment_id,),
        )
        proj_row = await cursor.fetchone()
        app_dir = f"/app/{proj_row['name']}" if proj_row else "/app"

        logs = await collect_compose_logs(conn, app_dir)
        conn.close()
        return logs
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"로그 수집 실패: {exc}")


# ──────────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────────

@router.post("", response_model=AnalyzeResponse, status_code=201)
async def run_analysis(
    req: AnalyzeRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> AnalyzeResponse:
    if not req.deployment_id and not req.log_text:
        raise HTTPException(status_code=422, detail="deployment_id 또는 log_text 중 하나가 필요합니다")

    # 로그 수집
    if req.log_text:
        log_text = req.log_text
        deployment_id = req.deployment_id
        project_id = None
    else:
        log_text = await _collect_logs_from_deployment(db, req.deployment_id)
        deployment_id = req.deployment_id
        cursor = await db.execute(
            "SELECT project_id FROM deployments WHERE id = ?", (deployment_id,)
        )
        row = await cursor.fetchone()
        project_id = row["project_id"] if row else None

    # AI 프로바이더 로드 (use_ai=False면 None)
    ai_provider = None
    if req.use_ai:
        ai_provider = await _get_ai_provider(db)

    # 분석 실행
    result = await failure_analyzer.analyze(log_text, ai_provider)

    # DB 저장
    analysis_id = str(uuid.uuid4())
    analyzed_at = datetime.now(timezone.utc).isoformat()
    errors_json = json.dumps(
        [
            {
                "name": e.name,
                "severity": e.severity,
                "category": e.category,
                "suggestion": e.suggestion,
                "matched_lines": e.matched_lines,
            }
            for e in result.detected_errors
        ],
        ensure_ascii=False,
    )

    await db.execute(
        """INSERT INTO analyses
           (id, project_id, deployment_id, severity, error_type, errors_json, analyzed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            analysis_id,
            project_id,
            deployment_id,
            result.overall_severity,
            result.detected_errors[0].category if result.detected_errors else None,
            errors_json,
            analyzed_at,
        ),
    )
    await db.commit()

    await audit_log(
        db,
        action="analyze",
        entity_type="analysis",
        entity_id=analysis_id,
        metadata={"severity": result.overall_severity, "error_count": len(result.detected_errors)},
    )

    return AnalyzeResponse(
        analysis_id=analysis_id,
        overall_severity=result.overall_severity,
        detected_errors=[
            DetectedErrorOut(
                name=e.name,
                severity=e.severity,
                category=e.category,
                suggestion=e.suggestion,
                matched_lines=e.matched_lines,
            )
            for e in result.detected_errors
        ],
        ai_summary=result.ai_summary,
        analyzed_at=analyzed_at,
    )


@router.get("/{analysis_id}", response_model=AnalyzeResponse)
async def get_analysis(
    analysis_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> AnalyzeResponse:
    cursor = await db.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    errors = json.loads(row["errors_json"] or "[]")
    return AnalyzeResponse(
        analysis_id=row["id"],
        overall_severity=row["severity"],
        detected_errors=[DetectedErrorOut(**e) for e in errors],
        ai_summary="",
        analyzed_at=row["analyzed_at"],
    )


@router.post("/{analysis_id}/patch", response_model=list[PatchOut])
async def generate_patches(
    analysis_id: str,
    req: PatchRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> list[PatchOut]:
    cursor = await db.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")

    errors_data = json.loads(row["errors_json"] or "[]")
    from aidevops.analyzer.failure_analyzer import AnalysisResult, DetectedError
    result = AnalysisResult(
        detected_errors=[DetectedError(**e) for e in errors_data],
        overall_severity=row["severity"],
    )

    # 프로젝트 경로
    project_path = "."
    if row["project_id"]:
        cursor = await db.execute("SELECT path FROM projects WHERE id = ?", (row["project_id"],))
        proj = await cursor.fetchone()
        if proj:
            project_path = proj["path"]

    ai_provider = None
    if req.use_ai:
        ai_provider = await _get_ai_provider(db)

    suggestions = await patch_generator.generate_patches(result, project_path, ai_provider)

    # DB 저장
    out: list[PatchOut] = []
    for s in suggestions:
        patch_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO patches (id, analysis_id, file_path, diff_content, description, confidence)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (patch_id, analysis_id, s.file_path, s.diff_content, s.description, s.confidence),
        )
        out.append(PatchOut(
            id=patch_id,
            file_path=s.file_path,
            description=s.description,
            diff_content=s.diff_content,
            confidence=s.confidence,
            applied=False,
        ))
    await db.commit()

    return out


@router.post("/{analysis_id}/apply", response_model=dict)
async def apply_patch(
    analysis_id: str,
    req: ApplyPatchRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    cursor = await db.execute(
        "SELECT p.*, a.project_id FROM patches p JOIN analyses a ON p.analysis_id = a.id WHERE p.id = ?",
        (req.patch_id,),
    )
    patch = await cursor.fetchone()
    if not patch:
        raise HTTPException(status_code=404, detail="Patch not found")
    if patch["applied"]:
        raise HTTPException(status_code=409, detail="이미 적용된 패치입니다")

    # 프로젝트 경로 확인
    project_path = Path(".")
    if patch["project_id"]:
        cursor = await db.execute("SELECT path FROM projects WHERE id = ?", (patch["project_id"],))
        proj = await cursor.fetchone()
        if proj:
            project_path = Path(proj["path"])

    target_file = project_path / patch["file_path"]
    if not target_file.exists():
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {target_file}")

    # diff_content를 파일에 기록 (백업 후 patch 명령 실행)
    import subprocess, tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False, encoding="utf-8") as tf:
        tf.write(patch["diff_content"])
        patch_file = tf.name

    try:
        proc = subprocess.run(
            ["patch", "-p1", "--input", patch_file],
            cwd=str(project_path),
            capture_output=True, text=True,
        )
        success = proc.returncode == 0
        output = proc.stdout + proc.stderr
    except FileNotFoundError:
        # patch 명령어 없으면 실패 안내
        success = False
        output = "`patch` 명령어가 설치되어 있지 않습니다. 수동으로 diff를 적용하세요."
    finally:
        os.unlink(patch_file)

    if success:
        applied_at = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE patches SET applied = 1, applied_at = ? WHERE id = ?",
            (applied_at, req.patch_id),
        )
        await db.commit()
        await audit_log(
            db, action="patch_apply", entity_type="patch", entity_id=req.patch_id, status="success"
        )

    return {"success": success, "output": output}
