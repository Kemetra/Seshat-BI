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
from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class _RunReport:
    """Everything a result document needs besides the outcome itself.

    Accumulated along the run (``dataclasses.replace``) so refusal sites emit
    a fully-cited document without re-threading loose arguments.
    """

    table: str
    table_file: str | None = None
    actions: tuple[dict[str, str], ...] = ()
    excluded: tuple[str, ...] = ()
    dry_run: bool = False

    def doc(self, outcome: str, blockers: Iterable[str] = ()) -> dict[str, Any]:
        counts = {"insert": 0, "update": 0, "skip": 0}
        for action in self.actions:
            counts[action["action"]] += 1
        return {
            "schema_version": SCHEMA_VERSION,
            "outcome": outcome,
            "table": self.table,
            "table_file": self.table_file,
            "dry_run": self.dry_run,
            "actions": list(self.actions),
            "counts": counts,
            "excluded": list(self.excluded),
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


def _is_doc_line(lines: list[str], idx: int, ind: int) -> bool:
    if idx < 0:
        return False
    if _indent(lines[idx]) != ind:
        return False
    return lines[idx].strip().startswith("///")


def _doc_start(lines: list[str], header: int) -> int:
    """First line of the contiguous ``///`` doc comment above ``header``."""
    ind = _indent(lines[header])
    start = header
    while _is_doc_line(lines, start - 1, ind):
        start -= 1
    return start


def _lineage_tag(lines: list[str], start: int, end: int) -> str | None:
    for line in lines[start:end]:
        match = _LINEAGE_TAG.match(line.rstrip("\r\n"))
        if match:
            return match.group("value")
    return None


def _measure_header_at(lines: list[str], i: int) -> re.Match[str] | None:
    if _indent(lines[i]) != 1:
        return None
    return _is_measure_header(lines[i].strip())


def _is_anchor_line(line: str) -> bool:
    if _indent(line) != 1:
        return False
    stripped = line.strip()
    return bool(_is_column_header(stripped) or _is_source_header(stripped))


def _register_measure(
    lines: list[str], i: int, name: str, measures: dict[str, _MeasureBlock]
) -> tuple[int, str | None]:
    """Record the measure block headed at ``i``; (next line, duplicate error)."""
    end = _block_end(lines, i, len(lines))
    if name in measures:
        return end, _DUPLICATE_MEASURE
    trimmed = _trim_trailing_blanks(lines, i, end)
    measures[name] = _MeasureBlock(
        name=name,
        start=_doc_start(lines, i),
        end=trimmed,
        lineage_tag=_lineage_tag(lines, i, trimmed),
    )
    return end, None


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
        header = _measure_header_at(lines, i)
        if header:
            name = header.group("name").strip()
            i, duplicate = _register_measure(lines, i, name, measures)
            if duplicate is not None:
                return measures, n, duplicate
            continue
        if anchor is None and _is_anchor_line(lines[i]):
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


@dataclass(frozen=True)
class _TableScan:
    """The structure `_scan_measures` proved about the target table file."""

    measures: dict[str, _MeasureBlock]
    anchor: int


def _measure_change(
    target: _SyncTarget, existing: _MeasureBlock | None, block: str
) -> tuple[str, tuple[str, ...]]:
    """(action, desired logical lines) for ONE rendered measure."""
    desired = tuple(_desired_lines(block, existing.lineage_tag if existing else None))
    if existing is None:
        return "insert", desired
    current = "".join(target.lines[existing.start : existing.end])
    wanted = "".join(line + target.newline for line in desired)
    return ("skip" if current == wanted else "update"), desired


def _insertion_edit(target: _SyncTarget, anchor: int, inserted: list[str]) -> _Edit:
    if anchor > 0 and target.lines[anchor - 1].strip():
        inserted = ["", *inserted]
    return _Edit(anchor, anchor, tuple(inserted))


def _plan(
    target: _SyncTarget, scan: _TableScan, rendered: dict[str, str]
) -> tuple[list[dict[str, str]], list[_Edit]]:
    """Per-measure action plan plus the concrete line edits (all-or-nothing)."""
    actions: list[dict[str, str]] = []
    edits: list[_Edit] = []
    inserted: list[str] = []
    for name in sorted(rendered):
        existing = scan.measures.get(name)
        action, desired = _measure_change(target, existing, rendered[name])
        actions.append({"measure": name, "action": action})
        if action == "insert":
            inserted.extend([*desired, ""])
        elif action == "update":
            assert existing is not None
            edits.append(_Edit(existing.start, existing.end, desired))
    if inserted:
        edits.append(_insertion_edit(target, scan.anchor, inserted))
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
    target: _SyncTarget, edits: list[_Edit], report: _RunReport
) -> dict[str, Any]:
    """Apply the planned edits atomically and prove the partitions untouched."""
    expected = _partition_texts(target.lines)
    new_lines = _apply(target.lines, edits, target.newline)
    data = target.bom + "".join(new_lines).encode("utf-8")
    error = _atomic_replace(target.table_path, data)
    refusal = replace(report, actions=())
    if error is not None:
        blocker = f"The table file could not be published safely ({error})."
        return refusal.doc("refused", [blocker])
    drift = _postwrite_partition_check(target.table_path, target.original, expected)
    if drift is not None:
        return refusal.doc("refused", [drift])
    return report.doc("synced")


@dataclass(frozen=True)
class MeasureSyncRequest:
    """One measure-sync invocation (the CLI's argument bundle)."""

    repo: Path | str
    model: Path | str
    table: str
    metrics_dir: str = "mappings"
    dry_run: bool = False


def _approved_rendered(
    request: MeasureSyncRequest, report: _RunReport
) -> tuple[dict[str, str], _RunReport, dict[str, Any] | None]:
    """Render every approved contract; (rendered, report, failure document)."""
    contracts, excluded = _approved_for_table(
        Path(request.repo), request.metrics_dir, request.table
    )
    report = replace(report, excluded=tuple(excluded))
    if not contracts:
        return {}, report, report.doc("refused", [_NO_APPROVED])
    rendered, render_errors = _render_contracts(contracts)
    if render_errors:
        return {}, report, report.doc("refused", render_errors)
    return rendered, report, None


def _planned_edits(
    target: _SyncTarget, rendered: dict[str, str], report: _RunReport
) -> tuple[list[dict[str, str]], list[_Edit], dict[str, Any] | None]:
    """Plan the safe edit set; (actions, edits, failure document)."""
    measures, anchor, duplicate = _scan_measures(target.lines)
    if duplicate is not None:
        return [], [], report.doc("refused", [duplicate])
    actions, edits = _plan(target, _TableScan(measures, anchor), rendered)
    if _touches_partition(edits, _partition_regions(target.lines)):
        return [], [], report.doc("refused", [_PARTITION_TOUCH])
    return actions, edits, None


def sync_measures(request: MeasureSyncRequest) -> dict[str, Any]:
    """Upsert approved contract measures into one adopted model table.

    Returns the normalized result document (see :class:`_RunReport`); the CLI
    renders it and maps it to an exit code via :func:`measure_sync_exit_code`.
    """
    report = _RunReport(table=request.table)
    defect = _input_defect_reason(Path(request.repo), Path(request.model))
    if defect is not None:
        return report.doc("input_defect", [defect])
    gate = _manifest_gate(Path(request.model))
    if gate is not None:
        return report.doc("refused", [gate])
    rendered, report, failure = _approved_rendered(request, report)
    if failure is not None:
        return failure
    target = _load_target(Path(request.model), request.table)
    if isinstance(target, tuple):
        outcome, reason = target
        return report.doc(outcome, [reason])
    report = replace(report, table_file=target.table_file)
    actions, edits, failure = _planned_edits(target, rendered, report)
    if failure is not None:
        return failure
    report = replace(report, actions=tuple(actions), dry_run=request.dry_run)
    if request.dry_run:
        return report.doc("planned")
    if not edits:
        return report.doc("synced")
    return _write_synced(target, edits, report)


__all__ = [
    "MeasureSyncRequest",
    "measure_sync_exit_code",
    "render_measure_sync_text",
    "sync_measures",
]
