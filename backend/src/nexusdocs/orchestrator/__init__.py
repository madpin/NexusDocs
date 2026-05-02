"""Orchestrator — shared API + CLI entry points.

Every API route and every CLI command goes through one of these functions
so that the two surfaces stay in lockstep.
"""

from .definitions import apply_yaml, apply_yaml_text
from .ingest import (
    IngestionStatus,
    get_ingestion_status,
    ingest_confluence,
    ingest_jira,
    ingest_markdown,
    ingest_repository,
    list_jobs,
)
from .search import search_graph
from .views import render_view

__all__ = [
    "IngestionStatus",
    "apply_yaml",
    "apply_yaml_text",
    "get_ingestion_status",
    "ingest_confluence",
    "ingest_jira",
    "ingest_markdown",
    "ingest_repository",
    "list_jobs",
    "render_view",
    "search_graph",
]
