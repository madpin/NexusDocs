"""nexdoc ingest — trigger an ingestion job."""

from typing import Annotated

import typer
from rich.table import Table

from ...orchestrator import ingest_repository
from ._shared import console, emit, repo_from_state


def run(
    ctx: typer.Context,
    repo_url: Annotated[str, typer.Argument(help="Git repository URL.")],
    branch: Annotated[str, typer.Option("--branch")] = "main",
) -> None:
    repo = repo_from_state(ctx.obj.get("state_path"))
    result = ingest_repository(repo, repo_url=repo_url, branch=branch)

    def pretty(data: dict) -> None:
        table = Table(title="Ingestion job")
        table.add_column("Field")
        table.add_column("Value")
        for k, v in data.items():
            table.add_row(str(k), str(v))
        console.print(table)

    emit(ctx, result, table_renderer=pretty)
