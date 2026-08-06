"""S6/S8 -- the gold dim `-1` unknown-member pair, and the text scrubber they need.

Split out of ``rules/sql.py`` (which crossed the 800-line ceiling when S9 landed).
The fault line is the SCANNING TECHNIQUE, not the rule numbering: every other
S-family rule reads the ``tokenize_sql`` token stream, but the token lexer drops
numeric literals, so a `-1` member is invisible in token space. S6 and S8 are the
two rules that must therefore scan noise-stripped RAW TEXT, and
``_strip_sql_noise`` below is theirs alone -- it has no other caller in the tree.

S6 and S8 are complementary halves of one decision: every `gold.dim_*` SHOULD
carry a `-1` unknown member (RC14, WARNING), except a `gold.dim_date*`, which must
NOT (a marked date table rejects null/sentinel keys, ERROR). They are kept in one
module because they share the regex pair, the scrubber, and that exemption.

S9 stayed in ``rules/sql.py``: it matches on ``strip_sql_comments`` text, which
PRESERVES string literals, so it is not a client of this scrubber.
"""

from __future__ import annotations

import re

from ..core import Finding, RuleContext, Severity
from ..registry import register
from ..sql import WAREHOUSE_SQL_CORPUS, _dollar_quote_end
from .sql import line_at, live_sql_files, read_sql_text


def _strip_sql_noise(text: str) -> str:
    """Remove -- and /* */ comments and collapse string literals to ''.

    The token lexer drops numeric literals, so RC14's `-1` member can
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
        consumed = _consume_noise_at(text, i)
        if consumed is None:
            out.append(text[i])
            i += 1
            continue
        emitted, i = consumed
        out.append(emitted)
    return "".join(out)


def _consume_noise_at(text: str, i: int) -> tuple[str, int] | None:
    """The scrubbed replacement for the noise construct opening at `text[i]`, or
    None if `text[i]` opens none and should be copied through verbatim.

    Recognition order matters: a comment marker is checked before a quote, so
    `-- it's` is a comment rather than an unterminated literal.
    """
    if text.startswith("--", i):
        return _consume_line_comment(text, i)
    if text.startswith("/*", i):
        return _consume_block_comment(text, i)
    if text[i] == "$":
        # None when this is not a dollar-quote opener (e.g. `$1`), which the
        # caller then copies through -- a `$` is never a quote character.
        return _consume_dollar_quote(text, i)
    if text[i] in ("'", '"'):
        return _consume_quoted_string(text, i)
    return None


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


def _dims_with_minus1_member(clean: str) -> set[str]:
    """Lowercased `dim_*` names that receive a -1-member INSERT in `clean`."""
    return {m.group(1).lower() for m in _INSERT_GOLD_DIM_MINUS1.finditer(clean)}


@register(
    "S6",
    "gold dim -1 unknown member (enforces ADR RC14)",
    requires=(WAREHOUSE_SQL_CORPUS,),
)
def s6_gold_unknown_member(ctx: RuleContext) -> list[Finding]:
    """Each `gold.dim_*` should carry a `-1` unknown member (RC14).

    Static and PARTIAL (per the compliance matrix): proves a `-1`-valued INSERT
    exists for each created `gold.dim_*`, not full referential correctness (that
    is the live `retail validate` surface). Operates on noise-stripped raw text
    (comments/strings removed) because the token lexer drops numeric literals, so
    `-1` is invisible in token space. WARNING (reviewable; never blocks).
    """
    findings: list[Finding] = []
    for rel in live_sql_files(ctx):
        clean = _strip_sql_noise(read_sql_text(ctx, rel))
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
                    locator=f"{rel}:{line_at(clean, m.start())}",
                )
            )
    return findings


@register(
    "S8",
    "date dim has no -1/NULL unknown member (marked date table)",
    requires=(WAREHOUSE_SQL_CORPUS,),
)
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
    for rel in live_sql_files(ctx):
        clean = _strip_sql_noise(read_sql_text(ctx, rel))
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
                    locator=f"{rel}:{line_at(clean, m.start())}",
                )
            )
    return findings
