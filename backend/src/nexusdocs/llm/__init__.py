"""LLM client Protocol and implementations."""

from .client import (
    AssemblyRequest,
    AssemblyResponse,
    EntityExtractionResult,
    ExtractedEntity,
    ExtractedFragment,
    ExtractedRelationship,
    ExtractionRequest,
    FragmentExtractionResult,
    LLMClient,
    RelationshipExtractionResult,
    build_default_client,
)
from .mock import DeterministicMockClient

__all__ = [
    "AssemblyRequest",
    "AssemblyResponse",
    "DeterministicMockClient",
    "EntityExtractionResult",
    "ExtractedEntity",
    "ExtractedFragment",
    "ExtractedRelationship",
    "ExtractionRequest",
    "FragmentExtractionResult",
    "LLMClient",
    "RelationshipExtractionResult",
    "build_default_client",
]
