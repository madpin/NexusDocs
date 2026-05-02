"""Tests for the Entity model."""

import pytest
from pydantic import ValidationError

from nexusdocs.core import Entity, Kind


def test_entity_minimal() -> None:
    e = Entity(id="team.payments", kind=Kind.team, name="Payments")
    assert e.id == "team.payments"
    assert e.kind is Kind.team


def test_entity_class_kind_uses_string_value() -> None:
    """`class` is a Python keyword, so the enum member name is `cls` but value is "class"."""
    e = Entity(id="class.jwt-signer", kind=Kind("class"), name="JwtSigner")
    assert e.kind.value == "class"


def test_entity_rejects_invalid_id() -> None:
    with pytest.raises(ValidationError):
        Entity(id="Bad-ID", kind=Kind.team, name="x")


def test_entity_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Entity.model_validate(
            {
                "id": "team.x",
                "kind": "team",
                "name": "X",
                "wrong_field": True,
            }
        )


def test_entity_unique_labels() -> None:
    with pytest.raises(ValidationError):
        Entity(id="team.x", kind=Kind.team, name="X", labels=["a", "a"])


def test_entity_blank_name_rejected() -> None:
    with pytest.raises(ValidationError):
        Entity(id="team.x", kind=Kind.team, name="   ")
