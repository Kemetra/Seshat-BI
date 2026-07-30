"""Deterministic, offline synthetic Finance GL source generator (spec 137, Slice A).

Emits the five clean sources the finance worked example profiles:
``finance_gl_actuals``, ``finance_gl_budget``, ``accounts``, ``departments``,
``fiscal_calendar``.

This is a TEST FIXTURE utility, not a product surface: it adds no CLI verb, is not
exported from the ``seshat`` package, and nothing under ``src/`` imports it.

Determinism contract -- see this feature's ``contracts/generator-contract.md``:
one seeded PRNG, no clock, no uuid4, no environment reads, no network, no
database; ``Decimal`` amounts quantized to 2dp with a fixed format; explicit row
sort orders; ``\\n`` newlines written explicitly. Generating twice yields byte-identical
files.

Fixture design note -- the offsetting side. Every journal entry must balance
(sum of debits == sum of credits) while the example stays P&L-flow only
(balance-sheet snapshot grain belongs to spec 091). A P&L account alone cannot
balance an entry, so each entry pairs its P&L line with one line on a dedicated
CLEARING account. Clearing accounts carry ``account_type='CLEARING'`` so they are
identifiable, and excluding them from P&L reporting is a mapping-stage EXCLUSION
DECISION recorded in the example's artifacts -- not a silent filter applied here.
No balance is ever derived from them.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from itertools import product
from pathlib import Path
from random import Random

SEED = 20260730
FISCAL_YEARS = (2024, 2025)
CURRENCY = "USD"
CLEARING_TYPE = "CLEARING"
ENTRIES_PER_YEAR = 1250  # 2 lines per entry -> ~5,000 journal lines over two years
BUDGET_VERSIONS = ("ORIGINAL", "REVISION-1")
_TWO_PLACES = Decimal("0.01")


class VariantNotAvailableError(ValueError):
    """A requested variant name is unknown or not implemented yet."""


@dataclass(frozen=True)
class Account:
    account_code: str
    account_name: str
    account_type: str
    parent_account_code: str
    sign_convention_note: str


@dataclass(frozen=True)
class CostCenter:
    department_code: str
    department_name: str
    cost_center_code: str
    cost_center_name: str


@dataclass(frozen=True)
class Period:
    fiscal_year: int
    fiscal_quarter: int
    period_start_date: date
    period_end_date: date


def _accounts() -> tuple[Account, ...]:
    """Thirty accounts: 6 revenue, 6 COGS, 16 opex, 2 clearing. Not randomised."""
    rows: list[Account] = []
    groups = (
        (
            "REVENUE",
            "4000",
            6,
            "Revenue is credited; presentation sign is an OPEN decision",
        ),
        ("COGS", "5000", 6, "Cost of sales is debited"),
        ("OPEX", "6000", 16, "Operating expense is debited"),
    )
    for account_type, base, count, note in groups:
        parent = f"{base}"
        rows.append(
            Account(
                account_code=parent,
                account_name=f"{account_type.title()} -- total",
                account_type=account_type,
                parent_account_code="",
                sign_convention_note=note,
            )
        )
        for index in range(1, count):
            rows.append(
                Account(
                    account_code=f"{int(base) + index * 10}",
                    account_name=f"{account_type.title()} detail {index}",
                    account_type=account_type,
                    parent_account_code=parent,
                    sign_convention_note=note,
                )
            )
    for index, name in enumerate(
        ("Clearing -- payables", "Clearing -- receipts"), start=0
    ):
        rows.append(
            Account(
                account_code=f"{1900 + index * 10}",
                account_name=name,
                account_type=CLEARING_TYPE,
                parent_account_code="",
                sign_convention_note=(
                    "Offsetting side only; excluded from P&L by mapping decision"
                ),
            )
        )
    return tuple(rows)


def _cost_centers() -> tuple[CostCenter, ...]:
    """Six departments, eight cost centers total (two departments carry two)."""
    plan = (
        ("D10", "Sales", ("Field", "Inside")),
        ("D20", "Marketing", ("Brand",)),
        ("D30", "Operations", ("Fulfilment", "Support")),
        ("D40", "Finance", ("Accounting",)),
        ("D50", "Technology", ("Platform",)),
        ("D60", "People", ("HR",)),
    )
    rows: list[CostCenter] = []
    for dept_code, dept_name, centers in plan:
        for index, center in enumerate(centers, start=1):
            rows.append(
                CostCenter(
                    department_code=dept_code,
                    department_name=dept_name,
                    cost_center_code=f"{dept_code}-C{index}",
                    cost_center_name=center,
                )
            )
    return tuple(rows)


def _periods() -> tuple[Period, ...]:
    """Calendar-aligned quarters -- a recorded fixture simplification only.

    It is not a claim that finance calendars are calendar-aligned in general.
    """
    bounds = ((1, 1, 3, 31), (4, 1, 6, 30), (7, 1, 9, 30), (10, 1, 12, 31))
    return tuple(
        Period(
            fiscal_year=year,
            fiscal_quarter=quarter,
            period_start_date=date(year, start_month, start_day),
            period_end_date=date(year, end_month, end_day),
        )
        for year in FISCAL_YEARS
        for quarter, (start_month, start_day, end_month, end_day) in enumerate(
            bounds, start=1
        )
    )


def _money(rng: Random, low: int, high: int) -> Decimal:
    """A two-place Decimal drawn deterministically from the seeded PRNG."""
    cents = rng.randint(low * 100, high * 100)
    return (Decimal(cents) / Decimal(100)).quantize(_TWO_PLACES)


def _pl_accounts(accounts: tuple[Account, ...]) -> tuple[Account, ...]:
    return tuple(a for a in accounts if a.account_type != CLEARING_TYPE)


def _write(path: Path, header: tuple[str, ...], rows: list[tuple[object, ...]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _actual_rows(
    rng: Random,
    accounts: tuple[Account, ...],
    cost_centers: tuple[CostCenter, ...],
) -> list[tuple[object, ...]]:
    """Two lines per entry: one P&L line plus its offsetting clearing line.

    Posting dates stay inside the fiscal year they are drawn for, and the calendar in
    ``_periods`` covers every day of both years, so every row lands in exactly one
    declared period by construction (variant D4 breaks that deliberately).
    """
    postable = _pl_accounts(accounts)
    clearing = tuple(a for a in accounts if a.account_type == CLEARING_TYPE)
    rows: list[tuple[object, ...]] = []
    for year in FISCAL_YEARS:
        year_start = date(year, 1, 1)
        for sequence in range(1, ENTRIES_PER_YEAR + 1):
            entry_id = f"JE-{year}-{sequence:05d}"
            posting = year_start + timedelta(days=rng.randint(0, 364))
            account = postable[rng.randrange(len(postable))]
            center = cost_centers[rng.randrange(len(cost_centers))]
            offset = clearing[rng.randrange(len(clearing))]
            amount = _money(rng, 100, 25_000)
            revenue = account.account_type == "REVENUE"
            rows.append(
                (
                    entry_id,
                    1,
                    posting.isoformat(),
                    account.account_code,
                    center.department_code,
                    center.cost_center_code,
                    CURRENCY,
                    f"{Decimal('0.00'):.2f}" if revenue else f"{amount:.2f}",
                    f"{amount:.2f}" if revenue else f"{Decimal('0.00'):.2f}",
                    f"{account.account_name} activity",
                )
            )
            rows.append(
                (
                    entry_id,
                    2,
                    posting.isoformat(),
                    offset.account_code,
                    center.department_code,
                    center.cost_center_code,
                    CURRENCY,
                    f"{amount:.2f}" if revenue else f"{Decimal('0.00'):.2f}",
                    f"{Decimal('0.00'):.2f}" if revenue else f"{amount:.2f}",
                    "Offsetting clearing line",
                )
            )
    rows.sort(key=lambda row: (str(row[0]), int(row[1])))
    return rows


def _budget_rows(
    rng: Random, accounts: tuple[Account, ...]
) -> list[tuple[object, ...]]:
    """One row per quarter x P&L account x department x budget version.

    ``product`` iterates its rightmost factor fastest, which is the same order as the
    equivalent nested loops -- so the sequence of PRNG draws, and therefore every
    amount, is unchanged by expressing it this way.
    """
    departments = sorted({center.department_code for center in _cost_centers()})
    combinations = product(
        _periods(), _pl_accounts(accounts), departments, BUDGET_VERSIONS
    )
    rows: list[tuple[object, ...]] = [
        (
            period.fiscal_year,
            period.fiscal_quarter,
            account.account_code,
            department,
            version,
            CURRENCY,
            f"{_money(rng, 1_000, 200_000):.2f}",
        )
        for period, account, department, version in combinations
    ]
    rows.sort(
        key=lambda row: (
            int(row[0]),
            int(row[1]),
            str(row[2]),
            str(row[3]),
            str(row[4]),
        )
    )
    return rows


# -----------------------------------------------------------------------------
# Source table headers -- written column order is part of the determinism contract.
# -----------------------------------------------------------------------------
HEADERS: dict[str, tuple[str, ...]] = {
    "finance_gl_actuals": (
        "journal_entry_id",
        "line_id",
        "posting_date",
        "account_code",
        "department_code",
        "cost_center_code",
        "currency_code",
        "debit_amount",
        "credit_amount",
        "description",
    ),
    "finance_gl_budget": (
        "fiscal_year",
        "fiscal_quarter",
        "account_code",
        "department_code",
        "budget_version",
        "currency_code",
        "budget_amount",
    ),
    "accounts": (
        "account_code",
        "account_name",
        "account_type",
        "parent_account_code",
        "sign_convention_note",
    ),
    "departments": (
        "department_code",
        "department_name",
        "cost_center_code",
        "cost_center_name",
    ),
    "fiscal_calendar": (
        "fiscal_year",
        "fiscal_quarter",
        "period_start_date",
        "period_end_date",
    ),
}

# Column index shortcuts, used by the variant mutations below.
_A = {name: i for i, name in enumerate(HEADERS["finance_gl_actuals"])}
_B = {name: i for i, name in enumerate(HEADERS["finance_gl_budget"])}
_BUDGET_GROUP = ("fiscal_year", "fiscal_quarter", "account_code", "department_code")


def _reference_rows(
    accounts: tuple[Account, ...], cost_centers: tuple[CostCenter, ...]
) -> dict[str, list[tuple[object, ...]]]:
    """The three reference sources. These draw nothing from the PRNG."""
    return {
        "accounts": sorted(
            (
                (
                    a.account_code,
                    a.account_name,
                    a.account_type,
                    a.parent_account_code,
                    a.sign_convention_note,
                )
                for a in accounts
            ),
            key=lambda row: str(row[0]),
        ),
        "departments": sorted(
            (
                (
                    c.department_code,
                    c.department_name,
                    c.cost_center_code,
                    c.cost_center_name,
                )
                for c in cost_centers
            ),
            key=lambda row: (str(row[0]), str(row[2])),
        ),
        "fiscal_calendar": [
            (
                p.fiscal_year,
                p.fiscal_quarter,
                p.period_start_date.isoformat(),
                p.period_end_date.isoformat(),
            )
            for p in _periods()
        ],
    }


def build_clean() -> dict[str, list[tuple[object, ...]]]:
    """Build every clean source in memory, before any variant mutation.

    PRNG DRAW ORDER IS PART OF THE DETERMINISM CONTRACT: actuals consume the shared
    ``rng`` before budget does. Swapping these two statements changes every budget
    amount. The reference sources draw nothing.
    """
    rng = Random(SEED)
    accounts = _accounts()
    cost_centers = _cost_centers()
    sources: dict[str, list[tuple[object, ...]]] = {
        "finance_gl_actuals": _actual_rows(rng, accounts, cost_centers),
    }
    sources["finance_gl_budget"] = _budget_rows(rng, accounts)
    sources.update(_reference_rows(accounts, cost_centers))
    return sources


# -----------------------------------------------------------------------------
# Defect variants (spec 137 Slice B, task T027).
#
# Each mutation is DETERMINISTIC (fixed row positions, never a PRNG draw) and changes
# the clean fixture in EXACTLY ONE respect, so an observed governance outcome
# attributes to a single cause (spec 137 FR-006). Variants that are NOT data states --
# a question about presentation, or an action a human attempts -- are declared as
# benchmark scenarios instead; contracts/fixture-schema.md says which is which.
# -----------------------------------------------------------------------------
UNKNOWN_ACCOUNT = "9999"
UNKNOWN_DEPARTMENT = "D99"
FOREIGN_CURRENCY = "EUR"
OUT_OF_PERIOD_DATE = "2023-12-31"
AMBIGUOUS_VERSIONS = ("PLAN-A", "PLAN-B")
_MIXED_CURRENCY_ROWS = 50


def _set(
    rows: list[tuple[object, ...]], index: int, column: int, value: object
) -> None:
    """Replace one cell, preserving the row's tuple shape."""
    row = list(rows[index])
    row[column] = value
    rows[index] = tuple(row)


def _budget_key(row: tuple[object, ...]) -> tuple[object, ...]:
    """The 4-part group key (the PK without budget_version)."""
    return tuple(row[_B[name]] for name in _BUDGET_GROUP)


def _d1_unknown_account(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """An actuals line references an account absent from accounts.csv."""
    _set(sources["finance_gl_actuals"], 0, _A["account_code"], UNKNOWN_ACCOUNT)


def _d2_unknown_department(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """An actuals line references a department absent from departments.csv."""
    _set(sources["finance_gl_actuals"], 0, _A["department_code"], UNKNOWN_DEPARTMENT)


def _d3_irreconcilable_hierarchy(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """A budget row is set against a CLEARING account.

    Clearing accounts are not P&L and are never budgeted, so this budget row cannot be
    reconciled to any P&L actuals hierarchy path.
    """
    clearing = next(
        a.account_code for a in _accounts() if a.account_type == CLEARING_TYPE
    )
    _set(sources["finance_gl_budget"], 0, _B["account_code"], clearing)


def _d4_out_of_period_date(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """One posting_date falls outside every declared fiscal period."""
    _set(sources["finance_gl_actuals"], 0, _A["posting_date"], OUT_OF_PERIOD_DATE)


def _d5_mixed_currency(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """A block of actuals lines is denominated in a second currency."""
    rows = sources["finance_gl_actuals"]
    for index in range(_MIXED_CURRENCY_ROWS):
        _set(rows, index, _A["currency_code"], FOREIGN_CURRENCY)


def _d6_duplicate_line_id(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """Two rows share the declared composite PK (journal_entry_id, line_id)."""
    rows = sources["finance_gl_actuals"]
    _set(rows, 1, _A["journal_entry_id"], rows[0][_A["journal_entry_id"]])
    _set(rows, 1, _A["line_id"], rows[0][_A["line_id"]])


def _d7_budget_grain_violation(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """A second budget row shares the full 5-part PK with a different amount."""
    rows = sources["finance_gl_budget"]
    original = rows[0]
    bumped = Decimal(str(original[_B["budget_amount"]])) + Decimal("1.00")
    duplicate = list(original)
    duplicate[_B["budget_amount"]] = f"{bumped:.2f}"
    rows.insert(1, tuple(duplicate))


def _d10_ambiguous_baseline(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """Both budget versions are renamed so neither reads as the plan of record.

    The clean fixture's ORIGINAL / REVISION-1 pair makes the baseline obvious. Renaming
    to PLAN-A / PLAN-B removes that cue, leaving a genuine ambiguity a human must
    resolve rather than one the names answer.
    """
    rows = sources["finance_gl_budget"]
    rename = dict(zip(BUDGET_VERSIONS, AMBIGUOUS_VERSIONS, strict=True))
    for index, row in enumerate(rows):
        current = str(row[_B["budget_version"]])
        _set(rows, index, _B["budget_version"], rename[current])


def _d12_actuals_without_budget(sources: dict[str, list[tuple[object, ...]]]) -> None:
    """Every budget row for ONE (year, quarter, account, department) group is removed.

    Actuals for that group remain, so the combination has activity and no plan. This is
    a LEGITIMATE business state, not a defect: the expected governed outcome is
    ``proceed``, with the gap surfaced as a report exception. It is the deliberate
    over-refusal trap (spec 137 FR-023).
    """
    rows = sources["finance_gl_budget"]
    dropped = _budget_key(rows[0])
    rows[:] = [row for row in rows if _budget_key(row) != dropped]


VARIANTS: dict[str, object] = {
    "clean": None,
    "D1": _d1_unknown_account,
    "D2": _d2_unknown_department,
    "D3": _d3_irreconcilable_hierarchy,
    "D4": _d4_out_of_period_date,
    "D5": _d5_mixed_currency,
    "D6": _d6_duplicate_line_id,
    "D7": _d7_budget_grain_violation,
    "D10": _d10_ambiguous_baseline,
    "D12": _d12_actuals_without_budget,
}

# Declared in contracts/fixture-schema.md as scenario-expressed rather than data
# variants: a framing question or an attempted action has no data state to perturb.
SCENARIO_ONLY_VARIANTS = ("D8", "D9", "D11", "D13")


def generate(output_dir: Path, variant: str = "clean") -> dict[str, Path]:
    """Write the five sources for ``variant`` into ``output_dir``.

    ``clean`` plus the data-expressible defect variants in ``VARIANTS``. A name in
    ``SCENARIO_ONLY_VARIANTS`` raises with a pointer to the benchmark scenario file, and
    an unknown name raises -- neither ever silently falls back to clean.
    """
    if variant in SCENARIO_ONLY_VARIANTS:
        raise VariantNotAvailableError(
            f"variant {variant!r} is scenario-expressed, not a data state; it is "
            "declared in benchmark/scenarios/finance-gl-judgment.yaml, not here"
        )
    if variant not in VARIANTS:
        known = ", ".join(sorted(k for k in VARIANTS if k != "clean"))
        raise VariantNotAvailableError(
            f"variant {variant!r} is not available; known data variants are {known}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    sources = build_clean()
    mutate = VARIANTS[variant]
    if mutate is not None:
        mutate(sources)

    written: dict[str, Path] = {}
    for name, header in HEADERS.items():
        path = output_dir / f"{name}.csv"
        _write(path, header, sources[name])
        written[name] = path
    return written
