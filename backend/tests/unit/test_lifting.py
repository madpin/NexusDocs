"""Tests for the lifting / filtering step."""

from nexusdocs.core import (
    Coverage,
    DocFragment,
    Provenance,
    SourceType,
    ViewRequest,
)
from nexusdocs.core.enums import GeneratedBy
from nexusdocs.core.fragment import LiftOn
from nexusdocs.view.lifting import filter_and_lift
from nexusdocs.view.topology import EntityMetrics, ViewportTopology


def _provenance(reviewed: bool = True, confidence: float = 1.0) -> Provenance:
    return Provenance(
        source_type=SourceType.manual,
        generated_by=GeneratedBy.human if confidence == 1.0 else GeneratedBy.llm,
        confidence=confidence,
        reviewed=reviewed,
    )


def _fragment(
    *,
    fid: str = "docfrag.x",
    zoom_min: int = 50,
    zoom_max: int = 80,
    lenses: list[str] | None = None,
    lift_by: int = 0,
    lift_on: LiftOn | None = None,
    subjects: list[str] | None = None,
    tags: list[str] | None = None,
) -> DocFragment:
    coverage = Coverage(
        zoom_min=zoom_min,
        zoom_max=zoom_max,
        lenses=lenses or ["technical"],
        lift_by=lift_by,
        lift_on=lift_on or LiftOn(),
    )
    payload = dict(
        id=fid,
        title="X",
        body="hello",
        coverage=coverage,
        provenance=_provenance(),
    )
    if subjects:
        payload["subjects"] = [{"entity": s} for s in subjects]
    elif tags:
        payload["tags"] = tags
    else:
        payload["tags"] = ["catchall"]
    return DocFragment(**payload)


def _topology(metrics: dict[str, EntityMetrics]) -> ViewportTopology:
    return ViewportTopology(metrics=metrics)


def test_lens_intersection_required() -> None:
    f = _fragment(lenses=["onboarding"])
    request = ViewRequest(focus="service.x", zoom=50, lenses=["technical"])
    survivors = filter_and_lift([f], request, _topology({}))
    assert survivors == []


def test_zoom_window_open_check() -> None:
    f = _fragment(zoom_min=30, zoom_max=60, lenses=["technical"])
    request = ViewRequest(focus="service.x", zoom=70, lenses=["technical"])
    survivors = filter_and_lift([f], request, _topology({}))
    assert survivors == []


def test_centrality_lifts_floor() -> None:
    f = _fragment(
        zoom_min=60,
        zoom_max=90,
        lenses=["technical"],
        lift_by=15,
        lift_on=LiftOn(centrality_threshold=0.4),
        subjects=["service.hub"],
    )
    metrics = {
        "service.hub": EntityMetrics(
            entity_id="service.hub",
            degree_centrality=0.7,
            betweenness_centrality=0.0,
            cluster_coverage=0.0,
            path_relevance=0.0,
        )
    }
    request = ViewRequest(
        focus="service.hub", zoom=50, lenses=["technical"]
    )
    survivors = filter_and_lift([f], request, _topology(metrics))
    assert len(survivors) == 1
    assert survivors[0].lifted is True
    assert survivors[0].effective_zoom_min == 45


def test_path_match_lift() -> None:
    f = _fragment(
        zoom_min=50,
        zoom_max=85,
        lenses=["debug"],
        lift_by=20,
        lift_on=LiftOn(path_match=True),
        subjects=["kafka_cluster.core-kafka-prod"],
    )
    metrics = {
        "kafka_cluster.core-kafka-prod": EntityMetrics(
            entity_id="kafka_cluster.core-kafka-prod",
            degree_centrality=0.0,
            betweenness_centrality=0.0,
            cluster_coverage=0.0,
            path_relevance=1.0,
        )
    }
    request = ViewRequest(
        focus="service.payments-api",
        zoom=35,
        lenses=["debug"],
        navigation_path=["kafka_cluster.core-kafka-prod"],
    )
    survivors = filter_and_lift([f], request, _topology(metrics))
    assert len(survivors) == 1
    assert survivors[0].effective_zoom_min == 30


def test_zoom_max_is_never_lifted() -> None:
    """zoom_max must remain fixed even when lifts trigger."""
    f = _fragment(
        zoom_min=60,
        zoom_max=70,
        lift_by=20,
        lift_on=LiftOn(centrality_threshold=0.1),
        subjects=["service.hub"],
        lenses=["technical"],
    )
    metrics = {
        "service.hub": EntityMetrics(
            entity_id="service.hub",
            degree_centrality=0.5,
            betweenness_centrality=0.0,
            cluster_coverage=0.0,
            path_relevance=0.0,
        )
    }
    request = ViewRequest(focus="service.hub", zoom=80, lenses=["technical"])
    survivors = filter_and_lift([f], request, _topology(metrics))
    assert survivors == []  # 80 > zoom_max=70
