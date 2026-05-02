"""Multi-document YAML loader."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..core import DocFragment, Entity, Relationship, ViewPreset
from .envelope import EnvelopeError, EnvelopeKind, parse_envelope


class LoadError(ValueError):
    """Raised when a YAML file cannot be parsed or validated."""


@dataclass
class LoadedDocuments:
    """Result of loading one or more YAML documents."""

    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    fragments: list[DocFragment] = field(default_factory=list)
    presets: list[ViewPreset] = field(default_factory=list)

    def __len__(self) -> int:
        return (
            len(self.entities)
            + len(self.relationships)
            + len(self.fragments)
            + len(self.presets)
        )


def load_documents(source: str | Path | Iterable[dict[str, Any]]) -> LoadedDocuments:
    """Load YAML documents from text, a file path, or an iterable of dicts."""
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
        docs_iter = yaml.safe_load_all(text)
    elif isinstance(source, str):
        # If the string looks like it could be a file path (no newlines and short
        # enough), try resolving it. Otherwise treat it as raw YAML content.
        # Path probing on multi-line / very long strings throws OSError.
        text = source
        if "\n" not in source and len(source) < 4096:
            try:
                path = Path(source)
                if path.exists() and path.is_file():
                    text = path.read_text(encoding="utf-8")
            except OSError:
                pass
        docs_iter = yaml.safe_load_all(text)
    else:
        docs_iter = source

    out = LoadedDocuments()
    errors: list[str] = []

    for idx, raw in enumerate(docs_iter):
        if raw is None:
            continue
        try:
            kind, model = parse_envelope(raw)
        except EnvelopeError as e:
            errors.append(f"document #{idx}: {e}")
            continue

        if kind == EnvelopeKind.Entity:
            out.entities.append(model)
        elif kind == EnvelopeKind.Relationship:
            out.relationships.append(model)
        elif kind == EnvelopeKind.DocFragment:
            out.fragments.append(model)
        elif kind == EnvelopeKind.ViewPreset:
            out.presets.append(model)

    if errors:
        raise LoadError("YAML load failed:\n" + "\n".join(errors))
    return out
