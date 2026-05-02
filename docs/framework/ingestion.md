# Ingestion pipeline

> How existing READMEs, code, and configs become entities, edges, and fragments.

**Source of truth:** [PRD §9.1](../../PRD.md)

---

## Goal

> *"Existing READMEs, code, and configs populate the graph automatically;
> >60% of fragments created by LLM, not manually."* — [PRD §G4, §16](../../PRD.md)

The ingestion pipeline turns existing organization data into NexusDocs
entities, relationships, and fragments. It runs continuously and
incrementally: a webhook on a Git push triggers re-ingestion of changed
files; a scheduled job reconciles Confluence pages.

---

## Pipeline shape

```
SOURCE CONNECTORS              EXTRACTION ENGINE            GRAPH POPULATION
┌─────────────────┐           ┌──────────────────┐         ┌───────────────┐
│ Git Repos       │──README──▶│                  │──────▶  │ Create/Update │
│ (README, ADR,   │──code───▶ │  LLM Extractor   │         │ Entities      │
│  docker-compose,│──config─▶ │                  │         │               │
│  k8s manifests) │           │  Schema-guided   │──────▶  │ Create/Update │
├─────────────────┤           │  extraction with │         │ Relationships │
│ Confluence      │──pages──▶ │  confidence      │         │               │
├─────────────────┤           │  scoring         │──────▶  │ Create/Update │
│ JIRA            │──tickets─▶│                  │         │ DocFragments  │
├─────────────────┤           │                  │         │               │
│ API Specs       │──openapi─▶│                  │         │ With          │
│ (OpenAPI, Proto)│──proto──▶ │                  │         │ provenance &  │
├─────────────────┤           └──────────────────┘         │ confidence    │
│ Backstage       │──yaml───▶                              └───────────────┘
└─────────────────┘
```

---

## Source connectors

A **connector** pulls content from one source system and emits documents
in a normalized form for the LLM extractor.

| Connector              | Triggered by                  | Phase    |
| ---------------------- | ----------------------------- | -------- |
| Git (README, code, configs) | Git push webhook         | Phase 2  |
| Confluence             | Scheduled poll (e.g. hourly)  | Phase 2  |
| JIRA                   | Scheduled poll                | Phase 4  |
| OpenAPI / Proto        | Git push or release           | Phase 4  |
| Backstage catalog      | Scheduled YAML import         | Phase 4  |
| Manual YAML            | `nexdoc apply`                | Phase 1  |

See [PRD §17 / Phased Rollout](../../PRD.md). v1 ships with Git +
Confluence; the rest follow in later phases.

### Connector contract

A connector implements:

```yaml
ConnectorJob:
  source_type: enum             # readme | confluence | jira | api_spec | …
  source_path: string           # File path or URL
  content: string               # Raw text content
  source_hash: string           # Hash for change detection
  metadata: map                 # Connector-specific (branch, page version, …)
```

The framework guarantees:

- `source_hash` is stable for unchanged content.
- Re-running a connector with unchanged input produces no graph mutations.
- Errors in one document do not abort the batch.

---

## Change detection

Each ingestion run computes the content hash of every document it pulls
and compares to the `provenance.source_hash` stored on existing fragments
or the `metadata.source_hash` on `document` entities.

| Comparison                          | Action                                                      |
| ----------------------------------- | ----------------------------------------------------------- |
| New (no existing record)            | Run extraction, create entities + fragments.                |
| Hash matches                        | Skip. No graph mutation.                                    |
| Hash differs                        | Run extraction. Diff against existing. Update changed.      |

This makes the pipeline cheap to run frequently. A daily run on a
1000-repo org skips ~95% of files because they haven't changed.

---

## LLM extraction

For each document the connector emits, the extraction engine runs one or
more **schema-guided extraction prompts**. See
[`framework/llm-integration.md`](./llm-integration.md) for the full prompt
templates.

Conceptually:

```
INPUT:
  - Source content (README, config, etc.)
  - Source type
  - Existing entities/relationships in the same scope (for grounding)

EXTRACTION:
  Phase A: Identify entities mentioned.
    - "List all services, databases, Kafka topics, and APIs in this README.
       For each, return id, kind, name, and confidence."
  Phase B: Identify relationships.
    - "For each entity, list its dependencies, API calls, Kafka publishes,
       and database reads/writes. Include protocol and mode."
  Phase C: Decompose into fragments.
    - "Decompose this document into discrete fragments. For each, estimate
       zoom_min, zoom_max, and the lens set."

OUTPUT:
  - List of {entity, relationship, fragment} candidates with confidence scores.
```

Every output carries a confidence score. Anything below the
configurable acceptance threshold (default `0.6`) is created with the
`reviewed: false` flag and surfaces a review-needed badge in the UI.

---

## Conflict resolution

When LLM-extracted data conflicts with existing data, the platform follows
strict precedence:

```
human-authored (manual)  >  human-reviewed LLM  >  unreviewed LLM
```

| Existing                     | New extraction proposes              | Resolution                              |
| ---------------------------- | ------------------------------------ | --------------------------------------- |
| Human-authored               | Different value                      | **Reject the change.** Flag for review. |
| Human-reviewed LLM (✓)       | Different value                      | **Hold.** Mark as drift; do not auto-overwrite. |
| Unreviewed LLM               | Different value                      | Overwrite. Update `last_synced`.        |
| Empty                        | Anything                             | Create.                                 |

> **The platform never silently overwrites human work.** This is critical
> for adoption — see [PRD §16 / risks](../../PRD.md).

When a conflict is "held," both versions are stored. The UI shows the
human-authored one and offers a side-by-side comparison.

---

## Drift detection

When the *source* of a previously-extracted fragment changes (hash
mismatch) but the LLM extracts the same content, the platform updates
`last_synced` only.

When the source changes and extraction produces *different* content, the
fragment is marked as drifted. A `lens=operations` automated alert
("README mentions REST but the extracted relationships still say gRPC")
is the kind of signal Phase 5 will surface — see
[PRD §17 Phase 5](../../PRD.md).

---

## Freshness signals

Stored on every extracted fragment via `provenance`:

| Signal                            | Effect                                                           |
| --------------------------------- | ---------------------------------------------------------------- |
| `confidence < 0.6`                | ⚠️ flagged.                                                      |
| `confidence ≥ 0.8`                | Render normally.                                                 |
| `reviewed: true`                  | ✓ verified badge.                                                |
| `last_synced > 30 days`           | Stale flag.                                                      |
| `source_hash` mismatch detected   | Re-extraction triggered automatically.                           |

These map directly to the [`provenance` block on `DocFragment`](../schemas/doc-fragment.md#provenance-object-required).

---

## CLI: `nexdoc apply`

For human-authored content, ingestion is bypassed and YAML is applied
directly:

```
nexdoc apply ./payments-graph.yaml
```

Behaviorally identical to `POST /api/v1/definitions/apply`. See
[`framework/api.md`](./api.md) and
[`schemas/yaml-format.md`](../schemas/yaml-format.md).

YAML applies are *trusted* — they bypass the LLM and the confidence-based
review gate. The contract is: humans review their own YAML.

---

## Ingestion API

```
POST /api/v1/ingest/repository    # Trigger repo ingestion
  Body: { repo_url, branch }

POST /api/v1/ingest/document      # Ingest a single document
  Body: { url, source_type }

GET  /api/v1/ingest/status/{job_id}  # Check ingestion job status
```

See [`framework/api.md`](./api.md).

---

## Phasing summary

| Phase | What lands                                                 |
| ----- | ---------------------------------------------------------- |
| 1     | Manual YAML, `nexdoc apply`.                               |
| 2     | Git connector (READMEs, configs, manifests). Confluence connector. LLM extraction with confidence scoring. Change detection. |
| 4     | JIRA connector. OpenAPI/Proto connector. Backstage import. |
| 5     | Drift detection. Suggested fragments. Semantic search.     |

See [PRD §17](../../PRD.md).

---

## See also

- [`framework/llm-integration.md`](./llm-integration.md) — extraction prompts.
- [`schemas/doc-fragment.md`](../schemas/doc-fragment.md#provenance-object-required) — provenance fields populated by ingestion.
- [`framework/api.md`](./api.md) — ingestion endpoints.
