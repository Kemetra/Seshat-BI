"""#417: a pure, defense-in-depth check that a migration WRITES to Bronze.

In existing-bronze source mode the ADAPTER is read-only, but the medallion run
then applies committed silver/gold migrations. A correctly-layered migration
targets silver/gold and only READS Bronze (``FROM``/``JOIN bronze.<t>`` -- the
medallion flow). A migration that WRITES Bronze is a layering violation; this
predicate lets the gate fail closed before executing it, extending the adapter's
read-only guarantee to whole-run Bronze immutability.

Scope (deliberately bounded -- defense-in-depth, NOT a SQL parser): the check is
verb-anchored and matches only Bronze as the TARGET of DDL/DML. It never fires on
a bare ``FROM``/``JOIN bronze`` read. A write verb buried inside a string literal
is a documented false-negative: the goal is to catch the plausible layering
mistake, not to defeat an adversary crafting SQL to evade the guard.

KNOWN fail-OPEN gap (comment stripping is not string-literal-aware): a ``--``
INSIDE a SQL string literal is treated as a comment start, so a real write after a
literal that contains ``--`` on the same line can be hidden -- e.g.
``SELECT '--'; DELETE FROM bronze.orders;`` strips from the quoted ``--`` and
returns False. Distinguishing literals from comments needs a real tokenizer
(escaped quotes, dollar-quoting ``$$...$$``), out of scope for a heuristic guard.
Migrations are committed, reviewed artifacts; this masks a write only via SQL no
plausible layering mistake produces, so it is accepted as a bounded gap.
"""

from __future__ import annotations

import re

# Comments first, so a comment that MENTIONS bronze -- even one documenting a
# `DELETE FROM bronze.orders` -- can never trip the write patterns below.
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")

# Every pattern anchors to a WRITE verb and matches bronze as the write TARGET.
# `bronze` is the schema, matched with a word boundary + a `.` (a relation) or,
# for CREATE SCHEMA, the schema itself -- so a table merely NAMED `bronze_x` in
# another schema (`silver.bronze_snapshot`) is NOT the bronze schema. An optional
# double-quote allows `"bronze"."t"`. `\s+` between keywords tolerates newlines.
_BRONZE = r'"?bronze"?'
_REL = rf"{_BRONZE}\s*\.\s*"  # bronze.<relation> as a write target
# The BOUNDED object-type run a CREATE/DROP/ALTER may put before its target: only
# real relation object-type keywords + TEMP/UNLOGGED/GLOBAL/LOCAL/MATERIALIZED
# modifiers + IF [NOT] EXISTS. NOT an unbounded `\w+` crawl -- that would march
# through a whole `... AS SELECT ... FROM bronze.x` READ body and wrongly flag it
# (a false positive on the normal medallion flow). Anchored to these tokens, the
# pattern only fires when bronze.<rel> is the DDL TARGET.
_OBJ = (
    r"(?:OR\s+REPLACE|TEMP|TEMPORARY|UNLOGGED|GLOBAL|LOCAL|MATERIALIZED|"
    r"TABLE|VIEW|SEQUENCE|MATVIEW|ONLY)\s+"
)
_MODS = rf"(?:{_OBJ})*(?:IF\s+(?:NOT\s+)?EXISTS\s+)?"
# DML verbs tolerate an ONLY/TABLE modifier between verb and target (Postgres
# `TRUNCATE ONLY`, `UPDATE ONLY`, `DELETE FROM ONLY`) -- a BOUNDED allowance, so a
# modifier can never let the match crawl into a read body.
_ONLY = r"(?:ONLY\s+)?"
_WRITE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE | re.DOTALL)
    for pattern in (
        # CREATE / DROP / ALTER <bounded object modifiers> bronze.<rel>
        rf"\b(?:CREATE|DROP|ALTER)\s+{_MODS}{_REL}",
        # CREATE [UNIQUE] INDEX [CONCURRENTLY] [name] ON bronze.<rel> -- the index's
        # TARGET follows ON. This `ON` is safe to anchor on because it is preceded
        # by CREATE ... INDEX; a JOIN's `ON bronze.c...` is never preceded by
        # CREATE INDEX, so this cannot re-introduce the read-side false positive.
        rf"\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:CONCURRENTLY\s+)?"
        rf"(?:(?:IF\s+NOT\s+EXISTS\s+)?\w+\s+)?ON\s+{_REL}",
        # CREATE / DROP / ALTER SCHEMA bronze  -- the schema ITSELF is the target
        # (DROP SCHEMA bronze CASCADE is the most destructive bronze write of all).
        rf"\b(?:CREATE|DROP|ALTER)\s+SCHEMA\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?{_BRONZE}\b",
        rf"\bTRUNCATE\s+(?:TABLE\s+)?{_ONLY}{_REL}",
        rf"\bINSERT\s+INTO\s+{_REL}",
        rf"\bUPDATE\s+{_ONLY}{_REL}",
        rf"\bDELETE\s+FROM\s+{_ONLY}{_REL}",  # a write whose target follows FROM
        rf"\bMERGE\s+INTO\s+{_REL}",
        rf"\bCOPY\s+{_REL}",
        rf"\bINTO\s+{_REL}",  # SELECT ... INTO bronze.<rel>
    )
)


def _strip_comments(sql: str) -> str:
    return _LINE_COMMENT.sub(" ", _BLOCK_COMMENT.sub(" ", sql))


def _targets_bronze_write(sql: str) -> bool:
    """True iff ``sql`` contains a statement that WRITES to the ``bronze`` schema.

    Bronze appearing only in a ``FROM``/``JOIN`` read, in a comment, or as a
    substring of another schema's relation name returns False.
    """
    stripped = _strip_comments(sql)
    return any(pattern.search(stripped) for pattern in _WRITE_PATTERNS)
