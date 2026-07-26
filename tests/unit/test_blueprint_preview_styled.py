"""Unit tests for the Blueprint Preview's three-way input state split (task 5).

`_load_yaml_mapping` (`src/seshat/blueprint_preview.py`) must never conflate
ABSENT (a not-yet-authored artifact -- non-fatal, returns ``{}``) with
UNREADABLE / MALFORMED YAML / WRONG-SHAPE (a corrupt or misshapen artifact --
must raise ``PreviewInputError`` naming the file, never silently render as an
empty-but-valid-looking preview).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.blueprint_preview import PreviewInputError, _load_yaml_mapping

pytestmark = pytest.mark.unit


def test_absent_input_is_not_an_error(tmp_path: Path) -> None:
    """A not-yet-authored page is a real use case -- stays non-fatal."""
    assert _load_yaml_mapping(tmp_path / "missing.yaml") == {}


def test_empty_input_is_not_an_error(tmp_path: Path) -> None:
    """A file that exists but parses to ``None`` (fully empty/whitespace-only)
    is the same non-fatal case as absent, not a malformed-input error."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    assert _load_yaml_mapping(empty) == {}


def test_unparseable_input_is_reported(tmp_path: Path) -> None:
    """A corrupt file must NOT silently become an empty preview."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("pages: [unclosed\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="bad.yaml"):
        _load_yaml_mapping(bad)


def test_non_mapping_input_is_reported(tmp_path: Path) -> None:
    """A YAML list parses fine but is the wrong shape -- name it."""
    listy = tmp_path / "listy.yaml"
    listy.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(PreviewInputError, match="mapping"):
        _load_yaml_mapping(listy)


def test_undecodable_bytes_are_reported(tmp_path: Path) -> None:
    """An unreadable (undecodable-as-utf-8-sig) file is the UNREADABLE state,
    distinct from malformed-YAML-but-decodable -- both must raise, but this
    exercises the ``UnicodeDecodeError`` branch specifically, triggered
    portably (no chmod/permissions needed) via a byte sequence that is
    invalid UTF-8."""
    undecodable = tmp_path / "undecodable.yaml"
    raw = b"pages:\n  - \xff\xfe not valid utf-8\n"
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8-sig")  # confirm the fixture actually triggers this branch
    undecodable.write_bytes(raw)
    with pytest.raises(PreviewInputError, match="undecodable.yaml"):
        _load_yaml_mapping(undecodable)
