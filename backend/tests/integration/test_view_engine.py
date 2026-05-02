"""End-to-end view engine tests against the payments fixture.

Mirrors the three user-flow scenarios from docs/examples/README.md.
"""

from nexusdocs.core import ViewRequest
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.llm import DeterministicMockClient
from nexusdocs.view import ViewEngine


def _engine(repo: InMemoryGraphRepository) -> ViewEngine:
    return ViewEngine(repo, llm=DeterministicMockClient())


def test_director_view(payments_repo: InMemoryGraphRepository) -> None:
    """Zoom 15 + product/onboarding lenses → team-overview fragment surfaces."""
    engine = _engine(payments_repo)
    request = ViewRequest(
        focus="team.payments",
        zoom=15,
        lenses=["product", "onboarding"],
        radius=2,
    )
    view = engine.render(request)
    fragment_ids = {f.id for f in view.fragments}
    assert "docfrag.payments-team-overview" in fragment_ids


def test_debug_view(payments_repo: InMemoryGraphRepository) -> None:
    """Zoom 65 + debug → failure-mode fragment is the top result."""
    engine = _engine(payments_repo)
    request = ViewRequest(
        focus="service.payments-api",
        zoom=65,
        lenses=["debug", "operations"],
        radius=2,
    )
    view = engine.render(request)
    fragment_ids = [f.id for f in view.fragments]
    assert "docfrag.payments-auth-failure-mode" in fragment_ids


def test_kafka_throughput_lifts_via_cluster_coverage(
    payments_repo: InMemoryGraphRepository,
) -> None:
    """The throughput-ceiling fragment lifts down when cluster_coverage > 0.5."""
    engine = _engine(payments_repo)
    request = ViewRequest(
        focus="kafka_cluster.core-kafka-prod",
        zoom=40,
        lenses=["technical", "operations"],
        radius=2,
    )
    view = engine.render(request)
    fragment_ids = {f.id for f in view.fragments}
    assert "docfrag.kafka-throughput-ceiling" in fragment_ids
    lifted = next(f for f in view.fragments if f.id == "docfrag.kafka-throughput-ceiling")
    assert lifted.lifted is True
    assert lifted.effective_zoom_min < 50


def test_unrelated_focus_yields_smaller_viewport(
    payments_repo: InMemoryGraphRepository,
) -> None:
    """A small radius keeps a Person view tightly scoped."""
    engine = _engine(payments_repo)
    request = ViewRequest(
        focus="person.tpinto",
        zoom=10,
        lenses=["product", "onboarding"],
        radius=1,
    )
    view = engine.render(request)
    assert "person.tpinto" in {e.id for e in view.entities}


def test_topology_highlights_populated(payments_repo: InMemoryGraphRepository) -> None:
    engine = _engine(payments_repo)
    request = ViewRequest(
        focus="service.payments-api",
        zoom=65,
        lenses=["technical"],
        radius=2,
    )
    view = engine.render(request)
    assert view.topology_highlights.most_central is not None


def test_diagram_has_mermaid_header(payments_repo: InMemoryGraphRepository) -> None:
    engine = _engine(payments_repo)
    request = ViewRequest(
        focus="service.payments-api",
        zoom=65,
        lenses=["technical"],
        radius=2,
    )
    view = engine.render(request)
    assert view.diagram.startswith("graph LR")
