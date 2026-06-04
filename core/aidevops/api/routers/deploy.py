"""
배포 REST 엔드포인트.

POST /deploy        → 배포 시작 (BackgroundTask)
GET  /deploy/{id}   → 배포 상태 조회
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

import aiosqlite

from aidevops.agents.deployment import deployment_agent
from aidevops.db.database import get_db
from aidevops.models.deployment import (
    DeployRequest,
    DeployStartResponse,
    DeployStatusResponse,
    DeployStepInfo,
)
from aidevops.security.audit_logger import log as audit_log

router = APIRouter(prefix="/deploy", tags=["deploy"])


@router.post("", response_model=DeployStartResponse, status_code=202)
async def start_deployment(
    req: DeployRequest,
    background_tasks: BackgroundTasks,
    db: aiosqlite.Connection = Depends(get_db),
) -> DeployStartResponse:
    # 프로젝트 존재 확인
    cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (req.project_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Project not found")

    # 서버 존재 확인
    cursor = await db.execute("SELECT id FROM servers WHERE id = ?", (req.server_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Server not found")

    deployment_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """INSERT INTO deployments
           (id, project_id, server_id, status, strategy, started_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (deployment_id, req.project_id, req.server_id, "running", req.strategy, started_at),
    )
    await db.commit()

    queue = deployment_agent.create_queue(deployment_id)

    background_tasks.add_task(
        deployment_agent.run_deployment,
        deployment_id,
        req.project_id,
        req.server_id,
        req.strategy,
        req.options,
        queue,
    )

    await audit_log(
        db,
        action="deploy_start",
        entity_type="deployment",
        entity_id=deployment_id,
        status="started",
        metadata={"project_id": req.project_id, "server_id": req.server_id, "strategy": req.strategy},
    )

    ws_url = f"/api/v1/ws/deploy/{deployment_id}"
    return DeployStartResponse(deployment_id=deployment_id, ws_url=ws_url)


@router.get("/{deployment_id}", response_model=DeployStatusResponse)
async def get_deployment(
    deployment_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> DeployStatusResponse:
    cursor = await db.execute(
        "SELECT * FROM deployments WHERE id = ?", (deployment_id,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")

    cursor = await db.execute(
        "SELECT * FROM deploy_steps WHERE deployment_id = ? ORDER BY rowid",
        (deployment_id,),
    )
    step_rows = await cursor.fetchall()
    steps = [
        DeployStepInfo(
            name=s["name"],
            status=s["status"],
            duration_sec=s["duration_sec"],
            log_output=s["log_output"] or "",
        )
        for s in step_rows
    ]

    return DeployStatusResponse(
        deployment_id=row["id"],
        project_id=row["project_id"],
        server_id=row["server_id"],
        status=row["status"],
        strategy=row["strategy"],
        steps=steps,
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        service_url=row["service_url"],
        error_message=row["error_message"],
    )
