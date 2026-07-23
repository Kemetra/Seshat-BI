from __future__ import annotations

import re
from collections.abc import Callable
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


def _line_comment_end(text: str, i: int) -> int:
    """Index of the newline terminating a ``--`` comment opening at ``text[i]``.

    The newline itself is NOT consumed (callers re-process it for line
    accounting). An unterminated comment fails closed to EOF.
    """
    j = text.find("\n", i)
    return len(text) if j == -1 else j


def _block_comment_end(text: str, i: int) -> int:
    """Index just past the ``*/`` closing a ``/* */`` comment opening at ``text[i]``.

    An unterminated block comment fails closed to EOF.
    """
    j = text.find("*/", i)
    return len(text) if j == -1 else j + 2


def _quoted_span_end(text: str, i: int) -> int:
    """Index just past the close quote of a ``'...'``/``"..."`` span at ``text[i]``.

    ``text[i]`` is the opening quote. Returns the index after the matching close
    quote, or EOF if unterminated. A PG doubled-quote escape (``''``/``""``) is
    left as two adjacent spans -- this reproduces the existing behavior exactly and
    is correct for comment-stripping (whose only job is to neutralize comments).
    """
    ch = text[i]
    j = text.find(ch, i + 1)
    return len(text) if j == -1 else j + 1


def _blank_span(span: str) -> str:
    """Map each char in ``span`` to a space, keeping newlines, so downstream line
    numbers and columns outside the removed span are unchanged."""
    return "".join("\n" if c == "\n" else " " for c in span)


# ``tokenize_sql`` branch producers. Each takes ``(text, i, line)`` where ``text[i]``
# opens the span, and returns ``(token_or_None, new_line, next_i)``: the placeholder
# token to emit (or ``None`` when the span produces no token), the updated 1-based
# line after crossing the span, and the index to resume scanning from. Line
# accounting lives here so the main loop is a flat dispatcher.


def _scan_line_comment(
    text: str, i: int, line: int
) -> tuple[SqlToken | None, int, int]:
    """A ``--`` comment: emits no token; a single-line span never changes ``line``."""
    return None, line, _line_comment_end(text, i)


def _scan_block_comment(
    text: str, i: int, line: int
) -> tuple[SqlToken | None, int, int]:
    """A ``/* */`` comment: emits no token; ``line`` advances past inner newlines."""
    end = _block_comment_end(text, i)
    return None, line + text.count("\n", i, end), end


def _scan_quoted_token(
    text: str, i: int, line: int
) -> tuple[SqlToken | None, int, int]:
    """A ``'...'``/``"..."`` span collapses to an empty-text placeholder token so no
    inner word leaks; ``line`` is advanced to the token's end line."""
    end = _quoted_span_end(text, i)
    new_line = line + text.count("\n", i, end)
    return SqlToken("", new_line), new_line, end


def _scan_dollar_token(
    text: str, i: int, line: int
) -> tuple[SqlToken | None, int, int]:
    """A ``$$``/``$tag$`` PL/pgSQL body collapses to a placeholder token (like a
    string literal) so no inner word leaks; line accounting spans the body.

    Returns ``(None, line, i)`` unchanged when ``text[i]`` is NOT a dollar-quote
    opener (e.g. ``$1``), signalling the caller to fall through to word-matching.
    """
    end = _dollar_quote_end(text, i)
    if end is None:
        return None, line, i
    new_line = line + text.count("\n", i, end)
    return SqlToken("", new_line), new_line, end


_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[().,;*]")

# A psql backslash meta-command: `\` + a run of command chars (letters/digits/`?`/
# `+`). PostgreSQL's psql applies migration files with `psql -f` (warehouse/
# README.md), and the tokenizer must PRESERVE the backslash so a downstream rule can
# tell a buffer-sending meta-command (`\g`, `\gx`, `\gexec`) apart from an ordinary
# identifier named `g` -- which is impossible once the `\` is dropped. Only the
# command word is captured; its arguments are ordinary tokens on the same line.
_META_COMMAND = re.compile(r"\\[A-Za-z?]+[+]?|\\[gG][xX]?")


def _scan_meta_command(
    text: str, i: int, line: int
) -> tuple[SqlToken | None, int, int]:
    """A psql ``\\``-meta-command emits a single token with the backslash preserved
    (e.g. ``\\g``, ``\\set``), so a rule can recognize the buffer-sending family as a
    statement terminator. A bare trailing ``\\`` (end of input, or ``\\`` followed by
    a non-command char) matches nothing -> decline (return ``i`` unchanged) so the
    caller falls through and the lone ``\\`` is skipped as an unknown char."""
    m = _META_COMMAND.match(text, i)
    if not m:
        return None, line, i  # bare/backslash-only: decline, caller skips the char
    return SqlToken(m.group(0), line), line, m.end()


def _scan_span(
    text: str, i: int, ch: str, line: int
) -> tuple[SqlToken | None, int, int] | None:
    """Consume a comment/quote/dollar span opening at ``text[i]``, if any.

    Returns ``(token_or_None, new_line, next_i)`` when a span was consumed
    (``next_i > i``); the token is the placeholder to emit, or ``None`` for a span
    that emits nothing (a comment). Returns ``None`` (the outer sentinel) when no
    span opens here -- including the dollar non-opener case (e.g. ``$1``) where the
    producer declines to consume -- so the caller falls through to word-matching.
    Flattening the "producer exists" + "producer consumed" decision into this one
    helper keeps the main scan loop shallow.
    """
    producer = _tokenize_producer(text, i, ch)
    if producer is None:
        return None
    tok, new_line, next_i = producer(text, i, line)
    if next_i == i:
        return None  # producer declined (e.g. `$1`); fall through to word-matching
    return tok, new_line, next_i


def tokenize_sql(text: str) -> list[SqlToken]:
    """Tokenize SQL, dropping comments and string-literal contents.

    Each token keeps its 1-based source line so rules can emit path:line.
    String literals collapse to an empty-text placeholder token so no inner
    word leaks into rule matching while position is preserved.
    """
    tokens: list[SqlToken] = []
    i, line, n = 0, 1, len(text)
    while i < n:
        ch = text[i]

        skip = _skip_whitespace(ch, line, i)
        if skip is not None:
            line, i = skip
            continue

        # Comment/quote/dollar spans are dispatched here; the helper returns None
        # when no span opens (or a dollar non-opener declines) so we word-match.
        span = _scan_span(text, i, ch, line)
        if span is not None:
            tok, line, i = span
            _append_if_token(tokens, tok)  # comments emit no token; append the rest
            continue

        m = _WORD.match(text, i)
        if m:
            tokens.append(SqlToken(m.group(0), line))
            i = m.end()
            continue
        i += 1
    return tokens


def _append_if_token(tokens: list[SqlToken], tok: SqlToken | None) -> None:
    """Append ``tok`` unless it is ``None`` (a comment span emits no token)."""
    if tok is not None:
        tokens.append(tok)


def _skip_whitespace(ch: str, line: int, i: int) -> tuple[int, int] | None:
    """Advance past a single whitespace char at index ``i``.

    Returns the updated ``(line, next_i)`` when ``ch`` is whitespace -- a newline
    bumps ``line``; any other whitespace only advances ``i`` -- or ``None`` (the
    sentinel) when ``ch`` is not whitespace and the caller should keep classifying.
    """
    if ch == "\n":
        return line + 1, i + 1
    if ch.isspace():
        return line, i + 1
    return None


# Producer type: (text, i, line) -> (token_or_None, new_line, next_i).
_TokenProducer = Callable[[str, int, int], tuple["SqlToken | None", int, int]]


def _tokenize_producer(text: str, i: int, ch: str) -> _TokenProducer | None:
    """Select the span producer for the token opening at ``text[i]``, or ``None``
    when no span opens here and the caller should word-match directly."""
    if text.startswith("--", i):
        return _scan_line_comment
    if text.startswith("/*", i):
        return _scan_block_comment
    if ch in ("'", '"'):
        return _scan_quoted_token
    if ch == "$":
        return _scan_dollar_token
    if ch == "\\":
        return _scan_meta_command
    return None


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
        span = _strip_span(text, i)
        if span is None:
            out.append(text[i])  # ordinary char (or a `$1`-style non-opener `$`)
            i += 1
            continue
        emitted, i = span
        out.append(emitted)
    return "".join(out)


def _strip_span(text: str, i: int) -> tuple[str, int] | None:
    """Emit the replacement text for a span opening at ``text[i]``, comment-aware.

    Returns ``(emitted_text, next_i)`` for a recognized span, or ``None`` (the
    sentinel) when ``text[i]`` is an ordinary character the caller should copy
    through verbatim -- including a ``$`` that is NOT a dollar-quote opener (e.g.
    ``$1``). Kept in dispatch order so a comment marker inside a quoted span is
    data, never a comment. Mirrors ``_scan_span`` so ``strip_sql_comments`` stays a
    flat dispatcher instead of a bumpy chain of nested branches.
    """
    ch = text[i]
    # Inside a quoted span, copy through until the matching close quote; never
    # interpret a comment marker here.
    if ch in ("'", '"'):
        end = _quoted_span_end(text, i)
        return text[i:end], end
    if ch == "$":
        end = _dollar_quote_end(text, i)
        if end is None:
            return None  # not a dollar-quote opener (e.g. `$1`); copy the `$` through
        # Blank a PL/pgSQL body (a `--`/quoted-ident inside it is data, not code)
        # but keep columns + newlines so line numbers downstream hold.
        return _blank_span(text[i:end]), end
    if text.startswith("--", i):
        end = _line_comment_end(text, i)
        return " " * (end - i), end  # keep columns; a trailing newline is copied next
    if text.startswith("/*", i):
        end = _block_comment_end(text, i)
        # preserve newlines inside the block so line numbers downstream hold
        return _blank_span(text[i:end]), end
    return None


def iter_sql_files(ctx: RuleContext) -> list[str]:
    """Repo-relative POSIX paths of tracked warehouse SQL files."""
    return sorted(
        p
        for p in ctx.tracked_files
        if p.startswith("warehouse/") and p.endswith(".sql")
    )


def _is_schema_qualifying_position(prev: str, prev2: str, nxt: str) -> bool:
    """True when a schema token at this position is used as an actual schema.

    ``prev``/``prev2`` are the two preceding tokens (upper-cased); ``nxt`` is the
    following token. A token qualifies when it is a ``<schema>.<name>`` qualifier,
    the object of ``FROM``/``JOIN``, or the target of ``CREATE SCHEMA``. Written as
    guard clauses so no single branch expression combines logical operators.
    """
    if nxt == ".":  # `<schema>.<name>` qualifier
        return True
    if prev in ("FROM", "JOIN"):  # `FROM <schema>` / `JOIN <schema>`
        return True
    if prev != "SCHEMA":  # `CREATE SCHEMA <schema>` is the only remaining form
        return False
    return prev2 == "CREATE"


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
        if _is_schema_qualifying_position(prev, prev2, nxt):
            hits.append((low, tok.line))
    return hits


def _collect_statement_tokens(
    toks: list[SqlToken], stmt_start_idx: int
) -> list[SqlToken]:
    """Return the tokens from ``stmt_start_idx`` up to (not including) the next ";".

    Bounding at the statement terminator prevents leakage from a preceding
    ``SET search_path`` statement into the target-zone detection.
    """
    stmt: list[SqlToken] = []
    for i in range(stmt_start_idx, len(toks)):
        if toks[i].text == ";":
            break
        stmt.append(toks[i])
    return stmt


def _qualified_zone(stmt: list[SqlToken], pos: int) -> str:
    """Return the zone at ``stmt[pos]`` iff it is an explicit ``<zone>.<name>``.

    ``pos`` must point at the candidate schema qualifier. The token earns a zone
    only when it is a zone token AND immediately followed by ".". Anything else --
    an out-of-range ``pos``, a non-zone token, or a missing dot -- is "unknown"
    (fail-closed).
    """
    if pos >= len(stmt):
        return "unknown"
    candidate = stmt[pos].text.lower()
    if candidate in _ZONE_TOKENS:
        if pos + 1 < len(stmt) and stmt[pos + 1].text == ".":
            return candidate
    return "unknown"


def _index_ddl_zone(stmt: list[SqlToken], stmt_texts_upper: list[str]) -> str | None:
    """Zone for a CREATE/DROP INDEX statement, or ``None`` if it is not one.

    For an index DDL the target is the TABLE after the ON keyword, not the index
    name itself. Returns a zone or "unknown" (never ``None``) when it IS an index
    DDL; returns ``None`` only when the caller should fall through to the general
    case.
    """
    verb = stmt[0].text.upper()
    is_index_ddl = (
        verb in ("CREATE", "DROP")
        and "INDEX" in stmt_texts_upper
        and "ON" in stmt_texts_upper
    )
    if not is_index_ddl:
        return None
    on_pos = stmt_texts_upper.index("ON")
    return _qualified_zone(stmt, on_pos + 1)


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
    stmt = _collect_statement_tokens(toks, stmt_start_idx)
    if not stmt:
        return "unknown"

    stmt_texts_upper = [t.text.upper() for t in stmt]

    index_zone = _index_ddl_zone(stmt, stmt_texts_upper)
    if index_zone is not None:
        return index_zone

    # General case: skip the verb and any modifier keywords to find the target.
    pos = 1
    while pos < len(stmt) and stmt[pos].text.upper() in _DDL_MODIFIERS:
        pos += 1

    return _qualified_zone(stmt, pos)
