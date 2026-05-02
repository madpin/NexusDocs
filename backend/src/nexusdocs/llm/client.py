"""LLMClient protocol — extraction (3 prompts) + assembly (1 prompt)."""

import os
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..core import (
    DocFragment,
    Entity,
    Relationship,
    ViewRequest,
)

# ---------- Extraction inputs/outputs ----------------------------------------


@dataclass
class ExtractionRequest:
    """A blob of text for the extractor to consume (e.g. a README)."""

    text: str
    source_path: str | None = None
    hint_kinds: list[str] = field(default_factory=list)


@dataclass
class ExtractedEntity:
    suggested_id: str
    kind: str
    name: str
    confidence: float
    rationale: str = ""


@dataclass
class ExtractedRelationship:
    source_id: str
    target_id: str
    type: str
    protocol: str | None = None
    mode: str | None = None
    confidence: float = 0.0
    rationale: str = ""


@dataclass
class ExtractedFragment:
    title: str
    body: str
    subjects: list[str] = field(default_factory=list)
    relations: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    zoom_min: int = 30
    zoom_max: int = 70
    lenses: list[str] = field(default_factory=lambda: ["technical"])
    confidence: float = 0.5


@dataclass
class EntityExtractionResult:
    entities: list[ExtractedEntity] = field(default_factory=list)


@dataclass
class RelationshipExtractionResult:
    relationships: list[ExtractedRelationship] = field(default_factory=list)


@dataclass
class FragmentExtractionResult:
    fragments: list[ExtractedFragment] = field(default_factory=list)


# ---------- Assembly inputs/outputs ------------------------------------------


@dataclass
class AssemblyRequest:
    """Everything the LLM needs to write a narrative summary."""

    request: ViewRequest
    entities: list[Entity]
    relationships: list[Relationship]
    fragments: list[DocFragment]
    topology_summary: str
    structural_concerns: list[str] = field(default_factory=list)
    most_central: str | None = None


@dataclass
class AssemblyResponse:
    summary: str
    diagram: str
    follow_up_suggestions: list[str] = field(default_factory=list)
    cited_fragment_ids: list[str] = field(default_factory=list)


# ---------- Protocol ---------------------------------------------------------


@runtime_checkable
class LLMClient(Protocol):
    """Contract for the four prompts described in docs/framework/llm-integration.md."""

    def extract_entities(
        self, request: ExtractionRequest
    ) -> EntityExtractionResult: ...

    def extract_relationships(
        self,
        request: ExtractionRequest,
        known_entities: list[Entity],
    ) -> RelationshipExtractionResult: ...

    def extract_fragments(
        self,
        request: ExtractionRequest,
        known_entities: list[Entity],
        known_relationships: list[Relationship],
    ) -> FragmentExtractionResult: ...

    def assemble_view(self, request: AssemblyRequest) -> AssemblyResponse: ...


def build_default_client() -> LLMClient:
    """Return an OpenAI-backed client if an OpenAI-compatible target is configured,
    otherwise a deterministic mock.

    A custom base URL alone (e.g. a local Ollama / LM Studio endpoint) is enough
    to switch on the real client — many self-hosted providers do not require a
    real API key.
    """
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    has_base_url = bool(
        os.getenv("OPENAI_BASE_URL") or os.getenv("NEXUSDOCS_OPENAI_BASE_URL")
    )
    if has_key or has_base_url:
        from .openai_client import OpenAIClient

        return OpenAIClient()
    from .mock import DeterministicMockClient

    return DeterministicMockClient()


def filter_citations(text: str, allowed_ids: set[str]) -> tuple[str, list[str]]:
    """Drop any [fragment_id] citation that is not in the allowed set."""
    import re

    pattern = re.compile(r"\[([a-z][a-z0-9._\-]*)\]")
    cited: list[str] = []

    def repl(match: "re.Match[str]") -> str:
        fid = match.group(1)
        if fid in allowed_ids:
            cited.append(fid)
            return match.group(0)
        return ""

    cleaned = pattern.sub(repl, text)
    cleaned = re.sub(r" {2,}", " ", cleaned).strip()
    return cleaned, list(dict.fromkeys(cited))
