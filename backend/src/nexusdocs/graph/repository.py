"""GraphRepository Protocol — the persistence seam."""

from collections.abc import Iterable
from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from ..core import DocFragment, Entity, Relationship, ViewPreset


class RepositoryError(Exception):
    """Base class for repository errors."""


class EntityNotFoundError(RepositoryError):
    pass


class RelationshipNotFoundError(RepositoryError):
    pass


class FragmentNotFoundError(RepositoryError):
    pass


class PresetNotFoundError(RepositoryError):
    pass


class Transaction(AbstractContextManager["Transaction"]):
    """A unit of work. Implementations may be optimistic or pessimistic."""

    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@runtime_checkable
class GraphRepository(Protocol):
    """Persistence Protocol for entities, relationships, fragments, and presets."""

    # --- Lifecycle ---
    def initialize(self) -> None: ...
    def transaction(self) -> Transaction: ...

    # --- Entities ---
    def upsert_entity(self, entity: Entity) -> Entity: ...
    def get_entity(self, entity_id: str) -> Entity: ...
    def has_entity(self, entity_id: str) -> bool: ...
    def list_entities(self) -> list[Entity]: ...
    def delete_entity(self, entity_id: str) -> None: ...

    # --- Relationships ---
    def upsert_relationship(self, rel: Relationship) -> Relationship: ...
    def get_relationship(self, rel_id: str) -> Relationship: ...
    def has_relationship(self, rel_id: str) -> bool: ...
    def list_relationships(self) -> list[Relationship]: ...
    def delete_relationship(self, rel_id: str) -> None: ...
    def edges_of(
        self, entity_id: str, *, direction: str = "both"
    ) -> list[Relationship]:
        """Return edges of an entity. direction in {outgoing, incoming, both}."""
        ...

    def children_of(self, entity_id: str) -> list[Entity]:
        """Return entities whose `parent` is `entity_id`."""
        ...

    # --- Fragments ---
    def upsert_fragment(self, fragment: DocFragment) -> DocFragment: ...
    def get_fragment(self, fragment_id: str) -> DocFragment: ...
    def has_fragment(self, fragment_id: str) -> bool: ...
    def list_fragments(self) -> list[DocFragment]: ...
    def fragments_by_subject(self, entity_id: str) -> list[DocFragment]: ...
    def fragments_by_relation(self, rel_id: str) -> list[DocFragment]: ...
    def fragments_by_tag(self, tag: str) -> list[DocFragment]: ...
    def delete_fragment(self, fragment_id: str) -> None: ...

    # --- Presets ---
    def upsert_preset(self, preset: ViewPreset) -> ViewPreset: ...
    def get_preset(self, preset_id: str) -> ViewPreset: ...
    def list_presets(self) -> list[ViewPreset]: ...
    def delete_preset(self, preset_id: str) -> None: ...

    # --- Bulk ---
    def upsert_entities(self, entities: Iterable[Entity]) -> None:
        for e in entities:
            self.upsert_entity(e)

    def upsert_relationships(self, rels: Iterable[Relationship]) -> None:
        for r in rels:
            self.upsert_relationship(r)

    def upsert_fragments(self, frags: Iterable[DocFragment]) -> None:
        for f in frags:
            self.upsert_fragment(f)
