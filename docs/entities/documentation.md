# Documentation Entities

> The graph stores its own documentation as nodes.

**Source of truth:** [PRD §6.1, §6.4, §7.3](../../PRD.md)

---

## Kinds covered

| Kind            | Purpose                                                               | Typical zoom     |
| --------------- | --------------------------------------------------------------------- | ---------------- |
| `document`      | A whole document: a README, an ADR, a Confluence page, a runbook.     | matches content  |
| `doc_fragment`  | An anchorable, zoom-tagged chunk of documentation.                    | declared explicitly |

The headline idea: **documentation is not separate from the graph.**
A README does not live "next to" the auth service — it lives **in the graph**,
linked to the auth service via `describes` edges, decomposed into fragments
that are themselves nodes.

---

## `document`

A `document` represents a complete document as it exists in some source
system (a Git README, a Confluence page, a JIRA ticket comment thread, a
Markdown file, etc.).

A `document` is mostly a *grouping construct* — a way to remember that a set
of fragments came from the same source file, and to track that source file
for change detection.

### Schema

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
    primary_lens: technical
```

Recommended `metadata` keys:

| Key            | Type     | Notes                                             |
| -------------- | -------- | ------------------------------------------------- |
| `source_type`  | enum     | `readme`, `adr`, `runbook`, `ticket`, `api_spec`, `config_file`, `confluence`, `manual`. |
| `source_path`  | URL/path | Where the document lives.                         |
| `source_hash`  | string   | Content hash for change detection.                |
| `last_synced`  | datetime | When the ingestion last reconciled this doc.      |
| `primary_lens` | string   | Default lens to apply to fragments without one.   |

### Common relationships
- `(document) describes (entity)` — for the entire document's subject.
- `(doc_fragment) belongs_to (document)` — via `doc_id` on the fragment.

### When to model documents

You don't always need a `document` entity:

- For **manual** YAML-authored fragments, skip `document`. Each fragment
  stands alone.
- For **ingested** content, the connector typically creates a `document`
  entity per source file so re-ingestion can replace fragments cleanly when
  the source changes.

---

## `doc_fragment`

The unit of documentation. A `doc_fragment` is a **chunk of text anchored to
one or more graph nodes or edges, with metadata about where and when it is
relevant**.

A single README is ingested as multiple `doc_fragment` nodes:

- One for the high-level overview (zoom 25–45, `lens=product`).
- One for the setup guide (zoom 65–85, `lens=onboarding`).
- One for the API reference (zoom 50–70, `lens=technical`).

Same source, three different fragments, surfacing in three different views.

### Why fragments?

A traditional doc is monolithic: you read the whole page or you don't. In
NexusDocs, a doc is decomposable. The view engine assembles a *just-right*
slice of fragments for the current view; the reader never has to scroll past
"setup instructions" to find "the architecture overview."

This is also what makes **polyattachment** work: a single fragment can be
anchored to multiple subjects, surface in multiple lenses, and lift via
multiple topology conditions.

### Schema

The full schema is in [`schemas/doc-fragment.md`](../schemas/doc-fragment.md).
Minimal example:

```yaml
apiVersion: nexusdocs/v1
kind: DocFragment
spec:
  id: docfrag.auth-overview
  title: "Auth Service Overview"
  body: |
    The Auth Service handles user login, token issuance, and session
    management. It publishes lifecycle events (user created, user deactivated)
    to Kafka for downstream consumption by Billing, Notifications, and
    Analytics.
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

### Anchoring (the *what*)

A fragment may anchor to:

| Field        | Anchored to             | Meaning                                                        |
| ------------ | ----------------------- | -------------------------------------------------------------- |
| `subjects`   | one or more entity IDs  | "This fragment describes these nodes."                         |
| `relations`  | one or more edge IDs    | "This fragment describes these edges."                         |
| `tags`       | freeform strings        | "This fragment is relevant wherever entities have these labels." |

`tags` are how a fragment becomes **polyattached**. A fragment tagged
`[kafka]` will surface for any viewport entity whose `labels` include
`kafka`, even without explicit subject linkage. This is how a single
"Kafka best practices" fragment serves many topics.

### Coverage (the *when*)

```yaml
coverage:
  zoom_min: 25
  zoom_max: 55
  lenses: [product, technical]
  granularity: service           # company | division | team | system | service | component | code
  lift_on:
    centrality_threshold: 0.7    # null to disable
    cluster_coverage_threshold: 0.6
    path_match: true
  lift_by: 15
```

| Field                                    | Meaning                                                            |
| ---------------------------------------- | ------------------------------------------------------------------ |
| `zoom_min`, `zoom_max`                   | The zoom range where this fragment is relevant.                    |
| `lenses`                                 | Which lenses include this fragment (union, see [`lenses.md`](../concepts/lenses.md)). |
| `granularity`                            | Author's intent about subject scale; helps ranking ties.           |
| `lift_on.centrality_threshold`           | Lift `zoom_min` if subject centrality exceeds this.                |
| `lift_on.cluster_coverage_threshold`     | Lift `zoom_min` if subject covers this fraction of the viewport.   |
| `lift_on.path_match`                     | Lift `zoom_min` if subject is on the navigation path.              |
| `lift_by`                                | How many zoom levels to lower `zoom_min` when lifted.              |

See [`concepts/topology.md`](../concepts/topology.md) for lifting semantics.

### Provenance (the *whence*)

```yaml
provenance:
  source_type: readme            # readme | adr | runbook | ticket | api_spec | config_file | llm_generated | manual
  source_path: "https://gitlab.com/.../README.md#L42-L78"
  source_hash: "sha256:1f9b…"
  generated_by: llm              # human | llm | hybrid
  confidence: 0.84               # 0.0–1.0
  reviewed: false
  last_synced: "2026-04-29T10:11:00Z"
  created_at: "2026-04-01T08:00:00Z"
  updated_at: "2026-04-29T10:11:00Z"
```

Provenance answers: where did this come from, who wrote it, when was it
last verified, and how confident are we?

| Field             | Meaning                                                            |
| ----------------- | ------------------------------------------------------------------ |
| `source_type`     | The kind of source.                                                |
| `source_path`     | URL or file path.                                                  |
| `source_hash`     | Hash of the source for change detection.                           |
| `generated_by`    | `human`, `llm`, or `hybrid` (LLM-extracted then human-edited).     |
| `confidence`      | LLM confidence in extraction. Always `1.0` for `human`.            |
| `reviewed`        | Has a human verified this fragment?                                |
| `last_synced`     | When ingestion last touched this fragment.                         |
| `created_at` / `updated_at` | Standard timestamps.                                     |

The view engine uses provenance to rank and badge fragments:

| Signal                          | Effect                                                              |
| ------------------------------- | ------------------------------------------------------------------- |
| `confidence < 0.6`              | ⚠️ flag — human review requested.                                  |
| `confidence ≥ 0.8`              | Display normally.                                                   |
| `reviewed: true`                | ✓ verified badge.                                                   |
| `last_synced > 30 days`         | Stale flag.                                                         |
| `source_hash` mismatch on disk  | Ingestion is re-triggered.                                          |

See [`framework/llm-integration.md`](../framework/llm-integration.md) for the
full freshness model.

---

## Worked example: a fragment polyattached three ways

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

This fragment:

- Directly anchors to the cluster (`subjects`).
- Picks up any viewport entity that has `kafka` or `throughput` in its
  `labels` (via `tags`).
- Surfaces in `technical`, `operations`, OR `debug` lenses.
- Lifts from zoom 50 → 30 when the cluster covers ≥50% of the viewport.

It is one fragment serving three audiences across three zoom regions.

---

## See also

- [`schemas/doc-fragment.md`](../schemas/doc-fragment.md) — full schema.
- [`concepts/zoom-axis.md`](../concepts/zoom-axis.md) — zoom range semantics.
- [`concepts/lenses.md`](../concepts/lenses.md) — lens union semantics.
- [`concepts/topology.md`](../concepts/topology.md) — lifting algorithm.
- [`relationships/documentation.md`](../relationships/documentation.md) — `describes`, `references`, `supersedes`.
- [`framework/llm-integration.md`](../framework/llm-integration.md) — LLM-extracted fragments.
