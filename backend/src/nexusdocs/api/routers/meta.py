"""/api/v1/meta — version + counts so the About page can show something useful."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from fastapi import APIRouter, Depends

from ...graph.repository import GraphRepository
from ..deps import get_repository

router = APIRouter(prefix="/meta", tags=["meta"])


def _pkg_version() -> str:
    try:
        return version("nexusdocs")
    except PackageNotFoundError:
        return "0.0.0-dev"


@router.get("")
def read_meta(repo: GraphRepository = Depends(get_repository)) -> dict[str, Any]:
    entities = repo.list_entities()
    relationships = repo.list_relationships()
    fragments = repo.list_fragments()
    by_kind: dict[str, int] = {}
    for e in entities:
        by_kind[e.kind.value] = by_kind.get(e.kind.value, 0) + 1
    by_lens: dict[str, int] = {}
    for f in fragments:
        for lens in f.coverage.lenses:
            by_lens[lens] = by_lens.get(lens, 0) + 1
    return {
        "name": "NexusDocs",
        "version": _pkg_version(),
        "tagline": "Continuous-zoom architecture documentation, powered by a knowledge graph.",
        "homepage": "https://github.com/madpin/nexusdocs",
        "license": "Apache-2.0",
        "totals": {
            "entities": len(entities),
            "relationships": len(relationships),
            "fragments": len(fragments),
        },
        "entities_by_kind": by_kind,
        "fragments_by_lens": by_lens,
    }
