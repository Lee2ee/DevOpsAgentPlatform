"""
aidevops docker generate <project_id>
aidevops docker save <project_id>
"""

import typer
from rich.panel import Panel
from rich.syntax import Syntax

from aidevops_cli import client
from aidevops_cli.console import console, err, ok, warn

app = typer.Typer(help="Dockerfile / docker-compose 생성")


@app.command("generate")
def generate(
    project_id: str = typer.Argument(..., help="프로젝트 ID"),
    registry: str = typer.Option("", "--registry", help="Docker 레지스트리 주소 (선택)"),
    show: bool = typer.Option(False, "--show", help="생성된 Dockerfile 미리보기"),
):
    """Dockerfile과 docker-compose.yml을 생성한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    with console.status("생성 중..."):
        try:
            data = client.post("/docker/generate", {
                "project_id": project_id,
                "options": {"registry": registry or None},
            })
        except Exception as exc:
            err(f"생성 실패: {exc}")
            raise typer.Exit(1)

    warnings = data.get("warnings", [])
    if warnings:
        for w in warnings:
            warn(w)

    if show:
        dockerfile = data.get("dockerfile", "")
        if dockerfile:
            console.print(Panel(
                Syntax(dockerfile, "dockerfile", theme="monokai"),
                title="Dockerfile",
            ))

    ok(f"생성 완료 (generation_id: {data.get('generation_id', '?')})")
    console.print("[muted]저장하려면: aidevops docker save <project_id> --generation-id <id>[/muted]")


@app.command("save")
def save(
    project_id: str = typer.Argument(..., help="프로젝트 ID"),
    generation_id: str = typer.Option(..., "--generation-id", "-g", help="생성 ID"),
):
    """생성된 Docker 파일을 프로젝트 디렉토리에 저장한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    # 프로젝트 경로 조회
    try:
        proj = client.get(f"/projects/{project_id}")
    except Exception as exc:
        err(f"프로젝트 조회 실패: {exc}")
        raise typer.Exit(1)

    with console.status("저장 중..."):
        try:
            data = client.post("/docker/save", {
                "generation_id": generation_id,
                "project_path": proj["path"],
                "overwrite": True,
            })
        except Exception as exc:
            err(f"저장 실패: {exc}")
            raise typer.Exit(1)

    saved = data.get("saved_files", [])
    for f in saved:
        ok(f"저장: {f}")
