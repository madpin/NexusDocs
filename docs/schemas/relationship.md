# Relationship schema

> The full format for a directed edge between two entities.

**Source of truth:** [PRD §7.2](../../PRD.md)

---

## Schema

```yaml
Relationship:
  id: string                    # Required. Stable identifier, e.g. "rel.auth-publishes-user-events".
  source: string                # Required. Source entity ID.
  target: string                # Required. Target entity ID.
  type: enum                    # Required. See enum below.
  protocol: string | null       # Optional. Transport / storage protocol.
  mode: enum | null             # Optional. sync | async | batch.
  metadata: map<string, any>    # Optional. Type-and-protocol-specific fields.
  created_at: datetime          # Auto.
  updated_at: datetime          # Auto.
  source_ref: SourceRef         # Optional. Where this edge was discovered.
```

---

## YAML envelope

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-publishes-user-events
  source: service.auth
  target: topic.user-events
  type: publishes_to
  protocol: kafka
  mode: async
  metadata:
    topic: user.events.v1
    key_schema: user_id
    value_format: avro
```

---

## Field reference

### `id` (string, required)

Convention: `rel.<source-short>-<verb>-<target-short>`. Pattern:
`^[a-z][a-z0-9.-]*$`. Max 200 chars.

### `source`, `target` (string, required)

Entity IDs. Both must exist. Edges are **directed**: `source` and `target`
are not interchangeable.

A relationship cannot be created if `source` or `target` does not exist.
When using `nexdoc apply` on a multi-document YAML, the platform sorts so
that entities are created before relationships referring to them.

### `type` (enum, required)

One of:

```
# Organizational
belongs_to | owns | leads | member_of | reports_to

# Technical
depends_on | calls_api | provides_api | extends | implements

# Data flow
publishes_to | consumes_from | reads_from | writes_to | streams_to

# Documentation
describes | references | supersedes
```

See:

- [`relationships/organizational.md`](../relationships/organizational.md)
- [`relationships/technical.md`](../relationships/technical.md)
- [`relationships/data-flow.md`](../relationships/data-flow.md)
- [`relationships/documentation.md`](../relationships/documentation.md)

### `protocol` (string | null, optional)

The transport or storage protocol. One of (extensible):

```
# Sync APIs
rest | grpc | graphql | websocket

# Async messaging
kafka | pubsub | sqs | sns | rabbitmq | nats

# Storage / DB
postgres | mysql | mongodb | dynamodb | redis | memcached | s3 | bigtable | cassandra
```

Organizational and documentation edges typically have `protocol: null`.
See [`relationships/protocols.md`](../relationships/protocols.md).

### `mode` (enum | null, optional)

```
sync | async | batch | null
```

Conventionally:
- `sync` for REST, gRPC, DB queries.
- `async` for Kafka, queues, websockets.
- `batch` for ETL jobs, scheduled imports.

### `metadata` (map, optional)

Free-form, but conventional keys exist for each protocol. See
[`relationships/protocols.md`](../relationships/protocols.md) for the
recommended keys per protocol.

A relationship may carry **dynamic** metadata that changes over time
(e.g. `avg_qps`, `error_rate_24h`). These are typically populated by
ingestion connectors from monitoring data, not authored by hand.

### `source_ref` (SourceRef, optional)

Where this edge was discovered. Common values:

| Source                         | `source_type`                    |
| ------------------------------ | -------------------------------- |
| Manual YAML                    | `manual`                         |
| Extracted from a README        | `readme`                         |
| Extracted from a docker-compose | `config_file`                   |
| Extracted from an OpenAPI spec | `api_spec`                       |
| Inferred by an LLM             | `llm_generated`                  |

---

## Validation

| Rule                                                                            |
| ------------------------------------------------------------------------------- |
| `id` matches `^[a-z][a-z0-9.-]*$`, max 200 chars.                                |
| `source` and `target` refer to existing entities.                               |
| `type` is in the enum above.                                                    |
| `mode` (if set) is one of `sync`, `async`, `batch`.                             |
| `protocol` is recommended for `calls_api`, `provides_api`, `publishes_to`,      |
| `consumes_from`, `reads_from`, `writes_to`, `streams_to`. Not validated, but    |
| flagged for review on creation.                                                 |

---

## Worked examples

### REST call

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.payments-api-calls-auth
  source: service.payments-api
  target: service.auth
  type: calls_api
  protocol: rest
  mode: sync
  metadata:
    method: POST
    path: /api/v2/verify-session
    auth: oauth2
    timeout_ms: 3000
    circuit_breaker: true
    avg_qps: 850
```

### Kafka publish

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-publishes-user-events
  source: service.auth
  target: topic.user-events
  type: publishes_to
  protocol: kafka
  mode: async
  metadata:
    topic: user.events.v1
    key_schema: user_id
    value_format: avro
    avg_throughput: "1200 msgs/sec"
```

### Database write

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.billing-writes-transactions-db
  source: service.billing
  target: database.transactions
  type: writes_to
  protocol: postgres
  mode: sync
  metadata:
    tables: [transactions, invoices, payment_methods]
    transactional: true
    connection_pool_size: 20
```

### Person on a team

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.tpinto-member-of-payments
  source: person.tpinto
  target: team.payments
  type: member_of
  metadata:
    share: 0.8
    since: "2024-01-01"
```

### Team owns service

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.payments-owns-payments-api
  source: team.payments
  target: service.payments-api
  type: owns
```

---

## See also

- [`schemas/entity.md`](./entity.md) — what edges connect.
- [`relationships/protocols.md`](../relationships/protocols.md) — the protocol vocabulary.
- [`relationships/`](../relationships/README.md) — type-by-type documentation.
