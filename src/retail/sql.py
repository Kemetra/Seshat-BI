from __future__ import annotations

import re
from dataclasses import dataclass

from .core import RuleContext

_SCHEMA_TOKENS = ("raw", "marts", "bronze", "silver")

# Zone tokens for schema_zone detection only.
# NOTE: gold is intentionally NOT in _SCHEMA_TOKENS (it's the non-stale schema),
# but schema_zone must recognize it as a distinct zone.
_ZONE_TOKENS = ("bronze", "silver", "gold")

# DDL verb modifier keywords that appear between verb and target name.
# schema_zone skips these to find the first real target identifier.
_DDL_MODIFIERS = frozenset(
    {
        "TABLE",
        "VIEW",
        "MATERIALIZED",
        "INDEX",
        "SEQUENCE",
        "SCHEMA",
        "OR",
        "REPLACE",
        "IF",
        "NOT",
        "EXISTS",
        "TEMP",
        "TEMPORARY",
        "UNIQUE",
        "CONCURRENTLY",
        "ONLY",
    }
)


@dataclass(frozen=True)
class SqlToken:
    text: str
    line: int


# A PostgreSQL dollar-quote OPENING tag: `$$` or `$tag$` where tag is an
# identifier (letter/underscore start). `$1`/`$2` positional params are NOT
# tags -- the char after the optional identifier must be `$`, and a digit-led
# `$1` fails this, so it is never treated as a span opener.
_DOLLAR_TAG = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")
# PG's identifier-continuation class includes `$`, so a `$` glued to a preceding
# identifier char (`a$b$c`) is identifier text, not a tag opener (ASCII subset of
# scan.l's ident_cont `[A-Za-z0-9_$\200-\377]`).
_IDENT_CONT = re.compile(r"[A-Za-z0-9_$]")


def _dollar_quote_end(text: str, i: int) -> int | None:
    """If a dollar-quote span opens at ``text[i]`` (a `$`), return the index just
    past its CLOSING tag; otherwise return ``None``.

    Shared by all three SQL strippers so the close-tag-matching grammar lives in
    one place. The closing tag is the EXACT opening tag string -- e.g. an inner
    `$other$` inside a `$$ ... $$` span is body text, not a terminator. An
    unterminated span fails closed to EOF (returns ``len(text)``), mirroring the
    existing quote/comment branches.

    A `$` glued to a preceding identifier-continuation char does NOT open a span:
    PG lexes `a$b$c` as one identifier, so opening there would swallow real SQL to
    EOF (a regression vs the bare lexer). The ``i > 0`` check also guards ``i == 0``
    from reading ``text[-1]`` as a wrap-around index.
    """
    if i > 0 and _IDENT_CONT.match(text[i - 1]):
        return None  # `$` inside/after an identifier (e.g. `a$b$c`) is not a tag
    m = _DOLLAR_TAG.match(text, i)
    if not m:
        return None  # e.g. `$1` positional param -> caller handles normally
    open_tag = m.group(0)
    j = text.find(open_tag, m.end())
    return len(text) if j == -1 else j + len(open_tag)


def tokenize_sql(text: str) -> list[SqlToken]:
    """Tokenize SQL, dropping comments and string-literal contents.

    Each token keeps its 1-based source line so rules can emit path:line.
    String literals collapse to an empty-text placeholder token so no inner
    word leaks into rule matching while position is preserved.
    """
    tokens: list[SqlToken] = []
    i, line, n = 0, 1, len(text)
    word = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[().,;*]")
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch.isspace():
            i += 1
            continue
        if text.startswith("--", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i)
            line += text.count("\n", i, n if j == -1 else j)
            i = n if j == -1 else j + 2
            continue
        if ch in ("'", '"'):
            j = text.find(ch, i + 1)
            end = n if j == -1 else j
            line += text.count("\n", i, end)
            tokens.append(SqlToken("", line))
            i = n if j == -1 else j + 1
            continue
        if ch == "$":
            end = _dollar_quote_end(text, i)
            if end is not None:
                # A PL/pgSQL body collapses to a placeholder token (like a string
                # literal) so no inner word leaks; line accounting spans the body.
                line += text.count("\n", i, end)
                tokens.append(SqlToken("", line))
                i = end
                continue
            # not a dollar-quote opener (e.g. `$1`); fall through to skip the `$`.
        m = word.match(text, i)
        if m:
            tokens.append(SqlToken(m.group(0), line))
            i = m.end()
            continue
        i += 1
    return tokens


def strip_sql_comments(text: str) -> str:
    """Blank out `--` and `/* */` comments, PRESERVING line structure + quoted
    identifiers AND string literals.

    Unlike ``tokenize_sql`` (which also collapses quoted identifiers to an empty
    token), this keeps `'...'` literals and `"..."`/`[...]` identifiers intact so an
    identifier-level rule (S1) can still inspect them -- it only removes comment
    spans, replacing each removed character that is not a newline with a space so
    every line number and column outside comments is unchanged.

    Quote state is TRACKED (2026-06-25 Codex review fix): a `--` or `/*` that
    appears INSIDE a `'...'` string literal or a `"..."` quoted identifier is data,
    not a comment marker, and is copied through verbatim. Without this, a `'--'`
    literal opened a phantom comment that blanked the rest of the line -- hiding any
    real bad quoted identifier after it (an S1 false negative). PostgreSQL escapes a
    quote by doubling it (`''` / `""`) inside the same literal; that is handled by
    re-opening immediately, which leaves the doubled quotes (and the span) intact --
    correct for comment-stripping, whose only job is to neutralize comments.
    """
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        # Inside a quoted span, copy through until the matching close quote; never
        # interpret a comment marker here.
        if ch in ("'", '"'):
            out.append(ch)
            i += 1
            while i < n:
                out.append(text[i])
                if text[i] == ch:
                    i += 1
                    break
                i += 1
            continue
        if ch == "$":
            end = _dollar_quote_end(text, i)
            if end is not None:
                # Blank a PL/pgSQL body (a `--`/quoted-ident inside it is data, not
                # code) but keep columns + newlines so line numbers downstream hold.
                span = text[i:end]
                out.append("".join("\n" if c == "\n" else " " for c in span))
                i = end
                continue
            # not a dollar-quote opener (e.g. `$1`); copy the `$` through below.
        if text.startswith("--", i):
            j = text.find("\n", i)
            end = n if j == -1 else j
            out.append(
                " " * (end - i)
            )  # keep columns; newline (if any) added next loop
            i = end
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i)
            end = n if j == -1 else j + 2
            span = text[i:end]
            # preserve newlines inside the block so line numbers downstream hold
            out.append("".join("\n" if c == "\n" else " " for c in span))
            i = end
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def iter_sql_files(ctx: RuleContext) -> list[str]:
    """Repo-relative POSIX paths of tracked warehouse SQL files."""
    return sorted(
        p
        for p in ctx.tracked_files
        if p.startswith("warehouse/") and p.endswith(".sql")
    )


def stale_schema_tokens(text: str) -> list[tuple[str, int]]:
    """Find raw/marts/bronze/silver in schema-qualifying positions only."""
    toks = [t for t in tokenize_sql(text) if t.text]
    hits: list[tuple[str, int]] = []
    for idx, tok in enumerate(toks):
        low = tok.text.lower()
        if low not in _SCHEMA_TOKENS:
            continue
        prev = toks[idx - 1].text.upper() if idx else ""
        prev2 = toks[idx - 2].text.upper() if idx >= 2 else ""
        nxt = toks[idx + 1].text if idx + 1 < len(toks) else ""
        after_create_schema = prev == "SCHEMA" and prev2 == "CREATE"
        after_from_join = prev in ("FROM", "JOIN")
        schema_qualifier = nxt == "."
        if after_create_schema or after_from_join or schema_qualifier:
            hits.append((low, tok.line))
    return hits


def schema_zone(toks: list[SqlToken], stmt_start_idx: int) -> str:
    """Return the schema zone of the DDL target object.

    Given a token list and the index of the DDL verb (CREATE/ALTER/DROP),
    locate the target object's schema qualifier and return one of:
        "bronze" | "silver" | "gold" | "unknown"

    Rules:
    - Only inspects tokens up to the next ";" (statement boundary) to prevent
      leakage from a preceding SET search_path statement.
    - For CREATE/DROP INDEX, the target is the TABLE after the ON keyword,
      not the index name itself.
    - Only an explicitly detected <zone>.<name> pattern earns a zone.
      An unqualified target, a search_path-only qualification, or anything
      ambiguous returns "unknown" (fail-closed).
    """
    n = len(toks)
    # Collect this statement's tokens up to (not including) the next ";".
    stmt: list[SqlToken] = []
    for i in range(stmt_start_idx, n):
        if toks[i].text == ";":
            break
        stmt.append(toks[i])

    if not stmt:
        return "unknown"

    verb = stmt[0].text.upper()
    stmt_texts_upper = [t.text.upper() for t in stmt]

    # Special case: CREATE INDEX / DROP INDEX -> zone is from the TABLE after ON.
    # Detect: verb is CREATE/DROP and a modifier keyword INDEX is present before ON.
    is_index_ddl = (
        verb in ("CREATE", "DROP")
        and "INDEX" in stmt_texts_upper
        and "ON" in stmt_texts_upper
    )
    if is_index_ddl:
        on_pos = stmt_texts_upper.index("ON")
        # Token after ON should be <schema>.<name> or just <name>
        if on_pos + 1 < len(stmt):
            candidate = stmt[on_pos + 1].text.lower()
            if candidate in _ZONE_TOKENS:
                # Check for the dot after it
                if on_pos + 2 < len(stmt) and stmt[on_pos + 2].text == ".":
                    return candidate
        return "unknown"

    # General case: skip the verb and any modifier keywords to find the target.
    # Walk forward from position 1 (skip verb), skip modifiers/keywords.
    pos = 1
    while pos < len(stmt) and stmt[pos].text.upper() in _DDL_MODIFIERS:
        pos += 1

    # At pos we should have the first "real" identifier.
    if pos >= len(stmt):
        return "unknown"

    candidate = stmt[pos].text.lower()
    if candidate in _ZONE_TOKENS:
        # Must be followed by "." to be a schema qualifier.
        if pos + 1 < len(stmt) and stmt[pos + 1].text == ".":
            return candidate

    return "unknown"
