"""Tests for the YAML envelope loader."""

from pathlib import Path

import pytest

from nexusdocs.yaml import LoadError, load_documents
from nexusdocs.yaml.envelope import EnvelopeError, parse_envelope


def test_envelope_basic() -> None:
    kind, model = parse_envelope(
        {
            "apiVersion": "nexusdocs/v1",
            "kind": "Entity",
            "spec": {"id": "team.x", "type": "team", "name": "X"},
        }
    )
    assert kind.value == "Entity"
    assert model.id == "team.x"


def test_envelope_unknown_kind() -> None:
    with pytest.raises(EnvelopeError):
        parse_envelope(
            {"apiVersion": "nexusdocs/v1", "kind": "NotAThing", "spec": {}}
        )


def test_envelope_unknown_api_version() -> None:
    with pytest.raises(EnvelopeError):
        parse_envelope({"apiVersion": "wrong", "kind": "Entity", "spec": {}})


def test_load_payments_fixture(payments_yaml: Path) -> None:
    docs = load_documents(payments_yaml)
    # Sanity counts from the sample graph.
    assert len(docs.entities) >= 14
    assert len(docs.relationships) >= 12
    assert len(docs.fragments) >= 4
    assert len(docs.presets) >= 1
    ids = {e.id for e in docs.entities}
    assert "team.payments" in ids
    assert "service.payments-api" in ids
    assert "kafka_cluster.core-kafka-prod" in ids


def test_load_string_yaml() -> None:
    text = (
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: team.x\n"
        "  type: team\n"
        "  name: X\n"
    )
    docs = load_documents(text)
    assert len(docs.entities) == 1


def test_load_collects_errors() -> None:
    bad = (
        "apiVersion: nexusdocs/v1\n"
        "kind: Entity\n"
        "spec:\n"
        "  id: BAD\n"
        "  type: team\n"
        "  name: X\n"
    )
    with pytest.raises(LoadError):
        load_documents(bad)


def test_load_long_multiline_yaml_is_not_treated_as_path(payments_yaml: Path) -> None:
    """Regression: passing a long, multi-line YAML string used to OSError when
    the loader probed it as a Path (`File name too long`)."""
    text = payments_yaml.read_text(encoding="utf-8")
    docs = load_documents(text)
    assert len(docs.entities) >= 14
