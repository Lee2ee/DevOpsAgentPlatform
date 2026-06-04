"""
설정 관리 API
  GET  /config/ai             - AI Provider 설정 조회
  PUT  /config/ai             - AI Provider 설정 변경
  POST /config/credentials    - 자격증명 저장
  GET  /config/servers        - 서버 목록 조회
  POST /config/servers        - 서버 등록
  DELETE /config/servers/{id} - 서버 삭제
"""

import json
import uuid
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from aidevops.db.database import get_db
from aidevops.models.config import (
    AIProviderConfig,
    AIProviderConfigUpdate,
    CredentialCreate,
    CredentialResponse,
    ServerCreate,
    ServerResponse,
)
from aidevops.security.credential_vault import encrypt
from aidevops.security import audit_logger

router = APIRouter(prefix="/config", tags=["config"])

DB = Annotated[aiosqlite.Connection, Depends(get_db)]


async def _fetchone(db: aiosqlite.Connection, sql: str, params: tuple = ()):
    cursor = await db.execute(sql, params)
    return await cursor.fetchone()


# ── AI Provider ────────────────────────────────────────────────

@router.get("/ai", response_model=AIProviderConfig)
async def get_ai_config(db: DB):
    row = await _fetchone(db, "SELECT value_json FROM app_config WHERE key = 'ai_provider'")
    if row is None:
        return AIProviderConfig()
    data = json.loads(row["value_json"])
    has_api_key = bool(data.pop("api_key_encrypted", None))
    data.pop("api_key", None)
    return AIProviderConfig(**data, has_api_key=has_api_key)


@router.put("/ai", response_model=AIProviderConfig)
async def update_ai_config(body: AIProviderConfigUpdate, db: DB):
    row = await _fetchone(db, "SELECT value_json FROM app_config WHERE key = 'ai_provider'")
    current = json.loads(row["value_json"]) if row else {}

    updates = body.model_dump(exclude_none=True)
    if "api_key" in updates:
        updates["api_key_encrypted"] = encrypt(updates.pop("api_key"))

    current.update(updates)

    await db.execute(
        "INSERT INTO app_config(key, value_json, updated_at) VALUES('ai_provider', ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
        (json.dumps(current),),
    )
    await db.commit()

    current.pop("api_key_encrypted", None)
    current.pop("api_key", None)
    await audit_logger.log(db, action="config_update", entity_type="ai_provider",
                           metadata={"provider": current.get("provider"), "model": current.get("model")})
    return AIProviderConfig(**current)


# ── Credentials ────────────────────────────────────────────────

@router.post("/credentials", response_model=CredentialResponse, status_code=201)
async def create_credential(body: CredentialCreate, db: DB):
    existing = await _fetchone(db, "SELECT id FROM credentials WHERE key_name = ?", (body.key_name,))
    if existing:
        raise HTTPException(status_code=409, detail=f"key_name '{body.key_name}' already exists")

    cred_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO credentials(id, key_name, type, encrypted_value) VALUES(?,?,?,?)",
        (cred_id, body.key_name, body.type, encrypt(body.value)),
    )
    await db.commit()

    row = await _fetchone(
        db, "SELECT id, key_name, type, created_at FROM credentials WHERE id = ?", (cred_id,)
    )
    await audit_logger.log(db, action="credential_create", entity_type="credential",
                           entity_id=cred_id, metadata={"key_name": body.key_name, "type": body.type})
    return CredentialResponse(**dict(row))


# ── Servers ────────────────────────────────────────────────────

@router.get("/servers", response_model=list[ServerResponse])
async def list_servers(db: DB):
    cursor = await db.execute(
        "SELECT id, name, host, port, username, auth_type, credential_id, created_at "
        "FROM servers ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["has_credential"] = bool(d.get("credential_id"))
        result.append(ServerResponse(**d))
    return result


@router.post("/servers", response_model=ServerResponse, status_code=201)
async def create_server(body: ServerCreate, db: DB):
    server_id = str(uuid.uuid4())
    credential_id = body.credential_id
    auth_type = body.auth_type

    # 비밀번호 입력 시 credential 자동 생성
    if body.password:
        cred_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO credentials(id, key_name, type, encrypted_value) VALUES(?,?,?,?)",
            (cred_id, f"server_{server_id}_password", "password", encrypt(body.password)),
        )
        credential_id = cred_id
        auth_type = "password"
    elif credential_id:
        existing = await _fetchone(db, "SELECT id FROM credentials WHERE id = ?", (credential_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="credential_id not found")

    await db.execute(
        "INSERT INTO servers(id, name, host, port, username, auth_type, credential_id) VALUES(?,?,?,?,?,?,?)",
        (server_id, body.name, body.host, body.port, body.username, auth_type, credential_id),
    )
    await db.commit()

    row = await _fetchone(
        db,
        "SELECT id, name, host, port, username, auth_type, credential_id, created_at FROM servers WHERE id = ?",
        (server_id,),
    )
    await audit_logger.log(db, action="server_create", entity_type="server",
                           entity_id=server_id, target_server=body.host,
                           metadata={"name": body.name, "host": body.host})
    d = dict(row)
    d["has_credential"] = bool(d.get("credential_id"))
    return ServerResponse(**d)


@router.put("/servers/{server_id}", response_model=ServerResponse)
async def update_server(server_id: str, body: ServerCreate, db: DB):
    existing = await _fetchone(db, "SELECT id, credential_id FROM servers WHERE id = ?", (server_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Server not found")

    credential_id = existing["credential_id"]
    auth_type = body.auth_type

    # 새 비밀번호 입력 시 기존 credential 갱신 or 신규 생성
    if body.password:
        if credential_id:
            await db.execute(
                "UPDATE credentials SET encrypted_value=?, updated_at=datetime('now') WHERE id=?",
                (encrypt(body.password), credential_id),
            )
        else:
            cred_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO credentials(id, key_name, type, encrypted_value) VALUES(?,?,?,?)",
                (cred_id, f"server_{server_id}_password", "password", encrypt(body.password)),
            )
            credential_id = cred_id
        auth_type = "password"

    await db.execute(
        "UPDATE servers SET name=?, host=?, port=?, username=?, auth_type=?, credential_id=? WHERE id=?",
        (body.name, body.host, body.port, body.username, auth_type, credential_id, server_id),
    )
    await db.commit()
    row = await _fetchone(
        db,
        "SELECT id, name, host, port, username, auth_type, credential_id, created_at FROM servers WHERE id = ?",
        (server_id,),
    )
    await audit_logger.log(db, action="server_update", entity_type="server", entity_id=server_id,
                           target_server=body.host, metadata={"name": body.name})
    d = dict(row)
    d["has_credential"] = bool(d.get("credential_id"))
    return ServerResponse(**d)


@router.delete("/servers/{server_id}", status_code=204)
async def delete_server(server_id: str, db: DB):
    row = await _fetchone(db, "SELECT id FROM servers WHERE id = ?", (server_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    await db.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    await db.commit()
    await audit_logger.log(db, action="server_delete", entity_type="server", entity_id=server_id)
