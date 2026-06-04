"""
aidevops server start | stop | status
"""

import subprocess
import sys
import time

import typer
from rich.table import Table

from aidevops_cli import client
from aidevops_cli.console import console, err, info, ok, warn

app = typer.Typer(help="Core Engine 서버 관리")


@app.command()
def start(
    host: str = typer.Option("127.0.0.1", help="바인드 주소"),
    port: int = typer.Option(8765, help="포트"),
    background: bool = typer.Option(True, "--bg/--fg", help="백그라운드 실행"),
):
    """Core Engine 서버를 시작한다."""
    if client.is_server_running():
        warn("서버가 이미 실행 중입니다.")
        raise typer.Exit()

    cmd = [
        sys.executable, "-m", "uvicorn",
        "aidevops.main:app",
        "--host", host,
        "--port", str(port),
        "--log-level", "warning",
    ]

    if background:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        info("서버 기동 중...")
        for _ in range(10):
            time.sleep(1)
            if client.is_server_running():
                ok(f"서버 시작: http://{host}:{port}")
                return
        err("서버 시작 타임아웃. 로그를 확인하세요.")
        raise typer.Exit(1)
    else:
        info(f"서버 시작 (포그라운드): http://{host}:{port}")
        subprocess.run(cmd)


@app.command()
def stop():
    """실행 중인 Core Engine 서버를 종료한다."""
    import signal, os
    try:
        result = subprocess.run(
            ["pgrep", "-f", "aidevops.main:app"],
            capture_output=True, text=True,
        )
        pids = [int(p) for p in result.stdout.split() if p.strip()]
    except Exception:
        # Windows: taskkill 사용
        subprocess.run(
            ["taskkill", "/F", "/FI", "WINDOWTITLE eq aidevops*"],
            capture_output=True,
        )
        ok("종료 요청 전송 완료")
        return

    if not pids:
        warn("실행 중인 서버를 찾을 수 없습니다.")
        return

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    ok(f"서버 종료 요청 완료 (PID: {', '.join(str(p) for p in pids)})")


@app.command()
def status():
    """서버 상태를 출력한다."""
    if not client.is_server_running():
        err("서버가 실행 중이 아닙니다.")
        raise typer.Exit(1)

    data = client.get("/health")
    table = Table(show_header=False, box=None)
    table.add_row("[info]상태[/info]", f"[success]{data.get('status', '?')}[/success]")
    table.add_row("[info]앱[/info]", data.get("app", "?"))
    table.add_row("[info]버전[/info]", data.get("version", "?"))
    table.add_row("[info]URL[/info]", "http://127.0.0.1:8765")
    console.print(table)
