"""Reading required fields out of parsed YAML, and refusing when they are not there.

Three modules here read governed artifacts -- the print overlay, the binding map,
and the contracts -- and each was growing its own copy of the same four guards:
a non-empty string, an integer, a non-empty list, a list of strings. The
duplication mattered for more than tidiness: each copy chose its own wording, so
two artifacts could refuse the same malformed field with messages an adopter
could not tell apart.

Every helper takes the refusal it should raise. The caller knows what the field is
FOR, and a message like "needs a heading_code, so the wording resolves per
language" cannot be assembled from a type name.

`None` is never a return value. A field that is absent, of the wrong type, or
empty raises, because everything read through here is required -- an optional
field is read with a plain `.get` and a stated default at the call site.
"""

from __future__ import annotations

from collections.abc import Mapping

from seshat.report.model import ReportError


def required_text(source: Mapping[str, object], key: str, *, refusal: str) -> str:
    """A non-empty string. An empty string is absence, not a value."""
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ReportError(refusal)
    return value


def required_int(source: Mapping[str, object], key: str, *, refusal: str) -> int:
    """An integer, and never a bool -- ``True`` is an ``int`` in Python, and an
    order of ``True`` would sort as 1 rather than being caught."""
    value = source.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReportError(refusal)
    return value


def required_list(source: Mapping[str, object], key: str, *, refusal: str) -> list:
    """A non-empty list. An empty one declares nothing, which is never intended."""
    value = source.get(key)
    if not isinstance(value, list) or not value:
        raise ReportError(refusal)
    return value


def required_text_list(
    source: Mapping[str, object], key: str, *, refusal: str
) -> tuple[str, ...]:
    """A non-empty list whose every entry is a string."""
    values = required_list(source, key, refusal=refusal)
    if not all(isinstance(value, str) for value in values):
        raise ReportError(refusal)
    return tuple(values)


def required_mapping(value: object, *, refusal: str) -> dict:
    """A value that has to be a mapping before anything reads fields from it."""
    if not isinstance(value, dict):
        raise ReportError(refusal)
    return value
