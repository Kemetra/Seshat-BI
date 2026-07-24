"""Shared dbt files -- surgical, byte-faithful row removal (Q1 of #433).

The reset planner's shared-file leg: compute the rows attributable to ONE
table in ``dbt/selectors.yml`` and ``dbt/models/sources/_sources.yml``,
splice them out as whole ``- `` blocks (other tables' rows stay
byte-identical), and verify the edited text re-parses to the independently
computed expected document -- else fail closed and tell the operator to
hand-edit. Split from ``seshat.reset`` so each module stays a reviewable
size; ``seshat.reset`` re-exports the public names.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import yaml

_SELECTORS_REL = "dbt/selectors.yml"
_SOURCES_REL = "dbt/models/sources/_sources.yml"


class ResetError(ValueError):
    """A documented refusal, named by ``reason`` (never a raw traceback)."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class SharedFileEdit:
    """One surgical shared-file edit: remove only this table's rows.

    ``original_text`` pins the file content the edit was computed against;
    the executor refuses if the file changed since planning. ``new_text`` is
    the exact post-edit text (other tables' rows byte-identical); when the
    removal empties the whole file, ``remove_file`` is set instead.
    """

    path: str
    removed_rows: tuple[str, ...]
    original_text: str
    new_text: str
    remove_file: bool = False


def _read_shared(path: Path, rel: str) -> tuple[str, object]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            text = handle.read()
    except (OSError, UnicodeError) as exc:
        raise ResetError(
            "shared_file_unreadable",
            f"{rel} could not be read ({exc.__class__.__name__}); fix or "
            "remove it before resetting",
        ) from exc
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ResetError(
            "shared_file_unreadable",
            f"{rel} is not valid YAML ({exc.__class__.__name__}); it may "
            "carry rows for this table that cannot be removed safely -- fix "
            "it by hand before resetting",
        ) from exc
    return text, document


@dataclass(frozen=True)
class _Block:
    """One ``- ...`` sequence item as a line range [start, end)."""

    start: int
    end: int
    indent: int
    name: str | None


def _unquoted(value: str) -> str:
    """Strip one matching pair of surrounding quotes, if present."""
    if len(value) < 2:
        return value
    if value[0] != value[-1] or value[0] not in "'\"":
        return value
    return value[1:-1]


def _item_name(stripped: str) -> str | None:
    if not stripped.startswith("- name:"):
        return None
    value = _unquoted(stripped[len("- name:") :].strip())
    return value or None


def _block_end(lines: list[str], start: int, indent: int) -> int:
    """First line after ``start`` that is non-blank and not deeper-indented."""
    end = start + 1
    while end < len(lines):
        follower = lines[end]
        follower_indent = len(follower) - len(follower.lstrip(" "))
        if follower.strip() and follower_indent <= indent:
            break
        end += 1
    return end


def _sequence_blocks(lines: list[str]) -> list[_Block]:
    """Every ``- `` item block: the dash line plus its deeper-indented tail."""
    blocks: list[_Block] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        indent = len(line) - len(line.lstrip(" "))
        end = _block_end(lines, index, indent)
        blocks.append(_Block(index, end, indent, _item_name(stripped)))
    return blocks


def _splice_out(lines: list[str], ranges: list[tuple[int, int]]) -> str:
    keep = list(lines)
    for start, end in sorted(ranges, reverse=True):
        del keep[start:end]
    return "".join(keep)


def _edit_refusal(rel: str) -> ResetError:
    return ResetError(
        "shared_file_edit_unsupported",
        f"{rel} carries rows for this table but is not in a shape this "
        "surgical edit can verify; remove the table's rows by hand and "
        "retry",
    )


def _verify_edit(rel: str, new_text: str, expected: object) -> None:
    """The byte-level edit must parse to EXACTLY the expected document."""
    try:
        actual = yaml.safe_load(new_text)
    except yaml.YAMLError:
        raise _edit_refusal(rel) from None
    if actual != expected:
        raise _edit_refusal(rel)


def _has_named_row(rows: object, name: str) -> bool:
    """``rows`` is a list carrying a ``{name: <name>}`` mapping row."""
    if not isinstance(rows, list):
        return False
    return any(isinstance(row, dict) and row.get("name") == name for row in rows)


def _selectors_expected(document: dict, rows: list, selector: str) -> tuple[list, dict]:
    """(surviving rows, expected post-edit document) without ``selector``."""
    expected_rows = [
        row
        for row in rows
        if not (isinstance(row, dict) and row.get("name") == selector)
    ]
    return expected_rows, {**document, "selectors": expected_rows}


def _selector_block_ranges(lines: list[str], selector: str) -> list[tuple[int, int]]:
    return [
        (block.start, block.end)
        for block in _sequence_blocks(lines)
        if block.name == selector
    ]


def _selectors_edit(root: Path, table: str) -> SharedFileEdit | None:
    path = root / Path(*_SELECTORS_REL.split("/"))
    if not path.is_file():
        return None
    text, document = _read_shared(path, _SELECTORS_REL)
    selector = f"seshat_table_{table}"
    rows = document.get("selectors") if isinstance(document, dict) else None
    if not _has_named_row(rows, selector):
        return None
    expected_rows, expected = _selectors_expected(document, rows, selector)
    lines = text.splitlines(keepends=True)
    targets = _selector_block_ranges(lines, selector)
    if not targets:
        raise _edit_refusal(_SELECTORS_REL)
    new_text = _splice_out(lines, targets)
    if not expected_rows and len(expected) == 1:
        new_text = "selectors: []\n"
    _verify_edit(_SELECTORS_REL, new_text, expected)
    return SharedFileEdit(
        path=_SELECTORS_REL,
        removed_rows=(f"selector {selector}",),
        original_text=text,
        new_text=new_text,
    )


def _marts_model_names(root: Path, table: str) -> frozenset[str]:
    """The gold model names this table emitted (its marts .sql stems) -- the
    only rows of the shared ``migration_gold`` source group attributable to
    this table (a reused conformed dimension is owned elsewhere and never
    listed by the reuser)."""
    marts = root / "dbt" / "models" / "marts" / table
    if not marts.is_dir():
        return frozenset()
    return frozenset(
        entry.stem
        for entry in marts.iterdir()
        if entry.is_file() and entry.suffix == ".sql"
    )


def _group_rows_matching(
    group: object, removable: dict[str, set[str]]
) -> tuple[str, set[str]] | None:
    """(group name, matched row names) when the group carries removable rows."""
    if not isinstance(group, dict):
        return None
    allowed = removable.get(group.get("name"))
    tables = group.get("tables")
    if allowed is None or not isinstance(tables, list):
        return None
    matched = {
        row.get("name")
        for row in tables
        if isinstance(row, dict) and row.get("name") in allowed
    }
    return (group.get("name"), matched) if matched else None


def _rows_to_remove(
    document: dict, table: str, gold_names: frozenset[str]
) -> dict[str, set[str]]:
    removable = {"bronze": {table}, "migration_gold": set(gold_names)}
    planned: dict[str, set[str]] = {}
    for group in document.get("sources", []) or []:
        match = _group_rows_matching(group, removable)
        if match is not None:
            planned[match[0]] = match[1]
    return planned


def _surviving_group(group: object, planned: dict[str, set[str]]) -> object | None:
    """The group with its planned rows removed; None when it empties entirely."""
    if not (isinstance(group, dict) and group.get("name") in planned):
        return group
    removed = planned[group["name"]]
    group["tables"] = [
        row
        for row in group.get("tables", [])
        if not (isinstance(row, dict) and row.get("name") in removed)
    ]
    return group if group["tables"] else None


def _expected_sources(document: dict, planned: dict[str, set[str]]) -> dict:
    expected = copy.deepcopy(document)
    remaining_groups: list = []
    for group in expected.get("sources", []) or []:
        survivor = _surviving_group(group, planned)
        if survivor is not None:
            remaining_groups.append(survivor)
    expected["sources"] = remaining_groups
    return expected


def _removes_whole_group(
    name: str | None, planned: dict[str, set[str]], surviving: set
) -> bool:
    """The plan empties this top-level group, so its whole block goes."""
    return name in planned and name not in surviving


def _removes_row(
    block: _Block, group: str | None, planned: dict[str, set[str]], surviving: set
) -> bool:
    """The block is a planned row inside a group that otherwise survives."""
    if group not in planned or group not in surviving:
        return False
    return block.name in planned[group]


def _sources_row_ranges(
    lines: list[str], planned: dict[str, set[str]], expected: dict
) -> list[tuple[int, int]]:
    """Line ranges to splice out: whole emptied groups, else single rows."""
    surviving = {
        group.get("name")
        for group in expected.get("sources", [])
        if isinstance(group, dict)
    }
    blocks = _sequence_blocks(lines)
    top_indent = min(block.indent for block in blocks)
    ranges: list[tuple[int, int]] = []
    current_group: str | None = None
    for block in blocks:
        if block.indent == top_indent:
            current_group = block.name
            if _removes_whole_group(current_group, planned, surviving):
                ranges.append((block.start, block.end))
        elif _removes_row(block, current_group, planned, surviving):
            ranges.append((block.start, block.end))
    return ranges


def _require_sources_mapping(document: object) -> dict:
    if not isinstance(document, dict):
        raise ResetError(
            "shared_file_unreadable",
            f"{_SOURCES_REL} is not a YAML mapping; fix it by hand before resetting",
        )
    return document


def _removed_row_labels(planned: dict[str, set[str]]) -> tuple[str, ...]:
    return tuple(
        f"{group}: {name}"
        for group in sorted(planned)
        for name in sorted(planned[group])
    )


def _spliced_sources_text(
    text: str, planned: dict[str, set[str]], expected: dict
) -> str:
    """The byte-faithful post-edit text, verified against ``expected``."""
    lines = text.splitlines(keepends=True)
    ranges = _sources_row_ranges(lines, planned, expected)
    if not ranges:
        raise _edit_refusal(_SOURCES_REL)
    new_text = _splice_out(lines, ranges)
    _verify_edit(_SOURCES_REL, new_text, expected)
    return new_text


def _sources_edit(root: Path, table: str) -> SharedFileEdit | None:
    path = root / Path(*_SOURCES_REL.split("/"))
    if not path.is_file():
        return None
    text, document = _read_shared(path, _SOURCES_REL)
    document = _require_sources_mapping(document)
    planned = _rows_to_remove(document, table, _marts_model_names(root, table))
    if not planned:
        return None
    expected = _expected_sources(document, planned)
    removed_rows = _removed_row_labels(planned)
    if not expected["sources"]:
        # Every group emptied: the shared file is entirely this table's
        # residue, so the plan removes the file itself.
        return SharedFileEdit(
            path=_SOURCES_REL,
            removed_rows=removed_rows,
            original_text=text,
            new_text="",
            remove_file=True,
        )
    return SharedFileEdit(
        path=_SOURCES_REL,
        removed_rows=removed_rows,
        original_text=text,
        new_text=_spliced_sources_text(text, planned, expected),
    )
