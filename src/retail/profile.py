"""Mechanical profiling of a landed (bronze) source table.

The source-mapping gate's first artifact (source-profile.md) rests on numbers,
not adjectives. This helper computes the MECHANICAL ones -- row/col count,
per-column ''OR NULL missingness, distinct cardinality, and the candidate-PK
uniqueness proof on the landed data. Semantic profiling (code<->label 1:1,
dimension fan-out, the authoritative returns column) needs the table's MEANING
and is a Principle-V judgment call -- the agent proposes it, a human confirms it;
it is deliberately NOT computed here.

DRIVER-FREE: runs against the `retail.validate.QueryRunner` Protocol, so this
module's import path NEVER imports psycopg2. The real read-only runner is built
lazily in the CLI seam, exactly as `retail.validate` does. Inverted data flow vs
validate.py: this runs BEFORE a source-map.yaml exists (input is a bare table +
candidate PK), so it MUST NOT be routed through validate_targets.load_targets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .validate import QueryRunner

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _safe_identifier(name: str) -> str:
    """Reject anything that is not a plain (optionally dotted) SQL identifier.

    profile.py interpolates table/column names into SQL text (identifiers cannot
    be bound as query params). The runner is read-only, but a crafted name must
    not be able to break out of the identifier position. Allow letters, digits,
    underscore, and dots between parts; reject everything else.
    """
    if not _IDENT_RE.match(name):
        raise ValueError(f"unsafe SQL identifier: {name!r}")
    return name


@dataclass(frozen=True)
class ColumnProfile:
    name: str
    missing_count: int
    missing_pct: float
    distinct_cardinality: int


@dataclass(frozen=True)
class PkProof:
    total: int
    distinct_pk: int
    null_pk: int
    is_unique: bool


@dataclass(frozen=True)
class ProfileResult:
    table: str
    row_count: int
    column_count: int
    columns: tuple[ColumnProfile, ...]
    pk: PkProof


def _discover_columns(runner: QueryRunner, table: str) -> tuple[str, ...]:
    """Column names for ``schema.table`` from information_schema, in order."""
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = "public", table
    rows = runner.run(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (schema, name),
    )
    return tuple(r[0] for r in rows)


def profile(
    runner: QueryRunner, table: str, candidate_pk: tuple[str, ...]
) -> ProfileResult:
    """Profile ``table`` mechanically. Read-only; one pass of simple aggregates."""
    table = _safe_identifier(table)
    columns = _discover_columns(runner, table)

    row_rows = runner.run(f"SELECT count(*) FROM {table}")
    row_count = row_rows[0][0] if row_rows else 0

    col_profiles: list[ColumnProfile] = []
    for col in columns:
        col = _safe_identifier(col)
        # Missingness is ''OR NULL, NEVER IS NULL alone (RC5 / the load-bearing
        # trap): a faithful landing writes '' for None, so IS NULL reports 0.
        stat = runner.run(
            f"SELECT count(*) FILTER (WHERE trim({col}) = '' OR {col} IS NULL), "
            f"count(DISTINCT trim({col})) FROM {table}"
        )
        missing, distinct = (stat[0][0], stat[0][1]) if stat else (0, 0)
        pct = (missing / row_count * 100.0) if row_count else 0.0
        col_profiles.append(
            ColumnProfile(
                name=col,
                missing_count=missing,
                missing_pct=pct,
                distinct_cardinality=distinct,
            )
        )

    validated_pk = tuple(_safe_identifier(c) for c in candidate_pk)
    pk_cols = ", ".join(validated_pk)
    null_pred = " OR ".join(f"{c} IS NULL" for c in validated_pk)
    pk_rows = runner.run(
        f"SELECT count(*), count(DISTINCT ({pk_cols})), "
        f"count(*) FILTER (WHERE {null_pred}) FROM {table}"
    )
    total, distinct_pk, null_pk = pk_rows[0] if pk_rows else (0, 0, 0)
    pk = PkProof(
        total=total,
        distinct_pk=distinct_pk,
        null_pk=null_pk,
        is_unique=(total == distinct_pk and null_pk == 0),
    )

    return ProfileResult(
        table=table,
        row_count=row_count,
        column_count=len(columns),
        columns=tuple(col_profiles),
        pk=pk,
    )
