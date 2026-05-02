"""Step 6 — assemble the LLM narrative + diagram from ranked fragments."""

from ..core import (
    Entity,
    RankedFragment,
    Relationship,
    RenderedView,
    TopologyHighlights,
    ViewRequest,
)
from ..llm.client import (
    AssemblyRequest,
    LLMClient,
    filter_citations,
)
from .lifting import FilteredFragment
from .topology import ViewportTopology


def _topology_summary(topology: ViewportTopology) -> str:
    if not topology.metrics:
        return "Empty viewport."
    lines = []
    if topology.most_central:
        lines.append(f"Most central: {topology.most_central}.")
    if topology.structural_concerns:
        lines.append(
            f"High-betweenness nodes: {', '.join(topology.structural_concerns)}."
        )
    return " ".join(lines) or "No structural concerns."


def assemble(
    *,
    llm: LLMClient,
    request: ViewRequest,
    entities: list[Entity],
    relationships: list[Relationship],
    ranked: list[FilteredFragment],
    topology: ViewportTopology,
    top_k: int = 10,
) -> RenderedView:
    """Run the assembly LLM call, post-validate citations, build the response."""
    selected = ranked[:top_k]
    payload = AssemblyRequest(
        request=request,
        entities=entities,
        relationships=relationships,
        fragments=[f.fragment for f in selected],
        topology_summary=_topology_summary(topology),
        structural_concerns=topology.structural_concerns,
        most_central=topology.most_central,
    )
    response = llm.assemble_view(payload)
    allowed_ids = {f.fragment.id for f in selected}
    cleaned_summary, _ = filter_citations(response.summary, allowed_ids)

    ranked_out = []
    for i, f in enumerate(selected):
        rf = RankedFragment(
            id=f.fragment.id,
            title=f.fragment.title,
            body=f.fragment.body,
            rank=i + 1,
            effective_zoom_min=f.effective_zoom_min,
            lifted=f.lifted,
            lenses=list(f.fragment.coverage.lenses),
            confidence=f.fragment.provenance.confidence,
            reviewed=f.fragment.provenance.reviewed,
            source_path=f.fragment.provenance.source_path,
        )
        ranked_out.append(rf)

    return RenderedView(
        summary=cleaned_summary,
        diagram=response.diagram,
        fragments=ranked_out,
        entities=entities,
        relationships=relationships,
        topology_highlights=TopologyHighlights(
            most_central=topology.most_central,
            structural_concerns=list(topology.structural_concerns),
        ),
        follow_up_suggestions=list(response.follow_up_suggestions),
    )
