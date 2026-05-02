"""Tests for the topology metrics."""

from nexusdocs.core import Entity, Kind, Relationship, RelationshipType, ViewRequest
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.view.subgraph import extract_viewport
from nexusdocs.view.topology import compute_topology


def _build_star() -> InMemoryGraphRepository:
    """`hub` connected to 4 leaves; `hub` should be most central."""
    repo = InMemoryGraphRepository()
    repo.initialize()
    repo.upsert_entity(Entity(id="service.hub", kind=Kind.service, name="Hub"))
    for i in range(4):
        leaf_id = f"service.leaf-{i}"
        repo.upsert_entity(Entity(id=leaf_id, kind=Kind.service, name=f"Leaf {i}"))
        repo.upsert_relationship(
            Relationship(
                id=f"rel.hub-leaf-{i}",
                source="service.hub",
                target=leaf_id,
                type=RelationshipType.calls_api,
            )
        )
    return repo


def test_hub_is_most_central() -> None:
    repo = _build_star()
    request = ViewRequest(focus="service.hub", zoom=50, radius=2)
    viewport = extract_viewport(repo, request)
    topology = compute_topology(viewport, navigation_path=[])
    assert topology.most_central == "service.hub"
    assert topology.metrics["service.hub"].degree_centrality > 0.5


def test_path_relevance_decays() -> None:
    repo = _build_star()
    request = ViewRequest(
        focus="service.hub",
        zoom=50,
        radius=2,
        navigation_path=["service.hub", "service.leaf-0"],
    )
    viewport = extract_viewport(repo, request)
    topology = compute_topology(viewport, request.navigation_path)
    assert topology.metrics["service.hub"].path_relevance == 1.0
    assert (
        topology.metrics["service.leaf-0"].path_relevance
        < topology.metrics["service.hub"].path_relevance
    )
    assert topology.metrics["service.leaf-1"].path_relevance == 0.0


def test_cluster_coverage_is_local() -> None:
    repo = _build_star()
    request = ViewRequest(focus="service.hub", zoom=50, radius=2)
    viewport = extract_viewport(repo, request)
    topology = compute_topology(viewport, [])
    # Hub reaches all 4 leaves in 1 hop. Coverage should be 4/4.
    assert topology.metrics["service.hub"].cluster_coverage == 1.0
    # A leaf reaches only the hub.
    assert topology.metrics["service.leaf-0"].cluster_coverage == 0.25
