"""/api/v1/search — fuzzy search across entities/relationships/fragments."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...core.view_preset import FilterSet
from ...graph.repository import GraphRepository
from ...orchestrator import search_graph
from ...search import SearchScope
from ..deps import get_repository

router = APIRouter(prefix="/search", tags=["search"])


class SearchBody(BaseModel):
    query: str
    scope: SearchScope = SearchScope.all
    filters: FilterSet = Field(default_factory=FilterSet)
    limit: int = 25


@router.post("")
def search(
    body: SearchBody, repo: GraphRepository = Depends(get_repository)
) -> dict[str, Any]:
    hits = search_graph(
        repo,
        body.query,
        scope=body.scope,
        filters=body.filters,
        limit=body.limit,
    )
    return {"hits": [h.model_dump() for h in hits]}
