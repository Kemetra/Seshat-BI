"""Every rule's coverage declaration must agree with what that rule actually reads.

A declaration that disagrees with its rule is WORSE than no declaration: it reports
`evaluated` for a rule that scanned nothing, which is the false assurance the whole
census exists to remove. Two properties are checked here, both against the rules'
OWN selectors and messages rather than against copies of their logic:

1. a corpus rule is `evaluated` exactly when its own iterator selects something --
   asserted over the LIVE tracked-file list, so the check keeps working as the tree
   changes, plus over synthetic in-scope / fixture paths;
2. a rule declaring ``ReportsItsOwnAbsence`` really does speak up on an empty
   repository. That claim credits a rule without naming an input, so it is verified
   by measurement here rather than trusted.

The migration counter (79 -> 0 undeclared) is pinned at the bottom.

See docs/superpowers/specs/2026-08-04-rule-coverage-honesty-design.md.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Iterable

import pytest

import seshat.rules  # noqa: F401  -- side-effecting: fires every @register decorator
from seshat.core import RuleContext, is_test_path
from seshat.decision_store import store_files
from seshat.registry import all_rules
from seshat.rule_coverage import (
    CoverageState,
    ReportsItsOwnAbsence,
    Requirement,
    coverage_for,
)
from seshat.rules import (
    additivity_consistency,
    assumption_coherence,
    assumptions,
    comparison_baseline,
    currency_unit,
    design_background,
    design_categorical_distinctness,
    design_contrast,
    design_grid_closure,
    design_ramp_deltae,
    design_review_evidence,
    design_theme,
    design_theme_fidelity,
    design_visual_selfcheck,
    formatting_plan,
    g6,
    git_meta,
    live_surface_boundary,
    never_execute,
    pbir,
    publish_pack,
    readiness_status,
    rename_impact_guard,
    report_intent,
    rls_access,
    rule_kp1,
    scorecard,
    snapshot_time_additivity,
    source_data_contract,
    source_freshness,
)
from seshat.runner import _missing_for, build_context, coverage_census
from seshat.star_discovery import source_map_table
from seshat.tmdl import iter_model_files

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]

# A selector answers "did this rule have anything to read?" the way the RULE does.
# Where a rule exposes no path-selecting helper, the shared definition it itself
# uses is called instead (``source_map_table``, ``store_files``, its own compiled
# path regex) -- never a fresh copy of the predicate, which could drift silently.
Selector = Callable[[RuleContext], Iterable[object]]


def _non_test(ctx: RuleContext) -> list[str]:
    return [p for p in ctx.tracked_files if not is_test_path(p)]


def _tmdl(ctx: RuleContext) -> list[tuple[str, str]]:
    return list(iter_model_files(ctx, ".tmdl"))


def _store(ctx: RuleContext) -> list[str]:
    return store_files(tuple(_non_test(ctx)))


#: rule_id -> (selector, an in-scope path). The path is what the rule's own iterator
#: accepts; the fixture-prefixed variant of it must be rejected by both the selector
#: and the declaration.
CASES: tuple[tuple[str, Selector, str], ...] = (
    # --- TMDL / PBIP model corpora -------------------------------------------
    ("D1", _tmdl, "powerbi/Sales.SemanticModel/definition/tables/Sales.tmdl"),
    ("D5", _tmdl, "powerbi/Sales.SemanticModel/definition/tables/Sales.tmdl"),
    ("D6", _tmdl, "powerbi/Sales.SemanticModel/definition/model.tmdl"),
    ("D8", _tmdl, "powerbi/Sales.SemanticModel/definition/tables/Sales.tmdl"),
    ("C1", _tmdl, "powerbi/Sales.SemanticModel/definition/expressions.tmdl"),
    (
        "G6",
        g6._iter_param_files,
        "powerbi/Sales.SemanticModel/definition/expressions.tmdl",
    ),
    (
        "HR9",
        lambda ctx: [
            p
            for p in _non_test(ctx)
            if rename_impact_guard._TMDL_RE.match(p)  # HR9's own path regex
        ],
        "powerbi/Sales.SemanticModel/definition/tables/Sales.tmdl",
    ),
    ("R1", pbir._iter_pbir_files, "powerbi/Sales.Report/definition.pbir"),
    ("R2", pbir._iter_report_json, "powerbi/Sales.Report/definition/report.json"),
    ("G3", git_meta._iter_bom_candidates, "powerbi/Sales.Report/definition.pbir"),
    ("G5", lambda ctx: list(ctx.tracked_files), "docs/anything.md"),
    # --- decision store / mapping artifacts ----------------------------------
    ("DS1", _store, ".seshat/kpi-contracts.yaml"),
    ("DS5", _store, ".seshat/cleaning-rules.yaml"),
    ("AL1", assumptions._iter_contracts, "mappings/t/metrics/revenue.yaml"),
    ("AL2", assumption_coherence._iter_contracts, "mappings/t/metrics/revenue.yml"),
    (
        "HR5",
        snapshot_time_additivity._iter_contracts,
        "mappings/t/metrics/revenue.yaml",
    ),
    (
        "HR11",
        currency_unit._iter_metric_contract_files,
        "mappings/t/metrics/revenue.yaml",
    ),
    ("KP1", rule_kp1._contracts, "mappings/t/metrics/revenue.yaml"),
    ("HR4", source_freshness._iter_filled_maps, "mappings/t/source-map.yaml"),
    (
        "HR13",
        lambda ctx: [p for p in _non_test(ctx) if source_map_table(p)],
        "mappings/t/source-map.yaml",
    ),
    ("HR6", rls_access._iter_role_contract_files, "mappings/t/roles/analyst.yaml"),
    (
        "HR12",
        source_data_contract._iter_contracts,
        "mappings/t/source-data-contract.yaml",
    ),
    ("RS1", readiness_status._iter_status_files, "mappings/t/readiness-status.yaml"),
    ("SL1", scorecard._iter_scorecards, "mappings/t/kpi-coverage-scorecard.md"),
    ("PP1", publish_pack._iter_packs, "mappings/t/handoff/bi-handoff-pack.md"),
    # --- design artifacts -----------------------------------------------------
    ("DL1", design_theme._iter_theme_files, "design/kemetra.theme.json"),
    ("DL2", design_background._iter_background_specs, "design/page1.background.yaml"),
    (
        "DL3",
        design_theme_fidelity._iter_tokens_files,
        "design/kemetra-design-tokens.yaml",
    ),
    ("DL8", design_theme_fidelity._iter_tokens_files, "design/tokens.yaml"),
    ("CT1", design_contrast._iter_tokens_files, "design/kemetra-design-tokens.yaml"),
    ("CT2", design_ramp_deltae._iter_tokens_files, "design/tokens.yaml"),
    (
        "CT3",
        design_categorical_distinctness._iter_tokens_files,
        "design/kemetra-design-tokens.yaml",
    ),
    ("DL5", design_grid_closure._iter_grid_files, "design/grids/16x9-grid.yaml"),
    ("DL6", design_visual_selfcheck._iter_instances, "design/visuals/kpi-card.yaml"),
    ("DL9", report_intent._iter_instances, "reports/sales/design/report-intent.yaml"),
    (
        "DL4",
        design_review_evidence._iter_instances,
        "docs/quality/design-review-evidence.md",
    ),
    ("DL7", formatting_plan._iter_ledgers, "design/formatting-plan.md"),
    (
        "AD1",
        additivity_consistency._iter_corpus,
        "skills/retail-kpi-knowledge/contracts/revenue.md",
    ),
    (
        "CB1",
        comparison_baseline._iter_corpus,
        "skills/retail-kpi-knowledge/contracts/revenue.md",
    ),
    # --- source-scanning boundary rules --------------------------------------
    (
        "B1",
        lambda ctx: [p for p in ctx.tracked_files if never_execute._is_governed(p)],
        "src/seshat/rules/example.py",
    ),
    (
        "B3",
        lambda ctx: [
            p for p in ctx.tracked_files if p in live_surface_boundary._LIVE_SURFACE
        ],
        "src/seshat/dialect.py",
    ),
)

BY_ID = {registered.id: registered for registered in all_rules()}


def _state(rule_id: str, ctx: RuleContext) -> CoverageState:
    return coverage_for(BY_ID[rule_id], missing=_missing_for(ctx)).state


def _ran(selector: Selector, ctx: RuleContext) -> bool:
    return bool(list(selector(ctx)))


CASE_IDS = [case[0] for case in CASES]


@pytest.mark.parametrize(("rule_id", "selector", "in_scope"), CASES, ids=CASE_IDS)
def test_declaration_agrees_with_the_rules_own_selector_on_an_in_scope_path(
    rule_id: str, selector: Selector, in_scope: str, tmp_path: Path
) -> None:
    """One in-scope tracked file: the rule reads it, so coverage says `evaluated`."""
    target = tmp_path / in_scope
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(in_scope,))
    assert _ran(selector, ctx), f"{rule_id}: {in_scope} is not in scope for the rule"
    assert _state(rule_id, ctx) is CoverageState.EVALUATED, rule_id


@pytest.mark.parametrize(("rule_id", "selector", "in_scope"), CASES, ids=CASE_IDS)
def test_declaration_agrees_with_the_rules_own_selector_on_an_empty_tree(
    rule_id: str, selector: Selector, in_scope: str, tmp_path: Path
) -> None:
    """Nothing tracked: the rule reads nothing, so coverage must NOT say evaluated."""
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    assert not _ran(selector, ctx)
    assert _state(rule_id, ctx) is CoverageState.UNEVALUABLE, rule_id


@pytest.mark.parametrize(("rule_id", "selector", "in_scope"), CASES, ids=CASE_IDS)
def test_a_fixture_only_tree_credits_no_rule_that_exempts_fixtures(
    rule_id: str, selector: Selector, in_scope: str, tmp_path: Path
) -> None:
    """A tests/ copy of the same path must be treated identically by both sides.

    Most rules exempt committed fixtures (they carry deliberately non-conforming
    content); B1/G5 deliberately do not. Either way the declaration must AGREE with
    the rule, which is what this asserts -- not a blanket exemption.
    """
    fixture = f"tests/fixtures/{in_scope}"
    target = tmp_path / fixture
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x", encoding="utf-8")
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(fixture,))
    declared_ran = _state(rule_id, ctx) is CoverageState.EVALUATED
    assert declared_ran == _ran(selector, ctx), rule_id


@pytest.mark.parametrize(("rule_id", "selector", "in_scope"), CASES, ids=CASE_IDS)
def test_declaration_agrees_with_the_rules_own_selector_on_the_live_tree(
    rule_id: str, selector: Selector, in_scope: str
) -> None:
    """The same agreement over the REAL tracked-file list.

    Synthetic paths only prove the shapes a test author thought of. Running the
    comparison over the live tree is what catches a glob that is subtly wrong about
    this repo -- and it keeps holding as the tree changes.
    """
    ctx = build_context(REPO_ROOT)
    declared_ran = _state(rule_id, ctx) is CoverageState.EVALUATED
    assert declared_ran == _ran(selector, ctx), (
        f"{rule_id}: coverage says ran={declared_ran} but its own selector "
        f"disagrees on the live tree"
    )


# --- the self-reporting claim, measured -------------------------------------


SELF_REPORTING_IDS = tuple(
    registered.id
    for registered in all_rules()
    if any(isinstance(d, ReportsItsOwnAbsence) for d in registered.requires)
)


def test_self_reporting_rules_exist_so_the_measurement_below_is_not_vacuous() -> None:
    assert SELF_REPORTING_IDS


@pytest.mark.parametrize("rule_id", SELF_REPORTING_IDS)
def test_a_self_reporting_rule_really_speaks_on_an_empty_repository(
    rule_id: str, tmp_path: Path
) -> None:
    """The gate on the one declaration that names no input.

    ``ReportsItsOwnAbsence`` credits a rule as evaluated without naming an input,
    so an author could use it to manufacture coverage for a rule that silently
    skips. Measuring it -- run the rule against an empty repo, demand at least one
    finding -- makes that unavailable: the false claim turns this test red.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    ctx = build_context(tmp_path)
    findings = list(BY_ID[rule_id].rule(ctx))
    assert findings, (
        f"{rule_id} declares ReportsItsOwnAbsence but returned no finding against "
        "an empty repository -- its silence IS ambiguous, so it needs a Requirement"
    )


# --- the migration counter ---------------------------------------------------


def test_every_registered_rule_declares_its_coverage() -> None:
    """The migration's exit condition: no rule is left in UNDECLARED.

    Advisory, not fail-closed: this asserts the DECLARATIONS exist, which is a
    property of the source. It says nothing about whether a rule's input happens to
    be present in this repo -- `unevaluable` is a legitimate, honest state, and
    turning it into a build failure is Phase 3 and needs an owner ruling.
    """
    undeclared = [r.id for r in all_rules() if not r.requires]
    assert undeclared == [], f"rules still undeclared: {undeclared}"


def test_the_live_census_covers_the_registry_and_credits_nothing_undeclared() -> None:
    records = coverage_census(all_rules(), build_context(REPO_ROOT))
    assert {r.rule_id for r in records} == set(BY_ID)
    assert [r.rule_id for r in records if r.state is CoverageState.UNDECLARED] == []


def test_every_declared_requirement_names_an_input_or_claims_none() -> None:
    """No declaration is an empty gesture: each carries a target or the claim."""
    for registered in all_rules():
        for declaration in registered.requires:
            if isinstance(declaration, ReportsItsOwnAbsence):
                assert declaration.note.strip(), registered.id
            else:
                assert isinstance(declaration, Requirement)
                assert declaration.target, registered.id
