# Schemas

> Format reference for everything you can write to NexusDocs.

**Source of truth:** [PRD §7](../../PRD.md), [PRD §12](../../PRD.md)

---

## What this section covers

This section is the canonical format reference. Each page defines one
schema in full, with field-level types, constraints, and examples.

| Schema                                             | What it defines                                              |
| -------------------------------------------------- | ------------------------------------------------------------ |
| [`entity.md`](./entity.md)                         | A node in the graph.                                         |
| [`relationship.md`](./relationship.md)             | A directed edge between two entities.                        |
| [`doc-fragment.md`](./doc-fragment.md)             | An anchorable, zoom-tagged chunk of documentation.           |
| [`view-preset.md`](./view-preset.md)               | A saved view configuration.                                  |
| [`yaml-format.md`](./yaml-format.md)               | The `apiVersion` / `kind` / `spec` envelope and conventions. |

---

## Where these schemas come from

The schemas mirror the PRD §7 (Data Model) and §12 (YAML Definition Format)
sections. They are presented as YAML because the platform's primary author
interface is YAML applied via `nexdoc apply` (see [PRD §11.5](../../PRD.md)).
The same schemas underlie the REST API's JSON bodies — the field names and
types are identical.

---

## Cross-cutting types

Several types appear across schemas. They are defined once here.

### `SourceRef`

Where an entity, relationship, or fragment was discovered or defined.

```yaml
SourceRef:
  source_type: enum             # readme | adr | runbook | ticket | api_spec |
                                # config_file | llm_generated | manual | confluence |
                                # backstage | openapi | proto
  source_path: string | null    # File path or URL
  source_hash: string | null    # Content hash for change detection
```

Used directly as `source` on entities/relationships, and embedded as part of
`provenance` on fragments.

### `datetime`

ISO 8601 with timezone, e.g. `2026-04-29T10:11:00Z`. Always UTC.

### `id`

A URL-safe lowercase string of the form `<kind>.<short-name>` for entities
or `rel.<source>-<verb>-<target>` for relationships. Required, immutable,
unique within its kind namespace.

| Constraint                                                                 |
| -------------------------------------------------------------------------- |
| Lowercase, hyphens and dots only. Pattern: `^[a-z][a-z0-9.-]*$`.           |
| Max 200 characters.                                                        |
| Once created, never changes. Renaming an entity changes `name`, not `id`. |

### Common fields on all top-level types

| Field          | Type       | Required | Notes                                         |
| -------------- | ---------- | -------- | --------------------------------------------- |
| `id`           | id         | yes      | Stable identifier.                            |
| `name`         | string     | yes      | Human-readable label.                         |
| `created_at`   | datetime   | auto     | Set on creation, server-controlled.           |
| `updated_at`   | datetime   | auto     | Touched on every update.                      |
| `source`       | SourceRef  | no       | Where this object was discovered or defined.  |

---

## YAML envelope

Every YAML document follows this shape:

```yaml
apiVersion: nexusdocs/v1
kind: Entity | Relationship | DocFragment | ViewPreset
spec:
  # ...the schema-specific body
```

A single file may contain multiple YAML documents separated by `---`.
`nexdoc apply` validates and applies them in dependency order. See
[`yaml-format.md`](./yaml-format.md) for the full convention.

---

## Validation rules (cross-schema)

These rules apply to every type:

1. **`id` immutability**: once an object exists, its `id` cannot be changed.
   Updating with a different `id` is an error.
2. **Endpoint existence**: a `Relationship` cannot be created if its
   `source` or `target` entity does not exist. Use a single batch apply.
3. **Anchor existence**: a `DocFragment` cannot be created if any
   `subjects[].entity` or `relations[].rel` does not exist.
4. **Hash determinism**: the platform recomputes `source_hash` on ingest;
   user-provided hashes are accepted but verified.
5. **Timestamps**: `created_at` and `updated_at` are server-controlled.
   User-provided values are ignored.

---

## See also

- [`framework/api.md`](../framework/api.md) — REST endpoints that consume these schemas.
- [`framework/ingestion.md`](../framework/ingestion.md) — how connectors produce these schemas.
- [`examples/sample-graph.md`](../examples/sample-graph.md) — a complete worked example.
