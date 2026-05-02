# View engine

> Subgraph extraction → topology analysis → fragment ranking → LLM render.

**Source of truth:** [PRD §8](../../PRD.md)

---

## What the engine does

The view engine takes a `ViewRequest` and produces a `RenderedView`. A
`ViewRequest` is the four navigation parameters plus any filters:

```yaml
ViewRequest:
  focus: entity_id              # e.g. service.auth
  zoom: int                     # 0–100
  lenses: string[]              # e.g. [technical, debug]
  radius: int                   # edge-hops
  filters: FilterSet            # protocols, kinds, types, tags
  navigation_path: entity_id[]  # session trail (most recent first)
```

A `RenderedView` is what gets shown:

```yaml
RenderedView:
  summary: string               # LLM-generated narrative
  diagram: string               # Mermaid.js or C4 markup
  fragments: RankedFragment[]   # source content used
  entities: Entity[]            # nodes in the viewport
  relationships: Relationship[] # edges in the viewport
  topology_highlights:
    most_central: entity_id
    structural_concerns: entity_id[]
```

---

## The six-step pipeline

From [PRD §8.1](../../PRD.md):

```
INPUT: ViewRequest

  STEP 1: SUBGRAPH EXTRACTION
  STEP 2: TOPOLOGY ANALYSIS
  STEP 3: FRAGMENT COLLECTION
  STEP 4: FRAGMENT FILTERING & LIFTING
  STEP 5: DEDUPLICATION & RANKING
  STEP 6: LLM ASSEMBLY

OUTPUT: RenderedView
```

The rest of this page walks through each step.

---

## Step 1 — Subgraph extraction

Starting from the focus entity, traverse outward `radius` edge-hops along
edges that match the request's filters. Collect every entity and every
edge in the result. This is the **viewport**.

```python
def extract_viewport(focus, radius, filters):
    visited = {focus}
    frontier = {focus}
    edges = []
    for _ in range(radius):
        next_frontier = set()
        for node in frontier:
            for edge in node.edges():
                if not edge.matches(filters):
                    continue
                edges.append(edge)
                other = edge.other_end(node)
                if other not in visited:
                    next_frontier.add(other)
                    visited.add(other)
        frontier = next_frontier
    return visited, edges
```

Filters at this step apply to the *traversal*: an edge whose `protocol`
fails `filters.protocols` is not followed, so the entity at the far end
may not enter the viewport at all.

To bound runaway traversals, the engine caps the viewport size (e.g. 500
entities) and falls back to a smaller radius if the cap is hit.

---

## Step 2 — Topology analysis

For every entity in the viewport, compute four metrics:

| Metric                       | Algorithm                                              | Cost                          |
| ---------------------------- | ------------------------------------------------------ | ----------------------------- |
| `degree_centrality`          | edges incident / (n - 1)                               | O(E)                          |
| `betweenness_centrality`     | Brandes' algorithm                                     | O(V·E) on unweighted graphs   |
| `cluster_coverage`           | fraction of viewport reachable in 1 hop                | O(V·E)                        |
| `path_relevance`             | 1.0 if on `navigation_path`, decayed by recency        | O(V)                          |

These are computed **on the viewport**, not the global graph. A service
that is central to a payments-scoped viewport may be peripheral in a
company-wide one.

Topology metrics are cached per (focus, radius, filters) tuple with a
short TTL. See [PRD §16 / Performance risk](../../PRD.md).

---

## Step 3 — Fragment collection

For each entity and relationship in the viewport, gather candidate
fragments via three anchoring mechanisms:

1. **Direct subjects** — fragments whose `subjects` include this entity ID.
2. **Direct relations** — fragments whose `relations` include this edge ID.
3. **Tag-matched** — fragments whose `tags` intersect the entity's `labels`.

The same fragment may be reached via multiple paths (e.g. tag match *and*
explicit subject). Deduplication happens in step 5.

Collection is parallelizable per viewport entity.

---

## Step 4 — Fragment filtering & lifting

For each candidate fragment:

```python
def include_fragment(fragment, request, topology):
    # Lens check
    if not (set(fragment.coverage.lenses) & set(request.lenses)):
        return False

    # Compute effective zoom_min via lifting
    base = fragment.coverage.zoom_min
    subject_metrics = topology.metrics_for(fragment.subject_ids())

    if (fragment.coverage.lift_on.centrality_threshold and
        any(m.centrality > fragment.coverage.lift_on.centrality_threshold
            for m in subject_metrics)):
        base -= fragment.coverage.lift_by

    if (fragment.coverage.lift_on.cluster_coverage_threshold and
        any(m.cluster_coverage > fragment.coverage.lift_on.cluster_coverage_threshold
            for m in subject_metrics)):
        base -= fragment.coverage.lift_by

    if (fragment.coverage.lift_on.path_match and
        any(s in request.navigation_path for s in fragment.subject_ids())):
        base -= fragment.coverage.lift_by

    effective_zoom_min = max(0, base)
    return effective_zoom_min <= request.zoom <= fragment.coverage.zoom_max
```

`zoom_max` is **never** lifted. Lifting only widens the relevance window
downward. See [`concepts/topology.md`](../concepts/topology.md).

---

## Step 5 — Deduplication & ranking

Multiple paths to the same fragment collapse to one entry.

Survivors are ranked by, in order:

1. **`zoom_proximity`** — `|request.zoom - midpoint(effective_zoom_min, zoom_max)|`.
   Closer to the center of the relevance window wins.
2. **`lens_specificity`** — exact lens match beats broad lens set.
3. **`provenance.confidence`** — higher wins.
4. **`provenance.reviewed`** — `true` wins over `false`.
5. **Freshness** — more recent `last_synced` wins.

The top-ranked fragments (typically 5–15) are passed to the LLM. The rest
are returned as "additional sources" in the response so the UI can offer
"show more."

---

## Step 6 — LLM assembly

The LLM receives:

- The viewport graph (entities + relationships).
- The ranked fragments.
- The current zoom and lens set.
- The navigation path.
- Topology highlights.

It produces:

- A cohesive narrative summary appropriate for the zoom level.
- Citations back to fragment IDs so the reader can verify any claim.
- A suggested Mermaid.js or C4 diagram.
- Follow-up navigation suggestions ("Zoom into service.auth for API
  details").

The exact prompt template is in
[`framework/llm-integration.md`](./llm-integration.md).

---

## Why six steps and not five

A naïve implementation would skip topology analysis and rely solely on
declared `zoom_min` / `zoom_max`. That is the C4 model: fixed levels,
nothing dynamic.

The topology step is what makes NexusDocs different. It lets fragment
authors write "this is relevant at zoom 50–80" without anticipating every
view; the engine raises that floor when the graph says it should.

The LLM step is the second differentiator. The engine produces a
*narrative*, not a list of fragments. The reader gets a coherent
explanation of the current view, citing sources rather than dumping them.

---

## Failure modes

| Failure                                  | Behavior                                                    |
| ---------------------------------------- | ----------------------------------------------------------- |
| Focus entity does not exist              | 404. The request is rejected.                               |
| Viewport explodes past the cap           | Reduce radius; warn the user; render the smaller viewport.  |
| LLM unavailable / over budget            | Render fragments verbatim with a static, deterministic header. |
| All candidate fragments fail lens check  | Render the diagram + structured viewport; LLM is told "no fragments matched, summarize the structure only." |
| `navigation_path` is empty               | All steps still work; `path_match` lifts simply do not fire. |

The view engine prefers degraded rendering over outright failure. A
view with no LLM summary is still useful; a 500 is not.

---

## See also

- [`concepts/zoom-axis.md`](../concepts/zoom-axis.md), [`concepts/lenses.md`](../concepts/lenses.md), [`concepts/topology.md`](../concepts/topology.md), [`concepts/navigation.md`](../concepts/navigation.md) — the four parameters in detail.
- [`framework/llm-integration.md`](./llm-integration.md) — step 6 in detail.
- [`framework/api.md`](./api.md) — `POST /api/v1/views/render`.
