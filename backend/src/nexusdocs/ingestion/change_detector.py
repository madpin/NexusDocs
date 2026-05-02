"""Source-hash change detection.

Tracks the last seen `source_hash` per `source_path`. The connector skips a
file when the hash hasn't changed since the previous ingestion.
"""

from dataclasses import dataclass, field


@dataclass
class ChangeDetector:
    seen: dict[str, str] = field(default_factory=dict)

    def changed(self, source_path: str, source_hash: str) -> bool:
        prior = self.seen.get(source_path)
        if prior == source_hash:
            return False
        self.seen[source_path] = source_hash
        return True

    def reset(self) -> None:
        self.seen.clear()
