# YAML definition format

> The `apiVersion` / `kind` / `spec` envelope and bulk-apply convention.

**Source of truth:** [PRD §11.5, §12](../../PRD.md)

---

## Why YAML

NexusDocs supports a YAML format as its primary author interface, modeled
after Kubernetes and Backstage:

- Version-controlled definitions live next to the code they describe.
- A CI job can run `nexdoc apply ./nexusdocs.yaml` on every push.
- Multi-document files can define an entire subgraph atomically.
- The same schemas underlie the REST API; YAML is a thin envelope over
  JSON.

---

## The envelope

Every YAML document follows this exact shape:

```yaml
apiVersion: nexusdocs/v1
kind: Entity | Relationship | DocFragment | ViewPreset
spec:
  # ...the schema-specific body
```

| Field         | Type   | Required | Notes                                                |
| ------------- | ------ | -------- | ---------------------------------------------------- |
| `apiVersion`  | string | yes      | Currently `nexusdocs/v1`.                            |
| `kind`        | string | yes      | One of `Entity`, `Relationship`, `DocFragment`, `ViewPreset`. |
| `spec`        | object | yes      | The schema body. See `schemas/`.                     |
| `metadata`    | object | no       | Reserved. Currently unused at the envelope level.    |

`spec` follows the schema for the chosen `kind`:

- [`Entity`](./entity.md)
- [`Relationship`](./relationship.md)
- [`DocFragment`](./doc-fragment.md)
- [`ViewPreset`](./view-preset.md)

---

## Multi-document files

A single file may contain multiple YAML documents, separated by `---`:

```yaml
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.auth
  type: service
  name: Auth Service

---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: topic.user-events
  type: kafka_topic
  name: user.events.v1

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
```

The platform applies them as a single transaction: all succeed or all fail.

---

## Apply ordering

`nexdoc apply` (and the equivalent `POST /api/v1/definitions/apply` endpoint)
sorts documents to satisfy dependency ordering before applying:

1. Entities are upserted first, in `parent`-first topological order.
2. Relationships are upserted second.
3. Fragments are upserted third (after their `subjects` and `relations`
   exist).
4. ViewPresets are upserted last.

The author can list documents in any order. The server reorders.

---

## Upsert semantics

Apply is idempotent: applying the same YAML twice produces the same graph.

- An object with a known `id` is **updated** (merge semantics: provided
  fields overwrite, omitted fields preserved).
- An object with a new `id` is **created**.
- Apply does not delete. Removing a YAML file does not remove its objects.
  Use `nexdoc delete` or the DELETE API for removal.

> **Conflict resolution:** when YAML conflicts with LLM-extracted data,
> the YAML wins. The platform stores the LLM-extracted version as a
> separate provenance record but does not surface it. See
> [PRD §9.1](../../PRD.md) and
> [`framework/llm-integration.md`](../framework/llm-integration.md).

---

## File layout conventions

For a Git-backed workflow, conventional layouts:

### Per-service file

```
auth-service/
├── README.md
├── nexusdocs/
│   ├── service.yaml          # entity + parent + own relationships
│   ├── fragments.yaml        # manually-authored doc fragments
│   └── api.yaml              # api_endpoint entities + provides_api edges
└── src/...
```

### Per-team monorepo

```
infra/nexusdocs/
├── company.yaml
├── divisions.yaml
├── teams.yaml
├── people.yaml
├── infra/
│   ├── kafka.yaml
│   └── databases.yaml
└── presets/
    └── *.yaml
```

The platform doesn't care about file boundaries — it cares about the
union of all applied documents.

---

## Validation rules at apply time

| Rule                                                                            |
| ------------------------------------------------------------------------------- |
| Every doc has `apiVersion: nexusdocs/v1`.                                       |
| Every doc has a known `kind`.                                                   |
| `spec` validates against the schema for that `kind`.                            |
| All referenced IDs (`parent`, `source`, `target`, `subjects[].entity`, …) exist either in the apply batch or already in the graph. |
| All referenced IDs respect kind constraints (e.g. a `belongs_to` parent must be an org-unit kind). |
| No circular `parent` chains.                                                    |

If any document fails validation, the apply is **rejected as a whole**. No
partial writes.

---

## Worked example: a small subgraph in one file

```yaml
# Org structure
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

---
# A service the team owns
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.payments-api
  type: service
  name: Payments API
  metadata:
    technology: "Go / Echo"
    repository: "https://gitlab.com/acme/payments-api"

---
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.payments-owns-payments-api
  source: team.payments
  target: service.payments-api
  type: owns

---
# Infrastructure the service uses
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
  id: topic.order-events
  type: kafka_topic
  name: order.events.v1
  parent: kafka_cluster.core-kafka-prod
  metadata:
    partitions: 12
    retention_days: 7

---
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.payments-publishes-order-events
  source: service.payments-api
  target: topic.order-events
  type: publishes_to
  protocol: kafka
  mode: async

---
# A doc fragment about the topic
apiVersion: nexusdocs/v1
kind: DocFragment
spec:
  id: docfrag.order-events-overview
  title: "order.events.v1 — what's on this topic"
  body: |
    Every successful order checkout publishes one event to `order.events.v1`.
    The key is the `order_id`; values are Avro-encoded with schema id `12`.
  subjects:
    - entity: topic.order-events
  tags: [orders, kafka]
  coverage:
    zoom_min: 45
    zoom_max: 75
    lenses: [technical, client]
    granularity: service
    lift_on:
      cluster_coverage_threshold: 0.4
      path_match: true
    lift_by: 15
  provenance:
    source_type: manual
    generated_by: human
    confidence: 1.0
    reviewed: true
```

Apply this with:

```
nexdoc apply ./payments-graph.yaml
```

After apply, querying `team.payments` at zoom 25 with `lens=technical`
will show the team, the service it owns, the Kafka topic it publishes to,
and the topic-overview fragment (lifted via `path_match` from
`zoom_min: 45` down to `30`).

---

## See also

- [`schemas/`](./README.md) — the per-kind schema pages.
- [`framework/api.md`](../framework/api.md) — `POST /api/v1/definitions/apply`.
- [`examples/sample-graph.md`](../examples/sample-graph.md) — a fully worked example.
