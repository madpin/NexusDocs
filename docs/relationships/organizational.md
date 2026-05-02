# Organizational Relationships

> Who is part of what, who reports to whom, who owns what.

**Source of truth:** [PRD §6.1, §7.2](../../PRD.md)

---

## Types covered

| Type           | Direction                                | Purpose                                                        |
| -------------- | ---------------------------------------- | -------------------------------------------------------------- |
| `belongs_to`   | `(child) → (parent)`                     | Hierarchical containment of org units.                         |
| `owns`         | `(owner) → (asset)`                      | A team or person is responsible for an entity.                 |
| `leads`        | `(leader) → (org-unit)`                  | A person leads a team / tribe / division.                      |
| `member_of`    | `(person) → (team)`                      | A person belongs to a team. Many-to-many.                      |
| `reports_to`   | `(report) → (manager)`                   | The manager chain.                                             |

These edges have no `protocol` and no `mode`. Their `metadata` is typically
sparse.

---

## `belongs_to`

Hierarchical containment of organizational entities.

### Allowed pairs
| Source     | Target      |
| ---------- | ----------- |
| `division` | `company`   |
| `tribe`    | `division`  |
| `team`     | `tribe` or `division` |
| `service`  | `system`    |

`belongs_to` is conceptually the relationship form of `parent`. When `parent`
is set on an entity, the platform implicitly creates a `belongs_to` edge.

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.payments-belongs-to-fintech
  source: team.payments
  target: division.fintech
  type: belongs_to
```

This is usually unnecessary if `team.payments.parent = division.fintech`.
Use it only when you want to override or annotate the implicit edge.

---

## `owns`

A team or person owns an entity.

### Allowed pairs
| Source   | Target                                                                |
| -------- | --------------------------------------------------------------------- |
| `team`   | `system`, `service`, `component`, `database`, `kafka_cluster`, `kafka_topic`, `queue`, `cache`, `api_endpoint`, `document` |
| `person` | (same as above, when an IC owns a specific component)                 |

A single asset can have **multiple** `owns` edges if ownership is shared.

### Metadata
| Key            | Notes                                                          |
| -------------- | -------------------------------------------------------------- |
| `share`        | Optional float for fractional ownership (`0.5` = co-owner).    |
| `since`        | When the ownership started.                                    |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.payments-owns-payments-api
  source: team.payments
  target: service.payments-api
  type: owns
  metadata:
    since: "2024-03-01"
```

### Why `owns` matters for views

`owns` is the bridge between organizational and technical sub-graphs. A
view focused on `team.payments` with radius 2 traverses `owns` edges to
reach the team's services, then traverses `calls_api` and `publishes_to`
edges from those to reach external dependencies.

---

## `leads`

A person leads an organizational unit.

### Allowed pairs
| Source   | Target                          |
| -------- | ------------------------------- |
| `person` | `team`, `tribe`, `division`     |

A person can `lead` multiple units. A unit usually has at most one leader,
but the platform does not enforce this.

### Metadata
| Key       | Notes                                                |
| --------- | ---------------------------------------------------- |
| `role`    | `tech_lead`, `engineering_manager`, `vp`, etc.       |
| `since`   | When they took the role.                             |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.tpinto-leads-payments
  source: person.tpinto
  target: team.payments
  type: leads
  metadata:
    role: tech_lead
    since: "2025-01-15"
```

---

## `member_of`

A person belongs to a team. Many-to-many: one person may be on multiple
teams; one team has many members.

### Allowed pairs
| Source   | Target  |
| -------- | ------- |
| `person` | `team`  |

### Metadata
| Key                | Notes                                                          |
| ------------------ | -------------------------------------------------------------- |
| `share`            | Float 0.0–1.0 if the person splits time across teams.          |
| `since`            | Start date.                                                    |
| `until`            | End date (when the person leaves).                             |

### Example

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

---

## `reports_to`

The manager chain. Reverse traversal yields direct reports.

### Allowed pairs
| Source   | Target   |
| -------- | -------- |
| `person` | `person` |

A person typically `reports_to` exactly one manager; the platform does not
enforce this (matrix orgs, dual reporting).

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.tpinto-reports-to-aboss
  source: person.tpinto
  target: person.aboss
  type: reports_to
```

---

## Documentation patterns

Organizational relationships are usually documented at the entities, not at
the edges. A fragment about `team.payments` typically covers ownership
("we own the billing platform") more naturally than a fragment about a
single `owns` edge.

Exceptions where edge fragments make sense:

- `(team) owns (database)` with shared ownership — document the boundary.
- `(person) leads (team)` during a transition — document the handoff.

---

## See also

- [`entities/organizational.md`](../entities/organizational.md) — the endpoints of these edges.
- [`relationships/technical.md`](./technical.md) — what the owned services do.
