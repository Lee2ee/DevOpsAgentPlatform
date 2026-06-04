from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import aiosqlite

from aidevops.config import settings


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """FastAPI 의존성: 요청당 DB 연결을 제공한다."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[aiosqlite.Connection, None]:
    """lifespan/스크립트용 컨텍스트 매니저."""
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
