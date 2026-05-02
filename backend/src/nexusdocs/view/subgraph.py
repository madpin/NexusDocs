"""Step 1 — bounded BFS subgraph extraction with filter pushdown.

Containment (the `parent` field on entities) is expressed by a synthetic
`belongs_to` edge during traversal so that the engine "sees" containment
relationships even when no explicit edge has been authored. These synthetic
edges are not persisted; they exist only in the viewport.

Zoom + depth-aware granularity
------------------------------

Each entity kind has a *natural zoom band* — the zoom value at which it
first becomes visible at hop-1. As the user zooms in we progressively
reveal more granular kinds (services → datastores → APIs → components →
people → classes → functions).

On top of that, every additional hop past hop-1 adds a "depth penalty" to
the threshold, so the further an entity sits from the focus the longer
it stays invisible while zooming in. The result is a smart, depth-aware
view:

  * close-to-the-focus entities reveal their detail first,
  * far-from-the-focus entities only show up at higher zoom,
  * zooming out drops the deepest entities first, leaving a clean,
    pleasing view that always keeps the focus and its context on screen.

Entities are pinned (always visible regardless of zoom) when they are:
  * the current focus,
  * on the navigation path.

We deliberately do NOT pin the entire hop-1 ring — that produced a
hundred-team blob when focused on a company at low zoom. Hop-1 entities
are governed by the same zoom check, just with no depth penalty.

Within-kind stagger
-------------------

A pure kind threshold is a *step* function: when zoom crosses 30 every
service in scope pops in at once, which feels like a flood after a long
stretch of nothing. To make the reveal feel continuous, every entity gets
a per-instance "appearance zoom":

    appearance_zoom = base_threshold + spread * rank / (cohort_size - 1)

Cohorts are formed by `(kind, hop)`. Inside a cohort we rank entities by
descending in-scope degree (a cheap topology proxy that doesn't need
NetworkX). The most-connected service of a cohort still surfaces at the
kind threshold; less central peers slot in over the next ~`APPEARANCE_SPREAD`
zoom units. The result: roughly one new entity per zoom unit for cohorts
of typical size, so a slow scroll feels analog instead of stepwise.

Singleton cohorts (size == 1) keep the original threshold exactly, which
means the binary `kind_visible_at` contract still holds for any test or
caller that worked one entity at a time.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from ..core import Entity, Relationship, RelationshipType, ViewRequest
from ..core.enums import Kind
from ..core.view_preset import FilterSet
from ..graph.repository import EntityNotFoundError, GraphRepository


class FocusNotFoundError(Exception):
    """Raised when the focus entity does not exist."""


# Minimum zoom (0-100) at which a given Kind first becomes visible at hop-1.
# Lower numbers => visible while zoomed further out.
KIND_MIN_ZOOM: dict[str, int] = {
    Kind.company.value: 0,
    Kind.division.value: 5,
    Kind.system.value: 5,
    Kind.tribe.value: 12,
    Kind.team.value: 18,
    Kind.kafka_cluster.value: 22,
    Kind.service.value: 30,
    Kind.database.value: 40,
    Kind.queue.value: 42,
    Kind.cache.value: 44,
    Kind.kafka_topic.value: 50,
    Kind.api_endpoint.value: 55,
    Kind.component.value: 60,
    Kind.person.value: 65,
    Kind.cls.value: 75,
    Kind.function.value: 85,
}

# Each hop past hop-1 adds DEPTH_PENALTY_PER_HOP to the kind's threshold,
# so deeper entities require more zoom to surface.
DEPTH_PENALTY_PER_HOP = 12

# How many zoom units a single (kind, hop) cohort spans. The most-central
# member of the cohort appears at the kind threshold; the least-central
# appears `APPEARANCE_SPREAD` units later. ~25 gives a good "one new entity
# per zoom unit" feel for cohorts of 5-25, which is the typical range.
APPEARANCE_SPREAD = 25


def kind_min_zoom_at_depth(kind: str, hop: int) -> int:
    """Return the minimum zoom at which `kind` becomes visible at distance `hop`.

    `hop` is the BFS distance from the current focus (focus itself is hop=0,
    direct neighbours are hop=1, …). Hop-0 is always visible. Hop-1 uses the
    raw kind threshold; subsequent hops add a depth penalty.
    """
    base = KIND_MIN_ZOOM.get(kind, 50)
    if hop <= 1:
        return base
    return base + DEPTH_PENALTY_PER_HOP * (hop - 1)


def kind_visible_at(kind: str, zoom: int, hop: int = 1) -> bool:
    """Return True when an entity of `kind` is wide enough at `zoom` to render.

    This is the *singleton* visibility test — it ignores cohort stagger and
    answers "could a hypothetical lone entity of this kind, at this hop,
    appear at this zoom?". For the cohort-aware appearance zoom that the
    actual viewport uses, see `_appearance_zoom`.
    """
    return zoom >= kind_min_zoom_at_depth(kind, hop)


def _appearance_zoom(
    kind: str, hop: int, cohort_rank: int, cohort_size: int
) -> int:
    """Per-instance appearance threshold inside a (kind, hop) cohort.

    rank 0 (most-central) appears at the kind threshold; rank n-1 appears
    `APPEARANCE_SPREAD` later. Singleton cohorts keep the bare threshold so
    the legacy `kind_visible_at` contract still holds in that case.
    """
    base = kind_min_zoom_at_depth(kind, hop)
    if cohort_size <= 1:
        return base
    return base + APPEARANCE_SPREAD * cohort_rank // (cohort_size - 1)


@dataclass
class Viewport:
    """A viewport carries two layers:

    * `entities` / `relationships` — the *visible* slice rendered on screen
      after the depth-aware zoom filter has been applied.
    * `scope_entities` / `scope_relationships` — the full BFS sample the
      viewport was carved out of, before the zoom filter. Topology metrics
      (degree, cluster coverage, betweenness) operate on this larger set so
      lift_on rules and centrality are stable across zoom levels.
    """

    entities: dict[str, Entity]
    relationships: dict[str, Relationship]
    scope_entities: dict[str, Entity] | None = None
    scope_relationships: dict[str, Relationship] | None = None
    capped: bool = False
    effective_radius: int = 0

    def entity_ids(self) -> set[str]:
        return set(self.entities)

    def relationship_ids(self) -> set[str]:
        return set(self.relationships)

    @property
    def topology_entities(self) -> dict[str, Entity]:
        return self.scope_entities if self.scope_entities is not None else self.entities

    @property
    def topology_relationships(self) -> dict[str, Relationship]:
        if self.scope_relationships is not None:
            return self.scope_relationships
        return self.relationships


def _edge_matches(rel: Relationship, filters: FilterSet) -> bool:
    if filters.relationship_types and rel.type.value not in filters.relationship_types:
        return False
    if filters.protocols:
        proto = str(rel.protocol) if rel.protocol else None
        if proto not in filters.protocols:
            return False
    return True


def _entity_matches(entity: Entity, filters: FilterSet) -> bool:
    """Static filters from the user (kinds / tags). Zoom is applied later."""
    if filters.entity_kinds and entity.kind.value not in filters.entity_kinds:
        return False
    if filters.tags and not (set(entity.labels) & set(filters.tags)):
        return False
    return True


def _synthetic_belongs_to(child: Entity, parent_id: str) -> Relationship:
    """Build a transient `belongs_to` edge from a child entity to its parent."""
    now = datetime.now(UTC)
    return Relationship(
        id=f"implicit.belongs-to.{child.id}",
        source=child.id,
        target=parent_id,
        type=RelationshipType.belongs_to,
        metadata={"implicit": True},
        created_at=now,
        updated_at=now,
    )


def _edges_for(
    repo: GraphRepository, entity: Entity
) -> list[tuple[Relationship, str]]:
    """Return (edge, other_endpoint_id) pairs for the entity, including parent links."""
    pairs: list[tuple[Relationship, str]] = []
    try:
        for r in repo.edges_of(entity.id, direction="both"):
            other = r.target if r.source == entity.id else r.source
            pairs.append((r, other))
    except EntityNotFoundError:
        return pairs

    if entity.parent and repo.has_entity(entity.parent):
        pairs.append((_synthetic_belongs_to(entity, entity.parent), entity.parent))

    for child in repo.children_of(entity.id):
        pairs.append((_synthetic_belongs_to(child, entity.id), child.id))

    return pairs


def extract_viewport(
    repo: GraphRepository,
    request: ViewRequest,
    *,
    cap: int = 800,
) -> Viewport:
    """Run a bounded BFS from `request.focus` with zoom-aware kind filtering.

    BFS visits everything inside the requested radius (subject to static
    kind/tag filters and the cap). After BFS, we drop entities whose Kind
    is too granular for the current zoom level, *except* for the focus, the
    navigation path, and direct (hop-1) neighbours of the focus, which are
    always kept so the user never loses context.
    """
    if not repo.has_entity(request.focus):
        raise FocusNotFoundError(request.focus)

    focus = repo.get_entity(request.focus)
    entities: dict[str, Entity] = {focus.id: focus}
    relationships: dict[str, Relationship] = {}
    frontier: set[str] = {focus.id}
    hop_distance: dict[str, int] = {focus.id: 0}
    capped = False

    effective_radius = 0
    for hop in range(request.radius):
        if not frontier:
            break
        next_frontier: set[str] = set()
        for node_id in frontier:
            entity = entities[node_id]
            for edge, other_id in _edges_for(repo, entity):
                if not _edge_matches(edge, request.filters):
                    continue
                relationships[edge.id] = edge
                if other_id in entities:
                    continue
                try:
                    other = repo.get_entity(other_id)
                except EntityNotFoundError:
                    continue
                if not _entity_matches(other, request.filters):
                    continue
                if len(entities) >= cap:
                    capped = True
                    break
                entities[other_id] = other
                hop_distance[other_id] = hop + 1
                next_frontier.add(other_id)
            if capped:
                break
        if capped:
            break
        effective_radius = hop + 1
        frontier = next_frontier

    # Apply depth-aware zoom visibility. Focus + nav-path always stay so
    # the user never loses sight of where they are.
    pinned: set[str] = {focus.id}
    pinned.update(request.navigation_path)

    # Rank entities inside each (kind, hop) cohort by descending in-scope
    # degree so the most-connected members surface earliest as the user
    # zooms in. Ties break on entity id for stable ordering across calls.
    scope_degree: dict[str, int] = dict.fromkeys(entities, 0)
    for r in relationships.values():
        if r.source in scope_degree:
            scope_degree[r.source] += 1
        if r.target in scope_degree:
            scope_degree[r.target] += 1

    cohorts: dict[tuple[str, int], list[str]] = {}
    for eid, entity in entities.items():
        if eid in pinned:
            continue
        hop = hop_distance.get(eid, 1)
        cohorts.setdefault((entity.kind.value, hop), []).append(eid)

    cohort_rank: dict[str, tuple[int, int]] = {}
    for members in cohorts.values():
        members.sort(key=lambda i: (-scope_degree.get(i, 0), i))
        size = len(members)
        for rank, eid in enumerate(members):
            cohort_rank[eid] = (rank, size)

    visible_entities: dict[str, Entity] = {}
    for eid, entity in entities.items():
        if eid in pinned:
            visible_entities[eid] = entity
            continue
        hop = hop_distance.get(eid, 1)
        rank, size = cohort_rank.get(eid, (0, 1))
        if request.zoom >= _appearance_zoom(entity.kind.value, hop, rank, size):
            visible_entities[eid] = entity

    visible_relationships = {
        rid: r
        for rid, r in relationships.items()
        if r.source in visible_entities and r.target in visible_entities
    }

    return Viewport(
        entities=visible_entities,
        relationships=visible_relationships,
        scope_entities=dict(entities),
        scope_relationships=dict(relationships),
        capped=capped,
        effective_radius=effective_radius,
    )
