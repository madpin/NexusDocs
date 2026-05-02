# Infrastructure Entities

> The runtime fabric services depend on.

**Source of truth:** [PRD §6.1, §7.1](../../PRD.md)

---

## Kinds covered

| Kind             | Purpose                                                       | Typical zoom |
| ---------------- | ------------------------------------------------------------- | ------------ |
| `database`       | A relational, document, or key-value store.                   | 40–70        |
| `kafka_cluster`  | A Kafka deployment hosting one or more topics.                | 30–55        |
| `kafka_topic`    | A specific Kafka topic.                                       | 45–70        |
| `api_endpoint`   | A specific REST/gRPC route exposed by a service.              | 50–75        |
| `queue`          | A message queue (SQS, RabbitMQ, etc.).                        | 45–70        |
| `cache`          | A cache layer (Redis, Memcached).                             | 50–75        |

Infrastructure entities are typically the "shared waterworks" of an
organization: many services depend on the same Kafka cluster, the same
database, or the same cache. This makes them **prime candidates for topology
lifting** — see [`concepts/topology.md`](../concepts/topology.md).

---

## `database`

A persistent data store. Use this for any DB engine: Postgres, MySQL,
MongoDB, DynamoDB, Cassandra, etc.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: database.transactions
  type: database
  name: Transactions DB
  labels: [tier-1, postgres]
  metadata:
    engine: postgres
    version: "15"
    deployment: "rds/us-east-1/payments-prod"
    size_gb: 1200
    ha: true
    read_replicas: 2
    backup_policy: "daily-7d"
    pii: true
```

Recommended `metadata` keys:

| Key             | Type    | Notes                                       |
| --------------- | ------- | ------------------------------------------- |
| `engine`        | string  | `postgres`, `mysql`, `mongodb`, `dynamodb`. |
| `version`       | string  |                                             |
| `deployment`    | string  | `rds/region/name`, `aurora/...`.            |
| `pii`           | bool    | Whether the DB stores PII.                  |
| `read_replicas` | int     |                                             |
| `backup_policy` | string  |                                             |

### Common relationships
- `(team) owns (database)`
- `(service) reads_from (database)` (with `protocol: postgres|mysql|...`)
- `(service) writes_to (database)`

### Documentation patterns
- `lens=technical`, zoom 45–75: schema overview, indexes.
- `lens=operations`, zoom 40–65: backup/restore, on-call.
- `lens=debug`, zoom 60–85: known slow queries, lock patterns.

---

## `kafka_cluster`

A Kafka deployment. One cluster typically hosts many topics; the cluster
itself is the entity that services depend on.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: kafka_cluster.core-kafka-prod
  type: kafka_cluster
  name: Core Kafka (prod)
  labels: [tier-1, shared]
  metadata:
    region: "us-east-1"
    broker_count: 9
    version: "3.6"
    schema_registry: "https://schema-registry.internal"
    auth: sasl_scram
```

### Common relationships
- `(team) owns (kafka_cluster)`
- `(kafka_topic) belongs_to (kafka_cluster)` — via `parent`.

### Why it deserves its own entity

A Kafka cluster is exactly the kind of node where topology-aware lifting
shines. When a viewport contains many services that all touch the same
cluster, fragments authored at the cluster level (e.g. retention policy,
SASL config, broker outages) lift into team-level views automatically.

---

## `kafka_topic`

A single Kafka topic. ID convention: `topic.<name>`, but `kind` is
`kafka_topic`.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: topic.user-events
  type: kafka_topic
  name: user.events.v1
  parent: kafka_cluster.core-kafka-prod
  labels: [user-data, pii]
  metadata:
    cluster: kafka_cluster.core-kafka-prod
    partitions: 12
    retention_days: 7
    schema_registry: "https://schema-registry.internal/subjects/user-events-value"
    key_schema: "user_id (string)"
    value_format: avro
    avg_throughput: "1200 msgs/sec"
    compacted: false
```

### Common relationships
- `(service) publishes_to (kafka_topic)` (with `protocol: kafka, mode: async`)
- `(service) consumes_from (kafka_topic)`
- `(service) streams_to (kafka_topic)` — for stream-processing semantics.

### Documentation patterns
- `lens=technical`, zoom 50–75: schema, key strategy, partitioning.
- `lens=client`, zoom 45–65: how to subscribe (for external partners).
- `lens=debug`, zoom 65–95: consumer-lag patterns, replay procedures.
- `lens=operations`, zoom 50–70: alerting on consumer lag, SLA.

The fragment about a topic should set `lift_on.cluster_coverage_threshold:
0.5` so that high-fanout topics surface earlier in views.

---

## `api_endpoint`

A specific HTTP/gRPC route exposed by a service. Use this when the
endpoint-level granularity matters — typically tier-1 APIs, public APIs, or
heavily-used internal APIs.

> Not every endpoint needs to be modeled. A service with hundreds of
> internal handlers should usually be documented at the service level, with
> only its top-level public endpoints elevated to entity status.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: endpoint.auth.verify-session
  type: api_endpoint
  name: POST /api/v2/verify-session
  parent: service.auth
  labels: [public, auth]
  metadata:
    method: POST
    path: "/api/v2/verify-session"
    protocol: rest
    auth: oauth2
    rate_limit: "500 req/s per consumer"
    avg_latency_p95_ms: 18
    spec_url: "https://api.acme.com/openapi/auth.yaml#/paths/~1api~1v2~1verify-session/post"
```

### Common relationships
- `(service) provides_api (api_endpoint)` — via `parent` and explicit edge.
- `(service) calls_api (api_endpoint)` — from a consuming service.

---

## `queue`

A message queue. Use for SQS, RabbitMQ, Cloud Tasks, and similar.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: queue.email-outbox
  type: queue
  name: email-outbox
  labels: [notifications]
  metadata:
    engine: sqs
    region: "us-east-1"
    visibility_timeout_s: 30
    dlq: queue.email-outbox-dlq
    avg_depth: 200
```

### Common relationships
- `(service) publishes_to (queue)` (`mode: async`)
- `(service) consumes_from (queue)`

---

## `cache`

A cache layer. Use for Redis, Memcached, in-memory caches.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: cache.session-store
  type: cache
  name: Session Store
  labels: [tier-1]
  metadata:
    engine: redis
    version: "7.2"
    deployment: "elasticache/us-east-1/session-store"
    eviction_policy: "allkeys-lru"
    avg_hit_rate: 0.92
```

### Common relationships
- `(service) reads_from (cache)`
- `(service) writes_to (cache)`

---

## Worked example: services around a topic

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: kafka_cluster.core-kafka-prod
  type: kafka_cluster
  name: Core Kafka (prod)

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: topic.user-events
  type: kafka_topic
  name: user.events.v1
  parent: kafka_cluster.core-kafka-prod
  metadata:
    partitions: 12
    retention_days: 7

---
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-publishes-user-events
  source: service.auth
  target: topic.user-events
  type: publishes_to
  protocol: kafka
  mode: async

---
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.billing-consumes-user-events
  source: service.billing
  target: topic.user-events
  type: consumes_from
  protocol: kafka
  mode: async
```

This graph supports queries like:

- *"Who consumes user-events?"* → reverse `consumes_from` from
  `topic.user-events`.
- *"Which topics live on core-kafka-prod?"* → entities where
  `parent = kafka_cluster.core-kafka-prod`.

---

## See also

- [`relationships/data-flow.md`](../relationships/data-flow.md) — `publishes_to`, `consumes_from`, `reads_from`, `writes_to`, `streams_to`.
- [`relationships/protocols.md`](../relationships/protocols.md) — Kafka, REST, gRPC, SQL, etc.
- [`concepts/topology.md`](../concepts/topology.md) — why infrastructure entities lift early.
