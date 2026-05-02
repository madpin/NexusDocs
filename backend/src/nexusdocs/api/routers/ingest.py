"""/api/v1/ingest — ingestion job triggers and status."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...graph.repository import GraphRepository
from ...orchestrator import (
    get_ingestion_status,
    ingest_confluence,
    ingest_jira,
    ingest_markdown,
    ingest_repository,
    list_jobs,
)
from ..deps import get_repository
from ..errors import not_found

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRepositoryBody(BaseModel):
    repo_url: str
    branch: str = Field(default="main")


class IngestMarkdownBody(BaseModel):
    text: str = Field(..., min_length=1, description="The markdown / plain text body")
    title: str | None = Field(default=None, description="Optional document title")
    source_path: str | None = Field(
        default=None,
        description="Optional URL or path to record as the document's origin",
    )
    lenses: list[str] | None = Field(default=None)


class IngestConfluenceBody(BaseModel):
    base_url: str = Field(
        ..., description="Confluence base URL (e.g. https://your-org.atlassian.net/wiki)"
    )
    page_id: str
    token: str | None = Field(
        default=None, description="API token / PAT (omit for public pages)"
    )
    username: str | None = Field(
        default=None, description="Atlassian Cloud uses email + token (basic auth)"
    )
    lenses: list[str] | None = Field(default=None)


class IngestJiraBody(BaseModel):
    base_url: str
    issue_key: str
    token: str | None = None
    username: str | None = None
    lenses: list[str] | None = Field(default=None)


@router.post("/repository")
def trigger_repository(
    body: IngestRepositoryBody, repo: GraphRepository = Depends(get_repository)
) -> dict[str, Any]:
    return ingest_repository(repo, repo_url=body.repo_url, branch=body.branch)


@router.post("/markdown")
def trigger_markdown(
    body: IngestMarkdownBody, repo: GraphRepository = Depends(get_repository)
) -> dict[str, Any]:
    return ingest_markdown(
        repo,
        text=body.text,
        title=body.title,
        source_path=body.source_path,
        lenses=body.lenses,
    )


@router.post("/confluence")
def trigger_confluence(
    body: IngestConfluenceBody, repo: GraphRepository = Depends(get_repository)
) -> dict[str, Any]:
    return ingest_confluence(
        repo,
        base_url=body.base_url,
        page_id=body.page_id,
        token=body.token,
        username=body.username,
        lenses=body.lenses,
    )


@router.post("/jira")
def trigger_jira(
    body: IngestJiraBody, repo: GraphRepository = Depends(get_repository)
) -> dict[str, Any]:
    return ingest_jira(
        repo,
        base_url=body.base_url,
        issue_key=body.issue_key,
        token=body.token,
        username=body.username,
        lenses=body.lenses,
    )


@router.get("/status/{job_id}")
def status(
    job_id: str, repo: GraphRepository = Depends(get_repository)
) -> dict[str, Any]:
    s = get_ingestion_status(repo, job_id)
    if s is None:
        raise not_found("not_found", f"job {job_id} not found")
    return _status_to_dict(s)


@router.get("")
def jobs(repo: GraphRepository = Depends(get_repository)) -> list[dict[str, Any]]:
    return [_status_to_dict(s) for s in list_jobs(repo)]


def _status_to_dict(s) -> dict[str, Any]:
    return {
        "job_id": s.job_id,
        "status": s.status.value,
        "progress": s.progress,
        "documents_processed": s.documents_processed,
        "entities_created": s.entities_created,
        "entities_updated": s.entities_updated,
        "relationships_created": s.relationships_created,
        "fragments_created": s.fragments_created,
        "errors": list(s.errors),
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
        "metadata": s.metadata,
    }
