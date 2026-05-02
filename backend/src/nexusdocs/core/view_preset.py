"""ViewPreset — a saved view configuration."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .ids import validate_id


class FilterSet(BaseModel):
    """Filters applied to a view."""

    model_config = ConfigDict(extra="forbid")

    entity_kinds: list[str] = Field(default_factory=list)
    relationship_types: list[str] = Field(default_factory=list)
    protocols: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class ViewPreset(BaseModel):
    """A saved combination of focus, zoom, lenses, radius, and filters."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    owner: str
    shared_with: list[str] = Field(default_factory=list)

    focus: str
    zoom: Annotated[int, Field(ge=0, le=100)]
    lenses: list[str]
    radius: Annotated[int, Field(ge=0)]
    filters: FilterSet = Field(default_factory=FilterSet)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("id", "owner", "focus")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        return validate_id(v)

    @field_validator("shared_with")
    @classmethod
    def _validate_shared(cls, v: list[str]) -> list[str]:
        return [validate_id(x) for x in v]

    @field_validator("lenses")
    @classmethod
    def _at_least_one_lens(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("lenses must be non-empty")
        return v
