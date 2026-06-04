"""
aidevops config ai        - AI 설정 조회/변경
aidevops config server    - 서버 목록 / 등록 / 삭제
"""

import typer
from rich.table import Table

from aidevops_cli import client
from aidevops_cli.console import console, err, ok

app = typer.Typer(help="AI / 서버 설정 관리")


# ── AI 설정 ──────────────────────────────────────

@app.command("ai")
def ai_config(
    provider: str = typer.Option(None, "--provider", help="ollama | openai | anthropic"),
    model: str = typer.Option(None, "--model", "-m", help="모델명"),
    base_url: str = typer.Option(None, "--base-url", help="API 엔드포인트 URL"),
):
    """AI 프로바이더 설정을 조회하거나 변경한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    if provider or model or base_url:
        payload: dict = {}
        if provider:
            payload["provider"] = provider
        if model:
            payload["model"] = model
        if base_url:
            payload["base_url"] = base_url
        try:
            data = client.put("/config/ai", payload)
        except Exception as exc:
            err(f"AI 설정 변경 실패: {exc}")
            raise typer.Exit(1)
        ok(f"AI 설정 변경: {data.get('provider')} / {data.get('model')}")
        return

    # 조회
    data = client.get("/config/ai")
    table = Table(show_header=False, box=None)
    table.add_row("[info]Provider[/info]", data.get("provider", "-"))
    table.add_row("[info]Model[/info]", data.get("model", "-"))
    table.add_row("[info]Base URL[/info]", data.get("base_url", "-"))
    console.print(table)


# ── 서버 설정 ────────────────────────────────────

@app.command("server-list")
def server_list():
    """등록된 서버 목록을 출력한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    data = client.get("/config/servers")
    servers = data if isinstance(data, list) else data.get("servers", [])

    if not servers:
        console.print("[muted]등록된 서버가 없습니다.[/muted]")
        return

    table = Table(title="등록된 서버")
    table.add_column("ID", style="dim")
    table.add_column("이름", style="bold")
    table.add_column("호스트")
    table.add_column("포트", justify="right")
    table.add_column("사용자")

    for s in servers:
        table.add_row(s["id"][:8] + "...", s.get("name", "-"), s["host"], str(s["port"]), s["username"])

    console.print(table)


@app.command("server-add")
def server_add(
    name: str = typer.Option(..., "--name", "-n", help="서버 별명"),
    host: str = typer.Option(..., "--host", help="호스트 주소"),
    port: int = typer.Option(22, "--port", help="SSH 포트"),
    username: str = typer.Option(..., "--user", "-u", help="SSH 사용자명"),
    password: str = typer.Option(None, "--password", "-p", help="SSH 비밀번호 (패스워드 인증)"),
    credential_id: str = typer.Option(None, "--credential-id", help="크리덴셜 ID (SSH 키 인증)"),
):
    """서버를 등록한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    payload = {
        "name": name,
        "host": host,
        "port": port,
        "username": username,
        "auth_type": "password" if password else "key",
        "password": password,
        "credential_id": credential_id,
    }
    try:
        data = client.post("/config/servers", payload)
    except Exception as exc:
        err(f"서버 등록 실패: {exc}")
        raise typer.Exit(1)

    ok(f"서버 등록 완료 (id: {data.get('id', '?')})")


@app.command("server-delete")
def server_delete(
    server_id: str = typer.Argument(..., help="서버 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="확인 없이 삭제"),
):
    """서버를 삭제한다."""
    try:
        client.ensure_server_running(console)
    except RuntimeError as e:
        err(str(e))
        raise typer.Exit(1)

    if not force and not typer.confirm(f"서버 {server_id}를 삭제하시겠습니까?"):
        return

    try:
        client.delete(f"/config/servers/{server_id}")
    except Exception as exc:
        err(f"삭제 실패: {exc}")
        raise typer.Exit(1)

    ok(f"서버 삭제 완료: {server_id}")
