# Technical Relationships

> How services, components, and code depend on and call each other.

**Source of truth:** [PRD §6.1, §7.2](../../PRD.md)

---

## Types covered

| Type             | Direction                              | Purpose                                                       |
| ---------------- | -------------------------------------- | ------------------------------------------------------------- |
| `depends_on`     | `(dependent) → (dependency)`           | A general logical dependency.                                 |
| `calls_api`      | `(caller) → (callee)`                  | A synchronous or async API call.                              |
| `provides_api`   | `(provider) → (consumer-or-endpoint)`  | A service exposes an API for others.                          |
| `extends`        | `(subclass) → (superclass)`            | Class/interface inheritance.                                  |
| `implements`     | `(impl) → (interface)`                 | A class implements an interface or trait.                     |

These edges typically carry a `protocol` (see
[`protocols.md`](./protocols.md)) and a `mode` (`sync`, `async`, `batch`).

---

## `depends_on`

The general-purpose dependency edge. Use when the relationship is real but
does not fit a more specific type.

Examples of valid `depends_on` uses:

- `(service.payments-api) depends_on (cache.session-store)` — the service
  is unusable if the cache is down, but it does not strictly read or write.
- `(system.billing-platform) depends_on (system.identity-platform)` — at
  the system level, before specific edges are extracted.
- `(service.email-worker) depends_on (queue.email-outbox)` — when the
  consumer/publisher distinction is unclear or both apply.

**Prefer the specific edge when possible.** `calls_api` is more useful than
`depends_on` for a REST call; `reads_from` is more useful than `depends_on`
for a database read. Use `depends_on` for documenting *coarse* relationships
during initial graph population, then refine.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.payments-depends-on-session-store
  source: service.payments-api
  target: cache.session-store
  type: depends_on
  protocol: redis
  mode: sync
  metadata:
    criticality: tier-1
    fallback_behavior: "fail-open with no rate limiting"
```

---

## `calls_api`

A synchronous or asynchronous API call from one entity to another.

### Allowed pairs
| Source       | Target                                  |
| ------------ | --------------------------------------- |
| `service`    | `service`, `api_endpoint`, `system`     |
| `component`  | `service`, `api_endpoint`               |
| `function`   | `api_endpoint`                          |

### Common protocols
`rest`, `grpc`, `graphql`, `websocket`. See
[`protocols.md`](./protocols.md).

### Metadata
| Key                | Notes                                                          |
| ------------------ | -------------------------------------------------------------- |
| `method`           | For REST: `GET`, `POST`, etc.                                  |
| `path`             | For REST: e.g. `/api/v2/verify-session`.                       |
| `service`          | For gRPC: service name.                                        |
| `rpc`              | For gRPC: method name.                                         |
| `auth`             | `oauth2`, `jwt`, `mtls`, `none`.                               |
| `timeout_ms`       | Client-side timeout.                                           |
| `retries`          | Retry count.                                                   |
| `circuit_breaker`  | Boolean.                                                       |
| `avg_qps`          | Observed rate.                                                 |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-calls-billing-verify
  source: service.auth
  target: service.billing
  type: calls_api
  protocol: rest
  mode: sync
  metadata:
    method: POST
    path: /api/v2/verify-session
    auth: oauth2
    timeout_ms: 3000
    circuit_breaker: true
```

---

## `provides_api`

The complementary edge to `calls_api`: a service exposes an API.

### Allowed pairs
| Source     | Target                              |
| ---------- | ----------------------------------- |
| `service`  | `api_endpoint`                      |
| `service`  | `service` (when target is the consumer, e.g. for a private SDK) |

`provides_api` is most useful when an `api_endpoint` exists as a separate
entity. Then the graph forms a clean triangle:

```
caller-service ──calls_api──▶ api_endpoint
                                    ▲
                                    │ provides_api
                            provider-service
```

This makes endpoint-level fragments and metadata first-class.

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-provides-verify-session
  source: service.auth
  target: endpoint.auth.verify-session
  type: provides_api
  protocol: rest
  metadata:
    spec_url: "https://api.acme.com/openapi/auth.yaml#/paths/~1api~1v2~1verify-session/post"
```

---

## `extends`

Class or interface inheritance. Use sparingly — most architectural views do
not need to know that one class extends another. Reserve for cases where
the relationship matters at component or service level.

### Allowed pairs
| Source  | Target  |
| ------- | ------- |
| `class` | `class` |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.JwtSigner-extends-AbstractSigner
  source: class.JwtSigner
  target: class.AbstractSigner
  type: extends
```

---

## `implements`

A class implements an interface, trait, or protocol type.

### Allowed pairs
| Source  | Target                                                       |
| ------- | ------------------------------------------------------------ |
| `class` | `class` (where the target represents an interface or trait)  |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.JwtSigner-implements-Signer
  source: class.JwtSigner
  target: class.Signer
  type: implements
```

---

## Documentation patterns

The most common fragments anchored to **technical edges** are:

| Lens          | Zoom range | Content                                                                                |
| ------------- | ---------- | -------------------------------------------------------------------------------------- |
| `technical`   | 35–70      | The contract (method, path, schema, headers).                                          |
| `operations`  | 40–65      | Rate limits, SLAs the caller must respect.                                             |
| `debug`       | 55–95      | Failure modes, retry behavior, what 4xx vs 5xx mean.                                   |
| `client`      | 35–65      | If the API is consumed externally, the public-facing version of the same content.     |

A `calls_api` edge is a great anchor for the fragment *"if you see 429s on
this edge, the callee throttles to 500 req/s; circuit breaker opens after
3 consecutive failures."*

---

## See also

- [`relationships/protocols.md`](./protocols.md) — the protocol vocabulary.
- [`relationships/data-flow.md`](./data-flow.md) — Kafka, queues, DBs.
- [`entities/technical.md`](../entities/technical.md) — endpoints of these edges.
