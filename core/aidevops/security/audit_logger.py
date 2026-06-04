"""
Audit Logger - 모든 주요 작업을 해시체인으로 기록한다.

각 레코드는 이전 레코드의 hash를 포함하므로 변조 탐지가 가능하다.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

import aiosqlite


async def log(
    db: aiosqlite.Connection,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    project_path: str | None = None,
    target_server: str | None = None,
    status: str = "success",
    metadata: dict | None = None,
) -> None:
    """
    작업을 audit_logs에 기록한다.

    action 예시: scan, generate_docker, generate_cicd, deploy,
                 credential_create, server_create, config_update,
                 failure_analyze, fix_apply
    """
    prev_hash = await _get_last_hash(db)
    performed_at = datetime.now(timezone.utc).isoformat()

    record_data = {
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "project_path": project_path,
        "status": status,
        "performed_at": performed_at,
    }
    current_hash = _compute_hash(record_data, prev_hash)

    await db.execute(
        """INSERT INTO audit_logs(
               id, action, entity_type, entity_id,
               project_path, target_server, status,
               metadata_json, performed_at, prev_hash, hash
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            action,
            entity_type,
            entity_id,
            project_path,
            target_server,
            status,
            json.dumps(metadata or {}, ensure_ascii=False),
            performed_at,
            prev_hash,
            current_hash,
        ),
    )
    await db.commit()


async def query(
    db: aiosqlite.Connection,
    *,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """audit_logs를 최신 순으로 조회한다."""
    if action:
        cursor = await db.execute(
            "SELECT * FROM audit_logs WHERE action = ? ORDER BY performed_at DESC LIMIT ? OFFSET ?",
            (action, limit, offset),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM audit_logs ORDER BY performed_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def verify_chain(db: aiosqlite.Connection) -> dict:
    """
    해시체인 무결성을 검증한다.
    변조된 레코드가 있으면 해당 ID와 위치를 반환한다.
    """
    cursor = await db.execute(
        "SELECT id, action, entity_type, entity_id, project_path, status, performed_at, prev_hash, hash "
        "FROM audit_logs ORDER BY performed_at ASC"
    )
    rows = await cursor.fetchall()

    prev_hash: str | None = None
    for row in rows:
        expected_data = {
            "action": row["action"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "project_path": row["project_path"],
            "status": row["status"],
            "performed_at": row["performed_at"],
        }
        expected_hash = _compute_hash(expected_data, prev_hash)

        if row["hash"] != expected_hash:
            return {
                "valid": False,
                "tampered_record_id": row["id"],
                "message": f"레코드 {row['id']}에서 해시 불일치 감지",
            }
        if row["prev_hash"] != prev_hash:
            return {
                "valid": False,
                "tampered_record_id": row["id"],
                "message": f"레코드 {row['id']}의 prev_hash 불일치",
            }
        prev_hash = row["hash"]

    return {"valid": True, "checked_records": len(rows)}


# ── helpers ────────────────────────────────────────────────────

async def _get_last_hash(db: aiosqlite.Connection) -> str | None:
    cursor = await db.execute(
        "SELECT hash FROM audit_logs ORDER BY performed_at DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    return row["hash"] if row else None


def _compute_hash(record: dict, prev_hash: str | None) -> str:
    data = json.dumps(record, sort_keys=True, ensure_ascii=False) + (prev_hash or "")
    return hashlib.sha256(data.encode()).hexdigest()
