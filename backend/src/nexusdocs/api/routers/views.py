"""/api/v1/views — render and presets."""

from fastapi import APIRouter, Depends

from ...core import RenderedView, ViewPreset, ViewRequest
from ...graph.repository import GraphRepository, RepositoryError
from ...llm.client import LLMClient
from ...orchestrator import render_view
from ...view.subgraph import FocusNotFoundError
from ..deps import get_llm, get_repository
from ..errors import not_found, validation_failed

router = APIRouter(prefix="/views", tags=["views"])


@router.post("/render", response_model=RenderedView)
def render(
    request: ViewRequest,
    repo: GraphRepository = Depends(get_repository),
    llm: LLMClient = Depends(get_llm),
) -> RenderedView:
    try:
        return render_view(repo, request, llm=llm)
    except FocusNotFoundError as e:
        raise not_found("not_found", f"focus entity {e} not found")
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.post("/presets", response_model=ViewPreset, status_code=201)
def create_preset(
    preset: ViewPreset, repo: GraphRepository = Depends(get_repository)
) -> ViewPreset:
    try:
        return repo.upsert_preset(preset)
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.get("/presets", response_model=list[ViewPreset])
def list_presets(
    repo: GraphRepository = Depends(get_repository),
) -> list[ViewPreset]:
    return repo.list_presets()


@router.get("/presets/{preset_id}", response_model=ViewPreset)
def read_preset(
    preset_id: str, repo: GraphRepository = Depends(get_repository)
) -> ViewPreset:
    try:
        return repo.get_preset(preset_id)
    except Exception:
        raise not_found("not_found", f"preset {preset_id} not found")


@router.put("/presets/{preset_id}", response_model=ViewPreset)
def update_preset(
    preset_id: str,
    preset: ViewPreset,
    repo: GraphRepository = Depends(get_repository),
) -> ViewPreset:
    if preset.id != preset_id:
        raise validation_failed("path id does not match body id")
    try:
        return repo.upsert_preset(preset)
    except RepositoryError as e:
        raise validation_failed(str(e))


@router.delete("/presets/{preset_id}", status_code=204)
def delete_preset(
    preset_id: str, repo: GraphRepository = Depends(get_repository)
) -> None:
    try:
        repo.delete_preset(preset_id)
    except Exception:
        raise not_found("not_found", f"preset {preset_id} not found")
