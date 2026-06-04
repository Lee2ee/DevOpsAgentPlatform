"""
AI DevOps CLI 진입점.

Usage:
    aidevops server start
    aidevops server status
    aidevops scan <path>
    aidevops docker generate <project_id>
    aidevops docker save <project_id> -g <generation_id>
    aidevops cicd generate <project_id> --platform github_actions
    aidevops deploy <project_id> <server_id>
    aidevops deploy status <deployment_id>
    aidevops analyze <deployment_id>
    aidevops analyze patch <analysis_id>
    aidevops config ai
    aidevops config server-list
    aidevops config server-add
"""

import typer

from aidevops_cli.commands import (
    analyze_cmd,
    cicd_cmd,
    config_cmd,
    deploy_cmd,
    docker_cmd,
    scan,
    server,
)

app = typer.Typer(
    name="aidevops",
    help="AI DevOps Agent Platform CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(server.app, name="server")
app.add_typer(scan.app, name="scan")
app.add_typer(docker_cmd.app, name="docker")
app.add_typer(cicd_cmd.app, name="cicd")
app.add_typer(deploy_cmd.app, name="deploy")
app.add_typer(analyze_cmd.app, name="analyze")
app.add_typer(config_cmd.app, name="config")


if __name__ == "__main__":
    app()
