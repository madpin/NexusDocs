# Organizational Entities

> Who exists in the organization and how they nest.

**Source of truth:** [PRD §6.1, §7.1](../../PRD.md)

---

## Kinds covered

| Kind         | Purpose                                                        | Typical zoom |
| ------------ | -------------------------------------------------------------- | ------------ |
| `company`    | The top-level organization.                                    | 0–10         |
| `division`   | A major business division (e.g. Fintech, Platform).            | 5–20         |
| `tribe`      | A grouping of related teams (a Spotify-model "tribe").         | 10–25        |
| `team`       | A team that owns systems and ships work.                       | 15–35        |
| `person`     | An individual.                                                 | 20–40        |

These five kinds form a hierarchy, expressed via the `parent` field and
[`belongs_to` / `member_of`](../relationships/organizational.md) edges.

```
company
  └── division
        └── tribe
              └── team
                    └── person  (member_of, not parent)
```

`company`/`division`/`tribe`/`team` use the `parent` field for containment.
`person` does **not** use `parent`; instead, `person` connects to teams via
`member_of` edges, allowing a person to belong to multiple teams.

---

## `company`

The single root node of the organizational hierarchy.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: company.acme
  type: company
  name: Acme Corp
  metadata:
    headquarters: "Austin, TX"
    employee_count: 12000
    domain: acme.com
```

### Recommended labels
`["root", "internal"]`

### Common relationships
- `(division) belongs_to (company)`

---

## `division`

A major business unit.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: division.fintech
  type: division
  name: Fintech Division
  parent: company.acme
  labels: [fintech, regulated]
  metadata:
    leader: person.svp-fintech
    cost_center: "CC-100"
```

### Common relationships
- `(division) belongs_to (company)`
- `(tribe) belongs_to (division)`
- `(person) leads (division)` — for the leader.

---

## `tribe`

A Spotify-model tribe: a cluster of related teams sharing a domain.

> Optional. Organizations without tribes can skip this layer; teams may
> have a `division` as their `parent` directly.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: tribe.payments-experience
  type: tribe
  name: Payments Experience
  parent: division.fintech
  labels: [customer-facing]
  metadata:
    teams_count: 5
    chapter_lead: person.payments-cl
```

### Common relationships
- `(tribe) belongs_to (division)`
- `(team) belongs_to (tribe)`

---

## `team`

The unit of ownership. Teams own systems, services, components, and
documentation.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: team.payments
  type: team
  name: Team Payments
  parent: tribe.payments-experience   # or division.fintech if no tribe layer
  labels: [tier-1, on-call]
  metadata:
    slack_channel: "#team-payments"
    on_call_rotation: "pagerduty:team-payments"
    tech_lead: person.payments-tl
    headcount: 8
```

### Common relationships
- `(team) belongs_to (tribe|division)`
- `(person) member_of (team)`
- `(person) leads (team)` — for tech/eng leads.
- `(team) owns (system|service|component|database|...)`

### Documentation patterns
A team typically has:

- A `lens=onboarding`, zoom 15–40 fragment: *"Welcome to Team Payments"*.
- A `lens=product`, zoom 10–25 fragment: *"What this team does and why."*
- A `lens=operations`, zoom 25–45 fragment: *"On-call expectations and
  escalation paths."*

---

## `person`

An individual. People are first-class so that `owns`, `leads`, `reports_to`,
and `member_of` edges have stable endpoints.

### Schema

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: person.tpinto
  type: person
  name: Thiago M Pinto
  labels: [eng, principal]
  metadata:
    ldap: tpinto
    email: tpinto@acme.com
    role: "Principal Developer"
    timezone: "Europe/Dublin"
    location: "Dublin, IE"
```

`person` does **not** carry a `parent`. Membership is expressed via edges:

- `(person) member_of (team)` — possibly multiple.
- `(person) reports_to (person)` — manager chain.
- `(person) leads (team|tribe|division)` — leadership.
- `(person) owns (entity)` — for ICs who own a specific component.

### Documentation patterns
Person entities rarely carry their own fragments at low zooms. They typically
appear as endpoints of `owns` and `leads` edges, with their relationships
documented elsewhere.

A `lens=onboarding` fragment can be useful: *"Tpinto's areas of expertise
and ongoing projects."*

---

## Worked example: a small org

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: company.acme
  type: company
  name: Acme Corp

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: division.fintech
  type: division
  name: Fintech
  parent: company.acme

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: team.payments
  type: team
  name: Team Payments
  parent: division.fintech
  metadata:
    slack_channel: "#team-payments"

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: person.tpinto
  type: person
  name: Thiago M Pinto
  metadata:
    role: "Principal Developer"

---
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.tpinto-member-of-payments
  source: person.tpinto
  target: team.payments
  type: member_of
```

This small graph supports queries like:

- *"Who is on Team Payments?"* → reverse `member_of` from `team.payments`.
- *"What divisions exist?"* → entities of `kind: division`.
- *"What does Acme own?"* → traverse `belongs_to` and `owns` edges.

---

## See also

- [`relationships/organizational.md`](../relationships/organizational.md) — `belongs_to`, `owns`, `leads`, `member_of`, `reports_to`.
- [`entities/technical.md`](./technical.md) — what teams own.
- [`schemas/entity.md`](../schemas/entity.md) — full schema.
