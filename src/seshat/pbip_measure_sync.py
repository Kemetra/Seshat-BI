"""Governed measure sync into an ADOPTED PBIP semantic model (issue #457).

``adopt-pbip measure-sync`` upserts APPROVED metric-contract measures into an
existing table ``.tmdl`` inside a scaffolded (adopted) PBIP model. Fail-closed
at every step:

- only a model recorded by an accepted adoption manifest is served (the
  governance hook: ``adopt-pbip assess`` -> ``scaffold`` must have run);
- only contracts passing :func:`load_contract_inventory` (owner-approved,
  named ``semantic_model_ready`` approval) are rendered -- every exclusion is
  reported with its reason, never silently skipped;
- every measure re-verifies through :func:`generate_measure` (L3 semantic
  drift + D1-D11 form rules); one unrenderable contract refuses the whole run;
- the partition/M-source region is proven byte-identical before AND after
  every write (post-write re-read; rollback on any difference);
- writes are atomic (staged temp file + ``os.replace``), all-or-nothing.

Partition/M-source content is NEVER echoed into any output -- it may carry
connection details. All refusal prose is fixed (mirrors ``_boundaries``).
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .metric_contract_inventory import MetricContract, normalize_table_binding
from .pbip_adoption import MANIFEST_PATH
from .tmdl import (
    _continues_block,
    _indent,
    _is_column_header,
    _is_measure_header,
    _is_source_header,
)

SCHEMA_VERSION = "1.0"

_BOM = b"\xef\xbb\xbf"
_LINEAGE_TAG = re.compile(r"^\t*lineageTag:\s*(?P<value>\S+)\s*$")

_NO_MANIFEST = (
    "No adoption manifest was found for this model; run adopt-pbip assess, "
    "review the digest, then adopt-pbip scaffold before measure-sync."
)
_MANIFEST_UNREADABLE = (
    "The adoption manifest exists but could not be read; re-run adopt-pbip "
    "assess and scaffold to restore a usable baseline."
)
_MANIFEST_MISMATCH = (
    "The adoption manifest does not record this semantic model as its adopted "
    "target; assess and scaffold the project containing this model first."
)
_NO_APPROVED = (
    "No approved metric contract binds to the requested table; nothing to sync."
)
_TABLE_ABSENT = (
    "No table definition matching the requested table name was found under the "
    "model's definition/tables/ directory."
)
_TABLE_AMBIGUOUS = (
    "More than one table definition matches the requested table name; resolve "
    "the duplicate before syncing."
)
_DUPLICATE_MEASURE = (
    "The table definition declares the same measure name more than once; "
    "resolve the duplicate before syncing."
)
_PARTITION_TOUCH = (
    "A planned measure edit would touch the partition/M-source region; "
    "refusing to modify source bindings."
)
_PARTITION_DRIFT = (
    "Post-write verification found a partition/M-source difference; the file "
    "was restored and nothing was synced."
)


# ---------------------------------------------------------------------------
# Result document
# ---------------------------------------------------------------------------


def _result(
    outcome: str,
    *,
    table: str,
    table_file: str | None = None,
    actions: Iterable[dict[str, str]] = (),
    excluded: Iterable[str] = (),
    blockers: Iterable[str] = (),
    dry_run: bool = False,
) -> dict[str, Any]:
    action_list = list(actions)
    counts = {"insert": 0, "update": 0, "skip": 0}
    for action in action_list:
        counts[action["action"]] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": outcome,
        "table": table,
        "table_file": table_file,
        "dry_run": dry_run,
        "actions": action_list,
        "counts": counts,
        "excluded": list(excluded),
        "blocking_reasons": list(blockers),
        "next_step": "value-check",
    }


def measure_sync_exit_code(result: dict[str, Any]) -> int:
    if result["outcome"] in ("synced", "planned"):
        return 0
    return 2 if result["outcome"] == "input_defect" else 1


def render_measure_sync_text(result: dict[str, Any], prog: str = "seshat") -> str:
    """Human-readable rendering; ``prog`` is the brand the client typed."""
    lines = [
        f"PBIP measure sync: {result['outcome']}",
        f"Table: {result['table']}",
    ]
    if result["table_file"]:
        lines.append(f"Table file: {result['table_file']}")
    lines.extend(
        f"- {action['action']} {action['measure']}" for action in result["actions"]
    )
    counts = result["counts"]
    lines.append("Counts: insert={insert} update={update} skip={skip}".format(**counts))
    lines.extend(f"Excluded: {reason}" for reason in result["excluded"])
    lines.extend(f"Blocker: {reason}" for reason in result["blocking_reasons"])
    if result["outcome"] in ("synced", "planned"):
        lines.append(
            f"Next step: {prog} value-check verifies each synced measure "
            "against live gold values (not run here)."
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Governance gates
# ---------------------------------------------------------------------------


def _manifest_components(model_dir: Path) -> list[Any] | str:
    """Parsed manifest components for the model's project, or a refusal."""
    manifest = model_dir.parent / Path(MANIFEST_PATH)
    if not manifest.is_file():
        return _NO_MANIFEST
    try:
        import yaml

        document = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return _MANIFEST_UNREADABLE
    if not isinstance(document, dict):
        return _MANIFEST_UNREADABLE
    target = document.get("target")
    components = target.get("components") if isinstance(target, dict) else None
    if not isinstance(components, list):
        return _MANIFEST_UNREADABLE
    return components


def _manifest_gate(model_dir: Path) -> str | None:
    """Refusal reason unless the adoption manifest records THIS model."""
    components = _manifest_components(model_dir)
    if isinstance(components, str):
        return components
    prefix = model_dir.name + "/"
    recorded = any(
        isinstance(component, dict)
        and isinstance(component.get("artifact"), str)
        and component["artifact"].startswith(prefix)
        for component in components
    )
    return None if recorded else _MANIFEST_MISMATCH


def _approved_for_table(
    repo_root: Path, metrics_dir: str, table: str
) -> tuple[list[MetricContract], list[str]]:
    """Approved contracts bound to ``table`` plus every exclusion reason."""
    from .metric_contract_inventory import load_contract_inventory

    paths = sorted((repo_root / metrics_dir).glob("*/metrics/*.yaml"))
    inventory = load_contract_inventory(paths, repo_root)
    wanted = normalize_table_binding(table)
    matching = [
        contract
        for contract in inventory.approved.values()
        if normalize_table_binding(contract.gold_table) == wanted
    ]
    return sorted(matching, key=lambda contract: contract.name), list(inventory.errors)


def _render_contracts(
    contracts: list[MetricContract],
) -> tuple[dict[str, str], list[str]]:
    """Verified TMDL block per contract, or the reasons the run must refuse."""
    from .dax_gen import generate_measure, load_contract

    rendered: dict[str, str] = {}
    errors: list[str] = []
    for contract in contracts:
        try:
            raw = load_contract(str(contract.path))
        except (OSError, ValueError) as exc:
            errors.append(f"{contract.name}: contract became unreadable: {exc}")
            continue
        result = generate_measure(
            contract.definition,
            name=contract.name,
            doc_intent=raw.get("formula_intent"),
        )
        if not result.ok:
            errors.append(f"{contract.name}: {result.reason}")
        else:
            assert result.tmdl_block is not None
            rendered[contract.name] = result.tmdl_block
    return rendered, errors


# ---------------------------------------------------------------------------
# Table file discovery and structure scan
# ---------------------------------------------------------------------------


def _find_table_file(model_dir: Path, table: str) -> tuple[Path | None, str | None]:
    """Locate the table's .tmdl by PARSED table name, never filename guess."""
    from .tmdl import parse_tmdl

    tables_dir = model_dir / "definition" / "tables"
    wanted = normalize_table_binding(table)
    matches: list[Path] = []
    if tables_dir.is_dir():
        for path in sorted(tables_dir.glob("*.tmdl")):
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError):
                continue
            parsed = parse_tmdl(text)
            if parsed is not None and normalize_table_binding(parsed.name) == wanted:
                matches.append(path)
    if not matches:
        return None, _TABLE_ABSENT
    if len(matches) > 1:
        return None, _TABLE_AMBIGUOUS
    return matches[0], None


@dataclass(frozen=True)
class _MeasureBlock:
    """One existing measure's replaceable region: [start, end) line indices.

    ``start`` includes the contiguous ``///`` doc lines immediately above the
    header; ``end`` excludes trailing blank separator lines.
    """

    name: str
    start: int
    end: int
    lineage_tag: str | None


def _block_end(lines: list[str], i: int, n: int) -> int:
    """One past the last line of the block whose header is at line ``i``."""
    ind = _indent(lines[i])
    j = i + 1
    while _continues_block(lines, j, n, ind):
        j += 1
    return j


def _trim_trailing_blanks(lines: list[str], start: int, end: int) -> int:
    while end > start and not lines[end - 1].strip():
        end -= 1
    return end


def _doc_start(lines: list[str], header: int) -> int:
    """First line of the contiguous ``///`` doc comment above ``header``."""
    ind = _indent(lines[header])
    start = header
    while (
        start > 0
        and _indent(lines[start - 1]) == ind
        and lines[start - 1].strip().startswith("///")
    ):
        start -= 1
    return start


def _lineage_tag(lines: list[str], start: int, end: int) -> str | None:
    for line in lines[start:end]:
        match = _LINEAGE_TAG.match(line.rstrip("\r\n"))
        if match:
            return match.group("value")
    return None


def _scan_measures(
    lines: list[str],
) -> tuple[dict[str, _MeasureBlock], int, str | None]:
    """Existing measure regions, the insertion anchor, and a duplicate error.

    The anchor is the first indent-1 ``column``/``partition``/``source`` header
    OUTSIDE any measure block (new measures insert before it), or end-of-file.
    """
    n = len(lines)
    measures: dict[str, _MeasureBlock] = {}
    anchor: int | None = None
    i = 0
    while i < n:
        stripped = lines[i].strip()
        ind = _indent(lines[i])
        header = _is_measure_header(stripped)
        if header and ind == 1:
            end = _block_end(lines, i, n)
            name = header.group("name").strip()
            if name in measures:
                return measures, n, _DUPLICATE_MEASURE
            trimmed = _trim_trailing_blanks(lines, i, end)
            measures[name] = _MeasureBlock(
                name=name,
                start=_doc_start(lines, i),
                end=trimmed,
                lineage_tag=_lineage_tag(lines, i, trimmed),
            )
            i = end
            continue
        is_anchor = _is_column_header(stripped) or _is_source_header(stripped)
        if ind == 1 and is_anchor and anchor is None:
            anchor = i
        i += 1
    return measures, n if anchor is None else anchor, None


def _partition_regions(lines: list[str]) -> list[tuple[int, int]]:
    """Every partition/M-source block range, at ANY indent (guard oracle).

    Scanned independently of the measure walk so a source block nested inside
    a malformed measure region is still protected.
    """
    n = len(lines)
    regions: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if _is_source_header(lines[i].strip()):
            end = _block_end(lines, i, n)
            regions.append((i, _trim_trailing_blanks(lines, i, end)))
            i = end
            continue
        i += 1
    return regions


def _partition_texts(lines: list[str]) -> tuple[str, ...]:
    """The byte-identity oracle: raw text of every partition/source block."""
    return tuple("".join(lines[start:end]) for start, end in _partition_regions(lines))


# ---------------------------------------------------------------------------
# Plan and apply
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Edit:
    """Replace lines[start:end] with ``logical_lines`` (no line endings)."""

    start: int
    end: int
    logical_lines: tuple[str, ...]


def _desired_lines(tmdl_block: str, lineage_tag: str | None) -> list[str]:
    """The verified block's logical lines; a replaced measure keeps its
    existing lineageTag (Desktop identity), a new measure gets none."""
    lines = tmdl_block.splitlines()
    if lineage_tag is not None:
        lines.append(f"\t\tlineageTag: {lineage_tag}")
    return lines


def _plan(
    lines: list[str],
    newline: str,
    rendered: dict[str, str],
    measures: dict[str, _MeasureBlock],
    anchor: int,
) -> tuple[list[dict[str, str]], list[_Edit]]:
    """Per-measure action plan plus the concrete line edits (all-or-nothing)."""
    actions: list[dict[str, str]] = []
    edits: list[_Edit] = []
    inserted: list[str] = []
    for name in sorted(rendered):
        existing = measures.get(name)
        desired = _desired_lines(
            rendered[name], existing.lineage_tag if existing else None
        )
        if existing is None:
            actions.append({"measure": name, "action": "insert"})
            inserted.extend([*desired, ""])
            continue
        current = "".join(lines[existing.start : existing.end])
        if current == "".join(line + newline for line in desired):
            actions.append({"measure": name, "action": "skip"})
        else:
            actions.append({"measure": name, "action": "update"})
            edits.append(_Edit(existing.start, existing.end, tuple(desired)))
    if inserted:
        if anchor > 0 and lines[anchor - 1].strip():
            inserted.insert(0, "")
        edits.append(_Edit(anchor, anchor, tuple(inserted)))
    return actions, edits


def _touches_partition(edits: list[_Edit], regions: list[tuple[int, int]]) -> bool:
    """True when any replacement or in-block insertion hits a source region.

    An insertion AT a region's header line (start == end == region start)
    pushes the region down intact and is allowed; anything overlapping the
    region's interior is refused.
    """
    for edit in edits:
        for start, end in regions:
            if edit.start < end and edit.end > start:
                return True
            if edit.start == edit.end and start < edit.start < end:
                return True
    return False


def _apply(lines: list[str], edits: list[_Edit], newline: str) -> list[str]:
    result = list(lines)
    for edit in sorted(edits, key=lambda item: item.start, reverse=True):
        result[edit.start : edit.end] = [line + newline for line in edit.logical_lines]
    return result


# ---------------------------------------------------------------------------
# Atomic write + post-write self-check
# ---------------------------------------------------------------------------


def _atomic_replace(path: Path, data: bytes) -> str | None:
    """Atomically replace ``path``; return an error name on failure.

    Mirrors ``_scaffold._publish_manifest``'s staged-tempfile technique, with
    ``os.replace`` because the target here MUST already exist.
    """
    fd, staging_name = tempfile.mkstemp(
        prefix=".measure-sync-", suffix=".tmp", dir=path.parent
    )
    staging = Path(staging_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging, path)
    except OSError as exc:
        staging.unlink(missing_ok=True)
        return type(exc).__name__
    return None


def _decode_table_bytes(raw: bytes) -> tuple[bytes, str] | None:
    bom = _BOM if raw.startswith(_BOM) else b""
    try:
        return bom, raw[len(bom) :].decode("utf-8")
    except UnicodeDecodeError:
        return None


def _postwrite_partition_check(
    path: Path, original: bytes, expected: tuple[str, ...]
) -> str | None:
    """Re-read the written file; roll back unless partitions are identical."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return f"The synced file could not be re-read safely ({type(exc).__name__})."
    decoded = _decode_table_bytes(raw)
    observed = (
        _partition_texts(decoded[1].splitlines(keepends=True)) if decoded else None
    )
    if observed == expected:
        return None
    _atomic_replace(path, original)
    return _PARTITION_DRIFT


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _SyncTarget:
    """Everything resolved and proven safe before any write is planned."""

    table_path: Path
    table_file: str
    original: bytes
    bom: bytes
    lines: list[str]
    newline: str


def _load_target(model_dir: Path, table: str) -> _SyncTarget | tuple[str, str]:
    """Resolve and read the table file, or ``(outcome, reason)`` on failure."""
    table_path, find_error = _find_table_file(model_dir, table)
    if find_error is not None:
        return "refused", find_error
    assert table_path is not None
    try:
        original = table_path.read_bytes()
    except OSError as exc:
        name = type(exc).__name__
        return "input_defect", f"table file could not be read safely ({name})"
    decoded = _decode_table_bytes(original)
    if decoded is None:
        return "input_defect", "table file is not valid UTF-8"
    bom, text = decoded
    return _SyncTarget(
        table_path=table_path,
        table_file=table_path.relative_to(model_dir).as_posix(),
        original=original,
        bom=bom,
        lines=text.splitlines(keepends=True),
        newline="\r\n" if "\r\n" in text else "\n",
    )


def _input_defect_reason(repo_root: Path, model_dir: Path) -> str | None:
    if not repo_root.is_dir():
        return "repository root does not exist"
    if not model_dir.is_dir() or not model_dir.name.endswith(".SemanticModel"):
        return "model must be an existing .SemanticModel directory"
    return None


def _write_synced(
    target: _SyncTarget,
    edits: list[_Edit],
    actions: list[dict[str, str]],
    excluded: list[str],
    table: str,
) -> dict[str, Any]:
    """Apply the planned edits atomically and prove the partitions untouched."""
    expected = _partition_texts(target.lines)
    new_lines = _apply(target.lines, edits, target.newline)
    data = target.bom + "".join(new_lines).encode("utf-8")
    error = _atomic_replace(target.table_path, data)
    if error is not None:
        return _result(
            "refused",
            table=table,
            table_file=target.table_file,
            excluded=excluded,
            blockers=[f"The table file could not be published safely ({error})."],
        )
    drift = _postwrite_partition_check(target.table_path, target.original, expected)
    if drift is not None:
        return _result(
            "refused",
            table=table,
            table_file=target.table_file,
            excluded=excluded,
            blockers=[drift],
        )
    return _result(
        "synced",
        table=table,
        table_file=target.table_file,
        actions=actions,
        excluded=excluded,
    )


def sync_measures(
    repo: Path | str,
    model: Path | str,
    table: str,
    *,
    metrics_dir: str = "mappings",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Upsert approved contract measures into one adopted model table.

    Returns the normalized result document (see :func:`_result`); the CLI
    renders it and maps it to an exit code via :func:`measure_sync_exit_code`.
    """
    repo_root = Path(repo)
    model_dir = Path(model)
    defect = _input_defect_reason(repo_root, model_dir)
    if defect is not None:
        return _result("input_defect", table=table, blockers=[defect])
    gate = _manifest_gate(model_dir)
    if gate is not None:
        return _result("refused", table=table, blockers=[gate])
    contracts, excluded = _approved_for_table(repo_root, metrics_dir, table)
    if not contracts:
        return _result(
            "refused", table=table, excluded=excluded, blockers=[_NO_APPROVED]
        )
    rendered, render_errors = _render_contracts(contracts)
    if render_errors:
        return _result(
            "refused", table=table, excluded=excluded, blockers=render_errors
        )
    target = _load_target(model_dir, table)
    if isinstance(target, tuple):
        outcome, reason = target
        return _result(outcome, table=table, excluded=excluded, blockers=[reason])
    measures, anchor, duplicate = _scan_measures(target.lines)
    if duplicate is not None:
        return _result(
            "refused",
            table=table,
            table_file=target.table_file,
            excluded=excluded,
            blockers=[duplicate],
        )
    actions, edits = _plan(target.lines, target.newline, rendered, measures, anchor)
    if _touches_partition(edits, _partition_regions(target.lines)):
        return _result(
            "refused",
            table=table,
            table_file=target.table_file,
            excluded=excluded,
            blockers=[_PARTITION_TOUCH],
        )
    if dry_run:
        return _result(
            "planned",
            table=table,
            table_file=target.table_file,
            actions=actions,
            excluded=excluded,
            dry_run=True,
        )
    if not edits:
        return _result(
            "synced",
            table=table,
            table_file=target.table_file,
            actions=actions,
            excluded=excluded,
        )
    return _write_synced(target, edits, actions, excluded, table)


__all__ = [
    "measure_sync_exit_code",
    "render_measure_sync_text",
    "sync_measures",
]
