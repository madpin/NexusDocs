# Protocols

> Edge metadata that captures *how* two entities communicate.

**Source of truth:** [PRD §6.1, §7.2](../../PRD.md)

---

## Why protocols are first-class

A primary differentiator of NexusDocs from existing tools is **protocol-aware
relationships**. A relationship that says "Service A talks to Service B" is
half a story; you also want to know *over what*: REST, gRPC, Kafka, a shared
database, a queue, a cache, a websocket.

The PRD lists this as Goal G6 and as the only "✅" capability under
"Protocol-aware relationships" in Appendix B. See
[PRD §G6, App B](../../PRD.md).

---

## The protocol vocabulary

The `protocol` field on a relationship is one of:

| Protocol      | Used with edge types                                      | Typical `mode` |
| ------------- | --------------------------------------------------------- | -------------- |
| `rest`        | `calls_api`, `provides_api`                               | `sync`         |
| `grpc`        | `calls_api`, `provides_api`                               | `sync`         |
| `graphql`     | `calls_api`, `provides_api`                               | `sync`         |
| `websocket`   | `calls_api`                                               | `async`        |
| `kafka`       | `publishes_to`, `consumes_from`, `streams_to`             | `async`        |
| `pubsub`      | `publishes_to`, `consumes_from`                           | `async`        |
| `sqs`         | `publishes_to`, `consumes_from`                           | `async`        |
| `sns`         | `publishes_to`                                            | `async`        |
| `rabbitmq`    | `publishes_to`, `consumes_from`                           | `async`        |
| `postgres`    | `reads_from`, `writes_to`                                 | `sync`         |
| `mysql`       | `reads_from`, `writes_to`                                 | `sync`         |
| `mongodb`     | `reads_from`, `writes_to`                                 | `sync`         |
| `dynamodb`    | `reads_from`, `writes_to`                                 | `sync`         |
| `redis`       | `reads_from`, `writes_to`                                 | `sync`         |
| `memcached`   | `reads_from`, `writes_to`                                 | `sync`         |
| `s3`          | `reads_from`, `writes_to`                                 | `sync`         |
| `null` / unset | organizational and documentation edges                   | n/a            |

The platform treats `protocol` as an enum but stores it as a string;
organizations may extend it (e.g. `nats`, `kinesis`, `cassandra`, `bigtable`)
without code changes.

---

## `mode`: sync vs async vs batch

Orthogonal to `protocol`, the `mode` field captures **timing**:

| Mode      | Meaning                                                                     |
| --------- | --------------------------------------------------------------------------- |
| `sync`    | The caller blocks until the callee responds. REST, gRPC, DB queries.        |
| `async`   | Fire-and-forget or eventual response. Kafka, queues, websockets.            |
| `batch`   | Periodic bulk movement of data. ETL jobs, scheduled imports.                |
| `null`    | Unset — applies to organizational and documentation edges.                  |

A single edge has exactly one `mode`. If the same source–target pair has
both sync and async traffic, model two edges (one per mode) with different
IDs.

---

## How to choose `protocol` and `mode`

```
                ┌──────────────────────────────────────────────────────┐
                │ Does data go to a topic / queue?                     │
                └────────────┬───────────────────────────┬─────────────┘
                             │ yes                       │ no
                             ▼                           ▼
                ┌────────────────────────┐    ┌──────────────────────┐
                │ kafka / sqs / pubsub / │    │ Does data go to a DB │
                │ rabbitmq / sns ?       │    │ or cache?            │
                └────────────┬───────────┘    └────────────┬─────────┘
                             │ async                       │ yes
                             ▼                             ▼
                ┌─────────────────────┐    ┌──────────────────────────┐
                │ publishes_to /      │    │ postgres / mysql /       │
                │ consumes_from /     │    │ mongodb / dynamodb /     │
                │ streams_to          │    │ redis / memcached / s3   │
                └─────────────────────┘    │   sync                   │
                                           │ reads_from / writes_to   │
                                           └──────────────────────────┘
                                                          │ no
                                                          ▼
                                           ┌──────────────────────────┐
                                           │ rest / grpc / graphql /  │
                                           │ websocket                │
                                           │   sync (or async for ws) │
                                           │ calls_api / provides_api │
                                           └──────────────────────────┘
```

If the answer is "this is a coarse logical dependency, not a specific call":
use `depends_on` and skip `protocol`.

---

## Protocol-specific metadata

Each protocol has a small set of conventional metadata keys. The platform
does not enforce these; they are recommended for searchability.

### `rest`
```yaml
metadata:
  method: POST                # GET | POST | PUT | DELETE | PATCH
  path: /api/v2/verify-session
  auth: oauth2                # none | basic | jwt | oauth2 | mtls
  timeout_ms: 3000
  retries: 2
  circuit_breaker: true
  status_codes: [200, 401, 429, 500]
```

### `grpc`
```yaml
metadata:
  service: identity.v1.AuthService
  rpc: VerifySession
  auth: mtls
  streaming: false            # bidirectional / server / client / false
  timeout_ms: 1500
```

### `graphql`
```yaml
metadata:
  operation: query
  operation_name: getUser
  schema_url: "https://api.acme.com/graphql/schema.graphql"
```

### `websocket`
```yaml
metadata:
  path: /ws/notifications
  auth: jwt
  heartbeat_s: 30
  reconnection: client_initiated
```

### `kafka`
```yaml
metadata:
  topic: user.events.v1
  cluster: kafka_cluster.core-kafka-prod
  partitions: 12
  key_schema: user_id
  value_format: avro          # avro | protobuf | json
  consumer_group: billing-user-events-v3
  delivery: at_least_once     # at_most_once | at_least_once | exactly_once
```

### `sqs`, `sns`, `pubsub`, `rabbitmq`
```yaml
metadata:
  queue: email-outbox
  region: us-east-1
  visibility_timeout_s: 30
  dlq: queue.email-outbox-dlq
```

### `postgres`, `mysql`
```yaml
metadata:
  tables: [transactions, invoices]
  read_replicas: true         # for reads_from
  transactional: true         # for writes_to
  consistency: read_your_writes
  connection_pool_size: 20
```

### `mongodb`, `dynamodb`
```yaml
metadata:
  collections: [sessions]     # mongodb
  table: Sessions             # dynamodb
  consistency: eventual
  partition_key: user_id      # dynamodb
```

### `redis`, `memcached`
```yaml
metadata:
  key_pattern: "session:{user_id}"
  ttl_s: 3600
  eviction_policy: allkeys-lru
```

### `s3`
```yaml
metadata:
  bucket: acme-billing-archives
  prefix: invoices/2026/
  region: us-east-1
```

---

## Querying by protocol

Protocol-aware queries are first-class:

```
"Which services depend on Kafka?"
→ entities reachable via type ∈ {publishes_to, consumes_from, streams_to}
   AND protocol = kafka

"Which services use Postgres?"
→ entities reachable via type ∈ {reads_from, writes_to}
   AND protocol = postgres

"Show me only the gRPC traffic into auth-service"
→ filter: target = service.auth, type = calls_api, protocol = grpc
```

The View API exposes this as the `filters.protocols` field. See
[`framework/api.md`](../framework/api.md).

---

## See also

- [`relationships/data-flow.md`](./data-flow.md) — `publishes_to`, `consumes_from`, `reads_from`, `writes_to`, `streams_to`.
- [`relationships/technical.md`](./technical.md) — `calls_api`, `provides_api`.
- [`schemas/relationship.md`](../schemas/relationship.md) — full edge schema.
