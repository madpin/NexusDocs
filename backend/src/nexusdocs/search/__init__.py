"""Search index — Protocol and an in-memory rapidfuzz-backed implementation."""

from .index import (
    EntityHit,
    FragmentHit,
    RelationshipHit,
    SearchHit,
    SearchIndex,
    SearchScope,
)
from .memory import InMemorySearchIndex

__all__ = [
    "EntityHit",
    "FragmentHit",
    "InMemorySearchIndex",
    "RelationshipHit",
    "SearchHit",
    "SearchIndex",
    "SearchScope",
]
