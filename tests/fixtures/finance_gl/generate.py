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
    """One row per quarter x P&L account x department x budget version."""
    departments = sorted({center.department_code for center in _cost_centers()})
    rows: list[tuple[object, ...]] = []
    for period in _periods():
        for account in _pl_accounts(accounts):
            for department in departments:
                for version in BUDGET_VERSIONS:
                    rows.append(
                        (
                            period.fiscal_year,
                            period.fiscal_quarter,
                            account.account_code,
                            department,
                            version,
                            CURRENCY,
                            f"{_money(rng, 1_000, 200_000):.2f}",
                        )
                    )
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


def generate(output_dir: Path, variant: str = "clean") -> dict[str, Path]:
    """Write the five sources for ``variant`` into ``output_dir``.

    Only ``clean`` exists today. Defect variants (D1-D7, D10, D12) arrive with spec 137
    task T027; an unknown or not-yet-implemented name raises rather than silently
    falling back to clean.
    """
    if variant != "clean":
        raise VariantNotAvailableError(
            f"variant {variant!r} is not available; only 'clean' is implemented "
            "(defect variants land with spec 137 task T027)"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    rng = Random(SEED)
    accounts = _accounts()
    cost_centers = _cost_centers()
    periods = _periods()

    written: dict[str, Path] = {}

    actuals = output_dir / "finance_gl_actuals.csv"
    _write(
        actuals,
        (
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
        _actual_rows(rng, accounts, cost_centers),
    )
    written["finance_gl_actuals"] = actuals

    budget = output_dir / "finance_gl_budget.csv"
    _write(
        budget,
        (
            "fiscal_year",
            "fiscal_quarter",
            "account_code",
            "department_code",
            "budget_version",
            "currency_code",
            "budget_amount",
        ),
        _budget_rows(rng, accounts),
    )
    written["finance_gl_budget"] = budget

    accounts_path = output_dir / "accounts.csv"
    _write(
        accounts_path,
        (
            "account_code",
            "account_name",
            "account_type",
            "parent_account_code",
            "sign_convention_note",
        ),
        sorted(
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
    )
    written["accounts"] = accounts_path

    departments_path = output_dir / "departments.csv"
    _write(
        departments_path,
        ("department_code", "department_name", "cost_center_code", "cost_center_name"),
        sorted(
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
    )
    written["departments"] = departments_path

    calendar_path = output_dir / "fiscal_calendar.csv"
    _write(
        calendar_path,
        ("fiscal_year", "fiscal_quarter", "period_start_date", "period_end_date"),
        [
            (
                p.fiscal_year,
                p.fiscal_quarter,
                p.period_start_date.isoformat(),
                p.period_end_date.isoformat(),
            )
            for p in periods
        ],
    )
    written["fiscal_calendar"] = calendar_path

    return written
