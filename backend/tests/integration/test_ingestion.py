"""Tests for the ingestion pipeline using the local-files connector + mock LLM."""

from pathlib import Path

import pytest

from nexusdocs.core import (
    Coverage,
    DocFragment,
    Entity,
    Kind,
    Provenance,
    SourceType,
)
from nexusdocs.core.enums import GeneratedBy
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.ingestion.change_detector import ChangeDetector
from nexusdocs.ingestion.conflict import ConflictResolver
from nexusdocs.ingestion.connectors.local_files import LocalFilesConnector
from nexusdocs.llm import DeterministicMockClient


@pytest.fixture
def docs_dir(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text(
        "# Payments API\n\n"
        "service: payments-api\n\n"
        "The Payments API calls the Auth Service to verify session tokens.\n"
        "service: auth\n"
        "database: transactions\n"
    )
    return tmp_path


def test_local_files_extracts_entities(docs_dir: Path) -> None:
    repo = InMemoryGraphRepository()
    repo.initialize()
    connector = LocalFilesConnector(
        DeterministicMockClient(), ConflictResolver(repo)
    )
    report = connector.ingest(docs_dir)
    assert report.documents_processed >= 1
    ids = {e.id for e in repo.list_entities()}
    assert {"service.payments-api", "service.auth", "database.transactions"} <= ids


def test_change_detector_short_circuits(docs_dir: Path) -> None:
    repo = InMemoryGraphRepository()
    repo.initialize()
    detector = ChangeDetector()
    connector = LocalFilesConnector(
        DeterministicMockClient(), ConflictResolver(repo), detector
    )
    first = connector.ingest(docs_dir)
    second = connector.ingest(docs_dir)
    assert first.documents_processed >= 1
    assert second.documents_processed == 0  # nothing changed


def test_human_overrides_unreviewed_llm() -> None:
    repo = InMemoryGraphRepository()
    repo.initialize()
    repo.upsert_entity(Entity(id="service.x", kind=Kind.service, name="X"))
    repo.upsert_fragment(
        DocFragment(
            id="docfrag.x",
            title="Human authored",
            body="this is the source of truth",
            subjects=[{"entity": "service.x"}],
            tags=["t"],
            coverage=Coverage(zoom_min=10, zoom_max=80, lenses=["technical"]),
            provenance=Provenance(
                source_type=SourceType.manual,
                generated_by=GeneratedBy.human,
                confidence=1.0,
                reviewed=True,
            ),
        )
    )

    incoming = DocFragment(
        id="docfrag.x",
        title="LLM authored",
        body="...",
        subjects=[{"entity": "service.x"}],
        tags=["t"],
        coverage=Coverage(zoom_min=10, zoom_max=80, lenses=["technical"]),
        provenance=Provenance(
            source_type=SourceType.llm_generated,
            generated_by=GeneratedBy.llm,
            confidence=0.7,
            reviewed=False,
        ),
    )
    resolver = ConflictResolver(repo)
    conflict = resolver.upsert_fragment(incoming)
    assert conflict is not None
    surviving = repo.get_fragment("docfrag.x")
    assert surviving.title == "Human authored"


def test_pipeline_status_endpoint(payments_yaml: Path) -> None:
    """Smoke test: a queued/failed status is recorded for a bad URL."""
    from nexusdocs.ingestion.pipeline import IngestionPipeline

    repo = InMemoryGraphRepository()
    repo.initialize()
    pipeline = IngestionPipeline(repo, llm=DeterministicMockClient())
    job = pipeline.submit_repository(repo_url="not-a-real-repo://nope", branch="main")
    status = pipeline.status(job.job_id)
    assert status is not None
    assert status.status.value in {"queued", "in_progress", "succeeded", "failed"}
