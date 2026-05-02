# Entity schema

> The full format for a node in the graph.

**Source of truth:** [PRD §7.1](../../PRD.md)

---

## Schema

```yaml
Entity:
  id: string                    # Required. Stable identifier, e.g. "service.auth".
  kind: enum                    # Required. See enum below.
  name: string                  # Required. Human-readable label.
  parent: string | null         # Optional. Parent entity ID for hierarchical containment.
  labels: string[]              # Optional. Freeform tags for cross-cutting concerns.
  metadata: map<string, any>    # Optional. Kind-specific structured fields.
  created_at: datetime          # Auto. Set on creation.
  updated_at: datetime          # Auto. Touched on every update.
  source: SourceRef             # Optional. Where this entity was discovered.
```

---

## YAML envelope

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.auth
  type: service                 # Note: written `type` in YAML; stored as `kind`.
  name: Auth Service
  parent: system.identity-platform
  labels: [authentication, tier-1]
  metadata:
    technology: "Node.js / Express"
    repository: "https://gitlab.com/acme/auth-service"
```

> **YAML quirk:** the field `type:` in `spec` corresponds to the schema
> field `kind`. This is to avoid conflict with the envelope's outer `kind:
> Entity` and matches the Backstage convention. Both `type:` and `kind:`
> are accepted in `spec`, but `type:` is preferred.

---

## Field reference

### `id` (string, required)

A stable URL-safe identifier. Pattern: `^[a-z][a-z0-9.-]*$`. Max 200 chars.

Conventional form: `<kind>.<short-name>`, e.g. `service.auth`. See
[`entities/README.md`](../entities/README.md#id-conventions) for the full
table.

### `kind` (enum, required)

One of the following values. The set is closed; new kinds require a
platform release.

```
company | division | tribe | team | person |
system | service | component | class | function |
database | kafka_cluster | kafka_topic | api_endpoint | queue | cache |
document | doc_fragment
```

See:

- [`entities/organizational.md`](../entities/organizational.md) for the first row.
- [`entities/technical.md`](../entities/technical.md) for the second row.
- [`entities/infrastructure.md`](../entities/infrastructure.md) for the third row.
- [`entities/documentation.md`](../entities/documentation.md) for the last row.

### `name` (string, required)

Human-readable label. Not used as an identifier. Can be changed without
breaking references.

### `parent` (string | null, optional)

The ID of a parent entity. Used for hierarchical containment:

| Child kind        | Allowed parent kinds                       |
| ----------------- | ------------------------------------------ |
| `division`        | `company`                                  |
| `tribe`           | `division`                                 |
| `team`            | `tribe`, `division`                        |
| `service`         | `system`                                   |
| `component`       | `service`                                  |
| `class`           | `component`, `service`                     |
| `function`        | `class`, `component`, `service`            |
| `kafka_topic`     | `kafka_cluster`                            |
| `api_endpoint`    | `service`                                  |
| `doc_fragment`    | (none — uses `subjects` instead)           |
| any other         | (none, or organization-defined)            |

Setting `parent` implicitly creates a `belongs_to` edge from child to
parent. You do not need to also create the edge explicitly.

### `labels` (string[], optional)

Freeform tags. Use for cross-cutting concerns that don't fit metadata:
`[tier-1, pii, regulated, deprecated]`.

Labels are queryable. They also drive **fragment polyattachment** via
`tags`: a fragment whose `tags` intersect an entity's `labels` is treated as
relevant to that entity. See [`schemas/doc-fragment.md`](./doc-fragment.md).

### `metadata` (map, optional)

A free-form map of kind-specific fields. The platform does not validate the
schema of `metadata`, but conventional keys are listed in each entity
category page:

- [Organizational metadata](../entities/organizational.md)
- [Technical metadata](../entities/technical.md)
- [Infrastructure metadata](../entities/infrastructure.md)
- [Documentation metadata](../entities/documentation.md)

### `source` (SourceRef, optional)

Where this entity was discovered or defined. Set automatically by ingestion
connectors. Manual entries should set it to indicate `manual`:

```yaml
source:
  source_type: manual
  source_path: "ops/nexusdocs/entities/payments.yaml"
```

---

## Validation

| Rule                                                                            |
| ------------------------------------------------------------------------------- |
| `id` matches `^[a-z][a-z0-9.-]*$`, max 200 chars.                                |
| `kind` is in the enum above.                                                    |
| `parent` (if set) refers to an existing entity.                                 |
| `parent.kind` is allowed for the given `kind` (see table above).                |
| `labels` are unique within the array.                                           |
| `metadata` is a map with string keys.                                           |

---

## Worked examples

### Service with full metadata

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.payments-api
  type: service
  name: Payments API
  parent: system.billing-platform
  labels: [tier-1, pci]
  metadata:
    technology: "Go / Echo"
    repository: "https://gitlab.com/acme/payments-api"
    deployment: "k8s/us-east-1/payments"
    primary_language: go
    sla_uptime: "99.95%"
    runbook_url: "https://runbooks.acme.com/payments-api"
```

### Person

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: person.tpinto
  type: person
  name: Thiago M Pinto
  metadata:
    ldap: tpinto
    email: tpinto@acme.com
    role: "Principal Developer"
    timezone: "Europe/Dublin"
```

### Kafka topic

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: topic.user-events
  type: kafka_topic
  name: user.events.v1
  parent: kafka_cluster.core-kafka-prod
  labels: [pii, retention-7d]
  metadata:
    partitions: 12
    retention_days: 7
    schema_registry: "https://schema-registry.internal/subjects/user-events-value"
    avg_throughput: "1200 msgs/sec"
```

### Document

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: doc.auth-readme
  type: document
  name: Auth Service README
  metadata:
    source_type: readme
    source_path: "https://gitlab.com/acme/auth-service/-/blob/main/README.md"
    source_hash: "sha256:1f9b…"
    last_synced: "2026-04-29T10:11:00Z"
```

---

## See also

- [`schemas/relationship.md`](./relationship.md) — what edges connect these entities.
- [`schemas/doc-fragment.md`](./doc-fragment.md) — how fragments anchor to these entities.
- [`schemas/yaml-format.md`](./yaml-format.md) — the envelope and bulk apply.
- [`entities/`](../entities/README.md) — the documentation companion of this reference.
