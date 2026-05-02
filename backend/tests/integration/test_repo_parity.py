"""Memory ↔ Neo4j parity test.

Skipped unless `NEXUSDOCS_NEO4J_URI` is set. The test exercises the same
sequence of upserts/queries against both backends and asserts equality on
the visible state.
"""

import os
from pathlib import Path

import pytest

from nexusdocs.core import ViewRequest
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.llm import DeterministicMockClient
from nexusdocs.view import ViewEngine
from nexusdocs.yaml import apply_documents, load_documents

NEO4J_URI = os.getenv("NEXUSDOCS_NEO4J_URI")
NEO4J_USER = os.getenv("NEXUSDOCS_NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEXUSDOCS_NEO4J_PASSWORD", "neo4jneo4j")


pytestmark = pytest.mark.neo4j


@pytest.fixture
def neo4j_repo():
    if not NEO4J_URI:
        pytest.skip("NEXUSDOCS_NEO4J_URI is unset")
    from nexusdocs.graph.neo4j_repo import Neo4jGraphRepository

    repo = Neo4jGraphRepository(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASS)
    repo.initialize()
    # Wipe any leftovers from prior runs
    with repo.driver.session(database=repo.database) as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield repo
    with repo.driver.session(database=repo.database) as session:
        session.run("MATCH (n) DETACH DELETE n")
    repo.close()


def _ids(items):
    return sorted(i.id for i in items)


def test_apply_and_render_parity(payments_yaml: Path, neo4j_repo) -> None:
    docs = load_documents(payments_yaml)

    memory = InMemoryGraphRepository()
    memory.initialize()
    apply_documents(memory, docs)
    apply_documents(neo4j_repo, docs)

    assert _ids(memory.list_entities()) == _ids(neo4j_repo.list_entities())
    assert _ids(memory.list_relationships()) == _ids(neo4j_repo.list_relationships())
    assert _ids(memory.list_fragments()) == _ids(neo4j_repo.list_fragments())

    request = ViewRequest(
        focus="service.payments-api",
        zoom=65,
        lenses=["debug", "operations"],
        radius=2,
    )
    mem_view = ViewEngine(memory, llm=DeterministicMockClient()).render(request)
    neo_view = ViewEngine(neo4j_repo, llm=DeterministicMockClient()).render(request)
    assert sorted(f.id for f in mem_view.fragments) == sorted(
        f.id for f in neo_view.fragments
    )
    assert {e.id for e in mem_view.entities} == {e.id for e in neo_view.entities}
