# LLM integration

> The two pipelines: extraction (write) and assembly (read).

**Source of truth:** [PRD §9](../../PRD.md)

---

## Why two pipelines

The LLM appears in NexusDocs in exactly two places:

1. **Extraction**: at ingest time, the LLM reads source content
   (READMEs, configs, ADRs) and produces entity / relationship /
   fragment candidates.
2. **Assembly**: at view time, the LLM takes a viewport plus a ranked
   set of fragments and produces a cohesive narrative summary.

Both pipelines are schema-guided and confidence-tracked. The platform
trusts neither without provenance.

---

## Pipeline 1 — Extraction

### Goal

Turn raw source content into validated graph contributions:

- Entities (with `kind`, `name`, recommended `metadata`).
- Relationships (with `type`, `protocol`, `mode`, `metadata`).
- DocFragments (with `subjects`, `tags`, `coverage`, `provenance`).

Each output is tagged with a `confidence ∈ [0.0, 1.0]`.

### Prompt structure

The extractor uses **three sequential prompts** per document:

```
─── PROMPT A: ENTITY DETECTION ──────────────────────────────────────────────

You are reading {source_type}: {source_path}.

Source content:
"""
{content}
"""

Existing entities in scope (for grounding; do not duplicate):
{existing_entities_summary}

Identify every service, database, Kafka topic, queue, cache, API endpoint,
team, person, or other entity mentioned. For each, return:

  - id (suggested, lowercase, dotted)
  - kind (one of: company, division, tribe, team, person, system, service,
    component, class, function, database, kafka_cluster, kafka_topic,
    api_endpoint, queue, cache)
  - name (human-readable)
  - parent (if implied by the content)
  - metadata (kind-specific fields)
  - confidence (0.0–1.0): your certainty this entity actually exists
    and is correctly typed.

Return a JSON array. Do not invent entities not mentioned.
─────────────────────────────────────────────────────────────────────────────
```

```
─── PROMPT B: RELATIONSHIP DETECTION ────────────────────────────────────────

Given the entities below and the source content, identify relationships
between them. For each, return:

  - id (suggested)
  - source, target (entity ids)
  - type (one of the allowed relationship types)
  - protocol (rest, kafka, postgres, …; null for organizational/doc edges)
  - mode (sync | async | batch | null)
  - metadata (e.g. method, path, topic, tables, …)
  - confidence (0.0–1.0)

Be especially careful with direction. (`A calls_api B` ≠ `B calls_api A`.)

Return a JSON array.
─────────────────────────────────────────────────────────────────────────────
```

```
─── PROMPT C: FRAGMENT DECOMPOSITION ────────────────────────────────────────

Decompose the source content into discrete fragments. A fragment is a
self-contained 1–4 paragraph chunk that describes a specific aspect of one
or more of the identified entities/relationships.

For each fragment:

  - title (5–10 words)
  - body (markdown, the actual content)
  - subjects (entity ids it directly describes)
  - relations (relationship ids it directly describes)
  - tags (cross-cutting concerns: kafka, security, onboarding, …)
  - coverage:
      zoom_min, zoom_max (0–100; what zoom band is this useful at?)
      lenses (which audiences benefit: product, technical, operations,
              debug, client, onboarding)
      lift_on (if the subject is structurally significant, should this
               fragment surface earlier? centrality_threshold,
               cluster_coverage_threshold, path_match)
      lift_by (how many zoom levels to lift)
  - confidence (0.0–1.0)

Return a JSON array.
─────────────────────────────────────────────────────────────────────────────
```

### Confidence scoring

The LLM is asked to self-rate. The platform also computes a derived
confidence based on:

- **Source-type prior**: an OpenAPI spec yields high-confidence relationship
  extractions; a free-text wiki page yields lower.
- **Grounding match**: extracted entities that match existing graph
  entities by name/kind get a confidence boost.
- **Pattern strength**: explicit configuration (e.g. a Kafka producer
  config block) is more reliable than prose.

Final stored `confidence = min(LLM_self_rating, derived)`.

### Acceptance threshold

Configurable per organization. Defaults:

| Confidence band     | Action                                                       |
| ------------------- | ------------------------------------------------------------ |
| `>= 0.8`            | Apply directly. `reviewed: false`.                           |
| `0.6 – 0.8`         | Apply. Surfaces with ⚠️ until reviewed.                       |
| `< 0.6`             | Hold in a queue. Surfaces only in a review UI.               |

### Conflict handling

See [`framework/ingestion.md`](./ingestion.md#conflict-resolution). The
LLM-extracted version **never overwrites human-authored content silently**.

---

## Pipeline 2 — Assembly

### Goal

At view time, given:

- The viewport (entities + relationships).
- A ranked set of relevant fragments.
- The current `zoom`, `lenses`, and `navigation_path`.
- Topology highlights (most-central entity, structural concerns).

Produce a cohesive narrative that answers *"what should the reader
understand right now?"*

### Prompt template

From [PRD §9.2](../../PRD.md):

```
─── ASSEMBLY PROMPT ─────────────────────────────────────────────────────────

You are rendering a view of a technical knowledge graph.

  Current focus:    {focus_entity.name} ({focus_entity.id})
  Zoom level:       {zoom} (scale: 0=company, 100=code)
  Active lenses:    {lenses}
  Navigation path:  {navigation_path or "(empty session)"}

  Entities in viewport:
  {entity_list}             # ID, kind, name, key metadata

  Relationships in viewport:
  {relationship_list}       # source → target, type, protocol, key metadata

  Topology highlights:
  - Most central:        {most_central_entity}
  - Structural concerns: {structural_concerns}

  Relevant documentation fragments (in rank order):
  {fragments}               # id, title, body, lenses, source

Generate a cohesive summary appropriate for zoom level {zoom}.

At this zoom, the reader expects: {zoom_expectations}
  (e.g. for zoom 25, "team-level overview, business outcomes, ownership;
   no code-level detail")

Highlight the structurally significant entities listed above.
Cite every claim with [fragment_id] back to its source.

If a Mermaid.js or C4 diagram would help, include it.

Return:
  summary: <markdown narrative>
  diagram: <Mermaid markup or empty>
  follow_up_suggestions: [<short suggestions for next navigation>]
─────────────────────────────────────────────────────────────────────────────
```

### Why the LLM, not a template

A traditional system would render fragments verbatim, in rank order, with
horizontal rules between them. The output reads like a wiki: a list of
disconnected paragraphs.

The LLM's job is to **stitch fragments into a coherent explanation** that
matches the chosen zoom and lens. At zoom 15 it abstracts away
implementation; at zoom 75 it dives into specifics. Same fragments, same
graph, completely different voice.

### Citations

Every claim in the rendered summary carries a `[fragment_id]` citation.
The UI renders these as click-throughs to the fragment source. This:

- Lets readers verify claims.
- Surfaces stale or low-confidence fragments visually.
- Makes the LLM accountable: it cannot summarize content that wasn't
  passed in.

### Failure modes

| Failure                      | Behavior                                                           |
| ---------------------------- | ------------------------------------------------------------------ |
| LLM unavailable              | Render fragments verbatim with a deterministic ranking header.    |
| LLM exceeds token budget     | Pass top-k fragments only; the rest are listed as "more sources." |
| LLM hallucinates a citation  | Citation post-validator drops citations that don't match input.   |
| Output contains forbidden content | Standard guardrails on the model side.                       |

---

## Token budget management

A typical zoom-30 view passes ~5–10 fragments to the LLM. A zoom-70 view
may pass 15–20. The engine sorts by rank and truncates to fit the model's
context window.

When the budget is tight:

1. Keep the highest-ranked fragments verbatim.
2. Summarize lower-ranked ones to a single sentence.
3. Surface the dropped fragments as "additional sources" in the response.

---

## Embedding-based retrieval (Phase 5)

[PRD §17 Phase 5](../../PRD.md) calls for semantic search across all
fragments. This will be backed by an embedding store (pgvector or
Pinecone — see [PRD §14.2](../../PRD.md)). Once available, fragment
collection in step 3 of the view engine will optionally include a
semantic-similarity pass alongside the structural anchoring.

---

## Hallucination defenses

| Defense                                          | What it prevents                                              |
| ------------------------------------------------ | ------------------------------------------------------------- |
| Schema-guided extraction (JSON output, validated) | LLM inventing fields not in the schema.                      |
| Existing-entities grounding in Prompt A          | Duplicate or misnamed entities.                               |
| Confidence threshold gates auto-apply            | Low-confidence outputs reaching the graph unreviewed.         |
| Source-hash verification                         | Stale fragments masquerading as fresh.                        |
| Citation post-validation                         | Made-up `[fragment_id]` citations.                            |
| Never-overwrite-human rule                       | LLM revising human-authored content silently.                 |

See [PRD §16 / risks](../../PRD.md) — *LLM hallucination in extraction*
is rated `High` severity and these are its mitigations.

---

## See also

- [`framework/ingestion.md`](./ingestion.md) — where Pipeline 1 fits.
- [`framework/view-engine.md`](./view-engine.md) — where Pipeline 2 fits.
- [`schemas/doc-fragment.md`](../schemas/doc-fragment.md#provenance-object-required) — `confidence`, `generated_by`, `reviewed`.
