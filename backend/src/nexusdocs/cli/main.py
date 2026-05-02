"""nexdoc — top-level Typer entrypoint."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .commands import apply as apply_cmd
from .commands import ingest as ingest_cmd
from .commands import render as render_cmd
from .commands import search as search_cmd
from .commands import serve as serve_cmd

app = typer.Typer(
    name="nexdoc",
    help="Topology-aware knowledge graph documentation. https://docs.nexusdocs.example",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def _global_options(
    ctx: typer.Context,
    state: Annotated[
        Path | None,
        typer.Option(
            "--state",
            "-s",
            envvar="NEXUSDOCS_STATE_PATH",
            help=(
                "Path to a YAML file (or directory) used as the graph state. "
                "Reloaded at the start of every command for offline use. "
                "Set NEXUSDOCS_STATE_PATH to make this persistent across invocations."
            ),
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of pretty output."),
    ] = False,
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["state_path"] = state
    ctx.obj["json"] = json_output


app.command("apply", help="Apply a YAML file to the graph.")(apply_cmd.run)
app.command("render", help="Render a view.")(render_cmd.run)
app.command("search", help="Search the graph.")(search_cmd.run)
app.command("ingest", help="Trigger ingestion of a remote source.")(ingest_cmd.run)
app.command("serve", help="Run the HTTP API.")(serve_cmd.run)


if __name__ == "__main__":
    app()
