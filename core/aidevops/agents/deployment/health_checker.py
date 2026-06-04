"""
HTTP 헬스 체크 유틸리티.
지정한 URL이 200을 반환할 때까지 재시도한다.
"""

import asyncio
import logging

import httpx

logger = logging.getLogger("aidevops.health_checker")


async def wait_for_health(url: str, timeout: int = 60, interval: float = 3.0) -> bool:
    """
    URL이 HTTP 200을 반환할 때까지 최대 timeout초 동안 재시도한다.
    성공하면 True, 타임아웃이면 False를 반환한다.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient(timeout=5.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url)
                if resp.status_code < 400:
                    logger.info("Health check passed: %s (status=%d)", url, resp.status_code)
                    return True
            except Exception as exc:
                logger.debug("Health check attempt failed: %s – %s", url, exc)
            await asyncio.sleep(interval)
    logger.warning("Health check timed out after %ds: %s", timeout, url)
    return False
