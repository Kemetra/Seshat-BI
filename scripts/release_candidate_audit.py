"""Produce a credential-free, non-authorizing public release candidate audit."""

from __future__ import annotations

import argparse
import json
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

try:
    from scripts.check_release_versions import audit_versions
    from scripts.export_agent_bundles import ExportError, check_all
except ModuleNotFoundError:  # direct `python scripts/release_candidate_audit.py`
    from check_release_versions import audit_versions
    from export_agent_bundles import ExportError, check_all

REGISTRY_PATH = Path("skills/retail-kpi-knowledge/registry.yaml")
_CONTRADICTORY_HISTORY_PHRASES = (
    "there is no prior git tag",
    "no prior git tag exists",
)


def _registry_failure(reason: str) -> dict[str, Any]:
    return {"status": "fail", "blocking_reasons": [reason]}


def _load_registry(
    repo_root: Path, registry_document: Mapping[str, Any] | None
) -> tuple[Mapping[str, Any] | None, str | None]:
    if registry_document is not None:
        return registry_document, None
    path = repo_root / REGISTRY_PATH
    if not path.is_file():
        return None, f"required KPI registry is missing: {REGISTRY_PATH}"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        return None, "KPI registry must be a YAML object"
    return loaded, None


def _audit_registry_entry(
    repo_root: Path, index: int, entry: object
) -> tuple[str | None, list[str]]:
    if not isinstance(entry, Mapping):
        return None, [f"registry entry {index} is not an object"]
    identifier = entry.get("id")
    if not isinstance(identifier, str):
        return None, [f"registry entry {index} has no string id"]
    contract = entry.get("knowledge_contract_ref")
    if not isinstance(contract, str) or not (repo_root / contract).is_file():
        return identifier, [
            f"registry {identifier} contract does not resolve: {contract!r}"
        ]
    return identifier, []


def _audit_registry_entries(
    repo_root: Path, entries: list[object]
) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    blockers: list[str] = []
    for index, entry in enumerate(entries):
        identifier, entry_blockers = _audit_registry_entry(repo_root, index, entry)
        blockers.extend(entry_blockers)
        if identifier is not None:
            ids.append(identifier)
    return ids, blockers


def audit_registry(
    repo_root: Path, registry_document: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Check registry uniqueness, contract resolution, and KPI-MC-15 projection."""

    document, load_error = _load_registry(repo_root, registry_document)
    if load_error is not None or document is None:
        return _registry_failure(load_error or "KPI registry could not be loaded")
    entries = document.get("entries")
    if not isinstance(entries, list):
        return _registry_failure("KPI registry entries must be a list")
    ids, blockers = _audit_registry_entries(repo_root, entries)
    duplicates = sorted(
        identifier for identifier, count in Counter(ids).items() if count > 1
    )
    if duplicates:
        blockers.append(f"duplicate KPI registry IDs: {duplicates}")
    kpi_count = ids.count("KPI-MC-15")
    if kpi_count != 1:
        blockers.append(f"KPI-MC-15 must resolve exactly once; observed {kpi_count}")
    return {
        "status": "fail" if blockers else "pass",
        "entry_count": len(entries),
        "kpi_mc_15_count": kpi_count,
        "blocking_reasons": sorted(blockers),
    }


def _audit_package(repo_root: Path) -> dict[str, Any]:
    pyproject_path = repo_root / "pyproject.toml"
    blockers: list[str] = []
    version: str | None = None
    if not pyproject_path.is_file():
        blockers.append("pyproject.toml is missing")
    else:
        document = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = document.get("project", {})
        version = project.get("version")
        if project.get("name") != "seshat-bi":
            blockers.append("Python project name must be seshat-bi")
        scripts = project.get("scripts", {})
        if scripts.get("seshat") != "seshat.cli:main":
            blockers.append("seshat console script must resolve to seshat.cli:main")
        if scripts.get("retail") != "seshat.cli:main":
            blockers.append("retail console script must resolve to seshat.cli:main")
    return {
        "status": "fail" if blockers else "pass",
        "version": version,
        "blocking_reasons": blockers,
    }


def _history_doc_blockers(repo_root: Path, relative: str) -> list[str]:
    path = repo_root / relative
    if not path.is_file():
        return [f"release history document is missing: {relative}"]
    lowered = path.read_text(encoding="utf-8").casefold()
    return [
        f"{relative} contradicts the existing v0.1.0 tag: {phrase!r}"
        for phrase in _CONTRADICTORY_HISTORY_PHRASES
        if phrase in lowered
    ]


def _audit_history_docs(repo_root: Path) -> dict[str, Any]:
    blockers = [
        blocker
        for relative in ("CHANGELOG.md", "docs/releases/v0.1.md")
        for blocker in _history_doc_blockers(repo_root, relative)
    ]
    return {
        "status": "fail" if blockers else "pass",
        "blocking_reasons": blockers,
    }


def _generated_bundles_check(
    repo_root: Path, allow_untracked_inputs: bool
) -> dict[str, Any]:
    try:
        check_all(repo_root, allow_untracked_inputs=allow_untracked_inputs)
    except ExportError as exc:
        return {"status": "fail", "blocking_reasons": [str(exc)]}
    return {"status": "pass", "blocking_reasons": []}


def _repository_checks(repo_root: Path, allow_untracked_inputs: bool) -> dict[str, Any]:
    return {
        "package": _audit_package(repo_root),
        "registry": audit_registry(repo_root),
        "history_docs": _audit_history_docs(repo_root),
        "generated_bundles": _generated_bundles_check(
            repo_root, allow_untracked_inputs
        ),
    }


def _check_blockers(checks: Mapping[str, Any]) -> list[str]:
    return sorted(
        blocker for check in checks.values() for blocker in check["blocking_reasons"]
    )


def _immutable_version_blockers(
    version: str, known_versions: set[str] | None
) -> list[str]:
    if version not in (known_versions or set()):
        return []
    return [
        f"immutable package version {version} already exists; "
        "select a new owner-approved version"
    ]


def _artifact_digests(repo_root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for platform, relative in (
        ("claude", "integrations/claude-code/seshat-bi/bundle-manifest.json"),
        ("codex", "integrations/codex/seshat-bi/bundle-manifest.json"),
    ):
        path = repo_root / relative
        if not path.is_file():
            continue
        digest = json.loads(path.read_text(encoding="utf-8")).get("manifest_digest")
        if isinstance(digest, str):
            digests[f"{platform}-bundle-manifest"] = digest
    return digests


def _surface_status(blocked: bool) -> dict[str, Any]:
    coordinated_status = "blocked" if blocked else "unverified"
    return {
        "schema_version": "1.0",
        "surfaces": {
            "python_pypi": {
                "status": "unverified",
                "reason": "no clean public PyPI install evidence is attached",
            },
            "claude_repository": {
                "status": "unverified",
                "reason": (
                    "no external public GitHub marketplace acceptance is attached"
                ),
            },
            "codex_repository": {
                "status": "unverified",
                "reason": "no external public Codex CLI and IDE acceptance is attached",
            },
            "claude_public_catalog": {
                "status": "unavailable",
                "reason": "no owner-approved public catalog submission was performed",
            },
            "openai_public_plugin": {
                "status": "unavailable",
                "reason": "no owner-approved OpenAI plugin submission was performed",
            },
        },
        "coordinated_release_status": coordinated_status,
        "summary": (
            "Repository candidate evidence only; public surfaces remain unverified."
        ),
    }


def _evidence_manifest(report: Mapping[str, Any]) -> dict[str, Any]:
    checks = report["repository_checks"]
    return {
        "schema_version": "1.0",
        "candidate_id": report["candidate_id"],
        "version": report["candidate_version"],
        "source_revision": report["source_revision"],
        "artifact_digests": report["artifact_digests"],
        "repository_check_statuses": {
            name: check["status"] for name, check in checks.items()
        },
        "surface_availability": report["surface_availability"],
        "publication_approval": None,
        "authority_disclaimer": (
            "Sanitized evidence only; no version, configuration, publication, "
            "submission, tag, release, or rollback action is approved."
        ),
    }


def audit_candidate(
    repo_root: Path,
    *,
    allow_untracked_inputs: bool = False,
    known_immutable_package_versions: set[str] | None = None,
) -> dict[str, Any]:
    """Audit repository readiness and enumerate release blockers without a score."""

    repository_checks = _repository_checks(repo_root, allow_untracked_inputs)
    version_report = audit_versions(repo_root)
    repository_blockers = _check_blockers(repository_checks)
    release_blockers = list(version_report["blocking_reasons"])
    version = str(version_report["candidate_version"])
    release_blockers.extend(
        _immutable_version_blockers(version, known_immutable_package_versions)
    )
    all_blockers = sorted(repository_blockers + release_blockers)
    candidate_id = f"candidate-{version}-{version_report['source_revision'][:12]}"
    artifact_digests = _artifact_digests(repo_root)
    surface_status = _surface_status(bool(all_blockers))
    report = {
        "schema_version": "1.0",
        "candidate_id": candidate_id,
        "candidate_version": version,
        "source_revision": version_report["source_revision"],
        "status": "blocked" if all_blockers else "validated",
        "repository_status": "fail" if repository_blockers else "pass",
        "repository_checks": repository_checks,
        "version_sync": version_report,
        "blocking_reasons": all_blockers,
        "artifact_digests": artifact_digests,
        "surface_availability": surface_status,
        "approval": None,
        "authority_disclaimer": (
            "This audit records evidence only; it grants no version, tag, publication, "
            "catalog, submission, or rollback approval."
        ),
    }
    report["evidence_manifest"] = _evidence_manifest(report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repository-check", action="store_true")
    parser.add_argument("--require-release-ready", action="store_true")
    parser.add_argument("--allow-untracked-inputs", action="store_true")
    parser.add_argument(
        "--known-immutable-package-version", action="append", default=[]
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = audit_candidate(
            args.repo.resolve(),
            allow_untracked_inputs=args.allow_untracked_inputs,
            known_immutable_package_versions=set(args.known_immutable_package_version),
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(
            json.dumps({"status": "blocked", "blocking_reasons": [str(exc)]}, indent=2)
        )
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if args.repository_check and report["repository_status"] != "pass":
        return 1
    if args.require_release_ready and report["status"] != "validated":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
