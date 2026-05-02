"""Render a view through the engine."""

from ..core import RenderedView, ViewRequest
from ..graph.repository import GraphRepository
from ..llm.client import LLMClient
from ..view import ViewEngine


def render_view(
    repo: GraphRepository,
    request: ViewRequest,
    *,
    llm: LLMClient | None = None,
    top_k: int = 10,
) -> RenderedView:
    engine = ViewEngine(repo, llm=llm)
    return engine.render(request, top_k=top_k)
