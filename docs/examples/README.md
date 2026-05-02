# Examples

> Worked end-to-end examples that combine entities, relationships,
> fragments, and views.

**Source of truth:** [PRD §13](../../PRD.md)

---

## What's here

| Page                                            | What it shows                                                |
| ----------------------------------------------- | ------------------------------------------------------------ |
| [`sample-graph.md`](./sample-graph.md)          | A complete YAML graph for a small Payments scenario.         |

---

## User-flow walkthroughs

These are the user flows from the PRD. Each one is a story of a reader
moving through the graph, seeing different fragments surface based on
zoom, lenses, and topology.

### 13.1 Director investigating a cross-team dependency

A division director wants to understand a cross-team risk.

```
1. Director opens NexusDocs, sees company map (zoom 5).
2. Clicks on "Fintech Division" → zoom 15, sees 4 teams.
3. Notices a thick edge between Team Payments and Team Identity → clicks edge.
4. View centers on the relationship; zoom auto-adjusts to 30.
5. LLM summary: "Team Payments depends on Team Identity via 3 integration
   points: REST API for session verification, Kafka for user lifecycle
   events, and a shared Postgres read replica for user profiles."
6. Director clicks "Kafka" edge → zoom stays at 30 but Kafka fragments
   surface because Kafka has high cluster_coverage in this viewport.
7. Summary now includes: "The user.events.v1 topic carries ~1200 msgs/sec
   and is consumed by 4 services across 3 teams."
```

What made this work:

- The director never had to know zoom 30 was the "right" depth.
- Kafka fragments with `zoom_min: 50` lifted to `effective_zoom_min: 30`
  via `cluster_coverage_threshold: 0.5` and `lift_by: 20`.

Source: [PRD §13.1](../../PRD.md).

### 13.2 Principal developer debugging a cross-team issue

A staff engineer at 2 AM, an incident in flight.

```
1. Principal Dev starts at service.payments-api (zoom 45, lens=debug).
2. Sees outgoing edges: REST → auth, Kafka → order-events, Postgres → transactions-db.
3. Notices error rate on the REST → auth edge (metadata from monitoring).
4. Clicks the REST edge → zoom auto-adjusts to 55.
5. Fragment surfaces: "Auth Service rate-limits to 500 req/s per consumer.
   Circuit breaker trips after 3 consecutive 429s."
6. Clicks through to service.auth (now another team's service).
7. At zoom 55, sees high-level components: TokenIssuer, SessionManager,
   RateLimiter.
8. Zooms to 75 → sees specific code: RateLimiter class, config values,
   Kafka consumer group lag for the topic this service reads.
9. All from the same graph, same tool — no switching context.
```

What made this work:

- `lens=debug` surfaced failure-mode fragments, not architecture.
- `path_match` lifting kept the auth-related fragments relevant as the
  reader walked into the auth service.
- Class- and component-level entities were already in the graph for the
  hot paths.

Source: [PRD §13.2](../../PRD.md).

### 13.3 Junior developer onboarding

A new hire, week one.

```
1. Junior Dev opens NexusDocs, searches "payments team".
2. Lands on team.payments view (zoom 20, lens=onboarding).
3. LLM summary: "Team Payments builds and operates the billing platform.
   Key services: payments-api, invoice-generator, payment-gateway. Tech
   stack: Go, PostgreSQL, Kafka."
4. Fragment surfaces: "Getting Started" guide (zoom 15–40, lens=onboarding).
5. Clicks service.payments-api → zoom 45.
6. Fragment surfaces: "Local Setup" runbook (zoom 40–80, lens=onboarding).
7. Zooms to 70 → sees components, DB schema, Kafka topics with exact names.
8. All setup instructions, architecture context, and code pointers in one flow.
```

What made this work:

- `lens=onboarding` content was carried by fragments specifically tagged
  for it.
- The same graph the staff engineer used (Flow 13.2) at the same nodes;
  only zoom and lens differed.

Source: [PRD §13.3](../../PRD.md).

### 13.4 LLM auto-ingestion

A developer pushes a commit; documentation updates automatically.

```
1. Developer pushes commit updating auth-service README:
   "Added support for gRPC endpoint for internal token validation"

2. Git webhook triggers NexusDocs ingestion pipeline.

3. LLM reads the diff, extracts:
   - New relationship:
       service.auth ──provides_api(grpc)──▶ service.payments-api
   - New fragment:
       "gRPC token validation endpoint added for low-latency internal
       calls. Proto definition at /proto/auth/v2/token.proto"
       zoom_min: 45, zoom_max: 70, lenses: [technical]
       confidence: 0.83, reviewed: false

4. Graph updated. Next time anyone views service.auth at zoom 45+, they
   see the new gRPC edge and associated documentation.

5. No manual documentation update needed.
```

What made this work:

- The Git connector triggered on push.
- LLM extraction with confidence scoring filled in the new edge and
  fragment.
- The new fragment is `reviewed: false` so it surfaces with a ⚠️ badge
  until a human approves.

Source: [PRD §13.4](../../PRD.md).

---

## See also

- [`sample-graph.md`](./sample-graph.md) — the YAML for a working graph.
- [`framework/view-engine.md`](../framework/view-engine.md) — why these flows behave this way.
- [PRD §13](../../PRD.md) — original flow descriptions.
