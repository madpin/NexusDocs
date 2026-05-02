"""End-to-end user-flow scenarios from docs/examples/README.md.

Each scenario exercises the public HTTP API against the in-process ASGI app
loaded with the canonical payments fixture. These are the M10 milestone tests:
they capture the three lived workflows that NexusDocs claims to enable, and
make sure they actually work end-to-end through the same surface a real client
would touch.

Run:

    pytest tests/integration/test_user_flows.py -v

The tests use `httpx.ASGITransport`, so no external services are required —
the same fixtures back the docker-compose seed.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from nexusdocs.api import build_app
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.llm import DeterministicMockClient
from nexusdocs.yaml import apply_documents, load_documents


@pytest.fixture
def app(payments_yaml: Path):
    repo = InMemoryGraphRepository()
    repo.initialize()
    apply_documents(repo, load_documents(payments_yaml))
    return build_app(repository=repo, llm=DeterministicMockClient())


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Scenario 1 — Director / onboarding view (zoom 15)
# ---------------------------------------------------------------------------


async def test_director_view_surfaces_team_overview(client: httpx.AsyncClient) -> None:
    """A director focusing on team.payments at low zoom sees the team overview.

    Maps to docs/examples/director-view.md.
    """
    body = {
        "focus": "team.payments",
        "zoom": 15,
        "lenses": ["product", "onboarding"],
        "radius": 2,
    }
    r = await client.post("/api/v1/views/render", json=body)
    assert r.status_code == 200, r.text
    rv = r.json()

    fragment_ids = {f["id"] for f in rv["fragments"]}
    assert "docfrag.payments-team-overview" in fragment_ids, (
        f"expected the team-overview fragment at zoom 15; got {fragment_ids}"
    )

    overview = next(
        f for f in rv["fragments"] if f["id"] == "docfrag.payments-team-overview"
    )
    assert overview["reviewed"] is True
    assert overview["confidence"] == 1.0

    # Director-grade view should not surface deep-debug fragments.
    assert "docfrag.payments-auth-failure-mode" not in fragment_ids

    # The narrative summary must be non-empty and the diagram must be Mermaid.
    assert rv["summary"].strip(), "summary should not be empty"
    assert rv["diagram"].startswith("graph LR")


# ---------------------------------------------------------------------------
# Scenario 2 — Debug view (zoom 65, debug + operations lenses)
# ---------------------------------------------------------------------------


async def test_debug_view_surfaces_failure_modes(client: httpx.AsyncClient) -> None:
    """An on-call engineer at zoom 65 sees the rate-limit / failure-mode fragment.

    Maps to docs/examples/debug-view.md.
    """
    body = {
        "focus": "service.payments-api",
        "zoom": 65,
        "lenses": ["debug", "operations"],
        "radius": 2,
    }
    r = await client.post("/api/v1/views/render", json=body)
    assert r.status_code == 200, r.text
    rv = r.json()

    fragment_ids = [f["id"] for f in rv["fragments"]]
    assert "docfrag.payments-auth-failure-mode" in fragment_ids, (
        f"expected the failure-mode fragment at zoom 65; got {fragment_ids}"
    )

    # The failure-mode fragment should rank above any product/onboarding ones.
    failure_idx = fragment_ids.index("docfrag.payments-auth-failure-mode")
    product_only = [
        i
        for i, fid in enumerate(fragment_ids)
        if fid == "docfrag.payments-team-overview"
    ]
    assert all(failure_idx < i for i in product_only), (
        "operational fragments should outrank product fragments in a debug view"
    )

    assert rv["topology_highlights"]["most_central"] is not None


# ---------------------------------------------------------------------------
# Scenario 3 — Kafka throughput lifts via cluster_coverage > 0.5
# ---------------------------------------------------------------------------


async def test_kafka_throughput_fragment_lifts_in_view(
    client: httpx.AsyncClient,
) -> None:
    """The throughput-ceiling fragment is normally `zoom_min: 50`, but lifts down
    when the focus's cluster_coverage exceeds 0.5 — i.e. when the user is
    looking *at* the Kafka cluster the fragment is anchored to.

    Maps to docs/examples/kafka-throughput.md.
    """
    body = {
        "focus": "kafka_cluster.core-kafka-prod",
        "zoom": 40,
        "lenses": ["technical", "operations"],
        "radius": 2,
    }
    r = await client.post("/api/v1/views/render", json=body)
    assert r.status_code == 200, r.text
    rv = r.json()

    matches = [
        f for f in rv["fragments"] if f["id"] == "docfrag.kafka-throughput-ceiling"
    ]
    assert matches, (
        "kafka-throughput-ceiling should appear at zoom 40 because cluster_coverage "
        "of the focus exceeds 0.5"
    )
    fragment = matches[0]
    assert fragment["lifted"] is True
    assert fragment["effective_zoom_min"] < 50, (
        "the fragment must have been lifted (effective_zoom_min < zoom_min=50)"
    )


# ---------------------------------------------------------------------------
# Cross-flow assertions that protect future regressions
# ---------------------------------------------------------------------------


async def test_changing_zoom_changes_fragments(client: httpx.AsyncClient) -> None:
    """Same focus + lenses, two zooms — the fragment list should differ."""
    base = {
        "focus": "team.payments",
        "lenses": ["product", "onboarding", "technical", "debug"],
        "radius": 3,
    }
    r1 = await client.post("/api/v1/views/render", json={**base, "zoom": 15})
    r2 = await client.post("/api/v1/views/render", json={**base, "zoom": 75})
    assert r1.status_code == 200 and r2.status_code == 200

    low_ids = {f["id"] for f in r1.json()["fragments"]}
    high_ids = {f["id"] for f in r2.json()["fragments"]}
    assert low_ids != high_ids, (
        "zoom must change which fragments are surfaced — got identical sets"
    )


async def test_navigation_path_lifts_path_matched_fragments(
    client: httpx.AsyncClient,
) -> None:
    """Path-match lifting is first-class: a fragment anchored to an entity that
    appears in the navigation_path lifts down by `lift_by`.

    The team-overview fragment has zoom_min=15, lift_by=5, lift_on.path_match=true.
    At zoom 10 it is normally below the window; placing team.payments on the
    navigation path should pull it back into scope (effective_zoom_min=10).
    """
    base_request = {
        "focus": "team.payments",
        "zoom": 10,
        "lenses": ["product", "onboarding"],
        "radius": 1,
    }

    no_path = await client.post("/api/v1/views/render", json=base_request)
    with_path = await client.post(
        "/api/v1/views/render",
        json={**base_request, "navigation_path": ["team.payments"]},
    )
    assert no_path.status_code == 200 and with_path.status_code == 200

    no_path_ids = {f["id"] for f in no_path.json()["fragments"]}
    with_path_ids = {f["id"] for f in with_path.json()["fragments"]}

    assert "docfrag.payments-team-overview" not in no_path_ids, (
        "team-overview should not surface at zoom 10 without lifting"
    )
    assert "docfrag.payments-team-overview" in with_path_ids, (
        "team-overview should be lifted into view when its subject is on the "
        f"navigation path; got with_path_ids={with_path_ids}"
    )

    lifted = next(
        f
        for f in with_path.json()["fragments"]
        if f["id"] == "docfrag.payments-team-overview"
    )
    assert lifted["lifted"] is True
    assert lifted["effective_zoom_min"] <= 10


async def test_search_finds_kafka_topic_and_throughput_fragment(
    client: httpx.AsyncClient,
) -> None:
    """Search across all scopes returns both entities and fragments."""
    r = await client.post(
        "/api/v1/search", json={"query": "kafka throughput", "scope": "all"}
    )
    assert r.status_code == 200, r.text
    hits = r.json()["hits"]
    kinds = {h["kind"] for h in hits}
    assert "fragment" in kinds or "entity" in kinds, (
        f"expected at least one entity or fragment hit, got {hits}"
    )


async def test_view_preset_round_trip_runs_director_view(
    client: httpx.AsyncClient,
) -> None:
    """Saved presets should reproduce the same fragment set when re-applied.

    This validates the preset → view-engine contract that makes director-style
    bookmarks reproducible across the team.
    """
    preset = {
        "id": "preset.team-overview",
        "name": "Director: Team Payments overview",
        "owner": "person.tpinto",
        "focus": "team.payments",
        "zoom": 15,
        "lenses": ["product", "onboarding"],
        "radius": 2,
    }
    create = await client.post("/api/v1/views/presets", json=preset)
    assert create.status_code == 201, create.text

    fetched = await client.get(f"/api/v1/views/presets/{preset['id']}")
    assert fetched.status_code == 200
    p = fetched.json()

    rendered = await client.post(
        "/api/v1/views/render",
        json={
            "focus": p["focus"],
            "zoom": p["zoom"],
            "lenses": p["lenses"],
            "radius": p["radius"],
        },
    )
    assert rendered.status_code == 200
    fragment_ids = {f["id"] for f in rendered.json()["fragments"]}
    assert "docfrag.payments-team-overview" in fragment_ids
