"""Relationship model — a directed edge between two entities."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import Mode, Protocol, RelationshipType
from .ids import validate_id
from .provenance import SourceRef


class Relationship(BaseModel):
    """A directed edge between two entities. See docs/schemas/relationship.md."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source: str
    target: str
    type: RelationshipType
    protocol: Protocol | str | None = None
    mode: Mode | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_ref: SourceRef | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("id", "source", "target")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        return validate_id(v)

    @field_validator("created_at", "updated_at")
    @classmethod
    def _normalize_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v
