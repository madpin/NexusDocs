"""nexdoc render — render a view."""

from typing import Annotated

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ...core import ViewRequest
from ...core.view_preset import FilterSet
from ...llm import build_default_client
from ...orchestrator import render_view
from ...view.subgraph import FocusNotFoundError
from ._shared import console, emit, repo_from_state


def run(
    ctx: typer.Context,
    focus: Annotated[str, typer.Argument(help="Focus entity ID.")],
    zoom: Annotated[int, typer.Option("--zoom", "-z", min=0, max=100)] = 50,
    lens: Annotated[list[str] | None, typer.Option("--lens", "-l", help="Lens (repeatable).")] = None,
    radius: Annotated[int, typer.Option("--radius", "-r", min=0)] = 2,
    top_k: Annotated[int, typer.Option("--top-k", "-k", min=1)] = 10,
    protocol: Annotated[list[str] | None, typer.Option("--protocol")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
) -> None:
    state_path = ctx.obj.get("state_path")
    repo = repo_from_state(state_path)
    request = ViewRequest(
        focus=focus,
        zoom=zoom,
        lenses=list(lens) if lens else ["technical"],
        radius=radius,
        filters=FilterSet(
            protocols=list(protocol or []),
            tags=list(tag or []),
        ),
    )
    try:
        view = render_view(repo, request, llm=build_default_client(), top_k=top_k)
    except FocusNotFoundError as e:
        console.print(f"[red]error:[/red] focus entity {e} not found")
        raise typer.Exit(code=1)

    payload = view.model_dump(mode="json")

    def pretty(data: dict) -> None:
        console.print(Panel.fit(Markdown(data["summary"]), title="Summary"))
        console.print(
            Panel.fit(
                data["diagram"],
                title="Diagram (Mermaid)",
                border_style="dim",
            )
        )
        if data["fragments"]:
            table = Table(title="Fragments")
            table.add_column("Rank", justify="right")
            table.add_column("ID")
            table.add_column("Title")
            table.add_column("Lifted", justify="center")
            table.add_column("Conf", justify="right")
            table.add_column("Reviewed", justify="center")
            for f in data["fragments"]:
                table.add_row(
                    str(f["rank"]),
                    f["id"],
                    f["title"],
                    "✓" if f["lifted"] else "",
                    f"{f['confidence']:.2f}",
                    "✓" if f["reviewed"] else "",
                )
            console.print(table)
        highlights = data["topology_highlights"]
        if highlights["most_central"]:
            console.print(f"[bold]Most central:[/bold] {highlights['most_central']}")
        if highlights["structural_concerns"]:
            console.print(
                "[bold]Structural concerns:[/bold] "
                + ", ".join(highlights["structural_concerns"])
            )
        for s in data.get("follow_up_suggestions", []):
            console.print(f"[dim]→[/dim] {s}")

    emit(ctx, payload, table_renderer=pretty)
