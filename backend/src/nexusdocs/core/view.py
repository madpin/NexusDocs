"""View request and response models."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .entity import Entity
from .ids import validate_id
from .relationship import Relationship
from .view_preset import FilterSet


class ViewRequest(BaseModel):
    """Inputs to the view engine."""

    model_config = ConfigDict(extra="forbid")

    focus: str
    zoom: Annotated[int, Field(ge=0, le=100)]
    lenses: list[str] = Field(default_factory=lambda: ["technical"])
    radius: Annotated[int, Field(ge=0)] = 2
    filters: FilterSet = Field(default_factory=FilterSet)
    navigation_path: list[str] = Field(default_factory=list)

    @field_validator("focus")
    @classmethod
    def _validate_focus(cls, v: str) -> str:
        return validate_id(v)

    @field_validator("navigation_path")
    @classmethod
    def _validate_path(cls, v: list[str]) -> list[str]:
        return [validate_id(x) for x in v]

    @field_validator("lenses")
    @classmethod
    def _at_least_one_lens(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("lenses must be non-empty")
        return v


class RankedFragment(BaseModel):
    """A fragment selected for the rendered view, with scoring metadata."""

    model_config = ConfigDict(extra="allow")

    id: str
    title: str
    body: str
    rank: int
    effective_zoom_min: int
    lifted: bool
    lenses: list[str]
    confidence: float
    reviewed: bool
    source_path: str | None = None


class TopologyHighlights(BaseModel):
    """Output of the topology analysis step."""

    model_config = ConfigDict(extra="forbid")

    most_central: str | None = None
    structural_concerns: list[str] = Field(default_factory=list)


class RenderedView(BaseModel):
    """The output of the view engine."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    diagram: str
    fragments: list[RankedFragment]
    entities: list[Entity]
    relationships: list[Relationship]
    topology_highlights: TopologyHighlights
    follow_up_suggestions: list[str] = Field(default_factory=list)
