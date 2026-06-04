"""
Rich 콘솔 공통 유틸리티.
"""

from rich.console import Console
from rich.theme import Theme

console = Console(theme=Theme({
    "success": "bold green",
    "error": "bold red",
    "warn": "bold yellow",
    "info": "cyan",
    "muted": "dim",
}))


def ok(msg: str) -> None:
    console.print(f"[success]OK[/success] {msg}")


def err(msg: str) -> None:
    console.print(f"[error]ERR[/error] {msg}")


def warn(msg: str) -> None:
    console.print(f"[warn]WARN[/warn] {msg}")


def info(msg: str) -> None:
    console.print(f"[info]--[/info] {msg}")
