"""ID validation. See docs/schemas/README.md#id.

The canonical pattern in the docs is `^[a-z][a-z0-9.-]*$`, but throughout
the example graphs and entity docs underscores appear in IDs that embed a
kind name (e.g. `kafka_cluster.core-kafka-prod`). We accept underscores in
addition to the documented set so that the example fixtures parse.
"""

import re

ID_PATTERN = re.compile(r"^[a-z][a-z0-9._\-]*$")
ID_MAX_LENGTH = 200


class InvalidIDError(ValueError):
    """Raised when an ID does not conform to the ID format."""


def validate_id(value: str) -> str:
    """Validate an ID string. Returns the value if valid, raises InvalidIDError otherwise."""
    if not isinstance(value, str):
        raise InvalidIDError(f"ID must be a string, got {type(value).__name__}")
    if len(value) == 0:
        raise InvalidIDError("ID cannot be empty")
    if len(value) > ID_MAX_LENGTH:
        raise InvalidIDError(f"ID exceeds {ID_MAX_LENGTH} characters: {value!r}")
    if not ID_PATTERN.match(value):
        raise InvalidIDError(
            f"ID {value!r} does not match pattern {ID_PATTERN.pattern}: "
            "lowercase, must start with a letter, allow [a-z0-9._-]"
        )
    return value
