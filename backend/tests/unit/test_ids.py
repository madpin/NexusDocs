"""Tests for ID validation."""

import pytest

from nexusdocs.core.ids import InvalidIDError, validate_id


@pytest.mark.parametrize(
    "value",
    [
        "service.auth",
        "team.payments",
        "person.tpinto",
        "rel.payments-api-calls-auth",
        "endpoint.auth.verify-session",
        "a",
        "a-b-c",
        "abc.def-ghi.jkl",
    ],
)
def test_valid_ids(value: str) -> None:
    assert validate_id(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1abc",
        "Abc",
        "abc.DEF",
        "abc def",
        "abc/def",
        "abc:def",
        "abc!def",
        ".abc",
        "-abc",
    ],
)
def test_invalid_ids(value: str) -> None:
    with pytest.raises(InvalidIDError):
        validate_id(value)


def test_id_too_long() -> None:
    long = "a" + "b" * 200
    with pytest.raises(InvalidIDError):
        validate_id(long)
