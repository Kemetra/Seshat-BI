"""Advisory column-shape comparison: shadow model vs its migrations counterpart.

WHY THIS IS NOT A PARITY ASSERTION (issue #492)
-----------------------------------------------
The reconciliation parity test asserts FOUR value classes -- ``fact_row_count``,
``business_key_count``, ``additive_money_total``, ``dimension_member_count``.
Those four are the WHOLE contract: ADR-0009 decision 5 enumerates them, and the
``assertion_class`` enum in ``schemas/dbt-run-evidence.schema.json`` is CLOSED to
exactly them (``evidence._parity_assertion`` fail-closes on a fifth). All four are
row-cardinality / SUM assertions, so a shadow model can gain, lose, or rename a
column and every assertion still passes with delta 0 -- the observed live case was
a date dimension whose shadow shape carried two extra columns while its member
count matched exactly (1096 = 1096).

This module closes that blind spot WITHOUT becoming a fifth assertion. A drift
finding here is ADVISORY: it is rendered to the operator, it never enters the run
evidence JSON, it never lands in ``blocking_reasons``, and it never changes an
exit code. That is deliberate, not a shortcut -- an intentional shadow-only column
is legitimate during a migration (the shadow star is allowed to lead), so drift
must be VISIBLE without being a failure. Making it blocking would either edit a
ratified contract or convert a legal migration state into a hard stop.

WHAT IS COMPARED
----------------
Shadow side: the governed ``ModelContract.columns`` that ``project.validate_project``
already parsed from the committed ``_models.yml`` -- the DECLARED contract for what
the model emits, not a re-parse of skeleton SQL. (The generated ``.sql`` files are
skeletons an operator completes by hand; the plan's pre-completion column list is
therefore NOT the shadow shape.)

Migrations side: the ``CREATE TABLE <schema>.<name> (...)`` column list in the
committed ``warehouse/migrations/*.sql`` -- the parity oracle's shape.

FAIL-SAFE, NOT FAIL-CLOSED
--------------------------
Every uncertainty resolves to NO FINDING: no migrations directory, an unreadable
file, a model with no counterpart DDL (a shadow-only star that migrations never
built), or a ``CREATE TABLE`` this narrow parser cannot read confidently. An
advisory that cried wolf on an unparseable comment would be worse than silence,
and a missing counterpart is a normal state, not a defect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# One `CREATE TABLE [IF NOT EXISTS] <schema>.<table> ( ... );` body. Non-greedy to
# the first `);` that closes the definition, so consecutive CREATEs in one
# migration do not bleed into each other.
_CREATE_TABLE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?"
    r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?(?P<table>[a-z_][a-z0-9_]*)\s*"
    r"\((?P<body>.*?)\n\s*\)\s*;",
    re.IGNORECASE | re.DOTALL,
)

# A table-level constraint / index clause, not a column. `PRIMARY KEY (a, b)` and
# friends open a definition body line the same way a column does, so the leading
# keyword is what distinguishes them.
_TABLE_CONSTRAINT = re.compile(
    r"^(?:constraint|primary\s+key|foreign\s+key|unique|check|exclude|like)\b",
    re.IGNORECASE,
)

_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")

_MIGRATIONS_DIR = "warehouse/migrations"


@dataclass(frozen=True, slots=True)
class ColumnShapeAdvisory:
    """One shadow/migrations column-shape divergence for one model pair.

    Deliberately NOT shaped like a parity assertion and NOT shaped like a
    ``Blocker``: no ``assertion_class``, no ``assertion_id``, no ``passed``, and no
    ``DBT_[A-Z0-9_]+`` code. Those vocabularies belong to the closed parity enum
    and the blocking channel respectively; borrowing either would invite a reader
    to mistake this for a fifth assertion or a failure.
    """

    model: str
    migration_relpath: str
    shadow_only: tuple[str, ...]
    migrations_only: tuple[str, ...]

    def message(self) -> str:
        parts = []
        if self.shadow_only:
            parts.append(f"shadow-only {list(self.shadow_only)}")
        if self.migrations_only:
            parts.append(f"migrations-only {list(self.migrations_only)}")
        return (
            f"{self.model}: column set differs from {self.migration_relpath} "
            f"({'; '.join(parts)}). The four parity assertions are value-only and "
            "cannot see this; confirm the divergence is intended."
        )


def _split_definition_body(body: str) -> list[str]:
    """Top-level comma-separated definition lines, ignoring commas nested in
    parentheses (``NUMERIC(12,2)``, ``PRIMARY KEY (a, b)``) and `--` comments."""
    lines: list[str] = []
    current: list[str] = []
    depth = 0
    for raw_line in body.splitlines():
        line = raw_line.split("--")[0]
        for char in line:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            if char == "," and depth == 0:
                lines.append("".join(current))
                current = []
                continue
            current.append(char)
        current.append("\n")
    lines.append("".join(current))
    return lines


def _column_names(body: str) -> frozenset[str] | None:
    """Column names in one ``CREATE TABLE`` body, or None if unreadable.

    None (-> no finding) whenever the body yields no column at all or a definition
    line starts with something this parser cannot classify as a column name: a
    half-understood column set would produce a bogus symmetric difference."""
    names: list[str] = []
    for definition in _split_definition_body(body):
        text = definition.strip().strip(",").strip()
        if not text or _TABLE_CONSTRAINT.match(text):
            continue
        candidate = text.split()[0].strip('"').lower()
        if not _IDENTIFIER.match(candidate):
            return None
        names.append(candidate)
    if not names or len(set(names)) != len(names):
        return None
    return frozenset(names)


def migration_column_sets(repo_root: Path) -> dict[str, tuple[frozenset[str], str]]:
    """``{table_name: (column_names, migration_relpath)}`` for the committed
    migrations, keyed on the BARE table name (the shadow star materializes the same
    model name into its own shadow schema, so the schema qualifier cannot match).

    A table created more than once (idempotent drop/recreate, or a later migration
    reshaping it) resolves to the LAST definition in filename order -- that is the
    shape the oracle ends up with. Unreadable files are skipped, never raised."""
    directory = Path(repo_root) / _MIGRATIONS_DIR
    if not directory.is_dir():
        return {}
    found: dict[str, tuple[frozenset[str], str]] = {}
    for path in sorted(directory.glob("*.sql")):
        relpath = f"{_MIGRATIONS_DIR}/{path.name}"
        for match in _CREATE_TABLE.finditer(_read_text(path)):
            columns = _column_names(match.group("body"))
            if columns is not None:
                found[match.group("table").lower()] = (columns, relpath)
    return found


def _read_text(path: Path) -> str:
    """The file's text, or '' when unreadable -- advisory input is never fatal."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def column_shape_advisories(
    repo_root: Path, model_contracts, *, skip: frozenset[str] = frozenset()
) -> tuple[ColumnShapeAdvisory, ...]:
    """Advisory column-shape divergences between the governed shadow models and
    their migrations counterparts.

    ``skip`` names models that have no migrations counterpart BY DESIGN -- the
    parity audit model is derived evidence the migrations path never builds, so
    comparing it would report a permanent phantom divergence.

    Returns () when nothing diverges, when migrations are absent, or when a model
    has no counterpart DDL. Never raises on malformed input: this is advisory."""
    migrations = migration_column_sets(repo_root)
    if not migrations:
        return ()
    advisories: list[ColumnShapeAdvisory] = []
    for contract in model_contracts:
        if contract.name in skip:
            continue
        counterpart = migrations.get(contract.name.lower())
        if counterpart is None:
            continue
        expected, relpath = counterpart
        shadow = frozenset(column.name.lower() for column in contract.columns)
        if shadow == expected:
            continue
        advisories.append(
            ColumnShapeAdvisory(
                model=contract.name,
                migration_relpath=relpath,
                shadow_only=tuple(sorted(shadow - expected)),
                migrations_only=tuple(sorted(expected - shadow)),
            )
        )
    return tuple(advisories)
