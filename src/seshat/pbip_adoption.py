"""Read-only, governed assessment and opt-in baseline scaffolding for PBIP.

This module deliberately owns no readiness state and grants no approval.  It
collects safe, project-relative structural facts, composes the existing rule and
readiness seams, and exposes one small write operation whose exact assessment
digest must be accepted by a human first.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .disclosure import scan_disclosure
from .tmdl import parse_relationships, parse_tmdl

SCHEMA_VERSION = "1.0"
MANIFEST_PATH = ".seshat/adoption/pbip-adoption.yaml"
_STAGE_ORDER = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)
_CREDENTIAL_LITERAL = re.compile(
    r"(?i)\b(?:password|passwd|pwd|token|api[_ -]?key|accountkey)\s*[=:]"
)
_CONNECTION_LITERAL = re.compile(
    r"(?i)\b(?:server|host|data[ _]?source|initial[ _]?catalog)\s*=\s*['\"]"
)
_NON_GOLD_SOURCE = re.compile(
    r"(?i)(?:schema\s*=\s*['\"](?!gold['\"]|gold\b)|\b(?:bronze|silver)\.)"
)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9 ._()\-]")


class PbipAdoptionError(ValueError):
    """A supported, concise assessment/scaffold input defect."""


@dataclass(frozen=True)
class _FileRecord:
    artifact: str
    sha256: str | None
    readable: bool


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_assessment_digest(assessment: dict[str, Any]) -> str:
    """Return the digest of substantive assessment content, excluding itself."""
    content = {
        key: value for key, value in assessment.items() if key != "assessment_digest"
    }
    return hashlib.sha256(_canonical_json(content).encode("utf-8")).hexdigest()


def _safe_name(value: object, *, fallback: str) -> str:
    text = str(value).strip() if value is not None else ""
    text = _SAFE_NAME.sub("_", text)
    return text[:160] or fallback


def _safe_detail(value: object, *, fallback: str) -> str:
    """Keep operational prose useful without carrying source literals forward."""
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = _CREDENTIAL_LITERAL.sub("credential=<redacted>", text)
    text = _CONNECTION_LITERAL.sub("connection=<redacted>", text)
    text = re.sub(
        r"(?i)(?:postgres(?:ql)?|mysql|mssql|sqlserver|snowflake)://\S+",
        "<redacted-connection>",
        text,
    )
    text = re.sub(r"[A-Za-z]:[\\/][^ ]+", "<redacted-path>", text)
    return text[:360] or fallback


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root)
    except ValueError:
        return False
    return True


def _relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise PbipAdoptionError(
            "a discovered path is outside the selected project"
        ) from exc


def _target_path(project: Path | str) -> tuple[Path, bool]:
    supplied = Path(project).expanduser()
    if not supplied.exists():
        raise PbipAdoptionError("project path does not exist")
    if supplied.is_file() and supplied.suffix.lower() == ".pbix":
        return supplied.resolve(), True
    if not supplied.is_dir():
        raise PbipAdoptionError("project must be a PBIP directory or a .pbix file")
    root = supplied.resolve()
    if not root.is_dir():
        raise PbipAdoptionError("project directory could not be resolved safely")
    return root, False


def _safe_files(root: Path) -> list[Path]:
    """Return ordinary files after proving each encountered link stays in root."""
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative_parts = path.relative_to(root).parts
        if ".git" in relative_parts:
            continue
        if path.is_symlink() and not _is_within(root, path):
            raise PbipAdoptionError(
                "project contains a linked path outside the selected root"
            )
        if path.is_file():
            if not _is_within(root, path):
                raise PbipAdoptionError(
                    "project contains a file outside the selected root"
                )
            files.append(path)
    return files


def _fingerprint(root: Path, path: Path) -> _FileRecord:
    artifact = _relative(root, path)
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return _FileRecord(artifact=artifact, sha256=None, readable=False)
    return _FileRecord(artifact=artifact, sha256=digest, readable=True)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None


def _git_state(root: Path) -> str:
    revision = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if revision.returncode != 0 or revision.stdout.strip() != "true":
        return "absent"
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if status.returncode != 0:
        return "absent"
    entries = [line for line in status.stdout.splitlines() if line]
    if any(entry.startswith("??") for entry in entries):
        return "untracked"
    return "dirty" if entries else "clean"


def _component(
    kind: str,
    identity: str,
    record: _FileRecord,
    support: str = "supported",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "identity": _safe_name(identity, fallback=kind),
        "artifact": record.artifact,
        "sha256": record.sha256,
        "support": support if record.readable else "unreadable",
    }


def _fact(
    fact_id: str,
    classification: str,
    category: str,
    subject: str,
    detail: str,
    *,
    artifact: str | None = None,
    reason: str | None = None,
    rule_id: str | None = None,
    required_authority: str | None = None,
) -> dict[str, Any]:
    return {
        "id": fact_id,
        "classification": classification,
        "category": category,
        "subject": _safe_name(subject, fallback="PBIP adoption fact"),
        "detail": _safe_detail(detail, fallback="No safe detail is available."),
        "artifact": artifact,
        "reason": _safe_detail(reason, fallback="No reason is available.")
        if reason
        else None,
        "rule_id": rule_id,
        "required_authority": required_authority,
    }


def _component_fact(component: dict[str, Any]) -> dict[str, Any]:
    support = component["support"]
    if support == "supported":
        return _fact(
            f"observed:{component['kind']}:{component['artifact']}",
            "observed",
            "coverage",
            f"{component['kind']} {component['identity']}",
            "Supported PBIP structure was observed.",
            artifact=component["artifact"],
        )
    classification = (
        "unavailable_with_reason"
        if support in {"unreadable", "unsupported"}
        else "missing"
    )
    return _fact(
        f"coverage:{support}:{component['kind']}:{component['artifact']}",
        classification,
        "coverage",
        f"{component['kind']} {component['identity']}",
        "PBIP structure is outside the supported assessment coverage.",
        artifact=component["artifact"],
        reason=f"Component support is {support}.",
    )


def _add_missing_governance_facts(root: Path, facts: list[dict[str, Any]]) -> None:
    checks = (
        (
            "source-profile",
            "mappings/*/source-profile.md",
            "No committed Source Ready profile was found.",
        ),
        (
            "source-map",
            "mappings/*/source-map.yaml",
            "No approved source mapping was found.",
        ),
        (
            "metric-contract",
            "mappings/*/metrics/*.yaml",
            "No metric contract was found.",
        ),
        (
            "approval-record",
            "mappings/*/readiness-status.yaml",
            "No committed readiness or approval record was found.",
        ),
    )
    for name, pattern, detail in checks:
        if not list(root.glob(pattern)):
            facts.append(
                _fact(
                    f"missing:{name}",
                    "missing",
                    "readiness",
                    name.replace("-", " "),
                    detail,
                    reason=detail,
                    required_authority="data_owner"
                    if name == "source-profile"
                    else "analyst",
                )
            )


def _scan_literal_boundaries(
    root: Path, records: Iterable[_FileRecord], facts: list[dict[str, Any]]
) -> None:
    for record in records:
        suffix = Path(record.artifact).suffix.lower()
        if suffix not in {".tmdl", ".pbir", ".json", ".m"}:
            continue
        text = _read_text(root / Path(record.artifact))
        if text is None:
            continue
        if _CREDENTIAL_LITERAL.search(text):
            facts.append(
                _fact(
                    f"blocked:C2:{record.artifact}",
                    "blocked",
                    "governance",
                    "credential-like literal",
                    "Credential-like source content was detected and redacted "
                    "from this assessment.",
                    artifact=record.artifact,
                    rule_id="C2",
                    required_authority="governance",
                )
            )
        elif _CONNECTION_LITERAL.search(text):
            facts.append(
                _fact(
                    f"blocked:C1:{record.artifact}",
                    "blocked",
                    "governance",
                    "literal connection detail",
                    "A literal connection detail was detected and redacted "
                    "from this assessment.",
                    artifact=record.artifact,
                    rule_id="C1",
                    required_authority="governance",
                )
            )
        if _NON_GOLD_SOURCE.search(text):
            facts.append(
                _fact(
                    f"blocked:D8:{record.artifact}",
                    "blocked",
                    "governance",
                    "non-gold semantic-model source",
                    "A semantic-model source outside the gold schema was detected.",
                    artifact=record.artifact,
                    rule_id="D8",
                    required_authority="governance",
                )
            )


def _discover_pbip(
    root: Path, files: list[Path]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[_FileRecord]]:
    components: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    records = [
        _fingerprint(root, path)
        for path in files
        if _relative(root, path) != MANIFEST_PATH
    ]
    by_artifact = {record.artifact: record for record in records}

    pbip_paths = sorted(root.glob("*.pbip"), key=lambda path: path.name.lower())
    if not pbip_paths:
        facts.append(
            _fact(
                "missing:pbip-project",
                "missing",
                "coverage",
                "PBIP project descriptor",
                "No .pbip project descriptor was found at the selected root.",
                required_authority="analyst",
            )
        )
    for pbip_path in pbip_paths:
        artifact = _relative(root, pbip_path)
        record = by_artifact[artifact]
        components.append(_component("project", pbip_path.stem, record))
        raw = _read_text(pbip_path)
        if raw is None:
            components[-1]["support"] = "unreadable"
            continue
        try:
            descriptor = json.loads(raw)
        except json.JSONDecodeError:
            components[-1]["support"] = "unsupported"
            facts.append(
                _fact(
                    f"unavailable:pbip-schema:{artifact}",
                    "unavailable_with_reason",
                    "coverage",
                    "PBIP descriptor schema",
                    "PBIP descriptor is not supported JSON.",
                    artifact=artifact,
                    reason="The descriptor could not be parsed as JSON.",
                )
            )
        else:
            if not isinstance(descriptor, dict):
                components[-1]["support"] = "unsupported"

    model_dirs = sorted(
        (path for path in root.glob("*.SemanticModel") if path.is_dir()),
        key=lambda path: path.name.lower(),
    )
    report_dirs = sorted(
        (path for path in root.glob("*.Report") if path.is_dir()),
        key=lambda path: path.name.lower(),
    )
    for model_dir in model_dirs:
        model_file = model_dir / "definition" / "model.tmdl"
        artifact_path = model_file if model_file.is_file() else model_dir
        artifact = _relative(root, artifact_path)
        record = by_artifact.get(artifact, _FileRecord(artifact, None, False))
        component = _component("semantic_model", model_dir.stem, record)
        if not model_file.is_file():
            component["support"] = "missing"
        components.append(component)

    if not model_dirs and pbip_paths:
        descriptor = by_artifact[_relative(root, pbip_paths[0])]
        components.append(
            _component(
                "semantic_model", "missing semantic model", descriptor, "missing"
            )
        )

    for report_dir in report_dirs:
        pbir_path = report_dir / "definition.pbir"
        artifact_path = pbir_path if pbir_path.is_file() else report_dir
        artifact = _relative(root, artifact_path)
        record = by_artifact.get(artifact, _FileRecord(artifact, None, False))
        component = _component("report", report_dir.stem, record)
        if not pbir_path.is_file():
            component["support"] = "missing"
        components.append(component)

    if not report_dirs and pbip_paths:
        descriptor = by_artifact[_relative(root, pbip_paths[0])]
        components.append(_component("report", "missing report", descriptor, "missing"))

    _discover_tmdl_components(root, model_dirs, by_artifact, components, facts)
    _discover_pbir_components(root, report_dirs, by_artifact, components, facts)
    if len(model_dirs) > 1:
        for component in components:
            if component["kind"] == "semantic_model":
                component["support"] = "ambiguous"
                facts.append(
                    _fact(
                        f"observed:ambiguous-semantic-model:{component['artifact']}",
                        "observed",
                        "coverage",
                        f"semantic model {component['identity']}",
                        "Semantic-model structure was observed, but its project "
                        "scope is ambiguous.",
                        artifact=component["artifact"],
                    )
                )
        facts.append(
            _fact(
                "blocked:multiple-semantic-models",
                "blocked",
                "readiness",
                "semantic model scope",
                "Multiple semantic models were found; project scope requires "
                "analyst selection.",
                required_authority="analyst",
            )
        )
    if len(report_dirs) > 1:
        for component in components:
            if component["kind"] == "report":
                component["support"] = "ambiguous"
                facts.append(
                    _fact(
                        f"observed:ambiguous-report:{component['artifact']}",
                        "observed",
                        "coverage",
                        f"report {component['identity']}",
                        "Report structure was observed, but its project scope is "
                        "ambiguous.",
                        artifact=component["artifact"],
                    )
                )
        facts.append(
            _fact(
                "blocked:multiple-reports",
                "blocked",
                "readiness",
                "report scope",
                "Multiple reports were found; project scope requires analyst "
                "selection.",
                required_authority="analyst",
            )
        )
    return components, facts, records


def _discover_tmdl_components(
    root: Path,
    model_dirs: list[Path],
    by_artifact: dict[str, _FileRecord],
    components: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> None:
    for model_dir in model_dirs:
        definition = model_dir / "definition"
        if not definition.is_dir():
            continue
        for tmdl_path in sorted(
            definition.rglob("*.tmdl"), key=lambda path: path.as_posix()
        ):
            artifact = _relative(root, tmdl_path)
            record = by_artifact.get(artifact, _FileRecord(artifact, None, False))
            text = _read_text(tmdl_path)
            if text is None:
                components.append(
                    _component("table", tmdl_path.stem, record, "unreadable")
                )
                continue
            try:
                table = parse_tmdl(text)
                relationships = parse_relationships(text)
            except (ValueError, IndexError):
                components.append(
                    _component("table", tmdl_path.stem, record, "unsupported")
                )
                facts.append(
                    _fact(
                        f"unavailable:tmdl:{artifact}",
                        "unavailable_with_reason",
                        "coverage",
                        "TMDL parser boundary",
                        "This TMDL file could not be read by the shipped parser.",
                        artifact=artifact,
                        reason="Unsupported or malformed TMDL structure.",
                    )
                )
                continue
            if table is not None:
                components.append(_component("table", table.name, record))
                for measure in table.measures:
                    components.append(_component("measure", measure.name, record))
                    measure_id = _safe_name(measure.name, fallback="measure")
                    facts.append(
                        _fact(
                            f"proposed:measure-meaning:{artifact}:{measure_id}",
                            "proposed",
                            "proposal",
                            f"meaning for measure {measure.name}",
                            "The measure structure is observed; its business "
                            "definition requires metric-owner review.",
                            artifact=artifact,
                            required_authority="metric_owner",
                        )
                    )
            for relationship in relationships:
                components.append(_component("relationship", relationship.name, record))
                relationship_id = _safe_name(relationship.name, fallback="relationship")
                facts.append(
                    _fact(
                        f"proposed:relationship-meaning:{artifact}:{relationship_id}",
                        "proposed",
                        "proposal",
                        f"meaning for relationship {relationship.name}",
                        "Relationship structure is observed; cardinality and "
                        "business meaning require analyst review.",
                        artifact=artifact,
                        required_authority="analyst",
                    )
                )
            if tmdl_path.name.lower() == "expressions.tmdl":
                for match in re.finditer(
                    r"(?mi)^expression\s+['\"]?([^=\n'\"]+)", text
                ):
                    components.append(_component("parameter", match.group(1), record))


def _discover_pbir_components(
    root: Path,
    report_dirs: list[Path],
    by_artifact: dict[str, _FileRecord],
    components: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> None:
    for report_dir in report_dirs:
        pbir_path = report_dir / "definition.pbir"
        if pbir_path.is_file():
            artifact = _relative(root, pbir_path)
            text = _read_text(pbir_path)
            if text is None:
                facts.append(
                    _fact(
                        f"unavailable:pbir:{artifact}",
                        "unavailable_with_reason",
                        "coverage",
                        "PBIR reader",
                        "PBIR file is unreadable.",
                        artifact=artifact,
                        reason="The file could not be read.",
                    )
                )
            else:
                _inspect_pbir_reference(root, pbir_path, artifact, text, facts)
        pages_root = report_dir / "definition" / "pages"
        if not pages_root.is_dir():
            continue
        for page_path in sorted(
            pages_root.glob("*/page.json"), key=lambda path: path.as_posix()
        ):
            artifact = _relative(root, page_path)
            record = by_artifact.get(artifact, _fingerprint(root, page_path))
            components.append(_component("page", page_path.parent.name, record))
        for visual_path in sorted(
            pages_root.glob("*/visuals/*/visual.json"), key=lambda path: path.as_posix()
        ):
            artifact = _relative(root, visual_path)
            record = by_artifact.get(artifact, _fingerprint(root, visual_path))
            components.append(_component("visual", visual_path.parent.name, record))


def _inspect_pbir_reference(
    root: Path, pbir_path: Path, artifact: str, text: str, facts: list[dict[str, Any]]
) -> None:
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        facts.append(
            _fact(
                f"unavailable:pbir-schema:{artifact}",
                "unavailable_with_reason",
                "coverage",
                "PBIR schema",
                "PBIR file is not supported JSON.",
                artifact=artifact,
                reason="The file could not be parsed as JSON.",
            )
        )
        return
    if not isinstance(document, dict):
        facts.append(
            _fact(
                f"unavailable:pbir-shape:{artifact}",
                "unavailable_with_reason",
                "coverage",
                "PBIR schema",
                "PBIR root is not an object.",
                artifact=artifact,
                reason="The PBIR document shape is unsupported.",
            )
        )
        return
    reference = document.get("datasetReference")
    if not isinstance(reference, dict):
        facts.append(
            _fact(
                f"missing:pbir-reference:{artifact}",
                "missing",
                "coverage",
                "PBIR semantic-model reference",
                "No PBIR semantic-model reference was found.",
                artifact=artifact,
                required_authority="analyst",
            )
        )
        return
    if "byConnection" in reference:
        facts.append(
            _fact(
                f"blocked:R1:{artifact}",
                "blocked",
                "governance",
                "PBIR model reference",
                "PBIR uses a connection-bound model reference rather than a "
                "relative project path.",
                artifact=artifact,
                rule_id="R1",
                required_authority="analyst",
            )
        )
        return
    by_path = reference.get("byPath")
    locator = by_path.get("path") if isinstance(by_path, dict) else None
    if not isinstance(locator, str) or not locator.strip():
        facts.append(
            _fact(
                f"missing:pbir-model:{artifact}",
                "missing",
                "coverage",
                "PBIR semantic-model reference",
                "PBIR does not declare a usable relative semantic-model reference.",
                artifact=artifact,
                required_authority="analyst",
            )
        )
        return
    target = (pbir_path.parent / locator).resolve(strict=False)
    if not _is_within(root, target):
        facts.append(
            _fact(
                f"blocked:pbir-reference-escape:{artifact}",
                "blocked",
                "coverage",
                "PBIR semantic-model reference",
                "PBIR model reference resolves outside the selected project root.",
                artifact=artifact,
                rule_id="R1",
                required_authority="analyst",
            )
        )
    elif not target.exists():
        facts.append(
            _fact(
                f"missing:pbir-model-target:{artifact}",
                "missing",
                "coverage",
                "PBIR semantic-model reference",
                "PBIR references a semantic model that is not present in this project.",
                artifact=artifact,
                required_authority="analyst",
            )
        )
    else:
        facts.append(
            _fact(
                f"observed:pbir-model-reference:{artifact}",
                "observed",
                "evidence",
                "PBIR semantic-model reference",
                "PBIR declares a contained relative semantic-model reference.",
                artifact=artifact,
            )
        )


def _governance_findings(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compose the shipped rule runner, degrading honestly when it is unavailable."""
    try:
        import seshat.rules  # noqa: F401

        from .kit_lint import is_bootstrapped
        from .registry import all_rules
        from .runner import build_context, collect_findings

        context = build_context(root)
        findings = collect_findings(
            all_rules(), context, bootstrapped=is_bootstrapped(root)
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return [], [
            _fact(
                "unavailable:governance-runner",
                "unavailable_with_reason",
                "governance",
                "existing governance findings",
                "Existing static governance findings could not be evaluated.",
                reason=_safe_detail(type(exc).__name__, fallback="runner unavailable"),
            )
        ]

    normalized: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    for finding in findings:
        locator = str(finding.locator).replace("\\", "/")
        if locator.startswith("../") or Path(locator).is_absolute():
            continue
        severity = finding.severity.value.upper()
        classification = "blocked" if severity == "ERROR" else "observed"
        normalized.append(
            {
                "rule_id": finding.rule_id,
                "severity": severity,
                "message": _safe_detail(
                    finding.message, fallback="Existing rule finding."
                ),
                "locator": locator or ".",
                "classification": classification,
            }
        )
        if severity == "ERROR":
            facts.append(
                _fact(
                    f"blocked:rule:{finding.rule_id}:{locator}",
                    "blocked",
                    "governance",
                    f"governance rule {finding.rule_id}",
                    "An existing governance rule reported a blocking finding.",
                    artifact=locator or None,
                    rule_id=finding.rule_id,
                    required_authority="governance",
                )
            )
    normalized.sort(
        key=lambda item: (item["rule_id"], item["locator"], item["message"])
    )
    return normalized, facts


def _readiness(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from .blocker_explainer import build_blocker_explanations
        from .readiness_projection import build_readiness_projection
        from .run_next import build_run_next_response

        projection = build_readiness_projection(root)
        tables = projection.get("tables", [])
        readiness: list[dict[str, Any]] = []
        for table in tables if isinstance(tables, list) else []:
            if not isinstance(table, dict):
                continue
            table_id = table.get("table_id")
            source_path = table.get("source_path")
            if not isinstance(table_id, str) or not isinstance(source_path, str):
                continue
            table_dir = source_path.rsplit("/", 2)[-2]
            readiness.append(
                {
                    "projection": table,
                    "run_next": build_run_next_response(root, table_dir),
                }
            )
        readiness.sort(key=lambda item: str(item["projection"].get("source_path")))
        blockers = build_blocker_explanations(root).get("items", [])
        return readiness, blockers if isinstance(blockers, list) else []
    except (OSError, ValueError, KeyError):
        return [], []


def _default_next_step() -> dict[str, Any]:
    return {
        "kind": "action",
        "stage": "source_ready",
        "action": "No readiness file found; start onboarding at Source Ready.",
        "blocking_reasons": [],
        "required_authority": "data_owner",
    }


def _next_step(
    target_kind: str,
    version_control: str,
    facts: list[dict[str, Any]],
    readiness: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    if target_kind == "pbix_unsupported":
        return {
            "kind": "terminal_stop",
            "stage": None,
            "action": (
                "Open the PBIX in Power BI Desktop, save it as a Power BI Project "
                "(PBIP), then assess the saved project directory."
            ),
            "blocking_reasons": [
                "PBIX binaries are not parsed or modified by PBIP adoption."
            ],
            "required_authority": "analyst",
        }
    if version_control == "absent":
        return {
            "kind": "action",
            "stage": "source_ready",
            "action": (
                "Initialize version control yourself, review the project files, "
                "and reassess before creating an adoption baseline."
            ),
            "blocking_reasons": [
                "The selected project is not in a Git worktree, so committed "
                "evidence cannot be evaluated."
            ],
            "required_authority": "analyst",
        }
    if version_control in {"dirty", "untracked"}:
        return {
            "kind": "action",
            "stage": "source_ready",
            "action": (
                "Review and commit or intentionally discard the changed project "
                "inputs, then reassess."
            ),
            "blocking_reasons": ["Project inputs are not clean committed evidence."],
            "required_authority": "analyst",
        }
    ambiguity = [
        fact
        for fact in facts
        if fact["id"]
        in {"blocked:multiple-semantic-models", "blocked:multiple-reports"}
    ]
    if ambiguity:
        return {
            "kind": "action",
            "stage": "source_ready",
            "action": (
                "Resolve the intended PBIP model and report scope with an analyst, "
                "then reassess."
            ),
            "blocking_reasons": [fact["detail"] for fact in ambiguity],
            "required_authority": "analyst",
        }
    unsafe = [fact for fact in facts if fact["classification"] == "blocked"]
    if unsafe:
        first = unsafe[0]
        return {
            "kind": "action",
            "stage": "source_ready",
            "action": (
                "Resolve the earliest recorded governance or containment blocker, "
                "then reassess."
            ),
            "blocking_reasons": [first["detail"]],
            "required_authority": first["required_authority"] or "governance",
        }
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for item in readiness:
        response = item.get("run_next")
        if not isinstance(response, dict):
            continue
        stage = response.get("stage")
        index = (
            _STAGE_ORDER.index(stage) if stage in _STAGE_ORDER else len(_STAGE_ORDER)
        )
        candidates.append((index, str(item["projection"].get("table_id")), response))
    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]))
        earliest = candidates[0]
        tied = [candidate for candidate in candidates if candidate[0] == earliest[0]]
        if len(tied) > 1:
            return {
                "kind": "action",
                "stage": _STAGE_ORDER[earliest[0]],
                "action": (
                    "Resolve which equally urgent readiness table is in scope "
                    "before proceeding."
                ),
                "blocking_reasons": [
                    "Multiple readiness tables share the earliest unresolved stage."
                ],
                "required_authority": "analyst",
            }
        response = earliest[2]
        outcome = response.get("outcome")
        return {
            "kind": "terminal_stop" if outcome == "terminal_pass" else "action",
            "stage": response.get("stage"),
            "action": _safe_detail(
                response.get("action_text")
                or "Review the existing readiness response before proceeding.",
                fallback="Review the existing readiness response before proceeding.",
            ),
            "blocking_reasons": [
                str(reason)
                for reason in response.get("blocking_reasons", [])
                if isinstance(reason, str)
            ],
            "required_authority": response.get("required_authority")
            if isinstance(response.get("required_authority"), str)
            else None,
        }
    if blockers:
        first = blockers[0]
        return {
            "kind": "action",
            "stage": "source_ready",
            "action": "Resolve the earliest recorded readiness blocker, then reassess.",
            "blocking_reasons": [
                _safe_detail(
                    first.get("reason"), fallback="A readiness blocker remains."
                )
            ],
            "required_authority": first.get("required_authority")
            if isinstance(first.get("required_authority"), str)
            else "data_owner",
        }
    return _default_next_step()


def _manifest_baseline(root: Path) -> dict[str, str] | None:
    path = root / Path(MANIFEST_PATH)
    if not path.is_file():
        return None
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    raw = data.get("authoritative_inputs") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return None
    result: dict[str, str] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        artifact, digest = entry.get("artifact"), entry.get("sha256")
        if (
            isinstance(artifact, str)
            and isinstance(digest, str)
            and re.fullmatch(r"[a-f0-9]{64}", digest)
        ):
            result[artifact] = digest
    return result


def _changes(root: Path, records: list[_FileRecord]) -> list[dict[str, Any]]:
    baseline = _manifest_baseline(root)
    if baseline is None:
        return []
    current = {
        record.artifact: record.sha256
        for record in records
        if record.sha256 is not None
    }
    changes: list[dict[str, Any]] = []
    for artifact in sorted(set(baseline) | set(current)):
        before, after = baseline.get(artifact), current.get(artifact)
        if before is None:
            kind = "added"
        elif after is None:
            kind = "removed"
        elif before == after:
            kind = "unchanged"
        else:
            kind = "changed"
        changes.append(
            {
                "kind": kind,
                "artifact": artifact,
                "previous_sha256": before,
                "current_sha256": after,
                "classification": "observed" if kind == "unchanged" else "blocked",
            }
        )
    return changes


def _coverage(components: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        name: 0
        for name in ("supported", "unsupported", "unreadable", "missing", "ambiguous")
    }
    for component in components:
        support = component.get("support")
        if support in counts:
            counts[support] += 1
    status = (
        "complete"
        if counts["supported"]
        and not any(
            counts[name]
            for name in ("unsupported", "unreadable", "missing", "ambiguous")
        )
        else "partial"
    )
    if not counts["supported"]:
        status = "blocked"
    return {"status": status, **counts}


def _finalize(assessment: dict[str, Any]) -> dict[str, Any]:
    assessment["facts"].sort(key=lambda item: item["id"])
    assessment["governance_findings"].sort(
        key=lambda item: (item["rule_id"], item["locator"], item["message"])
    )
    assessment["target"]["components"].sort(
        key=lambda item: (item["kind"], item["artifact"], item["identity"])
    )
    assessment["changes"].sort(key=lambda item: item["artifact"])
    disclosure = scan_disclosure(
        {
            key: value
            for key, value in assessment.items()
            if key not in {"disclosure", "assessment_digest"}
        }
    )
    assessment["disclosure"] = {
        "status": disclosure["status"],
        "findings": disclosure["findings"],
    }
    if disclosure["status"] != "pass":
        raise PbipAdoptionError(
            "assessment disclosure validation blocked unsafe output"
        )
    assessment["assessment_digest"] = canonical_assessment_digest(assessment)
    return assessment


def assess_pbip(project: Path | str) -> dict[str, Any]:
    """Assess one PBIP directory without changing it.

    ``PbipAdoptionError`` represents an unsafe or invalid input shape.  The CLI
    turns it into a concise exit-2 response; library callers can make the same
    distinction without parsing printed output.
    """
    root, is_pbix = _target_path(project)
    if is_pbix:
        assessment = {
            "schema_version": SCHEMA_VERSION,
            "target": {
                "kind": "pbix_unsupported",
                "label": _safe_name(root.name, fallback="PBIX file"),
                "version_control": _git_state(root.parent),
                "components": [],
            },
            "coverage": {
                "status": "blocked",
                "supported": 0,
                "unsupported": 1,
                "unreadable": 0,
                "missing": 0,
                "ambiguous": 0,
            },
            "facts": [
                _fact(
                    "unavailable:pbix",
                    "unavailable_with_reason",
                    "coverage",
                    "PBIX binary",
                    "PBIX input is a supported boundary: save it as a PBIP before "
                    "assessment.",
                    artifact=root.name,
                    reason="PBIX binaries are not parsed or modified in v1.",
                )
            ],
            "governance_findings": [],
            "readiness": [],
            "changes": [],
            "scaffold_plan": {
                "writes": [],
                "preconditions": ["PBIX must first be saved as a PBIP project."],
                "approvals": [],
            },
            "next_step": _next_step("pbix_unsupported", "clean", [], [], []),
            "disclosure": {"status": "pass", "findings": []},
            "assessment_digest": "",
        }
        return _finalize(assessment)
    files = _safe_files(root)
    components, discovered_facts, records = _discover_pbip(root, files)
    facts = [
        *discovered_facts,
        *(_component_fact(component) for component in components),
    ]
    _add_missing_governance_facts(root, facts)
    _scan_literal_boundaries(root, records, facts)
    governance_findings, governance_facts = _governance_findings(root)
    facts.extend(governance_facts)
    readiness, blockers = _readiness(root)
    state = _git_state(root)
    assessment = {
        "schema_version": SCHEMA_VERSION,
        "target": {
            "kind": "pbip_project",
            "label": _safe_name(root.name, fallback="PBIP project"),
            "version_control": state,
            "components": components,
        },
        "coverage": _coverage(components),
        "facts": facts,
        "governance_findings": governance_findings,
        "readiness": readiness,
        "changes": _changes(root, records),
        "scaffold_plan": {
            "writes": [MANIFEST_PATH],
            "preconditions": [
                "existing clean Git worktree",
                "exact current assessment digest",
                "contained absent manifest target",
            ],
            "approvals": [],
        },
        "next_step": _next_step("pbip_project", state, facts, readiness, blockers),
        "disclosure": {"status": "pass", "findings": []},
        "assessment_digest": "",
    }
    return _finalize(assessment)


def _manifest_document(
    assessment: dict[str, Any], records: list[_FileRecord]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "assessment_digest": assessment["assessment_digest"],
        "target": assessment["target"],
        "authoritative_inputs": [
            {"artifact": record.artifact, "sha256": record.sha256}
            for record in sorted(records, key=lambda item: item.artifact)
            if record.sha256 is not None
        ],
        "facts": assessment["facts"],
        "next_step": assessment["next_step"],
        "proposals": [
            fact for fact in assessment["facts"] if fact["classification"] == "proposed"
        ],
        "approvals": [],
    }


def _scaffold_result(
    outcome: str,
    digest: str | None,
    written: list[str],
    blockers: list[str],
    next_step: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "outcome": outcome,
        "assessment_digest": digest,
        "written": written,
        "blocking_reasons": blockers,
        "next_step": next_step,
        "approvals": [],
    }


def _safe_manifest_parent(root: Path) -> tuple[Path, list[Path]]:
    target = root / Path(MANIFEST_PATH)
    if not _is_within(root, target):
        raise PbipAdoptionError("manifest target resolves outside the selected project")
    created: list[Path] = []
    current = root
    for part in Path(MANIFEST_PATH).parts[:-1]:
        current = current / part
        if current.exists():
            if (
                current.is_symlink()
                or not current.is_dir()
                or not _is_within(root, current)
            ):
                raise PbipAdoptionError(
                    "manifest parent is not a safe contained directory"
                )
            continue
        current.mkdir()
        created.append(current)
    return target, created


def _cleanup_empty_directories(directories: list[Path]) -> None:
    for directory in reversed(directories):
        try:
            directory.rmdir()
        except OSError:
            pass


def scaffold_pbip(project: Path | str, accept_assessment: str) -> dict[str, Any]:
    """Create only the accepted adoption baseline, never overwriting a target."""
    try:
        root, is_pbix = _target_path(project)
    except PbipAdoptionError as exc:
        return _scaffold_result(
            "input_defect", None, [], [str(exc)], _default_next_step()
        )
    if is_pbix:
        assessment = assess_pbip(project)
        return _scaffold_result(
            "refused",
            assessment["assessment_digest"],
            [],
            ["PBIX must be saved as PBIP before scaffolding."],
            assessment["next_step"],
        )
    try:
        assessment = assess_pbip(root)
    except PbipAdoptionError as exc:
        return _scaffold_result(
            "input_defect", None, [], [str(exc)], _default_next_step()
        )
    digest = assessment["assessment_digest"]
    if not re.fullmatch(r"[a-f0-9]{64}", accept_assessment or ""):
        return _scaffold_result(
            "input_defect",
            digest,
            [],
            ["--accept-assessment must be a 64-character lowercase SHA-256 digest."],
            assessment["next_step"],
        )
    if accept_assessment != digest:
        return _scaffold_result(
            "refused",
            digest,
            [],
            [
                "The accepted assessment digest is stale or does not match the "
                "current assessment."
            ],
            assessment["next_step"],
        )
    target = root / Path(MANIFEST_PATH)
    if target.exists() or target.is_symlink():
        return _scaffold_result(
            "refused",
            digest,
            [],
            ["The adoption manifest already exists and will not be overwritten."],
            assessment["next_step"],
        )
    if assessment["target"]["version_control"] != "clean":
        return _scaffold_result(
            "refused",
            digest,
            [],
            [
                "Scaffolding requires a clean existing Git worktree; it never "
                "initializes Git."
            ],
            assessment["next_step"],
        )
    if assessment["scaffold_plan"]["writes"] != [MANIFEST_PATH]:
        return _scaffold_result(
            "refused",
            digest,
            [],
            ["The assessment does not declare the fixed adoption manifest write plan."],
            assessment["next_step"],
        )
    # Close the assessment-to-write gap: re-evaluate the complete normalized
    # document immediately before preparing the staged file.  Any concurrent
    # input change invalidates the human-accepted digest and creates no target.
    try:
        current_assessment = assess_pbip(root)
    except PbipAdoptionError as exc:
        return _scaffold_result(
            "input_defect", digest, [], [str(exc)], assessment["next_step"]
        )
    if current_assessment["assessment_digest"] != digest:
        return _scaffold_result(
            "refused",
            current_assessment["assessment_digest"],
            [],
            [
                "The accepted assessment digest is stale or does not match the "
                "current assessment."
            ],
            current_assessment["next_step"],
        )
    assessment = current_assessment
    records = [
        _fingerprint(root, path)
        for path in _safe_files(root)
        if _relative(root, path) != MANIFEST_PATH
    ]
    try:
        import yaml

        manifest = _manifest_document(assessment, records)
        rendered = yaml.safe_dump(
            manifest, sort_keys=True, allow_unicode=False, default_flow_style=False
        ).replace("\r\n", "\n")
        target, created = _safe_manifest_parent(root)
        if target.exists() or target.is_symlink():
            _cleanup_empty_directories(created)
            return _scaffold_result(
                "refused",
                digest,
                [],
                ["The adoption manifest already exists and will not be overwritten."],
                assessment["next_step"],
            )
        fd, staging_name = tempfile.mkstemp(
            prefix=".pbip-adoption-", suffix=".tmp", dir=target.parent
        )
        staging = Path(staging_name)
        published = False
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(staging, target)
            published = True
            staging.unlink()
        except OSError as exc:
            try:
                staging.unlink(missing_ok=True)
            finally:
                if published:
                    target.unlink(missing_ok=True)
                _cleanup_empty_directories(created)
            return _scaffold_result(
                "refused",
                digest,
                [],
                [
                    "The adoption manifest could not be published safely "
                    f"({type(exc).__name__})."
                ],
                assessment["next_step"],
            )
    except (OSError, PbipAdoptionError, yaml.YAMLError) as exc:
        return _scaffold_result(
            "refused",
            digest,
            [],
            [
                "The adoption manifest could not be prepared safely "
                f"({type(exc).__name__})."
            ],
            assessment["next_step"],
        )
    return _scaffold_result(
        "written", digest, [MANIFEST_PATH], [], assessment["next_step"]
    )


def render_assessment_text(assessment: dict[str, Any]) -> str:
    """Render the normalized assessment without collecting a second data view."""
    lines = [
        f"PBIP adoption assessment: {assessment['target']['label']}",
        f"Coverage: {assessment['coverage']['status']}",
        "Facts:",
    ]
    for fact in assessment["facts"]:
        locator = f" ({fact['artifact']})" if fact["artifact"] else ""
        lines.append(
            f"- [{fact['classification']}] {fact['subject']}: {fact['detail']}{locator}"
        )
    if assessment["governance_findings"]:
        lines.append("Governance findings:")
        for finding in assessment["governance_findings"]:
            lines.append(
                f"- [{finding['severity']}] {finding['rule_id']}: "
                f"{finding['message']} ({finding['locator']})"
            )
    next_step = assessment["next_step"]
    lines.extend(["Next step:", f"- {next_step['action']}"])
    for reason in next_step["blocking_reasons"]:
        lines.append(f"- blocker: {reason}")
    lines.append(f"Assessment digest: {assessment['assessment_digest']}")
    return "\n".join(lines) + "\n"


def render_scaffold_result_text(result: dict[str, Any]) -> str:
    lines = [
        f"PBIP adoption scaffold: {result['outcome']}",
        f"Assessment digest: {result['assessment_digest'] or 'unavailable'}",
    ]
    lines.extend(f"Written: {path}" for path in result["written"])
    lines.extend(f"Blocker: {reason}" for reason in result["blocking_reasons"])
    lines.append(f"Next step: {result['next_step']['action']}")
    return "\n".join(lines) + "\n"


def assessment_exit_code(assessment: dict[str, Any]) -> int:
    if (
        assessment["next_step"]["kind"] == "terminal_stop"
        or assessment["next_step"]["blocking_reasons"]
    ):
        return 1
    return (
        1
        if any(fact["classification"] == "blocked" for fact in assessment["facts"])
        else 0
    )


def scaffold_exit_code(result: dict[str, Any]) -> int:
    return (
        0
        if result["outcome"] == "written"
        else 2
        if result["outcome"] == "input_defect"
        else 1
    )


__all__ = [
    "MANIFEST_PATH",
    "PbipAdoptionError",
    "assessment_exit_code",
    "assess_pbip",
    "canonical_assessment_digest",
    "render_assessment_text",
    "render_scaffold_result_text",
    "scaffold_exit_code",
    "scaffold_pbip",
]
