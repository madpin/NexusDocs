# Navigation: Focus, Radius, Viewport, Path

> How a reader moves through the graph, and how that movement shapes the view.

**Source of truth:** [PRD §10](../../PRD.md), [PRD §6.5](../../PRD.md)

---

## Definition

NexusDocs is navigated like a map. Four parameters describe the reader's
position and motion:

| Parameter            | Type             | What it represents                                                |
| -------------------- | ---------------- | ----------------------------------------------------------------- |
| **`focus`**          | Entity ID        | The node at the center of the view.                               |
| **`radius`**         | int              | How many edge-hops outward to include from focus.                 |
| **`viewport`**       | derived subgraph | The set of entities and edges within `radius` hops of `focus`.    |
| **`navigation_path`** | Entity ID list   | An ordered trail of recently-visited focus entities (the session). |

`focus`, `radius`, [`zoom`](./zoom-axis.md), and [`lenses`](./lenses.md)
together fully define a view.

---

## Focus

The `focus` is a single entity ID. It is what the reader has currently
"clicked into."

Examples of focus values:

```
focus: company.acme              → company-wide overview at zoom 5–15
focus: division.fintech          → division view at zoom 10–25
focus: team.payments             → team view at zoom 15–35
focus: service.payments-api      → service view at zoom 35–65
focus: kafka_topic.user-events   → topic view at zoom 45–70
focus: class.JwtSigner           → code view at zoom 75–100
```

The view engine assembles content **around** the focus. The focus is always
visible in the rendered view, even at large zoom values.

---

## Radius

`radius` is an integer counting edge-hops outward from focus. Default `radius`
is `2`.

| Radius | What you see                                                                |
| ------ | --------------------------------------------------------------------------- |
| 0      | Only the focus entity. Used by code-level views and identity cards.         |
| 1      | Focus + every entity directly connected to it.                              |
| 2      | + entities connected to those (e.g. team → service → topic).                |
| 3+     | + indirect dependencies. Useful for impact analysis. Slower.                |

The viewport size grows non-linearly with radius. A radius-4 view of a busy
service may contain hundreds of entities. The engine bounds collection to
prevent runaway traversal — see [`framework/view-engine.md`](../framework/view-engine.md).

---

## Viewport

The **viewport** is the *derived* set of entities and edges that fall within
`radius` hops of `focus`, after filters are applied.

Viewport ≠ rendered view. The viewport is what the engine *reasons over*; the
rendered view is what gets shown. Many fragments anchored to viewport entities
will be excluded by zoom or lens filters.

The viewport is also the set over which [topology metrics](./topology.md) are
computed. Centrality is *relative to the viewport*, not the global graph. A
service that is central to a payments-scoped viewport may be peripheral in a
company-wide one.

---

## Navigation path

The `navigation_path` is an ordered list of focus entities the reader has
visited *in this session*. It is a stack:

```
[team.payments, service.payments-api, kafka_topic.order-events]
                                             ▲
                                        current focus
```

The path is **session-scoped**. It clears when the reader starts a new
session or explicitly resets. It is **not** persisted as part of any saved
[ViewPreset](../schemas/view-preset.md).

The path influences fragment relevance via the `path_match` [lift
condition](./topology.md): any fragment whose subject is on the active path
gets a relevance boost. A reader who clicked through `team → service → topic`
will see fragments about that exact chain surface earlier in the view than
they otherwise would.

---

## Primary navigation actions

| Action                  | Effect                                                                                  |
| ----------------------- | --------------------------------------------------------------------------------------- |
| **Focus**               | Center the view on a new entity. Pushes onto `navigation_path`.                         |
| **Zoom in**             | Raise `zoom`, revealing more detail.                                                    |
| **Zoom out**            | Lower `zoom`, abstracting away detail.                                                  |
| **Switch lens**         | Change the active lens set.                                                             |
| **Expand radius**       | Show more relationship hops.                                                            |
| **Trace relationship**  | Click a specific edge; the engine focuses on that edge and its endpoints.               |
| **Navigate path**       | Follow a chain of relationships, e.g. `team → service → topic → consumer service`.      |
| **Save preset**         | Persist focus + zoom + lenses + radius as a named [ViewPreset](../schemas/view-preset.md). |
| **Compare views**       | Open two viewports side-by-side at different zoom or lens settings.                     |

---

## Searching as navigation

Search is just another way to set `focus`. Searching `"payments"` returns
candidate entities; selecting one sets the focus and starts a navigation
path. The path is preserved across searches in a session.

See [`framework/api.md`](../framework/api.md) for the search API.

---

## Worked example

```
Session start: navigation_path = []

1. Search "payments" → user picks team.payments
   focus = team.payments
   navigation_path = [team.payments]

2. User zooms from 20 → 35 → 50, then clicks service.payments-api
   focus = service.payments-api
   navigation_path = [team.payments, service.payments-api]

3. User clicks the Kafka edge to topic.order-events
   focus = kafka_topic.order-events
   navigation_path = [team.payments, service.payments-api, kafka_topic.order-events]

4. User zooms out to 30. Topology kicks in:
   - kafka_topic.order-events is on the path → path_match fires.
   - Fragments about that topic with zoom_min: 50 lift to effective_zoom_min: 30.
   - The reader sees Kafka detail one level above where the fragment was authored.
```

---

## See also

- [`concepts/zoom-axis.md`](./zoom-axis.md) — depth axis.
- [`concepts/lenses.md`](./lenses.md) — perspective filter.
- [`concepts/topology.md`](./topology.md) — how the path triggers lifting.
- [`schemas/view-preset.md`](../schemas/view-preset.md) — persisting a view configuration.
- [`framework/view-engine.md`](../framework/view-engine.md) — runtime resolution.
