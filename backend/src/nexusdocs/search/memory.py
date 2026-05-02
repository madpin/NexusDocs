"""rapidfuzz-backed in-memory search.

Iterates the repository on every call. Adequate for v1; the SearchIndex
Protocol leaves room for a real index (Typesense, Elasticsearch) later.
"""

from rapidfuzz import fuzz

from ..core.view_preset import FilterSet
from ..graph.repository import GraphRepository
from .index import EntityHit, FragmentHit, RelationshipHit, SearchHit, SearchScope


def _score(query: str, *fields: str | None) -> float:
    text = " ".join(f for f in fields if f)
    if not text:
        return 0.0
    return fuzz.partial_ratio(query.lower(), text.lower()) / 100.0


class InMemorySearchIndex:
    """In-memory search backed by rapidfuzz partial-ratio scoring."""

    def __init__(self, repo: GraphRepository) -> None:
        self.repo = repo

    def search(
        self,
        query: str,
        *,
        scope: SearchScope = SearchScope.all,
        filters: FilterSet | None = None,
        limit: int = 25,
    ) -> list[SearchHit]:
        if not query or not query.strip():
            return []
        filters = filters or FilterSet()
        hits: list[SearchHit] = []

        if scope in (SearchScope.entities, SearchScope.all):
            for e in self.repo.list_entities():
                if filters.entity_kinds and e.kind.value not in filters.entity_kinds:
                    continue
                if filters.tags and not (set(e.labels) & set(filters.tags)):
                    continue
                score = _score(query, e.id, e.name, " ".join(e.labels))
                if score > 0.3:
                    hits.append(
                        EntityHit(
                            id=e.id,
                            score=score,
                            snippet=f"{e.name} ({e.kind.value})",
                        )
                    )

        if scope in (SearchScope.relationships, SearchScope.all):
            for r in self.repo.list_relationships():
                if (
                    filters.relationship_types
                    and r.type.value not in filters.relationship_types
                ):
                    continue
                if filters.protocols:
                    proto = str(r.protocol) if r.protocol else None
                    if proto not in filters.protocols:
                        continue
                proto_str = str(r.protocol) if r.protocol else ""
                score = _score(query, r.id, r.source, r.target, r.type.value, proto_str)
                if score > 0.3:
                    hits.append(
                        RelationshipHit(
                            id=r.id,
                            score=score,
                            snippet=f"{r.source} -[{r.type.value}]-> {r.target}",
                        )
                    )

        if scope in (SearchScope.fragments, SearchScope.all):
            for f in self.repo.list_fragments():
                if filters.tags and not (set(f.tags) & set(filters.tags)):
                    continue
                score = _score(query, f.id, f.title, f.body, " ".join(f.tags))
                if score > 0.3:
                    snippet = f.body[:160].replace("\n", " ")
                    hits.append(FragmentHit(id=f.id, score=score, snippet=snippet))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]
