"""SQL rules (S1–S8, plus D8 schema tokens). Added in M2; stub for M1.6 wiring."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from ..core import Finding, RuleContext, Severity, is_test_path, read_tracked_text
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
    """Return the text of tracked SQL file `rel`, or "" if it is absent on disk.

    A tracked-but-deleted-on-disk file (#430, e.g. deleted-but-unstaged) has no
    content to scan; every S-family rule treats empty text as "nothing to flag"
    (no identifiers/tokens/DDL to match), so returning "" is a silent no-finding
    skip rather than a crash. This is a content scan, not a presence check.
    """
    return read_tracked_text(ctx.repo_root / rel) or ""


def _tokens(ctx: RuleContext, rel: str) -> list[SqlToken]:
    """Non-empty (comment/string-stripped) tokens for `rel`. Shared by the
    token-based rules (S3/S4b/S5/S7) so each stops re-deriving this filter.
    """
    return [t for t in tokenize_sql(_read(ctx, rel)) if t.text]


def _live_sql_files(ctx: RuleContext) -> list[str]:
    """Tracked warehouse SQL files, excluding committed test fixtures.

    Shared preamble for the "live scan" rules (S5/S6/S7/S8): each rule skips
    `tests/` paths before scanning. S4b intentionally does NOT use this -- it
    has no `is_test_path` skip of its own -- so it keeps its own iteration.
    """
    return [rel for rel in iter_sql_files(ctx) if not is_test_path(rel)]


def _s1_findings_for_text(rel: str, text: str) -> list[Finding]:
    """S1 findings for one file's already comment-stripped `text`.

    Scans each line for quoted/bracketed identifiers and flags any that is not
    snake_case.
    """
    findings: list[Finding] = []
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


@register("S1", "snake_case SQL identifiers")
def s1_snake_case_identifiers(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        # Strip comments first (preserving line numbers + quoted identifiers) so a
        # double-quoted phrase inside a -- or /* */ comment is not mistaken for a
        # non-snake_case identifier. Real "..."/[...] identifiers in code survive.
        findings.extend(_s1_findings_for_text(rel, strip_sql_comments(_read(ctx, rel))))
    return findings


def _s2_findings_for_file(rel: str, text: str) -> list[Finding]:
    """S2 findings for one file's raw `text`: stale `raw`/`marts` schema tokens."""
    findings: list[Finding] = []
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


@register("S2", "medallion schema names")
def s2_medallion_schemas(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        if rel in EXEMPT_S2:
            continue
        findings.extend(_s2_findings_for_file(rel, _read(ctx, rel)))
    return findings


def _s3_view_name_token(toks: list[SqlToken], idx: int) -> SqlToken | None:
    """Resolve the view-name token for a `VIEW` keyword at toks[idx], or None.

    The view name is the next token; None if there is no next token. A schema
    qualifier (`gold.vw_x`) puts the name two further ahead -- skip the schema
    token and the `.`.
    """
    nxt = toks[idx + 1] if idx + 1 < len(toks) else None
    if nxt is None:
        return None
    # gold.vw_x -> name token is two ahead (skip "gold" and ".")
    if idx + 3 < len(toks) and toks[idx + 2].text == ".":
        return toks[idx + 3]
    return nxt


@register("S3", "vw_ prefix on views")
def s3_vw_prefix(ctx: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for rel in iter_sql_files(ctx):
        toks = _tokens(ctx, rel)
        for idx, tok in enumerate(toks):
            if tok.text.upper() != "VIEW":
                continue
            name_tok = _s3_view_name_token(toks, idx)
            if name_tok is None:
                continue
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


_DDL_VERBS = frozenset({"CREATE", "ALTER", "DROP"})


_TXN_BOUNDARY_VERBS = frozenset({"BEGIN", "START", "COMMIT", "ROLLBACK"})


# Tokens that CLOSE an open DDL statement. `;` is the SQL terminator; the psql
# buffer-sending meta-commands `\g`, `\gx`, `\gexec` are documented as equivalent to
# `;` (they send the current query buffer to the server) and a `psql -f` migration
# may legitimately use them instead of `;`. The tokenizer preserves the backslash
# (see sql.py::_scan_meta_command), so each is a distinct terminator token here and
# an unguarded `DROP TABLE bronze.x \g` followed by another statement is NOT masked
# as a sub-clause. Scope note: only the buffer-SENDING family terminates; `\set`,
# `\i`, `\echo` etc. do not send the buffer and are (correctly) not terminators.
# psql meta-command reference: https://www.postgresql.org/docs/current/app-psql.html
_STATEMENT_TERMINATORS = frozenset({";", "\\g", "\\gx", "\\gexec"})


def _txn_boundary_state(toks: list[SqlToken], idx: int, in_txn: bool) -> bool | None:
    """If toks[idx] is a transaction-boundary keyword, return the (possibly
    unchanged) `in_txn` state to carry forward; otherwise return None (not a
    boundary token -- caller proceeds to the DDL-verb check).

    `BEGIN` opens a txn; `START` only opens one when followed by `TRANSACTION`
    -- a bare `START` (e.g. `CREATE SEQUENCE ... START WITH 1`) must NOT
    suppress later bare-DDL findings (audit 2026-06-26 false-negative), so a
    bare `START` returns the state UNCHANGED (still a boundary -- it must not
    fall through to the DDL check). `COMMIT`/`ROLLBACK` close a txn.
    """
    upper = toks[idx].text.upper()
    if upper not in _TXN_BOUNDARY_VERBS:
        return None
    if upper == "BEGIN":
        return True
    if upper == "START":
        nxt = toks[idx + 1].text.upper() if idx + 1 < len(toks) else ""
        return True if nxt == "TRANSACTION" else in_txn
    return False  # COMMIT / ROLLBACK


def _s4b_finding_for_bare_ddl(
    rel: str, tok: SqlToken, upper: str, zone: str
) -> Finding:
    """Build the S4b Finding for a bare (unguarded) DDL verb outside bronze's
    ERROR path -- i.e. the silver/gold-no-txn WARNING or the unknown/
    unqualified fail-closed WARNING. Bronze's ERROR is built by the caller.
    """
    if zone in ("silver", "gold"):
        message = (
            f"S4b {zone}.* bare {upper} not in a transaction; "
            "wrap in BEGIN/COMMIT or use a guarded form "
            "(IF [NOT] EXISTS / OR REPLACE VIEW)"
        )
    else:
        message = (
            f"S4b bare {upper}: target schema undetermined "
            "(unqualified or search_path); use a qualified "
            "name + guarded form, or wrap in BEGIN/COMMIT"
        )
    return Finding(
        rule_id="S4b",
        severity=Severity.WARNING,
        message=message,
        locator=f"{rel}:{tok.line}",
    )


def _is_statement_start_verb(stmt_open: bool) -> bool:
    """True when a DDL verb STARTS a statement, not a sub-clause.

    A DDL keyword STARTS a statement unless a DDL statement is already open --
    i.e. a prior statement-starting DDL verb has not yet been closed by ``;``.
    ``stmt_open`` carries that state from the caller's single left-to-right walk.
    The same keyword appearing while a statement is open is a sub-clause, not a
    new statement: `ALTER TABLE gold.t ALTER COLUMN c ...` carries a SECOND
    `ALTER` whose target (the column) has no schema qualifier, so re-evaluating it
    as a top-level verb yielded a spurious "target schema undetermined" S4b
    warning even though the statement is schema-qualified and txn-wrapped (#442).
    Only the leading `ALTER` governs the statement -- regardless of whether the
    sub-clause sits on the same physical line or a wrapped one.

    Tracking open-vs-closed (rather than the previous token) also closes a hole a
    naive `prev == ";"` check left: a line-oriented psql meta-command such as
    `\\set ON_ERROR_STOP on` carries no ``;`` (warehouse/README.md applies these
    files with `psql -f`). With no statement open, the following `DROP TABLE
    bronze.x` is correctly a NEW statement start and still fires the
    bronze-source-of-truth ERROR. The buffer-sending meta-commands `\\g`/`\\gx`/
    `\\gexec` are the converse case: they DO close the current statement (they send
    the query buffer, like ``;``), so they are members of `_STATEMENT_TERMINATORS`
    and an unguarded `DROP TABLE bronze.x \\g` before another statement is not
    masked as a sub-clause. The tokenizer preserves the backslash so `\\g` is a
    distinct token, not an identifier `g`.
    """
    return not stmt_open


@dataclass(frozen=True)
class _S4bScanState:
    """The two flags a single left-to-right S4b walk carries: whether a
    BEGIN/COMMIT transaction is open, and whether a DDL statement is open
    (a statement-starting DDL verb not yet closed by ``;``, #442). Bundled so
    the per-verb evaluator receives the scan state as one value.
    """

    in_txn: bool
    stmt_open: bool


def _s4b_ddl_finding(
    rel: str, toks: list[SqlToken], idx: int, state: _S4bScanState
) -> Finding | None:
    """The S4b finding for the DDL verb at ``idx``, or ``None`` when it passes.

    Passes (returns ``None``) when the verb is not a statement-starting DDL verb
    (a mid-statement sub-clause keyword like the inner ALTER of `ALTER COLUMN`
    while a statement is already open, #442), is a guarded form, or is a
    silver/gold statement inside a transaction (the idempotent DROP+CREATE rebuild
    pattern). bronze bare DDL is an ERROR; everything else is the WARNING built by
    ``_s4b_finding_for_bare_ddl``.
    """
    if not _is_statement_start_verb(state.stmt_open) or _is_guarded(toks, idx):
        return None
    upper = toks[idx].text.upper()
    tok = toks[idx]
    zone = schema_zone(toks, idx)
    if zone == "bronze":
        return Finding(
            rule_id="S4b",
            severity=Severity.ERROR,
            message=(
                f"S4b bronze.* bare {upper} destroys/clobbers source-of-truth; "
                "use a guarded form (IF [NOT] EXISTS)"
            ),
            locator=f"{rel}:{tok.line}",
        )
    if zone in ("silver", "gold") and state.in_txn:
        return None  # DROP+CREATE-in-transaction pattern: PASS (idempotent rebuild)
    return _s4b_finding_for_bare_ddl(rel, tok, upper, zone)


def _s4b_findings_for_file(rel: str, toks: list[SqlToken]) -> list[Finding]:
    """S4b findings for one file's already-tokenized content."""
    findings: list[Finding] = []
    in_txn = False  # stateful flag toggled by BEGIN / COMMIT / ROLLBACK
    stmt_open = False  # a DDL statement is open until its `;` (sub-clause tracking)

    for idx, tok in enumerate(toks):
        if tok.text in _STATEMENT_TERMINATORS:
            stmt_open = False  # `;` or a buffer-sending psql meta-command (\g/\gx)
            continue
        boundary_state = _txn_boundary_state(toks, idx, in_txn)
        if boundary_state is not None:
            in_txn = boundary_state
            continue
        if tok.text.upper() not in _DDL_VERBS:
            continue
        state = _S4bScanState(in_txn=in_txn, stmt_open=stmt_open)
        finding = _s4b_ddl_finding(rel, toks, idx, state)
        if finding is not None:
            findings.append(finding)
        # A statement-starting DDL verb opens a statement (until its `;`); a
        # sub-clause DDL keyword while one is already open does not change state.
        stmt_open = True

    return findings


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
    for rel in iter_sql_files(ctx):
        findings.extend(_s4b_findings_for_file(rel, _tokens(ctx, rel)))
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


def _s5_cast_source(toks: list[SqlToken], idx: int) -> tuple[str, bool]:
    """Return (cast source identifier text, is_cast_position) for toks[idx].

    The cast source is the identifier right before the type token, or (for
    `CAST(x AS t)`) the token two back, after an AS.
    """
    prev = toks[idx - 1].text if idx else ""
    is_cast_position = bool(prev) and prev not in ("(", ",", ";", ")")
    if prev.upper() == "AS":
        src = toks[idx - 2].text if idx >= 2 else ""
    else:
        src = prev
    return src, is_cast_position


def _s5_finding_for_cast(rel: str, tok: SqlToken, src: str) -> Finding | None:
    """S5 Finding for a type-token cast, or None if it's not a flagged cast."""
    low = tok.text.lower()
    if low in _FLOAT_TYPES:
        return Finding(
            rule_id="S5",
            severity=Severity.WARNING,
            message=(
                f"{src or 'value'} cast to {tok.text}; money/quantities "
                "must be exact NUMERIC, never float (enforces RC7)"
            ),
            locator=f"{rel}:{tok.line}",
        )
    if low in _INT_TYPES and _is_id_like(src):
        return Finding(
            rule_id="S5",
            severity=Severity.WARNING,
            message=(
                f"{src} cast to {tok.text}; id-like columns may have "
                "leading zeros and must stay TEXT (enforces RC7)"
            ),
            locator=f"{rel}:{tok.line}",
        )
    return None


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
    for rel in _live_sql_files(ctx):
        toks = _tokens(ctx, rel)
        for idx, tok in enumerate(toks):
            src, is_cast_position = _s5_cast_source(toks, idx)
            if not is_cast_position:
                continue
            finding = _s5_finding_for_cast(rel, tok, src)
            if finding is not None:
                findings.append(finding)
    return findings


def _strip_sql_noise(text: str) -> str:
    """Remove -- and /* */ comments and collapse string literals to ''.

    The token lexer drops numeric literals entirely, so RC14's `-1` member can
    only be detected from (noise-stripped) raw text. This strips comments and
    string contents so a `-1` or `dim_` inside them never produces a match,
    while preserving structure (and newlines) for line accounting.

    KNOWN GAP (audit 2026-06-26 #10, DEFERRED): this comment-first stripper differs
    from ``seshat.sql.strip_sql_comments`` (quote-first), and its `''`-escape
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
            emitted, i = _consume_line_comment(text, i)
            out.append(emitted)
            continue
        if text.startswith("/*", i):
            emitted, i = _consume_block_comment(text, i)
            out.append(emitted)
            continue
        if text[i] == "$":
            consumed = _consume_dollar_quote(text, i)
            if consumed is not None:
                emitted, i = consumed
                out.append(emitted)
                continue
            # not a dollar-quote opener (e.g. `$1`); copy the `$` through below.
        if text[i] in ("'", '"'):
            emitted, i = _consume_quoted_string(text, i)
            out.append(emitted)
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _consume_line_comment(text: str, i: int) -> tuple[str, int]:
    """Consume a `--` line comment at `text[i]`. Emits nothing; advances to the
    newline (kept, so line accounting is preserved) or to EOF.
    """
    j = text.find("\n", i)
    return "", len(text) if j == -1 else j


def _consume_block_comment(text: str, i: int) -> tuple[str, int]:
    """Consume a `/* */` block comment at `text[i]`. Emits only the newlines it
    spanned (line accounting) and advances past the closing `*/` (or to EOF).
    """
    n = len(text)
    j = text.find("*/", i)
    seg = text[i : (n if j == -1 else j + 2)]
    return "\n" * seg.count("\n"), n if j == -1 else j + 2


def _consume_dollar_quote(text: str, i: int) -> tuple[str, int] | None:
    """Consume a dollar-quoted (`$$...$$`) body at `text[i]`, or None if `text[i]`
    is not a dollar-quote opener (e.g. `$1`), in which case the caller falls
    through to the quote/default handling.

    Collapse a PL/pgSQL body to `''` so a `-1` or `dim_` inside it never reaches
    the S6/S8 raw-text scan; keep newlines for line accounting.
    """
    end = _dollar_quote_end(text, i)
    if end is None:
        return None
    seg = text[i:end]
    return "''" + "\n" * seg.count("\n"), end


def _consume_quoted_string(text: str, i: int) -> tuple[str, int]:
    """Consume a `'...'` or `"..."` string literal at `text[i]`. Emits `''` for
    the collapsed literal plus the newlines it spanned; advances past the closing
    quote (or to EOF).
    """
    n = len(text)
    q = text[i]
    j = text.find(q, i + 1)
    seg = text[i : (n if j == -1 else j + 1)]
    return "''" + "\n" * seg.count("\n"), n if j == -1 else j + 1


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


def _line_at(clean: str, offset: int) -> int:
    """1-based line number of `offset` in noise-stripped text `clean`."""
    return clean.count("\n", 0, offset) + 1


def _dims_with_minus1_member(clean: str) -> set[str]:
    """Lowercased `dim_*` names that receive a -1-member INSERT in `clean`."""
    return {m.group(1).lower() for m in _INSERT_GOLD_DIM_MINUS1.finditer(clean)}


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
    for rel in _live_sql_files(ctx):
        clean = _strip_sql_noise(_read(ctx, rel))
        with_member = _dims_with_minus1_member(clean)
        for m in _CREATE_GOLD_DIM.finditer(clean):
            dim = m.group(1).lower()
            # A date dim is the documented EXCEPTION (S8): it becomes a marked date
            # table (dataCategory: Time), which rejects nulls, so it must NOT carry a
            # -1 unknown member. Exempt it here so S6 and S8 are complementary.
            if dim.startswith("dim_date"):
                continue
            if dim in with_member:
                continue
            findings.append(
                Finding(
                    rule_id="S6",
                    severity=Severity.WARNING,
                    message=(
                        f"gold.{dim} has no -1 unknown-member INSERT; a Kimball dim "
                        "should carry an unknown member at _sk = -1 (enforces RC14)"
                    ),
                    locator=f"{rel}:{_line_at(clean, m.start())}",
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
    for rel in _live_sql_files(ctx):
        clean = _strip_sql_noise(_read(ctx, rel))
        for m in _INSERT_GOLD_DIM_MINUS1.finditer(clean):
            dim = m.group(1).lower()
            if not dim.startswith("dim_date"):
                continue
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
                    locator=f"{rel}:{_line_at(clean, m.start())}",
                )
            )
    return findings


def _statement_tokens(toks: list[SqlToken], start_idx: int) -> list[SqlToken]:
    """This statement's tokens starting at `start_idx`, up to (not including)
    the next `;`.
    """
    stmt: list[SqlToken] = []
    for j in range(start_idx, len(toks)):
        if toks[j].text == ";":
            break
        stmt.append(toks[j])
    return stmt


def _s7_is_gappy_date_dim_insert(stmt: list[SqlToken]) -> bool:
    """True if `stmt` is an INSERT targeting dim_date built via SELECT DISTINCT
    (gappy) rather than generate_series (contiguous).
    """
    if not any(t.text.lower().startswith("dim_date") for t in stmt):
        return False
    up = [t.text.upper() for t in stmt]
    has_distinct = "SELECT" in up and "DISTINCT" in up
    has_genseries = any(t.text.lower() == "generate_series" for t in stmt)
    return has_distinct and not has_genseries


@register("S7", "contiguous date dim (enforces ADR RC15)")
def s7_contiguous_date_dim(ctx: RuleContext) -> list[Finding]:
    """A `dim_date` must be a contiguous generated calendar, not SELECT DISTINCT (RC15).

    Flags an `INSERT INTO ... dim_date` whose statement uses `SELECT DISTINCT`
    (gappy) rather than `generate_series` (contiguous). Statement-scoped so a
    SELECT DISTINCT populating some other dim does not trigger. WARNING.
    """
    findings: list[Finding] = []
    for rel in _live_sql_files(ctx):
        toks = _tokens(ctx, rel)
        for idx, tok in enumerate(toks):
            if tok.text.upper() != "INSERT":
                continue
            stmt = _statement_tokens(toks, idx)
            if not _s7_is_gappy_date_dim_insert(stmt):
                continue
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
