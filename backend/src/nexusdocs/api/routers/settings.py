"""/api/v1/settings — read effective configuration and runtime overrides.

This endpoint never returns API keys verbatim, only redacted markers, so
that an SPA can show "configured / unconfigured" without leaking secrets.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ...config import Settings
from ..deps import get_settings_dep

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsView(BaseModel):
    repository_backend: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_database: str
    openai_api_key_set: bool = Field(
        ..., description="Whether an API key is configured (never returns the value)."
    )
    openai_model: str
    openai_base_url: str | None
    api_host: str
    api_port: int
    api_cors_origins: list[str]
    llm_client: str = Field(
        ...,
        description=(
            "Effective LLM client class (OpenAIClient or DeterministicMockClient)."
        ),
    )


class SettingsPatch(BaseModel):
    """Runtime-only overrides — never persisted to disk."""

    openai_api_key: str | None = Field(
        default=None,
        description="Set or clear the OpenAI key (use empty string to clear).",
    )
    openai_model: str | None = None
    openai_base_url: str | None = Field(
        default=None,
        description="Set or clear the OpenAI-compatible base URL.",
    )


def _to_view(settings: Settings, llm) -> SettingsView:
    return SettingsView(
        repository_backend=settings.repository_backend,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_database=settings.neo4j_database,
        openai_api_key_set=bool(settings.openai_api_key),
        openai_model=settings.openai_model,
        openai_base_url=settings.openai_base_url,
        api_host=settings.api_host,
        api_port=settings.api_port,
        api_cors_origins=list(settings.api_cors_origins),
        llm_client=type(llm).__name__,
    )


@router.get("", response_model=SettingsView)
def read_settings(request: Request, settings: Settings = Depends(get_settings_dep)):
    return _to_view(settings, request.app.state.llm)


@router.patch("", response_model=SettingsView)
def patch_settings(
    body: SettingsPatch,
    request: Request,
    settings: Settings = Depends(get_settings_dep),
) -> Any:
    """Apply runtime LLM overrides and rebuild the LLM client.

    These changes live only in the running process — they reset on restart.
    Useful for trying out a model, point at a self-hosted endpoint, or
    swapping in a fresh API key without redeploying.
    """
    if body.openai_api_key is not None:
        settings.openai_api_key = body.openai_api_key or None
    if body.openai_model is not None and body.openai_model.strip():
        settings.openai_model = body.openai_model.strip()
    if body.openai_base_url is not None:
        settings.openai_base_url = body.openai_base_url or None

    llm = _build_llm(settings)
    request.app.state.llm = llm
    request.app.state.settings = settings

    # Rebind the ingestion pipeline so it picks up the new client.
    from ...orchestrator import ingest as ingest_module

    ingest_module._pipeline = None  # next call rebuilds with the new LLM

    return _to_view(settings, llm)


def _build_llm(settings: Settings):
    if settings.openai_api_key or settings.openai_base_url:
        from ...llm.openai_client import OpenAIClient

        return OpenAIClient(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )
    from ...llm.mock import DeterministicMockClient

    return DeterministicMockClient()
