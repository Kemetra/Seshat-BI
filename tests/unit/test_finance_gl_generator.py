"""Spec 137 Slice A: the Finance GL fixture generator is deterministic and well-formed.

Covers spec 137 FR-001 (offline, seeded), FR-002 / SC-002 (byte-identical regeneration),
FR-003 (five sources), FR-004 (no real/personal data), FR-006 (unknown variant raises),
FR-007 / FR-008 (declared grains and PKs), plus the data-model validation rules.

The generator is loaded BY PATH because ``tests/`` is not a package in this repository.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

_GENERATOR_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "finance_gl" / "generate.py"
)


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "finance_gl_generate", _GENERATOR_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = _load_generator()

EXPECTED_SOURCES = (
    "finance_gl_actuals",
    "finance_gl_budget",
    "accounts",
    "departments",
    "fiscal_calendar",
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def clean(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    return generator.generate(tmp_path_factory.mktemp("finance_gl_clean"))


@pytest.mark.unit
def test_generate_emits_the_five_declared_sources(clean: dict[str, Path]) -> None:
    assert tuple(sorted(clean)) == tuple(sorted(EXPECTED_SOURCES))
    for path in clean.values():
        assert path.is_file()
        assert path.stat().st_size > 0


@pytest.mark.unit
def test_regeneration_is_byte_identical(tmp_path: Path) -> None:
    """SC-002: verified by comparison, not asserted about the code."""
    first = generator.generate(tmp_path / "first")
    second = generator.generate(tmp_path / "second")

    assert sorted(first) == sorted(second)
    for name in first:
        assert first[name].read_bytes() == second[name].read_bytes(), name
        assert _digest(first[name]) == _digest(second[name]), name


@pytest.mark.unit
def test_committed_excerpts_match_the_generated_head(clean: dict[str, Path]) -> None:
    """The committed samples must stay a true prefix of the generated output.

    Excerpts exist because the full ~425 KB actuals file is git-ignored (spec 137
    research R3). If the generator changes and the excerpts are not refreshed, every
    document citing them becomes quietly wrong -- so this is a guard, not a nicety.
    ``.gitattributes`` pins these paths to ``eol=lf`` so the comparison holds on
    Windows checkouts too.
    """
    excerpts = _GENERATOR_PATH.parent / "excerpts"
    for name in ("finance_gl_actuals", "finance_gl_budget"):
        committed = (excerpts / f"{name}.head.csv").read_text(encoding="utf-8")
        expected_lines = len(committed.splitlines())
        generated = clean[name].read_text(encoding="utf-8").splitlines()
        assert committed == "\n".join(generated[:expected_lines]) + "\n", name


@pytest.mark.unit
def test_newlines_are_lf_only(clean: dict[str, Path]) -> None:
    for name, path in clean.items():
        assert b"\r\n" not in path.read_bytes(), name


@pytest.mark.unit
def test_unknown_variant_raises_rather_than_falling_back(tmp_path: Path) -> None:
    with pytest.raises(generator.VariantNotAvailableError):
        generator.generate(tmp_path / "bogus", variant="not-a-variant")
    with pytest.raises(generator.VariantNotAvailableError):
        generator.generate(tmp_path / "d1", variant="D1")


@pytest.mark.unit
def test_actuals_declared_pk_is_unique(clean: dict[str, Path]) -> None:
    """FR-007: (journal_entry_id, line_id) is the declared PK."""
    rows = _rows(clean["finance_gl_actuals"])
    keys = [(row["journal_entry_id"], row["line_id"]) for row in rows]
    assert len(keys) == len(set(keys))
    assert len(rows) >= 4_000  # ~5,000 journal lines at the declared shape


@pytest.mark.unit
def test_budget_declared_pk_is_unique_and_carries_version(
    clean: dict[str, Path],
) -> None:
    """FR-008 / FR-011: version is part of budget identity, not a mutable attribute."""
    rows = _rows(clean["finance_gl_budget"])
    keys = [
        (
            row["fiscal_year"],
            row["fiscal_quarter"],
            row["account_code"],
            row["department_code"],
            row["budget_version"],
        )
        for row in rows
    ]
    assert len(keys) == len(set(keys))
    assert len({row["budget_version"] for row in rows}) >= 2


@pytest.mark.unit
def test_every_journal_entry_balances(clean: dict[str, Path]) -> None:
    """data-model validation rule 2, and rule 1 (exactly one side non-zero per line)."""
    debits: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    credits: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for row in _rows(clean["finance_gl_actuals"]):
        debit = Decimal(row["debit_amount"])
        credit = Decimal(row["credit_amount"])
        assert debit >= 0 and credit >= 0
        assert (debit == 0) != (credit == 0), row
        debits[row["journal_entry_id"]] += debit
        credits[row["journal_entry_id"]] += credit

    assert debits and debits.keys() == credits.keys()
    for entry_id, total_debit in debits.items():
        assert total_debit == credits[entry_id], entry_id


@pytest.mark.unit
def test_reference_keys_close(clean: dict[str, Path]) -> None:
    """FR-009 groundwork: no actuals row references an unknown code.

    Broken references are variants D1 and D2.
    """
    accounts = {row["account_code"] for row in _rows(clean["accounts"])}
    departments = _rows(clean["departments"])
    department_codes = {row["department_code"] for row in departments}
    centers = {(row["department_code"], row["cost_center_code"]) for row in departments}

    for row in _rows(clean["finance_gl_actuals"]):
        assert row["account_code"] in accounts, row["account_code"]
        assert row["department_code"] in department_codes, row["department_code"]
        assert (row["department_code"], row["cost_center_code"]) in centers, row

    for row in _rows(clean["finance_gl_budget"]):
        assert row["account_code"] in accounts, row["account_code"]
        assert row["department_code"] in department_codes, row["department_code"]


@pytest.mark.unit
def test_every_posting_date_falls_in_exactly_one_declared_period(
    clean: dict[str, Path],
) -> None:
    """data-model validation rule 4 (variant D4 breaks this deliberately)."""
    periods = [
        (
            date.fromisoformat(row["period_start_date"]),
            date.fromisoformat(row["period_end_date"]),
        )
        for row in _rows(clean["fiscal_calendar"])
    ]
    assert len(periods) == 8  # two fiscal years x four quarters

    for row in _rows(clean["finance_gl_actuals"]):
        posting = date.fromisoformat(row["posting_date"])
        matches = [1 for start, end in periods if start <= posting <= end]
        assert len(matches) == 1, row["posting_date"]


@pytest.mark.unit
def test_clean_fixture_is_single_currency(clean: dict[str, Path]) -> None:
    """Mixed currency is isolated to variant D5; the clean set is single-currency."""
    currencies = {row["currency_code"] for row in _rows(clean["finance_gl_actuals"])}
    currencies |= {row["currency_code"] for row in _rows(clean["finance_gl_budget"])}
    assert currencies == {generator.CURRENCY}


@pytest.mark.unit
def test_declared_shape_bounds_are_met(clean: dict[str, Path]) -> None:
    """FR-005: ~2 fiscal years, 30 accounts, 6 departments, 4-8 cost centers."""
    accounts = _rows(clean["accounts"])
    departments = _rows(clean["departments"])
    calendar = _rows(clean["fiscal_calendar"])

    assert len(accounts) == 30
    assert len({row["department_code"] for row in departments}) == 6
    assert 4 <= len({row["cost_center_code"] for row in departments}) <= 8
    assert len({row["fiscal_year"] for row in calendar}) == 2


@pytest.mark.unit
def test_amounts_are_two_place_decimals(clean: dict[str, Path]) -> None:
    for row in _rows(clean["finance_gl_actuals"]):
        for column in ("debit_amount", "credit_amount"):
            assert row[column] == f"{Decimal(row[column]):.2f}", row[column]
    for row in _rows(clean["finance_gl_budget"]):
        assert row["budget_amount"] == f"{Decimal(row['budget_amount']):.2f}"


@pytest.mark.unit
def test_generator_reads_no_clock_network_or_uuid_source() -> None:
    """FR-001: determinism is structural, so the forbidden sources must be absent.

    Checked against the parsed AST rather than the raw text -- the module's own
    docstring names these sources in order to disclaim them, and a substring scan
    would flag that prose instead of real usage.
    """
    tree = ast.parse(_GENERATOR_PATH.read_text(encoding="utf-8"))
    referenced = {
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Attribute, ast.Name))
    }
    forbidden = {
        "datetime.now",
        "datetime.utcnow",
        "date.today",
        "uuid4",
        "uuid.uuid4",
        "time.time",
        "os.environ",
        "os.getenv",
        "requests.get",
    }
    assert not (referenced & forbidden), sorted(referenced & forbidden)

    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    # No network, no db driver, no uuid, no time-of-day source imported at all.
    assert not (
        imported & {"uuid", "time", "socket", "urllib", "requests", "psycopg2", "os"}
    )
    # The module-level `random` API would bypass the seeded instance.
    assert "random" in imported  # `from random import Random`
    assert "random" not in {
        ast.unparse(node) for node in ast.walk(tree) if isinstance(node, ast.Name)
    }
