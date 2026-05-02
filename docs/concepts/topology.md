# Topology-Aware Relevance

> The graph votes on what matters, not the fragment author.

**Source of truth:** [PRD §6.5](../../PRD.md), [PRD §8.1](../../PRD.md)

---

## Definition

**Topology-aware relevance** is the rule that determines, at render time,
which fragments surface in a view based on the **structure** of the
[viewport](./navigation.md) — not just static metadata.

A fragment declares the [zoom range](./zoom-axis.md) where it is *normally*
relevant. The view engine computes whether the fragment's subject is
**structurally significant** in the current viewport and, if so, may **lift**
the fragment so it appears at lower (more zoomed-out) zoom levels than it
otherwise would.

This is the platform's most distinctive feature. It is the answer to:

> *"Why should the reader have to know that Kafka is important here?"*

---

## The map analogy

Physical maps already do this:

- A small road is hidden at city scale — unless it is the only bridge between
  two districts. Then it is drawn boldly because of its **structural
  significance**, not its physical size.
- A point of interest appears at certain zoom levels — unless many roads
  converge on it, in which case it surfaces earlier.

NexusDocs applies the same logic to documentation.

> *"If Kafka appears in 2 of 20 services in the viewport, Kafka fragments
> stay at their declared zoom floor. If Kafka appears in 16 of 20 services,
> Kafka fragments lift into higher zoom levels automatically."*

---

## The four topology metrics

For every entity in the current viewport, the engine computes:

| Metric                     | Question it answers                                                    |
| -------------------------- | ---------------------------------------------------------------------- |
| **`degree_centrality`**    | How many connections does this node have, relative to the viewport?    |
| **`betweenness_centrality`** | What fraction of shortest paths in the viewport pass through it?     |
| **`cluster_coverage`**     | What % of viewport entities are connected to this node?                |
| **`path_relevance`**       | Is this node on the reader's recent navigation path?                   |

Each is a number in `[0.0, 1.0]`. Together they describe how *important* the
node is to the picture being rendered.

The exact algorithms (e.g. Brandes' algorithm for betweenness) are
implementation details — see [`framework/view-engine.md`](../framework/view-engine.md).

---

## Lifting

A fragment can declare conditions under which its `zoom_min` should be
lowered. This is called **lifting**:

```yaml
coverage:
  zoom_min: 50
  zoom_max: 80
  lenses: [technical]
  lift_on:
    centrality_threshold: 0.7         # if subject has degree centrality > 0.7
    cluster_coverage_threshold: 0.6   # OR if subject covers > 60% of viewport
    path_match: true                  # OR if subject is on the navigation path
  lift_by: 15                         # subtract 15 from zoom_min when lifted
```

When *any* `lift_on` condition fires, the engine computes:

```
effective_zoom_min = max(0, zoom_min - lift_by)
```

So in this example a fragment normally relevant at zoom 50–80 may surface as
early as zoom 35 in viewports where its subject is structurally important.

`lift_max` is **never** changed. A fragment lifted into a more zoomed-out
view still disappears at its original `zoom_max`. Lifting only widens the
window downward.

---

## Why this matters

Without topology-awareness, a reader at zoom 25 looking at "Team Payments"
would see only the team-level fragments. They would *not* see that:

- Kafka is the **bottleneck** for half of Payments' integrations.
- The Auth Service is on the **critical path** of every payments flow.
- One database is **shared** between four services.

These facts are already in the graph. They are not in the team-level
fragments. Topology-aware relevance pulls them up to where the reader is.

It also means the *fragment author does not have to anticipate every view*.
They write a fragment about Kafka throughput at zoom 50–70. The view engine
decides: does this Kafka topic matter at zoom 30 right now? If yes, lift.

---

## What is **not** lifted

| Property              | Lift-able?                                   |
| --------------------- | -------------------------------------------- |
| `zoom_min`            | ✅ Yes, by `lift_by` levels.                 |
| `zoom_max`            | ❌ Never. A code fragment never appears at zoom 5. |
| `lenses`              | ❌ Never. Lens membership is static.          |
| Entity visibility     | ❌ Topology does not surface new entities — only fragments anchored to entities already in the viewport. |

---

## Tuning

Default lift thresholds are conservative:

| `lift_on` condition            | Recommended starting threshold |
| ------------------------------ | ------------------------------ |
| `centrality_threshold`         | `0.7`                          |
| `cluster_coverage_threshold`   | `0.6`                          |
| `path_match`                   | `true` (boolean)               |

`lift_by` is typically `10`–`20`. A `lift_by` larger than 25 will bring
nearly any fragment to the top of the zoom range, drowning the view.

These thresholds are organization-tunable and are an open calibration
question. See [PRD §18 Q4](../../PRD.md).

---

## Worked example

```
Viewport (radius 2 from focus = team.payments) contains 20 entities.
- Kafka cluster `core-kafka-prod` is connected to 16 of them.
  → cluster_coverage = 0.80

Fragment "Kafka throughput limits" declares:
  zoom_min: 50, zoom_max: 75, lift_on.cluster_coverage_threshold: 0.6, lift_by: 20

The reader requests a view at zoom 30.

Lifting: cluster_coverage 0.80 > threshold 0.60 → lift fires.
effective_zoom_min = max(0, 50 - 20) = 30
30 ≤ request.zoom (30) ≤ zoom_max (75) → fragment is included.

Without lifting, this fragment would not have appeared in a zoom-30 view.
```

---

## See also

- [`concepts/zoom-axis.md`](./zoom-axis.md) — what is being lifted.
- [`concepts/navigation.md`](./navigation.md) — `path_match` and how the path is tracked.
- [`framework/view-engine.md`](../framework/view-engine.md) — the algorithm.
- [`schemas/doc-fragment.md`](../schemas/doc-fragment.md) — `coverage.lift_on` schema.
