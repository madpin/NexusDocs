"""Shared CLI helpers — repository loading, json/pretty output."""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from ...graph import InMemoryGraphRepository
from ...graph.repository import GraphRepository
from ...orchestrator import apply_yaml

console = Console()


def repo_from_state(state_path: Path | None) -> GraphRepository:
    """Build an in-memory repo and seed it from `state_path` if provided."""
    repo = InMemoryGraphRepository()
    repo.initialize()
    if state_path is None:
        return repo
    if state_path.is_dir():
        for yaml_file in sorted(state_path.glob("*.yaml")):
            apply_yaml(repo, yaml_file)
        for yaml_file in sorted(state_path.glob("*.yml")):
            apply_yaml(repo, yaml_file)
    elif state_path.is_file():
        apply_yaml(repo, state_path)
    else:
        raise typer.BadParameter(f"state path does not exist: {state_path}")
    return repo


def emit(ctx: typer.Context, data: Any, *, table_renderer=None) -> None:
    """Emit a result as JSON if --json was passed, else use the table_renderer."""
    if ctx.obj.get("json") or table_renderer is None:
        console.print_json(data=data, default=str)
    else:
        table_renderer(data)
