"""In-memory graph repository backed by a NetworkX MultiDiGraph."""

import copy
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import networkx as nx

from ..core import DocFragment, Entity, Relationship, ViewPreset
from ..core.enums import ALLOWED_PARENT_KINDS
from .repository import (
    EntityNotFoundError,
    FragmentNotFoundError,
    PresetNotFoundError,
    RelationshipNotFoundError,
    RepositoryError,
    Transaction,
)


class _MemoryTransaction(Transaction):
    def __init__(self, repo: "InMemoryGraphRepository") -> None:
        self._repo = repo
        self._snapshot: dict | None = None
        self._committed = False

    def __enter__(self) -> "_MemoryTransaction":
        self._snapshot = self._repo._snapshot()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is not None:
            self.rollback()
            return False
        if not self._committed:
            self.commit()
        return False

    def commit(self) -> None:
        self._committed = True
        self._snapshot = None

    def rollback(self) -> None:
        if self._snapshot is not None:
            self._repo._restore(self._snapshot)
            self._snapshot = None


class InMemoryGraphRepository:
    """NetworkX-backed implementation of `GraphRepository`."""

    def __init__(self) -> None:
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        self._fragments: dict[str, DocFragment] = {}
        self._presets: dict[str, ViewPreset] = {}

    # --- Lifecycle ---
    def initialize(self) -> None:
        return None

    def transaction(self) -> Transaction:
        return _MemoryTransaction(self)

    def _snapshot(self) -> dict:
        return {
            "graph": self._graph.copy(),
            "entities": dict(self._entities),
            "relationships": dict(self._relationships),
            "fragments": copy.copy(self._fragments),
            "presets": dict(self._presets),
        }

    def _restore(self, snapshot: dict) -> None:
        self._graph = snapshot["graph"]
        self._entities = snapshot["entities"]
        self._relationships = snapshot["relationships"]
        self._fragments = snapshot["fragments"]
        self._presets = snapshot["presets"]

    # --- Entities ---
    def upsert_entity(self, entity: Entity) -> Entity:
        if entity.parent is not None:
            if entity.parent not in self._entities:
                raise RepositoryError(
                    f"entity {entity.id!r} parent {entity.parent!r} does not exist"
                )
            parent = self._entities[entity.parent]
            allowed = ALLOWED_PARENT_KINDS.get(entity.kind, frozenset())
            if parent.kind not in allowed:
                raise RepositoryError(
                    f"entity {entity.id!r} (kind={entity.kind.value}) cannot have parent of kind "
                    f"{parent.kind.value!r}; allowed: {sorted(k.value for k in allowed)}"
                )

        existing = self._entities.get(entity.id)
        if existing is not None:
            entity = entity.model_copy(
                update={
                    "created_at": existing.created_at,
                    "updated_at": datetime.now(UTC),
                }
            )
        self._entities[entity.id] = entity
        self._graph.add_node(entity.id, kind=entity.kind.value, labels=set(entity.labels))
        return entity

    def get_entity(self, entity_id: str) -> Entity:
        try:
            return self._entities[entity_id]
        except KeyError as e:
            raise EntityNotFoundError(entity_id) from e

    def has_entity(self, entity_id: str) -> bool:
        return entity_id in self._entities

    def list_entities(self) -> list[Entity]:
        return list(self._entities.values())

    def delete_entity(self, entity_id: str) -> None:
        if entity_id not in self._entities:
            raise EntityNotFoundError(entity_id)
        # Cascade delete edges and fragments anchored to this entity
        rels_to_drop = [
            rid
            for rid, r in self._relationships.items()
            if r.source == entity_id or r.target == entity_id
        ]
        for rid in rels_to_drop:
            self.delete_relationship(rid)
        del self._entities[entity_id]
        if self._graph.has_node(entity_id):
            self._graph.remove_node(entity_id)

    # --- Relationships ---
    def upsert_relationship(self, rel: Relationship) -> Relationship:
        if rel.source not in self._entities:
            raise RepositoryError(
                f"relationship {rel.id!r} source {rel.source!r} does not exist"
            )
        if rel.target not in self._entities:
            raise RepositoryError(
                f"relationship {rel.id!r} target {rel.target!r} does not exist"
            )

        existing = self._relationships.get(rel.id)
        if existing is not None:
            rel = rel.model_copy(
                update={
                    "created_at": existing.created_at,
                    "updated_at": datetime.now(UTC),
                }
            )
            # Drop the previous edge in the multigraph
            self._remove_edge_by_rel_id(existing)

        self._relationships[rel.id] = rel
        self._graph.add_edge(
            rel.source,
            rel.target,
            key=rel.id,
            type=rel.type.value,
            protocol=str(rel.protocol) if rel.protocol else None,
            mode=rel.mode.value if rel.mode else None,
        )
        return rel

    def _remove_edge_by_rel_id(self, rel: Relationship) -> None:
        if self._graph.has_edge(rel.source, rel.target, key=rel.id):
            self._graph.remove_edge(rel.source, rel.target, key=rel.id)

    def get_relationship(self, rel_id: str) -> Relationship:
        try:
            return self._relationships[rel_id]
        except KeyError as e:
            raise RelationshipNotFoundError(rel_id) from e

    def has_relationship(self, rel_id: str) -> bool:
        return rel_id in self._relationships

    def list_relationships(self) -> list[Relationship]:
        return list(self._relationships.values())

    def delete_relationship(self, rel_id: str) -> None:
        if rel_id not in self._relationships:
            raise RelationshipNotFoundError(rel_id)
        rel = self._relationships.pop(rel_id)
        self._remove_edge_by_rel_id(rel)

    def edges_of(
        self, entity_id: str, *, direction: str = "both"
    ) -> list[Relationship]:
        if entity_id not in self._entities:
            raise EntityNotFoundError(entity_id)
        out: list[Relationship] = []
        if direction in ("outgoing", "both"):
            out.extend(r for r in self._relationships.values() if r.source == entity_id)
        if direction in ("incoming", "both"):
            out.extend(r for r in self._relationships.values() if r.target == entity_id)
        return out

    def children_of(self, entity_id: str) -> list[Entity]:
        return [e for e in self._entities.values() if e.parent == entity_id]

    # --- Fragments ---
    def upsert_fragment(self, fragment: DocFragment) -> DocFragment:
        for s in fragment.subjects:
            if s.entity not in self._entities:
                raise RepositoryError(
                    f"fragment {fragment.id!r} references missing entity {s.entity!r}"
                )
        for r in fragment.relations:
            if r.rel not in self._relationships:
                raise RepositoryError(
                    f"fragment {fragment.id!r} references missing relationship {r.rel!r}"
                )
        self._fragments[fragment.id] = fragment
        return fragment

    def get_fragment(self, fragment_id: str) -> DocFragment:
        try:
            return self._fragments[fragment_id]
        except KeyError as e:
            raise FragmentNotFoundError(fragment_id) from e

    def has_fragment(self, fragment_id: str) -> bool:
        return fragment_id in self._fragments

    def list_fragments(self) -> list[DocFragment]:
        return list(self._fragments.values())

    def fragments_by_subject(self, entity_id: str) -> list[DocFragment]:
        return [
            f
            for f in self._fragments.values()
            if any(s.entity == entity_id for s in f.subjects)
        ]

    def fragments_by_relation(self, rel_id: str) -> list[DocFragment]:
        return [
            f
            for f in self._fragments.values()
            if any(r.rel == rel_id for r in f.relations)
        ]

    def fragments_by_tag(self, tag: str) -> list[DocFragment]:
        return [f for f in self._fragments.values() if tag in f.tags]

    def delete_fragment(self, fragment_id: str) -> None:
        if fragment_id not in self._fragments:
            raise FragmentNotFoundError(fragment_id)
        del self._fragments[fragment_id]

    # --- Presets ---
    def upsert_preset(self, preset: ViewPreset) -> ViewPreset:
        if preset.owner not in self._entities:
            raise RepositoryError(
                f"preset {preset.id!r} owner {preset.owner!r} does not exist"
            )
        if preset.focus not in self._entities:
            raise RepositoryError(
                f"preset {preset.id!r} focus {preset.focus!r} does not exist"
            )
        self._presets[preset.id] = preset
        return preset

    def get_preset(self, preset_id: str) -> ViewPreset:
        try:
            return self._presets[preset_id]
        except KeyError as e:
            raise PresetNotFoundError(preset_id) from e

    def list_presets(self) -> list[ViewPreset]:
        return list(self._presets.values())

    def delete_preset(self, preset_id: str) -> None:
        if preset_id not in self._presets:
            raise PresetNotFoundError(preset_id)
        del self._presets[preset_id]

    # --- NetworkX accessor (used by view engine) ---
    @property
    def graph(self) -> nx.MultiDiGraph:
        return self._graph

    @contextmanager
    def view_transaction(self) -> Iterator["_MemoryTransaction"]:
        tx = _MemoryTransaction(self)
        with tx as t:
            yield t
