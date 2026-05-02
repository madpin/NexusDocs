"""Step 4 — fragment filtering and zoom-min lifting."""

from dataclasses import dataclass

from ..core import DocFragment, ViewRequest
from .topology import ViewportTopology


@dataclass(frozen=True)
class FilteredFragment:
    fragment: DocFragment
    effective_zoom_min: int
    lifted: bool


def _shared_lenses(fragment: DocFragment, request: ViewRequest) -> bool:
    return bool(set(fragment.coverage.lenses) & set(request.lenses))


def _path_match(fragment: DocFragment, request: ViewRequest) -> bool:
    if not fragment.coverage.lift_on.path_match:
        return False
    if not request.navigation_path:
        return False
    subjects = set(fragment.subject_ids())
    return bool(subjects & set(request.navigation_path))


def _centrality_lift(fragment: DocFragment, topology: ViewportTopology) -> bool:
    threshold = fragment.coverage.lift_on.centrality_threshold
    if threshold is None:
        return False
    metrics = topology.for_entities(fragment.subject_ids())
    return any(m.above_centrality(threshold) for m in metrics)


def _cluster_coverage_lift(fragment: DocFragment, topology: ViewportTopology) -> bool:
    threshold = fragment.coverage.lift_on.cluster_coverage_threshold
    if threshold is None:
        return False
    metrics = topology.for_entities(fragment.subject_ids())
    return any(m.above_cluster_coverage(threshold) for m in metrics)


def filter_and_lift(
    candidates: list[DocFragment],
    request: ViewRequest,
    topology: ViewportTopology,
) -> list[FilteredFragment]:
    """Apply lens filtering and lifting; return survivors with effective zoom_min."""
    out: list[FilteredFragment] = []
    for fragment in candidates:
        if not _shared_lenses(fragment, request):
            continue

        base = fragment.coverage.zoom_min
        lifted = False
        lift_amount = fragment.coverage.lift_by

        if lift_amount > 0:
            if _centrality_lift(fragment, topology):
                base -= lift_amount
                lifted = True
            if _cluster_coverage_lift(fragment, topology):
                base -= lift_amount
                lifted = True
            if _path_match(fragment, request):
                base -= lift_amount
                lifted = True

        effective_min = max(0, base)
        if effective_min <= request.zoom <= fragment.coverage.zoom_max:
            out.append(
                FilteredFragment(
                    fragment=fragment,
                    effective_zoom_min=effective_min,
                    lifted=lifted,
                )
            )
    return out
