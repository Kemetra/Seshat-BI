"""HR8 -- gold date dim is contiguous/gap-free (generate_series step + bounds).

What HR8 does (STATIC, fail-closed):
  Scans committed ``warehouse/migrations/*.sql`` files for an
  ``INSERT INTO ... dim_date...`` statement (statement-scoped, comment-stripped
  token span, target name starting with ``dim_date`` -- the same discovery
  shape as the shipped ``S7`` rule in ``src/retail/rules/sql.py``) that
  contains a ``generate_series(start, end, step)`` call, and inspects that
  call's own arguments -- something S7 deliberately never does (S7 only
  checks WHICH builder was used: ``SELECT DISTINCT`` vs ``generate_series``).

  For each qualifying call:
  - **Step classification** (FR-003/FR-004): the third argument is read from
    literal-preserving raw text (``strip_sql_comments``, NOT ``tokenize_sql``,
    which blanks string-literal contents). A literal ``INTERVAL`` value
    textually equal to one day -- recognized in EITHER spelling already used
    in this repo's committed SQL, ``INTERVAL '1 day'`` or the cast idiom
    ``'1 day'::interval`` (case-insensitive, whitespace-insensitive) -- passes
    with no Finding. A literal ``INTERVAL`` (either spelling) of any OTHER
    span is a fail-closed ``Severity.ERROR`` (a non-daily step leaves every
    day between generated rows absent from the calendar; every shipped
    date-dimension convention in this repo already presupposes a daily
    grain). A step that is present but is not a classifiable interval literal
    at all (a bare identifier, a computed expression, a non-interval literal)
    is ALSO a fail-closed ``Severity.ERROR``, with wording distinct from the
    non-daily-step message (Principle I: an unclassifiable step must not pass
    silently by default).
  - **Bounds-order check** (FR-005): fires ONLY when BOTH the start and end
    arguments are literal date values in a recognized spelling (a typed
    literal ``DATE '2022-01-01'`` or a cast literal ``'2022-01-01'::date``,
    case-insensitive on the ``DATE`` keyword). A reversed literal range
    (start chronologically after end) is a fail-closed ``Severity.ERROR``
    naming both literal values in the order given -- an inverted literal
    range is a proven authoring defect visible from the text alone (in
    PostgreSQL it silently produces zero rows). A bound written in neither
    recognized spelling (a subquery, a function call, a parameter, or any
    other form) is treated as NON-literal: the comparison is skipped, never
    treated as a violation by default.

What HR8 NEVER does:
  - It never proves, from static text alone, that the generated calendar's
    actual span covers the fact table's real minimum/maximum date. That is
    ``V-RC15`` (``src/retail/validate.py``, ``check_date_coverage``)'s LIVE,
    read-only responsibility, run against a real database at Gold Ready
    (Principle VIII -- static only). A clean HR8 result does not imply live
    coverage is proven; live, row-level coverage remains fully OUT OF SCOPE
    here and is never asserted, claimed, or fabricated by this module (hard
    rule #9). To keep that boundary unambiguous, HR8 deliberately emits NO
    finding at all for a call that clears both checks above -- silence, not
    an affirmative "pending" or "clean" claim, exactly like HR7's own
    FULL_DROP_AND_REBUILD path emits nothing for a load that needs no
    declaration.
  - It never re-flags the DISTINCT-vs-``generate_series`` builder choice
    itself (that remains S7's exclusive concern; HR8 only fires on a
    statement that already contains a ``generate_series`` call) and never
    edits, imports, or calls ``s7_contiguous_date_dim``.
  - It never opens a database connection, executes, or simulates a reload or
    a query (Principle VIII).
  - It never re-derives a table's grain or primary key, never reads
    ``source-map.yaml``, never decides a Principle-V judgment (grain, PII,
    business rollup, product identity, or approval) -- daily grain here is an
    ALREADY-SETTLED repo convention being enforced, not a new business rule
    -- and emits no numeric score, ratio, or completeness tally (hard rule
    #9). Output is categorical ``Finding`` objects only.
  - It never auto-fixes, rewrites, or reformats migration SQL, and never
    self-grants, records, or moves any readiness stage.

Mirrors the S7/HR7 discipline: reads noise-stripped raw text (via
``strip_sql_comments``) to recover literal text that ``tokenize_sql``
deliberately blanks, uses ``tokenize_sql`` only for statement DISCOVERY
(finding the qualifying ``INSERT ... dim_date`` span), and skips ``tests/``
fixtures.
"""

from __future__ import annotations

import datetime
import re
from collections.abc import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..sql import SqlToken, iter_sql_files, strip_sql_comments, tokenize_sql

RULE_ID = "HR8"

# --- literal recognition (operates on strip_sql_comments-preserved raw text) ---

# INTERVAL '1 day' (typed literal form)
_INTERVAL_TYPED = re.compile(r"INTERVAL\s*'(?P<span>[^']*)'", re.IGNORECASE)
# '1 day'::interval (cast idiom) -- the Opus-review-flagged valid alternate form
_INTERVAL_CAST = re.compile(r"'(?P<span>[^']*)'\s*::\s*interval\b", re.IGNORECASE)
# DATE '2022-01-01' (typed literal form)
_DATE_TYPED = re.compile(r"DATE\s*'(?P<val>[^']*)'", re.IGNORECASE)
# '2022-01-01'::date (cast idiom)
_DATE_CAST = re.compile(r"'(?P<val>[^']*)'\s*::\s*date\b", re.IGNORECASE)

# FR-003 recognizes exactly ONE daily span, in either of the two authorized
# literal spellings (`INTERVAL '1 day'` / `'1 day'::interval`) -- NOT semantic
# equivalents like `24 hours` or bare `day`, which the spec never sanctions;
# widening this set on a fail-closed rule would create silent false negatives.
_DAILY_SPANS = {"1 day"}


def _normalize_span(span: str) -> str:
    return re.sub(r"\s+", " ", span.strip()).lower()


def _classify_interval_literal(text: str) -> str | None:
    """Return the normalized interval span text if ``text`` is a recognized
    literal INTERVAL expression (either spelling); otherwise ``None``."""
    text = text.strip()
    m = _INTERVAL_TYPED.fullmatch(text) or _INTERVAL_CAST.fullmatch(text)
    if not m:
        return None
    return _normalize_span(m.group("span"))


def _classify_date_literal(text: str) -> str | None:
    """Return the literal date text (e.g. ``2022-01-01``) if ``text`` is a
    recognized literal date expression (either spelling); otherwise ``None``."""
    text = text.strip()
    m = _DATE_TYPED.fullmatch(text) or _DATE_CAST.fullmatch(text)
    if not m:
        return None
    return m.group("val").strip()


def _parse_date_literal(text: str) -> datetime.date | None:
    """Parse a recognized date literal to a ``datetime.date`` for CHRONOLOGICAL
    comparison. Handles PostgreSQL's zero-padded (``2022-01-09``) AND non-padded
    (``2022-1-9``) forms. Returns ``None`` if not a literal or not parseable --
    the caller then skips the bounds-order check (never string-compares)."""
    raw = _classify_date_literal(text)
    if raw is None:
        return None
    parts = raw.split("-")
    if len(parts) != 3:
        return None
    try:
        y, mth, d = (int(p) for p in parts)
        return datetime.date(y, mth, d)
    except (ValueError, TypeError):
        return None


def _split_top_level_args(arg_text: str) -> list[str]:
    """Balanced-parenthesis top-level comma split of a call's argument list.

    A bound MAY itself contain a parenthesized subquery (e.g.
    ``(SELECT max(d) FROM silver.orders)``), so a naive ``str.split(",")``
    would wrongly split inside it. Quoted string literals are also honored so
    a comma inside a string (unlikely here, but safe) is not split on.
    """
    args: list[str] = []
    depth = 0
    current: list[str] = []
    i, n = 0, len(arg_text)
    while i < n:
        ch = arg_text[i]
        if ch == "'":
            j = arg_text.find("'", i + 1)
            end = n if j == -1 else j + 1
            current.append(arg_text[i:end])
            i = end
            continue
        if ch == "(":
            depth += 1
            current.append(ch)
            i += 1
            continue
        if ch == ")":
            depth -= 1
            current.append(ch)
            i += 1
            continue
        if ch == "," and depth == 0:
            args.append("".join(current))
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1
    if current:
        args.append("".join(current))
    return [a.strip() for a in args]


def _find_generate_series_call(clean_slice: str) -> tuple[str, int] | None:
    """Find the first ``generate_series(...)`` call in ``clean_slice``.

    Returns ``(inner_arg_text, offset_of_open_paren)`` or ``None`` if no call
    is found. Uses a balanced-parenthesis scan from the matched opening ``(``
    so a parenthesized subquery argument does not truncate the match early.
    """
    m = re.search(r"generate_series\s*\(", clean_slice, re.IGNORECASE)
    if m is None:
        return None
    start = m.end()  # just past the opening "("
    depth = 1
    i = start
    n = len(clean_slice)
    while i < n and depth > 0:
        ch = clean_slice[i]
        if ch == "'":
            j = clean_slice.find("'", i + 1)
            i = n if j == -1 else j + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    if depth != 0:
        return (
            None  # unterminated call -- fail-open (no finding), not our text to guess
        )
    inner = clean_slice[start : i - 1]
    return inner, m.start()


def _read(ctx: RuleContext, rel: str) -> str:
    return (ctx.repo_root / rel).read_text(encoding="utf-8")


def _qualifying_statement_spans(rel: str, raw_text: str) -> list[tuple[int, int]]:
    """Re-derive S7's statement-discovery loop independently (FR-010: this
    does not call or edit ``s7_contiguous_date_dim``).

    Returns a list of ``(start_offset, end_offset)`` character spans in
    ``raw_text`` for each ``INSERT ... dim_date...`` statement (target name
    starting with ``dim_date``) that also contains a ``generate_series``
    token -- HR8's own precondition, same as S7's discovery shape.
    """
    toks = [t for t in tokenize_sql(raw_text) if t.text]
    spans: list[tuple[int, int]] = []
    if not toks:
        return spans

    # Map each token to its character offset in raw_text by re-scanning:
    # tokenize_sql does not expose offsets, only line numbers, so recover
    # offsets by locating each token's line start and searching within it.
    # Simpler + robust: operate on line spans instead of char offsets, since
    # Finding locators are file:line and strip_sql_comments preserves lines.
    lines = raw_text.splitlines(keepends=True)
    total_len = len(raw_text)
    # line_start_offset[i] = character offset where line i (1-based) begins;
    # line_start_offset[len(lines) + 1] = total_len, so "one past the last
    # line" resolves to EOF rather than a stale default of 0.
    line_start_offset = [0] * (len(lines) + 2)
    acc = 0
    for idx, ln in enumerate(lines, start=1):
        line_start_offset[idx] = acc
        acc += len(ln)
    line_start_offset[len(lines) + 1] = total_len

    for idx, tok in enumerate(toks):
        if tok.text.upper() != "INSERT":
            continue
        stmt: list[SqlToken] = []
        end_idx = idx
        for j in range(idx, len(toks)):
            if toks[j].text == ";":
                end_idx = j
                break
            stmt.append(toks[j])
            end_idx = j
        targets_dim_date = any(t.text.lower().startswith("dim_date") for t in stmt)
        if not targets_dim_date:
            continue
        has_genseries = any(t.text.lower() == "generate_series" for t in stmt)
        if not has_genseries:
            continue
        start_line = tok.line
        end_line = toks[end_idx].line
        start_off = (
            line_start_offset[start_line] if start_line < len(line_start_offset) else 0
        )
        # end offset: end of end_line's line (or EOF)
        end_off = (
            line_start_offset[end_line + 1]
            if end_line + 1 < len(line_start_offset)
            else total_len
        )
        end_off = min(end_off, total_len)
        spans.append((start_off, end_off))
    return spans


def _check_statement(
    rel: str, raw_text: str, start_off: int, end_off: int
) -> list[Finding]:
    """Inspect one qualifying statement span's generate_series call."""
    findings: list[Finding] = []

    # Literal-preserving text for this statement's span, comments blanked.
    full_clean = strip_sql_comments(raw_text)
    clean_slice = full_clean[start_off:end_off]

    call = _find_generate_series_call(clean_slice)
    if call is None:
        return findings
    inner, call_rel_offset = call
    call_abs_offset = start_off + call_rel_offset
    call_line = raw_text.count("\n", 0, call_abs_offset) + 1

    args = _split_top_level_args(inner)
    if len(args) < 3:
        return findings  # not a well-formed 3-arg call -- nothing HR8 can classify
    start_arg, end_arg, step_arg = args[0], args[1], args[2]

    # --- step classification (FR-003 / FR-004) ---
    daily_span = _classify_interval_literal(step_arg)
    if daily_span is not None:
        if daily_span not in _DAILY_SPANS:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dim_date generate_series step is '{step_arg.strip()}', "
                        "not a one-day step; a non-daily step leaves every day "
                        "between generated rows absent from the calendar and "
                        "breaks DAX time-intelligence measures -- use "
                        "INTERVAL '1 day' (or '1 day'::interval)"
                    ),
                    locator=f"{rel}:{call_line}",
                )
            )
    else:
        findings.append(
            Finding(
                rule_id=RULE_ID,
                severity=Severity.ERROR,
                message=(
                    f"dim_date generate_series step '{step_arg.strip()}' is not a "
                    "classifiable literal INTERVAL (INTERVAL '1 day' or "
                    "'1 day'::interval); an unclassifiable step cannot be proven "
                    "daily and must not pass by default"
                ),
                locator=f"{rel}:{call_line}",
            )
        )

    # --- bounds-order check (FR-005) -- only when BOTH bounds are literal dates ---
    # Compare CHRONOLOGICALLY (parsed dates), never lexically: PostgreSQL accepts
    # non-zero-padded literals (2022-1-9) whose string order != date order.
    start_raw = _classify_date_literal(start_arg)
    end_raw = _classify_date_literal(end_arg)
    start_date = _parse_date_literal(start_arg)
    end_date = _parse_date_literal(end_arg)
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            findings.append(
                Finding(
                    rule_id=RULE_ID,
                    severity=Severity.ERROR,
                    message=(
                        f"dim_date generate_series bounds are reversed: start "
                        f"'{start_raw}' is after end '{end_raw}' -- an inverted "
                        "literal range silently produces zero rows in PostgreSQL"
                    ),
                    locator=f"{rel}:{call_line}",
                )
            )

    return findings


@register(RULE_ID, "gold date dim is contiguous/gap-free")
def check_hr8(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if is_test_path(rel):
            continue
        if not rel.startswith("warehouse/migrations/"):
            continue
        try:
            raw = _read(ctx, rel)
        except OSError:
            continue
        for start_off, end_off in _qualifying_statement_spans(rel, raw):
            findings.extend(_check_statement(rel, raw, start_off, end_off))
    return findings
