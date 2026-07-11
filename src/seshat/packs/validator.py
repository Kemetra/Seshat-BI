"""Extension-pack validation (spec 120, US5, FR-028 through FR-032).

Two layers, both fail-closed and returning disclosure-safe findings:

- :func:`validate_pack` -- one manifest: published-schema conformance,
  namespace discipline, category, declarative-content enforcement (no
  executable artifacts or hooks), secret/disclosure scanning, stage-order and
  authority-escalation rejection, universal-schema-claim rejection, artifact
  containment/existence, and core-contract compatibility.
- :func:`validate_selection` -- an explicit multi-pack selection: duplicate
  fully qualified IDs, missing dependencies, dependency cycles, and declared
  conflicts, reported BEFORE any pack content contributes to a projection.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..artifact_identity import resolve_within
from ..disclosure import scan_disclosure
from ..ecosystem_contracts import validate_json_contract
from .loader import load_pack_document
from .model import PackError, PackManifest, manifest_from_document

# The pack<->core contract line this core supports (MAJOR of the extension
# pack contract, not the Python package version).
CORE_CONTRACT_MAJOR = 1
_CORE_COMPAT_RE = re.compile(r"^([0-9]+)\.(x|[0-9]+)$")
_LOCAL_ID_RE = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")

# Declarative allow-list: pack content is data and prose, never code.
_DECLARATIVE_SUFFIXES = frozenset(
    {".yaml", ".yml", ".md", ".csv", ".json", ".txt", ".svg"}
)
_HOOK_KEYS = frozenset(
    {"entry_point", "entry_points", "hooks", "on_load", "plugin", "exec", "command"}
)
_STAGE_KEYS = frozenset({"stages", "stage_order", "readiness_stages"})
_AUTHORITY_RE = re.compile(
    r"self[-_ ]?approv|auto[-_ ]?approv|grants?\s+approval|bypass(es)?\s+the\s+gate",
    re.IGNORECASE,
)
_UNIVERSAL_RE = re.compile(
    r"universal\s+schema|works\s+for\s+(all|any)\s+(client|retailer|schema)",
    re.IGNORECASE,
)

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / (
    "schemas/seshat-extension-pack.schema.json"
)


def _finding(rule: str, locator: str, message: str) -> dict[str, str]:
    return {"rule": rule, "locator": locator, "message": message}


def _children(node: Any, path: str) -> list[tuple[str, str | None, Any]]:
    """Normalize container children to ``(path, key, value)`` triples."""
    if isinstance(node, dict):
        return [(f"{path}.{key}", str(key), value) for key, value in node.items()]
    if isinstance(node, list):
        return [(f"{path}[{index}]", None, value) for index, value in enumerate(node)]
    return []


def _walk_keys(node: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    """Yield ``(path, key)`` for every mapping key, recursively."""
    for child_path, key, value in _children(node, path):
        if key is not None:
            yield child_path, key
        yield from _walk_keys(value, child_path)


def _walk_strings(node: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    """Yield ``(path, value)`` for every string leaf, recursively."""
    if isinstance(node, str):
        yield path, node
        return
    for child_path, _key, value in _children(node, path):
        yield from _walk_strings(value, child_path)


def _schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _namespace_findings(document: dict[str, Any], locator: str) -> list[dict[str, str]]:
    findings = []
    provides = document.get("provides", [])
    if isinstance(provides, list):
        seen: set[str] = set()
        for local_id in provides:
            if not isinstance(local_id, str) or not _LOCAL_ID_RE.fullmatch(local_id):
                findings.append(
                    _finding(
                        "pack_namespace",
                        f"{locator}#provides",
                        f"provided id {local_id!r} is not a lowercase local id",
                    )
                )
            elif local_id in seen:
                findings.append(
                    _finding(
                        "pack_duplicate_id",
                        f"{locator}#provides",
                        f"provided id {local_id!r} is declared twice",
                    )
                )
            seen.add(local_id if isinstance(local_id, str) else repr(local_id))
    return findings


def _key_finding(path: str, key: str, locator: str) -> dict[str, str] | None:
    if key in _HOOK_KEYS:
        return _finding(
            "pack_executable_content",
            f"{locator}#{path}",
            f"packs are declarative; key {key!r} suggests executable wiring",
        )
    if key in _STAGE_KEYS:
        return _finding(
            "pack_stage_change",
            f"{locator}#{path}",
            "packs cannot declare or reorder readiness stages",
        )
    return None


def _string_findings(path: str, value: str, locator: str) -> list[dict[str, str]]:
    findings = []
    if _AUTHORITY_RE.search(value):
        findings.append(
            _finding(
                "pack_authority",
                f"{locator}#{path}",
                "packs cannot claim or grant approval authority",
            )
        )
    if _UNIVERSAL_RE.search(value):
        findings.append(
            _finding(
                "pack_universal_claim",
                f"{locator}#{path}",
                "packs cannot claim a universal schema (Principle VII)",
            )
        )
    return findings


def _content_findings(document: dict[str, Any], locator: str) -> list[dict[str, str]]:
    """Declarative-content, stage-order, authority, and claim enforcement."""
    candidates = [
        _key_finding(path, key, locator) for path, key in _walk_keys(document)
    ]
    findings = [finding for finding in candidates if finding is not None]
    for path, value in _walk_strings(document):
        findings.extend(_string_findings(path, value, locator))
    return findings


def _suffix_finding(declared: str, locator: str, kind: str) -> dict[str, str] | None:
    if Path(declared).suffix.lower() in _DECLARATIVE_SUFFIXES:
        return None
    return _finding(
        "pack_executable_content",
        locator,
        f"{kind} {declared!r} is not a declarative content file",
    )


def _location_findings(
    root: Path, candidate: str, locator: str, label: str
) -> list[dict[str, str]]:
    try:
        resolved = resolve_within(root, candidate)
    except ValueError:
        return [
            _finding(
                "pack_artifact_escape",
                locator,
                f"{label} escapes the pack directory",
            )
        ]
    if not resolved.is_file():
        return [
            _finding(
                "pack_artifact_missing",
                locator,
                f"{label} is declared but absent",
            )
        ]
    return []


def _declared_files(manifest: PackManifest) -> list[tuple[str, str, str]]:
    """Every declared content file as ``(declared, locator, kind)``."""
    entries = [
        (artifact.path, f"{manifest.manifest_path}#artifacts[{index}]", "artifact")
        for index, artifact in enumerate(manifest.artifacts)
    ]
    entries.extend(
        (fixture, f"{manifest.manifest_path}#fixtures[{index}]", "fixture")
        for index, fixture in enumerate(manifest.fixtures)
    )
    return entries


def _declared_file_findings(root: Path, manifest: PackManifest) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for declared, locator, kind in _declared_files(manifest):
        if not declared:
            findings.append(
                _finding(f"pack_{kind}_missing", locator, f"{kind} path is empty")
            )
            continue
        suffix = _suffix_finding(declared, locator, kind)
        if suffix is not None:
            findings.append(suffix)
        candidate = (
            f"{manifest.directory}/{declared}" if manifest.directory else declared
        )
        findings.extend(
            _location_findings(root, candidate, locator, f"{kind} {declared!r}")
        )
    return findings


def _compatibility_findings(
    core_compatibility: object, locator: str
) -> list[dict[str, str]]:
    if not isinstance(core_compatibility, str):
        return []
    match = _CORE_COMPAT_RE.fullmatch(core_compatibility)
    if match is None:
        return [
            _finding(
                "pack_incompatible_core",
                f"{locator}#core_compatibility",
                "core_compatibility must be 'MAJOR.x' or 'MAJOR.MINOR'",
            )
        ]
    if int(match.group(1)) != CORE_CONTRACT_MAJOR:
        return [
            _finding(
                "pack_incompatible_core",
                f"{locator}#core_compatibility",
                f"pack targets core contract major {match.group(1)}; "
                f"this core supports {CORE_CONTRACT_MAJOR}.x",
            )
        ]
    return []


def _secret_findings(document: dict[str, Any], relative: str) -> list[dict[str, str]]:
    return [
        _finding(
            "pack_secret",
            f"{relative}#{disclosure_finding['locator']}",
            disclosure_finding["message"],
        )
        for disclosure_finding in scan_disclosure(document)["findings"]
    ]


def validate_pack(
    repo_root: Path | str, manifest_path: Path | str
) -> tuple[PackManifest | None, list[dict[str, str]]]:
    """Validate one pack manifest. Returns ``(manifest, findings)``; the
    manifest is ``None`` when the document is unreadable or schema-invalid,
    and pack content must not contribute to any projection while findings
    exist (FR-032)."""
    root = Path(repo_root).resolve()
    try:
        document, relative = load_pack_document(root, manifest_path)
    except PackError as exc:
        return None, [_finding("pack_unreadable", str(manifest_path), str(exc))]

    schema_errors = validate_json_contract(document, _schema())
    findings = [_finding("pack_schema", relative, error) for error in schema_errors]
    if findings:
        return None, findings

    findings.extend(_namespace_findings(document, relative))
    findings.extend(_content_findings(document, relative))
    findings.extend(
        _compatibility_findings(document.get("core_compatibility"), relative)
    )
    findings.extend(_secret_findings(document, relative))

    manifest = manifest_from_document(document, relative)
    findings.extend(_declared_file_findings(root, manifest))
    return manifest, findings


def _cycle_findings(packs: dict[str, PackManifest]) -> list[dict[str, str]]:
    findings = []
    state: dict[str, int] = {}  # 0 visiting, 1 done

    def visit(pack_id: str, trail: tuple[str, ...]) -> None:
        if state.get(pack_id) == 1:
            return
        if state.get(pack_id) == 0:
            cycle = " -> ".join((*trail[trail.index(pack_id) :], pack_id))
            findings.append(
                _finding(
                    "pack_dependency_cycle",
                    packs[pack_id].manifest_path,
                    f"dependency cycle: {cycle}",
                )
            )
            return
        state[pack_id] = 0
        for requirement in packs[pack_id].requires:
            # Self-requires is reported separately by validate_selection.
            if requirement in packs and requirement != pack_id:
                visit(requirement, (*trail, pack_id))
        state[pack_id] = 1

    for pack_id in sorted(packs):
        visit(pack_id, ())
    return findings


def _index_selection(
    packs: list[PackManifest],
) -> tuple[dict[str, PackManifest], list[dict[str, str]]]:
    by_id: dict[str, PackManifest] = {}
    findings: list[dict[str, str]] = []
    for pack in packs:
        if pack.pack_id in by_id:
            findings.append(
                _finding(
                    "pack_duplicate_id",
                    pack.manifest_path,
                    f"pack id {pack.pack_id!r} is selected twice",
                )
            )
            continue
        by_id[pack.pack_id] = pack
    return by_id, findings


def _provides_collisions(by_id: dict[str, PackManifest]) -> list[dict[str, str]]:
    qualified_owners: dict[str, str] = {}
    findings: list[dict[str, str]] = []
    for pack in by_id.values():
        for qualified in pack.qualified_provides():
            owner = qualified_owners.setdefault(qualified, pack.pack_id)
            if owner != pack.pack_id:
                findings.append(
                    _finding(
                        "pack_duplicate_id",
                        pack.manifest_path,
                        f"provided id {qualified!r} collides with pack {owner!r}",
                    )
                )
    return findings


def _requirement_finding(
    pack: PackManifest, requirement: str, by_id: dict[str, PackManifest]
) -> dict[str, str] | None:
    if requirement == pack.pack_id:
        return _finding(
            "pack_dependency_cycle",
            pack.manifest_path,
            f"pack {pack.pack_id!r} requires itself",
        )
    if requirement not in by_id:
        return _finding(
            "pack_missing_dependency",
            pack.manifest_path,
            f"pack {pack.pack_id!r} requires {requirement!r}, "
            "which is not in the selection",
        )
    return None


def _dependency_findings(by_id: dict[str, PackManifest]) -> list[dict[str, str]]:
    candidates = [
        _requirement_finding(pack, requirement, by_id)
        for pack in by_id.values()
        for requirement in pack.requires
    ]
    return [finding for finding in candidates if finding is not None]


def _conflict_findings(by_id: dict[str, PackManifest]) -> list[dict[str, str]]:
    return [
        _finding(
            "pack_conflict",
            pack.manifest_path,
            f"pack {pack.pack_id!r} declares a conflict with selected pack {rival!r}",
        )
        for pack in by_id.values()
        for rival in pack.conflicts
        if rival in by_id and rival != pack.pack_id
    ]


def validate_selection(
    manifests: Iterable[PackManifest],
) -> list[dict[str, str]]:
    """Validate an explicit selection graph before projection (FR-032)."""
    by_id, findings = _index_selection(list(manifests))
    findings.extend(_provides_collisions(by_id))
    findings.extend(_dependency_findings(by_id))
    findings.extend(_conflict_findings(by_id))
    findings.extend(_cycle_findings(by_id))
    return findings
