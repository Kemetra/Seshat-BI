"""Read-only structural discovery of a PBIP project.

The discovery pass walks a contained project root and produces two parallel
streams -- ``components`` (what structure exists) and ``facts`` (what that
structure means for adoption).  A small :class:`_Discovery` context carries the
shared state so each helper stays narrow and single-purpose.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..tmdl import parse_relationships, parse_tmdl
from ._facts import _component, _Fact
from ._safety import (
    MANIFEST_PATH,
    _FileRecord,
    _fingerprint,
    _is_within,
    _read_text,
    _relative,
    _safe_name,
)


@dataclass
class _Discovery:
    root: Path
    by_artifact: dict[str, _FileRecord]
    components: list[dict[str, Any]] = field(default_factory=list)
    facts: list[_Fact] = field(default_factory=list)


@dataclass(frozen=True)
class _ScopeAmbiguity:
    kind: str
    observed_id_prefix: str
    observed_subject: str
    observed_detail: str
    blocked_id: str
    blocked_subject: str
    blocked_detail: str


_MODEL_AMBIGUITY = _ScopeAmbiguity(
    kind="semantic_model",
    observed_id_prefix="observed:ambiguous-semantic-model",
    observed_subject="semantic model",
    observed_detail=(
        "Semantic-model structure was observed, but its project scope is ambiguous."
    ),
    blocked_id="blocked:multiple-semantic-models",
    blocked_subject="semantic model scope",
    blocked_detail=(
        "Multiple semantic models were found; project scope requires analyst selection."
    ),
)
_REPORT_AMBIGUITY = _ScopeAmbiguity(
    kind="report",
    observed_id_prefix="observed:ambiguous-report",
    observed_subject="report",
    observed_detail=(
        "Report structure was observed, but its project scope is ambiguous."
    ),
    blocked_id="blocked:multiple-reports",
    blocked_subject="report scope",
    blocked_detail=(
        "Multiple reports were found; project scope requires analyst selection."
    ),
)


def _fingerprint_inputs(
    root: Path, files: list[Path]
) -> tuple[list[_FileRecord], dict[str, _FileRecord]]:
    records = [
        _fingerprint(root, path)
        for path in files
        if _relative(root, path) != MANIFEST_PATH
    ]
    return records, {record.artifact: record for record in records}


def _sorted_dirs(root: Path, pattern: str) -> list[Path]:
    return sorted(
        (path for path in root.glob(pattern) if path.is_dir()),
        key=lambda path: path.name.lower(),
    )


def _discover_pbip(
    root: Path, files: list[Path]
) -> tuple[list[dict[str, Any]], list[_Fact], list[_FileRecord]]:
    records, by_artifact = _fingerprint_inputs(root, files)
    ctx = _Discovery(root=root, by_artifact=by_artifact)
    pbip_paths = sorted(root.glob("*.pbip"), key=lambda path: path.name.lower())
    _register_projects(ctx, pbip_paths)
    fallback = by_artifact[_relative(root, pbip_paths[0])] if pbip_paths else None
    model_dirs = _sorted_dirs(root, "*.SemanticModel")
    report_dirs = _sorted_dirs(root, "*.Report")
    _register_models(ctx, model_dirs, fallback)
    _register_reports(ctx, report_dirs, fallback)
    _discover_tmdl_components(ctx, model_dirs)
    _discover_pbir_components(ctx, report_dirs)
    if len(model_dirs) > 1:
        _mark_ambiguous(ctx, _MODEL_AMBIGUITY)
    if len(report_dirs) > 1:
        _mark_ambiguous(ctx, _REPORT_AMBIGUITY)
    return ctx.components, ctx.facts, records


def _register_projects(ctx: _Discovery, pbip_paths: list[Path]) -> None:
    if not pbip_paths:
        ctx.facts.append(
            _Fact(
                id="missing:pbip-project",
                classification="missing",
                category="coverage",
                subject="PBIP project descriptor",
                detail="No .pbip project descriptor was found at the selected root.",
                required_authority="analyst",
            )
        )
        return
    for pbip_path in pbip_paths:
        _register_one_project(ctx, pbip_path)


def _register_one_project(ctx: _Discovery, pbip_path: Path) -> None:
    artifact = _relative(ctx.root, pbip_path)
    record = ctx.by_artifact[artifact]
    ctx.components.append(_component("project", pbip_path.stem, record))
    raw = _read_text(pbip_path)
    if raw is None:
        ctx.components[-1]["support"] = "unreadable"
        return
    try:
        descriptor = json.loads(raw)
    except json.JSONDecodeError:
        ctx.components[-1]["support"] = "unsupported"
        ctx.facts.append(
            _Fact(
                id=f"unavailable:pbip-schema:{artifact}",
                classification="unavailable_with_reason",
                category="coverage",
                subject="PBIP descriptor schema",
                detail="PBIP descriptor is not supported JSON.",
                artifact=artifact,
                reason="The descriptor could not be parsed as JSON.",
            )
        )
        return
    if not isinstance(descriptor, dict):
        ctx.components[-1]["support"] = "unsupported"


def _register_models(
    ctx: _Discovery, model_dirs: list[Path], fallback: _FileRecord | None
) -> None:
    for model_dir in model_dirs:
        model_file = model_dir / "definition" / "model.tmdl"
        artifact_path = model_file if model_file.is_file() else model_dir
        artifact = _relative(ctx.root, artifact_path)
        record = ctx.by_artifact.get(artifact, _FileRecord(artifact, None, False))
        component = _component("semantic_model", model_dir.stem, record)
        if not model_file.is_file():
            component["support"] = "missing"
        ctx.components.append(component)
    if not model_dirs and fallback is not None:
        ctx.components.append(
            _component("semantic_model", "missing semantic model", fallback, "missing")
        )


def _register_reports(
    ctx: _Discovery, report_dirs: list[Path], fallback: _FileRecord | None
) -> None:
    for report_dir in report_dirs:
        pbir_path = report_dir / "definition.pbir"
        artifact_path = pbir_path if pbir_path.is_file() else report_dir
        artifact = _relative(ctx.root, artifact_path)
        record = ctx.by_artifact.get(artifact, _FileRecord(artifact, None, False))
        component = _component("report", report_dir.stem, record)
        if not pbir_path.is_file():
            component["support"] = "missing"
        ctx.components.append(component)
    if not report_dirs and fallback is not None:
        ctx.components.append(
            _component("report", "missing report", fallback, "missing")
        )


def _mark_ambiguous(ctx: _Discovery, spec: _ScopeAmbiguity) -> None:
    for component in ctx.components:
        if component["kind"] != spec.kind:
            continue
        component["support"] = "ambiguous"
        ctx.facts.append(
            _Fact(
                id=f"{spec.observed_id_prefix}:{component['artifact']}",
                classification="observed",
                category="coverage",
                subject=f"{spec.observed_subject} {component['identity']}",
                detail=spec.observed_detail,
                artifact=component["artifact"],
            )
        )
    ctx.facts.append(
        _Fact(
            id=spec.blocked_id,
            classification="blocked",
            category="readiness",
            subject=spec.blocked_subject,
            detail=spec.blocked_detail,
            required_authority="analyst",
        )
    )


def _discover_tmdl_components(ctx: _Discovery, model_dirs: list[Path]) -> None:
    for model_dir in model_dirs:
        definition = model_dir / "definition"
        if not definition.is_dir():
            continue
        for tmdl_path in sorted(
            definition.rglob("*.tmdl"), key=lambda path: path.as_posix()
        ):
            _discover_one_tmdl(ctx, tmdl_path)


def _parse_tmdl_safe(text: str) -> tuple[Any, list[Any]] | None:
    try:
        return parse_tmdl(text), parse_relationships(text)
    except (ValueError, IndexError):
        return None


def _discover_one_tmdl(ctx: _Discovery, tmdl_path: Path) -> None:
    artifact = _relative(ctx.root, tmdl_path)
    record = ctx.by_artifact.get(artifact, _FileRecord(artifact, None, False))
    text = _read_text(tmdl_path)
    if text is None:
        ctx.components.append(_component("table", tmdl_path.stem, record, "unreadable"))
        return
    parsed = _parse_tmdl_safe(text)
    if parsed is None:
        ctx.components.append(
            _component("table", tmdl_path.stem, record, "unsupported")
        )
        ctx.facts.append(
            _Fact(
                id=f"unavailable:tmdl:{artifact}",
                classification="unavailable_with_reason",
                category="coverage",
                subject="TMDL parser boundary",
                detail="This TMDL file could not be read by the shipped parser.",
                artifact=artifact,
                reason="Unsupported or malformed TMDL structure.",
            )
        )
        return
    table, relationships = parsed
    if table is not None:
        _emit_table(ctx, table, artifact, record)
    _emit_relationships(ctx, relationships, artifact, record)
    if tmdl_path.name.lower() == "expressions.tmdl":
        _emit_parameters(ctx, text, record)


def _emit_table(
    ctx: _Discovery, table: Any, artifact: str, record: _FileRecord
) -> None:
    ctx.components.append(_component("table", table.name, record))
    for measure in table.measures:
        ctx.components.append(_component("measure", measure.name, record))
        measure_id = _safe_name(measure.name, fallback="measure")
        ctx.facts.append(
            _Fact(
                id=f"proposed:measure-meaning:{artifact}:{measure_id}",
                classification="proposed",
                category="proposal",
                subject=f"meaning for measure {measure.name}",
                detail="The measure structure is observed; its business "
                "definition requires metric-owner review.",
                artifact=artifact,
                required_authority="metric_owner",
            )
        )


def _emit_relationships(
    ctx: _Discovery, relationships: Iterable[Any], artifact: str, record: _FileRecord
) -> None:
    for relationship in relationships:
        ctx.components.append(_component("relationship", relationship.name, record))
        relationship_id = _safe_name(relationship.name, fallback="relationship")
        ctx.facts.append(
            _Fact(
                id=f"proposed:relationship-meaning:{artifact}:{relationship_id}",
                classification="proposed",
                category="proposal",
                subject=f"meaning for relationship {relationship.name}",
                detail="Relationship structure is observed; cardinality and "
                "business meaning require analyst review.",
                artifact=artifact,
                required_authority="analyst",
            )
        )


def _emit_parameters(ctx: _Discovery, text: str, record: _FileRecord) -> None:
    for match in re.finditer(r"(?mi)^expression\s+['\"]?([^=\n'\"]+)", text):
        ctx.components.append(_component("parameter", match.group(1), record))


def _discover_pbir_components(ctx: _Discovery, report_dirs: list[Path]) -> None:
    for report_dir in report_dirs:
        _discover_pbir_reference(ctx, report_dir)
        _discover_pbir_pages(ctx, report_dir)


def _discover_pbir_reference(ctx: _Discovery, report_dir: Path) -> None:
    pbir_path = report_dir / "definition.pbir"
    if not pbir_path.is_file():
        return
    artifact = _relative(ctx.root, pbir_path)
    text = _read_text(pbir_path)
    if text is None:
        ctx.facts.append(
            _Fact(
                id=f"unavailable:pbir:{artifact}",
                classification="unavailable_with_reason",
                category="coverage",
                subject="PBIR reader",
                detail="PBIR file is unreadable.",
                artifact=artifact,
                reason="The file could not be read.",
            )
        )
        return
    ctx.facts.append(_pbir_reference_fact(ctx.root, pbir_path, artifact, text))


def _discover_pbir_pages(ctx: _Discovery, report_dir: Path) -> None:
    pages_root = report_dir / "definition" / "pages"
    if not pages_root.is_dir():
        return
    for page_path in sorted(
        pages_root.glob("*/page.json"), key=lambda path: path.as_posix()
    ):
        artifact = _relative(ctx.root, page_path)
        record = ctx.by_artifact.get(artifact, _fingerprint(ctx.root, page_path))
        ctx.components.append(_component("page", page_path.parent.name, record))
    for visual_path in sorted(
        pages_root.glob("*/visuals/*/visual.json"), key=lambda path: path.as_posix()
    ):
        artifact = _relative(ctx.root, visual_path)
        record = ctx.by_artifact.get(artifact, _fingerprint(ctx.root, visual_path))
        ctx.components.append(_component("visual", visual_path.parent.name, record))


def _pbir_document(text: str) -> tuple[Any, bool]:
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        return None, False


def _pbir_reference_fact(
    root: Path, pbir_path: Path, artifact: str, text: str
) -> _Fact:
    document, decoded = _pbir_document(text)
    if not decoded:
        return _Fact(
            id=f"unavailable:pbir-schema:{artifact}",
            classification="unavailable_with_reason",
            category="coverage",
            subject="PBIR schema",
            detail="PBIR file is not supported JSON.",
            artifact=artifact,
            reason="The file could not be parsed as JSON.",
        )
    if not isinstance(document, dict):
        return _Fact(
            id=f"unavailable:pbir-shape:{artifact}",
            classification="unavailable_with_reason",
            category="coverage",
            subject="PBIR schema",
            detail="PBIR root is not an object.",
            artifact=artifact,
            reason="The PBIR document shape is unsupported.",
        )
    reference = document.get("datasetReference")
    if not isinstance(reference, dict):
        return _Fact(
            id=f"missing:pbir-reference:{artifact}",
            classification="missing",
            category="coverage",
            subject="PBIR semantic-model reference",
            detail="No PBIR semantic-model reference was found.",
            artifact=artifact,
            required_authority="analyst",
        )
    if "byConnection" in reference:
        return _Fact(
            id=f"blocked:R1:{artifact}",
            classification="blocked",
            category="governance",
            subject="PBIR model reference",
            detail="PBIR uses a connection-bound model reference rather than a "
            "relative project path.",
            artifact=artifact,
            rule_id="R1",
            required_authority="analyst",
        )
    return _pbir_locator_fact(root, pbir_path, artifact, reference)


def _pbir_locator_fact(
    root: Path, pbir_path: Path, artifact: str, reference: dict[str, Any]
) -> _Fact:
    by_path = reference.get("byPath")
    locator = by_path.get("path") if isinstance(by_path, dict) else None
    if not isinstance(locator, str) or not locator.strip():
        return _Fact(
            id=f"missing:pbir-model:{artifact}",
            classification="missing",
            category="coverage",
            subject="PBIR semantic-model reference",
            detail="PBIR does not declare a usable relative semantic-model reference.",
            artifact=artifact,
            required_authority="analyst",
        )
    target = (pbir_path.parent / locator).resolve(strict=False)
    if not _is_within(root, target):
        return _Fact(
            id=f"blocked:pbir-reference-escape:{artifact}",
            classification="blocked",
            category="coverage",
            subject="PBIR semantic-model reference",
            detail="PBIR model reference resolves outside the selected project root.",
            artifact=artifact,
            rule_id="R1",
            required_authority="analyst",
        )
    if not target.exists():
        return _Fact(
            id=f"missing:pbir-model-target:{artifact}",
            classification="missing",
            category="coverage",
            subject="PBIR semantic-model reference",
            detail="PBIR references a semantic model that is not present in this "
            "project.",
            artifact=artifact,
            required_authority="analyst",
        )
    return _Fact(
        id=f"observed:pbir-model-reference:{artifact}",
        classification="observed",
        category="evidence",
        subject="PBIR semantic-model reference",
        detail="PBIR declares a contained relative semantic-model reference.",
        artifact=artifact,
    )
