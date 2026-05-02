# The Graph Model

> Everything is a node or an edge in a directed property graph.

**Source of truth:** [PRD §6.1](../../PRD.md), [PRD §7](../../PRD.md)

---

## Definition

NexusDocs stores the world as a single **directed property graph**:

- **Nodes** are *entities*: things that exist (a Team, a Service, a KafkaTopic).
- **Edges** are *relationships*: how two entities are connected (a Service
  `publishes_to` a Topic, a Person `member_of` a Team).
- Every node and every edge carries **properties** (metadata), including a
  `kind`/`type`, an `id`, freeform `labels`, and kind-specific fields.
- Documentation lives in the same graph as **DocFragments** anchored to nodes
  and edges.

There is exactly **one graph** per NexusDocs deployment. Teams do not get
isolated graphs. Different views of the same graph are produced by the
[view engine](../framework/view-engine.md), not by data partitioning.

---

## Why a graph

Documentation problems are relationship problems:

- *"Who consumes this Kafka topic?"* → traverse `consumes_from` edges.
- *"What is the blast radius if Auth Service goes down?"* → reverse traversal
  of `depends_on` and `calls_api` edges.
- *"Which teams own services that read from this database?"* → graph join
  across `reads_from` and `owns`.

A graph database makes these queries first-class. A wiki cannot answer them.

---

## What kinds of node exist

Entities are grouped by category. Each category has its own dedicated
documentation:

| Category                                                      | Example kinds                                              |
| ------------------------------------------------------------- | ---------------------------------------------------------- |
| [Organizational](../entities/organizational.md)               | `company`, `division`, `tribe`, `team`, `person`           |
| [Technical](../entities/technical.md)                         | `system`, `service`, `component`, `class`, `function`      |
| [Infrastructure](../entities/infrastructure.md)               | `database`, `kafka_cluster`, `kafka_topic`, `api_endpoint`, `queue`, `cache` |
| [Documentation](../entities/documentation.md)                 | `document`, `doc_fragment`                                 |

The full list of allowed values for `kind` is enumerated in
[`schemas/entity.md`](../schemas/entity.md).

---

## What kinds of edge exist

Relationships are also grouped by purpose:

| Category                                                              | Example types                                                                       |
| --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [Organizational](../relationships/organizational.md)                  | `belongs_to`, `owns`, `leads`, `member_of`, `reports_to`                            |
| [Technical](../relationships/technical.md)                            | `depends_on`, `calls_api`, `provides_api`, `extends`, `implements`                  |
| [Data flow](../relationships/data-flow.md)                            | `publishes_to`, `consumes_from`, `reads_from`, `writes_to`, `streams_to`            |
| [Documentation](../relationships/documentation.md)                    | `describes`, `references`, `supersedes`                                             |

Each edge carries:

- A `type` (one of the values above).
- An optional `protocol` (e.g. `kafka`, `rest`, `grpc`, `postgres`). See
  [`relationships/protocols.md`](../relationships/protocols.md).
- An optional `mode` (`sync`, `async`, `batch`).
- A `metadata` map for protocol-specific or relationship-specific detail.

---

## Identifiers

Every entity and relationship has a stable, human-readable `id`. By
convention:

- **Entities** use a dotted `kind.name` form, e.g. `service.auth`,
  `team.payments`, `topic.user-events`.
- **Relationships** use `rel.<source-short>-<verb>-<target-short>`, e.g.
  `rel.auth-publishes-user-events`.

IDs are URL-safe lowercase strings. They are immutable once created; renaming
an entity changes its `name`, not its `id`.

---

## Property graph: minimal example

```yaml
# Entity
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.auth
  type: service
  name: Auth Service
  metadata:
    technology: "Node.js / Express"

---
# Entity
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: topic.user-events
  type: kafka_topic
  name: user.events.v1
  metadata:
    cluster: core-kafka-prod

---
# Relationship
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-publishes-user-events
  source: service.auth
  target: topic.user-events
  type: publishes_to
  protocol: kafka
  mode: async
```

This three-document YAML defines two nodes and one edge. Every concept in
NexusDocs is built on top of this primitive.

---

## How the graph relates to other concepts

| Concept                                       | Relationship to the graph                                              |
| --------------------------------------------- | ---------------------------------------------------------------------- |
| [Zoom axis](./zoom-axis.md)                   | A render-time parameter; not stored on the graph itself.               |
| [Lenses](./lenses.md)                         | A render-time parameter; lens membership is declared on fragments.     |
| [Topology](./topology.md)                     | Computed from the graph at render time (centrality, betweenness, …).  |
| [Navigation](./navigation.md)                 | A stateful trail of focus entities; influences fragment lifting.       |
| [DocFragments](../entities/documentation.md)  | Stored as nodes themselves, linked to subjects via `subjects`/`relations`. |

---

## See also

- [`schemas/entity.md`](../schemas/entity.md) — full entity schema.
- [`schemas/relationship.md`](../schemas/relationship.md) — full relationship schema.
- [`framework/view-engine.md`](../framework/view-engine.md) — how the graph is rendered.
