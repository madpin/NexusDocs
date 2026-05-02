"""Ingestion job orchestration. Real Phase-2 logic lives in the ingestion package."""

from typing import Any

from ..graph.repository import GraphRepository
from ..ingestion.pipeline import IngestionPipeline, IngestionStatus

# Module-level singleton — keeps the in-process job table per process.
_pipeline: IngestionPipeline | None = None


def _get_pipeline(repo: GraphRepository) -> IngestionPipeline:
    global _pipeline
    if _pipeline is None or _pipeline.repo is not repo:
        _pipeline = IngestionPipeline(repo)
    return _pipeline


def ingest_repository(
    repo: GraphRepository, *, repo_url: str, branch: str = "main"
) -> dict[str, Any]:
    pipeline = _get_pipeline(repo)
    job = pipeline.submit_repository(repo_url=repo_url, branch=branch)
    return {"job_id": job.job_id, "status": job.status.value}


def ingest_markdown(
    repo: GraphRepository,
    *,
    text: str,
    title: str | None = None,
    source_path: str | None = None,
    lenses: list[str] | None = None,
) -> dict[str, Any]:
    pipeline = _get_pipeline(repo)
    status = pipeline.submit_markdown(
        text=text, title=title, source_path=source_path, lenses=lenses
    )
    return _summary_dict(status)


def ingest_confluence(
    repo: GraphRepository,
    *,
    base_url: str,
    page_id: str,
    token: str | None = None,
    username: str | None = None,
    lenses: list[str] | None = None,
) -> dict[str, Any]:
    pipeline = _get_pipeline(repo)
    status = pipeline.submit_confluence(
        base_url=base_url,
        page_id=page_id,
        token=token,
        username=username,
        lenses=lenses,
    )
    return _summary_dict(status)


def ingest_jira(
    repo: GraphRepository,
    *,
    base_url: str,
    issue_key: str,
    token: str | None = None,
    username: str | None = None,
    lenses: list[str] | None = None,
) -> dict[str, Any]:
    pipeline = _get_pipeline(repo)
    status = pipeline.submit_jira(
        base_url=base_url,
        issue_key=issue_key,
        token=token,
        username=username,
        lenses=lenses,
    )
    return _summary_dict(status)


def get_ingestion_status(repo: GraphRepository, job_id: str) -> IngestionStatus | None:
    pipeline = _get_pipeline(repo)
    return pipeline.status(job_id)


def list_jobs(repo: GraphRepository) -> list[IngestionStatus]:
    pipeline = _get_pipeline(repo)
    return pipeline.list_jobs()


def _summary_dict(status: IngestionStatus) -> dict[str, Any]:
    """Compact dict the API returns from synchronous ingestion endpoints."""
    return {
        "job_id": status.job_id,
        "status": status.status.value,
        "documents_processed": status.documents_processed,
        "entities_created": status.entities_created,
        "entities_updated": status.entities_updated,
        "relationships_created": status.relationships_created,
        "fragments_created": status.fragments_created,
        "parent_fragment_id": status.metadata.get("parent_fragment_id"),
        "errors": list(status.errors),
        "metadata": status.metadata,
    }
