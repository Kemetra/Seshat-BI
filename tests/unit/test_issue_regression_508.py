"""Regression tests for issue #508 (HR1/HR13 read-parity + a dead fallback).

Issue #508 reported two nits deferred out of #499 (PR #505). Investigating them
CORRECTED one premise and found the real defect underneath it:

1. The report says a BOM-prefixed ``source-map.yaml`` "is readable by one and not
   the other" because HR1 read with ``utf-8`` and HR13 with ``utf-8-sig``. That is
   NOT so: PyYAML's ``Reader`` strips a leading U+FEFF itself, so a BOM'd map
   parses to the IDENTICAL dict under either encoding.
   ``test_a_bom_prefixed_source_map_parses_identically_under_both_encodings``
   pins that, so nobody re-derives the false premise from the issue text.

   The genuine asymmetry was the EXCEPTION TUPLE guarding the same read. HR13
   caught ``UnicodeDecodeError`` (a ``ValueError``, NOT an ``OSError``); HR1 did
   not. On a map carrying one undecodable byte, HR13 degraded to ``None`` while
   HR1 raised -- and ``runner.run`` invokes ``registered.rule(ctx)`` unguarded, so
   that exception escaped and took the WHOLE ``retail check`` run down, reporting
   no findings at all. Two governance rules reading the same file disagreed about
   whether it was parseable, which is exactly the defect #508 names -- just the
   half with teeth. That is what the parity tests below fail on pre-fix.

2. ``_attr_type_divergence``'s ``dim_bare = _bare(dim.get("name")) or bare`` had an
   unreachable ``or bare`` arm. Every dim reaching that loop is indexed via
   ``star_dimensions`` -> ``_add_dim``, which drops any dim whose
   ``bare_dim_name(name)`` is falsy BEFORE it can be indexed. The arm is deleted;
   ``bare`` became an unused parameter of ``_attr_type_divergence`` and
   ``_conformed_divergence`` and was dropped from both.

   The durable guard is NOT a test of the deleted branch -- it is a pin on the
   BOUNDARY FILTER that makes it dead. If someone later loosens ``_add_dim``, the
   boundary tests below fail and point straight at the invariant HR1's loop rests
   on.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext

pytestmark = pytest.mark.unit

_MAP_REL = "mappings/s1/source-map.yaml"
_DECL_REL = "docs/quality/conformed-dimension-map.yaml"

_MAP_BODY = (
    "source_id: s1\n"
    "gold_star:\n"
    "  fact: gold.fct_s1\n"
    "  dimensions:\n"
    "    - name: gold.dim_a\n"
    "      surrogate_key: a_sk\n"
    "columns:\n"
    "  - source_column: item\n"
    "    silver_type: text\n"
    "    gold_placement: dim:dim_a.item\n"
)


def _ctx(tmp_path: Path, raw: bytes) -> RuleContext:
    """A one-map context whose source-map holds exactly ``raw`` bytes."""
    dest = tmp_path / _MAP_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return RuleContext(repo_root=tmp_path, tracked_files=(_MAP_REL,))


def _both_loaders():
    """HR1's and HR13's private ``_load_yaml``, which must agree on every input."""
    from seshat.rules.conformed_dimension import _load_yaml as hr1_load
    from seshat.rules.placement_resolution import _load_yaml as hr13_load

    return hr1_load, hr13_load


# --------------------------------------------------------------------------- #
# 1. read parity between HR1 and HR13 on the SAME source-map                   #
# --------------------------------------------------------------------------- #


def test_an_undecodable_byte_degrades_both_rules_identically(tmp_path: Path) -> None:
    """The real #508 defect: HR1 raised where HR13 returned None.

    FAILS PRE-FIX -- HR1's tuple omitted ``UnicodeDecodeError`` and the read raised.
    """
    ctx = _ctx(tmp_path, _MAP_BODY.encode("utf-8") + b"comment: \xff\xfe\n")
    hr1_load, hr13_load = _both_loaders()

    assert hr1_load(ctx, _MAP_REL) is None
    assert hr13_load(ctx, _MAP_REL) == hr1_load(ctx, _MAP_REL)


def test_an_undecodable_byte_never_escapes_hr1_through_the_runner(
    tmp_path: Path,
) -> None:
    """``runner.run`` calls ``registered.rule(ctx)`` UNGUARDED (runner.py:128).

    So a rule that raises does not merely fail itself -- it aborts the entire
    ``retail check`` run and reports nothing. A governance rule degrades on an
    unreadable artifact; it never takes the gate down.

    FAILS PRE-FIX with ``UnicodeDecodeError`` escaping ``check_hr1``.
    """
    from seshat.rules.conformed_dimension import check_hr1
    from seshat.rules.placement_resolution import check_hr13

    ctx = _ctx(tmp_path, _MAP_BODY.encode("utf-8") + b"comment: \xff\n")

    assert list(check_hr1(ctx)) == []
    assert list(check_hr13(ctx)) == []


def test_a_bom_prefixed_source_map_parses_identically_under_both_encodings(
    tmp_path: Path,
) -> None:
    """PIN, not a regression test: #508's BOM premise is incorrect.

    PyYAML's ``Reader`` strips a leading U+FEFF, so a BOM'd map parses to the same
    dict whether the bytes were decoded with ``utf-8`` or ``utf-8-sig``. This
    PASSES pre-fix and post-fix; it exists so the false premise is not re-derived
    from the issue text, and so a future "optimisation" back to bare ``utf-8``
    still has to keep the two rules in agreement.
    """
    import yaml

    from seshat import star_discovery

    ctx = _ctx(tmp_path, b"\xef\xbb\xbf" + _MAP_BODY.encode("utf-8"))
    hr1_load, hr13_load = _both_loaders()

    parsed = hr1_load(ctx, _MAP_REL)
    assert parsed == hr13_load(ctx, _MAP_REL)
    # the BOM did not corrupt the first key, so the map is still seen as a star
    assert parsed is not None
    assert star_discovery.is_star(parsed)
    assert sorted(star_discovery.star_dimensions(parsed)) == ["dim_a"]
    # ...and the encoding literal is not what saves it -- PyYAML is
    assert yaml.safe_load("\ufeffsource_id: s1\n") == {"source_id": "s1"}


# --------------------------------------------------------------------------- #
# 2. the boundary filter that makes the deleted `or bare` arm unreachable      #
# --------------------------------------------------------------------------- #

# Every falsy-bare shape a dimension `name` can take. `bare_dim_name` returns None
# for absent/blank/non-str and "" for a schema-only name like "gold." -- `_add_dim`
# guards on truthiness (`if not b`), so BOTH kinds are dropped.
_FALSY_BARE_NAMES: tuple[object, ...] = (
    None,  # explicit null
    "",  # empty
    "   ",  # whitespace only
    ".",  # bare delimiter -> ""
    "gold.",  # schema-only -> ""
    123,  # non-str
    True,  # non-str (and not a name)
)


@pytest.mark.parametrize("name", _FALSY_BARE_NAMES)
@pytest.mark.parametrize("slot", ["dimensions", "date_dimension"])
def test_a_falsy_bare_dimension_name_is_dropped_at_the_boundary(
    slot: str, name: object
) -> None:
    """``star_dimensions`` never yields a dim whose bare name is falsy.

    Both indexed slots are covered: an explicit ``dimensions[]`` entry and the
    standalone ``date_dimension``. This is the invariant HR1's
    ``_attr_type_divergence`` loop relies on after the ``or bare`` arm was deleted.
    """
    from seshat.star_discovery import star_dimensions

    dim = {"name": name, "surrogate_key": "x_sk"}
    gold_star: dict = {"fact": "gold.fct_s1"}
    gold_star[slot] = [dim] if slot == "dimensions" else dim

    assert star_dimensions({"gold_star": gold_star}) == {}


def test_a_dimension_missing_the_name_key_entirely_is_dropped() -> None:
    """The absent-key case, distinct from an explicit falsy value."""
    from seshat.star_discovery import star_dimensions

    document = {
        "gold_star": {
            "fact": "gold.fct_s1",
            "dimensions": [{"surrogate_key": "x_sk"}],
            "date_dimension": {"surrogate_key": "d_sk"},
        }
    }
    assert star_dimensions(document) == {}


def test_every_dim_hr1_indexes_has_a_truthy_bare_name_equal_to_its_key() -> None:
    """The exact precondition the deleted ``or bare`` arm pretended to handle.

    Across every combination of falsy-bare and valid names in BOTH slots, each
    ``(bare, star)`` pair HR1 iterates carries a dim whose ``bare_dim_name`` is
    truthy AND equal to the key it was indexed under -- so ``_bare(...) or bare``
    could never take its right-hand arm, and would have been a no-op if it had.
    """
    import itertools

    from seshat.rules.conformed_dimension import _index_dims_by_name
    from seshat.star_discovery import bare_dim_name

    names = (*_FALSY_BARE_NAMES, "gold.dim_a", "DIM_A", " gold.dim_b ", "a.b.dim_c")
    stars = {
        f"star{i}": {
            "gold_star": {
                "fact": "gold.fct",
                "dimensions": [{"name": n1}],
                "date_dimension": {"name": n2},
            }
        }
        for i, (n1, n2) in enumerate(itertools.product(names, repeat=2))
    }

    indexed = _index_dims_by_name(stars)
    assert indexed, "the valid names must produce SOME index, or this proves nothing"
    for bare, star_map in indexed.items():
        assert bare, "a falsy bare name must never become an index key"
        for dim, _data in star_map.values():
            assert bare_dim_name(dim.get("name")) == bare


def test_conformed_divergence_helpers_take_no_bare_argument() -> None:
    """``bare`` was threaded through only to feed the dead fallback.

    Pins the narrowed signatures so the parameter is not reinstated (an unused
    parameter is the same trap as the dead branch, one level up).
    """
    import inspect

    from seshat.rules.conformed_dimension import (
        _attr_type_divergence,
        _conformed_divergence,
    )

    assert list(inspect.signature(_attr_type_divergence).parameters) == ["stars"]
    assert list(inspect.signature(_conformed_divergence).parameters) == ["stars"]
