"""Deterministically export reviewed Seshat knowledge for Claude Code and Codex."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import yaml

EXPORTER_VERSION = "1.0"
TARGET_ROOTS = {
    "claude": Path("integrations/claude-code/seshat-bi"),
    "codex": Path("integrations/codex/seshat-bi"),
}
CANONICAL_ROOTS = frozenset(
    {
        "skills/bi-sql-knowledge/SKILL.md",
        "skills/bi-dax-knowledge/SKILL.md",
        "skills/bi-python-knowledge/SKILL.md",
        "skills/bi-bigdata-knowledge/SKILL.md",
        "skills/retail-kpi-knowledge/SKILL.md",
    }
)
ALLOWED_MEDIA_TYPES = {
    "application/json",
    "application/yaml",
    "text/markdown",
    "text/plain",
}
ALLOWED_TRANSFORMS = {"copy-normalized-v1", "template-substitute-version-v1"}
_REFERENCE_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential-bearing URL": re.compile(
        r"\b[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@", re.IGNORECASE
    ),
    "Windows user path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
    "macOS user path": re.compile(r"/Users/[^/\s]+/"),
    "client-confidential marker": re.compile(r"\bCLIENT[ _-]CONFIDENTIAL\b", re.I),
}


class ExportError(ValueError):
    """An allowlist or generated bundle violates the public export contract."""


@dataclass
class _AllowlistState:
    tracked: set[str]
    allow_untracked_inputs: bool
    seen_ids: set[str] = field(default_factory=set)
    seen_sources: set[str] = field(default_factory=set)
    destinations: dict[str, set[str]] = field(
        default_factory=lambda: {target: set() for target in TARGET_ROOTS}
    )


@dataclass(frozen=True)
class BuildOptions:
    source_revision: str | None = None
    allow_untracked_inputs: bool = False


@dataclass(frozen=True)
class _BundleContext:
    repo_root: Path
    target: str
    output_root: Path
    version: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _normalize_text(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExportError("allowlisted public files must be UTF-8 text") from exc
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"
    return normalized.encode("utf-8")


def _path_text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ExportError(f"{label} must be a non-empty repository-relative path")
    if not value:
        raise ExportError(f"{label} must be a non-empty repository-relative path")
    return value


def _reject_path_metacharacters(value: str, label: str) -> None:
    if "\\" in value:
        raise ExportError(f"{label} must be a literal POSIX path: {value!r}")
    if "*" in value:
        raise ExportError(f"{label} must be a literal POSIX path: {value!r}")
    if "?" in value:
        raise ExportError(f"{label} must be a literal POSIX path: {value!r}")


def _reject_path_escape(path: PurePosixPath, value: str, label: str) -> None:
    if path.is_absolute():
        raise ExportError(f"{label} escapes its allowed root: {value!r}")
    if ".." in path.parts:
        raise ExportError(f"{label} escapes its allowed root: {value!r}")
    if "." in path.parts:
        raise ExportError(f"{label} escapes its allowed root: {value!r}")


def _reject_drive_prefix(path: PurePosixPath, value: str, label: str) -> None:
    if not path.parts:
        return
    if ":" in path.parts[0]:
        raise ExportError(f"{label} contains a drive prefix: {value!r}")


def _safe_relative_path(value: object, *, label: str) -> str:
    text = _path_text(value, label)
    _reject_path_metacharacters(text, label)
    path = PurePosixPath(text)
    _reject_path_escape(path, text, label)
    _reject_drive_prefix(path, text, label)
    return text


def _git_paths(repo_root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return {part.decode("utf-8") for part in result.stdout.split(b"\0") if part}


def _git_revision(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _project_version(repo_root: Path) -> str:
    document = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    return str(document["project"]["version"])


def load_allowlist(repo_root: Path, path: Path | None = None) -> dict[str, Any]:
    source = path or repo_root / "distribution" / "public-knowledge-allowlist.yaml"
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ExportError("public knowledge allowlist must be a YAML object")
    return document


def _entry_mapping(entry: object, section: str) -> Mapping[str, Any]:
    if not isinstance(entry, Mapping):
        raise ExportError(f"{section} entries must be objects")
    return entry


def _section_entries(
    document: Mapping[str, Any], section: str
) -> list[Mapping[str, Any]]:
    value = document.get(section)
    if not isinstance(value, list):
        raise ExportError(f"{section} must be a list")
    return [_entry_mapping(entry, section) for entry in value]


def _all_entries(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _section_entries(document, "entries") + _section_entries(
        document, "template_entries"
    )


def _validate_allowlist_identity(document: Mapping[str, Any]) -> None:
    if document.get("schema_version") != 1:
        raise ExportError("allowlist schema_version must be 1")
    if document.get("canonical_repository") != "ahmed-shaaban-94/Seshat_BI":
        raise ExportError("allowlist canonical_repository is not Seshat_BI")


def _canonical_root_values(document: Mapping[str, Any]) -> list[object]:
    roots = document.get("canonical_roots")
    if not isinstance(roots, list):
        raise ExportError("allowlist must declare the five canonical entrypoints")
    if len(roots) != 5:
        raise ExportError("allowlist must declare the five canonical entrypoints")
    return roots


def _validate_allowlist_header(document: Mapping[str, Any]) -> set[str]:
    _validate_allowlist_identity(document)
    root_set = {
        _safe_relative_path(item, label="canonical root")
        for item in _canonical_root_values(document)
    }
    if root_set != CANONICAL_ROOTS:
        raise ExportError("allowlist canonical_roots must match the five Seshat skills")
    return root_set


def _unique_entry_id(entry: Mapping[str, Any], state: _AllowlistState) -> str:
    entry_id = entry.get("entry_id", entry.get("template_id"))
    if not isinstance(entry_id, str):
        raise ExportError("every allowlist/template entry needs a unique stable ID")
    if not entry_id:
        raise ExportError("every allowlist/template entry needs a unique stable ID")
    if entry_id in state.seen_ids:
        raise ExportError("every allowlist/template entry needs a unique stable ID")
    state.seen_ids.add(entry_id)
    return entry_id


def _path_contains_symlink(repo_root: Path, source: str) -> bool:
    cursor = repo_root
    for part in PurePosixPath(source).parts:
        cursor /= part
        if cursor.is_symlink():
            return True
    return False


def _require_source_tracked(source: str, state: _AllowlistState) -> None:
    if source in state.tracked:
        return
    if not state.allow_untracked_inputs:
        raise ExportError(f"allowlisted source is not tracked by Git: {source}")


def _validate_source(
    repo_root: Path,
    entry: Mapping[str, Any],
    entry_id: str,
    state: _AllowlistState,
) -> str:
    source = _safe_relative_path(entry.get("source"), label=f"{entry_id} source")
    if source in state.seen_sources:
        raise ExportError(f"duplicate allowlisted source: {source}")
    state.seen_sources.add(source)
    source_path = repo_root / Path(source)
    if not source_path.is_file():
        raise ExportError(f"allowlisted source is missing or not a file: {source}")
    if _path_contains_symlink(repo_root, source):
        raise ExportError(f"allowlisted symlinks are prohibited: {source}")
    _require_source_tracked(source, state)
    return source


def _require_allowed_entry_value(
    entry: Mapping[str, Any], field: str, allowed: set[str], error: str
) -> None:
    if entry.get(field) not in allowed:
        raise ExportError(error)


def _require_entry_is_required(entry_id: str, entry: Mapping[str, Any]) -> None:
    if entry.get("required") is not True:
        raise ExportError(f"{entry_id} must explicitly be required")


def _require_review_reason(entry_id: str, entry: Mapping[str, Any]) -> None:
    review_reason = entry.get("review_reason")
    if not isinstance(review_reason, str):
        raise ExportError(f"{entry_id} requires a public review reason")
    if not review_reason.strip():
        raise ExportError(f"{entry_id} requires a public review reason")


def _validate_entry_policy(entry_id: str, entry: Mapping[str, Any]) -> None:
    _require_allowed_entry_value(
        entry,
        "classification",
        {"generated_wrapper", "public_knowledge", "public_license"},
        f"{entry_id} has an unreviewed classification",
    )
    _require_allowed_entry_value(
        entry,
        "media_type",
        ALLOWED_MEDIA_TYPES,
        f"{entry_id} has a prohibited media type",
    )
    _require_allowed_entry_value(
        entry,
        "transform",
        ALLOWED_TRANSFORMS,
        f"{entry_id} has an unknown transform",
    )
    _require_entry_is_required(entry_id, entry)
    _require_review_reason(entry_id, entry)


def _record_destination(
    entry_id: str,
    target: object,
    destination_value: object,
    state: _AllowlistState,
) -> None:
    if target not in TARGET_ROOTS:
        raise ExportError(f"{entry_id} names unsupported target {target!r}")
    destination = _safe_relative_path(
        destination_value, label=f"{entry_id} {target} destination"
    )
    if destination in state.destinations[target]:
        raise ExportError(f"two sources collide at {target}/{destination}")
    state.destinations[target].add(destination)


def _record_destinations(
    entry_id: str, entry: Mapping[str, Any], state: _AllowlistState
) -> None:
    targets = entry.get("targets")
    if not isinstance(targets, Mapping):
        raise ExportError(f"{entry_id} requires at least one target")
    if not targets:
        raise ExportError(f"{entry_id} requires at least one target")
    for target, destination_value in targets.items():
        _record_destination(entry_id, target, destination_value, state)


def validate_allowlist(
    repo_root: Path,
    document: Mapping[str, Any],
    *,
    tracked_paths: set[str] | None = None,
    allow_untracked_inputs: bool = False,
) -> list[Mapping[str, Any]]:
    """Validate and return the stable list of reviewed allowlist entries."""

    root_set = _validate_allowlist_header(document)
    tracked = tracked_paths if tracked_paths is not None else _git_paths(repo_root)
    entries = _all_entries(document)
    state = _AllowlistState(
        tracked=tracked, allow_untracked_inputs=allow_untracked_inputs
    )
    for entry in entries:
        entry_id = _unique_entry_id(entry, state)
        _validate_source(repo_root, entry, entry_id, state)
        _validate_entry_policy(entry_id, entry)
        _record_destinations(entry_id, entry, state)
    if not root_set.issubset(state.seen_sources):
        missing = sorted(root_set - state.seen_sources)
        raise ExportError(f"canonical entrypoints are not allowlisted: {missing}")
    return sorted(
        entries, key=lambda item: str(item.get("entry_id", item.get("template_id")))
    )


def _scan_public_content(source: str, data: bytes) -> None:
    text = data.decode("utf-8")
    for label, pattern in _SECRET_PATTERNS.items():
        if pattern.search(text):
            raise ExportError(f"{source} contains prohibited {label} content")


def _render_entry(
    repo_root: Path, entry: Mapping[str, Any], *, version: str
) -> tuple[bytes, str]:
    source = str(entry["source"])
    raw = (repo_root / Path(source)).read_bytes()
    normalized_source = _normalize_text(raw)
    _scan_public_content(source, normalized_source)
    rendered = normalized_source
    transform = str(entry["transform"])
    if transform == "template-substitute-version-v1":
        rendered = rendered.replace(b"{{VERSION}}", version.encode("utf-8"))
        if b"{{" in rendered:
            raise ExportError(f"unresolved template marker in {source}")
        if b"}}" in rendered:
            raise ExportError(f"unresolved template marker in {source}")
    return rendered, _sha256(normalized_source)


def _is_external_reference(reference: str) -> bool:
    if not reference:
        return True
    return reference.startswith(("#", "http://", "https://", "mailto:"))


def _reject_unsafe_reference(path: Path, reference: str) -> None:
    if reference.startswith("/"):
        raise ExportError(f"unsafe Markdown reference in {path}: {reference}")
    if "\\" in reference:
        raise ExportError(f"unsafe Markdown reference in {path}: {reference}")


def _resolve_bundle_reference(bundle_root: Path, path: Path, reference: str) -> Path:
    resolved = (path.parent / reference).resolve()
    try:
        resolved.relative_to(bundle_root.resolve())
    except ValueError as exc:
        raise ExportError(
            f"Markdown reference escapes generated bundle in {path}: {reference}"
        ) from exc
    return resolved


def _require_reference_exists(resolved: Path, path: Path, reference: str) -> None:
    if not resolved.exists():
        raise ExportError(
            f"unlisted or missing transitive reference in {path}: {reference}"
        )


def _validate_reference(bundle_root: Path, path: Path, reference: str) -> None:
    _reject_unsafe_reference(path, reference)
    resolved = _resolve_bundle_reference(bundle_root, path, reference)
    _require_reference_exists(resolved, path, reference)


def _validate_markdown_links(bundle_root: Path, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for match in _REFERENCE_RE.finditer(text):
        reference = match.group(1).split("#", 1)[0].strip()
        if not _is_external_reference(reference):
            _validate_reference(bundle_root, path, reference)


def _validate_links(bundle_root: Path) -> None:
    for path in bundle_root.rglob("*.md"):
        _validate_markdown_links(bundle_root, path)


def _prepare_output_root(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)


def _write_bundle_entry(
    context: _BundleContext, entry: Mapping[str, Any]
) -> dict[str, str] | None:
    targets = entry["targets"]
    if context.target not in targets:
        return None
    destination = str(targets[context.target])
    data, source_digest = _render_entry(
        context.repo_root, entry, version=context.version
    )
    output = context.output_root / Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {
        "classification": str(entry["classification"]),
        "destination": destination,
        "output_sha256": _sha256(data),
        "source": str(entry["source"]),
        "source_id": str(entry.get("entry_id", entry.get("template_id"))),
        "source_sha256": source_digest,
        "transform": str(entry["transform"]),
    }


def _manifest_entries(
    context: _BundleContext, entries: Iterable[Mapping[str, Any]]
) -> list[dict[str, str]]:
    manifest_entries: list[dict[str, str]] = []
    for entry in entries:
        rendered = _write_bundle_entry(context, entry)
        if rendered is not None:
            manifest_entries.append(rendered)
    return manifest_entries


def build_bundle(
    repo_root: Path,
    target: str,
    output_root: Path,
    options: BuildOptions | None = None,
) -> dict[str, Any]:
    """Build one target bundle and return its deterministic manifest."""

    if target not in TARGET_ROOTS:
        raise ExportError(f"unsupported target: {target}")
    resolved_options = options or BuildOptions()
    entries = validate_allowlist(
        repo_root,
        load_allowlist(repo_root),
        allow_untracked_inputs=resolved_options.allow_untracked_inputs,
    )
    version = _project_version(repo_root)
    _prepare_output_root(output_root)
    context = _BundleContext(repo_root, target, output_root, version)
    manifest_entries = _manifest_entries(context, entries)
    _validate_links(output_root)
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "exporter_version": EXPORTER_VERSION,
        "target": target,
        "plugin": "seshat-bi",
        "version": version,
        "source_revision": resolved_options.source_revision or _git_revision(repo_root),
        "entries": sorted(manifest_entries, key=lambda item: item["destination"]),
    }
    payload["manifest_digest"] = _sha256(_canonical_json(payload))
    (output_root / "bundle-manifest.json").write_bytes(
        json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    return payload


def _tree_bytes(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def compare_bundle_trees(
    expected_root: Path, actual_root: Path, *, target: str
) -> None:
    """Fail with stable details for missing, unexpected, or hand-edited files."""

    expected = _tree_bytes(expected_root)
    actual = _tree_bytes(actual_root)
    if expected == actual:
        return
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    changed = sorted(
        path for path in set(expected) & set(actual) if expected[path] != actual[path]
    )
    raise ExportError(
        "generated bundle drift for "
        f"{target}: missing={missing}, unexpected={unexpected}, changed={changed}"
    )


def compare_shared_provenance(
    claude_manifest: Mapping[str, Any], codex_manifest: Mapping[str, Any]
) -> None:
    """Require identical canonical digests across both platform projections."""

    def canonical(manifest: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
        result: dict[str, tuple[str, str]] = {}
        for entry in manifest.get("entries", []):
            if entry.get("classification") in {"public_knowledge", "public_license"}:
                result[str(entry["source"])] = (
                    str(entry["source_sha256"]),
                    str(entry["output_sha256"]),
                )
        return result

    if canonical(claude_manifest) != canonical(codex_manifest):
        raise ExportError("Claude and Codex canonical provenance differs")


def export_all(repo_root: Path, *, allow_untracked_inputs: bool = False) -> None:
    """Regenerate both committed platform bundles from reviewed inputs."""

    manifests: dict[str, Mapping[str, Any]] = {}
    for target, relative_root in TARGET_ROOTS.items():
        manifests[target] = build_bundle(
            repo_root,
            target,
            repo_root / relative_root,
            BuildOptions(allow_untracked_inputs=allow_untracked_inputs),
        )
    compare_shared_provenance(manifests["claude"], manifests["codex"])


def check_all(repo_root: Path, *, allow_untracked_inputs: bool = False) -> None:
    """Fail if a clean regeneration differs from either committed bundle."""

    manifests: dict[str, Mapping[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="seshat-bundle-check-") as temp:
        temp_root = Path(temp)
        for target, relative_root in TARGET_ROOTS.items():
            existing_root = repo_root / relative_root
            existing_manifest_path = existing_root / "bundle-manifest.json"
            source_revision = None
            if existing_manifest_path.exists():
                existing_manifest = json.loads(
                    existing_manifest_path.read_text(encoding="utf-8")
                )
                source_revision = existing_manifest.get("source_revision")
            generated_root = temp_root / target
            manifests[target] = build_bundle(
                repo_root,
                target,
                generated_root,
                BuildOptions(
                    source_revision=source_revision,
                    allow_untracked_inputs=allow_untracked_inputs,
                ),
            )
            compare_bundle_trees(generated_root, existing_root, target=target)
        compare_shared_provenance(manifests["claude"], manifests["codex"])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--allow-untracked-inputs",
        action="store_true",
        help="development-only: permit newly authored inputs before their first commit",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo.resolve()
    try:
        if args.check:
            check_all(repo_root, allow_untracked_inputs=args.allow_untracked_inputs)
        else:
            export_all(repo_root, allow_untracked_inputs=args.allow_untracked_inputs)
    except (ExportError, OSError, subprocess.CalledProcessError, KeyError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print("PASS: generated Claude and Codex bundles match reviewed inputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
