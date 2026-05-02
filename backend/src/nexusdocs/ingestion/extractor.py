"""Drive the three extraction prompts and turn results into core models."""

import hashlib
from dataclasses import dataclass, field

from ..core import (
    DocFragment,
    Entity,
    Kind,
    Mode,
    Protocol,
    Relationship,
    RelationshipType,
)
from ..core.enums import GeneratedBy
from ..core.fragment import Coverage
from ..core.provenance import Provenance, SourceRef
from ..llm.client import ExtractionRequest, LLMClient


@dataclass
class ExtractionOutput:
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    fragments: list[DocFragment] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _safe_relationship_id(src: str, type_: str, tgt: str) -> str:
    return f"rel.{src.replace('.', '-')}-{type_}-{tgt.replace('.', '-')}"


def _coerce_protocol(value: str | None) -> Protocol | str | None:
    if not value:
        return None
    try:
        return Protocol(value)
    except ValueError:
        return value


def _coerce_mode(value: str | None) -> Mode | None:
    if not value:
        return None
    try:
        return Mode(value)
    except ValueError:
        return None


def extract(
    *,
    text: str,
    source_path: str,
    source_hash: str | None = None,
    llm: LLMClient,
) -> ExtractionOutput:
    """Run the 3 extraction prompts and yield core domain objects."""
    out = ExtractionOutput()
    request = ExtractionRequest(text=text, source_path=source_path)
    src_hash = source_hash or hashlib.sha1(text.encode("utf-8")).hexdigest()
    src = SourceRef(
        source_type="readme",
        source_path=source_path,
        source_hash=src_hash,
    )

    # Entities
    entity_result = llm.extract_entities(request)
    for e in entity_result.entities:
        try:
            kind = Kind(e.kind)
        except ValueError:
            out.errors.append(f"unknown kind {e.kind!r}")
            continue
        try:
            out.entities.append(
                Entity(
                    id=e.suggested_id,
                    kind=kind,
                    name=e.name,
                    source=src,
                )
            )
        except Exception as exc:
            out.errors.append(f"entity {e.suggested_id!r}: {exc}")

    # Relationships
    rel_result = llm.extract_relationships(request, out.entities)
    for r in rel_result.relationships:
        try:
            rt = RelationshipType(r.type)
        except ValueError:
            out.errors.append(f"unknown relationship type {r.type!r}")
            continue
        try:
            out.relationships.append(
                Relationship(
                    id=_safe_relationship_id(r.source_id, r.type, r.target_id),
                    source=r.source_id,
                    target=r.target_id,
                    type=rt,
                    protocol=_coerce_protocol(r.protocol),
                    mode=_coerce_mode(r.mode),
                    source_ref=src,
                )
            )
        except Exception as exc:
            out.errors.append(f"relationship {r.source_id}->{r.target_id}: {exc}")

    # Fragments
    frag_result = llm.extract_fragments(request, out.entities, out.relationships)
    for f in frag_result.fragments:
        try:
            fid = "docfrag." + hashlib.sha1((f.title + f.body).encode()).hexdigest()[:10]
            out.fragments.append(
                DocFragment(
                    id=fid,
                    title=f.title,
                    body=f.body,
                    subjects=[{"entity": s} for s in (f.subjects or []) if s],
                    relations=[{"rel": r} for r in (f.relations or []) if r],
                    tags=list(f.tags or []) or ["extracted"],
                    coverage=Coverage(
                        zoom_min=f.zoom_min,
                        zoom_max=f.zoom_max,
                        lenses=list(f.lenses or ["technical"]),
                    ),
                    provenance=Provenance(
                        source_type="readme",
                        source_path=source_path,
                        source_hash=src_hash,
                        generated_by=GeneratedBy.llm,
                        confidence=f.confidence,
                        reviewed=False,
                    ),
                )
            )
        except Exception as exc:
            out.errors.append(f"fragment {f.title!r}: {exc}")

    return out
