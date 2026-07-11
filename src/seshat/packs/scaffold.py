"""Category-aware declarative pack scaffolding (spec 120, US5, FR-028).

Writes one new pack directory -- manifest, a category-specific starter
artifact, and a synthetic fixture -- that validates cleanly out of the box.
Fail-closed: the target directory must be new, stay within the workspace,
and nothing outside it is touched. Scaffolding never activates anything.
"""

from __future__ import annotations

from pathlib import Path

from ..artifact_identity import canonical_relative_path, resolve_within
from .model import CATEGORIES, PackError, PackSpec

_STARTERS: dict[str, tuple[str, str]] = {
    "kpi": (
        "artifacts/kpi-template.yaml",
        """\
# Declarative KPI template. A named data owner must approve the business
# definition before any metric contract is created from it (Principle V).
kpi: example-kpi
question: "What is the measured business outcome for the period?"
grain_note: "State the fact grain this KPI aggregates over."
required_decisions:
  - "Named owner confirms the business definition."
  - "Named owner confirms the denominator and filters."
""",
    ),
    "source_vocabulary": (
        "artifacts/vocabulary.yaml",
        """\
# Source vocabulary: raw column spellings -> suggested snake_case names.
# Suggestions only; the mapping gate still decides per table.
terms:
  - raw: "Example Raw Header"
    suggested: example_raw_header
    note: "Replace with the source system's real spelling."
""",
    ),
    "warehouse_compatibility": (
        "artifacts/dialect-notes.md",
        """\
# Warehouse compatibility notes

Document dialect renderings for the silver/gold SQL conventions here.
Notes advise authors; they never change the medallion contract.
""",
    ),
    "regional_policy": (
        "artifacts/policy-notes.md",
        """\
# Regional policy notes

Document region-specific handling (currency display, fiscal calendar,
privacy disposition defaults) as guidance for named-human decisions.
""",
    ),
    "accessibility": (
        "artifacts/accessibility-guidance.md",
        """\
# Accessibility guidance

Document contrast, keyboard, and legibility guidance for report design.
Guidance informs design review; it grants no readiness pass.
""",
    ),
    "dashboard_blueprint": (
        "artifacts/blueprint.yaml",
        """\
# Dashboard blueprint: a layout suggestion bound to metric-contract slots.
# Every visual slot must bind to an APPROVED contract at design time.
pages:
  - title: "Example page"
    visual_slots:
      - purpose: "Headline KPI"
        binds: "an approved metric contract (filled at design time)"
""",
    ),
}

_FIXTURE = """\
example_key,example_value
synthetic-1,10
synthetic-2,20
"""


def _validate_pack_id(pack_id: str) -> str:
    """Namespace discipline shared with validate; returns the short name."""
    from .validator import _LOCAL_ID_RE

    segments = pack_id.split(".")
    if len(segments) < 2 or not all(
        _LOCAL_ID_RE.fullmatch(segment) for segment in segments
    ):
        raise PackError(
            "pack id must be an owner-qualified lowercase namespace "
            "such as 'acme.retail-kpis'"
        )
    return segments[-1]


def _validate_spec(spec: PackSpec) -> str:
    """Fail-closed input validation; returns the pack's short local name."""
    if spec.category not in CATEGORIES:
        raise PackError(
            f"unknown category {spec.category!r}; "
            f"expected one of {', '.join(CATEGORIES)}"
        )
    if not spec.owner.strip():
        raise PackError("pack owner must be a non-empty name")
    return _validate_pack_id(spec.pack_id)


def _resolve_new_directory(
    root: Path, name: str, target_dir: Path | str | None
) -> Path:
    directory = Path(target_dir) if target_dir else Path("packs/local") / name
    try:
        resolved_dir = resolve_within(root, directory)
    except ValueError as exc:
        raise PackError("pack target directory escapes the workspace") from exc
    if resolved_dir.exists():
        raise PackError(
            f"pack target directory already exists: "
            f"{canonical_relative_path(root, resolved_dir)}"
        )
    return resolved_dir


def _manifest_body(spec: PackSpec, relative_dir: str) -> str:
    starter_path, _ = _STARTERS[spec.category]
    return f"""\
schema_version: "1.0"
pack_id: {spec.pack_id}
version: 0.1.0
category: {spec.category}
owner: "{spec.owner}"
description: "Describe what this pack contributes and for whom."
core_compatibility: "1.x"
provides:
  - {spec.pack_id.split(".")[-1]}
requires: []
conflicts: []
artifacts:
  - path: {starter_path}
    purpose: "Category starter content; replace with real declarative content."
human_decisions:
  - "A named human owner approves every business meaning this pack suggests."
fixtures:
  - fixtures/synthetic-example.csv
verification:
  - "retail pack validate --repo . --pack {relative_dir}/seshat-pack.yaml"
non_goals:
  - "Does not execute code, change stage order, or grant any approval."
  - "Does not claim to fit every client schema."
"""


def scaffold_pack(
    repo_root: Path | str,
    spec: PackSpec,
    *,
    target_dir: Path | str | None = None,
) -> list[str]:
    """Write the pack skeleton and return the repo-relative paths written."""
    root = Path(repo_root).resolve()
    name = _validate_spec(spec)
    resolved_dir = _resolve_new_directory(root, name, target_dir)
    relative_dir = canonical_relative_path(root, resolved_dir)
    starter_path, starter_body = _STARTERS[spec.category]
    files = {
        resolved_dir / "seshat-pack.yaml": _manifest_body(spec, relative_dir),
        resolved_dir / starter_path: starter_body,
        resolved_dir / "fixtures/synthetic-example.csv": _FIXTURE,
    }
    written: list[str] = []
    for path, body in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")
        written.append(canonical_relative_path(root, path))
    return written
