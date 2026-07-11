"""Unit tests for AL2 -- Cross-Contract Assumption-Coherence Rule (spec 067).

AL2 ERRORs when two metric contracts binding to the SAME ``binds_to.gold_table`` record
>= 2 distinct DECIDED rulings for the same ambiguity code (whitespace-normalized,
case-insensitive text comparison). Only ``decision_status == "decided"`` entries with a
non-empty ruling contribute; undecided/absent contributes nothing; different gold tables
never cross-contaminate.

Contracts:
  C1  two contracts, same gold table, same code, DIFFERENT rulings   -> one ERROR
  C2  two contracts, same gold table, same code, SAME ruling         -> no Finding
  C3  same code, one decided + one undecided                         -> no Finding
  C4  different rulings but DIFFERENT gold tables                     -> no Finding
  C5  whitespace/case-only difference (normalized-equal)             -> no Finding
  C6  placeholder gold_table excluded from grouping                  -> no Finding
  C7  no mappings/*/metrics/*.yaml                                   -> no Finding
  C8  tracked-but-unparseable contract                               -> fail-loud ERROR
  C9  template + tests/ fixtures excluded from the scan              -> no Finding
"""

from __future__ import annotations

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.assumption_coherence import _TEMPLATE_PATH, check_assumption_coherence

pytestmark = pytest.mark.unit


def _ctx(tmp_path, files: dict[str, str]) -> RuleContext:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _contract(name: str, gold_table: str, code: str, status: str, ruling: str) -> str:
    return (
        f"name: {name}\n"
        "binds_to:\n"
        f"  gold_table: {gold_table}\n"
        "ambiguities:\n"
        f"  - id: {code}\n"
        f"    decision_status: {status}\n"
        f'    ruling: "{ruling}"\n'
    )


def _findings(ctx):
    return [f for f in check_assumption_coherence(ctx) if f.rule_id == "AL2"]


# C1: same gold table, same code, different decided rulings -> ERROR
def test_contradiction_fires(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            "mappings/t/metrics/A.yaml": _contract(
                "A", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
            "mappings/t/metrics/B.yaml": _contract(
                "B", "gold.fct_sales", "A3", "decided", "VAT included"
            ),
        },
    )
    fs = _findings(ctx)
    assert len(fs) == 1
    assert fs[0].severity is Severity.ERROR
    assert "A3" in fs[0].message and "gold.fct_sales" in fs[0].message


# C2: same gold table, same code, same ruling -> no Finding
def test_agreement_does_not_fire(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            "mappings/t/metrics/A.yaml": _contract(
                "A", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
            "mappings/t/metrics/B.yaml": _contract(
                "B", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
        },
    )
    assert _findings(ctx) == []


# C3: decided vs undecided on the same code -> no Finding (undecided contributes zero)
def test_decided_vs_undecided_does_not_fire(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            "mappings/t/metrics/A.yaml": _contract(
                "A", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
            "mappings/t/metrics/B.yaml": _contract(
                "B", "gold.fct_sales", "A3", "undecided", "VAT included"
            ),
        },
    )
    assert _findings(ctx) == []


# C4: different rulings but different gold tables -> no Finding
def test_different_gold_tables_do_not_cross(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            "mappings/t/metrics/A.yaml": _contract(
                "A", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
            "mappings/t/metrics/B.yaml": _contract(
                "B", "gold.fct_returns", "A3", "decided", "VAT included"
            ),
        },
    )
    assert _findings(ctx) == []


# C5: whitespace/case-only difference normalizes equal -> no Finding
def test_normalized_equal_does_not_fire(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            "mappings/t/metrics/A.yaml": _contract(
                "A", "gold.fct_sales", "A3", "decided", "VAT  Excluded"
            ),
            "mappings/t/metrics/B.yaml": _contract(
                "B", "gold.fct_sales", "A3", "decided", "vat excluded"
            ),
        },
    )
    assert _findings(ctx) == []


# C6: placeholder gold_table is excluded from grouping -> no Finding
def test_placeholder_gold_table_excluded(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            "mappings/t/metrics/A.yaml": _contract(
                "A", "gold.<fact>", "A3", "decided", "VAT excluded"
            ),
            "mappings/t/metrics/B.yaml": _contract(
                "B", "gold.<fact>", "A3", "decided", "VAT included"
            ),
        },
    )
    assert _findings(ctx) == []


# C7: no contract files -> no Finding
def test_no_contracts(tmp_path):
    ctx = _ctx(tmp_path, {"docs/readme.md": "# hi\n"})
    assert _findings(ctx) == []


# C8: tracked-but-unparseable contract -> fail-loud ERROR
def test_unparseable_fails_loud(tmp_path):
    ctx = _ctx(tmp_path, {"mappings/t/metrics/A.yaml": "name: A\n  bad: [unbalanced\n"})
    fs = _findings(ctx)
    assert len(fs) == 1
    assert fs[0].severity is Severity.ERROR
    assert "could not read/parse" in fs[0].message


# C9: template + tests/ fixtures excluded from the scan -> no Finding
def test_template_and_tests_excluded(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            _TEMPLATE_PATH: _contract(
                "T", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
            "tests/fixtures/x/metrics/B.yaml": _contract(
                "B", "gold.fct_sales", "A3", "decided", "VAT included"
            ),
        },
    )
    assert _findings(ctx) == []


# Three-contract group: two agree, one differs -> still one ERROR (>=2 distinct rulings)
def test_three_contracts_two_distinct_rulings(tmp_path):
    ctx = _ctx(
        tmp_path,
        {
            "mappings/t/metrics/A.yaml": _contract(
                "A", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
            "mappings/t/metrics/B.yaml": _contract(
                "B", "gold.fct_sales", "A3", "decided", "VAT excluded"
            ),
            "mappings/t/metrics/C.yaml": _contract(
                "C", "gold.fct_sales", "A3", "decided", "VAT included"
            ),
        },
    )
    assert len(_findings(ctx)) == 1
