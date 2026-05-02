"""Tests for the zoom-band, depth-aware kind filter inside `extract_viewport`.

The filter must:
  * always include the focus and entities on the navigation path,
  * hide entities whose kind is too granular for the current zoom (with a
    depth penalty per hop past hop-1),
  * drop relationships whose endpoints get hidden,
  * still respect explicit `filters.entity_kinds` overrides.
"""

from datetime import UTC, datetime
from itertools import pairwise

from nexusdocs.core import Entity, Kind, Relationship, RelationshipType, ViewRequest
from nexusdocs.core.view_preset import FilterSet
from nexusdocs.graph import InMemoryGraphRepository
from nexusdocs.view.subgraph import (
    APPEARANCE_SPREAD,
    DEPTH_PENALTY_PER_HOP,
    KIND_MIN_ZOOM,
    extract_viewport,
    kind_min_zoom_at_depth,
    kind_visible_at,
)


def _ent(eid: str, kind: Kind, parent: str | None = None) -> Entity:
    return Entity(id=eid, kind=kind, name=eid, parent=parent)


def _rel(rid: str, src: str, tgt: str, type_: RelationshipType) -> Relationship:
    now = datetime.now(UTC)
    return Relationship(
        id=rid,
        source=src,
        target=tgt,
        type=type_,
        created_at=now,
        updated_at=now,
    )


def _layered_repo() -> InMemoryGraphRepository:
    """Company → division → team → service → component → class → function chain
    plus a `person` member-of the team so the kind filter has plenty to chew on."""
    repo = InMemoryGraphRepository()
    repo.initialize()
    repo.upsert_entity(_ent("company.acme", Kind.company))
    repo.upsert_entity(_ent("division.fintech", Kind.division, parent="company.acme"))
    repo.upsert_entity(_ent("team.payments", Kind.team, parent="division.fintech"))
    repo.upsert_entity(_ent("person.tpinto", Kind.person))
    repo.upsert_entity(_ent("service.payments", Kind.service))
    repo.upsert_entity(_ent("component.processor", Kind.component, parent="service.payments"))
    repo.upsert_entity(_ent("class.signer", Kind.cls, parent="component.processor"))
    repo.upsert_entity(_ent("function.sign", Kind.function, parent="class.signer"))

    repo.upsert_relationship(
        _rel("rel.tpinto-member-of-payments", "person.tpinto", "team.payments", RelationshipType.member_of)
    )
    repo.upsert_relationship(
        _rel("rel.payments-owns-service", "team.payments", "service.payments", RelationshipType.owns)
    )
    return repo


def test_kind_visible_thresholds_at_hop1() -> None:
    assert kind_visible_at(Kind.company.value, 0)
    assert not kind_visible_at(Kind.team.value, 10)
    assert kind_visible_at(Kind.team.value, KIND_MIN_ZOOM[Kind.team.value])
    assert not kind_visible_at(Kind.function.value, 50)
    assert kind_visible_at(Kind.function.value, 95)


def test_depth_penalty_pushes_threshold_higher() -> None:
    base = KIND_MIN_ZOOM[Kind.service.value]
    assert kind_min_zoom_at_depth(Kind.service.value, 1) == base
    assert kind_min_zoom_at_depth(Kind.service.value, 2) == base + DEPTH_PENALTY_PER_HOP
    assert kind_min_zoom_at_depth(Kind.service.value, 3) == base + 2 * DEPTH_PENALTY_PER_HOP
    # hop=0 (the focus) is always visible.
    assert kind_min_zoom_at_depth(Kind.service.value, 0) == base


def test_focus_always_present_even_at_low_zoom() -> None:
    repo = _layered_repo()
    request = ViewRequest(
        focus="function.sign",  # function requires zoom >= 85 at hop-1
        zoom=0,
        lenses=["technical"],
        radius=1,
    )
    viewport = extract_viewport(repo, request)
    assert "function.sign" in viewport.entities


def test_hop1_neighbours_visible_at_their_kind_threshold() -> None:
    """At hop-1, a kind appears once zoom >= the kind's base threshold."""
    repo = _layered_repo()
    # team.payments → service.payments (hop-1, owns relationship). service min=30.
    request = ViewRequest(focus="team.payments", zoom=30, lenses=["technical"], radius=1)
    viewport = extract_viewport(repo, request)
    assert "service.payments" in viewport.entities

    # Person hop-1: kind threshold is 65 → at z=64 it should still be hidden.
    request = ViewRequest(focus="team.payments", zoom=64, lenses=["technical"], radius=1)
    viewport = extract_viewport(repo, request)
    assert "person.tpinto" not in viewport.entities

    request = ViewRequest(focus="team.payments", zoom=65, lenses=["technical"], radius=1)
    viewport = extract_viewport(repo, request)
    assert "person.tpinto" in viewport.entities


def test_hop2_pays_depth_penalty() -> None:
    """Service is hop-1 of team, but component (hop-2) needs an extra penalty."""
    repo = _layered_repo()
    component_min = KIND_MIN_ZOOM[Kind.component.value]
    threshold = component_min + DEPTH_PENALTY_PER_HOP  # hop-2 penalty

    # Just below the hop-2 threshold → not visible.
    request = ViewRequest(
        focus="team.payments", zoom=threshold - 1, lenses=["technical"], radius=2
    )
    viewport = extract_viewport(repo, request)
    assert "component.processor" not in viewport.entities

    # At the threshold → visible.
    request = ViewRequest(
        focus="team.payments", zoom=threshold, lenses=["technical"], radius=2
    )
    viewport = extract_viewport(repo, request)
    assert "component.processor" in viewport.entities


def test_relationships_drop_when_endpoint_filtered() -> None:
    repo = _layered_repo()
    request = ViewRequest(
        focus="company.acme",
        zoom=0,
        lenses=["technical"],
        radius=4,
    )
    viewport = extract_viewport(repo, request)
    # rel.payments-owns-service connects two non-pinned, too-granular nodes.
    assert "rel.payments-owns-service" not in viewport.relationships


def test_navigation_path_pins_through_zoom_bands() -> None:
    repo = _layered_repo()
    request = ViewRequest(
        focus="company.acme",
        zoom=0,
        lenses=["technical"],
        radius=4,
        navigation_path=["service.payments"],  # would otherwise be filtered out
    )
    viewport = extract_viewport(repo, request)
    assert "service.payments" in viewport.entities


def test_explicit_kind_filter_still_applies() -> None:
    repo = _layered_repo()
    request = ViewRequest(
        focus="team.payments",
        zoom=80,
        lenses=["technical"],
        radius=3,
        filters=FilterSet(entity_kinds=["team", "service"]),
    )
    viewport = extract_viewport(repo, request)
    kinds = {e.kind.value for e in viewport.entities.values()}
    # team.payments is the focus (kind=team), service.payments is hop-1.
    # The static filter blocks person/division/component/etc. from joining
    # the BFS in the first place.
    assert kinds.issubset({"team", "service"})
    assert "person.tpinto" not in viewport.entities
    assert "division.fintech" not in viewport.entities


def _service_cohort_repo(num_services: int = 6) -> InMemoryGraphRepository:
    """A team with N hop-1 services and varying in-scope degree, so the
    cohort stagger has something to rank."""
    repo = InMemoryGraphRepository()
    repo.initialize()
    repo.upsert_entity(_ent("team.payments", Kind.team))
    for i in range(num_services):
        sid = f"service.svc{i}"
        repo.upsert_entity(_ent(sid, Kind.service))
        repo.upsert_relationship(
            _rel(f"rel.team-owns-{sid}", "team.payments", sid, RelationshipType.owns)
        )
    # Add extra cross-edges between services so degree-in-scope varies:
    # svc0 connects to every other service (high degree),
    # svc1 connects to two,
    # svc2..svcN-1 stay at degree 1 (just the team-owns edge).
    for i in range(1, num_services):
        repo.upsert_relationship(
            _rel(f"rel.svc0-deps-svc{i}", "service.svc0", f"service.svc{i}",
                 RelationshipType.depends_on)
        )
    if num_services >= 3:
        repo.upsert_relationship(
            _rel("rel.svc1-deps-svc2", "service.svc1", "service.svc2",
                 RelationshipType.depends_on)
        )
    return repo


def test_cohort_stagger_reveals_progressively() -> None:
    """At a multi-entity cohort's threshold, only the most-connected member
    appears; the rest stream in over the next ~APPEARANCE_SPREAD zoom units."""
    repo = _service_cohort_repo(num_services=6)
    base = KIND_MIN_ZOOM[Kind.service.value]  # 30 for service at hop-1

    # Right at the kind threshold: only the highest-degree service is in.
    request = ViewRequest(
        focus="team.payments", zoom=base, lenses=["technical"], radius=1
    )
    viewport = extract_viewport(repo, request)
    visible_services = {
        e.id for e in viewport.entities.values() if e.kind == Kind.service
    }
    assert visible_services == {"service.svc0"}, (
        f"only the most-central service should surface at the kind threshold, "
        f"got {visible_services}"
    )

    # Walk the zoom up one step at a time — every step should add at most a
    # handful of new entities, never the whole cohort at once.
    counts = []
    for z in range(base, base + APPEARANCE_SPREAD + 1):
        request = ViewRequest(
            focus="team.payments", zoom=z, lenses=["technical"], radius=1
        )
        vp = extract_viewport(repo, request)
        counts.append(
            sum(1 for e in vp.entities.values() if e.kind == Kind.service)
        )

    # Monotonic non-decrease, no single-step floods, full cohort by the end.
    assert counts == sorted(counts), f"reveal should be monotonic, got {counts}"
    max_step = max(b - a for a, b in pairwise(counts))
    assert max_step <= 2, (
        f"no zoom step should reveal more than ~2 services in a cohort of 6, "
        f"got max_step={max_step} (counts={counts})"
    )
    assert counts[-1] == 6, (
        f"by the end of the spread the entire cohort should be visible, "
        f"got counts={counts}"
    )


def test_singleton_cohort_still_obeys_bare_threshold() -> None:
    """The new stagger collapses to the legacy threshold when a (kind, hop)
    cohort has exactly one member — preserves backwards compatibility."""
    repo = _layered_repo()
    base = KIND_MIN_ZOOM[Kind.service.value]
    request = ViewRequest(
        focus="team.payments", zoom=base - 1, lenses=["technical"], radius=1
    )
    viewport = extract_viewport(repo, request)
    assert "service.payments" not in viewport.entities

    request = ViewRequest(
        focus="team.payments", zoom=base, lenses=["technical"], radius=1
    )
    viewport = extract_viewport(repo, request)
    assert "service.payments" in viewport.entities
