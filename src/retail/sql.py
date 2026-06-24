from __future__ import annotations

import re
from dataclasses import dataclass

from .core import RuleContext

_SCHEMA_TOKENS = ("raw", "marts", "bronze", "silver")


@dataclass(frozen=True)
class SqlToken:
    text: str
    line: int


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
        m = word.match(text, i)
        if m:
            tokens.append(SqlToken(m.group(0), line))
            i = m.end()
            continue
        i += 1
    return tokens


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
