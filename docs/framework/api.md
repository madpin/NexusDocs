# API surface (v1)

> REST endpoints for graph CRUD, view rendering, ingestion, search, and bulk apply.

**Source of truth:** [PRD §11](../../PRD.md)

---

## Conventions

- All endpoints are prefixed with `/api/v1`.
- Bodies are JSON. The shape of every body matches the schemas in
  [`schemas/`](../schemas/README.md). YAML in `nexdoc apply` is parsed
  and converted to the same JSON shape before hitting the API.
- Successful responses return `200 OK` with the resource representation
  (or `201 Created` on POST).
- Errors are `4xx` (validation, not found) or `5xx` (server). Bodies are
  `{ error: { code, message, details? } }`.
- Authentication: organization-deployable, typically an opaque bearer
  token. ACLs are out of scope for v1 — see [PRD §5 NG2](../../PRD.md).

---

## Graph CRUD

Endpoints for direct manipulation of entities, relationships, and
fragments. Mostly used by integrations and tooling. Humans usually go
through `nexdoc apply` (see below) instead.

### Entities

```
POST   /api/v1/entities                  # Create entity
GET    /api/v1/entities/{id}             # Read entity
PUT    /api/v1/entities/{id}             # Update entity (merge semantics)
DELETE /api/v1/entities/{id}             # Delete entity (and dependent edges)
```

**Body**: matches [`schemas/entity.md`](../schemas/entity.md) — fields under
`spec`, plus `id` at the top level for updates.

### Relationships

```
POST   /api/v1/relationships             # Create relationship
GET    /api/v1/relationships/{id}        # Read relationship
GET    /api/v1/entities/{id}/edges       # All relationships for an entity
DELETE /api/v1/relationships/{id}        # Delete relationship
```

`GET /entities/{id}/edges` returns both `outgoing` and `incoming` edges:

```json
{
  "outgoing": [Relationship, ...],
  "incoming": [Relationship, ...]
}
```

Optional query params: `?type=publishes_to,calls_api`, `?protocol=kafka`.

### Fragments

```
POST   /api/v1/fragments                 # Create fragment
GET    /api/v1/fragments/{id}            # Read fragment
PUT    /api/v1/fragments/{id}            # Update fragment
GET    /api/v1/entities/{id}/fragments   # All fragments anchored to entity
```

`GET /entities/{id}/fragments` returns fragments anchored via *any*
mechanism (subjects, relations connected to the entity, or tag matches
against the entity's labels).

---

## View rendering

The primary read surface. This is what UIs and integrations call to
display a view.

```
POST   /api/v1/views/render
```

**Body**:

```json
{
  "focus": "service.auth",
  "zoom": 35,
  "lenses": ["technical"],
  "radius": 3,
  "filters": {
    "entity_kinds": ["service", "kafka_topic", "database"],
    "relationship_types": ["calls_api", "publishes_to", "consumes_from"],
    "protocols": ["kafka", "rest"],
    "tags": ["tier-1"]
  },
  "navigation_path": ["team.payments", "service.payments-api"]
}
```

**Response**: a [RenderedView](./view-engine.md):

```json
{
  "summary": "...markdown narrative with [fragment_id] citations...",
  "diagram": "graph TD\n  service.auth --> topic.user-events\n  ...",
  "fragments": [
    {
      "id": "docfrag.auth-overview",
      "title": "Auth Service Overview",
      "body": "...",
      "rank": 1,
      "effective_zoom_min": 25,
      "lifted": false
    }
  ],
  "entities": [...],
  "relationships": [...],
  "topology_highlights": {
    "most_central": "service.auth",
    "structural_concerns": ["kafka_cluster.core-kafka-prod"]
  }
}
```

### View presets

```
POST   /api/v1/views/presets             # Save a view preset
GET    /api/v1/views/presets             # List presets visible to the caller
GET    /api/v1/views/presets/{id}        # Load a specific preset
PUT    /api/v1/views/presets/{id}        # Update preset (owner only)
DELETE /api/v1/views/presets/{id}        # Delete preset (owner only)
```

Bodies match [`schemas/view-preset.md`](../schemas/view-preset.md). To
*render* a preset, call `GET /api/v1/views/presets/{id}` to get the
preset, then `POST /api/v1/views/render` with its parameters.

---

## Ingestion

Trigger or query the [ingestion pipeline](./ingestion.md).

```
POST   /api/v1/ingest/repository
  Body: { "repo_url": "https://gitlab.com/acme/auth-service", "branch": "main" }

POST   /api/v1/ingest/document
  Body: { "url": "https://wiki.acme.com/payments-overview", "source_type": "confluence" }

GET    /api/v1/ingest/status/{job_id}
```

`POST /ingest/*` returns:

```json
{ "job_id": "ing.7f3a…", "status": "queued" }
```

`GET /ingest/status/{job_id}` returns:

```json
{
  "job_id": "ing.7f3a…",
  "status": "in_progress | succeeded | failed",
  "progress": 0.42,
  "documents_processed": 17,
  "entities_created": 4,
  "entities_updated": 9,
  "relationships_created": 22,
  "fragments_created": 31,
  "errors": [...]
}
```

---

## Search

Free-text and structured search across entities, relationships, and
fragments.

```
POST   /api/v1/search
```

**Body**:

```json
{
  "query": "kafka dependencies in payments",
  "scope": "entities | relationships | fragments | all",
  "filters": {
    "entity_kinds": ["service", "kafka_topic"],
    "protocols": ["kafka"]
  }
}
```

**Response**: a flat list of typed results:

```json
{
  "hits": [
    { "kind": "entity", "id": "topic.user-events", "score": 0.91, "snippet": "…" },
    { "kind": "fragment", "id": "docfrag.kafka-throughput", "score": 0.84, "snippet": "…" },
    { "kind": "relationship", "id": "rel.auth-publishes-user-events", "score": 0.62 }
  ]
}
```

Search supports:

- **Entity search**: `"payments"` → `team.payments`, `service.payments-api`,
  `database.payments-db`.
- **Relationship search**: `"who publishes to order-events"` → all
  `publishes_to` edges where `target.name` matches.
- **Protocol search**: `"kafka dependencies"` → all edges where
  `protocol = kafka`.
- **Fragment search**: `"how to set up local auth"` → fragments matching
  by text, returned in context of their anchored entities.

---

## Bulk YAML apply

The `nexdoc apply` command and its API equivalent.

```
POST   /api/v1/definitions/apply
```

**Body**: raw YAML (multi-document, separated by `---`). `Content-Type:
application/yaml`.

**Response**:

```json
{
  "applied": [
    { "kind": "Entity", "id": "service.auth", "action": "created" },
    { "kind": "Relationship", "id": "rel.auth-publishes-user-events", "action": "created" },
    { "kind": "DocFragment", "id": "docfrag.auth-overview", "action": "updated" }
  ],
  "skipped": [],
  "errors": []
}
```

Apply is **transactional**: if any document fails validation, *no*
documents are applied. See
[`schemas/yaml-format.md`](../schemas/yaml-format.md).

---

## Error model

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Relationship rel.foo-bar references missing entity service.bar",
    "details": [
      { "field": "spec.target", "reason": "entity_not_found" }
    ]
  }
}
```

Standard error codes:

| Code                       | When                                                          |
| -------------------------- | ------------------------------------------------------------- |
| `not_found`                | The requested resource doesn't exist.                         |
| `validation_failed`        | Body fails schema validation.                                 |
| `conflict`                 | A change conflicts with human-authored content (see ingestion). |
| `forbidden`                | Caller lacks permission (only relevant for owner-gated ops).  |
| `rate_limited`             | Too many requests.                                            |
| `view_engine_unavailable`  | LLM or graph DB temporarily down.                             |

---

## Future endpoints (post-v1)

| Phase | Endpoint                                       | Purpose                                   |
| ----- | ---------------------------------------------- | ----------------------------------------- |
| 5     | `POST /api/v1/analysis/impact`                 | Impact analysis: blast radius queries.    |
| 5     | `POST /api/v1/analysis/drift`                  | Drift detection between sources.          |
| 5     | `POST /api/v1/search/semantic`                 | Embedding-based semantic search.          |

See [PRD §17 Phase 5](../../PRD.md).

---

## See also

- [`schemas/`](../schemas/README.md) — request/response bodies.
- [`framework/view-engine.md`](./view-engine.md) — what `/views/render` does internally.
- [`framework/ingestion.md`](./ingestion.md) — what `/ingest/*` triggers.
