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

    NOTE (audit 2026-06-26 #40): this overlaps :mod:`retail.identifiers`, but the
    grammars differ deliberately -- this accepts an UNLIMITED dotted chain via one
    regex (the inverted-data-flow profiler runs before a source-map exists), while
    ``identifiers.validate_qualified_identifier`` caps at two parts. They are kept
    separate rather than merged so neither validator's contract shifts; both use
    ``fullmatch`` and reject quotes/comments/separators identically.
    """
    # fullmatch (not match): `.match` anchors only at the start, so a
    # newline-terminated name like "valid_id\nDROP ..." would slip past the
    # ^...$ regex (since $ matches before a trailing \n). fullmatch closes that
    # bypass (audit 2026-06-26, defense-in-depth -- identifiers are interpolated
    # into SQL text).
    if not _IDENT_RE.fullmatch(name):
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


# Postgres data_type strings (information_schema) that hold character data and so
# support trim()/'' missingness. Everything else (timestamptz, numeric, boolean, a
# lineage _loaded_at, ...) is profiled with plain IS NULL -- trim() is text-only and
# crashes (`function btrim(timestamp with time zone) does not exist`) on non-text.
_TEXT_TYPES = frozenset(
    {"text", "character varying", "varchar", "character", "char", "name", '"char"'}
)


def _discover_columns(runner: QueryRunner, table: str) -> tuple[tuple[str, str], ...]:
    """Ordered (column_name, data_type) for ``schema.table`` from information_schema."""
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = "public", table
    rows = runner.run(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (schema, name),
    )
    # tolerate a runner that only returns the name (older fixtures) -> assume text
    return tuple((r[0], (r[1] if len(r) > 1 else "text")) for r in rows)


def profile(
    runner: QueryRunner, table: str, candidate_pk: tuple[str, ...]
) -> ProfileResult:
    """Profile ``table`` mechanically. Read-only; one pass of simple aggregates."""
    table = _safe_identifier(table)
    columns = _discover_columns(runner, table)

    row_rows = runner.run(f"SELECT count(*) FROM {table}")
    row_count = row_rows[0][0] if row_rows else 0

    col_profiles: list[ColumnProfile] = []
    for col_name, data_type in columns:
        col = _safe_identifier(col_name)
        if data_type.lower() in _TEXT_TYPES:
            # TEXT: missingness is ''OR NULL, NEVER IS NULL alone (RC5 / the
            # load-bearing trap): a faithful landing writes '' for None, so IS NULL
            # alone reports 0. trim() also folds whitespace-variant phantom distincts.
            stat = runner.run(
                f"SELECT count(*) FILTER (WHERE trim({col}) = '' OR {col} IS NULL), "
                f"count(DISTINCT trim({col})) FROM {table}"
            )
        else:
            # NON-TEXT (timestamptz, numeric, boolean, a lineage column, ...):
            # trim() is text-only and would crash. A non-text column cannot hold '',
            # so plain IS NULL is the correct (and only valid) missingness measure.
            stat = runner.run(
                f"SELECT count(*) FILTER (WHERE {col} IS NULL), "
                f"count(DISTINCT {col}) FROM {table}"
            )
        missing, distinct = (stat[0][0], stat[0][1]) if stat else (0, 0)
        pct = (missing / row_count * 100.0) if row_count else 0.0
        col_profiles.append(
            ColumnProfile(
                name=col_name,
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
