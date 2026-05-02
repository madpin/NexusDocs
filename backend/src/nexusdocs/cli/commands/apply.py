"""nexdoc apply — load a YAML file into the graph."""

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from ...orchestrator import apply_yaml
from ._shared import console, emit, repo_from_state


def run(
    ctx: typer.Context,
    path: Annotated[Path, typer.Argument(help="Path to a YAML file or directory.")],
) -> None:
    repo = repo_from_state(ctx.obj.get("state_path"))
    if path.is_dir():
        files = sorted([*path.glob("*.yaml"), *path.glob("*.yml")])
    elif path.is_file():
        files = [path]
    else:
        raise typer.BadParameter(f"no such file or directory: {path}")

    applied: list[dict] = []
    errors: list[str] = []
    for f in files:
        result = apply_yaml(repo, f)
        applied.extend(
            {"file": str(f), "kind": a.kind, "id": a.id, "action": a.action}
            for a in result.applied
        )
        errors.extend(f"{f}: {e}" for e in result.errors)

    payload = {"applied": applied, "errors": errors}

    def render_table(data: dict) -> None:
        table = Table(title="Applied")
        table.add_column("Kind")
        table.add_column("ID")
        table.add_column("Action")
        for entry in data["applied"]:
            table.add_row(entry["kind"], entry["id"], entry["action"])
        console.print(table)
        if data["errors"]:
            console.print("[red]Errors:[/red]")
            for e in data["errors"]:
                console.print(f"  {e}")

    emit(ctx, payload, table_renderer=render_table)

    if errors:
        raise typer.Exit(code=1)
