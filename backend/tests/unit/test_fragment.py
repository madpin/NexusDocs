"""Tests for the DocFragment model."""

import pytest
from pydantic import ValidationError

from nexusdocs.core import Coverage, DocFragment, Provenance, SourceType
from nexusdocs.core.enums import GeneratedBy


def _provenance(**overrides) -> Provenance:
    base = dict(
        source_type=SourceType.manual, generated_by=GeneratedBy.human, confidence=1.0
    )
    base.update(overrides)
    return Provenance(**base)


def _coverage(**overrides) -> Coverage:
    base = dict(zoom_min=20, zoom_max=60, lenses=["technical"])
    base.update(overrides)
    return Coverage(**base)


def test_fragment_requires_anchor() -> None:
    with pytest.raises(ValidationError):
        DocFragment(
            id="docfrag.x",
            title="X",
            body="hello",
            coverage=_coverage(),
            provenance=_provenance(),
        )


def test_fragment_zoom_min_le_max() -> None:
    with pytest.raises(ValidationError):
        DocFragment(
            id="docfrag.x",
            title="X",
            body="hello",
            tags=["t"],
            coverage=_coverage(zoom_min=80, zoom_max=20),
            provenance=_provenance(),
        )


def test_fragment_blank_body_rejected() -> None:
    with pytest.raises(ValidationError):
        DocFragment(
            id="docfrag.x",
            title="X",
            body="   ",
            tags=["t"],
            coverage=_coverage(),
            provenance=_provenance(),
        )


def test_fragment_subjects_relations_tags_at_least_one() -> None:
    f = DocFragment(
        id="docfrag.x",
        title="X",
        body="hello",
        tags=["topic"],
        coverage=_coverage(),
        provenance=_provenance(),
    )
    assert f.tags == ["topic"]


def test_human_provenance_must_be_full_confidence() -> None:
    with pytest.raises(ValidationError):
        Provenance(
            source_type=SourceType.manual,
            generated_by=GeneratedBy.human,
            confidence=0.8,
        )


def test_lens_helpers() -> None:
    f = DocFragment(
        id="docfrag.x",
        title="X",
        body="hello",
        tags=["topic"],
        coverage=_coverage(lenses=["technical", "debug"]),
        provenance=_provenance(),
    )
    assert f.has_lens("debug") is True
    assert f.has_lens("onboarding") is False
