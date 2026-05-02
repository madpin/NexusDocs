# Framework

> The runtime that turns the graph into views.

**Source of truth:** [PRD §8, §9, §11, §14](../../PRD.md)

---

## What this section covers

This section documents the *machinery* of NexusDocs: how the graph is
ingested, how a view request is resolved, where the LLM fits in, and what
the public API looks like.

| Page                                            | What it covers                                                |
| ----------------------------------------------- | ------------------------------------------------------------- |
| [`view-engine.md`](./view-engine.md)            | View resolution: subgraph → topology → fragments → render.    |
| [`ingestion.md`](./ingestion.md)                | Source connectors, change detection, conflict resolution.     |
| [`llm-integration.md`](./llm-integration.md)    | LLM-powered extraction and view assembly.                     |
| [`api.md`](./api.md)                            | REST API surface.                                             |

---

## High-level architecture

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
     └─────┬─────┘  └────┬────┘  └──────┬──────┘
           │              │              │
           ▼              ▼              ▼
┌───────────────────────────────────────────────────────────────┐
│                      GRAPH DATABASE                           │
│                    (Neo4j / Neptune)                          │
└───────────────────────────────────────────────────────────────┘
           │
     ┌─────▼─────┐
     │  Search   │
     │  Index    │
     └───────────┘
```

Source: [PRD §14.1](../../PRD.md).

---

## Recommended technology choices

From [PRD §14.2](../../PRD.md):

| Component         | Recommendation                  | Rationale                                                       |
| ----------------- | ------------------------------- | --------------------------------------------------------------- |
| Graph database    | Neo4j (or AWS Neptune)          | Native graph traversal, Cypher / Gremlin, mature ecosystem.     |
| Search index      | Typesense                       | Full-text search across fragments, entity names, labels.        |
| LLM engine        | OpenAI GPT-4+                   | Schema-guided extraction, summary generation.                   |
| Embedding store   | pgvector or Pinecone            | Semantic search for fragment retrieval.                         |
| Backend API       | Python (FastAPI) or Go          | Performance for graph traversal + LLM orchestration.            |
| Frontend          | React + D3.js / Cytoscape.js    | Interactive graph visualization with zoom/pan.                  |
| Diagram renderer  | Mermaid.js                      | Text-to-diagram from graph data, embeddable.                    |
| YAML definitions  | Git-stored, CI-applied          | Version-controlled entity/relationship definitions.             |
| Event bus         | Kafka                           | Ingestion event pipeline, webhook processing.                   |

These choices are **recommendations**, not constraints. The platform's
schemas and APIs are technology-agnostic.

---

## Open question: graph database

> **Q1 from [PRD §18](../../PRD.md):** Neo4j (self-hosted, Cypher) vs
> Neptune (AWS-managed, Gremlin)? *Decision needed by Phase 1 kickoff.*

Both options are supported by the platform's abstraction layer. Trade-offs:

| Criterion              | Neo4j                  | Neptune                |
| ---------------------- | ---------------------- | ---------------------- |
| Query language         | Cypher (more readable) | Gremlin (more verbose) |
| Hosting model          | Self-host or Aura SaaS | Fully managed AWS      |
| Vendor lock-in         | Lower                  | Higher                 |
| Operational overhead   | Higher (self-host)     | Lower                  |
| Ecosystem maturity     | Larger                 | Smaller                |

---

## Where to read next

- New to the platform? Start with [`view-engine.md`](./view-engine.md).
- Building a connector? Read [`ingestion.md`](./ingestion.md).
- Calling the API? Read [`api.md`](./api.md).
- Tuning extraction prompts? Read [`llm-integration.md`](./llm-integration.md).
