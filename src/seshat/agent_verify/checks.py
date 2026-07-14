"""The eleven required `seshat agent verify` checks (spec 129).

Each check is a pure function reading committed/generated repo state and
returning exactly one :class:`~seshat.agent_verify.model.PerCheckResult`.
Nothing here launches a live agent, opens a database, or reaches the
network (FR-006/FR-008); the only external process started is a local,
offline ``git`` read via the already-shipped
``scripts.check_release_versions`` version audit.

Six checks are ``per_target`` (install & discovery, version compatibility,
update integrity, uninstall integrity, IDE surface, and the governance
contract-presence check that reads the selected target's own exported
``portable-operating-contract.md``). Five are ``shared_baseline`` (readiness
routing via the read-only governor, and the four hard-stop scenarios via the
benchmark's scenario loader + deterministic scripted reference) -- these are
repo-level and target-invariant, so their evidence is labeled a shared
baseline rather than implied per-target (FR-012 through FR-017).

No check re-implements hashing, version parsing, or scenario execution: it
reuses ``scripts.export_agent_bundles`` provenance shape, ``scripts.
check_release_versions.audit_versions``, ``seshat.benchmark`` (loader +
scripted reference), and ``seshat.governor.service.GovernorService``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .model import PerCheckResult
from .targets import VerifyTargetSpec, marketplace_path_for

# --- small result builders (keep every call site's invariant obvious) ------


def _pass(check_id: str, evidence_class: str, evidence: list[str]) -> PerCheckResult:
    return PerCheckResult(
        check_id=check_id,
        verdict="PASS",
        evidence_class=evidence_class,
        evidence=tuple(evidence),
    )


def _blocked(check_id: str, evidence_class: str, reasons: list[str]) -> PerCheckResult:
    return PerCheckResult(
        check_id=check_id,
        verdict="BLOCKED",
        evidence_class=evidence_class,
        blocking_reasons=tuple(reasons),
    )


def _unavailable(check_id: str, evidence_class: str, reason: str) -> PerCheckResult:
    return PerCheckResult(
        check_id=check_id,
        verdict="UNAVAILABLE",
        evidence_class=evidence_class,
        unavailable_reason=reason,
    )


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"is missing or unreadable ({exc})"
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"is not valid JSON ({exc})"
    if not isinstance(document, dict):
        return None, "is not a JSON object"
    return document, None


# --- installation & discovery (FR-009/FR-010; extends spec 108) -----------


def _plugin_matches(entry: object, name: object) -> bool:
    return isinstance(entry, dict) and entry.get("name") == name


def install_discovery_check(
    target_spec: VerifyTargetSpec, repo_root: Path | str
) -> PerCheckResult:
    check_id = "install_discovery"
    root = Path(repo_root)

    manifest, manifest_error = _read_json(root / target_spec.manifest_path)
    if manifest_error is not None:
        return _blocked(
            check_id,
            "per_target",
            [f"plugin manifest {target_spec.manifest_path} {manifest_error}"],
        )
    plugin_name = manifest.get("name") if manifest else None
    if not plugin_name:
        return _blocked(
            check_id,
            "per_target",
            [f"plugin manifest declares no name: {target_spec.manifest_path}"],
        )

    marketplace_rel = marketplace_path_for(target_spec.name)
    marketplace, marketplace_error = _read_json(root / marketplace_rel)
    if marketplace_error is not None:
        return _blocked(
            check_id,
            "per_target",
            [f"marketplace/discovery entry {marketplace_rel} {marketplace_error}"],
        )
    plugins = marketplace.get("plugins") if marketplace else None
    if not isinstance(plugins, list) or not any(
        _plugin_matches(entry, plugin_name) for entry in plugins
    ):
        return _blocked(
            check_id,
            "per_target",
            [
                f"marketplace entry does not list plugin {plugin_name!r}: "
                f"{marketplace_rel}"
            ],
        )

    provenance, provenance_error = _read_json(root / target_spec.provenance_manifest)
    if provenance_error is not None:
        return _blocked(
            check_id,
            "per_target",
            [
                f"provenance manifest {target_spec.provenance_manifest} "
                f"{provenance_error}"
            ],
        )
    if (
        provenance.get("target") != target_spec.name
        or provenance.get("plugin") != plugin_name
    ):
        return _blocked(
            check_id,
            "per_target",
            [
                "provenance manifest target/plugin identity mismatch: "
                f"{target_spec.provenance_manifest}"
            ],
        )

    return _pass(
        check_id,
        "per_target",
        [
            f"plugin manifest resolved: {target_spec.manifest_path} "
            f"(name={plugin_name!r}, version={manifest.get('version')!r})",
            f"marketplace/discovery entry resolved: {marketplace_rel}",
            f"provenance manifest resolved: {target_spec.provenance_manifest} "
            f"(target={provenance.get('target')!r})",
        ],
    )


# --- version compatibility (FR-011; extends spec 108) ----------------------


def version_compatibility_check(
    target_spec: VerifyTargetSpec, repo_root: Path | str
) -> PerCheckResult:
    check_id = "version_compatibility"
    root = Path(repo_root)

    try:
        from scripts.check_release_versions import VersionAuditError, audit_versions
    except ImportError as exc:
        return _blocked(
            check_id,
            "per_target",
            [f"version-compatibility audit surface is unavailable: {exc}"],
        )

    try:
        report = audit_versions(root)
    except (VersionAuditError, OSError) as exc:
        return _blocked(check_id, "per_target", [f"version audit failed: {exc}"])

    projections = {
        str(item.get("surface")): item for item in report.get("projections", [])
    }
    projection = projections.get(target_spec.version_source)
    if projection is None:
        return _blocked(
            check_id,
            "per_target",
            [
                "no version projection for surface "
                f"{target_spec.version_source!r} in the release-verification audit"
            ],
        )

    observed = projection.get("observed")
    expected = projection.get("expected")
    if projection.get("status") != "pass":
        reason = projection.get("blocking_reason") or (
            f"{target_spec.version_source} declared version {observed!r} is "
            f"outside the supported range; supported version is {expected!r}"
        )
        return _blocked(check_id, "per_target", [str(reason)])

    return _pass(
        check_id,
        "per_target",
        [
            f"{target_spec.version_source} declared version {observed!r} "
            f"matches the supported release version {expected!r}"
        ],
    )


# --- update integrity (FR-018; extends the exporter provenance manifest) --


def update_integrity_check(
    target_spec: VerifyTargetSpec, repo_root: Path | str
) -> PerCheckResult:
    check_id = "update_integrity"
    root = Path(repo_root)
    manifest_path = root / target_spec.provenance_manifest

    manifest, manifest_error = _read_json(manifest_path)
    if manifest_error is not None:
        return _blocked(
            check_id,
            "per_target",
            [f"provenance manifest {target_spec.provenance_manifest} {manifest_error}"],
        )
    entries = manifest.get("entries") if manifest else None
    if not isinstance(entries, list) or not entries:
        return _blocked(
            check_id,
            "per_target",
            [
                "provenance manifest declares no entries: "
                f"{target_spec.provenance_manifest}"
            ],
        )

    bundle_root = manifest_path.parent
    drifted: list[str] = []
    for entry in entries:
        destination = entry.get("destination") if isinstance(entry, dict) else None
        expected_hash = entry.get("output_sha256") if isinstance(entry, dict) else None
        if not isinstance(destination, str) or not isinstance(expected_hash, str):
            drifted.append(f"malformed provenance entry: {entry!r}")
            continue
        file_path = bundle_root / destination
        if not file_path.is_file():
            drifted.append(
                f"{destination}: generated file is missing "
                f"(expected sha256 {expected_hash})"
            )
            continue
        observed_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if observed_hash != expected_hash:
            drifted.append(
                f"{destination}: expected sha256 {expected_hash}, "
                f"observed {observed_hash}"
            )

    if drifted:
        return _blocked(check_id, "per_target", drifted)

    return _pass(
        check_id,
        "per_target",
        [
            f"{len(entries)} generated files under "
            f"{bundle_root.relative_to(root).as_posix()} match their recorded "
            "output_sha256 provenance"
        ],
    )


# --- uninstall integrity (FR-019) ------------------------------------------


def uninstall_integrity_check(
    target_spec: VerifyTargetSpec, repo_root: Path | str
) -> PerCheckResult:
    check_id = "uninstall_integrity"
    root = Path(repo_root)
    manifest_path = root / target_spec.footprint_source

    manifest, manifest_error = _read_json(manifest_path)
    if manifest_error is not None:
        return _unavailable(
            check_id,
            "per_target",
            f"installed footprint cannot be enumerated: "
            f"{target_spec.footprint_source} {manifest_error}",
        )
    entries = manifest.get("entries") if manifest else None
    destinations = sorted(
        str(entry.get("destination"))
        for entry in (entries or [])
        if isinstance(entry, dict) and isinstance(entry.get("destination"), str)
    )
    if not destinations:
        return _unavailable(
            check_id,
            "per_target",
            f"installed footprint cannot be enumerated: "
            f"{target_spec.footprint_source} declares no destinations",
        )

    return _pass(
        check_id,
        "per_target",
        [
            f"declared installed footprint: {len(destinations)} paths under "
            f"{manifest_path.parent.relative_to(root).as_posix()} "
            f"(from {target_spec.footprint_source})",
            *destinations,
        ],
    )


# --- IDE surface (FR-020) ---------------------------------------------------


def ide_surface_check(
    target_spec: VerifyTargetSpec, repo_root: Path | str
) -> PerCheckResult:
    check_id = "ide_surface"
    if not target_spec.ide_surface:
        return _unavailable(
            check_id,
            "per_target",
            f"{target_spec.name} declares no IDE surface for this bundle",
        )

    root = Path(repo_root)
    manifest, manifest_error = _read_json(root / target_spec.manifest_path)
    if manifest_error is not None:
        return _blocked(
            check_id,
            "per_target",
            [f"plugin manifest {target_spec.manifest_path} {manifest_error}"],
        )
    interface = manifest.get("interface") if manifest else None
    if not isinstance(interface, dict) or not interface.get("displayName"):
        return _blocked(
            check_id,
            "per_target",
            [
                f"{target_spec.name} declares an IDE surface but its manifest "
                f"has no usable interface block: {target_spec.manifest_path}"
            ],
        )

    return _pass(
        check_id,
        "per_target",
        [
            f"{target_spec.manifest_path} declares an IDE-surface interface "
            f"block: displayName={interface['displayName']!r}"
        ],
    )


# --- per-target governance-contract presence (FR-012a) ---------------------

# The authoritative hard-stop line set every target's own exported
# `portable-operating-contract.md` must carry verbatim (Phase 0 research Q5).
# This list is this feature's own governance fixture -- it is intentionally
# NOT derived from the file being checked (that would be circular); a
# maintainer updates it in lockstep with `distribution/bundle-templates/
# shared/portable-operating-contract.md` when that source template changes.
GOVERNANCE_HARD_STOP_LINES: tuple[tuple[str, str], ...] = (
    (
        "never_self_grant_approval",
        "Never self-grant an approval; grain, PII publish-safety, business "
        "rollups, and sentinel-versus-null decisions belong to a named human.",
    ),
    (
        "no_silver_before_mapping_cleared",
        "Never proceed to Silver until Mapping Ready is cleared.",
    ),
    (
        "no_gold_to_powerbi_before_live_validation",
        "Never point Power BI at Gold until live validation passes.",
    ),
    (
        "no_dashboard_before_metric_contracts",
        "Never design a dashboard before metric contracts exist.",
    ),
    (
        "no_powerbi_adapter_execution",
        "Never execute the Power BI adapter from this Public Beta bundle.",
    ),
    (
        "no_invented_mappings_or_fabricated_score",
        "Never invent mappings, expose secrets/PII, skip a readiness gate, or "
        "report a numeric readiness/confidence score.",
    ),
)


_WHITESPACE_RUN = re.compile(r"\s+")


def _normalize_prose(text: str) -> str:
    """Collapse whitespace runs (including the markdown source's manual
    line-wrapping of long bullets) so a hard-stop line can be located by
    substring containment regardless of where the file wraps it."""
    return _WHITESPACE_RUN.sub(" ", text).strip()


def governance_contract_presence_check(
    target_spec: VerifyTargetSpec, repo_root: Path | str
) -> PerCheckResult:
    check_id = "governance_contract_presence"
    path = Path(repo_root) / target_spec.operating_contract
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return _blocked(
            check_id,
            "per_target",
            [
                f"{target_spec.name}'s exported operating contract is missing "
                f"or unreadable: {target_spec.operating_contract} ({exc})"
            ],
        )
    text = _normalize_prose(raw_text)

    missing = [
        name
        for name, line in GOVERNANCE_HARD_STOP_LINES
        if _normalize_prose(line) not in text
    ]
    if missing:
        return _blocked(
            check_id,
            "per_target",
            [
                f"{target_spec.name}'s exported {target_spec.operating_contract} "
                f"drops or mutates hard stop {name!r}"
                for name in missing
            ],
        )

    return _pass(
        check_id,
        "per_target",
        [
            f"{target_spec.operating_contract} carries all "
            f"{len(GOVERNANCE_HARD_STOP_LINES)} governance hard-stop lines"
        ],
    )


# --- shared-baseline governance checks (FR-012 through FR-017) ------------

_SCENARIO_MANIFESTS = (
    "benchmark/scenarios/hard-stops.yaml",
    "benchmark/scenarios/retail-semantics.yaml",
)


def _scenario_baseline_check(
    check_id: str, scenario_id: str, repo_root: Path | str
) -> PerCheckResult:
    from ..benchmark.model import BenchmarkError, Observation
    from ..benchmark.reference import reference_participant
    from ..benchmark.runner import load_scenarios

    try:
        scenarios = load_scenarios(Path(repo_root), *_SCENARIO_MANIFESTS)
    except BenchmarkError as exc:
        return _blocked(
            check_id, "shared_baseline", [f"scenario manifest is malformed: {exc}"]
        )

    scenario = next(
        (item for item in scenarios if item.scenario_id == scenario_id), None
    )
    if scenario is None:
        return _blocked(
            check_id, "shared_baseline", [f"cited scenario is missing: {scenario_id!r}"]
        )
    if scenario.expected_behavior == "proceed":
        return _blocked(
            check_id,
            "shared_baseline",
            [
                f"{scenario_id} declared expected_behavior is 'proceed'; the "
                "governed hard stop no longer holds"
            ],
        )

    behavior, evidence = reference_participant().respond(scenario)
    observation = Observation(
        scenario_id=scenario.scenario_id,
        expected_behavior=scenario.expected_behavior,
        observed_behavior=behavior,
        evidence=evidence,
    )
    if observation.comparison != "match":
        return _blocked(
            check_id,
            "shared_baseline",
            [
                f"{scenario_id}: scripted reference baseline is a "
                f"{observation.comparison} (expected {scenario.expected_behavior!r}, "
                f"observed {behavior!r})"
            ],
        )

    return _pass(
        check_id,
        "shared_baseline",
        [
            f"{scenario_id}: declared expected_behavior={scenario.expected_behavior!r}",
            f"scripted reference reproduces it (observed={behavior!r})",
            *evidence,
        ],
    )


def pii_refusal_check(repo_root: Path | str) -> PerCheckResult:
    return _scenario_baseline_check("pii_refusal", "rs-pii-exposure", repo_root)


def no_self_approval_check(repo_root: Path | str) -> PerCheckResult:
    return _scenario_baseline_check(
        "no_self_approval", "hs-self-grant-approval", repo_root
    )


def no_silver_before_mapping_check(repo_root: Path | str) -> PerCheckResult:
    return _scenario_baseline_check(
        "no_silver_before_mapping", "hs-silver-before-mapping", repo_root
    )


def no_invented_metric_meaning_check(repo_root: Path | str) -> PerCheckResult:
    return _scenario_baseline_check(
        "no_invented_metric_meaning", "rs-metric-without-approval", repo_root
    )


# --- readiness routing (FR-012; the read-only governor) --------------------

_ROUTING_FIELDS = (
    "current_stage",
    "evidence",
    "blocking_reasons",
    "next_allowed_action",
)


def readiness_routing_check(repo_root: Path | str) -> PerCheckResult:
    check_id = "readiness_routing"
    root = Path(repo_root).resolve()

    try:
        from seshat.governor.service import GovernorService
    except ImportError as exc:
        return _unavailable(
            check_id,
            "shared_baseline",
            f"the read-only governor is not importable: {exc}",
        )

    try:
        service = GovernorService(root)
        result = service.call("seshat_get_next_action", {"workspace": str(root)})
    except (OSError, ValueError) as exc:
        return _unavailable(
            check_id,
            "shared_baseline",
            f"the read-only governor could not be invoked: {exc}",
        )

    if result.get("read_only_proof") is not True:
        return _unavailable(
            check_id,
            "shared_baseline",
            "the governor response did not carry its read-only proof",
        )

    content = result.get("content") or {}
    missing = [field for field in _ROUTING_FIELDS if field not in content]
    if "forbidden_scope" not in result:
        missing.append("forbidden_scope")
    if missing:
        return _unavailable(
            check_id,
            "shared_baseline",
            f"the governor response is missing fields: {', '.join(missing)}",
        )

    return _pass(
        check_id,
        "shared_baseline",
        [
            f"governor current_stage={content.get('current_stage')!r}",
            f"evidence entries: {len(content.get('evidence') or [])}",
            f"blocking_reasons entries: {len(content.get('blocking_reasons') or [])}",
            "next_allowed_action is present "
            f"({len(str(content.get('next_allowed_action')))} chars)",
            f"forbidden_scope entries: {len(result.get('forbidden_scope') or [])}",
            "no write performed (read_only_proof=True)",
        ],
    )


# --- the ordered set of required checks (US1 + US2) ------------------------

PER_TARGET_CHECK_IDS: tuple[str, ...] = (
    "install_discovery",
    "version_compatibility",
    "update_integrity",
    "uninstall_integrity",
    "ide_surface",
    "governance_contract_presence",
)
SHARED_BASELINE_CHECK_IDS: tuple[str, ...] = (
    "readiness_routing",
    "pii_refusal",
    "no_self_approval",
    "no_silver_before_mapping",
    "no_invented_metric_meaning",
)
REQUIRED_CHECK_IDS: tuple[str, ...] = PER_TARGET_CHECK_IDS + SHARED_BASELINE_CHECK_IDS


def run_all_checks(
    target_spec: VerifyTargetSpec, repo_root: Path | str
) -> tuple[PerCheckResult, ...]:
    """Run every required check for one target, in a stable order."""
    return (
        install_discovery_check(target_spec, repo_root),
        version_compatibility_check(target_spec, repo_root),
        update_integrity_check(target_spec, repo_root),
        uninstall_integrity_check(target_spec, repo_root),
        ide_surface_check(target_spec, repo_root),
        governance_contract_presence_check(target_spec, repo_root),
        readiness_routing_check(repo_root),
        pii_refusal_check(repo_root),
        no_self_approval_check(repo_root),
        no_silver_before_mapping_check(repo_root),
        no_invented_metric_meaning_check(repo_root),
    )
