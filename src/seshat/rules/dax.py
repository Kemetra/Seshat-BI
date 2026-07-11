"""DAX/TMDL rules (D1-D8, C1).

Rules registered here:
  D1 - Measure names must be PascalCase (^[A-Z][A-Za-z0-9]*$)
  D2 - Each measure must have a displayFolder
  D3 - No duplicated measure logic (exact normalized-body collision)
  D4 - Use DIVIDE() not the bare / operator
  D5 - WARNING: numeric column summarizeBy != none
  D6 - No bidirectional relationships (crossFilteringBehavior: bothDirections)
  D7 - Time-intelligence requires a date-table marker
  D8 - Partitions must source from gold schema only
  C1 - Connection must use parameter identifiers, not string literals
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core import Finding, RuleContext, Severity
from ..registry import register
from ..sql import stale_schema_tokens
from ..tmdl import (
    DATE_TABLE_MARKER,
    TI_TRIGGER_FUNCTIONS,
    TmdlColumn,
    TmdlMeasure,
    TmdlTable,
    iter_m_sources,
    iter_model_files,
    normalize_measure_body,
    parse_relationships,
    parse_tmdl,
)

# ---------------------------------------------------------------------------
# Shared scaffold — iterate parseable TMDL tables' measures / columns
# ---------------------------------------------------------------------------


def _iter_measures(ctx: RuleContext) -> Iterable[tuple[str, TmdlMeasure]]:
    """Yield ``(repo_relative_path, measure)`` for every measure in every
    parseable ``.tmdl`` table file.

    Folds the shared scaffold — ``iter_model_files`` → ``parse_tmdl`` →
    skip-None → ``table.measures`` — so per-measure rules reduce to one
    non-nested loop. Iteration order matches ``iter_model_files`` (file order)
    then ``table.measures`` (declaration order).
    """
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            yield rel, m


def _iter_columns(ctx: RuleContext) -> Iterable[tuple[str, TmdlColumn]]:
    """Yield ``(repo_relative_path, column)`` for every column in every
    parseable ``.tmdl`` table file (sibling of :func:`_iter_measures`, for D5).
    """
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for c in table.columns:
            yield rel, c


# ---------------------------------------------------------------------------
# D1 — PascalCase measure names
# ---------------------------------------------------------------------------

_PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@register("D1", "Measure names must be PascalCase")
def d1_pascalcase_measures(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any measure whose name does not match ``^[A-Z][A-Za-z0-9]*$``."""
    for rel, m in _iter_measures(ctx):
        if not _PASCAL.match(m.name):
            yield Finding(
                rule_id="D1",
                severity=Severity.ERROR,
                message=(f"Measure '{m.name}' is not PascalCase (^[A-Z][A-Za-z0-9]*$)"),
                locator=f"{rel}:{m.line}",
            )


# ---------------------------------------------------------------------------
# D2 — displayFolder required on every measure
# ---------------------------------------------------------------------------


@register("D2", "Each measure must have a displayFolder")
def d2_display_folder(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any measure that has NO ``displayFolder`` property line.

    Contract: a missing ``displayFolder`` line is parsed as ``None`` — that is
    the violation. An explicitly empty displayFolder (``displayFolder:``) is a
    different state and is NOT flagged here (the ``is None`` guard documents
    this distinction).
    """
    for rel, m in _iter_measures(ctx):
        if m.display_folder is None:
            yield Finding(
                rule_id="D2",
                severity=Severity.ERROR,
                message=f"Measure '{m.name}' has no displayFolder",
                locator=f"{rel}:{m.line}",
            )


# ---------------------------------------------------------------------------
# D3 — no duplicated measure logic
# ---------------------------------------------------------------------------


@register("D3", "No duplicated measure logic")
def d3_no_duplicate_logic(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any measure whose normalized body is identical to a previously seen one.

    Normalization (via ``normalize_measure_body``): strip ``//`` and ``/* */``
    comments, collapse whitespace, lowercase.  Two measures sharing the same
    normalized body are reported as duplicates; the *second* occurrence is the
    locator.
    """
    seen: dict[str, tuple[str, str, int]] = {}  # norm -> (rel, name, line)
    for rel, m in _iter_measures(ctx):
        norm = normalize_measure_body(m.expression)
        if not norm:
            continue
        if norm in seen:
            prev_rel, prev_name, prev_line = seen[norm]
            yield Finding(
                rule_id="D3",
                severity=Severity.ERROR,
                message=(
                    f"Measure '{m.name}' duplicates logic of "
                    f"'{prev_name}' (identical normalized body)"
                ),
                locator=f"{rel}:{m.line}",
            )
        else:
            seen[norm] = (rel, m.name, m.line)


# ---------------------------------------------------------------------------
# D4 — use DIVIDE() not the / operator
# ---------------------------------------------------------------------------


def _strip_dax_comments_and_strings(expr: str) -> str:
    """Strip ``/* */`` block comments, ``//`` line comments, and string literals.

    Returns the cleaned expression text, safe to scan for a bare ``/`` that
    would signal a division operator rather than a comment delimiter.
    """
    no_block = re.sub(r"/\*.*?\*/", " ", expr, flags=re.DOTALL)
    no_line = re.sub(r"//[^\n]*", " ", no_block)
    # Strip double-quoted DAX string literals (escaped quote is "")
    no_double = re.sub(r'"(?:[^"]|"")*"', " ", no_line)
    # Strip single-quoted DAX table/column name delimiters. DAX uses
    # 'Table Name'[Column]; '' escapes a literal quote inside the name. A
    # '/' inside such a name is never a division operator, so remove it before
    # the bare-'/' scan to avoid a false-positive D4 (audit 2026-06-26 #4).
    return re.sub(r"'(?:[^']|'')*'", " ", no_double)


@register("D4", "Use DIVIDE() not the / operator")
def d4_divide_not_slash(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any measure expression containing a bare ``/`` after stripping comments."""
    for rel, m in _iter_measures(ctx):
        cleaned = _strip_dax_comments_and_strings(m.expression)
        if "/" in cleaned:
            yield Finding(
                rule_id="D4",
                severity=Severity.ERROR,
                message=f"Measure '{m.name}' uses '/'; use DIVIDE() instead",
                locator=f"{rel}:{m.line}",
            )


# ---------------------------------------------------------------------------
# D5 — WARNING: numeric column summarizeBy != none
# ---------------------------------------------------------------------------

_NUMERIC_TYPES = frozenset({"int64", "decimal", "double", "int", "currency"})


@register("D5", "Prefer explicit measures over implicit aggregation")
def d5_explicit_aggregation(ctx: RuleContext) -> Iterable[Finding]:
    """Warn when a numeric column has ``summarizeBy`` set to anything other than
    ``none``.

    Severity is WARNING (does not fail the build). The ``summarizeBy`` property
    is only flagged when explicitly present and != ``none``; absent property is
    treated as acceptable (conservative: missing != implicit sum).
    """
    for rel, c in _iter_columns(ctx):
        dt = (c.data_type or "").lower()
        sb = (c.summarize_by or "none").lower()
        if dt in _NUMERIC_TYPES and sb != "none":
            yield Finding(
                rule_id="D5",
                severity=Severity.WARNING,
                message=(
                    f"Numeric column '{c.name}' has"
                    f" summarizeBy='{c.summarize_by}';"
                    " prefer explicit measures (summarizeBy: none)"
                ),
                locator=f"{rel}:{c.line}",
            )


# ---------------------------------------------------------------------------
# D6 — no bidirectional relationships
# ---------------------------------------------------------------------------


@register("D6", "No bidirectional relationships")
def d6_no_bidir_relationships(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any relationship with ``crossFilteringBehavior: bothDirections``.

    Bidirectional cross-filtering is a common performance pitfall and can cause
    ambiguous filter contexts. All relationships should use single-direction
    (the default) unless explicitly reviewed and overridden.

    Uses ``parse_relationships`` on every TMDL file; table files return an
    empty tuple and are harmlessly skipped.
    """
    for rel, text in iter_model_files(ctx, ".tmdl"):
        for relationship in parse_relationships(text):
            if relationship.cross_filtering_behavior == "bothDirections":
                yield Finding(
                    rule_id="D6",
                    severity=Severity.ERROR,
                    message=(
                        f"Relationship '{relationship.name}' uses"
                        " crossFilteringBehavior: bothDirections;"
                        " use single-direction instead"
                    ),
                    locator=f"{rel}:{relationship.line}",
                )


# ---------------------------------------------------------------------------
# D7 — time-intelligence requires a date-table marker
# ---------------------------------------------------------------------------

_TI_IDENT = re.compile(r"[A-Za-z_]\w*")


def _table_is_marked_date_table(table: TmdlTable) -> bool:
    """True if ``table`` carries either accepted date-table marker.

    A table counts as a marked date table if EITHER:
    (a) it carries the ``DATE_TABLE_MARKER`` annotation, OR
    (b) it has table-level ``dataCategory: Time`` AND at least one column
        flagged ``isKey`` -- the real "Mark as Date Table" marker Power BI
        writes (TOM ``Table.DataCategory = "Time"`` + a key column). Table-
        level ``dataCategory: Time`` WITHOUT a key column is not sufficient.
    """
    if any(ann.strip() == DATE_TABLE_MARKER for ann in table.annotations):
        return True
    return table.data_category == "Time" and any(c.is_key for c in table.columns)


def _measure_uses_ti(expression: str) -> bool:
    """True if ``expression`` invokes a time-intelligence trigger function.

    Strips comments and string literals, tokenizes identifiers, uppercases, and
    intersects with ``TI_TRIGGER_FUNCTIONS``.
    """
    cleaned = _strip_dax_comments_and_strings(expression)
    idents = {tok.upper() for tok in _TI_IDENT.findall(cleaned)}
    return bool(idents & TI_TRIGGER_FUNCTIONS)


@register("D7", "Time-intelligence requires a date-table marker")
def d7_ti_needs_date_marker(ctx: RuleContext) -> Iterable[Finding]:
    """Flag if any measure uses a time-intelligence function but no table carries
    the date-table annotation marker.

    This is a *model-level* rule: it scans all TMDL files first and yields at
    most one finding (a missing marker affects the whole model, not one file).

    Detection:
    - ``_measure_uses_ti`` flags any measure that invokes a TI trigger function.
    - ``_table_is_marked_date_table`` flags any table carrying an accepted
      date-table marker.
    """
    any_ti_use = False
    any_date_marker = False
    ti_locator = ""

    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        any_date_marker |= _table_is_marked_date_table(table)

        for m in table.measures:
            if _measure_uses_ti(m.expression):
                any_ti_use = True
                if not ti_locator:
                    ti_locator = f"{rel}:{m.line}"

    if any_ti_use and not any_date_marker:
        yield Finding(
            rule_id="D7",
            severity=Severity.ERROR,
            message=(
                "Model uses time-intelligence functions but no table is marked as a"
                f" date table (via '{DATE_TABLE_MARKER}', or table-level"
                " 'dataCategory: Time' with a column marked 'isKey')"
            ),
            locator=ti_locator,
        )


# ---------------------------------------------------------------------------
# D8 — gold-only sourcing
# ---------------------------------------------------------------------------

# Regex for double-quoted M string literals. M escapes an inner quote by doubling
# it (`""`), so `"a""b"` is the ONE literal `a"b` -- the `(?:[^"]|"")*` body
# consumes escaped pairs rather than ending at the first inner quote (audit
# 2026-06-26 #29; an old `"([^"]*)"` split there and could leak a schema token
# sitting after an escaped quote past D8's scan). Group 1 is the raw body (with
# `""` pairs intact); ``_extract_m_string_bodies`` unescapes them to the true value.
_M_STRING_LITERAL = re.compile(r'"((?:[^"]|"")*)"')

# Regex for the M connection option ``[Schema="<value>"]`` / ``Schema = "<value>"``.
_M_SCHEMA_OPTION = re.compile(r'Schema\s*=\s*"([^"]+)"', re.IGNORECASE)

# Non-gold schema tokens (mirrors seshat.sql._SCHEMA_TOKENS).
_STALE_SCHEMAS = frozenset({"bronze", "silver", "raw", "marts"})


def _extract_m_string_bodies(m_text: str) -> list[str]:
    """Return the text contents of all double-quoted string literals in ``m_text``.

    Used to expose SQL embedded in ``Value.NativeQuery(_, "SELECT … FROM schema.obj")``
    to ``stale_schema_tokens``, which would otherwise strip those strings. Each
    body has its M `""` escapes collapsed back to a single `"` so the returned text
    is the literal's true value.
    """
    return [body.replace('""', '"') for body in _M_STRING_LITERAL.findall(m_text)]


def _yield_d8(
    seen: set[str], token: str, locator: str, message: str
) -> Iterable[Finding]:
    """Emit a D8 Finding for ``token`` unless it was already reported for this block.

    Owns the dedup+construct logic shared by the three scan strategies: a token
    already in ``seen`` is skipped, so the first strategy to report a token wins
    (its ``message`` is the one emitted).
    """
    if token not in seen:
        seen.add(token)
        yield Finding(
            rule_id="D8",
            severity=Severity.ERROR,
            message=message,
            locator=locator,
        )


def _scan_outer_text(text: str) -> Iterable[tuple[str, str]]:
    """Yield (token, message) for non-gold schema tokens in the raw M text.

    Catches schema-qualifying positions (``FROM bronze.x``, ``bronze.obj``,
    ``CREATE SCHEMA bronze``) via ``stale_schema_tokens``.
    """
    for token, _line in stale_schema_tokens(text):
        yield (
            token,
            (
                f"Partition source references non-gold schema '{token}';"
                " all sources must use the gold schema"
            ),
        )


def _scan_string_bodies(text: str) -> Iterable[tuple[str, str]]:
    """Yield (token, message) for non-gold schema tokens inside string literals.

    Catches SQL embedded in ``Value.NativeQuery(Src, "SELECT * FROM bronze.obj")``;
    ``tokenize_sql`` strips string contents so the raw text alone misses it.
    """
    for body in _extract_m_string_bodies(text):
        for token, _line in stale_schema_tokens(body):
            yield (
                token,
                (
                    "Partition source native SQL references non-gold"
                    f" schema '{token}';"
                    " all sources must use the gold schema"
                ),
            )


def _scan_schema_option(text: str) -> Iterable[tuple[str, str]]:
    """Yield (token, message) for the M connection option ``[Schema="bronze"]``.

    A lone ``"bronze"`` body has no qualifying predecessor, so the outer-text
    and string-body scans both miss it, yet the spec lists M ``Schema="…"`` as a
    schema-qualifying position D8 MUST flag. The dedup token is the lowercased
    value; the message embeds the original-case value.
    """
    for value in _M_SCHEMA_OPTION.findall(text):
        token = value.lower()
        if token in _STALE_SCHEMAS:
            yield (
                token,
                (
                    f"Partition source uses non-gold schema option"
                    f' Schema="{value}";'
                    " all sources must use the gold schema"
                ),
            )


@register("D8", "Partitions must source from gold schema only")
def d8_gold_only_sourcing(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any M partition source or shared expression that references a
    non-gold schema token (raw, marts, bronze, silver).

    Three scan strategies per source block (de-duplicated by token, run in
    order so the first strategy to report a token wins):
    1. ``_scan_outer_text`` — the raw M text via ``stale_schema_tokens``.
    2. ``_scan_string_bodies`` — double-quoted string-literal bodies via
       ``stale_schema_tokens``.
    3. ``_scan_schema_option`` — the M connection option ``[Schema="bronze"]``.

    Strategies 1 and 2 reuse ``stale_schema_tokens`` from ``seshat.sql``.
    A given (locator, schema-token) is reported at most once per block.
    """
    for msrc in iter_m_sources(ctx.repo_root, ctx.tracked_files):
        seen: set[str] = set()  # schema tokens already reported for this block
        scanners = (_scan_outer_text, _scan_string_bodies, _scan_schema_option)
        for scan in scanners:
            for token, message in scan(msrc.text):
                yield from _yield_d8(seen, token, msrc.locator, message)


# ---------------------------------------------------------------------------
# D9 — no hardcoded date literals in measures
# ---------------------------------------------------------------------------

# DATE(yyyy, m, d) constructor or an ISO date literal yyyy-m-d. The ISO branch
# accepts 1-or-2-digit month/day (`2024-1-1` is just as hardcoded as `2024-01-01`;
# the old `\d{2}` each silently missed single-digit forms -- audit 2026-06-26 #30).
# The 4-digit-year anchor keeps it from matching 2-/3-digit `n-n-n` arithmetic runs.
_DATE_LITERAL = re.compile(r"DATE\s*\(\s*\d{3,4}\s*,|\b\d{4}-\d{1,2}-\d{1,2}\b")


@register("D9", "No hardcoded date literals in measures")
def d9_no_hardcoded_dates(ctx: RuleContext) -> Iterable[Finding]:
    """Warn when a measure embeds a hardcoded date (DATE(y,m,d) or "yyyy-mm-dd").

    Dates belong in the date dimension; baked-in literals bypass the model's date
    table and freeze the logic. Comments and string literals are stripped first so
    a date mentioned in a comment/string is not flagged.
    """
    for rel, m in _iter_measures(ctx):
        cleaned = _strip_dax_comments_and_strings(m.expression)
        if _DATE_LITERAL.search(cleaned):
            yield Finding(
                rule_id="D9",
                severity=Severity.WARNING,
                message=(
                    f"Measure '{m.name}' embeds a hardcoded date literal;"
                    " use the date dimension instead"
                ),
                locator=f"{rel}:{m.line}",
            )


# ---------------------------------------------------------------------------
# D10 — no FILTER(ALL(...)) full-table-scan anti-pattern
# ---------------------------------------------------------------------------

# FILTER ( ALL[ SELECTED | EXCEPT | NOBLANKROW ] ( ... -- a row-by-row full scan the
# engine can't push down; prefer a column filter in CALCULATE. ALLSELECTED/ALLEXCEPT
# inside FILTER share the same anti-pattern as ALL (audit 2026-06-26 #9).
_FILTER_ALL = re.compile(
    r"FILTER\s*\(\s*ALL(?:SELECTED|EXCEPT|NOBLANKROW)?\s*\(", re.IGNORECASE
)


@register(
    "D10", "No FILTER(ALL/ALLSELECTED/ALLEXCEPT(...)) full-table-scan anti-pattern"
)
def d10_no_filter_all(ctx: RuleContext) -> Iterable[Finding]:
    """Warn on FILTER(ALL/ALLSELECTED/ALLEXCEPT(...)); prefer a CALCULATE column filter.

    Comments and string literals are stripped first so the pattern is only matched
    in live DAX, not in a comment or string. Severity is WARNING: ALLSELECTED inside
    FILTER has legitimate percent-of-selection uses, so this guides rather than blocks.
    """
    for rel, m in _iter_measures(ctx):
        cleaned = _strip_dax_comments_and_strings(m.expression)
        if _FILTER_ALL.search(cleaned):
            yield Finding(
                rule_id="D10",
                severity=Severity.WARNING,
                message=(
                    f"Measure '{m.name}' uses FILTER(ALL/ALLSELECTED/ALLEXCEPT"
                    "(...)); prefer a column filter inside CALCULATE"
                ),
                locator=f"{rel}:{m.line}",
            )


# ---------------------------------------------------------------------------
# D11 — every measure carries a /// doc comment
# ---------------------------------------------------------------------------


@register("D11", "Each measure must have a /// doc comment")
def d11_measures_documented(ctx: RuleContext) -> Iterable[Finding]:
    """Warn when a measure has no TMDL `///` doc comment on the line above it.

    TMDL writes a measure description as one or more `///` lines immediately
    preceding the `measure` header. A measure with no such line is undocumented.
    Uses parse_tmdl for measure names + line numbers, then checks the raw line
    above each measure header (skipping blank lines) for a `///` prefix.
    """
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        lines = text.splitlines()
        for m in table.measures:
            # m.line is 1-based; the line above is index m.line - 2.
            idx = m.line - 2
            while idx >= 0 and not lines[idx].strip():
                idx -= 1  # skip blank lines between the doc and the measure
            documented = idx >= 0 and lines[idx].strip().startswith("///")
            if not documented:
                yield Finding(
                    rule_id="D11",
                    severity=Severity.WARNING,
                    message=f"Measure '{m.name}' has no /// doc comment",
                    locator=f"{rel}:{m.line}",
                )


# ---------------------------------------------------------------------------
# C1 — parameterized connection (no string literals for server/db)
# ---------------------------------------------------------------------------

# Match PostgreSQL.Database(…) or Sql.Database(…) — captures the argument list.
_DB_CALL = re.compile(
    r"(?:PostgreSQL|Sql|Oracle|MySQL|AzureSQL)\.Database\s*\(([^)]*)\)",
    re.IGNORECASE,
)

# A string literal argument: starts with " (with optional leading whitespace).
_STRING_ARG = re.compile(r'^\s*"')


def _first_literal_arg(args_raw: str) -> str | None:
    """Return the first of the host/database args that is a string literal, else None.

    Splits ``args_raw`` on the first comma to isolate the host and database
    arguments, and checks each against ``_STRING_ARG``. The return value is only
    a truthiness signal for the caller (the Finding message uses the full call
    text, not this arg).
    """
    parts = args_raw.split(",", 1)
    for part in parts[:2]:
        if _STRING_ARG.match(part):
            return part
    return None


@register("C1", "Connection must use parameter identifiers, not string literals")
def c1_parameterized_connection(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any ``.Database(…)`` call whose first or second argument is a
    string literal rather than a parameter identifier.

    Examples:
    - ``PostgreSQL.Database(Server, Database)`` → PASS (identifiers)
    - ``PostgreSQL.Database("myhost", "mydb")`` → FAIL
    - ``PostgreSQL.Database(Server, "mydb")`` → FAIL

    Only the ``.Database(…)`` constructor arguments are inspected; other
    string literals in the same block (e.g. a native SQL query) are ignored.
    """
    for msrc in iter_m_sources(ctx.repo_root, ctx.tracked_files):
        for match in _DB_CALL.finditer(msrc.text):
            if _first_literal_arg(match.group(1)) is not None:
                yield Finding(
                    rule_id="C1",
                    severity=Severity.ERROR,
                    message=(
                        "Connection uses a string literal for server/database;"
                        " use Power BI parameters instead"
                        f" (found: {match.group(0)!r})"
                    ),
                    locator=msrc.locator,
                )
