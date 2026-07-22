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

    NOTE (#410): since the profiler now QUOTES every emitted identifier through the
    dialect (``quote_ident`` / ``quote_qualified``, which re-run
    ``seshat.identifiers.validate_*``), this is a cheap FIRST-PASS reject on the raw
    table string before the authoritative dialect validation -- not the sole guard.
    Its regex still accepts an unlimited dotted chain, but the table then passes
    through ``validate_qualified_identifier`` (max two parts) in ``profile()``, so a
    3-part name is rejected there; this pre-check only rejects the obviously-unsafe
    (quotes, comments, separators) early. Both validators use ``fullmatch``.
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


@dataclass(frozen=True)
class _ResolvedColumn:
    """A candidate-key column resolved against the discovered catalog columns.

    ``discovered`` is the EXACT-case name the catalog returned (Postgres folds an
    unquoted name to lower, Snowflake to upper); ``data_type`` is that column's
    landed type; ``is_text`` is the dialect's text/non-text verdict for it.
    """

    discovered: str
    data_type: str
    is_text: bool


def _resolve_pk_columns(
    dialect: Dialect,
    candidate_pk: tuple[str, ...],
    columns: tuple[tuple[str, str], ...],
) -> tuple[_ResolvedColumn, ...]:
    """Match each ``--pk`` name to a DISCOVERED column, case-insensitively.

    The catalog already folded the name when it stored it (Postgres -> lower,
    Snowflake -> upper), so a raw case-sensitive lookup of the user's spelling
    misses on a case mismatch -- e.g. Postgres ``--pk ID`` on a stored ``id``, or
    Snowflake ``--pk id`` on a stored ``ID`` -- defaulting the type to ``text``
    and emitting ``trim(<key>)`` against a numeric column (a DB-boundary crash,
    #409/#410). Match EXACT-case first, then fall back to ``casefold()``; carry the
    DISCOVERED spelling forward so the emitted SQL names the column exactly as the
    engine stored it. Exact-first is load-bearing on a case-SENSITIVE catalog:
    Postgres can hold both ``id`` and a quoted ``"ID"`` in one table, so a
    casefold-only lookup would silently profile the WRONG column for ``--pk id`` --
    an exit-0 wrong PK proof, the worst kind of bug in the gate's evidence.

    An AMBIGUOUS folded match -- the user's spelling matches NO column exactly yet
    casefolds to TWO OR MORE discovered columns (e.g. ``--pk Id`` against both
    ``id`` and ``"ID"``) -- is REFUSED with an actionable error rather than
    silently resolved by catalog order (#410 review): guessing a grain key from
    ordinal position would fabricate a uniqueness proof for a column the user did
    not name. A candidate with no match at all falls back to a text-typed
    passthrough of the user's spelling (the DB then reports the unknown column).
    """
    exact = {name: (name, dt) for name, dt in columns}
    # Group discovered columns by casefold so an AMBIGUOUS (>1 candidate) fold is
    # detectable; keep every colliding spelling for the error message.
    by_casefold: dict[str, list[tuple[str, str]]] = {}
    for name, dt in columns:
        by_casefold.setdefault(name.casefold(), []).append((name, dt))

    def _match(col: str) -> tuple[str, str]:
        if col in exact:
            return exact[col]  # exact-case wins outright, even amid a collision
        candidates = by_casefold.get(col.casefold(), [])
        if len(candidates) > 1:
            spellings = ", ".join(repr(n) for n, _ in candidates)
            raise ValueError(
                f"candidate PK column {col!r} is ambiguous: it case-matches "
                f"multiple columns ({spellings}). Re-run --pk with the exact "
                f"column spelling to name the intended grain key."
            )
        return candidates[0] if candidates else (col, "text")

    # Dedupe on the RESOLVED discovered name, preserving first-seen order (#412):
    # `--pk id,ID` (only `id` exists) casefold-resolves BOTH to the same discovered
    # column, which without dedupe collapses to a redundant `count(DISTINCT ("id",
    # "id"))` -- arithmetically correct but a degenerate row-value tuple. An
    # order-preserving dict keyed on the DISCOVERED spelling (not the raw --pk
    # string) drops that collision; column ordering is load-bearing for the proof.
    resolved: dict[str, _ResolvedColumn] = {}
    for col in candidate_pk:
        discovered, data_type = _match(col)
        resolved.setdefault(
            discovered,
            _ResolvedColumn(
                discovered=discovered,
                data_type=data_type,
                is_text=dialect.is_text_type(data_type),
            ),
        )
    return tuple(resolved.values())


def _pk_null_predicate(dialect: Dialect, pk_cols: tuple[_ResolvedColumn, ...]) -> str:
    """The ``OR``-joined missing-key predicate for the candidate-PK null proof.

    Count an EMPTY-or-NULL key, not just NULL, for TEXT PK columns -- the same
    RC5 ``'' OR NULL`` measure used for text-column missingness. A faithful
    all-TEXT bronze landing writes ``''`` (not NULL) for a missing key, so
    ``IS NULL`` alone would miss a blank key and wrongly pass a non-unique grain;
    it also keeps the emitted ``NULLs/empty in PK`` proof honest (#409). Non-text
    keys cannot hold ``''`` -> plain ``IS NULL`` (``trim()`` is text-only, crashes).

    Each identifier is QUOTED via the dialect (``"id"`` / ``[id]`` / `` `id` ``) so
    a reserved word (``order``, ``group``) or a case-sensitive column parses as an
    identifier, not a keyword (#410); the DISCOVERED spelling is quoted so it
    matches the stored column on every engine.
    """

    def _term(rc: _ResolvedColumn) -> str:
        q = dialect.quote_ident(rc.discovered, context="candidate PK column")
        if rc.is_text:
            return f"trim({q}) = '' OR {q} IS NULL"
        return f"{q} IS NULL"

    return " OR ".join(_term(rc) for rc in pk_cols)


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
    # Quote the table so a reserved-word or case-sensitive object (bronze.order,
    # a mixed-case name) parses as an identifier, not a keyword (#410). Quoting
    # only -- NOT case-folding the table: `--table Bronze.T` casing is a separate
    # pre-existing concern (columns_query's normalize) and out of scope here.
    quoted_table = dialect.quote_qualified(table, context="profiled table")

    row_rows = runner.run(f"SELECT count(*) FROM {quoted_table}")
    row_count = row_rows[0][0] if row_rows else 0

    col_profiles: list[ColumnProfile] = []
    for col_name, data_type in columns:
        # col_name is the DISCOVERED (catalog-cased) name; quote it so a
        # reserved-word column (`order`, `group`) parses as an identifier (#410).
        col = dialect.quote_ident(col_name, context="profiled column")
        if dialect.is_text_type(data_type):
            # TEXT: missingness is ''OR NULL, NEVER IS NULL alone (RC5 / the
            # load-bearing trap): a faithful landing writes '' for None, so IS NULL
            # alone reports 0. trim() also folds whitespace-variant phantom distincts.
            missing_frag = dialect.count_where(f"trim({col}) = '' OR {col} IS NULL")
            stat = runner.run(
                f"SELECT {missing_frag}, count(DISTINCT trim({col})) "
                f"FROM {quoted_table}"
            )
        else:
            # NON-TEXT (timestamptz, numeric, boolean, a lineage column, ...):
            # trim() is text-only and would crash. A non-text column cannot hold '',
            # so plain IS NULL is the correct (and only valid) missingness measure.
            missing_frag = dialect.count_where(f"{col} IS NULL")
            stat = runner.run(
                f"SELECT {missing_frag}, count(DISTINCT {col}) FROM {quoted_table}"
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

    # Resolve each --pk name to its DISCOVERED (catalog-cased) column so the type
    # branch is correct on a case-mismatch and the emitted SQL names the column as
    # the engine stored it (#410); then quote each discovered name.
    pk_cols = _resolve_pk_columns(dialect, candidate_pk, columns)
    null_frag = dialect.count_where(_pk_null_predicate(dialect, pk_cols))
    # Route the tuple-distinct count through the dialect, NOT a hardcoded
    # Postgres row-value `count(DISTINCT (a, b))`. Postgres returns exactly that
    # form, but SQL Server / MySQL / Snowflake need their own shape (a DISTINCT
    # subquery) -- the hardcoded form reached the non-Postgres runners as invalid
    # SQL and failed at the DB boundary (PR #409 review). Pass the QUOTED discovered
    # names so a reserved-word / case-sensitive key is handled here too (#410).
    quoted_pk = tuple(
        dialect.quote_ident(rc.discovered, context="candidate PK column")
        for rc in pk_cols
    )
    distinct_frag = dialect.distinct_tuple_count(quoted_pk, quoted_table)
    pk_rows = runner.run(
        f"SELECT count(*), {distinct_frag}, {null_frag} FROM {quoted_table}"
    )
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
