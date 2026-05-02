"""DocFragment model — anchorable, zoom-tagged chunk of documentation."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import Granularity, Lens
from .ids import validate_id
from .provenance import Provenance


class _Subject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: str

    @field_validator("entity")
    @classmethod
    def _validate(cls, v: str) -> str:
        return validate_id(v)


class _Relation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rel: str

    @field_validator("rel")
    @classmethod
    def _validate(cls, v: str) -> str:
        return validate_id(v)


class LiftOn(BaseModel):
    """Conditions under which zoom_min is lowered."""

    model_config = ConfigDict(extra="forbid")

    centrality_threshold: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    cluster_coverage_threshold: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    path_match: bool = False


class Coverage(BaseModel):
    """When and where this fragment is relevant."""

    model_config = ConfigDict(extra="forbid")

    zoom_min: Annotated[int, Field(ge=0, le=100)]
    zoom_max: Annotated[int, Field(ge=0, le=100)]
    lenses: list[str]
    granularity: Granularity | None = None
    lift_on: LiftOn = Field(default_factory=LiftOn)
    lift_by: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def _zoom_min_le_max(self) -> "Coverage":
        if self.zoom_min > self.zoom_max:
            raise ValueError(
                f"zoom_min ({self.zoom_min}) must be <= zoom_max ({self.zoom_max})"
            )
        return self

    @field_validator("lenses")
    @classmethod
    def _at_least_one_lens(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("coverage.lenses must contain at least one lens")
        return v


class DocFragment(BaseModel):
    """A chunk of documentation anchored to entities/relationships."""

    model_config = ConfigDict(extra="forbid")

    id: str
    doc_id: str | None = None
    title: str
    body: str
    format: Literal["markdown", "plaintext", "structured_yaml", "mermaid"] = "markdown"

    subjects: list[_Subject] = Field(default_factory=list)
    relations: list[_Relation] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    coverage: Coverage
    provenance: Provenance

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        return validate_id(v)

    @field_validator("doc_id")
    @classmethod
    def _validate_doc_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return validate_id(v)

    @field_validator("body")
    @classmethod
    def _body_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("body cannot be empty")
        return v

    @model_validator(mode="after")
    def _at_least_one_anchor(self) -> "DocFragment":
        if not self.subjects and not self.relations and not self.tags:
            raise ValueError(
                "fragment must have at least one of subjects, relations, or tags"
            )
        return self

    def subject_ids(self) -> list[str]:
        return [s.entity for s in self.subjects]

    def relation_ids(self) -> list[str]:
        return [r.rel for r in self.relations]

    def lens_set(self) -> set[str]:
        return set(self.coverage.lenses)

    def has_lens(self, lens: str | Lens) -> bool:
        return str(lens) in self.lens_set()
