# Lenses

> Perspective filters: which *kind* of information to render at the chosen zoom.

**Source of truth:** [PRD §6.3](../../PRD.md)

---

## Definition

A **lens** is a named filter that determines which fragments are surfaced
at any given [zoom](./zoom-axis.md). Lenses are orthogonal to zoom: zoom
controls *how deep*, lenses control *what flavor*.

A view request specifies one or more active lenses. A fragment is shown only
if **at least one** of its declared lenses intersects the active lens set
(union semantics).

---

## The six built-in lenses

| Lens           | Shows                                                                | Hides                                          | Typical zoom |
| -------------- | -------------------------------------------------------------------- | ---------------------------------------------- | ------------ |
| **`product`**    | Goals, customers, outcomes, features, roadmap items                | Implementation details, infra specifics       | 5–35         |
| **`technical`**  | Architecture, interfaces, protocols, schemas                       | Business context, client-facing language      | 25–80        |
| **`operations`** | Alerts, runbooks, SLOs, on-call rotations, dependency chains       | Code-level detail, product framing            | 30–70        |
| **`debug`**      | Traces, logs, code paths, error handling, failure modes            | High-level summaries                          | 55–100       |
| **`client`**     | External-facing explanations, API guides, integration steps        | Internal team context                         | 25–70        |
| **`onboarding`** | Setup guides, glossary, "start here" paths                          | Deep debugging, incident history              | 15–60        |

These six lenses are guaranteed by v1. Organizations may extend with
additional lens names (e.g. `security`, `compliance`, `cost`) — the platform
treats them as opaque strings.

---

## Combining lenses

Lenses **stack with union semantics**. Specifying `lenses: [technical, debug]`
shows fragments tagged with `technical` OR `debug` (or both). It does **not**
require both.

This is intentional. A staff engineer debugging an incident wants both the
architecture (`technical`) and the failure mode notes (`debug`) at once.

```yaml
# Two requests on the same focus and zoom
focus: service.auth
zoom: 55

# Variant A: only architecture
lenses: [technical]

# Variant B: architecture AND failure mode notes
lenses: [technical, debug]
```

Variant B will be a strict superset of Variant A.

---

## How fragments declare lenses

Every fragment declares the lens set in which it is relevant:

```yaml
coverage:
  zoom_min: 40
  zoom_max: 75
  lenses: [technical, debug]
```

A fragment with no `lenses` field is treated as having an empty set and will
never surface. There is no implicit "all lenses" — be explicit.

A fragment may declare itself across many lenses if its content is broadly
useful (e.g. a glossary fragment may carry `[onboarding, product, technical]`).

---

## Interaction with other parameters

| Parameter                          | Interaction                                                                       |
| ---------------------------------- | --------------------------------------------------------------------------------- |
| [Zoom](./zoom-axis.md)             | Both must match. Zoom is gated on `[zoom_min, zoom_max]`; lens is gated on union. |
| [Topology](./topology.md)          | Lens set does **not** change with topology. Only zoom is lifted.                  |
| [Navigation path](./navigation.md) | Path entities lift fragments by zoom; lens membership is unaffected.              |

---

## Authoring guidance

- **Pick the smallest sufficient lens set.** A fragment that lives in every
  lens lives nowhere — it becomes noise.
- **`technical` is the default for code-and-architecture content.** Use it
  liberally.
- **`debug` is for "what to do when things go wrong."** It is *not* for
  "things that went wrong" (that is `operations` postmortem material).
- **`client` means external audience.** Internal API references should use
  `technical`, not `client`, unless you specifically expose them.
- **`onboarding` is a path lens, not a topic lens.** It marks fragments as
  useful for someone learning the system, regardless of their zoom.

---

## Why lens, not category

A traditional documentation system has fixed categories: API Reference,
Runbooks, Postmortems. NexusDocs uses lenses because the same content
sometimes serves multiple purposes:

- A *single* fragment about Kafka throughput limits is `technical` for an
  architect, `operations` for an SRE, and `debug` for someone investigating
  consumer lag.
- A category forces a primary owner. A lens set lets the same fragment serve
  three audiences without duplication.

---

## See also

- [`concepts/zoom-axis.md`](./zoom-axis.md) — the orthogonal axis.
- [`concepts/topology.md`](./topology.md) — lifts zoom but never lens.
- [`schemas/doc-fragment.md`](../schemas/doc-fragment.md) — full coverage schema.
