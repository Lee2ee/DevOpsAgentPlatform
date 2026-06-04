from typing import Literal
from pydantic import BaseModel, Field


# ── AI Provider ────────────────────────────────────────────────

class AIProviderConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic", "groq"] = "ollama"
    model: str = "qwen2.5-coder:7b"
    base_url: str | None = "http://localhost:11434"
    offline_mode: bool = False
    has_api_key: bool = False   # api_key 설정 여부 (실제 키는 반환하지 않음)


class AIProviderConfigUpdate(BaseModel):
    provider: Literal["ollama", "openai", "anthropic", "groq"] | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None   # 입력 전용, 응답에는 포함하지 않음
    offline_mode: bool | None = None


# ── Credential ─────────────────────────────────────────────────

class CredentialCreate(BaseModel):
    key_name: str = Field(..., description="식별 이름 (예: ssh_key_prod)")
    type: Literal["ssh_private_key", "password", "api_key"]
    value: str = Field(..., description="평문 값 (저장 시 암호화됨)")


class CredentialResponse(BaseModel):
    id: str
    key_name: str
    type: str
    created_at: str


# ── Server ─────────────────────────────────────────────────────

class ServerCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    username: str
    auth_type: Literal["key", "password"] = "key"
    credential_id: str | None = None
    password: str | None = None   # 입력 전용, 저장 시 암호화됨


class ServerResponse(BaseModel):
    id: str
    name: str
    host: str
    port: int
    username: str
    auth_type: str
    credential_id: str | None
    has_credential: bool = False
    created_at: str
