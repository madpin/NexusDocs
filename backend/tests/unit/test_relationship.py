"""Tests for the Relationship model."""

import pytest
from pydantic import ValidationError

from nexusdocs.core import Mode, Protocol, Relationship, RelationshipType


def test_relationship_minimal() -> None:
    r = Relationship(
        id="rel.x",
        source="service.a",
        target="service.b",
        type=RelationshipType.calls_api,
        protocol=Protocol.rest,
        mode=Mode.sync,
    )
    assert r.protocol == Protocol.rest


def test_relationship_unknown_protocol_string_accepted() -> None:
    """Protocol is open-enum-ish; unknown strings are kept verbatim."""
    r = Relationship(
        id="rel.x",
        source="service.a",
        target="service.b",
        type=RelationshipType.calls_api,
        protocol="thrift",
    )
    assert r.protocol == "thrift"


def test_relationship_invalid_id() -> None:
    with pytest.raises(ValidationError):
        Relationship(
            id="BAD",
            source="service.a",
            target="service.b",
            type=RelationshipType.calls_api,
        )
