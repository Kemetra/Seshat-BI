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
    *** PROVISIONAL ***  This is the table-level annotation form that M4.1's
    ``DATE_TABLE_MARKER`` constant consumes, used here so M0 and M4 agree. The exact
    "Mark as Date Table" TMDL literal is NOT yet confirmed against a real Power BI
    capture (spec §5.2 D7 note / §13 flag it may differ). RE-VERIFY against the real
    PBIP captured in Task M0.3 before M4 builds D7. If the captured real fixture shows
    a different marker literal, update BOTH M0 and M4.1's DATE_TABLE_MARKER together.

PUBLIC API (consumed by D1-D8 rules and by M4b):
  - TmdlMeasure(name, expression, display_folder, line)
  - TmdlColumn(name, data_type, summarize_by, line)
  - TmdlRelationship(name, cross_filtering_behavior, line)
  - TmdlTable(name, measures, columns, partition_sources, annotations, line)
  - TmdlModel(tables, relationships)
  - MSource(text, locator)
  - parse_tmdl(text: str) -> TmdlTable | None
  - parse_relationships(text: str) -> tuple[TmdlRelationship, ...]
  - iter_model_files(ctx: RuleContext, suffix: str) -> Iterable[tuple[str, str]]
  - iter_m_sources(repo_root: Path, tracked_files: tuple[str, ...]) -> Iterable[MSource]
  - normalize_measure_body(expression: str) -> str
  - top_level_blocks(text: str) -> list[str]   (M0 regression anchor — kept intact)
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
# Pinned to the table-level marker literal M0 captured from a real
# "Mark as Date Table" PBIP. M4 consumes this single constant; if M0's
# observed literal differs, only this line changes (single source of truth,
# per spec §9.0 / §13). Column-level `dataCategory: Time` alone is NOT the
# marker (spec line 135).

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
        partition_sources: RAW M source body texts (for D8).
        annotations: raw ``annotation <name> = <value>`` lines (for D7 marker).
        line: 1-based line number of the ``table`` header.
    """

    name: str
    measures: tuple[TmdlMeasure, ...]
    columns: tuple[TmdlColumn, ...]
    partition_sources: tuple[str, ...]
    annotations: tuple[str, ...]
    line: int


@dataclass(frozen=True)
class TmdlModel:
    """Parsed representation of a full semantic model (all tables + relationships).

    Attributes:
        tables: all parsed tables.
        relationships: all parsed relationships.
    """

    tables: tuple[TmdlTable, ...]
    relationships: tuple[TmdlRelationship, ...]


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
    table_name: str | None = None
    table_line = 0

    # Find the top-level ``table <name>`` header.
    for i, raw in enumerate(lines, start=1):
        m = re.match(r"table\s+('?)(?P<name>[^'\n]+?)\1\s*$", raw.strip())
        if raw and _indent(raw) == 0 and m:
            table_name = m.group("name")
            table_line = i
            break

    if table_name is None:
        return None

    measures: list[TmdlMeasure] = []
    columns: list[TmdlColumn] = []
    sources: list[str] = []
    annotations: list[str] = []

    n = len(lines)
    i = 0
    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        ind = _indent(raw)

        # --- measure block ---
        mm = re.match(
            r"measure\s+('?)(?P<name>[^'=]+?)\1\s*=\s*(?P<expr>.*)$", stripped
        )
        if mm and ind == 1:
            name = mm.group("name").strip()
            expr_parts = [mm.group("expr").rstrip()]
            df: str | None = None
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                child = lines[j].strip()
                dfm = re.match(r"displayFolder:\s*(?P<v>.+)$", child)
                if dfm:
                    df = dfm.group("v").strip()
                elif child and not re.match(r"\w+:\s", child):
                    # continuation of a multi-line expression
                    expr_parts.append(child)
                j += 1
            measures.append(
                TmdlMeasure(
                    name=name,
                    expression=" ".join(expr_parts).strip(),
                    display_folder=df,
                    line=i + 1,
                )
            )
            i = j
            continue

        # --- column block ---
        cm = re.match(r"column\s+('?)(?P<name>[^'\n]+?)\1\s*$", stripped)
        if cm and ind == 1:
            name = cm.group("name").strip()
            dt: str | None = None
            sb: str | None = None
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                child = lines[j].strip()
                d = re.match(r"dataType:\s*(?P<v>.+)$", child)
                s = re.match(r"summarizeBy:\s*(?P<v>.+)$", child)
                if d:
                    dt = d.group("v").strip()
                if s:
                    sb = s.group("v").strip()
                j += 1
            columns.append(
                TmdlColumn(name=name, data_type=dt, summarize_by=sb, line=i + 1)
            )
            i = j
            continue

        # --- partition / source block (raw M body for D8) ---
        # Require a real assignment header: ``source =`` or ``partition <name> =``.
        # The anchored form avoids matching column-property lines such as
        # ``source_type = ...`` that merely start with the word "source".
        if re.match(r"(source\s*=|partition\s+\S+\s*=)", stripped):
            body = [stripped.split("=", 1)[1].strip()]
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                if lines[j].strip():
                    body.append(lines[j].strip())
                j += 1
            sources.append(" ".join(p for p in body if p).strip())
            i = j
            continue

        # --- annotation lines ---
        if re.match(r"annotation\s+.+", stripped) and ind <= 1:
            annotations.append(stripped)

        i += 1

    return TmdlTable(
        name=table_name,
        measures=tuple(measures),
        columns=tuple(columns),
        partition_sources=tuple(sources),
        annotations=tuple(annotations),
        line=table_line,
    )


def parse_relationships(text: str) -> tuple[TmdlRelationship, ...]:
    """Parse a ``relationships.tmdl`` file and return all relationship blocks.

    Each top-level ``relationship <name>`` block is captured with its
    ``crossFilteringBehavior`` property (or ``None`` if absent).
    """
    lines = _strip_bom(text).splitlines()
    rels: list[TmdlRelationship] = []
    n = len(lines)
    i = 0
    while i < n:
        stripped = lines[i].strip()
        rm = re.match(r"relationship\s+('?)(?P<name>[^'\n]+?)\1\s*$", stripped)
        if rm and _indent(lines[i]) == 0:
            name = rm.group("name").strip()
            cfb: str | None = None
            j = i + 1
            while j < n and (not lines[j].strip() or _indent(lines[j]) > 0):
                c = re.match(r"crossFilteringBehavior:\s*(?P<v>.+)$", lines[j].strip())
                if c:
                    cfb = c.group("v").strip()
                j += 1
            rels.append(
                TmdlRelationship(name=name, cross_filtering_behavior=cfb, line=i + 1)
            )
            i = j
            continue
        i += 1
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
    for rel in tracked_files:
        if is_test_path(rel):
            continue
        if ".SemanticModel/definition/" not in rel:
            continue
        if not rel.lower().endswith(".tmdl"):
            continue
        path = repo_root / Path(rel)
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        lines = text.splitlines()
        n = len(lines)
        i = 0
        while i < n:
            raw = lines[i]
            stripped = raw.strip()
            ind = _indent(raw)

            # Partition source block: ``source =`` or ``partition <name> =``
            if re.match(r"(source\s*=|partition\s+\S+\s*=)", stripped):
                body_lines = [stripped.split("=", 1)[1].strip()]
                j = i + 1
                while j < n and (not lines[j].strip() or _indent(lines[j]) > ind):
                    body_lines.append(lines[j])
                    j += 1
                yield MSource(
                    text="\n".join(body_lines).strip(),
                    locator=rel,
                )
                i = j
                continue

            # Shared expression block: top-level ``expression <name> = …``
            if re.match(r"expression\s+\S", stripped) and ind == 0:
                first = stripped.split("=", 1)[1].strip() if "=" in stripped else ""
                body_lines = [first]
                j = i + 1
                while j < n and (not lines[j].strip() or _indent(lines[j]) > 0):
                    body_lines.append(lines[j])
                    j += 1
                yield MSource(
                    text="\n".join(body_lines).strip(),
                    locator=rel,
                )
                i = j
                continue

            i += 1


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
