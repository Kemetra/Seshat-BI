"""Unit tests for the Comparison-Baseline Declaration Guard (idea H6).

A growth / comparison metric contract must DECLARE two things or the gate ERRORs:
  1. a comparison baseline -- either RULED, or honestly DISCLOSED as owner-pending
     (an undisclosed silent omission is the target defect);
  2. a primary DATE field in its Required fields (a comparison is placed in time).

Detection is keyed on METRIC IDENTITY only (the title/business-question naming a
growth / same-store / like-for-like / year-to-date / period-over-period / YoY
comparison), NEVER on the presence of the baseline declaration itself -- otherwise a
contract that OMITS the baseline could never be detected as a comparison metric and
its omission would pass silently (the circular-detection trap).

Mirrors the AD1 prose-corpus harness: fixtures are planted at the real glob path
``skills/retail-kpi-knowledge/contracts/*.md`` and the rule reads committed text only
(stdlib ``re``), executes nothing, emits ERROR-only findings (no numeric score), and
exempts the template + any ``tests/`` fixture. Honest owner-pending disclosure passes
(the Principle-V discriminator, mirroring AL1's tolerance of a disclosed open item);
the rule NEVER chooses a baseline for a human (Principle V).
"""

from __future__ import annotations

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.comparison_baseline import RULE_ID, check_comparison_baseline

pytestmark = pytest.mark.unit

_C = "skills/retail-kpi-knowledge/contracts"


def _ctx(tmp_path, files: dict[str, str]) -> RuleContext:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _findings(ctx):
    return [f for f in check_comparison_baseline(ctx) if f.rule_id == RULE_ID]


def _contract(
    name: str, *, required: str = "", baseline: str = "", extra: str = ""
) -> str:
    """A define-layer contract shell with a title, Required fields, and body prose."""
    required_block = f"**Required fields**\n{required}\n\n" if required else ""
    return (
        f"# {name} -- Metric Contract\n\n"
        f"**Business definition**\nSome definition.\n\n"
        f"{required_block}"
        f"{baseline}\n{extra}\n"
    )


# A complete, correct comparison contract (baseline ruled + a date field present).
def _good_growth(name: str = "Net Sales Growth %") -> str:
    return _contract(
        name,
        required=(
            "- Net Sales at the transaction-line grain\n"
            "- sale date key (to place a row in the selected period vs the baseline)\n"
            "- the comparison-baseline (RULED -- SPLY primary)"
        ),
        baseline=(
            "**Comparison baseline -- RULED**\n"
            "The baseline is SPLY primary, prior period secondary."
        ),
    )


# --------------------------------------------------------------------------- #
# US1 -- a comparison contract missing the baseline is an ERROR (P1)
# --------------------------------------------------------------------------- #
def test_us1_growth_contract_missing_baseline_is_error(tmp_path):
    # Detected as a growth metric by its TITLE; body silently omits any baseline.
    files = {
        f"{_C}/SilentGrowth.md": _contract(
            "Net Sales Growth %",
            required="- Net Sales\n- sale date key (period placement)",
            baseline="**Interpretation**\nThe headline growth KPI.",  # no baseline word
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == Severity.ERROR
    assert "baseline" in f.message.lower()


def test_us1_growth_contract_missing_date_field_is_error(tmp_path):
    # Baseline present, but no primary DATE field in Required fields.
    files = {
        f"{_C}/NoDateGrowth.md": _contract(
            "Same-Store Sales Growth %",
            required="- Net Sales\n- branch/store key (comparable-store filter)",
            baseline=(
                "**Comparison baseline -- RULED**\n"
                "SPLY primary, prior period secondary."
            ),
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "date" in findings[0].message.lower()


# --------------------------------------------------------------------------- #
# US2 -- honest owner-pending disclosure PASSES (the Principle-V discriminator)
# --------------------------------------------------------------------------- #
def test_us2_owner_pending_baseline_disclosed_passes(tmp_path):
    # A growth contract whose baseline is HONESTLY declared owner-pending must NOT
    # fire -- the rule never forces a human's open ruling closed (mirrors AL1).
    files = {
        f"{_C}/SameStore.md": _contract(
            "Same-Store Sales Growth %",
            required=(
                "- Net Sales at line grain\n"
                "- sale date key (period vs baseline placement)\n"
                "- the comparison-baseline choice *(owner-pending -- un-coded)*"
            ),
            baseline=(
                "**Open ambiguity 2 -- comparison baseline"
                " (OWNER-PENDING, un-coded)**\n"
                "Same as KPI-MC-11: SPLY vs prior period. Agent does not choose it."
            ),
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_us2_ruled_baseline_passes(tmp_path):
    files = {f"{_C}/Growth.md": _good_growth()}
    assert _findings(_ctx(tmp_path, files)) == []


# --------------------------------------------------------------------------- #
# US3 -- no false positive on a NON-comparison base metric (over-firing guard)
# --------------------------------------------------------------------------- #
def test_us3_base_metric_without_growth_signal_is_clean(tmp_path):
    # A plain additive base metric names no comparison in its title -> not detected,
    # so the absence of a baseline is NOT an error. This is the over-firing guard:
    # a rule that errored on every contract would also pass the live-corpus check.
    files = {
        f"{_C}/NetSales.md": _contract(
            "Net Sales",
            required="- gross sales at line grain\n- sale date key",
            baseline="**Additivity**\nFully additive across all rows.",
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_us3_ratio_metric_without_comparison_is_clean(tmp_path):
    # A ratio/percentage metric (gross-margin-percent shape) is NOT a time comparison;
    # it must not be swept in by an incidental "percent"/"rate" word.
    files = {
        f"{_C}/GrossMarginPercent.md": _contract(
            "Gross Margin Percent",
            required="- gross margin\n- gross sales",
            baseline="**Additivity**\nNon-additive ratio; recompute at each grain.",
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


# --------------------------------------------------------------------------- #
# Edge cases + invariants (mirror AD1)
# --------------------------------------------------------------------------- #
def test_ytd_with_both_comparisons_disclosed_passes(tmp_path):
    # YTD names a to-date-vs-prior-year comparison and a marked date dimension.
    files = {
        f"{_C}/Ytd.md": _contract(
            "Year-to-Date Net Sales",
            required=(
                "- Net Sales at line grain, aggregable to day\n"
                "- a marked, contiguous date dimension\n"
                "- the calendar year-start boundary"
            ),
            baseline=(
                "**Year-start boundary + partial period -- RULED**\n"
                "Compared to-date-vs-to-date against the prior year (primary) and the "
                "full prior-year YTD (secondary) -- a comparison baseline, both ruled."
            ),
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_empty_corpus_is_clean_pass(tmp_path):
    assert _findings(_ctx(tmp_path, {})) == []


def test_template_and_test_paths_are_exempt(tmp_path):
    bad = _contract(
        "Net Sales Growth %",
        required="- Net Sales (no date field)",
        baseline="**Interpretation**\nno baseline here.",
    )
    files = {
        "skills/retail-kpi-knowledge/references/metric-contract-template.md": bad,
        "tests/fixtures/kpi/SomeFixture.md": bad,
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_unreadable_source_fails_loud(tmp_path):
    ctx = RuleContext(
        repo_root=tmp_path,
        tracked_files=(f"{_C}/Ghost.md",),  # declared tracked but never written
    )
    findings = _findings(ctx)
    assert any(
        f.severity == Severity.ERROR and "Ghost.md" in f.locator for f in findings
    )


def test_findings_carry_no_numeric_score(tmp_path):
    files = {
        f"{_C}/SilentGrowth.md": _contract(
            "Net Sales Growth %",
            required="- Net Sales\n- sale date key",
            baseline="**Interpretation**\nno baseline.",
        ),
    }
    for f in _findings(_ctx(tmp_path, files)):
        assert f.severity in (Severity.ERROR, Severity.WARNING)
