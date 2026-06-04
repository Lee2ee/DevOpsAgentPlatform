"""
WebSocket 엔드포인트 - 배포 실시간 스트리밍.

WS /ws/deploy/{deployment_id}

배포 에이전트의 asyncio.Queue에서 이벤트를 읽어 JSON으로 전송한다.
큐에서 None을 받으면 연결을 닫는다.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from aidevops.agents.deployment.deployment_agent import get_queue

logger = logging.getLogger("aidevops.ws")
router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/deploy/{deployment_id}")
async def ws_deploy(websocket: WebSocket, deployment_id: str) -> None:
    await websocket.accept()

    queue = get_queue(deployment_id)
    if queue is None:
        logger.warning("WS: queue not found for %s", deployment_id)
        await websocket.send_text(json.dumps({"event": "deploy_failed", "data": {"error": "배포 큐를 찾을 수 없습니다. 서버가 재시작되었을 수 있습니다."}}))
        await websocket.close()
        return

    try:
        while True:
            # 타임아웃을 두어 클라이언트 연결 끊김 감지
            try:
                item = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"event": "ping", "data": {}}))
                continue

            if item is None:
                # 배포 완료 신호
                await websocket.close()
                logger.info("WS closed (done): %s", deployment_id)
                break

            await websocket.send_text(json.dumps(item))

    except WebSocketDisconnect:
        logger.info("WS disconnected by client: %s", deployment_id)
    except Exception as exc:
        logger.exception("WS error for %s: %s", deployment_id, exc)
