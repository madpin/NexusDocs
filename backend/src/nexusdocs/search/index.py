"""Search Protocol — the seam for Typesense / Elasticsearch / pgvector."""

from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from ..core.view_preset import FilterSet


class SearchScope(StrEnum):
    entities = "entities"
    relationships = "relationships"
    fragments = "fragments"
    all = "all"


class _BaseHit(BaseModel):
    id: str
    score: float
    snippet: str | None = None


class EntityHit(_BaseHit):
    kind: Literal["entity"] = "entity"


class RelationshipHit(_BaseHit):
    kind: Literal["relationship"] = "relationship"


class FragmentHit(_BaseHit):
    kind: Literal["fragment"] = "fragment"


SearchHit = EntityHit | RelationshipHit | FragmentHit


@runtime_checkable
class SearchIndex(Protocol):
    """Persistence-layer search."""

    def search(
        self,
        query: str,
        *,
        scope: SearchScope = SearchScope.all,
        filters: FilterSet | None = None,
        limit: int = 25,
    ) -> list[SearchHit]: ...
