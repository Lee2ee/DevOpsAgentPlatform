"""
aidevops cicd generate <project_id> --platform github
aidevops cicd save <project_id> --generation-id <id>
"""

import typer
from rich.panel import Panel
from rich.syntax import Syntax

from aidevops_cli import client
from aidevops_cli.console import console, err, ok, warn

app = typer.Typer(help="CI/CD 파이프라인 생성")

_PLATFORMS = ["github_actions", "gitlab_ci", "jenkins", "azure_devops"]


@app.command("generate")
def generate(
    project_id: str = typer.Argument(..., help="프로젝트 ID"),
    platform: str = typer.Option("github_actions", "--platform", "-p",
                                  help=f"플랫폼: {', '.join(_PLATFORMS)}"),
    registry: str = typer.Option("", "--registry", help="컨테이너 레지스트리"),
    show: bool = typer.Option(False, "--show", help="생성 내용 미리보기"),
):
    """CI/CD 파이프라인 파일을 생성한다."""
    if platform not in _PLATFORMS:
        err(f"지원하지 않는 플랫폼: {platform}. 선택 가능: {', '.join(_PLATFORMS)}")
        raise typer.Exit(1)

    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    with console.status("생성 중..."):
        try:
            data = client.post("/cicd/generate", {
                "project_id": project_id,
                "platform": platform,
                "options": {"registry": registry},
            })
        except Exception as exc:
            err(f"생성 실패: {exc}")
            raise typer.Exit(1)

    if show:
        content = data.get("content", "")
        lang = "yaml" if platform != "jenkins" else "groovy"
        if content:
            console.print(Panel(
                Syntax(content, lang, theme="monokai"),
                title=f"{platform} 파이프라인",
            ))

    ok(f"생성 완료 (generation_id: {data.get('generation_id', '?')})")
    console.print(f"[muted]파일 경로: {data.get('file_path', '?')}[/muted]")


@app.command("save")
def save(
    project_id: str = typer.Argument(..., help="프로젝트 ID"),
    generation_id: str = typer.Option(..., "--generation-id", "-g", help="생성 ID"),
):
    """생성된 CI/CD 파일을 프로젝트 디렉토리에 저장한다."""
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
            data = client.post("/cicd/save", {
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
