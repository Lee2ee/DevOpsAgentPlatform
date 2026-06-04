"""
Core Engine HTTP 클라이언트.
모든 CLI 명령이 이 클라이언트를 통해 API를 호출한다.
"""

import httpx

BASE_URL = "http://127.0.0.1:8765/api/v1"
TIMEOUT = 30.0


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


def get(path: str, **params) -> dict:
    with _client() as c:
        r = c.get(path, params=params)
        r.raise_for_status()
        return r.json()


def post(path: str, json: dict | None = None) -> dict:
    with _client() as c:
        r = c.post(path, json=json or {})
        r.raise_for_status()
        return r.json()


def put(path: str, json: dict | None = None) -> dict:
    with _client() as c:
        r = c.put(path, json=json or {})
        r.raise_for_status()
        return r.json()


def delete(path: str) -> None:
    with _client() as c:
        r = c.delete(path)
        r.raise_for_status()


def is_server_running() -> bool:
    try:
        get("/health")
        return True
    except Exception:
        return False


def ensure_server_running(console=None) -> None:
    """서버 미실행 시 백그라운드로 자동 기동한다."""
    if is_server_running():
        return

    import subprocess
    import sys
    import time

    msg = "Core Engine이 실행 중이 아닙니다. 자동 시작합니다..."
    if console:
        console.print(f"[yellow]{msg}[/yellow]")
    else:
        print(msg)

    subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "aidevops.main:app",
            "--host", "127.0.0.1",
            "--port", "8765",
            "--log-level", "warning",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(10):
        time.sleep(1)
        if is_server_running():
            if console:
                console.print("[green]Core Engine 시작 완료[/green]")
            return

    raise RuntimeError("Core Engine 자동 시작 실패. 'aidevops server start'를 실행하세요.")
