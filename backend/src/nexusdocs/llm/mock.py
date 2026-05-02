"""Deterministic mock LLM client.

Output is keyed off the input hash so tests are reproducible. The mock is
not "smart" — it stitches together fragment bodies into a narrative and
emits a Mermaid diagram derived from the supplied entities.
"""

import hashlib
import re
import textwrap

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

_SAFE_ID = re.compile(r"[^a-z0-9._\-]")


def _slug(text: str) -> str:
    s = text.lower()
    s = _SAFE_ID.sub("-", s).strip(".-")
    return s or "extracted"


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


class DeterministicMockClient:
    """Deterministic LLM stand-in for tests and offline development."""

    # ---- Extraction --------------------------------------------------------

    def extract_entities(self, request: ExtractionRequest) -> EntityExtractionResult:
        entities: list[ExtractedEntity] = []
        text = request.text
        # Heuristic: lines like `service: foo` or `# Service: foo`.
        for kind in ["service", "system", "component", "database", "kafka_cluster"]:
            for m in re.finditer(rf"\b{kind}[s]?\b[:\-]\s*([A-Za-z0-9._\-]+)", text):
                name = m.group(1)
                entities.append(
                    ExtractedEntity(
                        suggested_id=f"{kind}.{_slug(name)}",
                        kind=kind,
                        name=name,
                        confidence=0.65,
                        rationale=f"matched literal pattern in {request.source_path or 'input'}",
                    )
                )
        return EntityExtractionResult(entities=entities)

    def extract_relationships(self, request, known_entities):
        rels: list[ExtractedRelationship] = []
        {e.id for e in known_entities}
        {e.name.lower(): e.id for e in known_entities}
        text = request.text.lower()
        for src in known_entities:
            for tgt in known_entities:
                if src.id == tgt.id:
                    continue
                # Naive: if both names appear in the same line, propose a `references`.
                pat = re.compile(
                    rf"^.*\b{re.escape(src.name.lower())}\b.*\b{re.escape(tgt.name.lower())}\b.*$",
                    re.MULTILINE,
                )
                if pat.search(text):
                    rels.append(
                        ExtractedRelationship(
                            source_id=src.id,
                            target_id=tgt.id,
                            type="references",
                            confidence=0.4,
                            rationale="co-mention in source",
                        )
                    )
        # de-dupe
        seen: set[tuple[str, str, str]] = set()
        unique: list[ExtractedRelationship] = []
        for r in rels:
            key = (r.source_id, r.target_id, r.type)
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return RelationshipExtractionResult(relationships=unique)

    def extract_fragments(self, request, known_entities, known_relationships):
        # Naive: split text into ~3-line "fragments". Anchor each to the entity whose name appears.
        out: list[ExtractedFragment] = []
        chunks = [c.strip() for c in re.split(r"\n\s*\n", request.text) if c.strip()]
        for chunk in chunks[:5]:
            anchored = [e.id for e in known_entities if e.name.lower() in chunk.lower()]
            if not anchored:
                continue
            title = chunk.splitlines()[0][:80]
            out.append(
                ExtractedFragment(
                    title=title,
                    body=chunk,
                    subjects=anchored,
                    confidence=0.6,
                    lenses=["technical"],
                )
            )
        return FragmentExtractionResult(fragments=out)

    # ---- Assembly ----------------------------------------------------------

    def assemble_view(self, request: AssemblyRequest) -> AssemblyResponse:
        focus_id = request.request.focus
        zoom = request.request.zoom
        lenses = ", ".join(request.request.lenses)

        if not request.fragments:
            summary = (
                f"No documentation fragments matched the active lenses "
                f"({lenses}) at zoom={zoom}. Showing structural overview only."
            )
        else:
            lines = [
                f"## View — {focus_id} (zoom {zoom}, lenses: {lenses})",
                "",
                f"This view spans {len(request.entities)} entities and "
                f"{len(request.relationships)} relationships.",
            ]
            if request.most_central:
                lines.append(
                    f"Most central in the viewport: `{request.most_central}`."
                )
            if request.structural_concerns:
                lines.append(
                    "Structural concerns (high betweenness): "
                    + ", ".join(f"`{c}`" for c in request.structural_concerns)
                    + "."
                )

            lines.append("")
            for f in request.fragments:
                excerpt = textwrap.shorten(f.body.replace("\n", " "), width=240)
                lines.append(f"- **{f.title}** [{f.id}]: {excerpt}")
            summary = "\n".join(lines)

        diagram = self._mermaid(request)
        follow_ups = self._follow_ups(request)
        cited_ids = [f.id for f in request.fragments]
        return AssemblyResponse(
            summary=summary,
            diagram=diagram,
            follow_up_suggestions=follow_ups,
            cited_fragment_ids=cited_ids,
        )

    @staticmethod
    def _mermaid(request: AssemblyRequest) -> str:
        if not request.entities:
            return "graph LR\n  empty[No entities in viewport]"
        lines = ["graph LR"]
        node_aliases: dict[str, str] = {}
        for i, e in enumerate(request.entities[:30]):
            alias = f"n{i}"
            node_aliases[e.id] = alias
            label = e.name.replace('"', "'")
            lines.append(f'  {alias}["{label}"]')
        for r in request.relationships[:60]:
            sa = node_aliases.get(r.source)
            ta = node_aliases.get(r.target)
            if sa and ta:
                edge_label = r.type.value
                if r.protocol:
                    edge_label += f"/{r.protocol}"
                lines.append(f"  {sa} -->|{edge_label}| {ta}")
        return "\n".join(lines)

    @staticmethod
    def _follow_ups(request: AssemblyRequest) -> list[str]:
        focus_id = request.request.focus
        zoom = request.request.zoom
        out: list[str] = []
        if zoom < 80:
            out.append(f"Zoom to 80 for code-level details on `{focus_id}`.")
        if zoom > 30:
            out.append("Zoom out to 25 for a team/system-level overview.")
        if request.most_central and request.most_central != focus_id:
            out.append(f"Re-focus on `{request.most_central}` to explore its neighborhood.")
        return out
