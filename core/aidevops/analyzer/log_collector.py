"""
원격 서버 로그 수집기.
SSH를 통해 docker 컨테이너 로그 및 시스템 로그를 가져온다.
"""

import logging
from typing import AsyncGenerator

import asyncssh

from aidevops.agents.deployment import ssh_deployer

logger = logging.getLogger("aidevops.log_collector")

# 한 번에 가져올 최대 로그 줄 수
DEFAULT_LINES = 200


async def collect_container_logs(
    conn: asyncssh.SSHClientConnection,
    container_name: str,
    lines: int = DEFAULT_LINES,
) -> str:
    """docker logs 명령으로 컨테이너 로그를 수집한다."""
    result = await ssh_deployer.run(
        conn, f"docker logs --tail {lines} {container_name} 2>&1"
    )
    return result.stdout or ""


async def collect_compose_logs(
    conn: asyncssh.SSHClientConnection,
    app_dir: str,
    lines: int = DEFAULT_LINES,
) -> str:
    """docker compose logs 명령으로 전체 스택 로그를 수집한다."""
    compose_cmd = await ssh_deployer.get_docker_compose_cmd(conn)
    result = await ssh_deployer.run(
        conn, f"cd {app_dir} && {compose_cmd} logs --tail {lines} 2>&1"
    )
    return result.stdout or ""


async def collect_system_journal(
    conn: asyncssh.SSHClientConnection,
    lines: int = 100,
) -> str:
    """systemd journal에서 최근 에러 로그를 수집한다."""
    result = await ssh_deployer.run(
        conn, f"journalctl -p err -n {lines} --no-pager 2>/dev/null || dmesg | tail -n {lines}"
    )
    return result.stdout or ""


async def list_running_containers(conn: asyncssh.SSHClientConnection) -> list[str]:
    """실행 중인 컨테이너 이름 목록을 반환한다."""
    result = await ssh_deployer.run(conn, "docker ps --format '{{.Names}}' 2>/dev/null")
    names = [n.strip() for n in result.stdout.splitlines() if n.strip()]
    return names
