"""YAML envelope: apiVersion / kind / spec parsing and ordered apply."""

from .apply import ApplyResult, apply_documents
from .envelope import API_VERSION, EnvelopeKind, parse_envelope
from .loader import LoadError, load_documents

__all__ = [
    "API_VERSION",
    "ApplyResult",
    "EnvelopeKind",
    "LoadError",
    "apply_documents",
    "load_documents",
    "parse_envelope",
]
