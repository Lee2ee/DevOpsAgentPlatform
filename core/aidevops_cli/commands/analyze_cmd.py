"""
aidevops analyze <deployment_id>
aidevops analyze patch <analysis_id>
"""

import typer
from rich.panel import Panel
from rich.table import Table

from aidevops_cli import client
from aidevops_cli.console import console, err, info, ok, warn

app = typer.Typer(help="장애 분석 및 패치 제안")

_SEVERITY_STYLE = {
    "critical": "[bold red]critical[/bold red]",
    "high": "[red]high[/red]",
    "medium": "[yellow]medium[/yellow]",
    "low": "[green]low[/green]",
}


@app.callback(invoke_without_command=True)
def analyze(
    ctx: typer.Context,
    deployment_id: str = typer.Argument(None, help="배포 ID (로그 자동 수집)"),
    log_file: str = typer.Option(None, "--log-file", "-f", help="로그 파일 경로 (직접 입력)"),
    no_ai: bool = typer.Option(False, "--no-ai", help="AI 분석 비활성화"),
):
    """배포 장애를 분석한다."""
    if ctx.invoked_subcommand:
        return

    if not deployment_id and not log_file:
        console.print(ctx.get_help())
        raise typer.Exit()

    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    payload: dict = {"use_ai": not no_ai}
    if log_file:
        try:
            payload["log_text"] = open(log_file, encoding="utf-8", errors="replace").read()
        except OSError as exc:
            err(f"파일 읽기 실패: {exc}")
            raise typer.Exit(1)
    else:
        payload["deployment_id"] = deployment_id

    with console.status("분석 중..."):
        try:
            data = client.post("/analyze", payload)
        except Exception as exc:
            err(f"분석 실패: {exc}")
            raise typer.Exit(1)

    analysis_id = data["analysis_id"]
    overall = data["overall_severity"]
    errors = data.get("detected_errors", [])

    # 결과 테이블
    table = Table(title="탐지된 에러", show_lines=True)
    table.add_column("에러명", style="bold")
    table.add_column("심각도", justify="center")
    table.add_column("카테고리")
    table.add_column("조치 방법")

    for e in errors:
        table.add_row(
            e["name"],
            _SEVERITY_STYLE.get(e["severity"], e["severity"]),
            e["category"],
            e["suggestion"],
        )

    console.print(table)

    if data.get("ai_summary"):
        console.print(Panel(data["ai_summary"], title="AI 분석 요약"))

    console.print()
    sev_str = _SEVERITY_STYLE.get(overall, overall)
    info(f"전체 심각도: {sev_str}  |  analysis_id: {analysis_id}")
    console.print(f"[muted]패치 제안을 보려면: aidevops analyze patch {analysis_id}[/muted]")


@app.command("patch")
def patch(
    analysis_id: str = typer.Argument(..., help="분석 ID"),
    no_ai: bool = typer.Option(False, "--no-ai", help="AI 패치 제안 비활성화"),
    apply: bool = typer.Option(False, "--apply", help="첫 번째 패치 즉시 적용"),
):
    """분석 결과를 바탕으로 패치 제안을 생성한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    with console.status("패치 생성 중..."):
        try:
            patches = client.post(f"/analyze/{analysis_id}/patch", {"use_ai": not no_ai})
        except Exception as exc:
            err(f"패치 생성 실패: {exc}")
            raise typer.Exit(1)

    if not patches:
        warn("생성된 패치가 없습니다.")
        return

    for i, p in enumerate(patches, 1):
        console.print(Panel(
            f"[bold]{p['description']}[/bold]\n"
            f"파일: [cyan]{p['file_path']}[/cyan]  신뢰도: [yellow]{p['confidence']:.0%}[/yellow]\n\n"
            f"[dim]{p['diff_content']}[/dim]",
            title=f"패치 {i} / {len(patches)}",
        ))

    if apply and patches:
        first = patches[0]
        if not typer.confirm(f"패치 1번({first['file_path']})을 적용하시겠습니까?"):
            return
        try:
            result = client.post(
                f"/analyze/{analysis_id}/apply",
                {"patch_id": first["id"]},
            )
        except Exception as exc:
            err(f"패치 적용 실패: {exc}")
            raise typer.Exit(1)

        if result.get("success"):
            ok(f"패치 적용 완료: {first['file_path']}")
        else:
            err(f"패치 적용 실패:\n{result.get('output', '')}")
