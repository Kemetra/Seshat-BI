"""Unit tests for HR1 (cross-star conformed-dimension conformance)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.conformed_dimension import check_hr1

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[2]
_MAP = "docs/quality/conformed-dimension-map.yaml"


def _star(tmp_path: Path, table: str, yaml_text: str) -> str:
    rel = f"mappings/{table}/source-map.yaml"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml_text, encoding="utf-8")
    return rel


def _map(tmp_path: Path, yaml_text: str) -> str:
    dest = tmp_path / _MAP
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(yaml_text, encoding="utf-8")
    return _MAP


def _ctx(tmp_path: Path, *rel: str) -> RuleContext:
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(rel))


# a minimal star: needs gold_star.fact + gold_star.dimensions[]
def _star_yaml(fact: str, *dims: str, **kw: str) -> str:
    lines = [
        f"source_id: {kw.get('sid', fact)}",
        "gold_star:",
        f"  fact: {fact}",
        "  dimensions:",
    ]
    for d in dims:
        lines.append(f"    - name: {d}")
    return "\n".join(lines) + "\n"


# --- FR-007: engage only when >1 star ---


def test_hr1_single_star_no_finding(tmp_path: Path) -> None:
    ctx = _ctx(
        tmp_path, _star(tmp_path, "s1", _star_yaml("fct_a", "dim_product", sid="s1"))
    )
    assert list(check_hr1(ctx)) == []


def test_hr1_two_stars_no_shared_name_no_finding(tmp_path: Path) -> None:
    # different naming conventions -> no overlap (the real committed situation)
    a = _star(tmp_path, "s1", _star_yaml("fct_a", "dim_product_rss", sid="s1"))
    b = _star(tmp_path, "s2", _star_yaml("fct_b", "dim_product", sid="s2"))
    ctx = _ctx(tmp_path, a, b)
    assert list(check_hr1(ctx)) == []


# --- FR-006: undeclared cross-star name collision => ERROR ---


def test_hr1_undeclared_shared_name_fails_closed(tmp_path: Path) -> None:
    a = _star(tmp_path, "s1", _star_yaml("fct_a", "dim_product", sid="s1"))
    b = _star(tmp_path, "s2", _star_yaml("fct_b", "dim_product", sid="s2"))
    ctx = _ctx(tmp_path, a, b)  # no map declared
    findings = list(check_hr1(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert findings[0].rule_id == "HR1"
    assert "dim_product" in findings[0].message


def test_hr1_declared_conformed_matching_clears(tmp_path: Path) -> None:
    ya = (
        "source_id: s1\ngold_star:\n  fact: fct_a\n  dimensions:\n"
        "    - name: dim_product\n      surrogate_key: product_sk\n"
    )
    yb = (
        "source_id: s2\ngold_star:\n  fact: fct_b\n  dimensions:\n"
        "    - name: dim_product\n      surrogate_key: product_sk\n"
    )
    a = _star(tmp_path, "s1", ya)
    b = _star(tmp_path, "s2", yb)
    m = _map(
        tmp_path,
        "dimensions:\n  dim_product:\n    status: conformed\n    stars: [s1, s2]\n",
    )
    ctx = _ctx(tmp_path, a, b, m)
    assert list(check_hr1(ctx)) == []


def test_hr1_declared_distinct_clears(tmp_path: Path) -> None:
    a = _star(tmp_path, "s1", _star_yaml("fct_a", "dim_product", sid="s1"))
    b = _star(tmp_path, "s2", _star_yaml("fct_b", "dim_product", sid="s2"))
    m = _map(
        tmp_path,
        "dimensions:\n  dim_product:\n    status: distinct\n    stars: [s1, s2]\n",
    )
    ctx = _ctx(tmp_path, a, b, m)
    assert list(check_hr1(ctx)) == []


# --- FR-005: declared conformed but divergent surrogate_key => ERROR ---


def test_hr1_conformed_divergent_surrogate_key_fails_closed(tmp_path: Path) -> None:
    ya = (
        "source_id: s1\ngold_star:\n  fact: fct_a\n  dimensions:\n"
        "    - name: dim_product\n      surrogate_key: product_sk\n"
    )
    yb = (
        "source_id: s2\ngold_star:\n  fact: fct_b\n  dimensions:\n"
        "    - name: dim_product\n      surrogate_key: prod_key\n"
    )
    a = _star(tmp_path, "s1", ya)
    b = _star(tmp_path, "s2", yb)
    m = _map(
        tmp_path,
        "dimensions:\n  dim_product:\n    status: conformed\n    stars: [s1, s2]\n",
    )
    ctx = _ctx(tmp_path, a, b, m)
    findings = list(check_hr1(ctx))
    assert len(findings) == 1
    assert findings[0].severity is Severity.ERROR
    assert "surrogate_key" in findings[0].message


def test_hr1_conformed_missing_key_on_one_side_is_not_divergence(
    tmp_path: Path,
) -> None:
    # graceful degradation: key present on one side, absent on other -> no divergence
    ya = (
        "source_id: s1\ngold_star:\n  fact: fct_a\n  dimensions:\n"
        "    - name: dim_product\n      surrogate_key: product_sk\n"
    )
    yb = (
        "source_id: s2\ngold_star:\n  fact: fct_b\n"
        "  dimensions:\n    - name: dim_product\n"
    )
    a = _star(tmp_path, "s1", ya)
    b = _star(tmp_path, "s2", yb)
    m = _map(
        tmp_path,
        "dimensions:\n  dim_product:\n    status: conformed\n    stars: [s1, s2]\n",
    )
    ctx = _ctx(tmp_path, a, b, m)
    assert list(check_hr1(ctx)) == []


def test_hr1_conformed_divergent_attribute_type_fails_closed(tmp_path: Path) -> None:
    """Regression (review Important): the attribute silver_type divergence limb
    must actually resolve -- gold_placement uses the BARE dim name, so the prefix
    must be built from _bare(name), not the schema-qualified declared name."""
    ya = (
        "source_id: s1\ngold_star:\n  fact: fct_a\n  dimensions:\n"
        "    - name: gold.dim_product\n      surrogate_key: product_sk\n"
        "columns:\n"
        '    - name: item\n      silver_type: TEXT\n      gold_placement: "dim:dim_product.item"\n'  # noqa: E501
    )
    yb = (
        "source_id: s2\ngold_star:\n  fact: fct_b\n  dimensions:\n"
        "    - name: gold.dim_product\n      surrogate_key: product_sk\n"
        "columns:\n"
        '    - name: item\n      silver_type: NUMERIC\n      gold_placement: "dim:dim_product.item"\n'  # noqa: E501
    )
    a = _star(tmp_path, "s1", ya)
    b = _star(tmp_path, "s2", yb)
    m = _map(
        tmp_path,
        "dimensions:\n  dim_product:\n    status: conformed\n    stars: [s1, s2]\n",
    )
    ctx = _ctx(tmp_path, a, b, m)
    findings = list(check_hr1(ctx))
    assert len(findings) == 1
    assert "silver_type" in findings[0].message
    assert "item" in findings[0].message


# --- bad status value => ERROR ---


def test_hr1_bad_status_value_fails_closed(tmp_path: Path) -> None:
    a = _star(tmp_path, "s1", _star_yaml("fct_a", "dim_product", sid="s1"))
    b = _star(tmp_path, "s2", _star_yaml("fct_b", "dim_product", sid="s2"))
    m = _map(
        tmp_path,
        "dimensions:\n  dim_product:\n    status: maybe\n    stars: [s1, s2]\n",
    )
    ctx = _ctx(tmp_path, a, b, m)
    findings = list(check_hr1(ctx))
    # bad-value ERROR (and, since the decl is invalid, dim_product is treated as
    # undeclared -> also the FR-006 ERROR). At least the bad-value one must fire.
    assert any("maybe" in f.message for f in findings)
    assert all(f.severity is Severity.ERROR for f in findings)


# --- degenerate dims are out of scope ---


def test_hr1_degenerate_dimension_not_conformed(tmp_path: Path) -> None:
    ya = (
        "source_id: s1\ngold_star:\n  fact: fct_a\n  dimensions:\n    - name: dim_a\n"
        "  degenerate_dimensions:\n    - transaction_id\n"
    )
    yb = (
        "source_id: s2\ngold_star:\n  fact: fct_b\n  dimensions:\n    - name: dim_b\n"
        "  degenerate_dimensions:\n    - transaction_id\n"
    )
    a = _star(tmp_path, "s1", ya)
    b = _star(tmp_path, "s2", yb)
    ctx = _ctx(tmp_path, a, b)
    # transaction_id shared as a degenerate dim must NOT trigger a conformance error
    assert list(check_hr1(ctx)) == []


# --- landing: HR1 is <no-finding> on the real committed tree (no shared names) ---


def test_hr1_clean_on_real_committed_tree() -> None:
    import subprocess

    tracked = tuple(
        subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, cwd=_REPO
        ).stdout.split()
    )
    ctx = RuleContext(repo_root=_REPO, tracked_files=tracked)
    assert list(check_hr1(ctx)) == []


# --- polish: static-only, no numeric score, no write ---


def test_hr1_module_imports_no_database_driver() -> None:
    src = (_REPO / "src" / "seshat" / "rules" / "conformed_dimension.py").read_text(
        encoding="utf-8"
    )
    for forbidden in ("import psycopg", "import sqlalchemy", ".connect(", "DSN"):
        assert forbidden not in src


def test_hr1_messages_have_no_numeric_score(tmp_path: Path) -> None:
    a = _star(tmp_path, "s1", _star_yaml("fct_a", "dim_product", sid="s1"))
    b = _star(tmp_path, "s2", _star_yaml("fct_b", "dim_product", sid="s2"))
    ctx = _ctx(tmp_path, a, b)
    for f in check_hr1(ctx):
        assert "%" not in f.message
