# Documentation Relationships

> How documentation fragments and documents connect to the rest of the graph.

**Source of truth:** [PRD §6.1, §7.2](../../PRD.md)

---

## Types covered

| Type           | Direction                                | Purpose                                                        |
| -------------- | ---------------------------------------- | -------------------------------------------------------------- |
| `describes`    | `(document\|fragment) → (entity)`        | A doc or fragment is *about* an entity.                        |
| `references`   | `(document\|fragment) → (any)`           | A doc or fragment links to another resource.                   |
| `supersedes`   | `(new) → (old)`                          | One document replaces another.                                 |

These edges have no `protocol` and `mode` is rarely set. Their `metadata`
captures things like the source location of the link (anchor, line range)
or the supersession reason.

> **Important:** for `doc_fragment` nodes, anchoring to entities and edges
> is normally expressed via the fragment's `subjects` and `relations`
> fields, not via separate `describes` edges. Use `describes` mainly for
> top-level `document` entities.

---

## `describes`

The fragment or document is *about* the target entity. Use sparingly — the
preferred way to anchor a fragment is via its `subjects` field.

### Allowed pairs
| Source           | Target          |
| ---------------- | --------------- |
| `document`       | any entity      |
| `doc_fragment`   | any entity      |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-readme-describes-auth
  source: doc.auth-readme
  target: service.auth
  type: describes
```

This edge says: *the Auth README is about the Auth Service.* It does not
say *every fragment of the README is about the service.* Each fragment
declares its own subjects.

### When to use `describes` vs `subjects`

| Situation                                                  | Preferred approach              |
| ---------------------------------------------------------- | ------------------------------- |
| A fragment describes one or two entities.                  | `subjects` on the fragment.     |
| A `document` exists as a node and has many fragments.      | `describes` on the document.    |
| The relationship is **about** the document (e.g. for navigation). | `describes` edge.        |

---

## `references`

A document or fragment links to another resource. The target can be any
entity — including another document or fragment.

### Allowed pairs
| Source           | Target               |
| ---------------- | -------------------- |
| `document`       | any entity           |
| `doc_fragment`   | any entity           |

### Metadata
| Key             | Notes                                                       |
| --------------- | ----------------------------------------------------------- |
| `anchor`        | Section anchor or line range in the source.                 |
| `link_text`     | Visible text of the link.                                   |
| `kind`          | `inline`, `see-also`, `further-reading`.                    |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-readme-references-jwt-doc
  source: doc.auth-readme
  target: doc.jwt-design
  type: references
  metadata:
    anchor: "#token-format"
    kind: see-also
```

`references` is a softer link than `describes`. *"This document mentions
that one"* is `references`. *"This document is about that thing"* is
`describes`.

---

## `supersedes`

One document replaces another. The replaced document is kept (for history)
but the view engine should prefer the new one.

### Allowed pairs
| Source     | Target     |
| ---------- | ---------- |
| `document` | `document` |

### Metadata
| Key             | Notes                                                       |
| --------------- | ----------------------------------------------------------- |
| `reason`        | Why the supersession happened.                              |
| `effective_from` | Date the supersession takes effect.                       |

### Example

```yaml
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-readme-v2-supersedes-v1
  source: doc.auth-readme-v2
  target: doc.auth-readme-v1
  type: supersedes
  metadata:
    reason: "Migration from JWT to PASETO completed; v1 covered the JWT-only flow."
    effective_from: "2025-12-01"
```

The view engine **demotes** fragments belonging to a superseded document
unless they are explicitly re-anchored to the new document. A demoted
fragment is not deleted; it remains queryable for historical context but
does not surface in default views.

---

## Documentation patterns

Documentation edges rarely carry their own fragments — they exist to make
the graph self-describing, not to host more text. The fragment `body`
already lives on the fragment itself.

That said, two useful patterns:

1. **Annotate `supersedes` edges** with a fragment in `lens=onboarding`
   that explains the migration.
2. **Annotate `references` to external systems** (e.g. Confluence) with a
   fragment that summarizes the external content for in-graph readers.

---

## See also

- [`entities/documentation.md`](../entities/documentation.md) — `document` and `doc_fragment` entities.
- [`schemas/doc-fragment.md`](../schemas/doc-fragment.md) — `subjects` and `relations` fields.
- [`framework/ingestion.md`](../framework/ingestion.md) — how `references` edges are extracted from links.
