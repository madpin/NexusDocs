# NexusDocs Backend

Python implementation of the NexusDocs platform: domain models, YAML loader,
graph repository, view engine, ingestion pipeline, REST API, and `nexdoc` CLI.

## Quick start

```bash
# Create a virtual environment and install
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

# Run tests
pytest

# Apply the sample graph and start the API
nexdoc apply ../examples/payments-sample.yaml
nexdoc serve
```

## Layout

```
src/nexusdocs/
├── core/              # Pydantic v2 domain models
├── yaml/              # apiVersion/kind/spec envelope + apply
├── graph/             # GraphRepository Protocol + memory + neo4j impls
├── view/              # 6-step view engine
├── llm/               # LLMClient Protocol + OpenAI + mock
├── ingestion/         # Connectors + LLM extractor + conflict resolver
├── search/            # SearchIndex Protocol
├── orchestrator/      # Shared API/CLI entry points
├── api/               # FastAPI app
└── cli/               # Typer app (nexdoc)
```

See [`../docs/`](../docs/README.md) for full documentation.
