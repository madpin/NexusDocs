"""/api/v1/fragments — CRUD."""

from fastapi import APIRouter, Depends

from ...core import DocFragment
from ...graph.repository import GraphRepository, RepositoryError
from ..deps import get_repository
from ..errors import not_found, validation_failed

router = APIRouter(prefix="/fragments", tags=["fragments"])


@router.post("", response_model=DocFragment, status_code=201)
def create_fragment(
    fragment: DocFragment, repo: GraphRepository = Depends(get_repository)
) -> DocFragment:
    try:
        return repo.upsert_fragment(fragment)
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.get("/{fragment_id}", response_model=DocFragment)
def read_fragment(
    fragment_id: str, repo: GraphRepository = Depends(get_repository)
) -> DocFragment:
    try:
        return repo.get_fragment(fragment_id)
    except Exception:
        raise not_found("not_found", f"fragment {fragment_id} not found")


@router.put("/{fragment_id}", response_model=DocFragment)
def update_fragment(
    fragment_id: str,
    fragment: DocFragment,
    repo: GraphRepository = Depends(get_repository),
) -> DocFragment:
    if fragment.id != fragment_id:
        raise validation_failed("path id does not match body id")
    try:
        return repo.upsert_fragment(fragment)
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.get("", tags=["fragments"])
def list_fragments(repo: GraphRepository = Depends(get_repository)) -> list[DocFragment]:
    return repo.list_fragments()
