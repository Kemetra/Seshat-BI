"""The shared field readers three governed-artifact loaders now use.

Each helper's contract is "the value, or a refusal carrying the caller's words" --
never None, and never a coerced substitute for a missing field.
"""

from __future__ import annotations

import pytest

from seshat.report.model import ReportError
from seshat.report.reading import (
    required_int,
    required_list,
    required_mapping,
    required_text,
    required_text_list,
)

pytestmark = pytest.mark.unit

_REFUSAL = "the caller's own wording"


def test_text_returns_the_value() -> None:
    assert required_text({"k": "v"}, "k", refusal=_REFUSAL) == "v"


@pytest.mark.parametrize("source", [{}, {"k": None}, {"k": 7}, {"k": ["v"]}])
def test_an_absent_or_wrongly_typed_text_refuses(source: dict) -> None:
    with pytest.raises(ReportError, match=_REFUSAL):
        required_text(source, "k", refusal=_REFUSAL)


def test_an_empty_string_is_absence_not_a_value() -> None:
    """A heading_code of "" would render an empty heading rather than refusing."""
    with pytest.raises(ReportError, match=_REFUSAL):
        required_text({"k": ""}, "k", refusal=_REFUSAL)


def test_int_returns_the_value() -> None:
    assert required_int({"k": 3}, "k", refusal=_REFUSAL) == 3


def test_zero_is_a_valid_int() -> None:
    assert required_int({"k": 0}, "k", refusal=_REFUSAL) == 0


def test_a_bool_is_not_an_int_here() -> None:
    """True IS an int in Python, so an order of `true` would silently sort as 1."""
    with pytest.raises(ReportError, match=_REFUSAL):
        required_int({"k": True}, "k", refusal=_REFUSAL)


@pytest.mark.parametrize("source", [{}, {"k": "3"}, {"k": 3.5}, {"k": None}])
def test_a_non_int_refuses(source: dict) -> None:
    with pytest.raises(ReportError, match=_REFUSAL):
        required_int(source, "k", refusal=_REFUSAL)


def test_list_returns_the_value() -> None:
    assert required_list({"k": [1, 2]}, "k", refusal=_REFUSAL) == [1, 2]


@pytest.mark.parametrize("source", [{}, {"k": []}, {"k": "ab"}, {"k": {"a": 1}}])
def test_an_absent_empty_or_wrongly_typed_list_refuses(source: dict) -> None:
    """A string is iterable, so without the type check "ab" would read as two items."""
    with pytest.raises(ReportError, match=_REFUSAL):
        required_list(source, "k", refusal=_REFUSAL)


def test_a_text_list_returns_a_tuple() -> None:
    assert required_text_list({"k": ["a", "b"]}, "k", refusal=_REFUSAL) == ("a", "b")


def test_a_list_with_a_non_string_entry_refuses() -> None:
    with pytest.raises(ReportError, match=_REFUSAL):
        required_text_list({"k": ["a", 2]}, "k", refusal=_REFUSAL)


def test_a_mapping_is_returned() -> None:
    assert required_mapping({"a": 1}, refusal=_REFUSAL) == {"a": 1}


@pytest.mark.parametrize("value", [None, [], "text", 3])
def test_a_non_mapping_refuses(value: object) -> None:
    with pytest.raises(ReportError, match=_REFUSAL):
        required_mapping(value, refusal=_REFUSAL)


def test_an_empty_mapping_is_a_mapping() -> None:
    """Emptiness is the caller's business here: a document with no keys still has a
    shape, and each field it needs refuses on its own."""
    assert required_mapping({}, refusal=_REFUSAL) == {}
