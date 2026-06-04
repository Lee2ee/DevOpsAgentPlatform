"""
aidevops deploy <project_id> <server_id>
aidevops deploy status <deployment_id>
"""

import time

import typer
from rich.live import Live
from rich.table import Table

from aidevops_cli import client
from aidevops_cli.console import console, err, info, ok, warn

app = typer.Typer(help="배포 관리")


def _status_table(data: dict) -> Table:
    table = Table(title=f"배포 상태: {data['deployment_id'][:8]}...", show_lines=False)
    table.add_column("단계", style="info")
    table.add_column("상태")
    table.add_column("소요 시간", justify="right")

    status_style = {
        "done": "[success]done[/success]",
        "running": "[warn]running...[/warn]",
        "failed": "[error]failed[/error]",
        "pending": "[muted]pending[/muted]",
        "rollback": "[warn]rollback[/warn]",
    }

    for step in data.get("steps", []):
        st = step["status"]
        dur = f"{step['duration_sec']}s" if step.get("duration_sec") else "-"
        table.add_row(step["name"], status_style.get(st, st), dur)

    return table


@app.callback(invoke_without_command=True)
def deploy(
    ctx: typer.Context,
    project_id: str = typer.Argument(None),
    server_id: str = typer.Argument(None),
    strategy: str = typer.Option("local_build", "--strategy", "-s",
                                  help="local_build | remote_build"),
    health_url: str = typer.Option(None, "--health-url", help="헬스 체크 URL"),
    no_rollback: bool = typer.Option(False, "--no-rollback", help="자동 롤백 비활성화"),
    watch: bool = typer.Option(True, "--watch/--no-watch", help="완료 시까지 상태 폴링"),
):
    """프로젝트를 서버에 배포한다."""
    if ctx.invoked_subcommand:
        return

    if not project_id or not server_id:
        console.print(ctx.get_help())
        raise typer.Exit()

    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    payload = {
        "project_id": project_id,
        "server_id": server_id,
        "strategy": strategy,
        "options": {
            "auto_rollback": not no_rollback,
        },
    }
    if health_url:
        payload["options"]["health_check_url"] = health_url

    with console.status("배포 시작 중..."):
        try:
            data = client.post("/deploy", payload)
        except Exception as exc:
            err(f"배포 시작 실패: {exc}")
            raise typer.Exit(1)

    deployment_id = data["deployment_id"]
    ws_url = data.get("ws_url", "")
    ok(f"배포 시작 (deployment_id: {deployment_id})")
    info(f"WebSocket 스트리밍: ws://127.0.0.1:8765{ws_url}")

    if not watch:
        return

    # 상태 폴링 (최대 10분)
    console.print()
    with Live(console=console, refresh_per_second=2) as live:
        for _ in range(200):
            time.sleep(3)
            try:
                status_data = client.get(f"/deploy/{deployment_id}")
            except Exception:
                continue
            live.update(_status_table(status_data))
            if status_data["status"] in ("success", "failed", "rollback"):
                break

    final = client.get(f"/deploy/{deployment_id}")
    console.print()
    if final["status"] == "success":
        ok(f"배포 성공! 서비스 URL: {final.get('service_url', '-')}")
    else:
        err(f"배포 실패: {final.get('error_message', '알 수 없는 오류')}")
        raise typer.Exit(1)


@app.command("status")
def status(
    deployment_id: str = typer.Argument(..., help="배포 ID"),
):
    """배포 상태를 조회한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    try:
        data = client.get(f"/deploy/{deployment_id}")
    except Exception as exc:
        err(f"조회 실패: {exc}")
        raise typer.Exit(1)

    console.print(_status_table(data))

    overall = data["status"]
    if overall == "success":
        ok(f"배포 성공 | URL: {data.get('service_url', '-')}")
    elif overall == "failed":
        err(f"배포 실패: {data.get('error_message', '-')}")
    else:
        info(f"상태: {overall}")
