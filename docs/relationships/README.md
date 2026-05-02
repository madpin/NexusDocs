# Relationships

> What can be an edge in the NexusDocs graph.

**Source of truth:** [PRD §6.1, §7.2](../../PRD.md)

---

## What is a Relationship?

A **Relationship** is a directed edge in the graph. It describes how two
entities connect: a Service `publishes_to` a Kafka Topic, a Person `member_of`
a Team, a Service `calls_api` another Service.

Every relationship has:

- An immutable `id`.
- A `source` (entity ID).
- A `target` (entity ID).
- A `type` from a fixed enum.
- An optional `protocol` (the *how*).
- An optional `mode` (`sync`, `async`, `batch`).
- A `metadata` map for type- and protocol-specific detail.
- Provenance: where the edge was discovered or defined.

The full schema is in [`schemas/relationship.md`](../schemas/relationship.md).

---

## Relationship taxonomy

Relationships are grouped into four documentation categories:

| Category                                 | Types                                                                                         |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| [Organizational](./organizational.md)    | `belongs_to`, `owns`, `leads`, `member_of`, `reports_to`                                      |
| [Technical](./technical.md)              | `depends_on`, `calls_api`, `provides_api`, `extends`, `implements`                            |
| [Data flow](./data-flow.md)              | `publishes_to`, `consumes_from`, `reads_from`, `writes_to`, `streams_to`                      |
| [Documentation](./documentation.md)      | `describes`, `references`, `supersedes`                                                       |

Plus one cross-cutting reference:

| Reference                                | Topic                                                                                         |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| [Protocols](./protocols.md)              | The transport/protocol metadata that decorates technical and data-flow edges.                 |

These categories are documentation conveniences — the platform stores all
edges in the same property graph, distinguished only by `type`.

---

## Direction matters

All relationships are **directed**. The `source` and `target` are not
interchangeable.

| Type            | Direction                                                                  |
| --------------- | -------------------------------------------------------------------------- |
| `belongs_to`    | `(child) belongs_to (parent)`                                              |
| `owns`          | `(owner) owns (asset)`                                                     |
| `leads`         | `(leader) leads (org-unit)`                                                |
| `member_of`     | `(person) member_of (team)`                                                |
| `reports_to`    | `(report) reports_to (manager)`                                            |
| `depends_on`    | `(dependent) depends_on (dependency)`                                      |
| `calls_api`     | `(caller) calls_api (callee)`                                              |
| `provides_api`  | `(provider) provides_api (consumer-or-endpoint)`                           |
| `extends`       | `(subclass) extends (superclass)`                                          |
| `implements`    | `(impl) implements (interface)`                                            |
| `publishes_to`  | `(publisher) publishes_to (topic\|queue)`                                  |
| `consumes_from` | `(consumer) consumes_from (topic\|queue)`                                  |
| `reads_from`    | `(reader) reads_from (database\|cache)`                                    |
| `writes_to`     | `(writer) writes_to (database\|cache)`                                     |
| `streams_to`    | `(producer) streams_to (sink)`                                             |
| `describes`     | `(document\|fragment) describes (entity)`                                  |
| `references`    | `(document\|fragment) references (document\|entity)`                       |
| `supersedes`    | `(new) supersedes (old)`                                                   |

Reverse traversal is always supported by the API; you do not need a reverse
edge.

---

## Protocol metadata

Edges in the **technical** and **data-flow** categories carry an additional
`protocol` field that captures the *how*:

```yaml
type: calls_api
protocol: rest        # or grpc, graphql, websocket
mode: sync            # or async, batch
```

The full vocabulary is in [`relationships/protocols.md`](./protocols.md).

Protocol metadata is what makes queries like *"show me all gRPC traffic into
Auth Service"* possible. The PRD lists this as a primary differentiator from
existing tools — see [PRD §2.3, §G6, App B](../../PRD.md).

---

## ID conventions

Relationship IDs follow the pattern
`rel.<source-short>-<verb>-<target-short>`:

| Edge                                                  | ID                                                  |
| ----------------------------------------------------- | --------------------------------------------------- |
| `(service.auth) publishes_to (topic.user-events)`     | `rel.auth-publishes-user-events`                    |
| `(service.payments-api) calls_api (service.auth)`    | `rel.payments-api-calls-auth`                       |
| `(person.tpinto) member_of (team.payments)`           | `rel.tpinto-member-of-payments`                     |
| `(service.billing) reads_from (database.transactions)` | `rel.billing-reads-transactions-db`                |

This convention keeps IDs human-readable and makes ad-hoc references in
fragment YAML straightforward.

---

## Authoring a relationship

Minimum viable edge:

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-publishes-user-events
  source: service.auth
  target: topic.user-events
  type: publishes_to
```

The `source` and `target` entities must exist before a relationship can be
created via the API. YAML batches applied via `nexdoc apply` are validated
in dependency order — see [`framework/api.md`](../framework/api.md).

---

## See also

- [`schemas/relationship.md`](../schemas/relationship.md) — full schema.
- [`relationships/protocols.md`](./protocols.md) — protocol vocabulary.
- [`entities/`](../entities/README.md) — what edges connect.
