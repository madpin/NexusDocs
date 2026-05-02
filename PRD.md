# Product Requirements Document (PRD)

## NexusDocs — Topology-Aware Knowledge Graph Documentation Platform

**Version:** 1.0 Draft  
**Author:** Thiago M Pinto  
**Date:** 2 May 2026  
**Status:** Proposal

---

## 1. Executive Summary

NexusDocs is an AI-native documentation and system-architecture platform that models an organization's people, teams, systems, infrastructure, and documentation as a single navigable knowledge graph. Unlike traditional wikis or architecture tools, NexusDocs treats **depth as a continuous zoom axis** (like a map) and **relevance as a function of graph topology at read time** — not as a property of the reader's job title.

Documentation is stored as **fragments** anchored to graph nodes and edges, each tagged with zoom-range and lens metadata. At render time, a view engine assembles the right fragments based on the reader's current focus, zoom level, chosen lens, navigation path, and the structural significance of entities in the viewport. An LLM pipeline ingests existing READMEs, code, and config files to populate the graph automatically, and generates audience-appropriate summaries on demand.

The result: one source of truth, infinite views — a director debugging a production issue sees the same graph as a junior developer onboarding, just at a different zoom.

---

## 2. Problem Statement

### 2.1 The Documentation Fragmentation Problem

In any mid-to-large tech organization, documentation about the same system exists in many places, written for different audiences:

| Document | Audience | Lives In |
|---|---|---|
| Product spec | Product managers | Confluence |
| Architecture diagram | Staff engineers | Structurizr / draw.io |
| README | Developers | Git repo |
| Runbook | On-call SREs | Internal wiki |
| Client integration guide | External partners | Docs site |
| Incident postmortem | Leadership + Eng | JIRA / Google Doc |

These documents **describe the same entities and relationships** but are disconnected. When System A changes how it publishes to Kafka, the README may get updated but the architecture diagram, runbook, and client guide do not. There is no single place to ask: *"Show me everything we know about this Kafka topic and everyone who touches it."*

### 2.2 The Depth Problem

A director and a junior developer need different levels of detail, but current tools force a binary choice: either you see everything (overwhelming) or you see a curated summary (lossy). Worse, depth is typically bound to **role** ("this is the executive summary") rather than to **context** ("I am currently zoomed into the payments service's Kafka integrations").

A principal developer looking at another team's system wants a high-level architecture view. That same principal developer, debugging an incident at 2 AM, wants to see exact topic names and consumer group IDs. **The person didn't change — the view did.**

### 2.3 The Relationship Visibility Problem

Communication protocols (REST, Kafka, gRPC, database reads/writes) are first-class architectural concerns, but they are buried in code and config files. There is no way to ask: *"Which services write to this database and which ones read from it?"* or *"Show me every team that depends on this Kafka cluster"* without manually tracing code.

---

## 3. Vision

**NexusDocs is Google Maps for your organization's technical landscape.**

- Zoom out: see the company, its divisions, and which teams own which domains.
- Zoom in: see services, their APIs, their Kafka topics, their database schemas.
- Keep zooming: see classes, functions, and specific code paths.
- Switch lenses: view the same graph through a product lens, a technical lens, a debugging lens, or an operations lens.
- Navigate relationships: click on a Kafka topic to see all publishers and consumers across all teams.
- Let the topology decide importance: if Kafka is central to the current view, Kafka-related documentation surfaces automatically — even if the reader didn't ask for it.

---

## 4. Goals

| #   | Goal                                                                                              | Measure                                                                           |
| --- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| G1  | **Single source of truth** for entities, relationships, and documentation across the organization | Reduction in duplicate/contradictory documentation                                |
| G2  | **Depth without role-binding** — any user can navigate to any zoom level                          | Zero role-gated content filters in the view engine                                |
| G3  | **Topology-aware relevance** — the graph determines what surfaces, not static tags                | Fragment surfacing correlates with structural significance (centrality, coverage) |
| G4  | **LLM-powered ingestion** — existing READMEs, code, and configs populate the graph automatically  | >60% of initial graph populated without manual entry                              |
| G5  | **LLM-powered rendering** — dynamic summaries assembled from fragments per view                   | Users rate summaries as accurate ≥80% of the time                                 |
| G6  | **Protocol-aware relationships** — Kafka, REST, gRPC, DB reads/writes are first-class edges       | All integration points queryable by protocol type                                 |

---

## 5. Non-Goals (v1)

| #   | Non-Goal                                 | Rationale                                                                 |
| --- | ---------------------------------------- | ------------------------------------------------------------------------- |
| NG1 | Replacing JIRA, Confluence, or Git       | NexusDocs indexes and links to them; it does not replace them             |
| NG2 | Access control / permissions engine      | v1 assumes all users can see all nodes; ACLs come in v2                   |
| NG3 | Real-time code analysis (AST parsing)    | v1 uses README/config ingestion; deep code analysis is a future extension |
| NG4 | Auto-generating code from documentation  | The LLM reads code to produce docs, not the reverse                       |
| NG5 | Replacing monitoring/observability tools | NexusDocs links to dashboards; it does not collect metrics                |

---

## 6. Core Concepts

### 6.1 The Graph

Everything is a node or an edge in a directed property graph.

**Nodes** (Entities) represent things that exist:
- Organizational: `Company`, `Division`, `Tribe`, `Team`, `Person`
- Technical: `System`, `Service`, `Component`, `Class`, `Function`
- Infrastructure: `Database`, `KafkaCluster`, `KafkaTopic`, `APIGateway`, `Queue`, `Cache`
- Documentation: `Document`, `DocFragment`

**Edges** (Relationships) represent how things connect:
- Organizational: `belongs_to`, `owns`, `leads`, `member_of`, `reports_to`
- Technical: `depends_on`, `calls_api`, `provides_api`, `extends`, `implements`
- Data flow: `publishes_to`, `consumes_from`, `reads_from`, `writes_to`, `streams_to`
- Documentation: `describes`, `references`, `supersedes`

Every edge carries **protocol metadata**: the *how* of the relationship.

### 6.2 The Zoom Axis

Depth is a continuous numeric axis from 0 to 100, analogous to map zoom levels:

| Zoom Range | Default Meaning | Example Content |
|---|---|---|
| 0–10 | Company / domain map | "Indeed has 4 engineering divisions" |
| 11–25 | Teams, ownership, major systems | "Team Payments owns the Billing Platform" |
| 26–40 | Systems and integrations | "Billing Platform communicates with Auth Service via REST" |
| 41–60 | Services, APIs, topics, databases | "Auth Service publishes to `auth.events.v1` Kafka topic" |
| 61–80 | Components, modules, flows | "The `TokenIssuer` module validates credentials and signs JWTs" |
| 81–100 | Classes, functions, files, config | "Class `JwtSigner` in `/src/auth/jwt.ts` uses RS256" |

**Zoom is a view parameter, not a content property.** A fragment declares the zoom *range* where it is useful, but the view engine may lift or suppress it based on topology.

### 6.3 Lenses

A lens is a perspective filter that determines *what kind* of information is shown at any zoom level:

| Lens         | Shows                                                       | Hides                                   |
| ------------ | ----------------------------------------------------------- | --------------------------------------- |
| `product`    | Goals, customers, outcomes, features, roadmap items         | Implementation details, infra specifics |
| `technical`  | Architecture, interfaces, protocols, schemas                | Business context, client language       |
| `operations` | Alerts, runbooks, SLOs, on-call, dependency chains          | Code-level detail, product framing      |
| `debug`      | Traces, logs, code paths, error handling, failure modes     | High-level summaries                    |
| `client`     | External-facing explanations, API guides, integration steps | Internal team context                   |
| `onboarding` | Setup guides, glossary, "start here" paths                  | Deep debugging, incident history        |

Lenses can be combined: `lens=[technical, debug]` shows architecture AND failure modes.

### 6.4 DocFragments

Documentation is not stored as monolithic pages. It is decomposed into **fragments** — discrete chunks of text, each anchored to one or more graph nodes or edges, with metadata about where and when it is relevant.

A single README is ingested as multiple fragments: one for the high-level overview (zoom 25–45), one for the setup guide (zoom 65–85, lens=onboarding), one for the API reference (zoom 50–70, lens=technical).

### 6.5 Topology-Aware Relevance

**This is the key differentiator.** Fragment visibility is not statically declared — it is computed at render time based on the graph topology within the current viewport.

If Kafka appears in 2 of 20 visible services, Kafka fragments stay at their declared zoom floor. If Kafka appears in 16 of 20 visible services, it becomes structurally significant and its fragments **lift** into higher (more zoomed-out) zoom levels automatically.

This mirrors how physical maps work: a small road is hidden at city scale, unless it is the only bridge between two districts — then it surfaces because of structural significance.

---

## 7. Data Model

### 7.1 Entity Schema

```yaml
Entity:
  id: string                    # Unique identifier (e.g., "team.payments", "service.auth")
  kind: enum                    # team | person | system | service | component | class |
                                # function | database | kafka_cluster | kafka_topic |
                                # api_endpoint | queue | cache | document
  name: string                  # Human-readable name
  parent: string | null         # Parent entity ID (org hierarchy)
  labels: string[]              # Freeform tags for cross-cutting concerns
  metadata: map<string, any>    # Kind-specific metadata
  created_at: datetime
  updated_at: datetime
  source: SourceRef             # Where this entity was discovered/defined
```

**Kind-specific metadata examples:**

```yaml
# For kind: service
metadata:
  technology: "Node.js / Express"
  repository: "https://gitlab.com/indeed/auth-service"
  deployment: "kubernetes/us-east-1"
  tier: "tier-1"

# For kind: kafka_topic
metadata:
  cluster: "core-kafka-prod"
  partitions: 12
  retention_days: 7
  schema_registry: "https://schema-registry.internal/subjects/user-events-value"

# For kind: person
metadata:
  ldap: "tpinto"
  email: "tpinto@indeed.com"
  role: "Principal Developer"
```

### 7.2 Relationship Schema

```yaml
Relationship:
  id: string                    # Unique identifier
  source: string                # Source entity ID
  target: string                # Target entity ID
  type: enum                    # owns | depends_on | calls_api | provides_api |
                                # publishes_to | consumes_from | reads_from |
                                # writes_to | streams_to | member_of | leads |
                                # reports_to | describes | references | escalates_to
  protocol: string | null       # kafka | rest | grpc | graphql | postgres | mysql |
                                # redis | s3 | sqs | sns | websocket | null
  mode: enum | null             # sync | async | batch | null
  metadata: map<string, any>    # Relationship-specific details
  created_at: datetime
  updated_at: datetime
  source_ref: SourceRef
```

**Relationship metadata examples:**

```yaml
# REST API call
Relationship:
  id: rel.auth-calls-billing-verify
  source: service.auth
  target: service.billing
  type: calls_api
  protocol: rest
  mode: sync
  metadata:
    method: POST
    path: /api/v2/verify-session
    auth: oauth2
    timeout_ms: 3000
    circuit_breaker: true

# Kafka publish
Relationship:
  id: rel.auth-publishes-user-events
  source: service.auth
  target: topic.user-events
  type: publishes_to
  protocol: kafka
  mode: async
  metadata:
    topic: user.events.v1
    key_schema: user_id
    value_format: avro
    avg_throughput: "1200 msgs/sec"

# Database read/write
Relationship:
  id: rel.billing-writes-transactions-db
  source: service.billing
  target: database.transactions
  type: writes_to
  protocol: postgres
  mode: sync
  metadata:
    tables: [transactions, invoices, payment_methods]
    connection_pool_size: 20
    read_replicas: false
```

### 7.3 DocFragment Schema

```yaml
DocFragment:
  id: string                    # Unique identifier
  doc_id: string | null         # Parent document ID (if part of a larger doc)
  title: string
  body: string                  # Markdown content
  format: enum                  # markdown | plaintext | structured_yaml | mermaid

  # --- Anchoring (where this fragment attaches) ---
  subjects:
    - entity: string            # Entity ID this fragment describes
  relations:
    - rel: string               # Relationship ID this fragment describes
  tags: string[]                # Cross-cutting concern tags (e.g., "kafka",
                                # "platform-standards", "security")

  # --- Coverage (when this fragment is relevant) ---
  coverage:
    zoom_min: int               # Default minimum zoom to surface (0-100)
    zoom_max: int               # Maximum zoom where still relevant (0-100)
    lenses: string[]            # Which lenses include this fragment
    granularity: enum           # company | division | team | system | service |
                                # component | code
    lift_on:                    # Conditions under which zoom_min is lowered
      centrality_threshold: float | null    # 0.0-1.0, lift if subject's centrality exceeds
      cluster_coverage_threshold: float | null  # 0.0-1.0, lift if % of viewport nodes
                                                # connected to subject exceeds
      path_match: bool          # Lift if subject is on reader's active navigation path
    lift_by: int                # How many zoom levels to lower zoom_min when lifted

  # --- Provenance (where this fragment came from) ---
  provenance:
    source_type: enum           # readme | adr | runbook | ticket | api_spec |
                                # config_file | llm_generated | manual
    source_path: string | null  # File path or URL of origin
    source_hash: string | null  # Content hash for change detection
    generated_by: enum          # human | llm | hybrid
    confidence: float           # 0.0-1.0, LLM confidence in extraction accuracy
    reviewed: bool              # Has a human verified this fragment?
    last_synced: datetime
    created_at: datetime
    updated_at: datetime
```

### 7.4 ViewPreset Schema

```yaml
ViewPreset:
  id: string
  name: string                  # "My team's architecture", "Debug payments flow"
  owner: string                 # Person entity ID
  shared_with: string[]         # Team or person entity IDs
  focus: string                 # Entity ID to center on
  zoom: int                     # 0-100
  lenses: string[]              # Active lenses
  radius: int                   # How many relationship hops to include
  filters:
    entity_kinds: string[]      # Only show these entity types
    relationship_types: string[] # Only show these edge types
    protocols: string[]         # Only show these protocols
    tags: string[]              # Only show nodes/fragments with these tags
  created_at: datetime
  updated_at: datetime
```

---

## 8. View Engine

### 8.1 View Resolution Algorithm

When a user requests a view, the engine executes the following pipeline:

```
INPUT: ViewRequest {
  focus: entity_id,
  zoom: int (0-100),
  lenses: string[],
  radius: int (relationship hops),
  filters: FilterSet,
  navigation_path: entity_id[]    # trail of previously visited nodes
}

STEP 1: SUBGRAPH EXTRACTION
  - Start at focus entity
  - Traverse outward `radius` hops along edges matching filters
  - Collect all entities and relationships in the subgraph
  - This is the "viewport"

STEP 2: TOPOLOGY ANALYSIS
  For each entity in viewport, compute:
  - degree_centrality: connections / total possible connections
  - betweenness_centrality: fraction of shortest paths passing through entity
  - cluster_coverage: % of viewport entities connected to this entity
  - path_relevance: is this entity on the navigation_path? how recently?

STEP 3: FRAGMENT COLLECTION
  For each entity and relationship in viewport:
  a) Collect directly anchored fragments (entity in fragment.subjects)
  b) Collect relationship-anchored fragments (rel in fragment.relations)
  c) Collect tag-matched fragments (intersection of entity.labels ∩ fragment.tags)

STEP 4: FRAGMENT FILTERING & LIFTING
  For each candidate fragment:
  - Check lens match: fragment.coverage.lenses ∩ request.lenses ≠ ∅
  - Compute effective_zoom_min:
      base = fragment.coverage.zoom_min
      if fragment.coverage.lift_on.centrality_threshold
         AND subject.centrality > threshold:
           base -= fragment.coverage.lift_by
      if fragment.coverage.lift_on.cluster_coverage_threshold
         AND subject.cluster_coverage > threshold:
           base -= fragment.coverage.lift_by
      if fragment.coverage.lift_on.path_match
         AND subject in navigation_path:
           base -= fragment.coverage.lift_by
      effective_zoom_min = max(0, base)
  - Include fragment if: effective_zoom_min <= request.zoom <= fragment.coverage.zoom_max

STEP 5: DEDUPLICATION & RANKING
  - Deduplicate by fragment.id (same fragment reached via multiple paths → shown once)
  - Rank by:
      1. zoom_proximity: |request.zoom - midpoint(effective_zoom_min, zoom_max)|
      2. lens_specificity: exact lens match > wildcard
      3. provenance.confidence
      4. provenance.reviewed (human-reviewed > unreviewed)
      5. freshness: provenance.last_synced recency

STEP 6: LLM ASSEMBLY
  - Feed viewport graph + ranked fragments to LLM
  - Generate cohesive narrative for the current view
  - Include citations back to fragment IDs and source documents
  - Generate/update Mermaid.js or C4 diagram for visual rendering

OUTPUT: RenderedView {
  summary: string (LLM-generated narrative),
  diagram: string (Mermaid/C4 markup),
  fragments: RankedFragment[] (sourced content),
  entities: Entity[] (nodes in viewport),
  relationships: Relationship[] (edges in viewport),
  topology_highlights: {
    most_central: entity_id,
    structural_concerns: entity_id[]   # high centrality/betweenness
  }
}
```

### 8.2 The Map Analogy, Formally

| Map Concept | NexusDocs Equivalent |
|---|---|
| Geographic coordinates | Entity ID (position in graph) |
| Zoom level | `zoom` parameter (0–100) |
| Map layer (satellite, terrain, traffic) | `lens` parameter |
| Viewport bounds | `focus` + `radius` |
| Road importance algorithm | Topology-aware relevance (centrality, coverage) |
| A small road shown because it's the only bridge | A fragment lifted because its subject has high betweenness |
| Points of interest appearing at certain zooms | Fragments surfacing at their `zoom_min` (or lifted `effective_zoom_min`) |
| Navigation route highlighting | `navigation_path` boosting path-relevant fragments |

---

## 9. LLM Integration Pipeline

### 9.1 Ingestion Pipeline

```
SOURCE CONNECTORS              EXTRACTION ENGINE            GRAPH POPULATION
┌─────────────────┐           ┌──────────────────┐         ┌───────────────┐
│ Git Repos        │──README──▶│                  │──────▶  │ Create/Update │
│ (README, ADR,   │──code───▶ │  LLM Extractor   │         │ Entities      │
│  docker-compose, │──config─▶ │                  │         │               │
│  k8s manifests)  │           │  Schema-guided   │──────▶  │ Create/Update │
├─────────────────┤           │  extraction with  │         │ Relationships │
│ Confluence       │──pages──▶ │  confidence       │         │               │
├─────────────────┤           │  scoring          │──────▶  │ Create/Update │
│ JIRA             │──tickets─▶│                  │         │ DocFragments  │
├─────────────────┤           │                  │         │               │
│ API Specs        │──openapi─▶│                  │         │ With          │
│ (OpenAPI, Proto) │──proto──▶ │                  │         │ provenance &  │
├─────────────────┤           └──────────────────┘         │ confidence    │
│ Backstage Catalog│──yaml───▶                              └───────────────┘
└─────────────────┘
```

**Ingestion steps:**

1. **Source connector** pulls content (Git webhook on push, scheduled Confluence/JIRA sync)
2. **Change detector** diffs against `provenance.source_hash` — only re-processes changed files
3. **LLM Extractor** uses schema-guided prompts:
   - *"Given this README, extract all services, databases, Kafka topics, and APIs mentioned. For each, identify relationships with protocols."*
   - *"Decompose this document into fragments. For each fragment, estimate the zoom range (0–100) and appropriate lenses."*
4. **Confidence scoring**: each extracted entity/relationship/fragment gets a `confidence` score
5. **Conflict resolution**: if LLM extraction conflicts with existing human-entered data, flag for review rather than overwrite
6. **Graph population**: upsert entities, relationships, and fragments into the graph database

### 9.2 Rendering Pipeline

At view time, the LLM assembles a coherent narrative:

```
INPUT:
  - Viewport subgraph (entities + relationships)
  - Ranked fragments for current view
  - Current zoom + lenses
  - Navigation context

PROMPT TEMPLATE:
  "You are rendering a view of a technical knowledge graph.
   Current focus: {focus_entity.name}
   Zoom level: {zoom} (scale: 0=company, 100=code)
   Active lenses: {lenses}
   
   Entities in viewport: {entity_list}
   Relationships: {relationship_list}
   Relevant documentation fragments: {fragments}
   
   Generate a cohesive summary appropriate for zoom level {zoom}.
   At this zoom, the reader expects {zoom_expectations}.
   Highlight structurally significant entities: {topology_highlights}.
   Include citations as [fragment_id]."

OUTPUT:
  - Narrative summary
  - Suggested diagram (Mermaid.js)
  - Follow-up navigation suggestions ("Zoom into service.auth for API details")
```

### 9.3 Freshness & Trust

| Signal | Handling |
|---|---|
| `confidence < 0.6` | Fragment flagged with ⚠️, human review requested |
| `confidence ≥ 0.8` | Fragment displayed normally |
| `reviewed: true` | Fragment marked with ✓ |
| `last_synced > 30 days` | Fragment flagged as potentially stale |
| `source_hash` mismatch | Source changed since extraction — re-ingest triggered |

---

## 10. Navigation & Interaction Model

### 10.1 Primary Navigation Actions

| Action | Description | Example |
|---|---|---|
| **Focus** | Center view on an entity | Click on `team.payments` |
| **Zoom In** | Increase zoom level, revealing more detail | Scroll / slider from 25 → 45 |
| **Zoom Out** | Decrease zoom level, abstracting away detail | Scroll / slider from 45 → 25 |
| **Switch Lens** | Change perspective filter | Toggle from `technical` to `debug` |
| **Expand Radius** | Show more relationship hops | Increase from radius 2 → 4 |
| **Trace Relationship** | Follow a specific edge | Click on the Kafka arrow between two services |
| **Navigate Path** | Follow a chain of relationships | `team → service → topic → consumer service` |
| **Save Preset** | Bookmark current view state | "Save as: Payments Debug View" |
| **Compare Views** | Side-by-side views at different zoom/lens | Zoom 25 `product` vs Zoom 60 `technical` |

### 10.2 Navigation Path Context

The system maintains a **navigation stack** — an ordered list of entities the reader has visited in this session. This stack influences fragment relevance:

```
Session navigation: [team.payments → service.payments-api → topic.order-events]

Effect: Any fragment anchored to entities ALONG this path gets a relevance boost.
If the reader is at zoom 35 and a fragment about topic.order-events has zoom_min=45,
the path_match lift may bring it to effective_zoom_min=27, surfacing it in the current view.
```

### 10.3 Search

Users can search across all entities, relationships, and fragment content:

- **Entity search**: *"payments"* → finds `team.payments`, `service.payments-api`, `database.payments-db`
- **Relationship search**: *"who publishes to order-events"* → finds all `publishes_to` edges targeting `topic.order-events`
- **Protocol search**: *"kafka dependencies"* → finds all relationships where `protocol: kafka`
- **Fragment search**: *"how to set up local auth"* → finds fragments matching by text, returns them in context of their anchored entities

---

## 11. API Surface (v1)

### 11.1 Graph CRUD

```
POST   /api/v1/entities                  # Create entity
GET    /api/v1/entities/{id}             # Read entity
PUT    /api/v1/entities/{id}             # Update entity
DELETE /api/v1/entities/{id}             # Delete entity

POST   /api/v1/relationships             # Create relationship
GET    /api/v1/relationships/{id}        # Read relationship
GET    /api/v1/entities/{id}/edges       # All relationships for an entity
DELETE /api/v1/relationships/{id}        # Delete relationship

POST   /api/v1/fragments                 # Create fragment
GET    /api/v1/fragments/{id}            # Read fragment
PUT    /api/v1/fragments/{id}            # Update fragment
GET    /api/v1/entities/{id}/fragments   # All fragments for an entity
```

### 11.2 View Rendering

```
POST   /api/v1/views/render
  Body: {
    focus: "service.auth",
    zoom: 35,
    lenses: ["technical"],
    radius: 3,
    filters: { protocols: ["kafka", "rest"] },
    navigation_path: ["team.payments", "service.payments-api"]
  }
  Response: RenderedView (summary + diagram + fragments + topology)

POST   /api/v1/views/presets             # Save view preset
GET    /api/v1/views/presets/{id}        # Load view preset
```

### 11.3 Ingestion

```
POST   /api/v1/ingest/repository         # Trigger repo ingestion
  Body: { repo_url: "...", branch: "main" }

POST   /api/v1/ingest/document            # Ingest a single document
  Body: { url: "...", source_type: "confluence" }

GET    /api/v1/ingest/status/{job_id}     # Check ingestion job status
```

### 11.4 Search

```
POST   /api/v1/search
  Body: {
    query: "kafka dependencies in payments",
    scope: "entities" | "relationships" | "fragments" | "all",
    filters: { ... }
  }
```

### 11.5 YAML Bulk Definition

```
POST   /api/v1/definitions/apply          # Apply YAML definitions (like kubectl apply)
  Body: YAML content (multi-document)
```

---

## 12. YAML Definition Format

For manual or version-controlled definitions, NexusDocs supports a YAML format inspired by Kubernetes and Backstage:

```yaml
# --- Entity definition ---
apiVersion: nexusdocs/v1
kind: Entity
spec:
  id: service.auth
  type: service
  name: Auth Service
  parent: system.identity-platform
  labels: [authentication, tier-1, identity]
  metadata:
    technology: "Node.js / Express"
    repository: "https://gitlab.com/indeed/auth-service"
    deployment: "k8s/us-east-1/auth-namespace"

---
# --- Relationship definition ---
apiVersion: nexusdocs/v1
kind: Relationship
spec:
  id: rel.auth-publishes-user-events
  source: service.auth
  target: topic.user-events
  type: publishes_to
  protocol: kafka
  mode: async
  metadata:
    topic: user.events.v1
    key_schema: user_id
    value_format: avro

---
# --- Fragment definition ---
apiVersion: nexusdocs/v1
kind: DocFragment
spec:
  id: docfrag.auth-overview
  title: "Auth Service Overview"
  body: |
    The Auth Service handles user login, token issuance, and session management.
    It publishes lifecycle events (user created, user deactivated) to Kafka for
    downstream consumption by Billing, Notifications, and Analytics.
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

---

## 13. Example User Flows

### 13.1 Director Investigating Cross-Team Dependency

```
1. Director opens NexusDocs, sees company map (zoom 5)
2. Clicks on "Fintech Division" → zoom 15, sees 4 teams
3. Notices thick edge between Team Payments and Team Identity → clicks edge
4. View centers on the relationship, zoom auto-adjusts to 30
5. LLM summary: "Team Payments depends on Team Identity via 3 integration points:
   REST API for session verification, Kafka for user lifecycle events, and shared
   Postgres read replica for user profiles."
6. Director clicks "Kafka" edge → zoom stays at 30 but Kafka fragments surface
   because Kafka has high centrality (both teams depend on it)
7. Summary now includes: "The user.events.v1 topic carries ~1200 msgs/sec and is
   consumed by 4 services across 3 teams."
```

### 13.2 Principal Developer Debugging Cross-Team Issue

```
1. Principal Dev starts at service.payments-api (zoom 45, lens=debug)
2. Sees outgoing edges: REST → auth, Kafka → order-events, Postgres → transactions-db
3. Notices error rate on the REST → auth edge (metadata from linked monitoring)
4. Clicks on the REST edge → zoom auto-adjusts to 55
5. Fragment surfaces: "Auth Service rate-limits to 500 req/s per consumer.
   Circuit breaker trips after 3 consecutive 429s."
6. Clicks through to service.auth (now viewing another team's service)
7. At zoom 55, sees high-level components: TokenIssuer, SessionManager, RateLimiter
8. Zooms to 75 → sees specific code: RateLimiter class, config values, Kafka
   consumer group lag for the topic this service reads
9. All from the same graph, same tool — no switching context
```

### 13.3 Junior Developer Onboarding

```
1. Junior Dev opens NexusDocs, searches "payments team"
2. Lands on team.payments view (zoom 20, lens=onboarding)
3. LLM summary: "Team Payments builds and operates the billing platform.
   Key services: payments-api, invoice-generator, payment-gateway.
   Tech stack: Go, PostgreSQL, Kafka."
4. Fragment surfaces: "Getting Started" guide (zoom 15–40, lens=onboarding)
5. Clicks service.payments-api → zoom 45
6. Fragment surfaces: "Local Setup" runbook (zoom 40–80, lens=onboarding)
7. Zooms to 70 → sees components, DB schema, Kafka topics with exact names
8. All setup instructions, architecture context, and code pointers in one flow
```

### 13.4 LLM Auto-Ingestion

```
1. Developer pushes commit updating auth-service README:
   "Added support for gRPC endpoint for internal token validation"
2. Git webhook triggers NexusDocs ingestion pipeline
3. LLM reads the diff, extracts:
   - New relationship: service.auth --provides_api(grpc)--> service.payments-api
   - New fragment: "gRPC token validation endpoint added for low-latency
     internal calls. Proto definition at /proto/auth/v2/token.proto"
     zoom_min: 45, zoom_max: 70, lenses: [technical]
4. Graph updated. Next time anyone views service.auth at zoom 45+,
   they see the new gRPC edge and associated documentation
5. No manual documentation update needed
```

---

## 14. Technical Architecture

### 14.1 Component Overview

```
┌───────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                           │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ Web UI  │  │ VS Code  │  │   CLI    │  │ API Consumers │   │
│  │ (React) │  │ Extension│  │ (nexdoc) │  │  (CI/CD, LLM) │   │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └──────┬────────┘   │
└───────┼────────────┼────────────┼────────────────┼────────────┘
        │            │            │                │
        ▼            ▼            ▼                ▼
┌───────────────────────────────────────────────────────────────┐
│                         API GATEWAY                           │
│              (REST + GraphQL + WebSocket)                     │
└──────────┬──────────────┬──────────────┬──────────────────────┘
           │              │              │
     ┌─────▼─────┐  ┌────▼────┐  ┌──────▼──────┐
     │   View    │  │  Graph  │  │  Ingestion  │
     │  Engine   │  │  CRUD   │  │  Pipeline   │
     │           │  │  Service │  │             │
     │ -topology │  │         │  │ -connectors │
     │ -fragment │  │         │  │ -LLM extract│
     │  ranking  │  │         │  │ -confidence │
     │ -LLM     │  │         │  │  scoring    │
     │  assembly │  │         │  │ -diffing    │
     └─────┬─────┘  └────┬────┘  └──────┬──────┘
           │              │              │
           ▼              ▼              ▼
┌───────────────────────────────────────────────────────────────┐
│                      GRAPH DATABASE                            │
│                    (Neo4j / Neptune)                            │
│                                                                │
│   Entities ──edges──▶ Entities                                 │
│       │                   │                                    │
│       └──fragments──┘     └──fragments──┘                      │
└───────────────────────────────────────────────────────────────┘
           │
     ┌─────▼─────┐
     │  Search   │
     │  Index    │
     │(Elastic / │
     │ Typesense)│
     └───────────┘
```

### 14.2 Technology Choices (Recommended)

| Component        | Recommendation                   | Rationale                                                       |
| ---------------- | -------------------------------- | --------------------------------------------------------------- |
| Graph Database   | **Neo4j** (or AWS Neptune)       | Native graph traversal, Cypher query language, mature ecosystem |
| Search Index     | Typesense                        | Full-text search across fragments, entity names, labels         |
| LLM Engine       | **OpenAI GPT-4+                  | Schema-guided extraction, summary generation                    |
| Embedding Store  | **pgvector** or **Pinecone**     | Semantic search for fragment retrieval                          |
| Backend API      | **Python (FastAPI)** or **Go**   | Performance for graph traversal + LLM orchestration             |
| Frontend         | **React + D3.js / Cytoscape.js** | Interactive graph visualization with zoom/pan                   |
| Diagram Renderer | **Mermaid.js**                   | Text-to-diagram from graph data, embeddable                     |
| YAML Definitions | **Git-stored, CI-applied**       | Version-controlled entity/relationship definitions              |
| Event Bus        | **Kafka**                        | Ingestion event pipeline, webhook processing                    |

---

## 15. Success Metrics

| Metric | Target (6 months post-launch) | Measurement |
|---|---|---|
| **Graph coverage** | >80% of production services represented as entities with ≥1 fragment | Entity count vs service registry |
| **Ingestion automation** | >60% of fragments created by LLM (not manually) | `provenance.generated_by` ratio |
| **View usage** | Avg 3+ zoom level changes per session | Session analytics |
| **Cross-team navigation** | >40% of sessions traverse into another team's graph | Navigation path analysis |
| **Documentation freshness** | <15 days average `last_synced` age for active services | Fragment provenance timestamps |
| **User satisfaction** | >4.0/5.0 "Did this view answer your question?" | In-app survey |
| **Duplicate doc reduction** | 30% fewer standalone docs created in Confluence for covered services | Confluence page creation rate |

---

## 16. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **LLM hallucination in extraction** | High | Confidence scoring, human review flags, source hash verification, never overwrite human-entered data |
| **Graph becomes stale** | High | Webhook-driven ingestion on git push, scheduled Confluence/JIRA sync, staleness alerts at 30 days |
| **Adoption resistance** (yet another tool) | Medium | VS Code extension for in-editor views, CLI for CI/CD integration, YAML definitions live in existing repos |
| **Performance at scale** (large graphs) | Medium | Subgraph extraction bounded by radius, lazy fragment loading, caching of topology metrics |
| **Fragment noise** (too many fragments surface) | Medium | Strict ranking algorithm, zoom_min/zoom_max enforcement, tunable lift_by thresholds |
| **Organizational resistance to transparency** | Low | Permissions layer in v2 for sensitive entities; v1 assumes internal openness |

---

## 17. Phased Rollout

### Phase 1: Foundation (Months 1–3)
- Neo4j graph database deployed
- Core entity/relationship/fragment schema implemented
- YAML definition format and `nexdoc apply` CLI
- Basic web UI: graph visualization with zoom, focus, and radius
- Manual fragment creation via UI and YAML

### Phase 2: LLM Ingestion (Months 3–5)
- Git connector: auto-ingest READMEs, docker-compose, k8s manifests
- LLM extraction pipeline with confidence scoring
- Confluence connector: ingest wiki pages as fragments
- Change detection and incremental re-ingestion

### Phase 3: View Engine (Months 5–7)
- Topology analysis (centrality, betweenness, cluster coverage)
- Fragment ranking and lifting algorithm
- LLM-assembled view summaries
- Lens support (product, technical, operations, debug, client, onboarding)
- Navigation path context and fragment boosting

### Phase 4: Ecosystem Integration (Months 7–10)
- JIRA connector (tickets as entities, link to services/teams)
- OpenAPI/Proto spec connector (auto-create API relationship edges)
- VS Code extension (view entity context while coding)
- Backstage catalog import
- View presets and sharing

### Phase 5: Intelligence (Months 10–12)
- Impact analysis: "If service.auth goes down, what is affected?" (graph traversal)
- Drift detection: "README says REST but code shows gRPC" (cross-reference)
- Suggested fragments: "This service has no operations lens coverage — generate runbook?"
- Semantic search across all fragments via embeddings

---

## 18. Open Questions

| # | Question | Options | Decision Needed By |
|---|---|---|---|
| 1 | **Graph database choice**: Neo4j (self-hosted, Cypher) vs Neptune (AWS-managed, Gremlin)? | Neo4j for query expressiveness; Neptune for managed ops | Phase 1 kickoff |
| 2 | **Fragment granularity**: How small should fragments be? Paragraph-level? Section-level? | Start section-level, decompose further based on usage | Phase 2 |
| 3 | **Zoom scale calibration**: Are the 0–100 ranges right, or should zoom be logarithmic? | User testing will calibrate | Phase 3 |
| 4 | **Lift algorithm tuning**: What centrality/coverage thresholds feel right? | A/B test with real users | Phase 3 |
| 5 | **Multi-tenancy**: Should different teams see different "default views" or one unified graph? | Unified graph, saved presets per team | Phase 4 |
| 6 | **Offline/export**: Should rendered views be exportable as static Markdown/PDF? | Yes for sharing with external stakeholders | Phase 4 |

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **Entity** | A node in the graph: a team, person, service, database, topic, etc. |
| **Relationship** | A directed edge between two entities, with type and protocol metadata |
| **DocFragment** | A chunk of documentation anchored to entities/relationships, with zoom and lens coverage |
| **Zoom** | Continuous 0–100 axis representing abstraction depth (0 = company, 100 = code) |
| **Lens** | Perspective filter (product, technical, operations, debug, client, onboarding) |
| **Focus** | The entity at the center of the current view |
| **Radius** | Number of relationship hops from focus included in the viewport |
| **Viewport** | The subgraph visible in the current view (focus + radius + filters) |
| **Topology-aware relevance** | Fragment importance computed from graph structure at render time |
| **Lifting** | Lowering a fragment's effective zoom_min because its subject is structurally significant |
| **ViewPreset** | A saved combination of focus, zoom, lenses, radius, and filters |
| **Provenance** | Metadata about a fragment's origin, confidence, and freshness |

---

## Appendix B: Comparison with Existing Tools

| Capability | Backstage | Confluence | Structurizr (C4) | NexusDocs |
|---|---|---|---|---|
| Service catalog | ✅ | ❌ | Partial | ✅ |
| Team ownership | ✅ | ❌ | ❌ | ✅ |
| Protocol-aware relationships | ❌ | ❌ | Partial | ✅ |
| Multi-zoom documentation | ❌ | ❌ | ✅ (4 levels) | ✅ (continuous 0–100) |
| Multi-lens perspectives | ❌ | ❌ | ❌ | ✅ |
| Topology-aware fragment surfacing | ❌ | ❌ | ❌ | ✅ |
| LLM-powered ingestion | ❌ | ❌ | ❌ | ✅ |
| LLM-powered view assembly | ❌ | ❌ | ❌ | ✅ |
| Graph database backend | ❌ (Postgres) | ❌ | ❌ | ✅ (Neo4j) |
| Code-level entities | ❌ | ❌ | ✅ (Level 4) | ✅ |
| Interactive graph navigation | ❌ | ❌ | Limited | ✅ |
| Fragment polyattachment | N/A | ❌ | ❌ | ✅ |

---

*End of PRD — NexusDocs v1.0*

---

That's the full PRD synthesized from every turn of your Perplexity conversation. The key evolutions it captures:

1. **Depth is not role-bound** — it's a continuous zoom axis like a map (your correction to the role-tagged `depth_tags`)
2. **Fragments attach to multiple nodes** — via direct subjects, tag matching, and graph-edge proximity (the polyattachment problem)
3. **Relevance is topology-computed at read time** — centrality, betweenness, and cluster coverage determine what surfaces (your final and most important insight: the graph votes on what matters, not the fragment author)
4. **Communication protocols are first-class** — Kafka, REST, DB reads/writes are edge metadata, not buried in prose
5. **LLM does the heavy lifting** — ingestion from existing sources AND dynamic assembly of view summaries

Would you like me to create this as a downloadable Confluence page, or break it into JIRA tickets for the phased rollout?