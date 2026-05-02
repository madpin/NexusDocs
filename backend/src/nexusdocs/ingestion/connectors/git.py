"""Git connector — clones a repo, walks for README/config files, runs the extractor."""

import hashlib
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

from ...core import DocFragment, Entity
from ...core.enums import GeneratedBy
from ...core.fragment import Coverage
from ...core.provenance import Provenance, SourceRef
from ...llm.client import ExtractionRequest, LLMClient
from ..conflict import ConflictResolver
from .base import IngestionReport

WALK_PATTERNS = ("README", "readme", ".md", "docker-compose.yml", "k8s", "openapi", ".proto")


class GitConnector:
    """Clones a repo with GitPython, then drives the extractor."""

    def __init__(self, llm: LLMClient, resolver: ConflictResolver) -> None:
        self.llm = llm
        self.resolver = resolver

    # ---- Public --------------------------------------------------------

    def ingest(self, *, repo_url: str, branch: str = "main") -> IngestionReport:
        report = IngestionReport()
        try:
            from git import Repo
        except ImportError as e:
            report.errors.append(f"GitPython not installed: {e}")
            return report

        with tempfile.TemporaryDirectory() as tmp:
            try:
                Repo.clone_from(repo_url, tmp, branch=branch, depth=1)
            except Exception as e:
                report.errors.append(f"clone failed: {e}")
                return report

            for path in self._walk(Path(tmp)):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    report.errors.append(f"{path}: {e}")
                    continue
                source_path = f"{repo_url}@{branch}/{path.relative_to(tmp)}"
                source_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
                self._ingest_text(
                    text,
                    source_path=source_path,
                    source_hash=source_hash,
                    report=report,
                )
        return report

    # ---- Internals -----------------------------------------------------

    @staticmethod
    def _walk(root: Path) -> Iterable[Path]:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                full = Path(dirpath) / name
                if any(p in name for p in WALK_PATTERNS):
                    yield full

    def _ingest_text(
        self,
        text: str,
        *,
        source_path: str,
        source_hash: str,
        report: IngestionReport,
    ) -> None:
        request = ExtractionRequest(text=text, source_path=source_path)

        # 1. Entities
        ents = self.llm.extract_entities(request).entities
        existing_entities: list[Entity] = []
        for e in ents:
            from ...core import Entity as EntityModel
            from ...core import Kind

            try:
                kind = Kind(e.kind)
            except ValueError:
                report.errors.append(f"unknown kind {e.kind} from extractor")
                continue
            entity = EntityModel(
                id=e.suggested_id,
                kind=kind,
                name=e.name,
                source=SourceRef(
                    source_type="readme",
                    source_path=source_path,
                    source_hash=source_hash,
                ),
            )
            try:
                preexisting = self.resolver.repo.has_entity(entity.id)
                conflict = self.resolver.upsert_entity(entity)
                if conflict:
                    report.held_conflicts.append(conflict.__dict__)
                    continue
                if preexisting:
                    report.entities_updated += 1
                else:
                    report.entities_created += 1
                existing_entities.append(entity)
            except Exception as exc:
                report.errors.append(f"entity {entity.id}: {exc}")

        # 2. Relationships
        rels = self.llm.extract_relationships(request, existing_entities).relationships
        for r in rels:
            from ...core import RelationshipType
            from ...core.enums import Mode, Protocol
            from ...core.relationship import Relationship as RelModel

            try:
                rel_type = RelationshipType(r.type)
            except ValueError:
                report.errors.append(f"unknown relationship type {r.type}")
                continue
            try:
                proto: Protocol | str | None = None
                if r.protocol:
                    try:
                        proto = Protocol(r.protocol)
                    except ValueError:
                        proto = r.protocol
                mode = Mode(r.mode) if r.mode else None
                rid = "rel.{}-{}-{}".format(
                    r.source_id.replace(".", "-"),
                    r.type,
                    r.target_id.replace(".", "-"),
                )
                relationship = RelModel(
                    id=rid,
                    source=r.source_id,
                    target=r.target_id,
                    type=rel_type,
                    protocol=proto,
                    mode=mode,
                    source_ref=SourceRef(
                        source_type="readme",
                        source_path=source_path,
                        source_hash=source_hash,
                    ),
                )
                conflict = self.resolver.upsert_relationship(relationship)
                if conflict:
                    report.held_conflicts.append(conflict.__dict__)
                    continue
                report.relationships_created += 1
            except Exception as exc:
                report.errors.append(f"relationship {r.source_id}->{r.target_id}: {exc}")

        # 3. Fragments
        frags = self.llm.extract_fragments(request, existing_entities, []).fragments
        for f in frags:
            try:
                fid = "docfrag." + hashlib.sha1((f.title + f.body).encode()).hexdigest()[:8]
                fragment = DocFragment(
                    id=fid,
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
                        source_type="readme",
                        source_path=source_path,
                        source_hash=source_hash,
                        generated_by=GeneratedBy.llm,
                        confidence=f.confidence,
                        reviewed=False,
                    ),
                )
                conflict = self.resolver.upsert_fragment(fragment)
                if conflict:
                    report.held_conflicts.append(conflict.__dict__)
                    continue
                report.fragments_created += 1
            except Exception as exc:
                report.errors.append(f"fragment for {source_path}: {exc}")

        report.documents_processed += 1
