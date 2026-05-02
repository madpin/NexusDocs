"""Search orchestration."""

from ..core.view_preset import FilterSet
from ..graph.repository import GraphRepository
from ..search import InMemorySearchIndex, SearchHit, SearchIndex, SearchScope


def search_graph(
    repo: GraphRepository,
    query: str,
    *,
    scope: SearchScope = SearchScope.all,
    filters: FilterSet | None = None,
    limit: int = 25,
    index: SearchIndex | None = None,
) -> list[SearchHit]:
    idx = index or InMemorySearchIndex(repo)
    return idx.search(query, scope=scope, filters=filters, limit=limit)
