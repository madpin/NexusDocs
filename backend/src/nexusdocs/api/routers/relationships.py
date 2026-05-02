"""/api/v1/relationships — CRUD."""

from fastapi import APIRouter, Depends

from ...core import Relationship
from ...graph.repository import (
    GraphRepository,
    RelationshipNotFoundError,
    RepositoryError,
)
from ..deps import get_repository
from ..errors import not_found, validation_failed

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.post("", response_model=Relationship, status_code=201)
def create_relationship(
    rel: Relationship, repo: GraphRepository = Depends(get_repository)
) -> Relationship:
    try:
        return repo.upsert_relationship(rel)
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.get("/{rel_id}", response_model=Relationship)
def read_relationship(
    rel_id: str, repo: GraphRepository = Depends(get_repository)
) -> Relationship:
    try:
        return repo.get_relationship(rel_id)
    except RelationshipNotFoundError:
        raise not_found("not_found", f"relationship {rel_id} not found")


@router.delete("/{rel_id}", status_code=204)
def delete_relationship(
    rel_id: str, repo: GraphRepository = Depends(get_repository)
) -> None:
    try:
        repo.delete_relationship(rel_id)
    except RelationshipNotFoundError:
        raise not_found("not_found", f"relationship {rel_id} not found")


@router.get("", tags=["relationships"])
def list_relationships(
    repo: GraphRepository = Depends(get_repository),
) -> list[Relationship]:
    return repo.list_relationships()
