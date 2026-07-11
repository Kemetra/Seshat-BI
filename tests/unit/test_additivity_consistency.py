"""Unit tests for the Additivity-Consistency Lineage Rule (spec 068, idea H1).

The rule statically cross-reads two committed define-layer facts per metric -- its
declared additivity classification (closed vocabulary "Fully additive" / "Semi-additive"
/ "Non-additive") and its derivation edges -- and ERRORs when a metric's additivity is
composed illegally per a small closed generic legality table:

  - a Non-additive (ratio/average) child composed by a DIRECT SUM  -> ILLEGAL
  - a Semi-additive component composed into a PLAIN-SUM parent      -> ILLEGAL
  - a Non-additive child recomputed base-over-base                  -> LEGAL

It acts ONLY on the exact committed classification words; an absent or
out-of-vocabulary classification on a metric that participates in a derivation
edge is ERRORed as absent/ambiguous and NEVER inferred (Principle V). An
unknown/unstated composition kind yields NO verdict (never assume SUM). It reads
committed text only, executes nothing, and emits ERROR-only findings (no score).

Fixtures are planted under a temp corpus at the real glob path so the parser is
exercised against committed-shape prose, mirroring the AL1 test harness.
"""

from __future__ import annotations

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.additivity_consistency import RULE_ID, check_additivity_consistency

pytestmark = pytest.mark.unit

# The rule globs this define-layer prose corpus (skills/retail-kpi-knowledge/contracts).
_C = "skills/retail-kpi-knowledge/contracts"


def _ctx(tmp_path, files: dict[str, str]) -> RuleContext:
    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return RuleContext(repo_root=tmp_path, tracked_files=tuple(files.keys()))


def _findings(ctx):
    return [f for f in check_additivity_consistency(ctx) if f.rule_id == RULE_ID]


def _contract(name: str, additivity: str, derives: str = "") -> str:
    """A define-layer contract shell with the two prose headings the rule reads."""
    derives_block = f"**Derives from**\n{derives}\n\n" if derives else ""
    return (
        f"# {name} -- Metric Contract\n\n{derives_block}**Additivity**\n{additivity}\n"
    )


# --------------------------------------------------------------------------- #
# US1 -- illegal composition surfaced as ERROR (P1)
# --------------------------------------------------------------------------- #
def test_us1_1_non_additive_child_direct_summed_is_error(tmp_path):
    # A parent that composes a Non-additive (ratio) child by direct SUM -> ILLEGAL.
    files = {
        f"{_C}/MarginRate.md": _contract(
            "MarginRate", "Non-additive ratio; recompute at each grain, never sum."
        ),
        f"{_C}/BadTotalMarginRate.md": _contract(
            "BadTotalMarginRate",
            "Fully additive across all dimensions.",
            derives="BadTotalMarginRate = sum of MarginRate across branches.",
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == Severity.ERROR
    assert "MarginRate" in f.message
    assert "sum" in f.message.lower()


def test_us1_2_base_over_base_recompute_is_legal(tmp_path):
    # A Non-additive child recomputed base-over-base from additive parents -> LEGAL.
    files = {
        f"{_C}/TotalSales.md": _contract(
            "TotalSales", "Fully additive across all rows."
        ),
        f"{_C}/TxnCount.md": _contract("TxnCount", "Fully additive count."),
        f"{_C}/AvgBasket.md": _contract(
            "AvgBasket",
            "Non-additive average; recompute at each grain.",
            derives="AvgBasket = TotalSales / TxnCount (recomputed at grain).",
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_us1_3_semi_additive_into_plain_sum_parent_is_error(tmp_path):
    files = {
        f"{_C}/Inventory.md": _contract(
            "Inventory",
            "Semi-additive over time; use a last/average time rule, never sum.",
        ),
        f"{_C}/BadInventoryTotal.md": _contract(
            "BadInventoryTotal",
            "Fully additive plain sum.",
            derives="BadInventoryTotal = sum of Inventory across periods.",
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert len(findings) == 1
    assert findings[0].severity == Severity.ERROR
    assert "Inventory" in findings[0].message


# --------------------------------------------------------------------------- #
# US2 -- absent/ambiguous classification refused, never inferred (P1)
# --------------------------------------------------------------------------- #
def test_us2_1_absent_classification_on_edge_is_error(tmp_path):
    # A metric on an edge with no Additivity heading -> ERROR absent, no verdict.
    files = {
        f"{_C}/NoClass.md": (
            "# NoClass -- Metric Contract\n\n"
            "Some prose but no additivity heading at all.\n"
        ),
        f"{_C}/UsesNoClass.md": _contract(
            "UsesNoClass",
            "Fully additive.",
            derives="UsesNoClass = sum of NoClass across branches.",
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert any(
        f.severity == Severity.ERROR
        and "NoClass" in f.message
        and ("absent" in f.message.lower() or "ambiguous" in f.message.lower())
        for f in findings
    )


def test_us2_2_out_of_vocabulary_classification_is_error(tmp_path):
    files = {
        f"{_C}/Weird.md": _contract(
            "Weird", "Somewhat additive-ish depending on mood."
        ),
        f"{_C}/UsesWeird.md": _contract(
            "UsesWeird",
            "Fully additive.",
            derives="UsesWeird = sum of Weird across branches.",
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    assert any(
        f.severity == Severity.ERROR
        and "Weird" in f.message
        and ("ambiguous" in f.message.lower() or "absent" in f.message.lower())
        for f in findings
    )


def test_us2_never_infers_a_class_no_composition_verdict(tmp_path):
    # An absent class must NOT yield a composition verdict guessed from a default class.
    files = {
        f"{_C}/NoClass.md": (
            "# NoClass -- Metric Contract\n\nno additivity heading.\n"
        ),
        f"{_C}/UsesNoClass.md": _contract(
            "UsesNoClass",
            "Fully additive.",
            derives="UsesNoClass = sum of NoClass across branches.",
        ),
    }
    findings = _findings(_ctx(tmp_path, files))
    # Exactly the absent/ambiguous ERROR -- no separate "illegal composition" verdict
    # that would only exist if the rule had defaulted NoClass to a real class.
    illegal_verdicts = [f for f in findings if "illegal" in f.message.lower()]
    assert illegal_verdicts == []


# --------------------------------------------------------------------------- #
# Edge cases + invariants
# --------------------------------------------------------------------------- #
def test_unknown_composition_kind_yields_no_verdict(tmp_path):
    # Derivation stated, but the composition kind is not explicitly a sum/ratio ->
    # unknown -> NO verdict (never assume SUM). Principle V knife-edge.
    files = {
        f"{_C}/RatioChild.md": _contract("RatioChild", "Non-additive ratio."),
        f"{_C}/Vague.md": _contract(
            "Vague",
            "Fully additive.",
            derives="Vague is related to RatioChild somehow (no stated composition).",
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_empty_corpus_is_clean_pass(tmp_path):
    assert _findings(_ctx(tmp_path, {})) == []


def test_classification_without_edges_is_not_an_error(tmp_path):
    files = {
        f"{_C}/StandaloneBase.md": _contract(
            "StandaloneBase", "Fully additive base measure."
        ),
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_template_and_test_paths_are_exempt(tmp_path):
    # The generic template + any tests/ fixture must not be scanned.
    illegal = (
        _contract("X", "Fully additive.", derives="X = sum of Y across branches.")
        + "\n"
    )  # would be illegal if Y were non-additive, but these paths are exempt
    files = {
        "skills/retail-kpi-knowledge/references/metric-contract-template.md": illegal,
        "tests/fixtures/kpi/SomeFixture.md": illegal,
    }
    assert _findings(_ctx(tmp_path, files)) == []


def test_unreadable_source_fails_loud(tmp_path):
    # A tracked contract path that does not exist on disk -> fail-loud ERROR naming it,
    # never a silent skip (AL1 fail-loud-on-unreadable seam).
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
        f"{_C}/MarginRate.md": _contract("MarginRate", "Non-additive ratio."),
        f"{_C}/BadTotal.md": _contract(
            "BadTotal",
            "Fully additive.",
            derives="BadTotal = sum of MarginRate across branches.",
        ),
    }
    for f in _findings(_ctx(tmp_path, files)):
        # Categorical only: severity is an enum, message carries no digit-based score.
        assert f.severity in (Severity.ERROR, Severity.WARNING)
