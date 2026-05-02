"""ViewEngine — orchestrates the 6-step pipeline."""

from dataclasses import dataclass

from ..core import RenderedView, ViewRequest
from ..graph.repository import GraphRepository
from ..llm.client import LLMClient, build_default_client
from .assembly import assemble
from .fragments import collect_candidates
from .lifting import filter_and_lift
from .ranking import rank
from .subgraph import Viewport, extract_viewport
from .topology import ViewportTopology, compute_topology


@dataclass
class ViewportCap:
    max_entities: int = 800
    fallback_min_radius: int = 1


class ViewEngine:
    """Top-level orchestrator. Each step is a small pure function in its own module."""

    def __init__(
        self,
        repo: GraphRepository,
        llm: LLMClient | None = None,
        *,
        cap: ViewportCap | None = None,
    ) -> None:
        self.repo = repo
        self.llm = llm if llm is not None else build_default_client()
        self.cap = cap or ViewportCap()

    def render(self, request: ViewRequest, *, top_k: int = 10) -> RenderedView:
        """Run all 6 steps and return a RenderedView."""
        viewport = self._extract_viewport(request)
        topology = compute_topology(viewport, request.navigation_path)
        candidates = collect_candidates(self.repo, viewport)
        survivors = filter_and_lift(candidates, request, topology)
        ranked = rank(survivors, request)
        return assemble(
            llm=self.llm,
            request=request,
            entities=list(viewport.entities.values()),
            relationships=list(viewport.relationships.values()),
            ranked=ranked,
            topology=topology,
            top_k=top_k,
        )

    def _extract_viewport(self, request: ViewRequest) -> Viewport:
        """Run extract_viewport, falling back to smaller radii if capped."""
        radius = request.radius
        while True:
            viewport = extract_viewport(
                self.repo, request.model_copy(update={"radius": radius}), cap=self.cap.max_entities
            )
            if not viewport.capped or radius <= self.cap.fallback_min_radius:
                return viewport
            radius -= 1

    # --- Convenience hooks for tests ---------------------------------------

    def viewport_for(self, request: ViewRequest) -> Viewport:
        return self._extract_viewport(request)

    def topology_for(self, request: ViewRequest) -> ViewportTopology:
        return compute_topology(self._extract_viewport(request), request.navigation_path)
