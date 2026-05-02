"""In-process ingestion job queue. Phase-2 connector logic plugs in here."""

import secrets
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from ..graph.repository import GraphRepository
from ..llm.client import LLMClient, build_default_client
from .conflict import ConflictResolver


class JobState(StrEnum):
    queued = "queued"
    in_progress = "in_progress"
    succeeded = "succeeded"
    failed = "failed"


@dataclass
class IngestionStatus:
    job_id: str
    status: JobState
    progress: float = 0.0
    documents_processed: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    relationships_created: int = 0
    fragments_created: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionJob:
    job_id: str
    status: JobState
    repo_url: str
    branch: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class IngestionPipeline:
    """Single-threaded job runner. Phase-2 fills in the actual ingestion."""

    def __init__(
        self,
        repo: GraphRepository,
        *,
        llm: LLMClient | None = None,
    ) -> None:
        self.repo = repo
        self.llm: LLMClient = llm if llm is not None else build_default_client()
        self.resolver = ConflictResolver(repo)
        self._jobs: dict[str, IngestionStatus] = {}
        self._lock = threading.Lock()

    def submit_repository(
        self, *, repo_url: str, branch: str = "main"
    ) -> IngestionJob:
        job_id = "ing." + secrets.token_hex(4)
        with self._lock:
            self._jobs[job_id] = IngestionStatus(
                job_id=job_id,
                status=JobState.queued,
                started_at=datetime.now(UTC),
                metadata={"source": "git", "repo_url": repo_url, "branch": branch},
            )
        try:
            self._run_repository_job(job_id, repo_url=repo_url, branch=branch)
        except Exception as e:
            with self._lock:
                self._jobs[job_id].status = JobState.failed
                self._jobs[job_id].errors.append(str(e))

        return IngestionJob(
            job_id=job_id,
            status=self._jobs[job_id].status,
            repo_url=repo_url,
            branch=branch,
        )

    # ---- New connector entry points -----------------------------------

    def submit_markdown(
        self,
        *,
        text: str,
        title: str | None = None,
        source_path: str | None = None,
        lenses: list[str] | None = None,
    ) -> IngestionStatus:
        from .connectors.markdown import MarkdownConnector

        job_id = "ing." + secrets.token_hex(4)
        meta = {
            "source": "markdown",
            "title": title,
            "source_path": source_path,
            "bytes": len(text),
        }
        with self._lock:
            self._jobs[job_id] = IngestionStatus(
                job_id=job_id,
                status=JobState.in_progress,
                started_at=datetime.now(UTC),
                metadata=meta,
            )
        connector = MarkdownConnector(self.llm, self.resolver)
        report = connector.ingest(
            text=text,
            title=title,
            source_path=source_path,
            lenses=lenses,
        )
        return self._finalize(
            job_id, report, extra={"parent_fragment_id": report.parent_fragment_id}
        )

    def submit_confluence(
        self,
        *,
        base_url: str,
        page_id: str,
        token: str | None = None,
        username: str | None = None,
        lenses: list[str] | None = None,
    ) -> IngestionStatus:
        from .connectors.confluence import ConfluenceConnector

        job_id = "ing." + secrets.token_hex(4)
        meta = {
            "source": "confluence",
            "base_url": base_url,
            "page_id": page_id,
        }
        with self._lock:
            self._jobs[job_id] = IngestionStatus(
                job_id=job_id,
                status=JobState.in_progress,
                started_at=datetime.now(UTC),
                metadata=meta,
            )
        connector = ConfluenceConnector(self.llm, self.resolver)
        report = connector.ingest_page(
            base_url=base_url,
            page_id=page_id,
            token=token,
            username=username,
            lenses=lenses,
        )
        return self._finalize(
            job_id, report, extra={"parent_fragment_id": report.parent_fragment_id}
        )

    def submit_jira(
        self,
        *,
        base_url: str,
        issue_key: str,
        token: str | None = None,
        username: str | None = None,
        lenses: list[str] | None = None,
    ) -> IngestionStatus:
        from .connectors.jira import JiraConnector

        job_id = "ing." + secrets.token_hex(4)
        meta = {
            "source": "jira",
            "base_url": base_url,
            "issue_key": issue_key,
        }
        with self._lock:
            self._jobs[job_id] = IngestionStatus(
                job_id=job_id,
                status=JobState.in_progress,
                started_at=datetime.now(UTC),
                metadata=meta,
            )
        connector = JiraConnector(self.llm, self.resolver)
        report = connector.ingest_issue(
            base_url=base_url,
            issue_key=issue_key,
            token=token,
            username=username,
            lenses=lenses,
        )
        return self._finalize(
            job_id, report, extra={"parent_fragment_id": report.parent_fragment_id}
        )

    # ---- helpers ------------------------------------------------------

    def _finalize(
        self,
        job_id: str,
        report,
        *,
        extra: dict[str, Any] | None = None,
    ) -> IngestionStatus:
        with self._lock:
            status = self._jobs[job_id]
            status.status = (
                JobState.succeeded if not report.errors else JobState.failed
            )
            status.documents_processed = report.documents_processed
            status.entities_created = report.entities_created
            status.entities_updated = report.entities_updated
            status.relationships_created = report.relationships_created
            status.fragments_created = report.fragments_created
            status.errors.extend(report.errors)
            status.progress = 1.0
            status.finished_at = datetime.now(UTC)
            if extra:
                for k, v in extra.items():
                    if v is not None:
                        status.metadata[k] = v
            return status

    def _run_repository_job(
        self, job_id: str, *, repo_url: str, branch: str
    ) -> None:
        from .connectors.git import GitConnector

        with self._lock:
            self._jobs[job_id].status = JobState.in_progress

        connector = GitConnector(self.llm, self.resolver)
        report = connector.ingest(repo_url=repo_url, branch=branch)
        self._finalize(job_id, report)

    def status(self, job_id: str) -> IngestionStatus | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[IngestionStatus]:
        with self._lock:
            return list(self._jobs.values())
