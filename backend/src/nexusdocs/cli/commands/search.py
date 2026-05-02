"""nexdoc search — search the graph."""

from typing import Annotated

import typer
from rich.table import Table

from ...orchestrator import search_graph
from ...search import SearchScope
from ._shared import console, emit, repo_from_state


def run(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Free-text query.")],
    scope: Annotated[SearchScope, typer.Option("--scope")] = SearchScope.all,
    limit: Annotated[int, typer.Option("--limit", min=1)] = 25,
) -> None:
    repo = repo_from_state(ctx.obj.get("state_path"))
    hits = search_graph(repo, query, scope=scope, limit=limit)
    payload = {"hits": [h.model_dump(mode="json") for h in hits]}

    def pretty(data: dict) -> None:
        table = Table(title=f"Search: '{query}' ({scope.value})")
        table.add_column("Kind")
        table.add_column("ID")
        table.add_column("Score", justify="right")
        table.add_column("Snippet")
        for h in data["hits"]:
            table.add_row(
                h["kind"], h["id"], f"{h['score']:.2f}", h.get("snippet") or ""
            )
        console.print(table)

    emit(ctx, payload, table_renderer=pretty)
