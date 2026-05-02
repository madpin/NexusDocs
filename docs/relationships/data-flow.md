# Data-Flow Relationships

> Where data moves: Kafka, queues, databases, caches.

**Source of truth:** [PRD §6.1, §7.2](../../PRD.md)

---

## Types covered

| Type             | Direction                              | Purpose                                                       |
| ---------------- | -------------------------------------- | ------------------------------------------------------------- |
| `publishes_to`   | `(producer) → (topic\|queue)`          | A service writes events to a topic or queue.                  |
| `consumes_from`  | `(consumer) → (topic\|queue)`          | A service reads events from a topic or queue.                 |
| `reads_from`     | `(reader) → (database\|cache)`         | A service reads from a persistent store.                      |
| `writes_to`      | `(writer) → (database\|cache)`         | A service writes to a persistent store.                       |
| `streams_to`     | `(producer) → (sink)`                  | Stream-processing semantics: continuous rather than discrete. |

These edges typically carry a `protocol` (see
[`protocols.md`](./protocols.md)) and a `mode` (`sync`, `async`, `batch`).

Data-flow edges are where the platform's "protocol-aware" promise pays off.
*"Which services write to this database?"* and *"Who consumes
user-events?"* should be one-hop graph queries.

---

## `publishes_to`

A service or component sends events to a topic or queue.

### Allowed pairs
| Source       | Target                          |
| ------------ | ------------------------------- |
| `service`    | `kafka_topic`, `queue`          |
| `component`  | `kafka_topic`, `queue`          |

### Common protocols
`kafka`, `sqs`, `sns`, `rabbitmq`, `pubsub`. Default `mode: async`.

### Metadata
| Key               | Notes                                                       |
| ----------------- | ----------------------------------------------------------- |
| `topic`           | Kafka: full topic name (often equals `target.metadata.name`). |
| `key_schema`      | Kafka: partition-key strategy, e.g. `user_id`.              |
| `value_format`    | `avro`, `protobuf`, `json`.                                  |
| `avg_throughput`  | Observed rate.                                              |
| `compression`     | `snappy`, `lz4`, `zstd`.                                    |

### Example

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

---

## `consumes_from`

A service reads events from a topic or queue.

### Allowed pairs
| Source       | Target                          |
| ------------ | ------------------------------- |
| `service`    | `kafka_topic`, `queue`          |
| `component`  | `kafka_topic`, `queue`          |

### Metadata
| Key                | Notes                                                       |
| ------------------ | ----------------------------------------------------------- |
| `consumer_group`   | Kafka: consumer-group ID.                                   |
| `from_offset`      | `earliest`, `latest`, or specific offset.                   |
| `delivery`         | `at_most_once`, `at_least_once`, `exactly_once`.            |
| `parallelism`      | Number of consumer instances.                               |
| `dlq`              | Dead-letter queue/topic ID, if any.                         |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.billing-consumes-user-events
  source: service.billing
  target: topic.user-events
  type: consumes_from
  protocol: kafka
  mode: async
  metadata:
    consumer_group: billing-user-events-v3
    from_offset: latest
    delivery: at_least_once
    parallelism: 6
    dlq: topic.billing-user-events-dlq
```

---

## `reads_from`

A service reads from a persistent store.

### Allowed pairs
| Source       | Target                |
| ------------ | --------------------- |
| `service`    | `database`, `cache`   |
| `component`  | `database`, `cache`   |

### Common protocols
`postgres`, `mysql`, `mongodb`, `dynamodb`, `redis`, `memcached`, `s3`.

### Metadata
| Key                  | Notes                                                       |
| -------------------- | ----------------------------------------------------------- |
| `tables` / `keys`    | Which tables (SQL) or key prefixes (KV) are read.           |
| `read_replicas`      | Whether reads target replicas.                              |
| `consistency`        | `strong`, `eventual`, `read_your_writes`.                   |
| `connection_pool_size` |                                                           |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.billing-reads-transactions-db
  source: service.billing
  target: database.transactions
  type: reads_from
  protocol: postgres
  mode: sync
  metadata:
    tables: [transactions, invoices, payment_methods]
    read_replicas: true
    consistency: read_your_writes
    connection_pool_size: 20
```

---

## `writes_to`

A service writes to a persistent store.

### Allowed pairs
Same as `reads_from`.

### Metadata
| Key                  | Notes                                                       |
| -------------------- | ----------------------------------------------------------- |
| `tables`             | Tables written to.                                          |
| `transactional`      | Whether writes are wrapped in DB transactions.              |
| `connection_pool_size` |                                                           |

### Example

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

A service that both reads and writes the same database typically has both
edges. They are intentionally separate so queries like *"who only reads vs
also writes"* are easy.

---

## `streams_to`

Stream-processing semantics. Use when the source continuously emits
records into the target rather than publishing discrete events.

### Allowed pairs
| Source                      | Target                                                              |
| --------------------------- | ------------------------------------------------------------------- |
| `service`, `component`      | `kafka_topic`, `database`, `queue` (when fed by a stream processor) |

### Metadata
| Key             | Notes                                                       |
| --------------- | ----------------------------------------------------------- |
| `framework`     | `kafka_streams`, `flink`, `spark_streaming`, `kinesis`.     |
| `state_store`   | Backing state store for the streaming job.                  |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.fraud-streams-to-suspicious-events
  source: service.fraud-detector
  target: topic.suspicious-events
  type: streams_to
  protocol: kafka
  mode: async
  metadata:
    framework: kafka_streams
    state_store: rocksdb
```

`streams_to` is semantically distinct from `publishes_to`: the latter
implies discrete events emitted in response to a trigger; the former
implies a continuous transformation pipeline.

---

## `publishes_to` vs `writes_to`

| Question                                    | Use            |
| ------------------------------------------- | -------------- |
| Does the data go into a topic / queue?      | `publishes_to` |
| Does the data go into a database / cache?   | `writes_to`    |
| Is it a continuous stream into either?      | `streams_to`   |

The protocol field disambiguates the rest. A `publishes_to` with `protocol:
sqs` is a queue write. A `writes_to` with `protocol: redis` is a cache
write.

---

## Documentation patterns

Data-flow edges deserve fragments that combine **technical** and
**debug**:

| Lens          | Zoom range | Example content                                                          |
| ------------- | ---------- | ------------------------------------------------------------------------ |
| `technical`   | 45–70      | Schema, partitioning, idempotency.                                       |
| `operations`  | 50–70      | Consumer-lag SLO, on-call runbook for the topic.                         |
| `debug`       | 60–90      | What out-of-order messages look like; how to replay safely.              |

A particularly useful pattern: anchor a single fragment to **multiple**
data-flow edges that share a Kafka topic. Tag it with the topic name so
that it polyattaches across the whole topology.

---

## See also

- [`entities/infrastructure.md`](../entities/infrastructure.md) — the things data flows into.
- [`relationships/protocols.md`](./protocols.md) — Kafka, SQL, Redis, etc.
- [`relationships/technical.md`](./technical.md) — `calls_api`, `depends_on`.
- [`concepts/topology.md`](../concepts/topology.md) — why high-fanout data flows trigger lifting.
