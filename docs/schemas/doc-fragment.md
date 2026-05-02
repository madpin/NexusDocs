# DocFragment schema

> The full format for an anchorable, zoom-tagged chunk of documentation.

**Source of truth:** [PRD §7.3](../../PRD.md)

---

## Schema

```yaml
DocFragment:
  id: string                    # Required. Stable identifier.
  doc_id: string | null         # Optional. Parent document ID, if part of a larger doc.
  title: string                 # Required. Human-readable title.
  body: string                  # Required. Content (markdown by default).
  format: enum                  # Optional. markdown | plaintext | structured_yaml | mermaid.

  # --- Anchoring (where this fragment attaches) ---
  subjects:                     # Direct entity anchors.
    - entity: string            # Entity ID this fragment describes.
  relations:                    # Direct relationship anchors.
    - rel: string               # Relationship ID this fragment describes.
  tags: string[]                # Cross-cutting concern tags. Polyattach to entities
                                # whose `labels` intersect.

  # --- Coverage (when this fragment is relevant) ---
  coverage:
    zoom_min: int               # 0–100. Default minimum zoom.
    zoom_max: int               # 0–100. Maximum zoom where still relevant.
    lenses: string[]            # Which lenses include this fragment.
    granularity: enum           # company | division | team | system | service |
                                # component | code
    lift_on:                    # Conditions to lower zoom_min.
      centrality_threshold: float | null
      cluster_coverage_threshold: float | null
      path_match: bool
    lift_by: int                # How many zoom levels to lower zoom_min when lifted.

  # --- Provenance (where this fragment came from) ---
  provenance:
    source_type: enum
    source_path: string | null
    source_hash: string | null
    generated_by: enum          # human | llm | hybrid
    confidence: float           # 0.0–1.0
    reviewed: bool
    last_synced: datetime
    created_at: datetime
    updated_at: datetime
```

---

## YAML envelope

```yaml
apiVersion: nexusdocs/v1
kind: DocFragment
spec:
  id: docfrag.auth-overview
  title: "Auth Service Overview"
  body: |
    The Auth Service handles user login, token issuance, and session management.
    It publishes lifecycle events to Kafka for downstream consumption.
  subjects:
    - entity: service.auth
    - entity: team.identity
  relations:
    - rel: rel.auth-publishes-user-events
  tags: [authentication, onboarding]
  coverage:
    zoom_min: 25
    zoom_max: 55
    lenses: [product, technical]
    granularity: service
    lift_on:
      centrality_threshold: 0.7
      path_match: true
    lift_by: 15
  provenance:
    source_type: manual
    generated_by: human
    confidence: 1.0
    reviewed: true
```

---

## Field reference

### `id` (string, required)

Stable identifier. Convention: `docfrag.<short-name>`.

### `doc_id` (string | null, optional)

If this fragment was extracted from a larger document, the ID of that
`document` entity. The platform uses this to:

- Re-extract the fragment when the source document changes.
- Group fragments by source for browsing.
- Apply `supersedes` semantics to all fragments of an old document.

`doc_id` is null for hand-authored standalone fragments.

### `title` (string, required)

Short title shown above the rendered fragment.

### `body` (string, required)

The actual content. Default format is markdown. The platform treats `body`
as opaque text — markdown rendering happens at view time.

Recommendations:

- **Be concise.** A fragment is not a chapter. 1–4 paragraphs typical.
- **Be self-contained.** A fragment may be rendered without the rest of
  its source document.
- **Don't repeat the entity's structured metadata.** A fragment about
  `service.auth` should not list its `repository` URL — that's already on
  the entity. Add what metadata cannot.

### `format` (enum, optional)

One of:

```
markdown | plaintext | structured_yaml | mermaid
```

Default: `markdown`. Use `structured_yaml` for fragments that are pure
data (e.g. an embedded API spec snippet). Use `mermaid` for diagrams.

### `subjects` (list, optional)

Direct entity anchors. Each item is `{ entity: <id> }`. A fragment may
have zero, one, or many subjects.

```yaml
subjects:
  - entity: service.auth
  - entity: team.identity
  - entity: kafka_cluster.core-kafka-prod
```

A fragment with no `subjects` and no `relations` and no `tags` will never
surface — it has nothing to anchor to.

### `relations` (list, optional)

Direct relationship anchors. Each item is `{ rel: <id> }`.

```yaml
relations:
  - rel: rel.auth-publishes-user-events
```

Fragments anchored to relationships are excellent for "the contract" or
"the failure mode" of a specific edge.

### `tags` (string[], optional)

Cross-cutting concern tags that **polyattach** the fragment. Any viewport
entity whose `labels` intersect the fragment's `tags` is treated as a
match.

```yaml
tags: [kafka, platform-standards, throughput]
```

A fragment with `tags: [kafka]` will surface for *every* viewport entity
labeled `kafka`, not just the ones explicitly listed in `subjects`.

This is the platform's "polyattachment" mechanism — see
[PRD §3 / Vision](../../PRD.md) and [`entities/documentation.md`](../entities/documentation.md).

### `coverage` (object, required)

Defines when this fragment is relevant. See the
[concepts/zoom-axis](../concepts/zoom-axis.md),
[concepts/lenses](../concepts/lenses.md), and
[concepts/topology](../concepts/topology.md) docs for the semantics.

#### `coverage.zoom_min` (int, required)

Minimum zoom (0–100) at which the fragment surfaces by default.

#### `coverage.zoom_max` (int, required)

Maximum zoom at which the fragment is still relevant. The fragment never
surfaces above this zoom, regardless of lifting.

#### `coverage.lenses` (string[], required)

Lenses in which this fragment surfaces. Union semantics — see
[`concepts/lenses.md`](../concepts/lenses.md).

A fragment must declare at least one lens.

#### `coverage.granularity` (enum, optional)

Author's intent about subject scale. Used for tie-breaking in fragment
ranking. One of:

```
company | division | team | system | service | component | code
```

#### `coverage.lift_on` (object, optional)

Conditions under which `zoom_min` is lowered. Any condition firing causes
the lift.

| Field                         | Type           | Meaning                                              |
| ----------------------------- | -------------- | ---------------------------------------------------- |
| `centrality_threshold`        | float | null   | Lift if subject's degree centrality > threshold.     |
| `cluster_coverage_threshold`  | float | null   | Lift if subject covers > threshold of viewport.      |
| `path_match`                  | bool           | Lift if subject is on the navigation path.           |

#### `coverage.lift_by` (int, optional)

How many zoom levels to lower `zoom_min` when lifted. Default 0 (no
lifting). Recommended range: 10–20.

### `provenance` (object, required)

Where the fragment came from. See [`entities/documentation.md`](../entities/documentation.md#provenance-the-whence)
for the freshness model.

| Field           | Type     | Required | Notes                                                       |
| --------------- | -------- | -------- | ----------------------------------------------------------- |
| `source_type`   | enum     | yes      | `readme`, `adr`, `runbook`, `ticket`, `api_spec`, `config_file`, `confluence`, `llm_generated`, `manual`. |
| `source_path`   | string   | no       | URL or file path of origin.                                 |
| `source_hash`   | string   | no       | Content hash for change detection.                          |
| `generated_by`  | enum     | yes      | `human`, `llm`, `hybrid`.                                   |
| `confidence`    | float    | yes      | 0.0–1.0. `1.0` for `human`.                                  |
| `reviewed`      | bool     | yes      | Has a human verified this fragment?                         |
| `last_synced`   | datetime | auto     | When ingestion last reconciled this fragment.               |
| `created_at`    | datetime | auto     |                                                             |
| `updated_at`    | datetime | auto     |                                                             |

---

## Validation

| Rule                                                                            |
| ------------------------------------------------------------------------------- |
| `id` matches `^[a-z][a-z0-9.-]*$`, max 200 chars.                                |
| `body` is non-empty.                                                            |
| At least one of `subjects`, `relations`, `tags` is non-empty.                   |
| `coverage.zoom_min ≤ coverage.zoom_max`.                                        |
| `coverage.zoom_min ≥ 0` and `coverage.zoom_max ≤ 100`.                          |
| `coverage.lenses` is non-empty.                                                 |
| `coverage.lift_by ≥ 0`.                                                         |
| All `subjects[].entity` and `relations[].rel` IDs refer to existing objects.    |
| `provenance.confidence` ∈ `[0.0, 1.0]`.                                          |
| If `provenance.generated_by = human`, then `provenance.confidence = 1.0`.       |

---

## Worked examples

### Polyattached Kafka fragment

```yaml
apiVersion: nexusdocs/v1
kind: DocFragment
spec:
  id: docfrag.kafka-throughput-ceiling
  title: "Kafka publisher throughput ceiling"
  body: |
    `core-kafka-prod` is sized for ~50k msgs/sec aggregate. Individual topics
    are capped at 8k msgs/sec by the cluster-wide quota. If you need more,
    request a partition rebalance from team-platform-data.
  subjects:
    - entity: kafka_cluster.core-kafka-prod
  tags: [kafka, platform-standards, throughput]
  coverage:
    zoom_min: 50
    zoom_max: 85
    lenses: [technical, operations, debug]
    granularity: system
    lift_on:
      cluster_coverage_threshold: 0.5
      path_match: true
    lift_by: 20
  provenance:
    source_type: runbook
    source_path: "https://wiki.acme.com/runbooks/kafka#throughput"
    generated_by: hybrid
    confidence: 0.95
    reviewed: true
```

### Service onboarding fragment

```yaml
apiVersion: nexusdocs/v1
kind: DocFragment
spec:
  id: docfrag.payments-api-local-setup
  doc_id: doc.payments-api-readme
  title: "Local setup for Payments API"
  body: |
    1. Clone the repo.
    2. `make bootstrap` installs Go and seeds a local Postgres.
    3. `make run-local` starts the API on `:8080` with mocked Kafka.
    Set `OAUTH_CLIENT_ID` from your dev tenant before authenticating.
  subjects:
    - entity: service.payments-api
  tags: [onboarding, golang]
  coverage:
    zoom_min: 40
    zoom_max: 80
    lenses: [onboarding, technical]
    granularity: service
    lift_on:
      path_match: true
    lift_by: 10
  provenance:
    source_type: readme
    source_path: "https://gitlab.com/acme/payments-api/-/blob/main/README.md#L42-L78"
    generated_by: llm
    confidence: 0.78
    reviewed: false
```

### Fragment about a relationship

```yaml
apiVersion: nexusdocs/v1
kind: DocFragment
spec:
  id: docfrag.payments-auth-rest-failure
  title: "Failure modes: Payments → Auth REST"
  body: |
    Auth Service rate-limits to 500 req/s per consumer. Circuit breaker trips
    after 3 consecutive 429s and opens for 30s. On a 401, the token is stale
    — refresh via `/oauth/refresh` before retrying.
  relations:
    - rel: rel.payments-api-calls-auth
  tags: [rate-limiting, debug]
  coverage:
    zoom_min: 50
    zoom_max: 85
    lenses: [debug, operations]
    granularity: service
    lift_on:
      path_match: true
    lift_by: 15
  provenance:
    source_type: manual
    generated_by: human
    confidence: 1.0
    reviewed: true
```

---

## See also

- [`entities/documentation.md`](../entities/documentation.md) — narrative companion.
- [`concepts/zoom-axis.md`](../concepts/zoom-axis.md) — `zoom_min` / `zoom_max` semantics.
- [`concepts/lenses.md`](../concepts/lenses.md) — `lenses` semantics.
- [`concepts/topology.md`](../concepts/topology.md) — `lift_on` and `lift_by`.
- [`framework/llm-integration.md`](../framework/llm-integration.md) — how LLM-generated fragments are produced.
