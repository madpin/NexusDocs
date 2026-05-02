"""Connector base class + report shape."""

from dataclasses import dataclass, field


@dataclass
class IngestionReport:
    documents_processed: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    relationships_created: int = 0
    fragments_created: int = 0
    errors: list[str] = field(default_factory=list)
    held_conflicts: list[dict] = field(default_factory=list)
