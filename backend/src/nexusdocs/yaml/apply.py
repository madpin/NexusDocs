"""Ordered, transactional apply of loaded YAML documents."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..core import Entity
from ..graph.repository import GraphRepository, RepositoryError
from .loader import LoadedDocuments, load_documents


@dataclass
class ApplyChange:
    kind: Literal["Entity", "Relationship", "DocFragment", "ViewPreset"]
    id: str
    action: Literal["created", "updated"]


@dataclass
class ApplyResult:
    applied: list[ApplyChange] = field(default_factory=list)
    skipped: list[ApplyChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return not self.errors


def _topo_sort_entities(entities: Iterable[Entity]) -> list[Entity]:
    """Return entities ordered so that any parent appears before its children."""
    by_id = {e.id: e for e in entities}
    visited: set[str] = set()
    out: list[Entity] = []

    def visit(eid: str, stack: tuple[str, ...]) -> None:
        if eid in visited:
            return
        if eid in stack:
            chain = " -> ".join((*stack, eid))
            raise RepositoryError(f"circular parent chain detected: {chain}")
        e = by_id.get(eid)
        if e is None:
            return  # parent lives outside this batch; skip
        if e.parent and e.parent in by_id:
            visit(e.parent, (*stack, eid))
        visited.add(eid)
        out.append(e)

    for e in entities:
        visit(e.id, ())
    return out


def apply_documents(
    repo: GraphRepository,
    docs: LoadedDocuments | str | Path,
) -> ApplyResult:
    """Apply loaded documents transactionally to the given repository."""
    if not isinstance(docs, LoadedDocuments):
        docs = load_documents(docs)

    result = ApplyResult()

    try:
        entities_sorted = _topo_sort_entities(docs.entities)
    except RepositoryError as e:
        result.errors.append(str(e))
        return result

    with repo.transaction() as tx:
        try:
            for e in entities_sorted:
                action = "updated" if repo.has_entity(e.id) else "created"
                repo.upsert_entity(e)
                result.applied.append(ApplyChange("Entity", e.id, action))

            for r in docs.relationships:
                action = "updated" if repo.has_relationship(r.id) else "created"
                repo.upsert_relationship(r)
                result.applied.append(ApplyChange("Relationship", r.id, action))

            for f in docs.fragments:
                action = "updated" if repo.has_fragment(f.id) else "created"
                repo.upsert_fragment(f)
                result.applied.append(ApplyChange("DocFragment", f.id, action))

            for p in docs.presets:
                exists = False
                try:
                    repo.get_preset(p.id)
                    exists = True
                except Exception:
                    pass
                action = "updated" if exists else "created"
                repo.upsert_preset(p)
                result.applied.append(ApplyChange("ViewPreset", p.id, action))

            tx.commit()
        except Exception as e:
            tx.rollback()
            result.errors.append(str(e))
            result.applied.clear()

    return result
