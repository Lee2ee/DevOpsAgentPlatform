"""
Audit Log 조회 API
  GET /audit            - 감사 로그 목록
  GET /audit/verify     - 해시체인 무결성 검증
"""

from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, Query

from aidevops.db.database import get_db
from aidevops.security import audit_logger

router = APIRouter(prefix="/audit", tags=["audit"])

DB = Annotated[aiosqlite.Connection, Depends(get_db)]


@router.get("")
async def list_audit_logs(
    db: DB,
    action: str | None = Query(default=None, description="action 필터 (예: scan, deploy)"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    records = await audit_logger.query(db, action=action, limit=limit, offset=offset)
    # metadata_json은 파싱하여 반환
    import json
    for r in records:
        if isinstance(r.get("metadata_json"), str):
            r["metadata"] = json.loads(r.pop("metadata_json"))
    return {"total": len(records), "records": records}


@router.get("/verify")
async def verify_audit_chain(db: DB):
    """해시체인 무결성을 검증한다. 변조가 없으면 valid=true."""
    return await audit_logger.verify_chain(db)
