"""Step 3 — fragment collection from subjects, relations, and tags."""

from ..core import DocFragment
from ..graph.repository import GraphRepository
from .subgraph import Viewport


def collect_candidates(repo: GraphRepository, viewport: Viewport) -> list[DocFragment]:
    """Gather candidate fragments anchored to the viewport.

    A fragment may be reached more than once via different anchors; we keep
    only one copy here and let step 5 finalise dedup-and-rank.
    """
    seen: dict[str, DocFragment] = {}

    for entity in viewport.entities.values():
        for f in repo.fragments_by_subject(entity.id):
            seen[f.id] = f
        for label in entity.labels:
            for f in repo.fragments_by_tag(label):
                seen[f.id] = f

    for rel in viewport.relationships.values():
        for f in repo.fragments_by_relation(rel.id):
            seen[f.id] = f

    return list(seen.values())
