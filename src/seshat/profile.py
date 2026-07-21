"""Mechanical profiling of a landed (bronze) source table.

The source-mapping gate's first artifact (source-profile.md) rests on numbers,
not adjectives. This helper computes the MECHANICAL ones -- row/col count,
per-column ''OR NULL missingness, distinct cardinality, and the candidate-PK
uniqueness proof on the landed data. Semantic profiling (code<->label 1:1,
dimension fan-out, the authoritative returns column) needs the table's MEANING
and is a Principle-V judgment call -- the agent proposes it, a human confirms it;
it is deliberately NOT computed here.

DRIVER-FREE: runs against the `seshat.validate.QueryRunner` Protocol, so this
module's import path NEVER imports psycopg2. The real read-only runner is built
lazily in the CLI seam, exactly as `seshat.validate` does. Inverted data flow vs
validate.py: this runs BEFORE a source-map.yaml exists (input is a bare table +
candidate PK), so it MUST NOT be routed through validate_targets.load_targets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .dialect import Dialect, get_dialect
from .validate import QueryRunner

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _safe_identifier(name: str) -> str:
    """Reject anything that is not a plain (optionally dotted) SQL identifier.

    profile.py interpolates table/column names into SQL text (identifiers cannot
    be bound as query params). The runner is read-only, but a crafted name must
    not be able to break out of the identifier position. Allow letters, digits,
    underscore, and dots between parts; reject everything else.

    NOTE (audit 2026-06-26 #40): this overlaps :mod:`seshat.identifiers`, but the
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
    # The type as landed (information_schema.data_type live; the "Type as landed"
    # markdown cell for a parsed baseline). Optional so pre-existing constructors
    # stay valid; drift's column_retyped compares it NORMALIZED (see classify).
    landed_type: str | None = None


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


def _discover_columns(
    runner: QueryRunner, table: str, dialect: Dialect
) -> tuple[tuple[str, str], ...]:
    """Ordered (column_name, data_type) for ``schema.table`` from information_schema."""
    if "." in table:
        schema, name = table.split(".", 1)
    else:
        schema, name = "public", table
    rows = runner.run(
        dialect.columns_query(),
        (
            dialect.normalize_catalog_literal(schema),
            dialect.normalize_catalog_literal(name),
        ),
    )
    # tolerate a runner that only returns the name (older fixtures) -> assume text
    return tuple((r[0], (r[1] if len(r) > 1 else "text")) for r in rows)


def _pk_null_predicate(
    dialect: Dialect,
    validated_pk: tuple[str, ...],
    columns: tuple[tuple[str, str], ...],
) -> str:
    """The ``OR``-joined missing-key predicate for the candidate-PK null proof.

    Count an EMPTY-or-NULL key, not just NULL, for TEXT PK columns -- the same
    RC5 ``'' OR NULL`` measure used for text-column missingness. A faithful
    all-TEXT bronze landing writes ``''`` (not NULL) for a missing key, so
    ``IS NULL`` alone would miss a blank key and wrongly pass a non-unique grain;
    it also keeps the emitted ``NULLs/empty in PK`` proof honest (#409). Non-text
    keys cannot hold ``''`` -> plain ``IS NULL`` (``trim()`` is text-only, crashes).

    Match a candidate-key name to its discovered type using the dialect's OWN
    catalog normalization -- NOT a raw case-sensitive dict lookup. Snowflake's
    INFORMATION_SCHEMA reports an unquoted ``id`` as ``ID``, so a user's ``--pk
    id`` would miss a case-sensitive lookup, default to ``text``, and emit
    ``trim(id) = ''`` against a NUMBER column -- a DB-boundary crash instead of a
    profile (#409). Postgres's normalize is identity, so its case-sensitive
    matching is unchanged; Snowflake folds to upper, aligning with ``columns_query``.
    """
    type_by_name = {
        dialect.normalize_catalog_literal(name): data_type
        for name, data_type in columns
    }

    def _term(col: str) -> str:
        data_type = type_by_name.get(dialect.normalize_catalog_literal(col), "text")
        if dialect.is_text_type(data_type):
            return f"trim({col}) = '' OR {col} IS NULL"
        return f"{col} IS NULL"

    return " OR ".join(_term(c) for c in validated_pk)


def profile(
    runner: QueryRunner,
    table: str,
    candidate_pk: tuple[str, ...],
    *,
    dialect: Dialect | None = None,
) -> ProfileResult:
    """Profile ``table`` mechanically. Read-only; one pass of simple aggregates."""
    dialect = dialect or get_dialect("postgres")
    table = _safe_identifier(table)
    columns = _discover_columns(runner, table, dialect)

    row_rows = runner.run(f"SELECT count(*) FROM {table}")
    row_count = row_rows[0][0] if row_rows else 0

    col_profiles: list[ColumnProfile] = []
    for col_name, data_type in columns:
        col = _safe_identifier(col_name)
        if dialect.is_text_type(data_type):
            # TEXT: missingness is ''OR NULL, NEVER IS NULL alone (RC5 / the
            # load-bearing trap): a faithful landing writes '' for None, so IS NULL
            # alone reports 0. trim() also folds whitespace-variant phantom distincts.
            missing_frag = dialect.count_where(f"trim({col}) = '' OR {col} IS NULL")
            stat = runner.run(
                f"SELECT {missing_frag}, count(DISTINCT trim({col})) FROM {table}"
            )
        else:
            # NON-TEXT (timestamptz, numeric, boolean, a lineage column, ...):
            # trim() is text-only and would crash. A non-text column cannot hold '',
            # so plain IS NULL is the correct (and only valid) missingness measure.
            missing_frag = dialect.count_where(f"{col} IS NULL")
            stat = runner.run(
                f"SELECT {missing_frag}, count(DISTINCT {col}) FROM {table}"
            )
        missing, distinct = (stat[0][0], stat[0][1]) if stat else (0, 0)
        pct = (missing / row_count * 100.0) if row_count else 0.0
        col_profiles.append(
            ColumnProfile(
                name=col_name,
                missing_count=missing,
                missing_pct=pct,
                distinct_cardinality=distinct,
                landed_type=data_type,
            )
        )

    validated_pk = tuple(_safe_identifier(c) for c in candidate_pk)
    null_frag = dialect.count_where(_pk_null_predicate(dialect, validated_pk, columns))
    # Route the tuple-distinct count through the dialect, NOT a hardcoded
    # Postgres row-value `count(DISTINCT (a, b))`. Postgres returns exactly that
    # form (byte-identical to before), but SQL Server / MySQL / Snowflake need
    # their own shape (a DISTINCT subquery) -- the hardcoded form reached the
    # non-Postgres runners as invalid SQL and failed at the DB boundary
    # (PR #409 review).
    distinct_frag = dialect.distinct_tuple_count(validated_pk, table)
    pk_rows = runner.run(f"SELECT count(*), {distinct_frag}, {null_frag} FROM {table}")
    total, distinct_pk, null_pk = pk_rows[0] if pk_rows else (0, 0, 0)
    pk = PkProof(
        total=total,
        distinct_pk=distinct_pk,
        null_pk=null_pk,
        # An empty table (total == 0) proves NOTHING: `0 == 0 and 0 == 0` would
        # otherwise pass a candidate PK on a source with no rows. Guard on a
        # nonempty table so this DB profiler agrees with the file profiler, which
        # already requires it (`file_profile.py`: `row_count > 0 and ...`), and so
        # the source-profile.md template's stated rule matches what runs (#409).
        is_unique=(total > 0 and total == distinct_pk and null_pk == 0),
    )

    return ProfileResult(
        table=table,
        row_count=row_count,
        column_count=len(columns),
        columns=tuple(col_profiles),
        pk=pk,
    )
