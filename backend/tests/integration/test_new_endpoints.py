"""Integration tests for the new ingest / settings / meta routes."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from nexusdocs.api import build_app
from nexusdocs.config import Settings
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.llm import DeterministicMockClient
from nexusdocs.yaml import apply_documents, load_documents


@pytest.fixture
def app(payments_yaml: Path):
    repo = InMemoryGraphRepository()
    repo.initialize()
    apply_documents(repo, load_documents(payments_yaml))
    settings = Settings()
    return build_app(
        repository=repo, llm=DeterministicMockClient(), settings=settings
    )


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ─── /api/v1/meta ────────────────────────────────────────────────────────


async def test_meta_returns_totals_and_metadata(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "NexusDocs"
    assert body["totals"]["entities"] > 0
    assert body["totals"]["relationships"] > 0
    assert body["totals"]["fragments"] > 0
    assert "team" in body["entities_by_kind"]
    assert "license" in body and "homepage" in body


# ─── /api/v1/settings ───────────────────────────────────────────────────


async def test_settings_get_redacts_api_key(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/settings")
    assert r.status_code == 200
    body = r.json()
    assert "openai_api_key" not in body  # never leaked verbatim
    assert "openai_api_key_set" in body
    assert "openai_base_url" in body
    assert body["llm_client"] == "DeterministicMockClient"


async def test_settings_patch_overrides_runtime_config(
    client: httpx.AsyncClient,
) -> None:
    r = await client.patch(
        "/api/v1/settings",
        json={
            "openai_base_url": "http://localhost:11434/v1",
            "openai_model": "llama3:70b",
            "openai_api_key": "sk-test-fake",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["openai_base_url"] == "http://localhost:11434/v1"
    assert body["openai_model"] == "llama3:70b"
    assert body["openai_api_key_set"] is True
    # The PATCH should rebuild the LLM client.
    assert body["llm_client"] in {"OpenAIClient", "DeterministicMockClient"}


async def test_settings_patch_clears_base_url(client: httpx.AsyncClient) -> None:
    await client.patch(
        "/api/v1/settings", json={"openai_base_url": "http://example.com"}
    )
    r = await client.patch("/api/v1/settings", json={"openai_base_url": ""})
    assert r.status_code == 200
    assert r.json()["openai_base_url"] is None


# ─── /api/v1/ingest/markdown ────────────────────────────────────────────


SAMPLE = """
# Payments Platform

The Payments Platform consists of payments-svc and ledger-db.

payments-svc owns the API. ledger-db stores journals.
"""


async def test_ingest_markdown_creates_parent_fragment(
    client: httpx.AsyncClient,
) -> None:
    r = await client.post(
        "/api/v1/ingest/markdown",
        json={"text": SAMPLE, "title": "Payments Platform"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] in {"succeeded", "failed"}
    assert body["documents_processed"] == 1
    assert body["fragments_created"] >= 1
    assert body["parent_fragment_id"]
    assert body["parent_fragment_id"].startswith("docfrag.doc-payments-platform-")

    # The parent fragment should be retrievable from the API.
    fid = body["parent_fragment_id"]
    r2 = await client.get(f"/api/v1/fragments/{fid}")
    assert r2.status_code == 200
    fragment = r2.json()
    assert fragment["title"] == "Payments Platform"
    assert "payments-svc" in fragment["body"]


async def test_ingest_markdown_rejects_empty(client: httpx.AsyncClient) -> None:
    r = await client.post("/api/v1/ingest/markdown", json={"text": ""})
    assert r.status_code == 422  # pydantic min_length=1


async def test_ingest_jobs_listing(client: httpx.AsyncClient) -> None:
    await client.post("/api/v1/ingest/markdown", json={"text": SAMPLE})
    r = await client.get("/api/v1/ingest")
    assert r.status_code == 200
    jobs = r.json()
    assert any(j["metadata"].get("source") == "markdown" for j in jobs)


# ─── Confluence / Jira (HTTP error handling without external network) ───


async def test_ingest_confluence_handles_unreachable(
    client: httpx.AsyncClient,
) -> None:
    # Use a port nothing listens on so httpx fails fast — we just want to
    # confirm the endpoint reports the error rather than crashes.
    r = await client.post(
        "/api/v1/ingest/confluence",
        json={
            "base_url": "http://127.0.0.1:1",
            "page_id": "1",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    errs = r.json()["errors"]
    assert any("confluence fetch failed" in e for e in errs)


async def test_ingest_jira_handles_unreachable(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/api/v1/ingest/jira",
        json={
            "base_url": "http://127.0.0.1:1",
            "issue_key": "ABC-1",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert any("jira fetch failed" in e for e in r.json()["errors"])
