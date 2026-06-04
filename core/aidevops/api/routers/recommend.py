"""
추천 API
  GET /projects/{id}/recommend - 프로젝트 배포 타겟 추천
"""
import json
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from aidevops.db.database import get_db
from aidevops.models.project import Dependency, Recommendation, ScanResult
from aidevops.recommender.deployment_recommender import recommend

router = APIRouter(prefix="/projects", tags=["recommend"])

DB = Annotated[aiosqlite.Connection, Depends(get_db)]


@router.get("/{project_id}/recommend", response_model=Recommendation)
async def get_recommendation(project_id: str, db: DB):
    """최신 스캔 결과를 기반으로 배포 타겟을 추천한다."""
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

    scan = ScanResult(
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

    return recommend(scan)
