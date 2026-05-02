"""Entity model — a node in the graph."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import Kind
from .ids import validate_id
from .provenance import SourceRef


class Entity(BaseModel):
    """A node in the NexusDocs graph. See docs/schemas/entity.md."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Kind
    name: str
    parent: str | None = None
    labels: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: SourceRef | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        return validate_id(v)

    @field_validator("parent")
    @classmethod
    def _validate_parent(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_id(v)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v

    @field_validator("labels")
    @classmethod
    def _unique_labels(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("labels must be unique")
        return v

    @field_validator("created_at", "updated_at")
    @classmethod
    def _normalize_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v
