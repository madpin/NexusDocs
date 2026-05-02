"""/api/v1/definitions/apply — bulk YAML."""

from typing import Any

from fastapi import APIRouter, Depends, Request

from ...graph.repository import GraphRepository
from ...orchestrator import apply_yaml_text
from ..deps import get_repository
from ..errors import validation_failed

router = APIRouter(prefix="/definitions", tags=["definitions"])


@router.post("/apply")
async def apply(
    request: Request, repo: GraphRepository = Depends(get_repository)
) -> dict[str, Any]:
    body = await request.body()
    text = body.decode("utf-8")

    if request.headers.get("content-type", "").startswith("application/json"):
        # Allow JSON wrapper {"yaml": "..."} for clients that prefer it.
        import json

        try:
            payload = json.loads(text)
            if isinstance(payload, dict) and "yaml" in payload:
                text = payload["yaml"]
        except json.JSONDecodeError as e:
            raise validation_failed(f"invalid JSON: {e}")

    result = apply_yaml_text(repo, text)
    if not result.ok():
        raise validation_failed("; ".join(result.errors))
    return {
        "applied": [
            {"kind": a.kind, "id": a.id, "action": a.action}
            for a in result.applied
        ],
        "skipped": [
            {"kind": a.kind, "id": a.id, "action": a.action}
            for a in result.skipped
        ],
        "errors": list(result.errors),
    }
