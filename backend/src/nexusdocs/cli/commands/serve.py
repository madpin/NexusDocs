"""nexdoc serve — run the FastAPI app."""

from pathlib import Path
from typing import Annotated

import typer

from ...api import build_app
from ...config import get_settings


def run(
    ctx: typer.Context,
    host: Annotated[str, typer.Option("--host")] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port")] = 8080,
    seed: Annotated[
        Path | None,
        typer.Option("--seed", help="YAML file or directory to seed the in-memory repo."),
    ] = None,
) -> None:
    import uvicorn

    state_path = seed or ctx.obj.get("state_path")
    repository = None
    if state_path:
        from ._shared import repo_from_state

        repository = repo_from_state(state_path)

    settings = get_settings()
    app = build_app(repository=repository, settings=settings)
    uvicorn.run(app, host=host, port=port)
