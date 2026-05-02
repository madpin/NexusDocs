"""Tests for the citation post-validator."""

from nexusdocs.llm.client import filter_citations


def test_filter_unknown_citations() -> None:
    text = "First [docfrag.real] then [docfrag.fake]."
    cleaned, cited = filter_citations(text, allowed_ids={"docfrag.real"})
    assert "[docfrag.fake]" not in cleaned
    assert cited == ["docfrag.real"]


def test_keeps_known_citations() -> None:
    text = "See [docfrag.a] and [docfrag.b]."
    cleaned, cited = filter_citations(text, allowed_ids={"docfrag.a", "docfrag.b"})
    assert "[docfrag.a]" in cleaned
    assert "[docfrag.b]" in cleaned
    assert cited == ["docfrag.a", "docfrag.b"]


def test_collapses_no_citations() -> None:
    text = "Plain text."
    cleaned, cited = filter_citations(text, allowed_ids=set())
    assert cleaned == "Plain text."
    assert cited == []
