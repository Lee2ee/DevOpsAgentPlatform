"""
설정(app_config)에서 AI Provider를 읽어 적절한 구현체를 반환한다.
"""

import json

import aiosqlite

from aidevops.ai.base import AIProvider
from aidevops.ai.claude_provider import ClaudeProvider
from aidevops.ai.ollama_provider import OllamaProvider
from aidevops.ai.openai_compat_provider import OpenAICompatProvider
from aidevops.security.credential_vault import decrypt


async def get_provider(db: aiosqlite.Connection) -> AIProvider | None:
    """
    DB 설정 기반으로 AIProvider를 생성한다.
    offline_mode=True 이거나 provider 미설정이면 None 반환.
    """
    cursor = await db.execute("SELECT value_json FROM app_config WHERE key = 'ai_provider'")
    row = await cursor.fetchone()
    if not row:
        return None

    cfg = json.loads(row["value_json"])
    if cfg.get("offline_mode"):
        return None

    provider = cfg.get("provider", "ollama")
    model = cfg.get("model", "qwen2.5-coder:7b")
    base_url = cfg.get("base_url", "http://localhost:11434")

    # API 키 복호화
    api_key = ""
    if cfg.get("api_key_encrypted"):
        try:
            api_key = decrypt(cfg["api_key_encrypted"])
        except Exception:
            pass

    if provider == "ollama":
        return OllamaProvider(base_url=base_url, model=model)
    if provider == "openai":
        return OpenAICompatProvider(api_key=api_key, model=model)
    if provider == "groq":
        return OpenAICompatProvider(
            api_key=api_key,
            model=model,
            base_url="https://api.groq.com/openai/v1",
        )
    if provider == "anthropic":
        return ClaudeProvider(api_key=api_key, model=model)

    return None
