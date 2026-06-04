"""
Docker 파일 생성 API
  POST /docker/generate  - Dockerfile + docker-compose.yml 생성
  POST /docker/save      - 생성된 파일을 프로젝트에 저장
"""

import json
import uuid
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from aidevops.db.database import get_db
from aidevops.security import audit_logger
from aidevops.generators.docker.compose_generator import generate_compose
from aidevops.generators.docker.dockerfile_generator import (
    generate_dockerfile,
    generate_dockerignore,
)
from aidevops.models.generation import (
    DockerGenerateRequest,
    DockerGenerateResult,
    DockerSaveRequest,
    DockerSaveResult,
)
from aidevops.models.project import Dependency, ScanResult

router = APIRouter(prefix="/docker", tags=["docker"])

DB = Annotated[aiosqlite.Connection, Depends(get_db)]


@router.post("/generate", response_model=DockerGenerateResult)
async def generate_docker(body: DockerGenerateRequest, db: DB):
    """ScanResult 기반으로 Dockerfile과 docker-compose.yml을 생성한다."""
    scan = await _load_scan(body.project_id, db)

    # Dockerfile 생성
    dockerfile, warnings = generate_dockerfile(scan, project_path=scan.path)

    # docker-compose.yml 생성
    compose_content: str | None = None
    if body.options.include_compose:
        compose_content, compose_warnings = generate_compose(scan, registry=body.options.registry)
        warnings.extend(compose_warnings)

    # .dockerignore 생성
    dockerignore = generate_dockerignore(scan)

    # DB에 생성 결과 저장
    generation_id = str(uuid.uuid4())
    content = {
        "dockerfile": dockerfile,
        "docker_compose": compose_content,
        "dockerignore": dockerignore,
        "warnings": warnings,
    }
    await db.execute(
        "INSERT INTO generations(id, project_id, type, content_json) VALUES(?,?,?,?)",
        (generation_id, body.project_id, "docker", json.dumps(content)),
    )
    await db.commit()

    await audit_logger.log(
        db,
        action="generate_docker",
        entity_type="project",
        entity_id=body.project_id,
        project_path=scan.path,
        metadata={"generation_id": generation_id, "warnings": warnings},
    )

    return DockerGenerateResult(
        generation_id=generation_id,
        dockerfile=dockerfile,
        docker_compose=compose_content,
        dockerignore=dockerignore,
        warnings=warnings,
    )


@router.post("/save", response_model=DockerSaveResult)
async def save_docker(body: DockerSaveRequest, db: DB):
    """생성된 Docker 파일을 프로젝트 경로에 저장한다."""
    from pathlib import Path

    cursor = await db.execute(
        "SELECT content_json FROM generations WHERE id = ? AND type = 'docker'",
        (body.generation_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Generation not found")

    content = json.loads(row["content_json"])
    root = Path(body.project_path)

    if not root.exists():
        raise HTTPException(status_code=422, detail=f"경로가 존재하지 않습니다: {body.project_path}")

    saved: list[str] = []

    def _write(filename: str, text: str | None):
        if not text:
            return
        target = root / filename
        if target.exists() and not body.overwrite:
            return
        target.write_text(text, encoding="utf-8")
        saved.append(filename)

    _write("Dockerfile", content.get("dockerfile"))
    _write("docker-compose.yml", content.get("docker_compose"))
    _write(".dockerignore", content.get("dockerignore"))

    return DockerSaveResult(saved_files=saved)


# ── helpers ────────────────────────────────────────────────────

async def _load_scan(project_id: str, db: aiosqlite.Connection) -> ScanResult:
    """DB에서 최신 ScanResult를 로드한다."""
    cursor = await db.execute(
        """SELECT p.id, p.path, p.name,
                  ps.language, ps.framework, ps.language_version, ps.build_tool,
                  ps.database_json, ps.message_queue_json, ps.cache_json,
                  ps.external_services_json, ps.dependencies_json,
                  ps.existing_docker, ps.existing_cicd, ps.scan_confidence, ps.scanned_at
           FROM projects p
           JOIN project_scans ps ON ps.project_id = p.id
           WHERE p.id = ?
           ORDER BY ps.scanned_at DESC
           LIMIT 1""",
        (project_id,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"프로젝트를 찾을 수 없습니다: {project_id}")

    return ScanResult(
        project_id=row["id"],
        path=row["path"],
        name=row["name"],
        language=row["language"],
        framework=row["framework"],
        language_version=row["language_version"],
        build_tool=row["build_tool"],
        database=json.loads(row["database_json"] or "[]"),
        message_queue=json.loads(row["message_queue_json"] or "[]"),
        cache=json.loads(row["cache_json"] or "[]"),
        storage=[],
        external_services=json.loads(row["external_services_json"] or "[]"),
        existing_docker=bool(row["existing_docker"]),
        existing_cicd=row["existing_cicd"] or "none",
        dependencies=[Dependency(**d) for d in json.loads(row["dependencies_json"] or "[]")],
        config_files=[],
        scan_confidence=row["scan_confidence"] or 0.0,
        scanned_at=row["scanned_at"] or "",
    )
