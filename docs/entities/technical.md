# Technical Entities

> Software artifacts that exist in code and runtime.

**Source of truth:** [PRD §6.1, §7.1](../../PRD.md)

---

## Kinds covered

| Kind        | Purpose                                                          | Typical zoom |
| ----------- | ---------------------------------------------------------------- | ------------ |
| `system`    | A coherent product or platform composed of services.             | 20–45        |
| `service`   | A deployable unit (microservice, lambda, daemon).                | 35–65        |
| `component` | A module, package, or feature inside a service.                  | 55–80        |
| `class`     | A class, interface, or struct in code.                           | 75–95        |
| `function`  | A function or method.                                            | 85–100       |

These five kinds form a containment chain via `parent`:

```
system
  └── service
        └── component
              └── class
                    └── function
```

This mirrors C4 levels (System → Container → Component → Code) but extends
into class- and function-level granularity. Unlike C4, the chain is not
required: a service may have no documented components yet still exist.

---

## `system`

A logical product or platform — a coherent set of services that solve a
business domain.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: system.identity-platform
  type: system
  name: Identity Platform
  labels: [tier-1, customer-facing]
  metadata:
    domain: identity
    tier: tier-1
    runbook_url: "https://runbooks.acme.com/identity"
    status: production
```

### Common relationships
- `(team) owns (system)`
- `(service) belongs_to (system)`
- `(system) depends_on (system)`

### Documentation patterns
A system typically carries:

- A `lens=product`, zoom 10–25 fragment: *what business problem it solves*.
- A `lens=technical`, zoom 20–40 fragment: *the architecture overview*.
- A `lens=operations`, zoom 25–45 fragment: *SLOs, on-call, escalation*.

---

## `service`

A deployable unit. The most common entity in most graphs.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.auth
  type: service
  name: Auth Service
  parent: system.identity-platform
  labels: [authentication, tier-1, identity]
  metadata:
    technology: "Node.js / Express"
    repository: "https://gitlab.com/acme/auth-service"
    deployment: "k8s/us-east-1/auth-namespace"
    tier: tier-1
    sla_uptime: "99.95%"
    primary_language: typescript
```

Recommended `metadata` keys:

| Key                | Type      | Notes                                                         |
| ------------------ | --------- | ------------------------------------------------------------- |
| `technology`       | string    | High-level stack ("Node.js / Express", "Go").                 |
| `primary_language` | string    | Single language for `lens=debug` filtering.                   |
| `repository`       | URL       | Source code location.                                         |
| `deployment`       | string    | `k8s/region/namespace` or `lambda/region/name`.               |
| `tier`             | enum      | `tier-1`, `tier-2`, `tier-3`.                                 |
| `sla_uptime`       | string    | Quoted percentage.                                            |
| `runbook_url`      | URL       | Link to ops runbook.                                          |

### Common relationships
- `(team) owns (service)`
- `(service) belongs_to (system)`
- `(service) calls_api (service)` (with `protocol: rest|grpc`)
- `(service) provides_api (service|api_endpoint)`
- `(service) publishes_to (kafka_topic)`
- `(service) consumes_from (kafka_topic)`
- `(service) reads_from (database)`
- `(service) writes_to (database)`
- `(service) depends_on (cache|queue|...)`

### Documentation patterns
A service typically has multiple fragments:

| Lens          | Zoom range | Content                                              |
| ------------- | ---------- | ---------------------------------------------------- |
| `product`     | 25–45      | What it does, business-side.                         |
| `technical`   | 35–70      | Architecture, interfaces, dependencies.              |
| `operations`  | 35–65      | SLOs, alerts, on-call, runbook links.                |
| `debug`       | 55–95      | Failure modes, error codes, log queries.             |
| `client`      | 35–60      | External API guide (if applicable).                  |
| `onboarding`  | 30–70      | Local setup, first contribution guide.               |

---

## `component`

A logical sub-unit of a service: a module, a package, a feature area.
Components are how a service decomposes for `lens=technical` zoom 55–80.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: component.token-issuer
  type: component
  name: TokenIssuer
  parent: service.auth
  labels: [crypto]
  metadata:
    package: "src/auth/token"
    test_coverage: 0.91
    primary_language: typescript
```

### Common relationships
- `(component) belongs_to (service)`
- `(component) calls_api (component|service)`
- `(class) belongs_to (component)`

### Documentation patterns
- `lens=technical`, zoom 55–80: what the component does, its public API.
- `lens=debug`, zoom 70–95: known issues, edge cases.

---

## `class`

A class, interface, struct, trait, or other named type construct.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: class.JwtSigner
  type: class
  name: JwtSigner
  parent: component.token-issuer
  labels: [crypto]
  metadata:
    file: "src/auth/jwt.ts"
    line_start: 42
    line_end: 178
    visibility: public
    language: typescript
```

### Common relationships
- `(class) belongs_to (component)`
- `(class) extends (class)`
- `(class) implements (class)` — where target is an interface/trait.
- `(function) belongs_to (class)`

### Documentation patterns
Classes are leaf-ish; their fragments are usually code-explanatory.

- `lens=technical`, zoom 75–95: contract, invariants, threading.
- `lens=debug`, zoom 80–100: pitfalls, expected exceptions.

---

## `function`

A function or method — the deepest documentable unit.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: function.JwtSigner.signToken
  type: function
  name: signToken
  parent: class.JwtSigner
  metadata:
    signature: "signToken(claims: JwtClaims, ttlSeconds: number): string"
    file: "src/auth/jwt.ts"
    line_start: 95
    line_end: 137
```

### Common relationships
- `(function) belongs_to (class|component|service)`
- `(function) calls_api (api_endpoint)` — for cross-service calls extracted from code.

### Documentation patterns
A function rarely needs more than a small `lens=technical` or `lens=debug`
fragment, zoom 85–100. Most function-level documentation should live in code
comments and be ingested as needed.

> **Note:** v1 ingestion uses README/config sources, not AST parsing. Class
> and function entities are typically created manually for hot paths or
> imported from a code-graph tool. See [PRD §5 NG3](../../PRD.md).

---

## Worked example: an auth service tree

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: system.identity-platform
  type: system
  name: Identity Platform

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.auth
  type: service
  name: Auth Service
  parent: system.identity-platform
  metadata:
    repository: "https://gitlab.com/acme/auth-service"
    technology: "Node.js / Express"

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: component.token-issuer
  type: component
  name: TokenIssuer
  parent: service.auth

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: class.JwtSigner
  type: class
  name: JwtSigner
  parent: component.token-issuer
  metadata:
    file: "src/auth/jwt.ts"
```

A reader at zoom 30 sees the system. Zoom to 50 reveals the service. Zoom to
70 reveals the component. Zoom to 85 reveals the class. All from the same
graph.

---

## See also

- [`entities/organizational.md`](./organizational.md) — who owns these.
- [`entities/infrastructure.md`](./infrastructure.md) — what these services talk to.
- [`relationships/technical.md`](../relationships/technical.md) — `depends_on`, `calls_api`, `provides_api`, `extends`, `implements`.
- [`relationships/data-flow.md`](../relationships/data-flow.md) — Kafka, DB, queue interactions.
