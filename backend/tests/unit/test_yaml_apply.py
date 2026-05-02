"""Tests for ordered transactional YAML apply."""

from pathlib import Path

import pytest

from nexusdocs.core import Entity, Kind, Relationship, RelationshipType
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.yaml import apply_documents, load_documents


def test_apply_payments_fixture(payments_yaml: Path) -> None:
    repo = InMemoryGraphRepository()
    repo.initialize()
    docs = load_documents(payments_yaml)
    result = apply_documents(repo, docs)
    assert result.ok(), result.errors

    # Spot-check specific entries
    assert repo.has_entity("team.payments")
    assert repo.has_entity("service.payments-api")
    assert repo.has_relationship("rel.payments-api-calls-auth")
    assert repo.has_fragment("docfrag.payments-team-overview")
    presets = repo.list_presets()
    assert any(p.id == "preset.payments-oncall-debug" for p in presets)

    # Counts should match what was loaded
    assert len(repo.list_entities()) == len(docs.entities)
    assert len(repo.list_relationships()) == len(docs.relationships)
    assert len(repo.list_fragments()) == len(docs.fragments)


def test_apply_topo_sorts_entities() -> None:
    """Children may appear before parents in YAML order — apply must reorder."""
    repo = InMemoryGraphRepository()
    repo.initialize()
    text = (
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: team.payments\n"
        "  type: team\n"
        "  name: Payments\n"
        "  parent: division.fintech\n"
        "---\n"
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: division.fintech\n"
        "  type: division\n"
        "  name: Fintech\n"
        "  parent: company.acme\n"
        "---\n"
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: company.acme\n"
        "  type: company\n"
        "  name: Acme\n"
    )
    result = apply_documents(repo, text)
    assert result.ok(), result.errors
    assert repo.has_entity("team.payments")


def test_apply_rolls_back_on_invalid_relationship() -> None:
    repo = InMemoryGraphRepository()
    repo.initialize()

    # Pre-seed valid entity, then attempt to apply a batch with a bad rel.
    repo.upsert_entity(Entity(id="service.a", kind=Kind.service, name="A"))

    text = (
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: service.b\n"
        "  type: service\n"
        "  name: B\n"
        "---\n"
        "apiVersion: nexusdocs/v1\n"
        "kind: Relationship\n"
        "spec:\n"
        "  id: rel.bad\n"
        "  source: service.b\n"
        "  target: service.does-not-exist\n"
        "  type: calls_api\n"
        "  protocol: rest\n"
    )

    result = apply_documents(repo, text)
    assert not result.ok()
    # rollback: service.b should NOT have been persisted
    assert not repo.has_entity("service.b")


def test_apply_kind_parent_validation() -> None:
    repo = InMemoryGraphRepository()
    repo.initialize()
    # team cannot have system as parent
    repo.upsert_entity(Entity(id="system.x", kind=Kind.system, name="X"))
    with pytest.raises(Exception):
        repo.upsert_entity(
            Entity(id="team.bad", kind=Kind.team, name="Bad", parent="system.x")
        )


def test_relationship_requires_existing_endpoints(empty_repo: InMemoryGraphRepository) -> None:
    with pytest.raises(Exception):
        empty_repo.upsert_relationship(
            Relationship(
                id="rel.x",
                source="service.missing",
                target="service.also-missing",
                type=RelationshipType.calls_api,
            )
        )
