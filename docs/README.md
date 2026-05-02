# NexusDocs Documentation

> Topology-aware knowledge graph documentation platform.
> One source of truth, infinite views.

This directory contains the working documentation for **NexusDocs** itself —
written following the platform's own principle: **everything is documentable**.

Every entity type, relationship type, protocol, schema, and framework concept
described here is something that NexusDocs models, ingests, fragments, and
renders. The docs are organized as the platform organizes the world: by
**topics**, **entities**, **relations**, and the **framework** that ties them
together.

---

## How to read these docs

There are several entry points depending on what you need:

| If you want to...                                            | Start here                                      |
| ------------------------------------------------------------ | ----------------------------------------------- |
| Understand the mental model (graph, zoom, lenses, topology) | [`concepts/`](./concepts/README.md)             |
| Look up an entity type (Service, KafkaTopic, Person, …)     | [`entities/`](./entities/README.md)             |
| Look up a relationship type (`publishes_to`, `calls_api`, …) | [`relationships/`](./relationships/README.md)   |
| Author a YAML definition or write to the API                 | [`schemas/`](./schemas/README.md)               |
| Understand the runtime (view engine, ingestion, LLM, API)    | [`framework/`](./framework/README.md)           |
| See worked examples and end-to-end flows                     | [`examples/`](./examples/README.md)             |
| Read the source PRD                                          | [`../PRD.md`](../PRD.md)                        |

---

## Documentation structure

```
docs/
├── README.md                        # This file
│
├── concepts/                        # The mental model
│   ├── README.md                    # Concept index
│   ├── graph-model.md               # Nodes, edges, property graph
│   ├── zoom-axis.md                 # The 0–100 zoom axis
│   ├── lenses.md                    # Perspective filters
│   ├── topology.md                  # Centrality, lifting, relevance
│   └── navigation.md                # Focus, radius, viewport, path
│
├── entities/                        # What can be a node
│   ├── README.md                    # Entity taxonomy
│   ├── organizational.md            # Company, Division, Tribe, Team, Person
│   ├── technical.md                 # System, Service, Component, Class, Function
│   ├── infrastructure.md            # Database, Kafka*, APIGateway, Queue, Cache
│   └── documentation.md             # Document, DocFragment
│
├── relationships/                   # What can be an edge
│   ├── README.md                    # Relationship taxonomy
│   ├── organizational.md            # belongs_to, owns, leads, member_of, reports_to
│   ├── technical.md                 # depends_on, calls_api, provides_api, extends, implements
│   ├── data-flow.md                 # publishes_to, consumes_from, reads_from, writes_to, streams_to
│   ├── documentation.md             # describes, references, supersedes
│   └── protocols.md                 # REST, Kafka, gRPC, GraphQL, SQL, etc.
│
├── schemas/                         # Format reference
│   ├── README.md                    # Schema overview
│   ├── entity.md                    # Entity schema
│   ├── relationship.md              # Relationship schema
│   ├── doc-fragment.md              # DocFragment schema
│   ├── view-preset.md               # ViewPreset schema
│   └── yaml-format.md               # apiVersion / kind / spec convention
│
├── framework/                       # The runtime
│   ├── README.md                    # Architecture overview
│   ├── view-engine.md               # Subgraph → topology → fragments → render
│   ├── ingestion.md                 # Source connectors, change detection
│   ├── llm-integration.md           # Extraction + assembly pipelines
│   └── api.md                       # REST surface
│
└── examples/                        # Worked examples
    ├── README.md                    # Example index
    └── sample-graph.md              # End-to-end YAML graph example
```

---

## The core idea, in one paragraph

NexusDocs models an organization's people, teams, systems, infrastructure, and
documentation as a single property graph. **Entities** (nodes) and
**relationships** (edges) are first-class. Documentation lives as
**DocFragments** anchored to entities and edges, each tagged with a **zoom
range** and one or more **lenses**. At read time, the **view engine** extracts
a subgraph around the reader's **focus**, analyzes its **topology**, picks the
fragments whose zoom and lens match the reader's request — **lifting** any
whose subjects are structurally significant — and asks an LLM to assemble the
result into a cohesive narrative with a diagram. Same graph, infinite views.

---

## Documentation principles

These docs themselves follow the platform's principles:

1. **Every type is documentable.** Each entity kind, relationship type, and
   framework concept gets its own document, identified, and cross-referenced.
2. **Topology over taxonomy.** Files are grouped by how they relate, not by
   alphabetical order or arbitrary categories.
3. **Schemas live next to prose.** Every doc that introduces a type embeds the
   YAML schema and a worked example.
4. **Zoom is explicit.** Each doc indicates the zoom levels and lenses where
   its subject typically surfaces in views.
5. **Provenance is honored.** Anything sourced from the PRD links back to the
   PRD section.

---

## Authoring conventions

When adding a new doc, follow this template:

```markdown
# <Subject>

> One-line tagline.

**Identifier prefix:** `kind.` or `rel.` or `topic.` (where applicable)
**Source of truth:** [PRD §X.Y](../../PRD.md)
**Default zoom:** N–M
**Default lenses:** [...]

## Definition
<What it is, one paragraph.>

## Schema
<Embedded YAML schema or reference to schemas/.>

## Examples
<At least one runnable YAML example.>

## Relationships
<Which other entities/edges typically connect.>

## Documentation patterns
<What fragments typically anchor here, at which zooms, in which lenses.>
```

---

*Source: [PRD v1.0 Draft](../PRD.md), 2 May 2026, Thiago M Pinto.*
