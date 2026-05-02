"""Tests for the ranking step."""

from nexusdocs.core import (
    Coverage,
    DocFragment,
    Provenance,
    SourceType,
    ViewRequest,
)
from nexusdocs.core.enums import GeneratedBy
from nexusdocs.view.lifting import FilteredFragment
from nexusdocs.view.ranking import rank


def _ff(
    fid: str,
    zoom_min: int,
    zoom_max: int,
    lenses: list[str],
    confidence: float = 0.9,
    reviewed: bool = True,
) -> FilteredFragment:
    f = DocFragment(
        id=fid,
        title=fid,
        body="x",
        tags=["t"],
        coverage=Coverage(zoom_min=zoom_min, zoom_max=zoom_max, lenses=lenses),
        provenance=Provenance(
            source_type=SourceType.manual,
            generated_by=GeneratedBy.human if confidence == 1.0 else GeneratedBy.llm,
            confidence=confidence,
            reviewed=reviewed,
        ),
    )
    return FilteredFragment(fragment=f, effective_zoom_min=zoom_min, lifted=False)


def test_zoom_proximity_dominates() -> None:
    request = ViewRequest(focus="service.x", zoom=50, lenses=["technical"])
    near = _ff("docfrag.near", 40, 60, ["technical"])
    far = _ff("docfrag.far", 10, 30, ["technical"])
    out = rank([far, near], request)
    assert out[0].fragment.id == "docfrag.near"


def test_lens_specificity_breaks_tie() -> None:
    request = ViewRequest(focus="service.x", zoom=50, lenses=["debug"])
    specific = _ff("docfrag.spec", 30, 70, ["debug"])  # 1 lens, 1 overlap = 1.0
    broad = _ff("docfrag.broad", 30, 70, ["debug", "technical", "operations"])
    out = rank([broad, specific], request)
    assert out[0].fragment.id == "docfrag.spec"


def test_dedup_keeps_lowest_zoom_min() -> None:
    request = ViewRequest(focus="service.x", zoom=50, lenses=["technical"])
    low = _ff("docfrag.same", 30, 70, ["technical"])
    high = _ff("docfrag.same", 60, 80, ["technical"])
    out = rank([high, low], request)
    assert len(out) == 1
    assert out[0].effective_zoom_min == 30
