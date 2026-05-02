"""Step 2 — viewport-scoped topology metrics."""

from dataclasses import dataclass, field

import networkx as nx

from .subgraph import Viewport


@dataclass(frozen=True)
class EntityMetrics:
    entity_id: str
    degree_centrality: float
    betweenness_centrality: float
    cluster_coverage: float
    path_relevance: float

    def above_centrality(self, threshold: float) -> bool:
        return self.degree_centrality >= threshold

    def above_cluster_coverage(self, threshold: float) -> bool:
        return self.cluster_coverage >= threshold


@dataclass
class ViewportTopology:
    metrics: dict[str, EntityMetrics] = field(default_factory=dict)
    most_central: str | None = None
    structural_concerns: list[str] = field(default_factory=list)

    def for_entities(self, ids: list[str]) -> list[EntityMetrics]:
        return [self.metrics[i] for i in ids if i in self.metrics]


def _path_relevance(entity_id: str, navigation_path: list[str]) -> float:
    """1.0 if focus, decayed by recency (closer to head => more recent)."""
    if not navigation_path:
        return 0.0
    try:
        idx = navigation_path.index(entity_id)
    except ValueError:
        return 0.0
    return max(0.0, 1.0 - 0.2 * idx)


def compute_topology(
    viewport: Viewport, navigation_path: list[str]
) -> ViewportTopology:
    """Compute the four topology metrics for every node in the viewport.

    Topology is computed on the *unfiltered* BFS scope so that metrics like
    cluster_coverage and betweenness reflect the underlying graph density,
    not just whatever survives the current zoom filter. Without this, a
    zoomed-out user would see lift_on rules turn off as soon as their
    surrounding nodes got hidden by the depth-aware filter.
    """
    scope_entities = viewport.topology_entities
    scope_relationships = viewport.topology_relationships
    if not scope_entities:
        return ViewportTopology()

    g = nx.DiGraph()
    for eid in scope_entities:
        g.add_node(eid)
    for rel in scope_relationships.values():
        g.add_edge(rel.source, rel.target, key=rel.id)

    n = g.number_of_nodes()
    if n <= 1:
        deg_central: dict[str, float] = {eid: 0.0 for eid in g.nodes}
    else:
        deg_central = {eid: g.degree(eid) / (n - 1) for eid in g.nodes}

    if n <= 2:
        betweenness: dict[str, float] = {eid: 0.0 for eid in g.nodes}
    else:
        betweenness = nx.betweenness_centrality(g, normalized=True, endpoints=False)

    # cluster_coverage = fraction of scope reachable in 1 hop (either direction)
    cluster_coverage: dict[str, float] = {}
    denom = max(1, n - 1)
    for eid in g.nodes:
        successors = set(g.successors(eid))
        predecessors = set(g.predecessors(eid))
        reachable = (successors | predecessors) - {eid}
        cluster_coverage[eid] = len(reachable) / denom

    metrics: dict[str, EntityMetrics] = {}
    for eid in scope_entities:
        metrics[eid] = EntityMetrics(
            entity_id=eid,
            degree_centrality=deg_central.get(eid, 0.0),
            betweenness_centrality=betweenness.get(eid, 0.0),
            cluster_coverage=cluster_coverage.get(eid, 0.0),
            path_relevance=_path_relevance(eid, navigation_path),
        )

    most_central = max(metrics.values(), key=lambda m: m.degree_centrality, default=None)
    structural_concerns: list[str] = []
    for m in metrics.values():
        if m.betweenness_centrality > 0.4:
            structural_concerns.append(m.entity_id)

    return ViewportTopology(
        metrics=metrics,
        most_central=most_central.entity_id if most_central else None,
        structural_concerns=structural_concerns,
    )
