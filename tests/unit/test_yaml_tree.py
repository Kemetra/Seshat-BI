"""The shared YAML walker DL10 and DL11 both read their corpora through.

Extracted when each rule had grown its own recursive dict/list pair. One walker
means one place where the nesting lives -- and one place a traversal bug can hide,
so it is tested directly rather than only through its two callers.
"""

from __future__ import annotations

import pytest

from seshat.rules.yaml_tree import (
    first_value,
    load,
    pairs,
    read,
    strings_for,
    values_for,
)

_TREE = {
    "profiles": {
        "desktop": {"zones": {"header": 1, "footer_status": 2}},
        "bands": [{"band": "header"}, {"band": " kpi_strip "}, "bare_string"],
    },
    "section": "top_level",
}


@pytest.mark.unit
def test_pairs_reaches_keys_nested_in_mappings_and_lists():
    keys = {key for key, _ in pairs(_TREE)}

    assert {"profiles", "desktop", "zones", "header", "bands", "band"} <= keys


@pytest.mark.unit
def test_first_value_finds_a_declaration_inside_a_named_profile():
    """The grids nest `zones` under a profile, so root-only lookup would miss it."""
    assert first_value(_TREE, "zones") == {"header": 1, "footer_status": 2}


@pytest.mark.unit
def test_first_value_is_none_for_an_absent_key():
    assert first_value(_TREE, "no_such_key") is None


@pytest.mark.unit
def test_strings_for_strips_and_drops_non_strings():
    assert set(strings_for(_TREE, "band")) == {"header", "kpi_strip"}


@pytest.mark.unit
def test_strings_for_collects_one_key_across_depths():
    assert set(strings_for(_TREE, "section")) == {"top_level"}


@pytest.mark.unit
def test_values_for_keeps_non_string_values():
    assert set(values_for(_TREE, "header")) == {1}


@pytest.mark.unit
@pytest.mark.parametrize("node", [None, "scalar", 7, [], {}])
def test_walking_a_degenerate_node_yields_nothing(node):
    """A rule loading an empty or scalar document must not crash."""
    assert list(pairs(node)) == []
    assert first_value(node, "anything") is None


@pytest.mark.unit
def test_load_returns_none_for_an_unreadable_or_invalid_file(tmp_path):
    """Fail-soft: a rule reports nothing for a bad file rather than crashing."""
    missing = tmp_path / "absent.yaml"
    broken = tmp_path / "broken.yaml"
    broken.write_text("key: [unclosed\n", encoding="utf-8")

    assert load(missing) is None
    assert load(broken) is None


@pytest.mark.unit
def test_load_reads_a_utf8_bom_file(tmp_path):
    """PBIP-adjacent YAML is sometimes written with a BOM."""
    path = tmp_path / "bom.yaml"
    path.write_text("zones:\n  header: 1\n", encoding="utf-8-sig")

    assert load(path) == {"zones": {"header": 1}}


@pytest.mark.unit
def test_a_malformed_document_reports_a_parse_failure_rather_than_an_empty_tree(
    tmp_path,
):
    """Fails while `load` swallows a YAMLError and returns None.

    A rule that cannot parse a file must not behave as though the file contained no
    relevant keys: that turns an UNEXAMINED file into a clean result while the
    coverage census still reports the rule as evaluated. The parse status has to be
    distinguishable from a legitimately empty document.
    """
    bad = tmp_path / "malformed.yaml"
    bad.write_text("this: [is: not: valid: yaml\n  ][\n", encoding="utf-8")

    assert read(bad).failed is True


@pytest.mark.unit
def test_an_unreadable_path_reports_a_parse_failure(tmp_path):
    """A missing file is a failure to read, not an empty document."""
    assert read(tmp_path / "absent.yaml").failed is True


@pytest.mark.unit
def test_a_legitimately_empty_document_is_not_a_parse_failure(tmp_path):
    """The distinction that matters: empty is clean, malformed is not."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")

    result = read(empty)

    assert result.failed is False
    assert result.data is None


@pytest.mark.unit
def test_a_valid_document_round_trips_through_read(tmp_path):
    good = tmp_path / "good.yaml"
    good.write_text("a:\n  b: 1\n", encoding="utf-8")

    result = read(good)

    assert result.failed is False
    assert result.data == {"a": {"b": 1}}


@pytest.mark.unit
def test_invalid_utf8_is_a_parse_failure_not_a_crash(tmp_path):
    """Fails while `UnicodeDecodeError` escapes `read`.

    It is neither `OSError` nor `YAMLError`, so one invalid byte in one tracked file
    aborted the entire check run rather than producing the finding this fail-soft
    path exists to produce. Written as bytes because no text encoding can express it.
    """
    bad = tmp_path / "invalid-utf8.yaml"
    bad.write_bytes(b"section: \xff\xfe not utf-8 \x80\n")

    assert read(bad).failed is True
