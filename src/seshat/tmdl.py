"""Hand-rolled TMDL (Tabular Model Definition Language) parser.

PARSER DECISION (search-first; full rationale in
docs/decisions/0001-tmdl-pbir-parser.md):
  - TMDL is parsed by THIS hand-rolled indentation/block tokenizer. No PyPI TMDL
    parser is mature enough to depend on (surveyed 2026-06); TOM and sempy read TMDL
    only via the Windows/.NET or Fabric live path, which defeats headless CI, so both
    are disqualified for the static checker.
  - PBIR / report JSON is parsed with the stdlib ``json`` module opened
    ``encoding="utf-8-sig"`` because Power BI writes UTF-8-with-BOM and ``json.load``
    chokes on a leading BOM.

REGRESSION ANCHOR (token literals observed in tests/fixtures/golden_pbip/; M4/M5 pin
their regexes to these. If a fixture edit drops one, tests/unit/test_tmdl.py fails):
  - measure block shape:        ``measure 'TotalSales' = SUM(Sales[Amount])``
                                (single-quoted name; ``measure <name> = <expr>``)
  - display folder:             ``displayFolder: Sales``
  - relationship cross-filter:  ``crossFilteringBehavior: bothDirections``
  - implicit aggregation:       ``summarizeBy: sum``
  - gold-only M source schema:  ``Schema="gold"``
  - parameterized M source:     ``PostgreSQL.Database(Server, Database)``  (identifiers)
  - date-table marker:          ``annotation PBI_DateTable = true``  (table-level)
    NOTE: D7 also accepts the REAL "Mark as Date Table" marker -- table-level
    ``dataCategory: Time`` PLUS a column flagged ``isKey`` (TOM
    ``Table.DataCategory = "Time"`` + a key column; verified 2026-06 against the
    TOM reference, Microsoft Learn, and Tabular Editor). The annotation literal
    below is kept as an ALSO-accepted form (some models carry it) and as the M0
    fixture's marker, but it is no longer the sole signal -- so D7 no longer hinges
    on confirming that one literal against a captured PBIP. Capturing a real
    "Mark as Date Table" PBIP (CAPTURE.md) is still nice-to-have to retire the
    fixture's annotation form, but is no longer blocking.

PUBLIC API (consumed by D1-D8 rules and by M4b):
  - TmdlMeasure(name, expression, display_folder, line)
  - TmdlColumn(name, data_type, summarize_by, line, is_key)
  - TmdlRelationship(name, cross_filtering_behavior, line)
  - TmdlTable(name, measures, columns, partition_sources, annotations, line,
    data_category)
  - MSource(text, locator)
  - parse_tmdl(text: str) -> TmdlTable | None
  - parse_relationships(text: str) -> tuple[TmdlRelationship, ...]
  - iter_model_files(ctx: RuleContext, suffix: str) -> Iterable[tuple[str, str]]
  - iter_m_sources(repo_root: Path, tracked_files: tuple[str, ...]) -> Iterable[MSource]
  - normalize_measure_body(expression: str) -> str
  - top_level_blocks(text: str) -> list[str]   (M0 regression anchor; test-only)
  - DATE_TABLE_MARKER: str
  - TI_TRIGGER_FUNCTIONS: frozenset[str]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .core import RuleContext, is_test_path

DATE_TABLE_MARKER = "annotation PBI_DateTable = true"
# One of TWO accepted date-table markers (see D7 in rules/dax.py). The
# AUTHORITATIVE marker Power BI's "Mark as Date Table" writes is table-level
# ``dataCategory: Time`` + a column flagged ``isKey`` (TmdlTable.data_category +
# TmdlColumn.is_key); this annotation form is also accepted because some models
# carry it and the M0 golden fixture uses it. Table-level ``dataCategory: Time``
# alone (no key column) is NOT sufficient -- the key column is required.

TI_TRIGGER_FUNCTIONS = frozenset(
    {
        "TOTALYTD",
        "TOTALQTD",
        "TOTALMTD",
        "DATESYTD",
        "DATESQTD",
        "DATESMTD",
        "SAMEPERIODLASTYEAR",
        "DATEADD",
        "DATESINPERIOD",
        "DATESBETWEEN",
        "PARALLELPERIOD",
        "PREVIOUSYEAR",
        "PREVIOUSQUARTER",
        "PREVIOUSMONTH",
        "PREVIOUSDAY",
        "NEXTYEAR",
        "NEXTQUARTER",
        "NEXTMONTH",
        "NEXTDAY",
        "OPENINGBALANCEMONTH",
        "OPENINGBALANCEQUARTER",
        "OPENINGBALANCEYEAR",
        "CLOSINGBALANCEMONTH",
        "CLOSINGBALANCEQUARTER",
        "CLOSINGBALANCEYEAR",
        "STARTOFYEAR",
        "STARTOFQUARTER",
        "STARTOFMONTH",
        "ENDOFYEAR",
        "ENDOFQUARTER",
        "ENDOFMONTH",
        "FIRSTDATE",
        "LASTDATE",
    }
)


@dataclass(frozen=True)
class TmdlMeasure:
    """A parsed DAX measure block inside a table.

    Attributes:
        name: measure name (stripped of quotes).
        expression: RAW body text (comments + strings intact) for D4 lexing.
        display_folder: value of ``displayFolder:`` property, or None.
        line: 1-based line number of the ``measure`` header line.
    """

    name: str
    expression: str
    display_folder: str | None
    line: int


@dataclass(frozen=True)
class TmdlColumn:
    """A parsed column block inside a table.

    Attributes:
        name: column name (stripped of quotes).
        data_type: value of ``dataType:`` property, or None.
        summarize_by: value of ``summarizeBy:`` property, or None.
        line: 1-based line number of the ``column`` header line.
    """

    name: str
    data_type: str | None
    summarize_by: str | None
    line: int
    # True if the column carries the bare ``isKey`` flag. Part of the real
    # "Mark as Date Table" marker (table ``dataCategory: Time`` + a key column).
    is_key: bool = False


@dataclass(frozen=True)
class TmdlRelationship:
    """A parsed relationship block.

    Attributes:
        name: relationship name.
        cross_filtering_behavior: value of ``crossFilteringBehavior:`` or None.
        line: 1-based line number of the ``relationship`` header line.
    """

    name: str
    cross_filtering_behavior: str | None
    line: int


@dataclass(frozen=True)
class TmdlTable:
    """A fully parsed TMDL table block.

    Attributes:
        name: table name.
        measures: all ``measure`` blocks found.
        columns: all ``column`` blocks found.
        partition_sources: RAW M source body texts, one joined string per source.
            NOTE: D8 does NOT consume this field -- it re-scans raw table-file
            bodies independently (see ``iter_m_sources``); this attribute is
            retained for parser completeness, not for any rule.
        annotations: raw ``annotation <name> = <value>`` lines (for D7 marker).
        line: 1-based line number of the ``table`` header.
    """

    name: str
    measures: tuple[TmdlMeasure, ...]
    columns: tuple[TmdlColumn, ...]
    partition_sources: tuple[str, ...]
    annotations: tuple[str, ...]
    line: int
    # Value of the table-level ``dataCategory:`` property, or None. ``"Time"`` is
    # half of the real "Mark as Date Table" marker (the other half is a key column).
    data_category: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _indent(line: str) -> int:
    """Return the number of leading TAB characters (TMDL uses tab indentation)."""
    n = 0
    for ch in line:
        if ch == "\t":
            n += 1
        else:
            break
    return n


def _strip_bom(text: str) -> str:
    """Strip a UTF-8 BOM if present (fallback for non-utf-8-sig opens)."""
    return text.lstrip("﻿")


# ---------------------------------------------------------------------------
# Public parsing functions
# ---------------------------------------------------------------------------


def _continues_block(lines: list[str], j: int, n: int, parent_ind: int) -> bool:
    """True while line ``j`` is still inside a block opened at ``parent_ind``.

    A block continues across blank lines and any line indented deeper than
    ``parent_ind``. Shared by the indentation-driven block scanners in this
    module (measure/column/source bodies) so the "is this line still part of
    the block?" test has exactly one definition.
    """
    return j < n and (not lines[j].strip() or _indent(lines[j]) > parent_ind)


def _block_body_lines(
    lines: list[str], i: int, n: int, ind: int
) -> tuple[list[str], int]:
    """Collect the RAW child lines of the block whose header is at line ``i``.

    Walks forward from ``i + 1`` while :func:`_continues_block` holds for the
    parent indent ``ind`` and returns ``(raw_child_lines, next_index)`` — the
    unmodified lines strictly inside the block and the index of the first line
    past it. Callers decide how to seed, strip, filter blanks, and join; this
    only owns the shared indentation walk so every block parser scans blocks
    identically.
    """
    j = i + 1
    while _continues_block(lines, j, n, ind):
        j += 1
    return lines[i + 1 : j], j


def _find_table_header(lines: list[str]) -> tuple[str | None, int]:
    """Locate the top-level ``table <name>`` header line.

    Returns ``(name, 1-based line number)``, or ``(None, 0)`` if no such
    header exists (e.g. ``relationships.tmdl``, header-only ``model.tmdl``).
    """
    for i, raw in enumerate(lines, start=1):
        # Only a column-0 line can be the top-level table header; skip the rest
        # before the regex (an empty ``raw`` never matches the header pattern).
        if _indent(raw) != 0:
            continue
        m = re.match(r"table\s+('?)(?P<name>[^'\n]+?)\1\s*$", raw.strip())
        if m:
            return m.group("name"), i
    return None, 0


def _parse_measure_block(
    lines: list[str], i: int, n: int, match: re.Match[str]
) -> tuple[TmdlMeasure, int]:
    """Parse a ``measure`` block starting at line ``i`` (0-based).

    ``match`` is the already-matched header regex. Returns the parsed
    :class:`TmdlMeasure` and the index of the first line past the block.

    KNOWN GAP (audit 2026-06-26 #32, none-today): the name class `[^'=]+?`
    excludes `=`, so a single-quoted measure name CONTAINING `=` would be
    truncated at the `=`. No committed measure has `=` in its name; widening
    the regex risks re-testing all TMDL parsing for a zero-trigger case, so
    this is documented, not changed.
    """
    ind = _indent(lines[i])
    name = match.group("name").strip()
    expr_parts = [match.group("expr").rstrip()]
    df: str | None = None
    j = i + 1
    while _continues_block(lines, j, n, ind):
        child = lines[j].strip()
        dfm = re.match(r"displayFolder:\s*(?P<v>.+)$", child)
        if dfm:
            df = dfm.group("v").strip()
        elif child and not re.match(r"\w+:\s", child):
            # continuation of a multi-line expression
            expr_parts.append(child)
        j += 1
    measure = TmdlMeasure(
        name=name,
        expression=" ".join(expr_parts).strip(),
        display_folder=df,
        line=i + 1,
    )
    return measure, j


def _parse_column_block(
    lines: list[str], i: int, n: int, match: re.Match[str]
) -> tuple[TmdlColumn, int]:
    """Parse a ``column`` block starting at line ``i`` (0-based).

    ``match`` is the already-matched header regex. Returns the parsed
    :class:`TmdlColumn` and the index of the first line past the block.

    KNOWN GAP (audit 2026-06-26 #31, none-today): an UNQUOTED calculated
    column `column Name = expr` would let the name class absorb ` = expr`.
    No committed model has a calc column in this form; documented, not changed
    (a regex tweak here would re-test all column parsing for a zero trigger).
    """
    ind = _indent(lines[i])
    name = match.group("name").strip()
    dt: str | None = None
    sb: str | None = None
    is_key = False
    j = i + 1
    while _continues_block(lines, j, n, ind):
        child = lines[j].strip()
        d = re.match(r"dataType:\s*(?P<v>.+)$", child)
        s = re.match(r"summarizeBy:\s*(?P<v>.+)$", child)
        if d:
            dt = d.group("v").strip()
        if s:
            sb = s.group("v").strip()
        # ``isKey`` is a bare flag line (no value) in TMDL.
        if child == "isKey":
            is_key = True
        j += 1
    column = TmdlColumn(
        name=name, data_type=dt, summarize_by=sb, line=i + 1, is_key=is_key
    )
    return column, j


def _parse_source_block(
    lines: list[str], i: int, n: int, stripped: str
) -> tuple[str, int]:
    """Parse a ``source =`` / ``partition <name> =`` block starting at line ``i``.

    Returns the joined (space-separated, blank-lines-skipped) raw M body text
    and the index of the first line past the block.
    """
    ind = _indent(lines[i])
    children, j = _block_body_lines(lines, i, n, ind)
    body = [stripped.split("=", 1)[1].strip()]
    body.extend(child.strip() for child in children if child.strip())
    source_text = " ".join(p for p in body if p).strip()
    return source_text, j


def _is_measure_header(stripped: str) -> re.Match[str] | None:
    """Match a ``measure <name> = <expr>`` header line, or None."""
    return re.match(r"measure\s+('?)(?P<name>[^'=]+?)\1\s*=\s*(?P<expr>.*)$", stripped)


def _is_column_header(stripped: str) -> re.Match[str] | None:
    """Match a ``column <name>`` header line, or None."""
    return re.match(r"column\s+('?)(?P<name>[^'\n]+?)\1\s*$", stripped)


def _is_source_header(stripped: str) -> bool:
    """True for a real ``source =`` / ``partition <name> =`` assignment header.

    The anchored form avoids matching column-property lines such as
    ``source_type = ...`` that merely start with the word "source".
    """
    return bool(re.match(r"(source\s*=|partition\s+\S+\s*=)", stripped))


def _parse_data_category(stripped: str, ind: int) -> str | None:
    """Return the table-level ``dataCategory:`` value on this line, or None.

    Only the TABLE-level property counts (``ind == 1``, outside any column
    block); a column-level ``dataCategory: Time`` is intentionally NOT the
    date-table marker. Returns None for any non-matching or wrongly-indented
    line, so callers keep a previously captured value (last match wins).
    """
    if ind != 1:
        return None
    dcm = re.match(r"dataCategory:\s*(?P<v>.+)$", stripped)
    return dcm.group("v").strip() if dcm else None


def _collect_annotation(stripped: str, ind: int) -> str | None:
    """Return the raw ``annotation <name> = <value>`` line (for D7), or None.

    Annotations count at the table level or one deeper (``ind <= 1``). Returns
    None for any non-annotation or too-deep line.
    """
    if ind <= 1 and re.match(r"annotation\s+.+", stripped):
        return stripped
    return None


def _parse_table_block(
    lines: list[str], i: int, n: int
) -> tuple[str, TmdlMeasure | TmdlColumn | str, int] | None:
    """Dispatch a single multi-line table block starting at line ``i``.

    Recognizes the three block kinds :func:`parse_tmdl` consumes as whole
    blocks — ``measure``/``column`` (indent level 1) and ``partition``/``source``
    (raw M body). Returns ``(kind, parsed_item, next_index)`` where ``kind`` is
    ``"measure"``, ``"column"`` or ``"source"``, or ``None`` if the line is not
    a block header (leaving single-line collectors to the caller).
    """
    stripped = lines[i].strip()
    ind = _indent(lines[i])
    measure_header = _is_measure_header(stripped)
    if measure_header and ind == 1:
        measure, j = _parse_measure_block(lines, i, n, measure_header)
        return "measure", measure, j

    column_header = _is_column_header(stripped)
    if column_header and ind == 1:
        column, j = _parse_column_block(lines, i, n, column_header)
        return "column", column, j

    if _is_source_header(stripped):
        source_text, j = _parse_source_block(lines, i, n, stripped)
        return "source", source_text, j

    return None


def parse_tmdl(text: str) -> TmdlTable | None:
    """Parse a single TMDL *table* file's text and return a :class:`TmdlTable`.

    Returns ``None`` if the file does not contain a top-level ``table`` block
    (e.g. ``relationships.tmdl``, ``model.tmdl`` header-only files).

    The parser is indentation-driven (TMDL uses tabs). It captures:
    - All ``measure`` blocks at indent level 1 (name, expression, displayFolder).
    - All ``column`` blocks at indent level 1 (name, dataType, summarizeBy).
    - All ``partition/source`` blocks (raw M body for D8).
    - All ``annotation`` lines at indent level <= 1 (raw text for D7).
    """
    lines = _strip_bom(text).splitlines()
    table_name, table_line = _find_table_header(lines)

    if table_name is None:
        return None

    measures: list[TmdlMeasure] = []
    columns: list[TmdlColumn] = []
    sources: list[str] = []
    annotations: list[str] = []
    data_category: str | None = None

    # Maps each block kind reported by ``_parse_table_block`` to the list that
    # collects it, so the dispatch is a single lookup rather than a branch chain.
    buckets: dict[str, list] = {
        "measure": measures,
        "column": columns,
        "source": sources,
    }

    n = len(lines)
    i = 0
    while i < n:
        stripped = lines[i].strip()
        ind = _indent(lines[i])

        # A measure / column / source block spans multiple lines: record it in
        # its target list and jump past the whole block.
        block = _parse_table_block(lines, i, n)
        if block is not None:
            kind, item, j = block
            buckets[kind].append(item)
            i = j
            continue

        # Single-line collectors record and fall through to the next line.
        data_category_value = _parse_data_category(stripped, ind)
        if data_category_value is not None:
            data_category = data_category_value
        annotation = _collect_annotation(stripped, ind)
        if annotation is not None:
            annotations.append(annotation)

        i += 1

    return TmdlTable(
        name=table_name,
        measures=tuple(measures),
        columns=tuple(columns),
        partition_sources=tuple(sources),
        annotations=tuple(annotations),
        line=table_line,
        data_category=data_category,
    )


def _is_relationship_header(raw: str) -> re.Match[str] | None:
    """Match a top-level ``relationship <name>`` header line, or None.

    Only a column-0 line qualifies; a deeper-indented ``relationship`` word is
    not a top-level block header.
    """
    if _indent(raw) != 0:
        return None
    return re.match(r"relationship\s+('?)(?P<name>[^'\n]+?)\1\s*$", raw.strip())


def _parse_relationship_block(
    lines: list[str], i: int, n: int, match: re.Match[str]
) -> tuple[TmdlRelationship, int]:
    """Parse a top-level ``relationship`` block starting at line ``i`` (0-based).

    ``match`` is the already-matched header regex. Returns the parsed
    :class:`TmdlRelationship` and the index of the first line past the block,
    capturing the ``crossFilteringBehavior`` property (or ``None`` if absent).
    """
    name = match.group("name").strip()
    cfb: str | None = None
    j = i + 1
    while _continues_block(lines, j, n, 0):
        c = re.match(r"crossFilteringBehavior:\s*(?P<v>.+)$", lines[j].strip())
        if c:
            cfb = c.group("v").strip()
        j += 1
    relationship = TmdlRelationship(name=name, cross_filtering_behavior=cfb, line=i + 1)
    return relationship, j


def parse_relationships(text: str) -> tuple[TmdlRelationship, ...]:
    """Parse a ``relationships.tmdl`` file and return all relationship blocks.

    Each top-level ``relationship <name>`` block is captured with its
    ``crossFilteringBehavior`` property (or ``None`` if absent).
    """
    lines = _strip_bom(text).splitlines()
    n = len(lines)
    # A linear scan over every line is equivalent to skipping past each parsed
    # block: block-continuation lines are deeper-indented (or blank), so
    # _is_relationship_header can never match inside a block.
    rels = [
        _parse_relationship_block(lines, i, n, rm)[0]
        for i, raw in enumerate(lines)
        if (rm := _is_relationship_header(raw)) is not None
    ]
    return tuple(rels)


def iter_model_files(ctx: RuleContext, suffix: str) -> Iterable[tuple[str, str]]:
    """Yield ``(repo_relative_path, text)`` for TMDL model definition files.

    Scans ``ctx.tracked_files`` for paths containing
    ``*.SemanticModel/definition/`` and ending with ``suffix``
    (e.g. ``".tmdl"``). Files under ``tests/`` are **exempted** so that the
    M0 golden fixture's intentional violation content does not trigger rules
    when running against the real repo.

    Reads files from ``ctx.repo_root`` using ``encoding="utf-8-sig"`` (BOM-
    tolerant).
    """
    for rel in ctx.tracked_files:
        if is_test_path(rel):
            continue
        if ".SemanticModel/definition/" in rel and rel.endswith(suffix):
            text = (ctx.repo_root / Path(rel)).read_text(encoding="utf-8-sig")
            yield rel, text


def normalize_measure_body(expression: str) -> str:
    """Normalize a measure expression for duplicate-detection (D3).

    Steps:
    1. Strip ``/* */`` block comments.
    2. Strip ``//`` line comments.
    3. Collapse runs of whitespace to a single space.
    4. Strip spaces around punctuation (``( ) [ ] , = + - * /``) so that
       ``SUM( Sales[Amount] )`` and ``SUM(Sales[Amount])`` canonicalize to
       the same string.
    5. Lowercase and trim.

    The result is used as a hash key; two measures with the same normalized
    body are flagged as duplicates by D3.
    """
    no_block = re.sub(r"/\*.*?\*/", " ", expression, flags=re.DOTALL)
    no_line = re.sub(r"//[^\n]*", " ", no_block)
    collapsed = re.sub(r"\s+", " ", no_line).strip().lower()
    # Strip optional spaces around punctuation characters.
    collapsed = re.sub(r"\s*([(),\[\]=+\-*/])\s*", r"\1", collapsed)
    return collapsed


# ---------------------------------------------------------------------------
# Legacy API kept intact (M0 regression anchor)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MSource:
    """A raw M source block extracted from a TMDL model file.

    Attributes:
        text: the full raw M block text (multi-line, original whitespace preserved).
        locator: "repo_relative_path" — no line number (block spans multiple lines).
    """

    text: str
    locator: str


def _is_shared_expression_header(stripped: str, ind: int) -> bool:
    """True for a top-level ``expression <name> = …`` shared-M-expression header."""
    return bool(re.match(r"expression\s+\S", stripped)) and ind == 0


def _parse_m_partition_source(lines: list[str], i: int, n: int) -> tuple[str, int]:
    """Parse a partition-source block for :func:`iter_m_sources`.

    Returns the raw (unstripped, newline-joined) multi-line body text and the
    index of the first line past the block. NOTE: unlike
    :func:`_parse_source_block` (used by ``parse_tmdl``), this preserves
    original line whitespace and blank lines in the body — callers need the
    raw M text to run ``stale_schema_tokens`` and inspect ``.Database(`` call
    arguments.
    """
    ind = _indent(lines[i])
    children, j = _block_body_lines(lines, i, n, ind)
    body_lines = [lines[i].strip().split("=", 1)[1].strip(), *children]
    return "\n".join(body_lines).strip(), j


def _parse_m_shared_expression(
    lines: list[str], i: int, n: int, stripped: str
) -> tuple[str, int]:
    """Parse a top-level shared ``expression <name> = …`` block.

    Returns the raw (unstripped, newline-joined) multi-line body text and the
    index of the first line past the block.
    """
    first = stripped.split("=", 1)[1].strip() if "=" in stripped else ""
    children, j = _block_body_lines(lines, i, n, 0)
    body_lines = [first, *children]
    return "\n".join(body_lines).strip(), j


def _tmdl_files_to_scan(
    repo_root: Path, tracked_files: tuple[str, ...]
) -> Iterable[tuple[str, str]]:
    """Yield ``(rel, text)`` for each tracked TMDL file eligible for M scanning.

    Applies the same file-selection guards as :func:`iter_model_files`: skip
    ``tests/`` paths, require the ``*.SemanticModel/definition/`` segment and a
    ``.tmdl`` suffix (case-insensitive), and silently skip files that cannot be
    read. Text is read ``encoding="utf-8-sig"`` (BOM-tolerant).
    """
    for rel in tracked_files:
        if is_test_path(rel):
            continue
        if ".SemanticModel/definition/" not in rel:
            continue
        if not rel.lower().endswith(".tmdl"):
            continue
        try:
            text = (repo_root / Path(rel)).read_text(encoding="utf-8-sig")
        except OSError:
            continue
        yield rel, text


def _iter_m_sources_in_file(text: str, rel: str) -> Iterable[MSource]:
    """Yield every M partition-source and shared-expression block in one file.

    ``rel`` is the repo-relative path used as each :class:`MSource` locator.
    Scans ``text`` line by line, jumping past each recognized block.
    """
    lines = text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        stripped = lines[i].strip()
        ind = _indent(lines[i])

        # Partition source block: ``source =`` or ``partition <name> =``
        if _is_source_header(stripped):
            source_text, j = _parse_m_partition_source(lines, i, n)
            yield MSource(text=source_text, locator=rel)
            i = j
            continue

        # Shared expression block: top-level ``expression <name> = …``
        if _is_shared_expression_header(stripped, ind):
            source_text, j = _parse_m_shared_expression(lines, i, n, stripped)
            yield MSource(text=source_text, locator=rel)
            i = j
            continue

        i += 1


def iter_m_sources(
    repo_root: Path, tracked_files: tuple[str, ...]
) -> Iterable[MSource]:
    """Yield every M partition-source block and shared-expression block.

    Walks all tracked TMDL files inside ``*.SemanticModel/definition/``
    (case-insensitive suffix match for ``.tmdl``). Files under ``tests/``
    are exempted (same policy as :func:`iter_model_files`).

    Captures two block types:

    * **Partition sources** — ``source =`` or ``partition <name> =`` blocks
      inside a table file.
    * **Shared expressions** — top-level ``expression <name> = …`` blocks
      (Power BI shared M expressions / named ranges).

    This is intentionally independent of ``TmdlTable.partition_sources`` which
    collapses each source to a single joined string — here we need the
    multi-line raw body to run ``stale_schema_tokens`` over string literals
    embedded in the M code (D8) and to inspect ``.Database(`` call arguments
    (C1).
    """
    for rel, text in _tmdl_files_to_scan(repo_root, tracked_files):
        yield from _iter_m_sources_in_file(text, rel)


def top_level_blocks(text: str) -> list[str]:
    """Return the stripped header line of each indentation-level-0 block, in order.

    A "top-level block" is any non-blank line that starts at column 0 (no leading
    whitespace) and is not a continuation. This is the M0 regression anchor — tests
    in ``tests/unit/test_tmdl.py`` assert specific values observed in the golden
    fixture. Do NOT modify the return type or semantics.
    """
    headers: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        if raw_line[0] in (" ", "\t"):
            continue
        headers.append(raw_line.strip())
    return headers
