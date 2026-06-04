"""
프로젝트 스캔 API
  POST /projects/scan           - 프로젝트 스캔
  POST /projects/scan-workspace - 워크스페이스 서브 프로젝트 탐지
  GET  /projects                - 프로젝트 목록
  GET  /projects/{id}           - 프로젝트 상세 조회
"""

import json
import uuid
from pathlib import Path
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from aidevops.ai.provider_factory import get_provider
from aidevops.db.database import get_db
from aidevops.models.project import ProjectSummary, ScanRequest, ScanResult
from aidevops.scanner.scanner import scan
from aidevops.scanner.workspace_scanner import find_subprojects
from aidevops.security import audit_logger

router = APIRouter(prefix="/projects", tags=["projects"])

DB = Annotated[aiosqlite.Connection, Depends(get_db)]


@router.post("/scan", response_model=ScanResult)
async def scan_project(body: ScanRequest, db: DB):
    """프로젝트 폴더를 분석하여 ScanResult를 반환하고 DB에 저장한다."""
    ai_provider = await get_provider(db) if body.use_ai else None

    try:
        result = await scan(body.path, ai_provider=ai_provider)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"스캔 실패: {e}")

    # projects 테이블 upsert
    await db.execute(
        "INSERT INTO projects(id, path, name) VALUES(?,?,?) "
        "ON CONFLICT(path) DO UPDATE SET name=excluded.name, updated_at=datetime('now')",
        (result.project_id, result.path, result.name),
    )

    # 실제 project_id는 기존 레코드의 것을 사용할 수 있으므로 재조회
    cursor = await db.execute("SELECT id FROM projects WHERE path = ?", (result.path,))
    row = await cursor.fetchone()
    project_id = row["id"]
    result = result.model_copy(update={"project_id": project_id})

    # project_scans 테이블에 저장
    scan_id = str(uuid.uuid4())
    await db.execute(
        """INSERT INTO project_scans(
            id, project_id, language, framework, language_version, build_tool,
            database_json, message_queue_json, cache_json,
            external_services_json, dependencies_json,
            existing_docker, existing_cicd, scan_confidence
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            scan_id,
            project_id,
            result.language,
            result.framework,
            result.language_version,
            result.build_tool,
            json.dumps(result.database),
            json.dumps(result.message_queue),
            json.dumps(result.cache),
            json.dumps(result.external_services),
            json.dumps([d.model_dump() for d in result.dependencies]),
            1 if result.existing_docker else 0,
            result.existing_cicd,
            result.scan_confidence,
        ),
    )
    await db.commit()

    await audit_logger.log(
        db,
        action="scan",
        entity_type="project",
        entity_id=project_id,
        project_path=result.path,
        metadata={"language": result.language, "framework": result.framework,
                  "confidence": result.scan_confidence},
    )
    return result


class WorkspaceScanRequest(BaseModel):
    path: str

class SubProjectInfo(BaseModel):
    path: str
    rel_path: str
    name: str
    build_file: str

class WorkspaceScanResult(BaseModel):
    root: str
    root_name: str
    subprojects: list[SubProjectInfo]

@router.post("/scan-workspace", response_model=WorkspaceScanResult)
async def scan_workspace(body: WorkspaceScanRequest):
    """워크스페이스 루트에서 서브 프로젝트를 탐지하여 트리 구조 반환."""
    if not Path(body.path).is_dir():
        raise HTTPException(status_code=422, detail="유효한 디렉토리 경로가 아닙니다.")
    subs = find_subprojects(body.path)
    return WorkspaceScanResult(
        root=body.path,
        root_name=Path(body.path).name,
        subprojects=[
            SubProjectInfo(path=s.path, rel_path=s.rel_path, name=s.name, build_file=s.build_file)
            for s in subs
        ],
    )


@router.get("", response_model=list[ProjectSummary])
async def list_projects(db: DB):
    cursor = await db.execute(
        """SELECT p.id, p.path, p.name, ps.language, ps.framework, ps.scanned_at
           FROM projects p
           LEFT JOIN project_scans ps ON ps.project_id = p.id
           GROUP BY p.id
           ORDER BY p.updated_at DESC"""
    )
    rows = await cursor.fetchall()
    return [
        ProjectSummary(
            project_id=r["id"],
            path=r["path"],
            name=r["name"],
            language=r["language"],
            framework=r["framework"],
            scanned_at=r["scanned_at"] or "",
        )
        for r in rows
    ]


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: DB):
    # deploy_steps → deployments → project 순서로 삭제 (FK 제약)
    cursor = await db.execute("SELECT id FROM deployments WHERE project_id = ?", (project_id,))
    dep_ids = [r["id"] for r in await cursor.fetchall()]
    for dep_id in dep_ids:
        await db.execute("DELETE FROM deploy_steps WHERE deployment_id = ?", (dep_id,))
    await db.execute("DELETE FROM deployments WHERE project_id = ?", (project_id,))
    # patches → analyses → project
    cursor = await db.execute("SELECT id FROM analyses WHERE project_id = ?", (project_id,))
    ana_ids = [r["id"] for r in await cursor.fetchall()]
    for ana_id in ana_ids:
        await db.execute("DELETE FROM patches WHERE analysis_id = ?", (ana_id,))
    await db.execute("DELETE FROM analyses WHERE project_id = ?", (project_id,))
    await db.execute("DELETE FROM generations WHERE project_id = ?", (project_id,))
    await db.execute("DELETE FROM project_scans WHERE project_id = ?", (project_id,))
    await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    await db.commit()


@router.get("/{project_id}", response_model=ScanResult)
async def get_project(project_id: str, db: DB):
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
        raise HTTPException(status_code=404, detail="Project not found")

    from aidevops.models.project import Dependency
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
