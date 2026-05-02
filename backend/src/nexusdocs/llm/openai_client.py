"""OpenAI-backed `LLMClient` using structured (JSON-schema-constrained) outputs.

If the OpenAI API call fails for any reason, the client logs and returns an
empty result — the engine then falls back to deterministic rendering.
"""

import json
import logging
import os
from typing import Any

from .client import (
    AssemblyRequest,
    AssemblyResponse,
    EntityExtractionResult,
    ExtractedEntity,
    ExtractedFragment,
    ExtractedRelationship,
    ExtractionRequest,
    FragmentExtractionResult,
    RelationshipExtractionResult,
)
from .prompts import load_prompt

log = logging.getLogger(__name__)


# JSON schemas constraining the structured output for each prompt.
ENTITY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["suggested_id", "kind", "name", "confidence", "rationale"],
                "properties": {
                    "suggested_id": {"type": "string"},
                    "kind": {"type": "string"},
                    "name": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string"},
                },
            },
        }
    },
    "required": ["entities"],
}


RELATIONSHIP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source_id", "target_id", "type", "confidence", "rationale"],
                "properties": {
                    "source_id": {"type": "string"},
                    "target_id": {"type": "string"},
                    "type": {"type": "string"},
                    "protocol": {"type": ["string", "null"]},
                    "mode": {"type": ["string", "null"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string"},
                },
            },
        }
    },
    "required": ["relationships"],
}


FRAGMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "fragments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "title",
                    "body",
                    "subjects",
                    "tags",
                    "zoom_min",
                    "zoom_max",
                    "lenses",
                    "confidence",
                ],
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "subjects": {"type": "array", "items": {"type": "string"}},
                    "relations": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "zoom_min": {"type": "integer", "minimum": 0, "maximum": 100},
                    "zoom_max": {"type": "integer", "minimum": 0, "maximum": 100},
                    "lenses": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
    "required": ["fragments"],
}


ASSEMBLY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "diagram", "follow_up_suggestions"],
    "properties": {
        "summary": {"type": "string"},
        "diagram": {"type": "string"},
        "follow_up_suggestions": {"type": "array", "items": {"type": "string"}},
    },
}


class OpenAIClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "openai package not installed. `pip install openai` or remove OPENAI_API_KEY."
            ) from e
        # base_url is optional — when None the SDK uses the official endpoint.
        # OpenAI-compatible providers (Azure, Ollama, vLLM, LM Studio, etc.)
        # can be reached by setting NEXUSDOCS_OPENAI_BASE_URL or OPENAI_BASE_URL.
        resolved_base_url = (
            base_url
            or os.getenv("NEXUSDOCS_OPENAI_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
        )
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        # Self-hosted endpoints (Ollama, vLLM, LM Studio, …) usually do not
        # require auth, but the OpenAI SDK still demands a non-empty api_key.
        # When the user only configures a base URL, pass a harmless sentinel.
        if not resolved_api_key and resolved_base_url:
            resolved_api_key = "sk-no-key-required"
        client_kwargs: dict[str, str] = {}
        if resolved_api_key:
            client_kwargs["api_key"] = resolved_api_key
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        self._client = OpenAI(**client_kwargs)
        self.model = model or os.getenv("NEXUSDOCS_OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = resolved_base_url

    # ---- Helpers ----------------------------------------------------------

    def _structured_call(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        schema_name: str,
    ) -> dict[str, Any]:
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    },
                },
                temperature=0.0,
            )
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as e:
            log.warning("OpenAI call failed (%s): %s", schema_name, e)
            return {}

    # ---- Extraction prompts -----------------------------------------------

    def extract_entities(self, request: ExtractionRequest) -> EntityExtractionResult:
        prompt = load_prompt("extract_entities").format(
            source_path=request.source_path or "<unknown>",
            text=request.text[:6000],
        )
        data = self._structured_call(
            prompt, schema=ENTITY_SCHEMA, schema_name="entity_extraction"
        )
        return EntityExtractionResult(
            entities=[ExtractedEntity(**e) for e in data.get("entities", [])]
        )

    def extract_relationships(
        self, request: ExtractionRequest, known_entities
    ) -> RelationshipExtractionResult:
        prompt = load_prompt("extract_relationships").format(
            source_path=request.source_path or "<unknown>",
            known_entities_json=json.dumps(
                [{"id": e.id, "kind": e.kind.value, "name": e.name} for e in known_entities]
            ),
            text=request.text[:6000],
        )
        data = self._structured_call(
            prompt, schema=RELATIONSHIP_SCHEMA, schema_name="relationship_extraction"
        )
        rels = [
            ExtractedRelationship(**{k: v for k, v in r.items()})
            for r in data.get("relationships", [])
        ]
        return RelationshipExtractionResult(relationships=rels)

    def extract_fragments(
        self, request: ExtractionRequest, known_entities, known_relationships
    ) -> FragmentExtractionResult:
        prompt = load_prompt("extract_fragments").format(
            source_path=request.source_path or "<unknown>",
            known_entities_json=json.dumps(
                [{"id": e.id, "name": e.name} for e in known_entities]
            ),
            known_relationships_json=json.dumps(
                [{"id": r.id, "type": r.type.value} for r in known_relationships]
            ),
            text=request.text[:6000],
        )
        data = self._structured_call(
            prompt, schema=FRAGMENT_SCHEMA, schema_name="fragment_extraction"
        )
        frags = [ExtractedFragment(**f) for f in data.get("fragments", [])]
        return FragmentExtractionResult(fragments=frags)

    # ---- Assembly --------------------------------------------------------

    def assemble_view(self, request: AssemblyRequest) -> AssemblyResponse:
        entities_block = "\n".join(
            f"- {e.id} : {e.kind.value} : {e.name}" for e in request.entities
        )
        relationships_block = "\n".join(
            f"- {r.id} : {r.type.value} : {r.source} -> {r.target}"
            for r in request.relationships
        )
        fragments_block = "\n".join(
            f"- {f.id} : {f.title} : {f.provenance.confidence:.2f} : "
            f"{'reviewed' if f.provenance.reviewed else 'unreviewed'}"
            for f in request.fragments
        )
        bodies_block = "\n\n".join(
            f"[{f.id}] {f.title}\n{f.body}" for f in request.fragments
        )

        prompt = load_prompt("assemble_view").format(
            focus=request.request.focus,
            zoom=request.request.zoom,
            lenses=", ".join(request.request.lenses),
            navigation_path=", ".join(request.request.navigation_path)
            or "<empty>",
            topology_summary=request.topology_summary,
            entities_block=entities_block or "(empty)",
            relationships_block=relationships_block or "(empty)",
            fragments_block=fragments_block or "(empty)",
            fragment_bodies_block=bodies_block or "(none)",
        )
        data = self._structured_call(
            prompt, schema=ASSEMBLY_SCHEMA, schema_name="view_assembly"
        )
        if not data:
            # Deterministic fallback when the LLM is unavailable.
            from .mock import DeterministicMockClient

            return DeterministicMockClient().assemble_view(request)

        return AssemblyResponse(
            summary=data.get("summary", ""),
            diagram=data.get("diagram", ""),
            follow_up_suggestions=data.get("follow_up_suggestions", []),
            cited_fragment_ids=[f.id for f in request.fragments],
        )
