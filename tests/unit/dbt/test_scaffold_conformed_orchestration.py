"""#418-P1 orchestrator wiring: the conformed-map is read fail-safe, and a reuse
is surfaced in the operator notes.

The reuse LOGIC is proven driver-free in ``test_dbt_scaffold.py`` (owner vs
reuser plans, gate + parity validators). Here we pin the two orchestrator seams
the plan tests do not touch: ``_load_conformed_map`` never fails closed on a bad
map, and ``_notes`` names a reused conformed dim + its owning star.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.dbt.scaffold import model_plan, orchestrator

pytestmark = pytest.mark.unit

_MAP_REL = "docs/quality/conformed-dimension-map.yaml"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit_map(root: Path, text: str) -> None:
    """Write the conformed map and COMMIT it, so it is visible at HEAD (the map is
    read from committed state, not the worktree -- #419 review)."""
    _git(root, "init", "-q")
    path = root / _MAP_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "map")


def test_load_conformed_map_absent_returns_none(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    assert orchestrator._load_conformed_map(tmp_path) is None


def test_load_conformed_map_uncommitted_is_ignored(tmp_path: Path) -> None:
    """#419 review: an UNCOMMITTED worktree map must NOT drive reuse -- the map is
    an ownership authority, read from HEAD. A file present only in the worktree
    (never committed) is invisible to the committed-state read -> no reuse."""
    _git(tmp_path, "init", "-q")
    path = tmp_path / _MAP_REL
    path.parent.mkdir(parents=True)
    path.write_text(
        "dimensions:\n  dim_customer:\n    status: conformed\n    stars: [a, b]\n",
        encoding="utf-8",
    )
    assert orchestrator._load_conformed_map(tmp_path) is None  # not committed


def test_load_conformed_map_malformed_returns_none(tmp_path: Path) -> None:
    _commit_map(tmp_path, "this: [is: not: valid: yaml")
    # fail-SAFE: a malformed map disables reuse, never crashes scaffold
    assert orchestrator._load_conformed_map(tmp_path) is None


def test_load_conformed_map_non_mapping_returns_none(tmp_path: Path) -> None:
    _commit_map(tmp_path, "- a\n- b\n")  # a list, not a mapping
    assert orchestrator._load_conformed_map(tmp_path) is None


def test_load_conformed_map_committed_returns_parsed(tmp_path: Path) -> None:
    _commit_map(
        tmp_path,
        "dimensions:\n  dim_customer:\n    status: conformed\n    stars: [a, b]\n",
    )
    parsed = orchestrator._load_conformed_map(tmp_path)
    assert parsed == {
        "dimensions": {"dim_customer": {"status": "conformed", "stars": ["a", "b"]}}
    }


def test_load_conformed_map_ignores_uncommitted_edit_to_committed_file(
    tmp_path: Path,
) -> None:
    """A committed map that is then EDITED in the worktree still reads the COMMITTED
    content, not the dirty edit (#419 review)."""
    _commit_map(
        tmp_path,
        "dimensions:\n  dim_customer:\n    status: conformed\n    stars: [a, b]\n",
    )
    # dirty the worktree copy with a DIFFERENT ruling
    (tmp_path / _MAP_REL).write_text(
        "dimensions:\n  dim_customer:\n    status: distinct\n    stars: [a, b]\n",
        encoding="utf-8",
    )
    parsed = orchestrator._load_conformed_map(tmp_path)
    # the COMMITTED `conformed` ruling wins, not the dirty `distinct` edit
    assert parsed["dimensions"]["dim_customer"]["status"] == "conformed"


def _plan_with_reuse() -> model_plan.ScaffoldPlan:
    from seshat.dbt.contracts import FactBinding

    fact = FactBinding(
        name="fct_x",
        business_key=("id",),
        additive_money_measures=(),
    )
    document = {
        "meta": {"table_id": "returns_line", "grain": "one row"},
        "columns": [
            {"source_name": "id", "decision": "keep", "rename_to": "id"},
            {"source_name": "cid", "decision": "keep", "rename_to": "customer_id"},
        ],
        "gold_star": {
            "fact": {"name": "gold.fct_x", "business_key": "id", "measures": []},
            "dimensions": [
                {
                    "name": "gold.dim_customer_rss",
                    "surrogate_key": "customer_sk",
                    "attributes": ["customer_id"],
                },
            ],
            "date_dimension": {"name": "gold.dim_date_x", "surrogate_key": "date_sk"},
        },
    }
    conformed = {
        "dimensions": {
            "dim_customer_rss": {
                "status": "conformed",
                "stars": ["retail_store_sales", "returns_line"],
            }
        }
    }
    source = model_plan.MapSource(
        document=document,
        source_map="mappings/returns_line/source-map.yaml",
        source_map_revision="d" * 40,
        conformed_map=conformed,
    )
    return model_plan.build_scaffold_plan(source, "returns_line", fact)


def test_notes_surface_a_reused_conformed_dimension() -> None:
    plan = _plan_with_reuse()
    assert plan.reused_dimensions == ("dim_customer_rss",)
    assert plan.reused_dimension_owners == {"dim_customer_rss": "retail_store_sales"}
    notes = orchestrator._notes(plan)
    reuse_note = next((n for n in notes if "dim_customer_rss" in n), None)
    assert reuse_note is not None
    assert "owned by another star" in reuse_note
    assert "ref()" in reuse_note
    # L4: the note NAMES the owning star, not just "another star"
    assert "retail_store_sales" in reuse_note


def test_notes_have_no_reuse_line_when_nothing_is_reused() -> None:
    from seshat.dbt.scaffold import model_plan as mp

    # a plan with no reuse (empty reused_dimensions) carries no reuse note
    fact = __import__("seshat.dbt.contracts", fromlist=["FactBinding"]).FactBinding(
        name="fct_y", business_key=("id",), additive_money_measures=()
    )
    document = {
        "meta": {"table_id": "solo", "grain": "one row"},
        "columns": [{"source_name": "id", "decision": "keep", "rename_to": "id"}],
        "gold_star": {
            "fact": {"name": "gold.fct_y", "business_key": "id", "measures": []},
            "dimensions": [
                {"name": "gold.dim_a", "surrogate_key": "a_sk", "attributes": ["id"]}
            ],
        },
    }
    plan = mp.build_scaffold_plan(
        mp.MapSource(
            document=document,
            source_map="mappings/solo/source-map.yaml",
            source_map_revision="d" * 40,
        ),
        "solo",
        fact,
    )
    notes = orchestrator._notes(plan)
    assert all("owned by another star" not in n for n in notes)
