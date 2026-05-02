"""Conflict resolution: human > reviewed-LLM > unreviewed-LLM precedence.

The resolver decides whether a newly-extracted fact should overwrite,
augment, or be held back. See docs/framework/ingestion.md.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from ..core import DocFragment, Entity, Relationship
from ..core.enums import GeneratedBy
from ..graph.repository import (
    EntityNotFoundError,
    FragmentNotFoundError,
    GraphRepository,
    RelationshipNotFoundError,
)


def _provenance_rank(generated_by: GeneratedBy, reviewed: bool) -> int:
    """Higher = takes precedence."""
    if generated_by == GeneratedBy.human:
        return 3
    if reviewed:
        return 2
    return 1


@dataclass
class ConflictRecord:
    target_kind: Literal["Entity", "Relationship", "DocFragment"]
    target_id: str
    reason: str
    held_value: dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ResolveReport:
    accepted: int = 0
    held: list[ConflictRecord] = field(default_factory=list)


class ConflictResolver:
    """Apply incoming objects to a repo, deferring conflicts."""

    def __init__(self, repo: GraphRepository) -> None:
        self.repo = repo

    # ---- Entities ---------------------------------------------------------

    def upsert_entity(self, entity: Entity) -> ConflictRecord | None:
        try:
            existing = self.repo.get_entity(entity.id)
        except EntityNotFoundError:
            self.repo.upsert_entity(entity)
            return None

        if existing.source and entity.source:
            existing_rank = _provenance_rank(
                GeneratedBy.human if existing.source.source_type == "manual" else GeneratedBy.llm,
                False,
            )
            incoming_rank = _provenance_rank(
                GeneratedBy.human if entity.source.source_type == "manual" else GeneratedBy.llm,
                False,
            )
            if incoming_rank < existing_rank:
                return ConflictRecord(
                    target_kind="Entity",
                    target_id=entity.id,
                    reason="incoming has lower provenance rank than existing",
                    held_value=entity.model_dump(mode="json"),
                )
        self.repo.upsert_entity(entity)
        return None

    # ---- Fragments --------------------------------------------------------

    def upsert_fragment(self, fragment: DocFragment) -> ConflictRecord | None:
        try:
            existing = self.repo.get_fragment(fragment.id)
        except FragmentNotFoundError:
            self.repo.upsert_fragment(fragment)
            return None

        existing_rank = _provenance_rank(
            existing.provenance.generated_by, existing.provenance.reviewed
        )
        incoming_rank = _provenance_rank(
            fragment.provenance.generated_by, fragment.provenance.reviewed
        )
        if incoming_rank < existing_rank:
            return ConflictRecord(
                target_kind="DocFragment",
                target_id=fragment.id,
                reason="existing fragment outranks incoming",
                held_value=fragment.model_dump(mode="json"),
            )
        self.repo.upsert_fragment(fragment)
        return None

    # ---- Relationships ----------------------------------------------------

    def upsert_relationship(self, relationship: Relationship) -> ConflictRecord | None:
        try:
            self.repo.get_relationship(relationship.id)
        except RelationshipNotFoundError:
            self.repo.upsert_relationship(relationship)
            return None
        # No provenance on relationships; always accept newer.
        self.repo.upsert_relationship(relationship)
        return None
