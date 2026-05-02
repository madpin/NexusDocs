# Core Concepts

> The mental model behind NexusDocs.

This section explains the abstractions every user, author, and integrator needs
to understand before working with NexusDocs. Read these in order if you are new
to the platform.

| #   | Concept                                                | What it answers                                                |
| --- | ------------------------------------------------------ | -------------------------------------------------------------- |
| 1   | [Graph model](./graph-model.md)                        | What is stored? Nodes and edges, with property metadata.       |
| 2   | [Zoom axis](./zoom-axis.md)                            | How is "depth" expressed? A continuous 0–100 axis.             |
| 3   | [Lenses](./lenses.md)                                  | How is "perspective" expressed? Filterable view modes.         |
| 4   | [Topology-aware relevance](./topology.md)              | How does the system decide what to surface? Graph structure.   |
| 5   | [Navigation: focus, radius, viewport, path](./navigation.md) | How do readers move through the graph? Stateful navigation.  |

---

## How the concepts fit together

```
                       ┌─────────────────────────┐
                       │   GRAPH MODEL           │
                       │   (entities + edges)    │
                       └────────────┬────────────┘
                                    │
                                    │ a reader requests a view by setting…
                                    ▼
        ┌───────────────────┬───────────────────┬───────────────────┐
        │  FOCUS            │  ZOOM             │  LENSES           │
        │  (which entity?)  │  (how deep?)      │  (which slice?)   │
        └────────┬──────────┴─────────┬─────────┴─────────┬─────────┘
                 │                    │                   │
                 │                    ▼                   │
                 │           ┌──────────────────┐         │
                 └─────────▶ │   VIEWPORT       │◀────────┘
                             │   (focus +radius)│
                             └────────┬─────────┘
                                      │
                                      ▼
                             ┌─────────────────────┐
                             │   TOPOLOGY ANALYSIS │
                             │   (centrality, etc) │
                             └─────────┬───────────┘
                                       │
                                       ▼
                             ┌─────────────────────┐
                             │  FRAGMENT LIFTING   │
                             │  (what surfaces?)   │
                             └─────────┬───────────┘
                                       │
                                       ▼
                             ┌─────────────────────┐
                             │   RENDERED VIEW     │
                             └─────────────────────┘
```

---

## The four properties of any view

Every view in NexusDocs is fully described by four parameters:

| Parameter   | Type           | Default | Meaning                                                    |
| ----------- | -------------- | ------- | ---------------------------------------------------------- |
| `focus`     | Entity ID      | —       | The node at the center of the view.                        |
| `zoom`      | int 0–100      | 30      | The depth of detail. 0 = company. 100 = code.              |
| `lenses`    | string[]       | `[technical]` | Which perspectives to include.                       |
| `radius`    | int            | 2       | How many edge-hops outward from focus.                     |

A `navigation_path` may also be provided to influence which fragments lift.
Together these define a **viewport** — the subgraph the engine reasons over.

---

*Source: [PRD §6](../../PRD.md).*
