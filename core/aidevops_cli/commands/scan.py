"""
aidevops scan <path>
"""

import typer
from rich.panel import Panel
from rich.table import Table

from aidevops_cli import client
from aidevops_cli.console import console, err, ok

app = typer.Typer(help="프로젝트 스캔")


@app.callback(invoke_without_command=True)
def scan(
    path: str = typer.Argument(..., help="스캔할 프로젝트 경로"),
    no_ai: bool = typer.Option(False, "--no-ai", help="AI 분석 없이 룰 기반만 사용"),
):
    """프로젝트를 스캔하여 언어/프레임워크/의존 서비스를 분석한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    with console.status("스캔 중..."):
        try:
            data = client.post("/projects/scan", {"path": path, "use_ai": not no_ai})
        except Exception as exc:
            err(f"스캔 실패: {exc}")
            raise typer.Exit(1)

    project_id = data.get("project_id", "?")

    # 기본 정보 (ScanResult 필드는 top-level에 있음)
    db_list = data.get("database", [])
    mq_list = data.get("message_queue", [])
    cache_list = data.get("cache", [])
    ext_list = data.get("external_services", [])
    all_services = db_list + mq_list + cache_list + ext_list

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[info]Project ID[/info]", project_id)
    table.add_row("[info]경로[/info]", data.get("path", path))
    table.add_row("[info]언어[/info]", data.get("language") or "unknown")
    table.add_row("[info]프레임워크[/info]", data.get("framework") or "-")
    table.add_row("[info]빌드 도구[/info]", data.get("build_tool") or "-")
    table.add_row("[info]버전[/info]", data.get("language_version") or "-")
    table.add_row("[info]외부 서비스[/info]", ", ".join(all_services) if all_services else "-")
    table.add_row("[info]신뢰도[/info]", f"{data.get('scan_confidence', 0):.0%}")

    warnings = []

    console.print(Panel(table, title="[bold]프로젝트 스캔 결과[/bold]", expand=False))

    if warnings:
        console.print("\n[warn]경고:[/warn]")
        for w in warnings:
            console.print(f"  • {w}")

    ok(f"스캔 완료 (project_id: {project_id})")
