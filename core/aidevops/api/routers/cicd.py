"""
CI/CD 생성 API
  POST /cicd/generate  - CI/CD 파이프라인 파일 생성
  POST /cicd/save      - 생성된 파일을 프로젝트에 저장
"""

import json
import uuid
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from aidevops.api.routers.docker import _load_scan
from aidevops.db.database import get_db
from aidevops.security import audit_logger
from aidevops.generators.cicd.cicd_generator import generate
from aidevops.models.cicd import (
    CicdGenerateRequest,
    CicdGenerateResult,
    CicdSaveRequest,
    CicdSaveResult,
)

router = APIRouter(prefix="/cicd", tags=["cicd"])

DB = Annotated[aiosqlite.Connection, Depends(get_db)]


@router.post("/generate", response_model=CicdGenerateResult)
async def generate_cicd(body: CicdGenerateRequest, db: DB):
    """CI/CD 파이프라인 파일을 생성하고 DB에 저장한다."""
    scan = await _load_scan(body.project_id, db)

    content, file_path = generate(scan, body.platform, body.options)

    generation_id = str(uuid.uuid4())
    stored = {
        "platform": body.platform,
        "file_path": file_path,
        "content": content,
    }
    await db.execute(
        "INSERT INTO generations(id, project_id, type, platform, content_json) VALUES(?,?,?,?,?)",
        (generation_id, body.project_id, "cicd", body.platform, json.dumps(stored)),
    )
    await db.commit()

    await audit_logger.log(
        db,
        action="generate_cicd",
        entity_type="project",
        entity_id=body.project_id,
        project_path=scan.path,
        metadata={"platform": body.platform, "file_path": file_path},
    )

    return CicdGenerateResult(
        generation_id=generation_id,
        platform=body.platform,
        file_path=file_path,
        content=content,
    )


@router.post("/save", response_model=CicdSaveResult)
async def save_cicd(body: CicdSaveRequest, db: DB):
    """생성된 CI/CD 파일을 프로젝트 경로에 저장한다."""
    from pathlib import Path

    cursor = await db.execute(
        "SELECT content_json FROM generations WHERE id = ? AND type = 'cicd'",
        (body.generation_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Generation not found")

    stored = json.loads(row["content_json"])
    root = Path(body.project_path)
    if not root.exists():
        raise HTTPException(status_code=422, detail=f"경로가 존재하지 않습니다: {body.project_path}")

    target = root / stored["file_path"]
    if target.exists() and not body.overwrite:
        return CicdSaveResult(saved_files=[])

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(stored["content"], encoding="utf-8")

    return CicdSaveResult(saved_files=[stored["file_path"]])
