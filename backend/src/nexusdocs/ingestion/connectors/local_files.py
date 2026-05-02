"""Local-files connector — useful for tests and development."""

import hashlib
import os
from collections.abc import Iterable
from pathlib import Path

from ...llm.client import LLMClient
from ..change_detector import ChangeDetector
from ..conflict import ConflictResolver
from ..extractor import extract
from .base import IngestionReport
from .git import WALK_PATTERNS


class LocalFilesConnector:
    """Walk a local directory tree, run the extractor, route through the resolver."""

    def __init__(
        self,
        llm: LLMClient,
        resolver: ConflictResolver,
        detector: ChangeDetector | None = None,
    ) -> None:
        self.llm = llm
        self.resolver = resolver
        self.detector = detector or ChangeDetector()

    def ingest(self, root: Path) -> IngestionReport:
        report = IngestionReport()
        for path in self._walk(root):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                report.errors.append(f"{path}: {e}")
                continue
            source_path = str(path)
            source_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
            if not self.detector.changed(source_path, source_hash):
                continue

            output = extract(
                text=text,
                source_path=source_path,
                source_hash=source_hash,
                llm=self.llm,
            )
            report.errors.extend(output.errors)
            report.documents_processed += 1

            for entity in output.entities:
                pre = self.resolver.repo.has_entity(entity.id)
                conflict = self.resolver.upsert_entity(entity)
                if conflict:
                    report.held_conflicts.append(conflict.__dict__)
                    continue
                if pre:
                    report.entities_updated += 1
                else:
                    report.entities_created += 1

            for rel in output.relationships:
                try:
                    conflict = self.resolver.upsert_relationship(rel)
                    if conflict:
                        report.held_conflicts.append(conflict.__dict__)
                    else:
                        report.relationships_created += 1
                except Exception as e:
                    report.errors.append(f"relationship {rel.id}: {e}")

            for fragment in output.fragments:
                try:
                    conflict = self.resolver.upsert_fragment(fragment)
                    if conflict:
                        report.held_conflicts.append(conflict.__dict__)
                    else:
                        report.fragments_created += 1
                except Exception as e:
                    report.errors.append(f"fragment {fragment.id}: {e}")

        return report

    @staticmethod
    def _walk(root: Path) -> Iterable[Path]:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                full = Path(dirpath) / name
                if any(p in name for p in WALK_PATTERNS):
                    yield full
