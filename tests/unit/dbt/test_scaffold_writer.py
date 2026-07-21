"""Writer merges: union new tables into shared source/selector files, fail closed.

Covers the two writer defects the shared ``_sources.yml`` / ``selectors.yml``
merges must not have: (1) a second onboarded table must have its tables UNIONED
into the existing ``bronze`` / ``migration_gold`` groups, not skipped because the
group name already exists; (2) a malformed existing file must fail closed, never
be clobbered with only the new rows (destroying other tables' entries).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from seshat.dbt.contracts import FactBinding
from seshat.dbt.scaffold import model_plan, writer
from seshat.safe_write import SafeWriteError

pytestmark = pytest.mark.unit

SOURCES = "dbt/models/sources/_sources.yml"
SELECTORS = "dbt/selectors.yml"


def _plan(table_id: str) -> model_plan.ScaffoldPlan:
    document = {
        "meta": {"table_id": table_id, "grain": "one row"},
        "columns": [
            {"source_name": "k", "decision": "keep", "rename_to": "k"},
            {"source_name": "m", "decision": "keep", "rename_to": "m"},
        ],
        "gold_star": {
            "fact": {
                "name": f"gold.fct_{table_id}",
                "business_key": "k",
                "measures": ["m"],
                "additive_money_measures": ["m"],
            },
            "dimensions": [
                {
                    "name": f"gold.dim_{table_id}",
                    "surrogate_key": "k_sk",
                    "attributes": ["k"],
                },
            ],
        },
    }
    fact = FactBinding(
        name=f"fct_{table_id}", business_key=("k",), additive_money_measures=("m",)
    )
    source = model_plan.MapSource(
        document=document,
        source_map=f"mappings/{table_id}/source-map.yaml",
        source_map_revision="a" * 40,
    )
    return model_plan.build_scaffold_plan(source, table_id, fact)


def _read(root: Path, relative: str) -> dict:
    return yaml.safe_load((root / relative).read_text(encoding="utf-8"))


def test_second_table_is_unioned_into_existing_source_groups(tmp_path: Path) -> None:
    plan_a = _plan("table_a")
    writer.merge_sources(tmp_path, plan_a)
    plan_b = _plan("table_b")

    changed = writer.merge_sources(tmp_path, plan_b)

    assert changed is True
    by_name = {s["name"]: s for s in _read(tmp_path, SOURCES)["sources"]}
    bronze_tables = {t["name"] for t in by_name["bronze"]["tables"]}
    gold_tables = {t["name"] for t in by_name["migration_gold"]["tables"]}
    assert bronze_tables == {"table_a", "table_b"}
    assert {"fct_table_a", "fct_table_b", "dim_table_a", "dim_table_b"} <= gold_tables


def test_re_merging_the_same_table_is_idempotent(tmp_path: Path) -> None:
    plan_a = _plan("table_a")
    writer.merge_sources(tmp_path, plan_a)

    assert writer.merge_sources(tmp_path, plan_a) is False


def test_second_selector_is_appended_not_replaced(tmp_path: Path) -> None:
    writer.merge_selector(tmp_path, "seshat_table_a")
    writer.merge_selector(tmp_path, "seshat_table_b")

    names = {s["name"] for s in _read(tmp_path, SELECTORS)["selectors"]}
    assert names == {"seshat_table_a", "seshat_table_b"}


def test_malformed_sources_fails_closed_without_clobbering(tmp_path: Path) -> None:
    path = tmp_path / SOURCES
    path.parent.mkdir(parents=True)
    original = "sources: [ this is : not valid yaml\n"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(model_plan.ScaffoldError, match="valid YAML"):
        writer.merge_sources(tmp_path, _plan("table_b"))
    # The malformed file is untouched -- NOT rewritten with only table_b's rows.
    assert path.read_text(encoding="utf-8") == original


def test_malformed_selectors_fails_closed_without_clobbering(tmp_path: Path) -> None:
    path = tmp_path / SELECTORS
    path.parent.mkdir(parents=True)
    original = "selectors: [ : broken\n"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(model_plan.ScaffoldError, match="valid YAML"):
        writer.merge_selector(tmp_path, "seshat_table_b")
    assert path.read_text(encoding="utf-8") == original


def test_selectors_wrong_type_fails_closed_without_clobbering(tmp_path: Path) -> None:
    """A `selectors:` that parses as valid YAML but is a MAPPING/scalar/null (not a
    list) must fail closed -- silently coercing to [] would rewrite the file and
    drop its existing content (#406 review). Covers the valid-YAML-wrong-shape gap
    the malformed-YAML test above does not."""
    path = tmp_path / SELECTORS
    path.parent.mkdir(parents=True)
    # valid YAML, but `selectors` is a mapping, not the expected list of rows
    original = "selectors:\n  name: not_a_list\n"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(model_plan.ScaffoldError, match="not a list"):
        writer.merge_selector(tmp_path, "seshat_table_b")
    assert path.read_text(encoding="utf-8") == original


# --------------------------------------------------------------------------- #
# FIX #3 regression -- a symlinked merge target is refused, never followed
# --------------------------------------------------------------------------- #
def test_merge_sources_refuses_a_symlinked_target(tmp_path: Path) -> None:
    """If _sources.yml is a SYMLINK, rewriting it through write_text would follow
    the link and clobber its target (possibly outside the repo). Refuse it."""
    path = tmp_path / SOURCES
    path.parent.mkdir(parents=True)
    outside = tmp_path / "escape_sources.yml"  # a dangling target
    try:
        os.symlink(outside, path)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError, match="symlink"):
        writer.merge_sources(tmp_path, _plan("table_a"))
    assert not outside.exists()  # nothing written through the symlink


def test_merge_selector_refuses_a_symlinked_target(tmp_path: Path) -> None:
    """A symlinked selectors.yml is refused before the rewrite, same as sources."""
    path = tmp_path / SELECTORS
    path.parent.mkdir(parents=True)
    outside = tmp_path / "escape_selectors.yml"
    try:
        os.symlink(outside, path)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError, match="symlink"):
        writer.merge_selector(tmp_path, "seshat_table_a")
    assert not outside.exists()


def test_merge_target_refusal_holds_without_os_symlink_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove the refusal branch even where the OS forbids creating symlinks (this
    Windows box): a path reporting is_symlink() True is refused and never
    rewritten, regardless of whether a real link could be planted."""
    path = tmp_path / SOURCES
    path.parent.mkdir(parents=True)
    original = "sources: []\n"
    path.write_text(original, encoding="utf-8")
    monkeypatch.setattr(Path, "is_symlink", lambda self: True)

    with pytest.raises(SafeWriteError, match="symlink"):
        writer.merge_sources(tmp_path, _plan("table_a"))
    assert path.read_text(encoding="utf-8") == original  # untouched


def test_merge_refuses_a_symlinked_parent_component(tmp_path: Path) -> None:
    """A symlinked PARENT dir (e.g. dbt/ -> outside) redirects the rewrite even
    when the target file itself is not a link -- refused too, mirroring safe_write's
    whole-chain containment (#351/#352), not just the final component."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "dbt").mkdir()
    try:
        os.symlink(outside, tmp_path / "dbt" / "models", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError, match="symlink"):
        writer.merge_sources(tmp_path, _plan("table_a"))
    assert not (outside / "sources" / "_sources.yml").exists()
