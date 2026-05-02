"""Provenance and source-reference structures."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import GeneratedBy, SourceType


class SourceRef(BaseModel):
    """Where an object was discovered or defined."""

    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    source_path: str | None = None
    source_hash: str | None = None


class Provenance(BaseModel):
    """Where a fragment came from, and how confident we are in it."""

    model_config = ConfigDict(extra="forbid")

    source_type: SourceType
    source_path: str | None = None
    source_hash: str | None = None
    generated_by: GeneratedBy
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    reviewed: bool = False
    last_synced: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("created_at", "updated_at", "last_synced")
    @classmethod
    def _normalize_tz(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v

    @model_validator(mode="after")
    def _human_implies_full_confidence(self) -> "Provenance":
        if self.generated_by == GeneratedBy.human and self.confidence != 1.0:
            raise ValueError(
                "provenance.confidence must be 1.0 when generated_by is 'human'"
            )
        return self
