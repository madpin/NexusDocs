"""Step 5 — deduplication and ranking by the 5-key tuple."""

from datetime import UTC, datetime

from ..core import ViewRequest
from .lifting import FilteredFragment


def _zoom_proximity(filtered: FilteredFragment, request: ViewRequest) -> float:
    midpoint = (filtered.effective_zoom_min + filtered.fragment.coverage.zoom_max) / 2.0
    return abs(request.zoom - midpoint)


def _lens_specificity(filtered: FilteredFragment, request: ViewRequest) -> float:
    """Lower = more specific. We approximate as |fragment_lenses| / |intersection|."""
    overlap = set(filtered.fragment.coverage.lenses) & set(request.lenses)
    if not overlap:
        return 1e9
    return len(filtered.fragment.coverage.lenses) / len(overlap)


def _confidence(filtered: FilteredFragment) -> float:
    return -filtered.fragment.provenance.confidence  # negative for ascending sort


def _reviewed(filtered: FilteredFragment) -> int:
    return 0 if filtered.fragment.provenance.reviewed else 1


def _freshness(filtered: FilteredFragment) -> float:
    last = filtered.fragment.provenance.last_synced
    if last is None:
        return 0.0
    return -(last - datetime(1970, 1, 1, tzinfo=UTC)).total_seconds()


def rank(
    survivors: list[FilteredFragment], request: ViewRequest
) -> list[FilteredFragment]:
    """Sort survivors by the 5-key tuple from docs/framework/view-engine.md Step 5."""
    seen: dict[str, FilteredFragment] = {}
    for f in survivors:
        existing = seen.get(f.fragment.id)
        if existing is None or f.effective_zoom_min < existing.effective_zoom_min:
            seen[f.fragment.id] = f

    return sorted(
        seen.values(),
        key=lambda f: (
            _zoom_proximity(f, request),
            _lens_specificity(f, request),
            _confidence(f),
            _reviewed(f),
            _freshness(f),
        ),
    )
