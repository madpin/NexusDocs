# Entities

> What can be a node in the NexusDocs graph.

**Source of truth:** [PRD §6.1](../../PRD.md), [PRD §7.1](../../PRD.md)

---

## What is an Entity?

An **Entity** is a node in the graph. It represents *something that exists*:
a team, a service, a database, a Kafka topic, a person, a document.

Every entity has:

- An immutable `id`.
- A `kind` from a fixed enum (see below).
- A human-readable `name`.
- Optional `parent` for hierarchical containment.
- Freeform `labels` and a `metadata` map for kind-specific fields.
- Provenance: where the entity was discovered or defined.

The full schema is in [`schemas/entity.md`](../schemas/entity.md).

---

## Entity taxonomy

Entities are grouped into four documentation categories. Each has its own doc:

| Category                                         | Kinds                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| [Organizational](./organizational.md)            | `company`, `division`, `tribe`, `team`, `person`                               |
| [Technical](./technical.md)                      | `system`, `service`, `component`, `class`, `function`                          |
| [Infrastructure](./infrastructure.md)            | `database`, `kafka_cluster`, `kafka_topic`, `api_endpoint`, `queue`, `cache`   |
| [Documentation](./documentation.md)              | `document`, `doc_fragment`                                                     |

These categories are documentation conveniences — the platform itself only
sees `kind` strings.

---

## Kind ↔ default zoom band

Each kind has a *natural* zoom band where it tends to live as a focus. This
is guidance, not enforcement:

| Kind              | Typical focus zoom |
| ----------------- | ------------------ |
| `company`         | 0–10               |
| `division`        | 5–20               |
| `tribe`           | 10–25              |
| `team`            | 15–35              |
| `person`          | 20–40              |
| `system`          | 20–45              |
| `service`         | 35–65              |
| `component`       | 55–80              |
| `class`           | 75–95              |
| `function`        | 85–100             |
| `database`        | 40–70              |
| `kafka_cluster`   | 30–55              |
| `kafka_topic`     | 45–70              |
| `api_endpoint`    | 50–75              |
| `queue`           | 45–70              |
| `cache`           | 50–75              |
| `document`        | matches its content |
| `doc_fragment`    | declared explicitly |

A reader can focus on any entity at any zoom; these bands inform fragment
authors where to set `coverage.zoom_min` / `zoom_max`.

---

## ID conventions

Entity IDs follow the pattern `<kind>.<short-name>`:

| Kind             | Example IDs                                                          |
| ---------------- | -------------------------------------------------------------------- |
| `company`        | `company.acme`                                                       |
| `division`       | `division.fintech`, `division.platform`                              |
| `tribe`          | `tribe.payments-experience`                                          |
| `team`           | `team.payments`, `team.identity`                                     |
| `person`         | `person.tpinto`                                                      |
| `system`         | `system.identity-platform`, `system.billing-platform`                |
| `service`        | `service.auth`, `service.payments-api`                               |
| `component`      | `component.token-issuer`                                             |
| `class`          | `class.JwtSigner`                                                    |
| `function`       | `function.signToken`                                                 |
| `database`       | `database.transactions`, `database.users`                            |
| `kafka_cluster`  | `kafka_cluster.core-kafka-prod`                                      |
| `kafka_topic`    | `topic.user-events`, `topic.order-events`                            |
| `api_endpoint`   | `endpoint.auth.verify-session`                                       |
| `queue`          | `queue.email-outbox`                                                 |
| `cache`          | `cache.session-store`                                                |
| `document`       | `doc.payments-overview`                                              |
| `doc_fragment`   | `docfrag.auth-overview`                                              |

(The `kafka_topic` kind uses the `topic.` prefix as a shorthand; the `kind`
field still says `kafka_topic`.)

---

## Authoring an entity

Minimum viable entity:

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.auth
  type: service
  name: Auth Service
```

That alone is a valid graph node. Add `parent`, `labels`, and `metadata` as
needed. See each category page for kind-specific metadata patterns.

---

## See also

- [`schemas/entity.md`](../schemas/entity.md) — full schema and validation rules.
- [`relationships/`](../relationships/README.md) — how entities connect.
- [`schemas/yaml-format.md`](../schemas/yaml-format.md) — YAML conventions.
