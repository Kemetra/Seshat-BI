"""PBIR-vs-approved-design validator (US8, spec 123). EXTENDS the shipped Visual
Implementation Review (``.claude/skills/powerbi-dashboard-design/workflows/
visual-implementation-review.md`` + ``templates/visual-implementation-trace.md``)
-- it is NOT a second reviewer (FR-031). Where the shipped review traces a built
page against the approved visual->contract binding map, this module additionally
compares committed PBIR against the approved PAGE BLUEPRINT (page/visual/type/
geometry/theme/nav intent), reporting expected-vs-actual per FR-030's dimension
list and flagging unapproved additions + missing elements.

WHY THIS IS THE ONE READ-ONLY CLI VERB (D12, R1/R2 precedent)
----------------------------------------------------------------
The delivery default for new capabilities in this feature is a SKILL, not a new
``retail`` CLI verb (ratified Option-B, ``docs/roadmap/decisions/
cli-verbs-vs-skill-driven.md``; research.md cross-cutting principle). This
module is the deliberate, narrow exception, for exactly the reason ``retail
check``'s R1 (relative model reference) and R2 (report-json authoring-lint) are
CLI, not skill-only: a CHECK SURFACE that POLICES what writers already produced
belongs on the same read-only, scriptable, CI-callable surface as those rules --
distinct from an AUTHORING skill that exercises human judgment. `retail
pbir-validate-blueprint` is that check surface for compiler- or human-produced
PBIR against the approved blueprint, exactly as `retail check` is the check
surface for the four PBIR authoring adapters. It reuses R1 (``rules/pbir.py``)
directly for the relative-model-reference dimension rather than re-deriving it.

READ-ONLY, GRANTS NO APPROVAL (FR-031, FR-036)
----------------------------------------------------------------
This module opens NOTHING for write. It never creates a trace file, never
mutates the Decision Store, never sets a readiness stage to `pass`. Its return
value, ``BlueprintValidationResult``, carries no field or method that could ever
grant approval (no ``.approve()``, no ``.grant_approval()``) -- the highest
status it can report is `pass` on CONFORMITY, which is evidence, not an approval
record. The four-status vocabulary (`not_started` / `blocked` / `warning` /
`pass`) is reused verbatim from the shipped trace, never a numeric score
(FR-035).

WHAT IT COMPARES (FR-030)
----------------------------------------------------------------
Expected (from the approved page blueprint + binding map) vs actual (the
committed PBIR tree): per-page visual inventory (unapproved additions / missing
elements, matched by visual id), visual type conformance (binding map's declared
type vs the committed ``visualType``), contract-binding IDENTITY (a visual id
resolves to exactly one approved contract, never an orphan), and relative model
references (reused directly from R1, ``rules/pbir.py``, rather than re-derived).

THIS INCREMENT DELIBERATELY DOES NOT YET COMPARE (named here so the scope is
honest, not silently narrower than it looks): the binding map's mapped
``semantic_model_field(s)`` column against the visual's actual bound
Entity/Property (contract-binding is checked at visual-id/contract-name
identity, not at the field level yet); titles / formats / geometry / theme /
background / navigation / statically-inspectable interactions, which the page
blueprint and binding-map templates do not carry per-visual position/format/
theme intent for -- that lives in ``visual-spec.yaml``, ``theme-json-spec.md``,
and ``background-spec.yaml``, each a future extension point, not a second
reviewer. Rather than fabricate a comparison with no approved expectation to
check against, this validator never invents one; a future increment wires those
sources into the SAME comparison, extending this module, not forking it
(FR-031).

No pbi-cli, no live Power BI, no network -- stdlib json/pathlib/re only, plus
the shipped R1 rule function and the shipped binding-map table parser
(``dashboard_coordinator._binding_visuals`` -- reused, not reimplemented, per
FR-031's "extend, don't fork").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from .core import Finding, RuleContext
from .dashboard_coordinator import _binding_visuals
from .rules.pbir import check_pbir_relative_reference

_STATUS_ORDER = ("pass", "warning", "not_started", "blocked")


class Deviation(NamedTuple):
    """One expected-vs-actual mismatch: a dimension where committed PBIR
    diverges from the approved design. Cites evidence; grants nothing."""

    dimension: str  # e.g. "visual_type", "geometry", "relative_model_ref"
    locator: str  # where in the PBIR tree (repo-relative-ish path/pointer)
    message: str  # human-readable expected-vs-actual statement


class BlueprintValidationResult(NamedTuple):
    """The validator's verdict. Read-only evidence, never an approval grant --
    ``grants_approval`` is ALWAYS False; there is no method on this shape that
    could ever flip it (FR-031)."""

    status: str  # one of _STATUS_ORDER; the WORST finding rolls up
    deviations: tuple[Deviation, ...]
    unapproved_additions: tuple[Deviation, ...]
    missing_elements: tuple[Deviation, ...]
    evidence: tuple[str, ...]
    grants_approval: bool = False


def _load_yaml_mapping(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _unreadable_source_blockers(
    blueprint: dict[str, Any] | None,
    blueprint_path: Path,
    binding_text: str | None,
    binding_map_path: Path,
) -> list[Deviation]:
    """A ``blocked`` deviation for each REQUIRED expected-source that is missing,
    unreadable, or malformed (FR-030/FR-034). ``None`` from ``_load_yaml_mapping``
    (absent file / non-mapping YAML) or ``_read_text`` (absent/undecodable file)
    is fail-closed here rather than coerced to empty -- a validator with no
    approved design to compare against must BLOCK, not silently pass."""
    blockers: list[Deviation] = []
    if blueprint is None:
        blockers.append(
            Deviation(
                dimension="unreadable_source",
                locator=str(blueprint_path),
                message=(
                    f"approved page blueprint at {blueprint_path} is missing, "
                    f"unreadable, or not a YAML mapping -- validation blocked "
                    f"(fail closed); supply the approved blueprint before "
                    f"validating committed PBIR against it"
                ),
            )
        )
    if binding_text is None:
        blockers.append(
            Deviation(
                dimension="unreadable_source",
                locator=str(binding_map_path),
                message=(
                    f"approved visual-contract binding map at {binding_map_path} "
                    f"is missing or unreadable -- validation blocked (fail closed); "
                    f"supply the approved binding map before validating committed "
                    f"PBIR against it"
                ),
            )
        )
    return blockers


def _blueprint_visual_ids(blueprint: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """``{visual_id: entry}`` for every visual the approved blueprint declares."""
    visuals = blueprint.get("visuals")
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(visuals, list):
        return out
    for entry in visuals:
        if isinstance(entry, dict) and isinstance(entry.get("visual_id"), str):
            out[entry["visual_id"]] = entry
    return out


# --------------------------------------------------------------------------- #
# PBIR tree readers (read-only; never write)
# --------------------------------------------------------------------------- #
def _iter_committed_visuals(report_dir: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    """``{visual_id_from_dirname: (path, parsed_json)}`` for every
    ``visuals/<id>/visual.json`` under the report's pages. The directory name is
    read as the visual's binding-map id (the convention the compiler and a
    Desktop build both follow: one folder per visual, named for its id)."""
    out: dict[str, tuple[Path, dict[str, Any]]] = {}
    pages_dir = report_dir / "definition" / "pages"
    if not pages_dir.is_dir():
        return out
    for visual_json in sorted(pages_dir.glob("*/visuals/*/visual.json")):
        visual_id = visual_json.parent.name
        try:
            doc = json.loads(visual_json.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict):
            out[visual_id] = (visual_json, doc)
    return out


def _rel_locator(report_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(report_dir.parent))
    except ValueError:
        return str(path)


def _visual_type(doc: dict[str, Any]) -> str | None:
    visual = doc.get("visual")
    if isinstance(visual, dict):
        vtype = visual.get("visualType")
        if isinstance(vtype, str):
            return vtype
    return None


# --------------------------------------------------------------------------- #
# R1 reuse: relative model reference (FR-030 "relative model references")
# --------------------------------------------------------------------------- #
def _relative_ref_deviations(report_dir: Path) -> list[Deviation]:
    """Reuse R1 (``rules/pbir.py``) directly rather than re-deriving the
    relative-model-reference check. Builds a minimal ``RuleContext`` over the
    report tree's OWN ``definition.pbir`` file(s) -- no git, no live repo scan."""
    pbir_files = sorted(report_dir.glob("*.pbir")) + sorted(
        report_dir.glob("definition.pbir")
    )
    if not pbir_files:
        return []
    tracked = tuple(
        str(p.relative_to(report_dir.parent)).replace("\\", "/") for p in pbir_files
    )
    ctx = RuleContext(repo_root=report_dir.parent, tracked_files=tracked)
    findings: list[Finding] = list(check_pbir_relative_reference(ctx))
    return [
        Deviation(
            dimension="relative_model_ref",
            locator=f.locator,
            message=f.message,
        )
        for f in findings
    ]


# --------------------------------------------------------------------------- #
# The comparison (expected from blueprint+binding-map, actual from PBIR)
# --------------------------------------------------------------------------- #
def _unapproved_additions(
    committed: dict[str, tuple[Path, dict[str, Any]]],
    approved_ids: set[str],
    report_dir: Path,
) -> list[Deviation]:
    """A committed visual with NO approved binding-map entry and NO blueprint
    entry -- a manually-added or rogue visual (T046a)."""
    return [
        Deviation(
            dimension="unapproved_visual",
            locator=f"{_rel_locator(report_dir, path)}#visual_id={visual_id}",
            message=(
                f"visual {visual_id!r} is committed in PBIR but has no "
                f"entry on the approved binding map or page blueprint -- "
                f"an unapproved addition"
            ),
        )
        for visual_id, (path, _doc) in committed.items()
        if visual_id not in approved_ids
    ]


def _missing_deviation(visual_id: str, binding: "_BindingRow") -> Deviation:
    return Deviation(
        dimension="missing_visual",
        locator=f"binding-map#visual_id={visual_id}",
        message=(
            f"visual {visual_id!r} (contract {binding.bound_contract!r}) "
            f"is on the approved binding map but not built in the "
            f"committed PBIR"
        ),
    )


def _type_deviation(
    visual_id: str,
    binding: "_BindingRow",
    path: Path,
    doc: dict[str, Any],
    report_dir: Path,
) -> Deviation | None:
    """A `visual_type` mismatch between the approved binding map and committed
    PBIR, or ``None`` when both types are present and agree (or either is absent)."""
    expected_type = binding.visual_type
    actual_type = _visual_type(doc)
    if not (expected_type and actual_type and expected_type != actual_type):
        return None
    return Deviation(
        dimension="visual_type",
        locator=f"{_rel_locator(report_dir, path)}#visual_id={visual_id}",
        message=(
            f"visual {visual_id!r} expected type {expected_type!r} "
            f"(approved binding map) but PBIR has {actual_type!r}"
        ),
    )


def _compare_visuals(
    blueprint_visuals: dict[str, dict[str, Any]],
    bindings: dict[str, "_BindingRow"],
    committed: dict[str, tuple[Path, dict[str, Any]]],
    report_dir: Path,
) -> tuple[list[Deviation], list[Deviation], list[Deviation]]:
    """Returns (deviations, unapproved_additions, missing_elements)."""
    approved_ids = set(bindings) | set(blueprint_visuals)
    unapproved = _unapproved_additions(committed, approved_ids, report_dir)

    deviations: list[Deviation] = []
    missing: list[Deviation] = []
    for visual_id, binding in bindings.items():
        if visual_id not in committed:
            missing.append(_missing_deviation(visual_id, binding))
            continue
        # Visual type conformance: blueprint declares the section only; the
        # binding map's `visual_type` column is the type-of-record when present.
        path, doc = committed[visual_id]
        dev = _type_deviation(visual_id, binding, path, doc, report_dir)
        if dev is not None:
            deviations.append(dev)

    return deviations, unapproved, missing


class _BindingRow(NamedTuple):
    visual_id: str
    visual_type: str | None
    bound_contract: str


_SEPARATOR_CELL_CHARS = {"-", ":", " "}


def _split_md_row(line: str) -> list[str] | None:
    """Split a markdown table row into trimmed cells, or ``None`` if not a row."""
    if "|" not in line:
        return None
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _header_type_indices(cells: list[str]) -> tuple[int, int] | None:
    """The (visual_id, visual_type) column indices in a header row, or ``None``
    when either column is absent."""
    lowered = [h.lower() for h in cells]
    id_idx = next(
        (j for j, h in enumerate(lowered) if "visual" in h and "id" in h), None
    )
    type_idx = next(
        (j for j, h in enumerate(lowered) if "visual" in h and "type" in h), None
    )
    if id_idx is None or type_idx is None:
        return None
    return id_idx, type_idx


def _row_visual_type(
    cells: list[str], id_idx: int, type_idx: int
) -> tuple[str, str] | None:
    """The (visual_id, visual_type) pair for one data row, or ``None`` for a
    header-echo / out-of-range row that carries no binding."""
    if id_idx >= len(cells) or type_idx >= len(cells):
        return None
    vid = cells[id_idx].strip("`").strip()
    if not vid or vid.lower() in ("visual_id", "visual id"):
        return None
    return vid, cells[type_idx].strip("`").strip()


def _collect_visual_types(
    rows: list[str], id_idx: int, type_idx: int
) -> dict[str, str]:
    """Read ``{visual_id: visual_type}`` from the data rows below a header,
    stopping at the first non-table line."""
    out: dict[str, str] = {}
    for row_line in rows:
        cells = _split_md_row(row_line)
        if cells is None:
            break
        if all(set(c) <= _SEPARATOR_CELL_CHARS for c in cells):
            continue
        pair = _row_visual_type(cells, id_idx, type_idx)
        if pair is not None:
            out[pair[0]] = pair[1]
    return out


def _binding_visual_types(text: str) -> dict[str, str]:
    """A second, narrow parse of the SAME binding-map table (reusing
    ``_binding_visuals`` for identity/contract, this local helper for the
    ``visual_type`` column FR-030 additionally needs) -- table selection logic
    is NOT duplicated; only the extra column is read here."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "visual_id" not in line.lower() or "|" not in line:
            continue
        indices = _header_type_indices(_split_md_row(line) or [])
        if indices is None:
            return {}
        return _collect_visual_types(lines[i + 1 :], *indices)
    return {}


def _build_bindings(binding_text: str) -> dict[str, "_BindingRow"]:
    """Reuse the shipped table parser for identity/contract (never reimplemented);
    attach the binding-map's own `visual_type` column (FR-030 needs it, the shared
    parser does not carry it) via a narrow second pass over the SAME table."""
    visual_types = _binding_visual_types(binding_text)
    return {
        b.visual_id: _BindingRow(
            visual_id=b.visual_id,
            visual_type=visual_types.get(b.visual_id),
            bound_contract=b.bound_contract,
        )
        for b in _binding_visuals(binding_text)
    }


def _rollup_status(
    deviations: list[Deviation],
    unapproved: list[Deviation],
    missing: list[Deviation],
    blueprint_visuals: dict[str, dict[str, Any]],
    bindings: dict[str, "_BindingRow"],
) -> str:
    """Worst-first roll-up: any unapproved/missing/deviation blocks; an empty
    expected design is `not_started`; a clean conformity is `pass`."""
    if unapproved or missing or deviations:
        return "blocked"
    if not blueprint_visuals and not bindings:
        return "not_started"
    return "pass"


def validate_blueprint(
    *,
    report_dir: Path,
    blueprint_path: Path,
    binding_map_path: Path,
) -> BlueprintValidationResult:
    """Compare committed PBIR under ``report_dir`` against the approved page
    blueprint (``blueprint_path``) and the approved visual-contract binding map
    (``binding_map_path``). READ-ONLY: opens nothing for write, never mutates
    the Decision Store, never sets a readiness stage. Returns evidence +
    deviations only -- ``grants_approval`` is always False (FR-031).
    """
    report_dir = Path(report_dir)
    blueprint_path = Path(blueprint_path)
    binding_map_path = Path(binding_map_path)

    evidence: list[str] = [
        f"blueprint: {blueprint_path}",
        f"binding map: {binding_map_path}",
        f"PBIR report dir: {report_dir}",
    ]

    # Fail CLOSED on an unreadable REQUIRED expected-source (FR-030/FR-034). A
    # check surface pointed at a missing/unreadable blueprint or binding map must
    # BLOCK naming the source -- never let empty inputs roll up to `pass`/exit 0
    # (that would report success for a report validated against nothing).
    blueprint = _load_yaml_mapping(blueprint_path)
    binding_text = _read_text(binding_map_path)
    unreadable = _unreadable_source_blockers(
        blueprint, blueprint_path, binding_text, binding_map_path
    )
    if unreadable:
        return BlueprintValidationResult(
            status="blocked",
            deviations=tuple(unreadable),
            unapproved_additions=(),
            missing_elements=(),
            evidence=tuple(evidence),
            grants_approval=False,
        )

    bindings = _build_bindings(binding_text)
    blueprint_visuals = _blueprint_visual_ids(blueprint)
    committed = _iter_committed_visuals(report_dir)

    deviations, unapproved, missing = _compare_visuals(
        blueprint_visuals, bindings, committed, report_dir
    )
    deviations.extend(_relative_ref_deviations(report_dir))

    status = _rollup_status(
        deviations, unapproved, missing, blueprint_visuals, bindings
    )

    return BlueprintValidationResult(
        status=status,
        deviations=tuple(deviations),
        unapproved_additions=tuple(unapproved),
        missing_elements=tuple(missing),
        evidence=tuple(evidence),
        grants_approval=False,
    )


def pbir_validate_blueprint_main(args: object) -> int:
    """CLI entry: ``retail pbir-validate-blueprint``. Read-only: prints the
    expected-vs-actual report to stdout and exits non-zero on ANY deviation,
    unapproved addition, or missing element -- it never writes a file and never
    grants ``dashboard_ready: pass`` (FR-031)."""
    result = validate_blueprint(
        report_dir=Path(args.report),  # type: ignore[attr-defined]
        blueprint_path=Path(args.blueprint),  # type: ignore[attr-defined]
        binding_map_path=Path(args.binding_map),  # type: ignore[attr-defined]
    )
    print(f"status: {result.status}")
    for d in result.deviations:
        print(f"[deviation] {d.dimension}: {d.message} ({d.locator})")
    for d in result.unapproved_additions:
        print(f"[unapproved] {d.dimension}: {d.message} ({d.locator})")
    for d in result.missing_elements:
        print(f"[missing] {d.dimension}: {d.message} ({d.locator})")
    print(
        "note: this is a read-only validation report; it grants no approval and "
        "never sets dashboard_ready: pass (FR-031)."
    )
    if result.status == "blocked":
        return 1
    return 0
