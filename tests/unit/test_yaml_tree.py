"""The shared YAML walker DL10 and DL11 both read their corpora through.

Extracted when each rule had grown its own recursive dict/list pair. One walker
means one place where the nesting lives -- and one place a traversal bug can hide,
so it is tested directly rather than only through its two callers.
"""

from __future__ import annotations

import pytest

from seshat.rules.yaml_tree import first_value, load, pairs, strings_for, values_for

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
