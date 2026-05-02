"""/api/v1/entities — CRUD."""

from fastapi import APIRouter, Depends

from ...core import Entity
from ...core.relationship import Relationship
from ...graph.repository import (
    EntityNotFoundError,
    GraphRepository,
    RepositoryError,
)
from ..deps import get_repository
from ..errors import not_found, validation_failed

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("", response_model=Entity, status_code=201)
def create_entity(
    entity: Entity, repo: GraphRepository = Depends(get_repository)
) -> Entity:
    try:
        return repo.upsert_entity(entity)
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.get("/{entity_id}", response_model=Entity)
def read_entity(
    entity_id: str, repo: GraphRepository = Depends(get_repository)
) -> Entity:
    try:
        return repo.get_entity(entity_id)
    except EntityNotFoundError:
        raise not_found("not_found", f"entity {entity_id} not found")


@router.put("/{entity_id}", response_model=Entity)
def update_entity(
    entity_id: str,
    entity: Entity,
    repo: GraphRepository = Depends(get_repository),
) -> Entity:
    if entity.id != entity_id:
        raise validation_failed("path id does not match body id")
    try:
        return repo.upsert_entity(entity)
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.delete("/{entity_id}", status_code=204)
def delete_entity(
    entity_id: str, repo: GraphRepository = Depends(get_repository)
) -> None:
    try:
        repo.delete_entity(entity_id)
    except EntityNotFoundError:
        raise not_found("not_found", f"entity {entity_id} not found")


@router.get("/{entity_id}/edges")
def edges_for_entity(
    entity_id: str,
    repo: GraphRepository = Depends(get_repository),
) -> dict[str, list[Relationship]]:
    try:
        outgoing = repo.edges_of(entity_id, direction="outgoing")
        incoming = repo.edges_of(entity_id, direction="incoming")
        return {"outgoing": outgoing, "incoming": incoming}
    except EntityNotFoundError:
        raise not_found("not_found", f"entity {entity_id} not found")


@router.get("/{entity_id}/fragments")
def fragments_for_entity(
    entity_id: str,
    repo: GraphRepository = Depends(get_repository),
):
    try:
        repo.get_entity(entity_id)
    except EntityNotFoundError:
        raise not_found("not_found", f"entity {entity_id} not found")
    seen: dict[str, object] = {}
    for f in repo.fragments_by_subject(entity_id):
        seen[f.id] = f
    entity = repo.get_entity(entity_id)
    for label in entity.labels:
        for f in repo.fragments_by_tag(label):
            seen[f.id] = f
    for r in repo.edges_of(entity_id, direction="both"):
        for f in repo.fragments_by_relation(r.id):
            seen[f.id] = f
    return list(seen.values())


@router.get("", tags=["entities"])
def list_entities(repo: GraphRepository = Depends(get_repository)) -> list[Entity]:
    return repo.list_entities()
