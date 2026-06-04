"""
AI DevOps Core Engine 진입점
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aidevops.api.middleware import RequestLoggingMiddleware
from aidevops.api.router import api_router
from aidevops.config import settings
from aidevops.db.database import get_db_context
from aidevops.db.migrations import run_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작: 데이터 디렉토리 생성 + DB 초기화
    settings.ensure_data_dir()
    async with get_db_context() as db:
        await run_migrations(db)
    logging.info("AI DevOps Core Engine started on %s:%d", settings.host, settings.port)
    yield
    # 종료
    logging.info("AI DevOps Core Engine stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(api_router)

    return app


app = create_app()


async def _serve() -> None:
    loop = asyncio.get_running_loop()
    logging.info("Event loop: %s", type(loop).__name__)
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


def run_server():
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_serve())
        finally:
            loop.close()
    else:
        asyncio.run(_serve())


if __name__ == "__main__":
    run_server()
