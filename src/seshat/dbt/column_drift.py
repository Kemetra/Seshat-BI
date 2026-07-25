"""Advisory column-shape comparison: shadow model vs its migrations counterpart.

WHY THIS IS NOT A PARITY ASSERTION (issue #492)
-----------------------------------------------
The reconciliation parity test asserts FOUR value classes -- ``fact_row_count``,
``business_key_count``, ``additive_money_total``, ``dimension_member_count``.
Those four are the WHOLE contract: ADR-0009 decision 5 enumerates them, and the
``assertion_class`` enum in ``schemas/dbt-run-evidence.schema.json`` is CLOSED to
exactly them (``evidence._parity_assertion`` fail-closes on a fifth). All four are
row-cardinality / SUM assertions, so a shadow model can gain, lose, or rename a
column and every assertion still passes with delta 0 -- the observed live case was
a date dimension whose shadow shape carried two extra columns while its member
count matched exactly (1096 = 1096).

This module closes that blind spot WITHOUT becoming a fifth assertion. A drift
finding here is ADVISORY: it is rendered to the operator, it never enters the run
evidence JSON, it never lands in ``blocking_reasons``, and it never changes an
exit code. That is deliberate, not a shortcut -- an intentional shadow-only column
is legitimate during a migration (the shadow star is allowed to lead), so drift
must be VISIBLE without being a failure. Making it blocking would either edit a
ratified contract or convert a legal migration state into a hard stop.

WHAT IS COMPARED
----------------
Shadow side: the governed ``ModelContract.columns`` that ``project.validate_project``
already parsed from the committed ``_models.yml`` -- the DECLARED contract for what
the model emits, not a re-parse of skeleton SQL. (The generated ``.sql`` files are
skeletons an operator completes by hand; the plan's pre-completion column list is
therefore NOT the shadow shape.)

Migrations side: the ``CREATE TABLE <schema>.<name> (...)`` column list in the
committed ``warehouse/migrations/*.sql`` -- the parity oracle's shape.

WHAT THIS DOES *NOT* COVER (stated, not implied)
-----------------------------------------------
The shadow side is a DECLARATION. Seshat's generated ``_models.yml`` carries the
governed column list under ``meta.seshat``, but it does NOT set dbt's
``contract: {enforced: true}``, so dbt never checks the built relation against it.
This comparison is therefore DECLARED-vs-MIGRATION, not BUILT-vs-BUILT:

- a model whose SELECT list drifts from its own ``_models.yml`` declaration is
  INVISIBLE here (both sides can agree while the materialized relation differs);
- a stale declaration can in principle produce an advisory for a pair whose built
  shapes actually agree.

That boundary is deliberate, not an oversight. The two alternatives were both
rejected: reading the scaffold PLAN reported a phantom
``{month_name, day_name, is_weekend}`` divergence on the committed worked example
(the generated SQL is a skeleton the operator completes, so the plan is the
pre-completion shape) and would have failed the no-finding census; and querying
``information_schema`` for the built shape needs a live DSN, which this offline,
driver-free static check does not have. The declaration is the best shape
available without a database -- so the advisory names what it compared, and this
note says what a clean result does not prove. Same discipline as the parity
disclaimer this module extends: state the gap rather than imply coverage.

FAIL-SAFE, NOT FAIL-CLOSED
--------------------------
Every uncertainty resolves to NO FINDING: no migrations directory, an unreadable
file, a model with no counterpart DDL (a shadow-only star that migrations never
built), or a ``CREATE TABLE`` this narrow parser cannot read confidently. An
advisory that cried wolf on an unparseable comment would be worse than silence,
and a missing counterpart is a normal state, not a defect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# One `CREATE TABLE [IF NOT EXISTS] <schema>.<table> ( ... );` body. Non-greedy to
# the first `);` that closes the definition, so consecutive CREATEs in one
# migration do not bleed into each other.
_CREATE_TABLE = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?"
    r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?(?P<table>[a-z_][a-z0-9_]*)\s*"
    r"\((?P<body>.*?)\n\s*\)\s*;",
    re.IGNORECASE | re.DOTALL,
)

# A table-level constraint / index clause, not a column. `PRIMARY KEY (a, b)` and
# friends open a definition body line the same way a column does, so the leading
# keyword is what distinguishes them.
_TABLE_CONSTRAINT = re.compile(
    r"^(?:constraint|primary\s+key|foreign\s+key|unique|check|exclude|like)\b",
    re.IGNORECASE,
)

_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")

# A column-CHANGING `ALTER TABLE`. The `CREATE TABLE` body alone is then a STALE
# view of the table's final shape, so the table is dropped from the comparison
# rather than compared against a shape we know to be out of date (#501 review).
# Deliberately narrow: `ALTER TABLE ... ADD CONSTRAINT` / `ALTER COLUMN ... TYPE`
# do not change the column SET and must not suppress a real finding.
_ALTER_COLUMN = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?"
    r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?(?P<table>[a-z_][a-z0-9_]*)\b"
    r"(?P<rest>[^;]*?)\b(?:add|drop|rename)\s+column\b",
    re.IGNORECASE | re.DOTALL,
)

# The same verbs with the optional `COLUMN` keyword omitted, which Postgres permits
# for ADD/DROP (`ALTER TABLE t ADD c INT`). A bare `ADD`/`DROP` followed by a
# constraint keyword is matched out so `ADD CONSTRAINT` / `ADD PRIMARY KEY` stay
# ignored -- the shipped 0004 migration uses `ADD CONSTRAINT` five times.
_ALTER_BARE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?"
    r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?(?P<table>[a-z_][a-z0-9_]*)\b"
    r"(?P<rest>[^;]*?)\b(?:add|drop)\s+"
    r"(?!column\b|constraint\b|primary\s+key\b|foreign\s+key\b|unique\b|check\b"
    r"|exclude\b)(?P<column>[a-z_][a-z0-9_]*)\b",
    re.IGNORECASE | re.DOTALL,
)

# Bare `RENAME <old> TO <new>` (no COLUMN keyword), which Postgres also permits.
# `RENAME TO <new>` renames the whole TABLE and does NOT change its column set, so
# the negative lookahead on `to` keeps a whole-table rename from tripping the guard
# (#501 review, finding A).
_ALTER_RENAME_BARE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?"
    r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?(?P<table>[a-z_][a-z0-9_]*)\s+"
    r"rename\s+(?!to\b|column\b|constraint\b)(?P<column>[a-z_][a-z0-9_]*)\s+to\b",
    re.IGNORECASE,
)

# `DROP TABLE [IF EXISTS] a.b [, c.d] [CASCADE]`. Processed in strict STATEMENT
# order alongside CREATE, because the committed migrations are idempotent: every
# `0004_*.sql` DROP is followed LATER IN THE SAME FILE by the CREATE that
# re-establishes the relation. Treating a dropped table as permanently absent would
# silently empty the comparison -- a false green (#501 review, finding B).
_DROP_TABLE = re.compile(
    r"drop\s+table\s+(?:if\s+exists\s+)?(?P<targets>[^;]+);",
    re.IGNORECASE | re.DOTALL,
)

# One `schema.table` (or bare `table`) inside a DROP's comma-separated target list.
# Either part may be double-quoted -- `DROP TABLE "gold"."dim_a"` is legal and
# equivalent to the unquoted spelling for all-lower-case names (#501 review).
_DROP_TARGET = re.compile(
    r'(?:"?(?P<schema>[a-z_][a-z0-9_]*)"?\s*\.\s*)?"?(?P<table>[a-z_][a-z0-9_]*)"?',
    re.IGNORECASE,
)

# Whole-TABLE `RENAME TO <new>`. The column set is unchanged, so this is NOT a
# column-changing ALTER -- but the relation is no longer reachable under its old
# name and does not yet exist under the new one as an indexed shape. Both names are
# omitted rather than tracked through the rename (#501 review, finding A).
_ALTER_RENAME_TABLE = re.compile(
    r"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?"
    r"(?:(?P<schema>[a-z_][a-z0-9_]*)\.)?(?P<table>[a-z_][a-z0-9_]*)\s+"
    r"rename\s+to\s+(?P<new_table>[a-z_][a-z0-9_]*)",
    re.IGNORECASE,
)

# A double-quoted identifier in a CREATE body. PostgreSQL folds unquoted names to
# lower case but preserves quoted ones EXACTLY, so `"CustomerID"` and `customerid`
# are different columns. This parser compares case-insensitively, so a table using
# quoted mixed-case identifiers is treated as unparseable rather than silently
# folded into a false match (#501 review, finding C).
_QUOTED_MIXED_CASE = re.compile(r'"[^"]*[A-Z][^"]*"')

# `--` to end of line, or a `/* ... */` block, or a single-quoted string literal.
# The string-literal alternative comes FIRST and is preserved verbatim, so a `--`
# or `/*` INSIDE a quoted value is not mistaken for a comment (#501 review,
# finding B). `''` is Postgres' escaped single quote inside a literal.
# `dollar` covers Postgres dollar-quoting (`$$...$$` / `$tag$...$tag$`), whose body
# is literal text -- DDL written inside one is DATA, not a statement (#501 review).
# The backreference pins the closing tag to the opening one.
_COMMENT_OR_LITERAL = re.compile(
    # Tagged `$tag$...$tag$`: the backreference pins the close to the open. The
    # untagged `$$...$$` form needs its own branch, because an optional tag group
    # would make `(?P=tag)` unmatchable when the tag is absent.
    r"(?P<dollar>\$(?P<tag>[a-z_][a-z0-9_]*)\$.*?\$(?P=tag)\$|\$\$.*?\$\$)"
    r"|(?P<literal>'(?:[^']|'')*')"
    r"|(?P<line>--[^\n]*)"
    r"|(?P<block>/\*.*?\*/)",
    re.DOTALL | re.IGNORECASE,
)

_MIGRATIONS_DIR = "warehouse/migrations"

# dbt materializes GOLD and stops (ADR-0009 decision 6), and the governed source
# map declares every mart `gold.`-qualified, so the gold relation is the only
# legitimate migrations counterpart for a mart. Keying the index by (schema, table)
# and selecting this layer stops a same-named `silver.` table from replacing the
# gold oracle on a last-write-wins basis (#501 review, finding C).
_ORACLE_SCHEMA = "gold"


@dataclass(frozen=True, slots=True)
class ColumnShapeAdvisory:
    """One shadow/migrations column-shape divergence for one model pair.

    Deliberately NOT shaped like a parity assertion and NOT shaped like a
    ``Blocker``: no ``assertion_class``, no ``assertion_id``, no ``passed``, and no
    ``DBT_[A-Z0-9_]+`` code. Those vocabularies belong to the closed parity enum
    and the blocking channel respectively; borrowing either would invite a reader
    to mistake this for a fifth assertion or a failure.
    """

    model: str
    migration_relpath: str
    shadow_only: tuple[str, ...]
    migrations_only: tuple[str, ...]

    def message(self) -> str:
        parts = []
        if self.shadow_only:
            parts.append(f"shadow-only {list(self.shadow_only)}")
        if self.migrations_only:
            parts.append(f"migrations-only {list(self.migrations_only)}")
        # State the boundary in the finding itself, not only in the docs: the
        # shadow side is the DECLARED column list, which dbt does not enforce.
        # A reader who acts on this line must know which shape it describes.
        return (
            f"{self.model}: DECLARED column set (_models.yml) differs from "
            f"{self.migration_relpath} ({'; '.join(parts)}). The four parity "
            "assertions are value-only and cannot see this; confirm the divergence "
            "is intended. Scope: compares the GOVERNED DECLARATION, which dbt does "
            "not enforce as a contract -- it cannot see a built model whose "
            "projection drifts from its own declaration."
        )


def _blanked(text: str) -> str:
    """``text`` as equivalent whitespace, preserving newlines so line-oriented
    structure and the ``[^;]*?`` spans in the ALTER patterns still behave."""
    return "".join("\n" if char == "\n" else " " for char in text)


def _matched_literal(match: re.Match[str]) -> str | None:
    """The single-quoted or dollar-quoted literal this match found, else None."""
    return match.group("literal") or match.group("dollar")


def _blank_comment(match: re.Match[str]) -> str:
    """Blank a comment; keep a string literal verbatim."""
    literal = _matched_literal(match)
    return literal if literal is not None else _blanked(match.group(0))


def _blank_comment_and_literal(match: re.Match[str]) -> str:
    """Blank comments AND string-literal CONTENTS, keeping the delimiters.

    A literal is DATA, so DDL text quoted inside one is not a statement: neither
    ``INSERT ... VALUES ('ALTER TABLE gold.x ADD COLUMN y')`` nor its dollar-quoted
    equivalent ``$tag$ALTER TABLE ...$tag$`` may register as a real ALTER. Blanking
    the contents rather than the delimiters keeps the literal one syntactic token so
    it cannot merge with surrounding SQL."""
    quoted = match.group("literal")
    if quoted is not None:
        return f"'{_blanked(quoted[1:-1])}'"
    dollar = match.group("dollar")
    if dollar is None:
        return _blanked(match.group(0))
    fence = f"${match.group('tag') or ''}$"
    return f"{fence}{_blanked(dollar[len(fence) : -len(fence)])}{fence}"


def _strip_comments(sql: str) -> str:
    """``sql`` with `--` line comments and `/* ... */` blocks removed.

    Comment-like sequences INSIDE single-quoted literals survive: `'--not a
    comment'` is data, not syntax (#501 review). Used where literal CONTENT still
    matters -- e.g. a ``CREATE TABLE`` body, whose defaults may be quoted."""
    return _COMMENT_OR_LITERAL.sub(_blank_comment, sql)


def _scannable(sql: str) -> str:
    """``sql`` reduced to what a STATEMENT scan may match: comments removed and
    string-literal contents blanked.

    Applied before the CREATE/ALTER scans so neither a commented-out statement nor
    one quoted as data can register -- the first would silently disable a table's
    shape check, the second would invent one."""
    return _COMMENT_OR_LITERAL.sub(_blank_comment_and_literal, sql)


def _split_definition_body(body: str) -> list[str]:
    """Top-level comma-separated definition lines, ignoring commas nested in
    parentheses (``NUMERIC(12,2)``, ``PRIMARY KEY (a, b)``) and `--` comments."""
    definitions: list[str] = []
    current: list[str] = []
    depth = 0
    for char in _strip_comments(body):
        depth += (char == "(") - (char == ")")
        if char == "," and depth == 0:
            definitions.append("".join(current))
            current = []
        else:
            current.append(char)
    definitions.append("".join(current))
    return definitions


def _column_names(body: str) -> frozenset[str] | None:
    """Column names in one ``CREATE TABLE`` body, or None if unreadable.

    None (-> no finding) whenever the body yields no column at all, a definition
    line starts with something this parser cannot classify as a column name, or the
    body uses a QUOTED MIXED-CASE identifier: a half-understood column set would
    produce a bogus symmetric difference.

    The quoted mixed-case rule closes a real folding hazard (#501 review). Postgres
    lower-cases unquoted identifiers but preserves quoted ones verbatim, so
    ``"CustomerID"`` and ``customerid`` are DISTINCT columns. This comparison is
    case-insensitive, which would fold them together and hide genuine drift -- so
    the table is skipped instead of compared on a wrong premise."""
    if _QUOTED_MIXED_CASE.search(body):
        return None
    names: list[str] = []
    for definition in _split_definition_body(body):
        text = definition.strip().strip(",").strip()
        if not text or _TABLE_CONSTRAINT.match(text):
            continue
        candidate = text.split()[0].strip('"').lower()
        if not _IDENTIFIER.match(candidate):
            return None
        names.append(candidate)
    if not names or len(set(names)) != len(names):
        return None
    return frozenset(names)


def migration_column_sets(repo_root: Path) -> dict[str, tuple[frozenset[str], str]]:
    """``{table_name: (column_names, migration_relpath)}`` for the committed
    migrations -- the ``gold`` relations only, keyed on the bare table name (the
    shadow star materializes the same model name into its own shadow schema, so the
    schema qualifier cannot match on the shadow side).

    Internally the index is keyed by ``(schema, table)`` and only the
    ``_ORACLE_SCHEMA`` layer is returned, so a same-named table in another schema
    (``silver.dim_customer`` beside ``gold.dim_customer``) cannot replace the gold
    oracle by last-write-wins. An unqualified ``CREATE TABLE`` has no determinable
    layer and is therefore DROPPED rather than guessed at (#501 review).

    CREATE and DROP are replayed in strict STATEMENT order (file order, then
    position within the file), so the idempotent ``DROP ... ; CREATE ...`` preamble
    the committed migrations use resolves to CREATED. This ordering is load-bearing:
    every ``DROP`` in ``0004_*.sql`` precedes ALL of its ``CREATE``s, so treating a
    dropped relation as permanently absent would remove the fact and every dimension
    from the comparison and leave a census of zero advisories that means nothing
    (#501 review, finding B). A relation counts as absent only if it ENDS the
    sequence dropped.

    A table created more than once IN THE SAME SCHEMA resolves to the LAST
    definition. Unreadable files are skipped, never raised.

    OMITTED entirely, on the honest-silence rule -- a shape this parser cannot know
    is better reported as nothing than guessed at:

    - a table whose history contains a column-changing ``ALTER TABLE`` (the CREATE
      body no longer describes its final shape; DDL is not replayed);
    - both the old and new names of a whole-table ``ALTER TABLE ... RENAME TO``
      (the old relation is gone, the new one has no indexed shape);
    - a table using quoted mixed-case identifiers (case folding would hide drift);
    - an unqualified ``CREATE TABLE`` (its layer resolves via ``search_path``).

    Returns ``{}`` -- no comparison at all -- when ANY migration is unreadable, since
    that file may be the one superseding what an earlier file created."""
    directory = Path(repo_root) / _MIGRATIONS_DIR
    if not directory.is_dir():
        return {}
    found: dict[tuple[str, str], tuple[frozenset[str], str]] = {}
    excluded: set[tuple[str, str]] = set()
    for path in sorted(directory.glob("*.sql")):
        text = _read_text(path)
        if text is None:
            # An unreadable file may hold the DROP/ALTER that supersedes what an
            # earlier file created; comparing against a possibly-stale view would be
            # worse than not comparing at all.
            return {}
        relpath = f"{_MIGRATIONS_DIR}/{path.name}"
        sql = _scannable(text)
        excluded.update(_altered_tables(sql))
        excluded.update(_renamed_tables(sql))
        _replay_statements(sql, relpath, found)
    return {
        table: shape
        for (schema, table), shape in found.items()
        if schema == _ORACLE_SCHEMA and (schema, table) not in excluded
    }


def _qualified(match: re.Match[str]) -> tuple[str, str] | None:
    """``(schema, table)`` for one statement, or None when unqualified.

    An unqualified name resolves through ``search_path`` at run time, which this
    static read cannot know -- so its layer is indeterminate and the caller drops
    it rather than assuming the oracle schema."""
    schema = match.group("schema")
    if schema is None:
        return None
    return (schema.lower(), match.group("table").lower())


def _replay_statements(
    sql: str, relpath: str, found: dict[tuple[str, str], tuple[frozenset[str], str]]
) -> None:
    """Apply one migration's CREATE/DROP statements to ``found`` in the order they
    appear, so a DROP followed by a CREATE of the same relation ends up CREATED."""
    events = sorted(
        [(m.start(), _CREATE_TABLE, m) for m in _CREATE_TABLE.finditer(sql)]
        + [(m.start(), _DROP_TABLE, m) for m in _DROP_TABLE.finditer(sql)],
        key=lambda event: event[0],
    )
    for _, pattern, match in events:
        if pattern is _DROP_TABLE:
            for key in _drop_targets(match.group("targets")):
                found.pop(key, None)
            continue
        key = _qualified(match)
        columns = _column_names(match.group("body"))
        if key is not None and columns is not None:
            found[key] = (columns, relpath)


def _drop_targets(targets: str) -> set[tuple[str, str]]:
    """The schema-qualified relations one ``DROP TABLE`` names.

    ``CASCADE`` / ``RESTRICT`` trail the list and are not relations; an unqualified
    target has no determinable layer, so it cannot match an indexed key anyway."""
    keys: set[tuple[str, str]] = set()
    for chunk in targets.split(","):
        text = re.sub(r"\b(cascade|restrict)\b", " ", chunk, flags=re.IGNORECASE)
        match = _DROP_TARGET.search(text)
        key = _qualified(match) if match is not None else None
        if key is not None:
            keys.add(key)
    return keys


def _renamed_tables(sql: str) -> set[tuple[str, str]]:
    """Both endpoints of every whole-table ``RENAME TO``.

    The column set does not change, so this is deliberately NOT a column-changing
    ALTER -- but the index is keyed by name, and after the rename the old name names
    nothing while the new name has no indexed shape. Omitting BOTH is the honest
    answer for either model that might look them up (#501 review, finding A)."""
    keys: set[tuple[str, str]] = set()
    for match in _ALTER_RENAME_TABLE.finditer(sql):
        key = _qualified(match)
        if key is None:
            continue
        schema, table = key
        keys.add((schema, table))
        keys.add((schema, match.group("new_table").lower()))
    return keys


def _altered_tables(sql: str) -> set[tuple[str, str]]:
    """``(schema, table)`` pairs one comment-stripped migration reshapes with a
    column-changing ``ALTER TABLE``. Constraint-only, type-only, and whole-table
    ``RENAME TO`` statements are ignored: they do not change the column SET, so they
    must not suppress a genuine finding."""
    patterns = (_ALTER_COLUMN, _ALTER_BARE, _ALTER_RENAME_BARE)
    keys = (_qualified(m) for p in patterns for m in p.finditer(sql))
    return {key for key in keys if key is not None}


def _read_text(path: Path) -> str | None:
    """The file's text, or None when unreadable.

    None INVALIDATES THE WHOLE INDEX rather than skipping just this file (#501
    review). An unreadable migration is not a neutral gap: it may be the one that
    drops or reshapes a relation an earlier file created, so silently omitting it
    would leave a stale shape indexed and let the advisory speak from an
    already-superseded view. Advisory input is never fatal, but it must not be
    confidently wrong -- so the comparison goes quiet instead."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def column_shape_advisories(
    repo_root: Path, model_contracts, *, skip: frozenset[str] = frozenset()
) -> tuple[ColumnShapeAdvisory, ...]:
    """Advisory column-shape divergences between the governed shadow models and
    their migrations counterparts.

    ``skip`` names models that have no migrations counterpart BY DESIGN -- the
    parity audit model is derived evidence the migrations path never builds, so
    comparing it would report a permanent phantom divergence.

    Returns () when nothing diverges, when migrations are absent, or when a model
    has no counterpart DDL. Never raises on malformed input: this is advisory."""
    migrations = migration_column_sets(repo_root)
    candidates = (c for c in model_contracts if c.name not in skip)
    advisories = (_compare(contract, migrations) for contract in candidates)
    return tuple(advisory for advisory in advisories if advisory is not None)


def _compare(contract, migrations) -> ColumnShapeAdvisory | None:
    """The advisory for one model, or None when it agrees / has no counterpart."""
    counterpart = migrations.get(contract.name.lower())
    if counterpart is None:
        return None
    expected, relpath = counterpart
    shadow = frozenset(column.name.lower() for column in contract.columns)
    if shadow == expected:
        return None
    return ColumnShapeAdvisory(
        model=contract.name,
        migration_relpath=relpath,
        shadow_only=tuple(sorted(shadow - expected)),
        migrations_only=tuple(sorted(expected - shadow)),
    )
