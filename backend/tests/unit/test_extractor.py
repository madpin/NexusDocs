"""Tests for the deterministic mock extractor and citation post-validator."""

from nexusdocs.core import Entity, Kind
from nexusdocs.llm import DeterministicMockClient
from nexusdocs.llm.client import (
    AssemblyRequest,
    ExtractionRequest,
    build_default_client,
    filter_citations,
)
from nexusdocs.llm.prompts import load_prompt


def test_extract_entities_finds_services() -> None:
    client = DeterministicMockClient()
    text = "service: payments-api\ndatabase: transactions\n"
    result = client.extract_entities(ExtractionRequest(text=text))
    ids = {e.suggested_id for e in result.entities}
    assert "service.payments-api" in ids
    assert "database.transactions" in ids


def test_extract_relationships_co_mention() -> None:
    client = DeterministicMockClient()
    known = [
        Entity(id="service.payments-api", kind=Kind.service, name="Payments API"),
        Entity(id="service.auth", kind=Kind.service, name="Auth Service"),
    ]
    text = "The Payments API calls the Auth Service to verify tokens."
    out = client.extract_relationships(ExtractionRequest(text=text), known)
    assert len(out.relationships) >= 1


def test_assembly_drops_unknown_citations() -> None:
    client = DeterministicMockClient()
    from nexusdocs.core import (
        Coverage,
        DocFragment,
        Provenance,
        SourceType,
        ViewRequest,
    )
    from nexusdocs.core.enums import GeneratedBy

    fragments = [
        DocFragment(
            id="docfrag.real",
            title="Real",
            body="something",
            tags=["t"],
            coverage=Coverage(zoom_min=0, zoom_max=100, lenses=["technical"]),
            provenance=Provenance(
                source_type=SourceType.manual,
                generated_by=GeneratedBy.human,
                confidence=1.0,
            ),
        )
    ]
    response = client.assemble_view(
        AssemblyRequest(
            request=ViewRequest(focus="service.x", zoom=50, lenses=["technical"]),
            entities=[],
            relationships=[],
            fragments=fragments,
            topology_summary="",
        )
    )
    cleaned, _cited = filter_citations(response.summary, {"docfrag.real"})
    assert "[docfrag.fake]" not in cleaned


def test_default_client_uses_mock_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = build_default_client()
    assert isinstance(client, DeterministicMockClient)


def test_prompt_files_exist() -> None:
    for name in (
        "extract_entities",
        "extract_relationships",
        "extract_fragments",
        "assemble_view",
    ):
        text = load_prompt(name)
        assert text.strip(), f"prompt {name} is empty"
