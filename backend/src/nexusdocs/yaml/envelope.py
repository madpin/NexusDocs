"""apiVersion / kind / spec envelope parsing."""

from enum import StrEnum
from typing import Any

from ..core import DocFragment, Entity, Relationship, ViewPreset

API_VERSION = "nexusdocs/v1"


class EnvelopeKind(StrEnum):
    Entity = "Entity"
    Relationship = "Relationship"
    DocFragment = "DocFragment"
    ViewPreset = "ViewPreset"


_MODEL_FOR: dict[EnvelopeKind, type] = {
    EnvelopeKind.Entity: Entity,
    EnvelopeKind.Relationship: Relationship,
    EnvelopeKind.DocFragment: DocFragment,
    EnvelopeKind.ViewPreset: ViewPreset,
}


class EnvelopeError(ValueError):
    """Raised when a YAML document does not conform to the envelope."""


def parse_envelope(doc: dict[str, Any]) -> tuple[EnvelopeKind, Any]:
    """Validate a YAML document's envelope and return (kind, parsed model).

    Accepts both `type` and `kind` inside `spec` for entities, mapping `type` to `kind`.
    """
    if not isinstance(doc, dict):
        raise EnvelopeError(f"YAML document must be a mapping, got {type(doc).__name__}")

    api_version = doc.get("apiVersion")
    if api_version != API_VERSION:
        raise EnvelopeError(
            f"unsupported apiVersion {api_version!r}; expected {API_VERSION!r}"
        )

    kind_str = doc.get("kind")
    if kind_str is None:
        raise EnvelopeError("missing required field 'kind' in envelope")
    try:
        kind = EnvelopeKind(kind_str)
    except ValueError as e:
        raise EnvelopeError(
            f"unknown kind {kind_str!r}; expected one of: {[k.value for k in EnvelopeKind]}"
        ) from e

    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise EnvelopeError("envelope 'spec' must be a mapping")

    spec = dict(spec)
    if kind == EnvelopeKind.Entity and "type" in spec:
        spec.setdefault("kind", spec.pop("type"))
    elif kind == EnvelopeKind.Entity and "type" not in spec and "kind" not in spec:
        raise EnvelopeError("entity spec must include 'type' (preferred) or 'kind'")

    model_cls = _MODEL_FOR[kind]
    try:
        instance = model_cls.model_validate(spec)
    except Exception as e:
        raise EnvelopeError(f"failed to validate {kind.value} spec: {e}") from e

    return kind, instance
