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
    iter_m_sources,
    iter_model_files,
    normalize_measure_body,
    parse_relationships,
    parse_tmdl,
)

# ---------------------------------------------------------------------------
# D1 — PascalCase measure names
# ---------------------------------------------------------------------------

_PASCAL = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@register("D1", "Measure names must be PascalCase")
def d1_pascalcase_measures(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any measure whose name does not match ``^[A-Z][A-Za-z0-9]*$``."""
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            if not _PASCAL.match(m.name):
                yield Finding(
                    rule_id="D1",
                    severity=Severity.ERROR,
                    message=(
                        f"Measure '{m.name}' is not PascalCase (^[A-Z][A-Za-z0-9]*$)"
                    ),
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
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
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
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
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
    return re.sub(r'"(?:[^"]|"")*"', " ", no_line)


@register("D4", "Use DIVIDE() not the / operator")
def d4_divide_not_slash(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any measure expression containing a bare ``/`` after stripping comments."""
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
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
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for c in table.columns:
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


@register("D7", "Time-intelligence requires a date-table marker")
def d7_ti_needs_date_marker(ctx: RuleContext) -> Iterable[Finding]:
    """Flag if any measure uses a time-intelligence function but no table carries
    the date-table annotation marker.

    This is a *model-level* rule: it scans all TMDL files first and yields at
    most one finding (a missing marker affects the whole model, not one file).

    Detection:
    - Strip comments and string literals from each measure expression, then
      tokenize identifiers, uppercase, and intersect with ``TI_TRIGGER_FUNCTIONS``.
    - Separately check every table's ``annotations`` for ``DATE_TABLE_MARKER``.
    """
    any_ti_use = False
    any_date_marker = False
    ti_locator = ""

    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        # Check for date-table marker in annotations
        for ann in table.annotations:
            if ann.strip() == DATE_TABLE_MARKER:
                any_date_marker = True

        # Check for TI function usage in measures
        for m in table.measures:
            cleaned = _strip_dax_comments_and_strings(m.expression)
            idents = {tok.upper() for tok in _TI_IDENT.findall(cleaned)}
            if idents & TI_TRIGGER_FUNCTIONS:
                any_ti_use = True
                if not ti_locator:
                    ti_locator = f"{rel}:{m.line}"

    if any_ti_use and not any_date_marker:
        yield Finding(
            rule_id="D7",
            severity=Severity.ERROR,
            message=(
                "Model uses time-intelligence functions but no table carries"
                f" '{DATE_TABLE_MARKER}'"
            ),
            locator=ti_locator,
        )


# ---------------------------------------------------------------------------
# D8 — gold-only sourcing
# ---------------------------------------------------------------------------

# Regex to extract the bodies of double-quoted M string literals.
_M_STRING_LITERAL = re.compile(r'"([^"]*)"')

# Regex for the M connection option ``[Schema="<value>"]`` / ``Schema = "<value>"``.
_M_SCHEMA_OPTION = re.compile(r'Schema\s*=\s*"([^"]+)"', re.IGNORECASE)

# Non-gold schema tokens (mirrors retail.sql._SCHEMA_TOKENS).
_STALE_SCHEMAS = frozenset({"bronze", "silver", "raw", "marts"})


def _extract_m_string_bodies(m_text: str) -> list[str]:
    """Return the text contents of all double-quoted string literals in ``m_text``.

    Used to expose SQL embedded in ``Value.NativeQuery(_, "SELECT … FROM schema.obj")``
    to ``stale_schema_tokens``, which would otherwise strip those strings.
    """
    return _M_STRING_LITERAL.findall(m_text)


@register("D8", "Partitions must source from gold schema only")
def d8_gold_only_sourcing(ctx: RuleContext) -> Iterable[Finding]:
    """Flag any M partition source or shared expression that references a
    non-gold schema token (raw, marts, bronze, silver).

    Three scan strategies per source block (de-duplicated by token):
    1. Outer M text via ``stale_schema_tokens`` — catches schema-qualifying
       positions (``FROM bronze.x``, ``bronze.obj``, ``CREATE SCHEMA bronze``).
    2. Double-quoted string-literal bodies via ``stale_schema_tokens`` — catches
       SQL embedded in ``Value.NativeQuery(Src, "SELECT * FROM bronze.obj")``;
       ``tokenize_sql`` strips string contents so the raw text alone misses it.
    3. The M connection option ``[Schema="bronze"]`` via ``_M_SCHEMA_OPTION`` —
       a lone ``"bronze"`` body has no qualifying predecessor, so strategies 1
       and 2 both miss it, yet the spec lists M ``Schema="…"`` as a
       schema-qualifying position D8 MUST flag.

    Strategies 1 and 2 reuse ``stale_schema_tokens`` from ``retail.sql``.
    A given (locator, schema-token) is reported at most once per block.
    """
    for msrc in iter_m_sources(ctx.repo_root, ctx.tracked_files):
        seen: set[str] = set()  # schema tokens already reported for this block

        # Strategy 1: outer M text
        for token, _line in stale_schema_tokens(msrc.text):
            if token not in seen:
                seen.add(token)
                yield Finding(
                    rule_id="D8",
                    severity=Severity.ERROR,
                    message=(
                        f"Partition source references non-gold schema '{token}';"
                        " all sources must use the gold schema"
                    ),
                    locator=msrc.locator,
                )

        # Strategy 2: string literal bodies (SQL in NativeQuery / Value.NativeQuery)
        for body in _extract_m_string_bodies(msrc.text):
            for token, _line in stale_schema_tokens(body):
                if token not in seen:
                    seen.add(token)
                    yield Finding(
                        rule_id="D8",
                        severity=Severity.ERROR,
                        message=(
                            "Partition source native SQL references non-gold"
                            f" schema '{token}';"
                            " all sources must use the gold schema"
                        ),
                        locator=msrc.locator,
                    )

        # Strategy 3: M connection option ``[Schema="bronze"]``
        for value in _M_SCHEMA_OPTION.findall(msrc.text):
            token = value.lower()
            if token in _STALE_SCHEMAS and token not in seen:
                seen.add(token)
                yield Finding(
                    rule_id="D8",
                    severity=Severity.ERROR,
                    message=(
                        f"Partition source uses non-gold schema option"
                        f' Schema="{value}";'
                        " all sources must use the gold schema"
                    ),
                    locator=msrc.locator,
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
            args_raw = match.group(1)
            # Split on the first comma to get the host and database args.
            parts = args_raw.split(",", 1)
            for part in parts[:2]:
                if _STRING_ARG.match(part):
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
                    break  # one finding per .Database() call
