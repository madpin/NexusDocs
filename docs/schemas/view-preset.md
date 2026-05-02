# ViewPreset schema

> A saved view configuration: focus, zoom, lenses, radius, filters.

**Source of truth:** [PRD §7.4](../../PRD.md), [PRD §10.1](../../PRD.md)

---

## Schema

```yaml
ViewPreset:
  id: string                    # Required. Stable identifier.
  name: string                  # Required. Human-readable name.
  owner: string                 # Required. Person entity ID.
  shared_with: string[]         # Optional. Team or person entity IDs.

  focus: string                 # Required. Entity ID to center on.
  zoom: int                     # Required. 0–100.
  lenses: string[]              # Required. Active lenses.
  radius: int                   # Required. Edge-hops from focus.

  filters:
    entity_kinds: string[]      # Restrict viewport to these entity kinds.
    relationship_types: string[] # Restrict to these edge types.
    protocols: string[]         # Restrict to these protocols.
    tags: string[]              # Restrict to entities/fragments with these tags.

  created_at: datetime
  updated_at: datetime
```

---

## YAML envelope

```yaml
apiVersion: nexusdocs/v1
kind: ViewPreset
spec:
  id: preset.payments-debug
  name: "Payments Debug View"
  owner: person.tpinto
  shared_with:
    - team.payments
  focus: service.payments-api
  zoom: 55
  lenses: [technical, debug]
  radius: 3
  filters:
    protocols: [kafka, rest, postgres]
    tags: [tier-1]
```

---

## Field reference

### `id` (string, required)

Stable identifier. Convention: `preset.<short-name>`.

### `name` (string, required)

Human-readable label, shown in the UI's preset list.

### `owner` (string, required)

Person entity ID. The owner is the only one who can update or delete the
preset.

### `shared_with` (string[], optional)

A list of team or person entity IDs. Anyone in those entities can load and
clone the preset, but cannot modify it.

V1 has no permission system (see [PRD §5 NG2](../../PRD.md)); `shared_with`
is currently advisory metadata that the UI uses for discovery.

### `focus` (string, required)

The entity ID at the center of the view.

### `zoom` (int, required)

The zoom level. See [`concepts/zoom-axis.md`](../concepts/zoom-axis.md).

### `lenses` (string[], required)

Active lens set. See [`concepts/lenses.md`](../concepts/lenses.md). At
least one lens is required.

### `radius` (int, required)

Number of edge-hops from focus included in the viewport. See
[`concepts/navigation.md`](../concepts/navigation.md). Recommended values:
1, 2, 3.

### `filters` (object, optional)

Each filter restricts the viewport:

| Filter                      | Effect                                                                       |
| --------------------------- | ---------------------------------------------------------------------------- |
| `entity_kinds`              | Drop entities whose `kind` is not in the list.                               |
| `relationship_types`        | Drop edges whose `type` is not in the list.                                  |
| `protocols`                 | Drop edges whose `protocol` is not in the list. Skips edges with no protocol unless explicitly listed. |
| `tags`                      | Drop entities whose `labels` do not intersect; drop fragments whose `tags` do not intersect. |

Filters compose with AND. An entity that fails any filter is dropped.

> **Note:** filters apply *after* subgraph extraction. Topology metrics are
> computed on the full radius-bounded subgraph, then filters narrow what's
> rendered. This means an entity that drops out of the rendered view can
> still influence centrality calculations.

### `created_at`, `updated_at` (datetime, auto)

Server-controlled timestamps.

---

## Validation

| Rule                                                                            |
| ------------------------------------------------------------------------------- |
| `id` matches `^[a-z][a-z0-9.-]*$`, max 200 chars.                                |
| `owner` refers to an existing `person` entity.                                  |
| `shared_with` (if set) refers to existing `team` or `person` entities.          |
| `focus` refers to an existing entity.                                           |
| `zoom` ∈ `[0, 100]`.                                                             |
| `lenses` is non-empty.                                                          |
| `radius` ≥ 0.                                                                   |
| `filters.entity_kinds` (if set) values are in the entity kind enum.             |
| `filters.relationship_types` (if set) values are in the relationship type enum. |

---

## Worked examples

### Team architecture overview

```yaml
apiVersion: nexusdocs/v1
kind: ViewPreset
spec:
  id: preset.payments-architecture
  name: "Payments architecture (overview)"
  owner: person.tpinto
  shared_with:
    - team.payments
  focus: team.payments
  zoom: 25
  lenses: [technical]
  radius: 3
  filters:
    relationship_types: [owns, calls_api, publishes_to, consumes_from, reads_from, writes_to]
```

A reader loading this preset gets a zoom-25 technical view of everything
the Payments team owns and how it connects to other systems.

### On-call debug view

```yaml
apiVersion: nexusdocs/v1
kind: ViewPreset
spec:
  id: preset.payments-oncall-debug
  name: "Payments on-call: debug"
  owner: person.tpinto
  shared_with:
    - team.payments
  focus: service.payments-api
  zoom: 65
  lenses: [debug, operations]
  radius: 2
  filters:
    protocols: [rest, kafka, postgres]
    tags: [tier-1]
```

This preset centers on Payments API at code-adjacent zoom, showing only
debug + operations content along tier-1 edges via REST, Kafka, or Postgres.

### Onboarding tour

```yaml
apiVersion: nexusdocs/v1
kind: ViewPreset
spec:
  id: preset.fintech-onboarding-tour
  name: "Fintech onboarding tour"
  owner: person.svp-fintech
  shared_with:
    - division.fintech
  focus: division.fintech
  zoom: 15
  lenses: [onboarding, product]
  radius: 4
  filters:
    entity_kinds: [division, tribe, team, system]
```

A wide, shallow view ideal for first-day onboarding. No services or
infrastructure entities included.

---

## Open question

> Multi-tenancy and default views per team: see
> [PRD §18 Q5](../../PRD.md). The current model is *unified graph, saved
> presets per team*; presets do that job.

---

## See also

- [`concepts/navigation.md`](../concepts/navigation.md) — focus, radius, viewport, path.
- [`concepts/zoom-axis.md`](../concepts/zoom-axis.md) — zoom semantics.
- [`concepts/lenses.md`](../concepts/lenses.md) — lens semantics.
- [`framework/api.md`](../framework/api.md) — `/api/v1/views/presets`.
