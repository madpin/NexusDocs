"""Apply YAML definitions through the repository."""

from pathlib import Path

from ..graph.repository import GraphRepository
from ..yaml import ApplyResult, apply_documents, load_documents


def apply_yaml(repo: GraphRepository, path: Path) -> ApplyResult:
    """Apply a YAML file (multi-doc) to the repository."""
    docs = load_documents(path)
    return apply_documents(repo, docs)


def apply_yaml_text(repo: GraphRepository, text: str) -> ApplyResult:
    """Apply a YAML string (multi-doc) to the repository."""
    docs = load_documents(text)
    return apply_documents(repo, docs)
