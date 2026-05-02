"""Markdown / free-text connector.

Takes a blob of text + optional title/source URL and:

1. Stores the **whole document** as a parent ``DocFragment`` so the original
   prose stays intact and citable (zoom 0-60, lens "source"). This becomes
   the *parent* the user asks for - fragments below are derived breakdowns
   of it.
2. Runs the LLM extractor (or the deterministic mock when no LLM is
   configured) to derive entities, relationships and child fragments.
3. Returns an :class:`IngestionReport` with counts.
"""

import hashlib
import re
from dataclasses import dataclass, field

from ...core import DocFragment, Entity, Kind, Relationship, RelationshipType
from ...core.enums import GeneratedBy, Mode, Protocol, SourceType
from ...core.fragment import Coverage
from ...core.provenance import Provenance, SourceRef
from ...llm.client import ExtractionRequest, LLMClient
from ..conflict import ConflictResolver
from .base import IngestionReport


@dataclass
class MarkdownIngestionResult(IngestionReport):
    parent_fragment_id: str | None = None
    derived_entity_ids: list[str] = field(default_factory=list)
    derived_relationship_ids: list[str] = field(default_factory=list)
    derived_fragment_ids: list[str] = field(default_factory=list)


_SLUG_RE = re.compile(r"[^a-z0-9._-]+")


def slugify(text: str, *, max_len: int = 32) -> str:
    text = text.strip().lower()
    text = _SLUG_RE.sub("-", text)
    text = text.strip("-._")
    return (text or "doc")[:max_len]


# Map the semantic name we expose to the API ("markdown", "jira", ...) to the
# closest SourceType enum value the data model understands.
_SOURCE_TYPE_MAP: dict[str, SourceType] = {
    "markdown": SourceType.manual,
    "manual": SourceType.manual,
    "confluence": SourceType.confluence,
    "jira": SourceType.ticket,
    "readme": SourceType.readme,
    "adr": SourceType.adr,
    "runbook": SourceType.runbook,
}


def resolve_source_type(name: str) -> SourceType:
    return _SOURCE_TYPE_MAP.get(name, SourceType.manual)


class MarkdownConnector:
    """Reusable text-ingestion entry point.

    The same logic is invoked by the Git connector (per file) and by the
    REST endpoint that accepts pasted markdown directly from the UI.
    """

    def __init__(
        self,
        llm: LLMClient,
        resolver: ConflictResolver,
        *,
        source_type: str = "markdown",
    ) -> None:
        self.llm = llm
        self.resolver = resolver
        self.source_type_label = source_type
        self.source_type = resolve_source_type(source_type)

    def ingest(
        self,
        text: str,
        *,
        title: str | None = None,
        source_path: str | None = None,
        lenses: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> MarkdownIngestionResult:
        report = MarkdownIngestionResult()
        if not text.strip():
            report.errors.append("empty document")
            return report

        title = (title or self._guess_title(text) or "Untitled document").strip()
        source_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
        slug = slugify(title) or source_hash[:8]
        # Make sure the doc id is unique-ish per source content so re-ingesting
        # the same text reuses the same parent fragment.
        doc_id = f"docfrag.doc-{slug}-{source_hash[:8]}"

        provenance_kwargs = {
            "source_type": self.source_type,
            "source_path": source_path,
            "source_hash": source_hash,
            "generated_by": (
                GeneratedBy.human
                if self.source_type_label == "markdown"
                else GeneratedBy.hybrid
            ),
            "confidence": 1.0,
            "reviewed": True,
        }
        source_ref = SourceRef(
            source_type=self.source_type,
            source_path=source_path,
            source_hash=source_hash,
        )

        # ─── 1. Parent fragment (the whole document) ─────────────────────
        try:
            parent = DocFragment(
                id=doc_id,
                title=title,
                body=text.strip(),
                tags=list(tags or ["source", self.source_type_label]),
                coverage=Coverage(
                    zoom_min=0,
                    zoom_max=60,
                    lenses=list(lenses or ["technical", "onboarding"]),
                ),
                provenance=Provenance(**provenance_kwargs),
            )
            conflict = self.resolver.upsert_fragment(parent)
            if conflict:
                report.held_conflicts.append(conflict.__dict__)
            else:
                report.fragments_created += 1
                report.parent_fragment_id = parent.id
                report.derived_fragment_ids.append(parent.id)
        except Exception as exc:  # validation, repository errors
            report.errors.append(f"parent fragment: {exc}")
            return report

        # ─── 2. LLM-driven extraction ────────────────────────────────────
        request = ExtractionRequest(text=text, source_path=source_path)

        # Entities
        extracted_entities: list[Entity] = []
        try:
            for e in self.llm.extract_entities(request).entities:
                try:
                    kind = Kind(e.kind)
                except ValueError:
                    report.errors.append(f"unknown kind {e.kind!r}")
                    continue
                eid = slugify(e.suggested_id) if e.suggested_id else None
                if not eid:
                    report.errors.append("entity missing suggested_id")
                    continue
                entity = Entity(
                    id=eid,
                    kind=kind,
                    name=e.name,
                    source=source_ref,
                )
                preexisting = self.resolver.repo.has_entity(entity.id)
                conflict = self.resolver.upsert_entity(entity)
                if conflict:
                    report.held_conflicts.append(conflict.__dict__)
                    continue
                if preexisting:
                    report.entities_updated += 1
                else:
                    report.entities_created += 1
                report.derived_entity_ids.append(entity.id)
                extracted_entities.append(entity)
        except Exception as exc:
            report.errors.append(f"entity extraction: {exc}")

        # Relationships
        extracted_relationships: list[Relationship] = []
        try:
            for r in self.llm.extract_relationships(
                request, extracted_entities
            ).relationships:
                try:
                    rel_type = RelationshipType(r.type)
                except ValueError:
                    report.errors.append(f"unknown relationship type {r.type!r}")
                    continue
                proto: Protocol | str | None = None
                if r.protocol:
                    try:
                        proto = Protocol(r.protocol)
                    except ValueError:
                        proto = r.protocol
                mode = Mode(r.mode) if r.mode else None
                rid = f"rel.{slugify(r.source_id)}-{r.type}-{slugify(r.target_id)}"
                relationship = Relationship(
                    id=rid,
                    source=r.source_id,
                    target=r.target_id,
                    type=rel_type,
                    protocol=proto,
                    mode=mode,
                    source_ref=source_ref,
                )
                conflict = self.resolver.upsert_relationship(relationship)
                if conflict:
                    report.held_conflicts.append(conflict.__dict__)
                    continue
                report.relationships_created += 1
                report.derived_relationship_ids.append(relationship.id)
                extracted_relationships.append(relationship)
        except Exception as exc:
            report.errors.append(f"relationship extraction: {exc}")

        # Child fragments
        try:
            for f in self.llm.extract_fragments(
                request, extracted_entities, extracted_relationships
            ).fragments:
                try:
                    fid_seed = (f.title + f.body).encode("utf-8")
                    fid = f"docfrag.frag-{slug}-{hashlib.sha1(fid_seed).hexdigest()[:6]}"
                    child = DocFragment(
                        id=fid,
                        doc_id=doc_id,
                        title=f.title,
                        body=f.body,
                        subjects=[{"entity": s} for s in f.subjects if s],
                        tags=list(f.tags or []) or ["extracted"],
                        coverage=Coverage(
                            zoom_min=f.zoom_min,
                            zoom_max=f.zoom_max,
                            lenses=list(f.lenses or ["technical"]),
                        ),
                        provenance=Provenance(
                            source_type=self.source_type,
                            source_path=source_path,
                            source_hash=source_hash,
                            generated_by=GeneratedBy.llm,
                            confidence=f.confidence,
                            reviewed=False,
                        ),
                    )
                    conflict = self.resolver.upsert_fragment(child)
                    if conflict:
                        report.held_conflicts.append(conflict.__dict__)
                        continue
                    report.fragments_created += 1
                    report.derived_fragment_ids.append(child.id)
                except Exception as exc:
                    report.errors.append(f"fragment: {exc}")
        except Exception as exc:
            report.errors.append(f"fragment extraction: {exc}")

        report.documents_processed += 1
        return report

    # ---- helpers --------------------------------------------------------

    @staticmethod
    def _guess_title(text: str) -> str | None:
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            line = line.lstrip("#").strip()
            return line[:120]
        return None
