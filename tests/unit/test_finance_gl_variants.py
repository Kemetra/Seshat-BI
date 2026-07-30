"""Spec 137 Slice B: the finance defect variants and the judgment scenarios.

Covers FR-006 (one defect per variant, deterministic), FR-021 (each variant declares one
categorical expected outcome), FR-022 (the six judgment cases live in the EXISTING
benchmark scenario format), and FR-023 (over-refusal is a failure, so the D12 trap must
expect ``proceed``).

The generator is loaded BY PATH because ``tests/`` is not a package in this repository.
The scenario file is validated through the SHIPPED loader rather than re-parsed here, so
this test cannot disagree with the runner about what a valid scenario is.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest

from seshat.benchmark.model import BEHAVIORS
from seshat.benchmark.runner import load_scenarios

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GENERATOR_PATH = _REPO_ROOT / "tests" / "fixtures" / "finance_gl" / "generate.py"
_SCENARIO_FILE = "benchmark/scenarios/finance-gl-judgment.yaml"

DATA_VARIANTS = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D10", "D12")
BUDGET_GROUP = ("fiscal_year", "fiscal_quarter", "account_code", "department_code")


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("finance_gl_gen_v", _GENERATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = _load_generator()


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def clean(tmp_path_factory: pytest.TempPathFactory) -> dict[str, list[dict[str, str]]]:
    written = generator.generate(tmp_path_factory.mktemp("fgl_clean"))
    return {name: _rows(path) for name, path in written.items()}


def _variant(tmp_path: Path, name: str) -> dict[str, list[dict[str, str]]]:
    written = generator.generate(tmp_path / name, variant=name)
    return {source: _rows(path) for source, path in written.items()}


# --------------------------------------------------------------------------- #
# shape of the variant set
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_declared_data_variants_match_the_registry() -> None:
    registry = tuple(sorted(k for k in generator.VARIANTS if k != "clean"))
    assert registry == tuple(sorted(DATA_VARIANTS))


@pytest.mark.unit
@pytest.mark.parametrize("name", DATA_VARIANTS)
def test_each_variant_touches_exactly_one_source(
    tmp_path: Path, clean: dict[str, list[dict[str, str]]], name: str
) -> None:
    """FR-006: one defect per variant, so an outcome attributes to a single cause."""
    got = _variant(tmp_path, name)
    changed = [source for source in clean if clean[source] != got[source]]
    assert len(changed) == 1, f"{name} changed {changed}"


@pytest.mark.unit
@pytest.mark.parametrize("name", DATA_VARIANTS)
def test_each_variant_is_deterministic(tmp_path: Path, name: str) -> None:
    first = generator.generate(tmp_path / f"{name}-a", variant=name)
    second = generator.generate(tmp_path / f"{name}-b", variant=name)
    for source, path in first.items():
        assert path.read_bytes() == second[source].read_bytes(), (name, source)
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == hashlib.sha256(second[source].read_bytes()).hexdigest()
        )


@pytest.mark.unit
def test_scenario_expressed_variants_raise_with_a_pointer(tmp_path: Path) -> None:
    """D8/D9/D11/D13 are framing questions, not data states."""
    for name in generator.SCENARIO_ONLY_VARIANTS:
        with pytest.raises(generator.VariantNotAvailableError) as excinfo:
            generator.generate(tmp_path / name, variant=name)
        assert "finance-gl-judgment.yaml" in str(excinfo.value), name


# --------------------------------------------------------------------------- #
# each structural variant breaks the ONE thing it claims to break
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_d1_references_an_unknown_account(tmp_path: Path) -> None:
    got = _variant(tmp_path, "D1")
    known = {row["account_code"] for row in got["accounts"]}
    orphans = {r["account_code"] for r in got["finance_gl_actuals"]} - known
    assert orphans == {generator.UNKNOWN_ACCOUNT}


@pytest.mark.unit
def test_d2_references_an_unknown_department(tmp_path: Path) -> None:
    got = _variant(tmp_path, "D2")
    known = {row["department_code"] for row in got["departments"]}
    orphans = {r["department_code"] for r in got["finance_gl_actuals"]} - known
    assert orphans == {generator.UNKNOWN_DEPARTMENT}


@pytest.mark.unit
def test_d3_budgets_a_clearing_account(tmp_path: Path) -> None:
    """A non-P&L account cannot be reconciled to any P&L actuals hierarchy path."""
    got = _variant(tmp_path, "D3")
    types = {r["account_code"]: r["account_type"] for r in got["accounts"]}
    budgeted_types = {types[r["account_code"]] for r in got["finance_gl_budget"]}
    assert generator.CLEARING_TYPE in budgeted_types


@pytest.mark.unit
def test_d4_posts_outside_every_declared_period(tmp_path: Path) -> None:
    got = _variant(tmp_path, "D4")
    periods = [
        (
            date.fromisoformat(row["period_start_date"]),
            date.fromisoformat(row["period_end_date"]),
        )
        for row in got["fiscal_calendar"]
    ]
    outside = [
        row["posting_date"]
        for row in got["finance_gl_actuals"]
        if not any(
            s <= date.fromisoformat(row["posting_date"]) <= e for s, e in periods
        )
    ]
    assert outside == [generator.OUT_OF_PERIOD_DATE]


@pytest.mark.unit
def test_d5_mixes_currencies_without_a_policy(tmp_path: Path) -> None:
    got = _variant(tmp_path, "D5")
    currencies = {row["currency_code"] for row in got["finance_gl_actuals"]}
    assert currencies == {generator.CURRENCY, generator.FOREIGN_CURRENCY}


@pytest.mark.unit
def test_d6_breaks_the_actuals_primary_key(tmp_path: Path) -> None:
    got = _variant(tmp_path, "D6")
    keys = [(r["journal_entry_id"], r["line_id"]) for r in got["finance_gl_actuals"]]
    assert len(keys) != len(set(keys))


@pytest.mark.unit
def test_d7_breaks_the_budget_primary_key(tmp_path: Path) -> None:
    got = _variant(tmp_path, "D7")
    keys = [
        tuple(r[c] for c in (*BUDGET_GROUP, "budget_version"))
        for r in got["finance_gl_budget"]
    ]
    assert len(keys) != len(set(keys))


# --------------------------------------------------------------------------- #
# the two judgment variants that DO have a data shape
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_d10_removes_the_baseline_cue(tmp_path: Path) -> None:
    """Neither version name should read as the plan of record."""
    got = _variant(tmp_path, "D10")
    versions = {row["budget_version"] for row in got["finance_gl_budget"]}
    assert versions == set(generator.AMBIGUOUS_VERSIONS)
    assert not versions & set(generator.BUDGET_VERSIONS)


@pytest.mark.unit
def test_d12_leaves_actuals_with_no_budget_row(tmp_path: Path) -> None:
    """The over-refusal trap: a LEGITIMATE state, so the gate must not refuse it."""
    got = _variant(tmp_path, "D12")
    types = {r["account_code"]: r["account_type"] for r in got["accounts"]}

    def group(row: dict[str, str], date_key: str | None = None) -> tuple[str, ...]:
        if date_key:
            month = int(row[date_key][5:7])
            return (
                row[date_key][:4],
                str((month - 1) // 3 + 1),
                row["account_code"],
                row["department_code"],
            )
        return tuple(row[c] for c in BUDGET_GROUP)

    budgeted = {group(r) for r in got["finance_gl_budget"]}
    actual_pl = {
        group(r, "posting_date")
        for r in got["finance_gl_actuals"]
        if types[r["account_code"]] != generator.CLEARING_TYPE
    }
    unbudgeted = actual_pl - budgeted
    assert unbudgeted, "D12 must leave at least one P&L combination with no budget row"


# --------------------------------------------------------------------------- #
# the judgment scenarios, validated by the SHIPPED loader
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_judgment_scenarios_load_and_validate() -> None:
    """FR-022: the existing format, validated by the existing fail-closed loader."""
    scenarios = load_scenarios(_REPO_ROOT, _SCENARIO_FILE)
    assert len(scenarios) == 6
    for scenario in scenarios:
        assert scenario.expected_behavior in BEHAVIORS
        assert scenario.observable_evidence
        assert scenario.scenario_id.startswith("fgl-")


@pytest.mark.unit
def test_judgment_scenarios_include_the_over_refusal_trap() -> None:
    """FR-023: at least one scenario must expect `proceed`.

    A scenario set with no legitimate-request case can only ever measure refusal, so a
    gate that blocks everything would score perfectly. The `proceed` case is what makes
    over-refusal observable.
    """
    scenarios = load_scenarios(_REPO_ROOT, _SCENARIO_FILE)
    by_behavior: dict[str, list[str]] = {}
    for scenario in scenarios:
        by_behavior.setdefault(scenario.expected_behavior, []).append(
            scenario.scenario_id
        )

    assert by_behavior.get("proceed") == ["fgl-actuals-without-budget-row"]
    assert "refuse" in by_behavior
    assert "request_human_decision" in by_behavior


@pytest.mark.unit
def test_no_scenario_expects_a_numeric_score() -> None:
    """Hard rule #9: nothing in the scenario set may ask for a confidence number."""
    text = (_REPO_ROOT / _SCENARIO_FILE).read_text(encoding="utf-8").lower()
    for banned in ("confidence score", "health score", "readiness score", "0-100"):
        assert banned not in text, banned
