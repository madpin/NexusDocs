"""HTTP API integration tests against the in-memory repo."""

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


async def test_healthz(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_get_entity(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/entities/team.payments")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "team.payments"
    assert body["kind"] == "team"


async def test_get_entity_404(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/entities/team.does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["error"]["code"] == "not_found"


async def test_create_entity(client: httpx.AsyncClient) -> None:
    payload = {"id": "team.platform", "kind": "team", "name": "Platform"}
    r = await client.post("/api/v1/entities", json=payload)
    assert r.status_code == 201, r.text
    assert r.json()["id"] == "team.platform"


async def test_get_edges(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/entities/service.payments-api/edges")
    assert r.status_code == 200
    body = r.json()
    assert "outgoing" in body
    assert "incoming" in body
    rel_ids = {r["id"] for r in body["outgoing"] + body["incoming"]}
    assert "rel.payments-api-calls-auth" in rel_ids


async def test_get_fragments_for_entity(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/entities/team.payments/fragments")
    assert r.status_code == 200
    fids = {f["id"] for f in r.json()}
    assert "docfrag.payments-team-overview" in fids


async def test_render_view(client: httpx.AsyncClient) -> None:
    body = {
        "focus": "service.payments-api",
        "zoom": 65,
        "lenses": ["debug", "operations"],
        "radius": 2,
    }
    r = await client.post("/api/v1/views/render", json=body)
    assert r.status_code == 200, r.text
    rv = r.json()
    assert rv["summary"]
    assert rv["diagram"].startswith("graph LR")
    assert rv["topology_highlights"]["most_central"] is not None
    fids = {f["id"] for f in rv["fragments"]}
    assert "docfrag.payments-auth-failure-mode" in fids


async def test_search(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/v1/search", json={"query": "kafka", "scope": "all"}
    )
    assert r.status_code == 200
    hits = r.json()["hits"]
    assert any(h["kind"] == "entity" and "kafka" in h["id"] for h in hits)


async def test_view_preset_crud(client: httpx.AsyncClient) -> None:
    payload = {
        "id": "preset.test",
        "name": "Test",
        "owner": "person.tpinto",
        "focus": "service.payments-api",
        "zoom": 50,
        "lenses": ["technical"],
        "radius": 2,
    }
    r = await client.post("/api/v1/views/presets", json=payload)
    assert r.status_code == 201, r.text
    r = await client.get("/api/v1/views/presets/preset.test")
    assert r.status_code == 200
    r = await client.delete("/api/v1/views/presets/preset.test")
    assert r.status_code == 204


async def test_apply_yaml_text(client: httpx.AsyncClient) -> None:
    yaml_text = (
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: service.new-thing\n"
        "  type: service\n"
        "  name: NewThing\n"
    )
    r = await client.post(
        "/api/v1/definitions/apply",
        content=yaml_text.encode(),
        headers={"content-type": "application/yaml"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert any(a["id"] == "service.new-thing" for a in body["applied"])


async def test_render_returns_404_for_missing_focus(client: httpx.AsyncClient) -> None:
    body = {"focus": "service.does-not-exist", "zoom": 50, "lenses": ["technical"]}
    r = await client.post("/api/v1/views/render", json=body)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


async def test_validation_error_envelope(client: httpx.AsyncClient) -> None:
    """Pydantic validation errors should still be returned with details."""
    r = await client.post("/api/v1/entities", json={"id": "BAD", "kind": "team", "name": "x"})
    assert r.status_code == 422
