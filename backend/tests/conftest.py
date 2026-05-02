"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.yaml import apply_documents, load_documents

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def payments_yaml(fixtures_dir: Path) -> Path:
    return fixtures_dir / "payments-sample.yaml"


@pytest.fixture
def empty_repo() -> InMemoryGraphRepository:
    repo = InMemoryGraphRepository()
    repo.initialize()
    return repo


@pytest.fixture
def payments_repo(payments_yaml: Path) -> InMemoryGraphRepository:
    repo = InMemoryGraphRepository()
    repo.initialize()
    docs = load_documents(payments_yaml)
    result = apply_documents(repo, docs)
    assert result.ok(), f"failed to apply fixture: {result.errors}"
    return repo
