# The Zoom Axis

> Depth as a continuous map-style axis, not a role-bound tag.

**Source of truth:** [PRD §6.2](../../PRD.md)

---

## Definition

`zoom` is a single integer in the range **0–100** that represents the level of
abstraction at which the reader wants to see the graph:

- **0** is the most zoomed-out view (the company, the planet from orbit).
- **100** is the most zoomed-in view (a specific class or function in code).

Like a map, the same graph is rendered differently at different zoom levels.
Like a map, **the reader chooses the zoom**, not the system.

`zoom` is a **view parameter**, not a property of any entity or fragment.
Entities exist at every zoom level. Fragments declare a *zoom range* in which
they are useful, and the [view engine](../framework/view-engine.md) decides
whether to surface them.

---

## The default zoom bands

The 0–100 axis is conventionally divided into bands. These are guidelines, not
hard partitions:

| Band     | Conventional meaning           | Example content                                              |
| -------- | ------------------------------ | ------------------------------------------------------------ |
| **0–10**   | Company / domain map           | "Indeed has 4 engineering divisions."                        |
| **11–25**  | Teams, ownership, big systems  | "Team Payments owns the Billing Platform."                   |
| **26–40**  | Systems and integrations       | "Billing Platform talks to Auth via REST."                   |
| **41–60**  | Services, APIs, topics, DBs    | "Auth publishes to `auth.events.v1`."                        |
| **61–80**  | Components, modules, flows     | "The `TokenIssuer` module signs JWTs."                       |
| **81–100** | Classes, functions, files      | "`JwtSigner` in `/src/auth/jwt.ts` uses RS256."              |

These bands inform the `coverage.zoom_min` and `coverage.zoom_max` of
fragments, but the platform never enforces them as buckets.

---

## Why continuous, not discrete

C4 model has 4 fixed levels (Context, Containers, Components, Code).
NexusDocs deliberately rejects fixed levels:

- A reader debugging at zoom 55 may need fragments authored for both 45 and
  65. A discrete model forces them to context-switch.
- Different domains have different "natural" zooms. A platform team works at
  20–40 most of the time; an SRE works at 60–90.
- Zoom interacts with [topology](./topology.md). A small detail can be
  *lifted* to a higher zoom level if the graph says it matters here.

---

## Zoom is not a permission

> **The reader did not change. The view did.**

A principal engineer reading at zoom 15 sees the same fragments a junior
engineer would see at zoom 15. A junior engineer can zoom to 95 and see
exactly the same code-level fragments a principal engineer would.

There are no `min_role` or `audience` filters in NexusDocs v1. Depth is
governed by intent (zoom), not identity (role). Future versions may layer
permissions on top, but they will never gate zoom.

See [PRD §G2 / Goal #2](../../PRD.md) — *"depth without role-binding"*.

---

## How fragments declare zoom

Every [DocFragment](../entities/documentation.md) declares a coverage range:

```yaml
coverage:
  zoom_min: 25      # surfaces from zoom 25 upward (toward 100)
  zoom_max: 55      # disappears past zoom 55
  lenses: [product, technical]
```

A fragment with `zoom_min: 25` and `zoom_max: 55` shows up at zoom 35; it does
*not* show up at zoom 10 or zoom 70.

But the engine may **lift** `zoom_min` if the fragment's subject is
structurally significant in the current viewport. See
[`topology.md`](./topology.md).

---

## Interaction with other parameters

| Parameter                          | Interaction                                                                |
| ---------------------------------- | -------------------------------------------------------------------------- |
| [Lens](./lenses.md)                | A fragment is included only if **both** zoom and lens match.               |
| [Radius](./navigation.md)          | Larger radius → more entities → more candidate fragments at every zoom.    |
| [Topology](./topology.md)          | High centrality / coverage → fragments lift to lower zoom_min.             |
| [Navigation path](./navigation.md) | Entities on the active path → their fragments lift on `path_match`.        |

---

## Calibrating zoom for your organization

The 0–100 axis is **organization-tunable**. Some recommendations:

- Reserve the lowest 5–10 levels for company- or division-wide views.
- Keep the team-and-system region wide (11–40); this is where most product
  decisions happen.
- Compress the code-level region (90–100) — most readers do not need to
  distinguish "function" from "line of code."
- Don't set `zoom_max: 100` on every fragment "just in case." A fragment that
  surfaces at every zoom is noise.

---

## Open question

> *Are 0–100 ranges right, or should zoom be logarithmic?*
> See [PRD §18 Open Question #3](../../PRD.md). Calibration is a Phase 3
> concern; user testing will adjust the conventional bands above.

---

## See also

- [`concepts/lenses.md`](./lenses.md) — perspective filters that combine with zoom.
- [`concepts/topology.md`](./topology.md) — how zoom is *lifted* dynamically.
- [`schemas/doc-fragment.md`](../schemas/doc-fragment.md) — full coverage schema.
