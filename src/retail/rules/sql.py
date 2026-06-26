"""SQL rules (S1–S8, plus D8 schema tokens). Added in M2; stub for M1.6 wiring."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register
from ..sql import (
    SqlToken,
    _dollar_quote_end,
    iter_sql_files,
    schema_zone,
    stale_schema_tokens,
    strip_sql_comments,
    tokenize_sql,
)

_SNAKE = re.compile(r"^[a-z_][a-z0-9_]*$")
# quoted/bracketed identifier in a declaration position
_QUOTED = re.compile(r'"([^"]*)"|\[([^\]]*)\]')
EXEMPT_S2 = frozenset({"warehouse/README.md"})


def _read(ctx: RuleContext, rel: str) -> str:
    return (ctx.repo_root / rel).read_text(encoding="utf-8")


@register("S1", "snake_case SQL identifiers")
def s1_snake_case_identifiers(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        # Strip comments first (preserving line numbers + quoted identifiers) so a
        # double-quoted phrase inside a -- or /* */ comment is not mistaken for a
        # non-snake_case identifier. Real "..."/[...] identifiers in code survive.
        text = strip_sql_comments(_read(ctx, rel))
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in _QUOTED.finditer(line):
                ident = m.group(1) if m.group(1) is not None else m.group(2)
                if not _SNAKE.match(ident):
                    findings.append(
                        Finding(
                            rule_id="S1",
                            severity=Severity.ERROR,
                            message=f"non-snake_case identifier {ident!r}",
                            locator=f"{rel}:{lineno}",
                        )
                    )
    return findings


@register("S2", "medallion schema names")
def s2_medallion_schemas(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if rel in EXEMPT_S2:
            continue
        text = _read(ctx, rel)
        for token, line in stale_schema_tokens(text):
            if token in ("raw", "marts"):
                findings.append(
                    Finding(
                        rule_id="S2",
                        severity=Severity.ERROR,
                        message=f"stale schema {token!r}; use bronze/silver/gold",
                        locator=f"{rel}:{line}",
                    )
                )
    return findings


@register("S3", "vw_ prefix on views")
def s3_vw_prefix(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
        for idx, tok in enumerate(toks):
            if tok.text.upper() != "VIEW":
                continue
            # the view name is the next identifier; skip a schema qualifier
            nxt = toks[idx + 1] if idx + 1 < len(toks) else None
            if nxt is None:
                continue
            # gold.vw_x -> name token is two ahead (skip "gold" and ".")
            if idx + 3 < len(toks) and toks[idx + 2].text == ".":
                name_tok = toks[idx + 3]
            else:
                name_tok = nxt
            if not name_tok.text.lower().startswith("vw_"):
                findings.append(
                    Finding(
                        rule_id="S3",
                        severity=Severity.ERROR,
                        message=f"view {name_tok.text!r} missing vw_ prefix",
                        locator=f"{rel}:{name_tok.line}",
                    )
                )
    return findings


_MIGRATION_NAME = re.compile(r"^\d{4}_.+\.sql$")


@register("S4a", "migration filename + numbering")
def s4a_migration_numbering(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    migrations = [
        rel for rel in iter_sql_files(ctx) if rel.startswith("warehouse/migrations/")
    ]
    numbers: dict[int, str] = {}
    for rel in migrations:
        name = PurePosixPath(rel).name
        if not _MIGRATION_NAME.match(name):
            findings.append(
                Finding(
                    rule_id="S4a",
                    severity=Severity.ERROR,
                    message=(
                        f"migration filename {name!r} must match" r" ^\d{4}_.+\.sql$"
                    ),
                    locator=rel,
                )
            )
            continue
        num = int(name[:4])
        if num in numbers:
            findings.append(
                Finding(
                    rule_id="S4a",
                    severity=Severity.ERROR,
                    message=f"duplicate migration number {num:04d}",
                    locator=rel,
                )
            )
        else:
            numbers[num] = rel
    if numbers:
        ordered = sorted(numbers)
        for prev, cur in zip(ordered, ordered[1:]):
            if cur != prev + 1:
                findings.append(
                    Finding(
                        rule_id="S4a",
                        severity=Severity.ERROR,
                        message=(
                            f"non-contiguous migration numbering: gap between "
                            f"{prev:04d} and {cur:04d}"
                        ),
                        locator=numbers[cur],
                    )
                )
    return findings


def _is_guarded(toks: list[SqlToken], idx: int) -> bool:
    """True if the CREATE/ALTER/DROP at toks[idx] is an accepted guarded form."""
    verb = toks[idx].text.upper()
    # window of the next few keyword tokens, upper-cased
    tail = [t.text.upper() for t in toks[idx : idx + 8]]
    joined = " ".join(tail)
    if verb == "CREATE":
        # Any OR REPLACE form (VIEW / FUNCTION / PROCEDURE) is a guarded create,
        # not just VIEW -- a literal "OR REPLACE VIEW" check false-positived on
        # every CREATE OR REPLACE FUNCTION/PROCEDURE migration (audit 2026-06-26).
        return "OR REPLACE" in joined or "IF NOT EXISTS" in joined
    if verb == "ALTER":
        return "IF EXISTS" in joined or "IF NOT EXISTS" in joined
    if verb == "DROP":
        return "IF EXISTS" in joined
    return False


@register("S4b", "migration guard form")
def s4b_guard_form(ctx: RuleContext) -> list[Finding]:
    """Layer-aware guard-form check.

    Policy (per DDL statement):
      - Any guarded form (IF [NOT] EXISTS / OR REPLACE VIEW) -> PASS regardless of zone.
      - bronze bare DROP/CREATE/ALTER -> ERROR (blocks build).
      - silver/gold bare + inside a BEGIN/COMMIT transaction -> PASS.
      - silver/gold bare + NOT in a transaction -> WARNING.
      - unknown/unqualified bare -> WARNING (fail-closed).
    """
    findings: list[Finding] = []
    _DDL_VERBS = frozenset({"CREATE", "ALTER", "DROP"})

    for rel in iter_sql_files(ctx):
        toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
        in_txn = False  # stateful flag toggled by BEGIN / COMMIT / ROLLBACK

        for idx, tok in enumerate(toks):
            upper = tok.text.upper()

            # Track transaction boundaries. `BEGIN` opens a txn; `START` only
            # opens one when followed by `TRANSACTION` -- a bare `START` (e.g.
            # `CREATE SEQUENCE ... START WITH 1`) must NOT suppress later bare-DDL
            # findings (audit 2026-06-26 false-negative).
            if upper == "BEGIN":
                in_txn = True
                continue
            if upper == "START":
                nxt = toks[idx + 1].text.upper() if idx + 1 < len(toks) else ""
                if nxt == "TRANSACTION":
                    in_txn = True
                continue
            if upper in ("COMMIT", "ROLLBACK"):
                in_txn = False
                continue

            if upper not in _DDL_VERBS:
                continue

            # Guarded forms pass unconditionally (any zone).
            if _is_guarded(toks, idx):
                continue

            zone = schema_zone(toks, idx)

            if zone == "bronze":
                findings.append(
                    Finding(
                        rule_id="S4b",
                        severity=Severity.ERROR,
                        message=(
                            f"S4b bronze.* bare {upper} destroys/clobbers "
                            "source-of-truth; use a guarded form "
                            "(IF [NOT] EXISTS)"
                        ),
                        locator=f"{rel}:{tok.line}",
                    )
                )
            elif zone in ("silver", "gold"):
                if in_txn:
                    # DROP+CREATE-in-transaction pattern: PASS (idempotent rebuild).
                    continue
                findings.append(
                    Finding(
                        rule_id="S4b",
                        severity=Severity.WARNING,
                        message=(
                            f"S4b {zone}.* bare {upper} not in a transaction; "
                            "wrap in BEGIN/COMMIT or use a guarded form "
                            "(IF [NOT] EXISTS / OR REPLACE VIEW)"
                        ),
                        locator=f"{rel}:{tok.line}",
                    )
                )
            else:
                # unknown / unqualified -> fail-closed WARNING.
                findings.append(
                    Finding(
                        rule_id="S4b",
                        severity=Severity.WARNING,
                        message=(
                            f"S4b bare {upper}: target schema undetermined "
                            "(unqualified or search_path); use a qualified "
                            "name + guarded form, or wrap in BEGIN/COMMIT"
                        ),
                        locator=f"{rel}:{tok.line}",
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# S5/S6/S7 -- enforce statically-checkable ADR 0002 cleaning defaults
# (RC7 type discipline, RC14 gold -1 unknown member, RC15 contiguous date dim).
# The rule IDS stay in the checker S-family; each CITES the RC default it
# enforces. Severity is WARNING (every RC default has an "override when" clause:
# surface for review, do not block). These scan tracked warehouse SQL and use the
# tokenize_sql lexer, so comments / string literals never trigger a finding.
# ---------------------------------------------------------------------------

# Float-ish SQL type keywords (money/qty should be exact NUMERIC, never float).
_FLOAT_TYPES = frozenset({"float", "float4", "float8", "double", "real"})
# Integer type keywords whose cast can DROP leading zeros from an id (data loss).
# NOTE: smallint/int2 are intentionally EXCLUDED -- RC7 explicitly sanctions
# "ordinal line numbers with no leading zeros -> small integer", so line_no::smallint
# is correct, not a violation. Only the wider int types are the leading-zero risk.
_INT_TYPES = frozenset({"int", "int4", "int8", "integer", "bigint"})
# An identifier looks id-like (kept TEXT under RC7) if it ends in these suffixes.
_ID_SUFFIXES = ("_id", "_no", "_code", "_ref")


def _is_id_like(name: str) -> bool:
    low = name.lower()
    # exclude surrogate keys (_sk) and ordinal line numbers handled by the caller
    return any(low.endswith(s) for s in _ID_SUFFIXES)


@register("S5", "type discipline (enforces ADR RC7)")
def s5_type_discipline(ctx: RuleContext) -> list[Finding]:
    """Flag money/qty cast to a float type, or an id-like column cast to integer.

    Detection uses the lexer: a cast `col::float8` tokenizes to `[col, float8]`
    (the `::` is dropped), and `CAST(col AS bigint)` to `[CAST, (, col, AS, bigint]`.
    So a float/int TYPE token whose preceding identifier token is the cast source
    is a cast to that type. WARNING (RC7 has an "override when"); ordinal line
    numbers cast to int are an accepted false-positive the warning prompts review of.
    """
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if is_test_path(rel):
            continue
        toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
        for idx, tok in enumerate(toks):
            low = tok.text.lower()
            prev = toks[idx - 1].text if idx else ""
            prev_up = prev.upper()
            # The cast source is the identifier right before the type token,
            # or (for CAST(x AS t)) the token two back, after an AS.
            is_cast_position = bool(prev) and prev not in ("(", ",", ";", ")")
            if prev_up == "AS":
                src = toks[idx - 2].text if idx >= 2 else ""
            else:
                src = prev
            if low in _FLOAT_TYPES and is_cast_position:
                findings.append(
                    Finding(
                        rule_id="S5",
                        severity=Severity.WARNING,
                        message=(
                            f"{src or 'value'} cast to {tok.text}; money/quantities "
                            "must be exact NUMERIC, never float (enforces RC7)"
                        ),
                        locator=f"{rel}:{tok.line}",
                    )
                )
            elif low in _INT_TYPES and is_cast_position and _is_id_like(src):
                findings.append(
                    Finding(
                        rule_id="S5",
                        severity=Severity.WARNING,
                        message=(
                            f"{src} cast to {tok.text}; id-like columns may have "
                            "leading zeros and must stay TEXT (enforces RC7)"
                        ),
                        locator=f"{rel}:{tok.line}",
                    )
                )
    return findings


def _strip_sql_noise(text: str) -> str:
    """Remove -- and /* */ comments and collapse string literals to ''.

    The token lexer drops numeric literals entirely, so RC14's `-1` member can
    only be detected from (noise-stripped) raw text. This strips comments and
    string contents so a `-1` or `dim_` inside them never produces a match,
    while preserving structure (and newlines) for line accounting.

    KNOWN GAP (audit 2026-06-26 #10, DEFERRED): this comment-first stripper differs
    from ``retail.sql.strip_sql_comments`` (quote-first), and its `''`-escape
    handling mis-splits `'it''s'` into `'it'`+`'s'` cosmetically. Verified at the
    rule level: the mis-split preserves span parity (the two pseudo-strings tile the
    same region as the true literal), so NO S6/S8 verdict changes on well-formed
    SQL -- a `-1` outside the string is never swallowed and one inside never leaks.
    Unifying both strippers into one quote-first state machine (the audit's
    suggested mechanism) is design-doc §A: it has S1/S6/S8 (two ERROR rules) blast
    radius and is human-gated. Kept separate; the latent edge is regression-tested.
    """
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text.startswith("--", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i)
            seg = text[i : (n if j == -1 else j + 2)]
            out.append("\n" * seg.count("\n"))  # keep line count
            i = n if j == -1 else j + 2
            continue
        if text[i] == "$":
            end = _dollar_quote_end(text, i)
            if end is not None:
                # Collapse a PL/pgSQL body so a `-1` or `dim_` inside it never
                # reaches the S6/S8 raw-text scan; keep newlines for line accounting.
                seg = text[i:end]
                out.append("''" + "\n" * seg.count("\n"))
                i = end
                continue
            # not a dollar-quote opener (e.g. `$1`); copy the `$` through below.
        if text[i] in ("'", '"'):
            q = text[i]
            j = text.find(q, i + 1)
            seg = text[i : (n if j == -1 else j + 1)]
            out.append("''" + "\n" * seg.count("\n"))
            i = n if j == -1 else j + 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


_CREATE_GOLD_DIM = re.compile(
    r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?gold\.(dim_\w+)", re.IGNORECASE
)
# An INSERT INTO gold.dim_x whose statement (up to ';') seeds a -1 member in the
# VALUES KEY position -- i.e. `... VALUES (-1, ...)` (the surrogate key column).
# Anchoring on the VALUES-position -1 (not -1 ANYWHERE) is shared by S6 (entity dims
# must HAVE such a member) and S8 (date dims must NOT), and excludes arithmetic like
# `extract(month FROM d) - 1` which is not an unknown-member insert (Codex review:
# S8 is ERROR, so a loose `-1`-anywhere match would block a valid calendar). Both
# `VALUES (-1, ...)` and `OVERRIDING SYSTEM VALUE VALUES (-1, ...)` match.
_INSERT_GOLD_DIM_MINUS1 = re.compile(
    r"\bINSERT\s+INTO\s+gold\.(dim_\w+)\b[^;]*?\bVALUES\s*\(\s*-\s*1\b",
    re.IGNORECASE | re.DOTALL,
)


@register("S6", "gold dim -1 unknown member (enforces ADR RC14)")
def s6_gold_unknown_member(ctx: RuleContext) -> list[Finding]:
    """Each `gold.dim_*` should carry a `-1` unknown member (RC14).

    Static and PARTIAL (per the compliance matrix): proves a `-1`-valued INSERT
    exists for each created `gold.dim_*`, not full referential correctness (that
    is the live `retail validate` surface). Operates on noise-stripped raw text
    (comments/strings removed) because the token lexer drops numeric literals, so
    `-1` is invisible in token space. WARNING (reviewable; never blocks).
    """
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if is_test_path(rel):
            continue
        clean = _strip_sql_noise(_read(ctx, rel))
        # dims that receive a -1 member insert
        with_member = {
            m.group(1).lower() for m in _INSERT_GOLD_DIM_MINUS1.finditer(clean)
        }
        for m in _CREATE_GOLD_DIM.finditer(clean):
            dim = m.group(1).lower()
            # A date dim is the documented EXCEPTION (S8): it becomes a marked date
            # table (dataCategory: Time), which rejects nulls, so it must NOT carry a
            # -1 unknown member. Exempt it here so S6 and S8 are complementary.
            if dim.startswith("dim_date"):
                continue
            if dim in with_member:
                continue
            line = clean.count("\n", 0, m.start()) + 1
            findings.append(
                Finding(
                    rule_id="S6",
                    severity=Severity.WARNING,
                    message=(
                        f"gold.{dim} has no -1 unknown-member INSERT; a Kimball dim "
                        "should carry an unknown member at _sk = -1 (enforces RC14)"
                    ),
                    locator=f"{rel}:{line}",
                )
            )
    return findings


@register("S8", "date dim has no -1/NULL unknown member (marked date table)")
def s8_date_dim_no_unknown_member(ctx: RuleContext) -> list[Finding]:
    """A `gold.dim_date*` must NOT carry a `-1`/NULL unknown member (inverse of S6).

    Codex PR review #1 (2026-06-25): a date dim destined to be a marked date table
    (`dataCategory: Time`) is validated by Power BI as unique/contiguous/NO-nulls.
    A `-1, NULL` unknown member lands a BLANK in the date key, so refresh or
    time-intelligence can fail even though the SQL migration succeeds and
    `retail validate` stays green (the -1 member is also a valid FK target, so date
    coverage / orphan checks do not catch it). This is the inverse of S6 (which
    REQUIRES the -1 member on every OTHER gold dim).

    ERROR severity (a hard correctness gate, not an "override-when" RC default like
    S6/S7): the bug reaches Power BI silently, which is exactly what a static gate
    must prevent. Operates on noise-stripped raw text (the lexer drops numeric
    literals, so -1 is invisible in token space). Unmatched/NULL FACT dates must be
    handled outside the marked calendar (fail-loud or a nullable FK + DAX), never by
    polluting the date table -- see ADR 0006.
    """
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if is_test_path(rel):
            continue
        clean = _strip_sql_noise(_read(ctx, rel))
        for m in _INSERT_GOLD_DIM_MINUS1.finditer(clean):
            dim = m.group(1).lower()
            if not dim.startswith("dim_date"):
                continue
            line = clean.count("\n", 0, m.start()) + 1
            findings.append(
                Finding(
                    rule_id="S8",
                    severity=Severity.ERROR,
                    message=(
                        f"gold.{dim} inserts a -1/NULL unknown member; a marked date "
                        "table (dataCategory: Time) must have NO null/sentinel key "
                        "member -- it breaks Power BI date-table validation / "
                        "time-intelligence. Handle unmatched fact dates outside the "
                        "calendar (fail-loud or nullable FK), not with a -1 member."
                    ),
                    locator=f"{rel}:{line}",
                )
            )
    return findings


@register("S7", "contiguous date dim (enforces ADR RC15)")
def s7_contiguous_date_dim(ctx: RuleContext) -> list[Finding]:
    """A `dim_date` must be a contiguous generated calendar, not SELECT DISTINCT (RC15).

    Flags an `INSERT INTO ... dim_date` whose statement uses `SELECT DISTINCT`
    (gappy) rather than `generate_series` (contiguous). Statement-scoped so a
    SELECT DISTINCT populating some other dim does not trigger. WARNING.
    """
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if is_test_path(rel):
            continue
        toks = [t for t in tokenize_sql(_read(ctx, rel)) if t.text]
        for idx, tok in enumerate(toks):
            if tok.text.upper() != "INSERT":
                continue
            # collect this statement's tokens (up to next ';')
            stmt: list[SqlToken] = []
            for j in range(idx, len(toks)):
                if toks[j].text == ";":
                    break
                stmt.append(toks[j])
            up = [t.text.upper() for t in stmt]
            targets_dim_date = any(t.text.lower().startswith("dim_date") for t in stmt)
            if not targets_dim_date:
                continue
            has_distinct = "SELECT" in up and "DISTINCT" in up
            has_genseries = any(t.text.lower() == "generate_series" for t in stmt)
            if has_distinct and not has_genseries:
                findings.append(
                    Finding(
                        rule_id="S7",
                        severity=Severity.WARNING,
                        message=(
                            "dim_date built from SELECT DISTINCT; use a contiguous "
                            "generate_series calendar over the full span (enforces "
                            "RC15) -- missing days break time-intelligence"
                        ),
                        locator=f"{rel}:{tok.line}",
                    )
                )
    return findings
