"""Strictly inspect Seshat BI wheel/sdist artifacts and rebuild from the sdist."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from email import message_from_bytes
from email.message import Message
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

_PROHIBITED_TOP_LEVEL = {
    ".github",
    ".specify",
    "integrations",
    "specs",
    "tests",
}
_PROHIBITED_PATH_PARTS = {
    ".coverage",
    ".env",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
}
_FORBIDDEN_MANDATORY_DEPS = {
    "build",
    "mysql-connector-python",
    "openpyxl",
    "playwright",
    "psycopg2-binary",
    "pyodbc",
    "pytest",
    "ruff",
    "snowflake-connector-python",
    "testcontainers",
    "twine",
}
_CONTENT_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "credential-bearing URL": re.compile(
        rb"\b[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@", re.IGNORECASE
    ),
    "Windows user path": re.compile(rb"[A-Za-z]:\\Users\\[^\\\s]+\\"),
    "macOS user path": re.compile(rb"/Users/[^/\s]+/"),
    "client-confidential marker": re.compile(rb"\bCLIENT[ _-]CONFIDENTIAL\b", re.I),
}


class ArtifactInspectionError(ValueError):
    """A release artifact is incomplete, unsafe, or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_non_posix_archive_path(name: str) -> None:
    if "\\" in name:
        raise ArtifactInspectionError(f"archive path is not POSIX: {name}")


def _reject_archive_escape(path: PurePosixPath, name: str) -> None:
    if path.is_absolute():
        raise ArtifactInspectionError(f"archive path escapes its root: {name}")
    if ".." in path.parts:
        raise ArtifactInspectionError(f"archive path escapes its root: {name}")
    if "." in path.parts:
        raise ArtifactInspectionError(f"archive path escapes its root: {name}")


def _safe_archive_path(name: str) -> PurePosixPath:
    _reject_non_posix_archive_path(name)
    path = PurePosixPath(name)
    _reject_archive_escape(path, name)
    return path


def scan_content(name: str, data: bytes) -> None:
    """Reject strong secret, client, credential, and machine-path markers."""

    lowered_parts = {part.casefold() for part in _safe_archive_path(name).parts}
    if lowered_parts & _PROHIBITED_PATH_PARTS:
        raise ArtifactInspectionError(f"prohibited archive path: {name}")
    for label, pattern in _CONTENT_PATTERNS.items():
        if pattern.search(data):
            raise ArtifactInspectionError(f"{name} contains prohibited {label}")


def _require_wheel_package(paths: list[PurePosixPath], package: str) -> None:
    top_levels = {path.parts[0] for path in paths if path.parts}
    if package not in top_levels:
        raise ArtifactInspectionError(f"wheel is missing the {package} package")


def _reject_development_paths(paths: list[PurePosixPath]) -> None:
    top_levels = {path.parts[0] for path in paths if path.parts}
    if top_levels & _PROHIBITED_TOP_LEVEL:
        raise ArtifactInspectionError(
            "wheel contains a development-only top-level path"
        )


def _require_wheel_entry_points(names: list[str]) -> None:
    if not any(name.endswith(".dist-info/entry_points.txt") for name in names):
        raise ArtifactInspectionError("wheel is missing console entry-point metadata")


def _require_wheel_license(names: list[str]) -> None:
    if not any(".dist-info/licenses/LICENSE" in name for name in names):
        raise ArtifactInspectionError("wheel is missing the Apache-2.0 license file")


def validate_wheel_inventory(names: Iterable[str]) -> None:
    members = list(names)
    paths = [_safe_archive_path(name) for name in members]
    _require_wheel_package(paths, "seshat")
    _require_wheel_package(paths, "retail")
    _reject_development_paths(paths)
    _require_wheel_entry_points(members)
    _require_wheel_license(members)


def _stripped_sdist_paths(names: Iterable[str]) -> list[PurePosixPath]:
    paths = [_safe_archive_path(name) for name in names]
    return [PurePosixPath(*path.parts[1:]) for path in paths if len(path.parts) > 1]


def _require_sdist_core_files(stripped: list[PurePosixPath]) -> None:
    required = {"LICENSE", "README.md", "pyproject.toml"}
    observed = {path.as_posix() for path in stripped}
    missing = sorted(required - observed)
    if missing:
        raise ArtifactInspectionError(f"sdist is missing required files: {missing}")


def _require_sdist_package(stripped: list[PurePosixPath], package: str) -> None:
    prefix = package + "/"
    if not any(path.as_posix().startswith(prefix) for path in stripped):
        raise ArtifactInspectionError(f"sdist is missing {package}")


def _validate_sdist_path(path: PurePosixPath) -> None:
    if not path.parts:
        return
    allowed = "tests/fixtures/demo/demo_sample_orders.csv"
    if path.as_posix() == allowed:
        return
    if path.parts[0] in _PROHIBITED_TOP_LEVEL:
        raise ArtifactInspectionError(
            "sdist contains unrelated development/publication files"
        )


def validate_sdist_inventory(names: Iterable[str]) -> None:
    stripped = _stripped_sdist_paths(names)
    _require_sdist_core_files(stripped)
    _require_sdist_package(stripped, "src/seshat")
    _require_sdist_package(stripped, "src/retail")
    for path in stripped:
        _validate_sdist_path(path)


def _metadata_values(message: Message) -> dict[str, Any]:
    return {
        "name": message.get("Name"),
        "version": message.get("Version"),
        "summary": message.get("Summary"),
        "requires_python": message.get("Requires-Python"),
        "license_expression": message.get("License-Expression")
        or message.get("License"),
        "description_content_type": message.get("Description-Content-Type"),
        "requires_dist": sorted(message.get_all("Requires-Dist", [])),
        "project_urls": sorted(message.get_all("Project-URL", [])),
    }


def _validate_expected_metadata(metadata: Mapping[str, Any]) -> None:
    expected = {
        "name": "seshat-bi",
        "license_expression": "Apache-2.0",
        "description_content_type": "text/markdown",
    }
    for field, value in expected.items():
        if str(metadata.get(field)).casefold() != value.casefold():
            raise ArtifactInspectionError(
                f"metadata {field} is {metadata.get(field)!r}; expected {value!r}"
            )


def _validate_required_metadata(metadata: Mapping[str, Any]) -> None:
    for field in ("version", "summary", "requires_python"):
        if not metadata.get(field):
            raise ArtifactInspectionError(f"metadata field is missing: {field}")


def _validate_project_urls(metadata: Mapping[str, Any]) -> None:
    urls = "\n".join(str(value) for value in metadata["project_urls"])
    for label in ("Changelog", "Documentation", "Homepage", "Issues", "Repository"):
        if f"{label}, " not in urls:
            raise ArtifactInspectionError(f"metadata is missing project URL: {label}")


def _mandatory_dependencies(metadata: Mapping[str, Any]) -> list[str]:
    requirements = (str(value) for value in metadata["requires_dist"])
    return [
        re.split(r"[ <>=;\[]", requirement, maxsplit=1)[0].casefold()
        for requirement in requirements
        if "extra ==" not in requirement.casefold()
    ]


def _validate_dependencies(metadata: Mapping[str, Any]) -> None:
    mandatory = _mandatory_dependencies(metadata)
    forbidden = sorted(set(mandatory) & _FORBIDDEN_MANDATORY_DEPS)
    if forbidden:
        raise ArtifactInspectionError(
            f"optional/development dependencies became mandatory: {forbidden}"
        )
    if "pyyaml" not in mandatory:
        raise ArtifactInspectionError(
            "wheel metadata is missing the PyYAML runtime dependency"
        )


def _validate_metadata(metadata: dict[str, Any]) -> None:
    _validate_expected_metadata(metadata)
    _validate_required_metadata(metadata)
    _validate_project_urls(metadata)
    _validate_dependencies(metadata)


def _wheel_member(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo
) -> tuple[str, bytes] | None:
    if info.is_dir():
        return None
    mode = (info.external_attr >> 16) & 0o170000
    if mode == 0o120000:
        raise ArtifactInspectionError(f"wheel contains a symlink: {info.filename}")
    data = archive.read(info)
    scan_content(info.filename, data)
    return info.filename, data


def _wheel_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            member = _wheel_member(archive, info)
            if member is not None:
                files[member[0]] = member[1]
    return files


def _single_member(
    files: Mapping[str, bytes], suffix: str, error: str
) -> tuple[str, bytes]:
    names = [name for name in files if name.endswith(suffix)]
    if len(names) != 1:
        raise ArtifactInspectionError(error)
    name = names[0]
    return name, files[name]


def _validate_wheel_entry_points(files: Mapping[str, bytes]) -> None:
    _, raw = _single_member(
        files,
        ".dist-info/entry_points.txt",
        "wheel must contain exactly one entry_points.txt file",
    )
    entry_points = raw.decode("utf-8")
    for command in ("retail = seshat.cli:main", "seshat = seshat.cli:main"):
        if command not in entry_points:
            raise ArtifactInspectionError(f"wheel entry points are missing {command!r}")


def _read_wheel(path: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    files = _wheel_files(path)
    validate_wheel_inventory(files)
    _, metadata_bytes = _single_member(
        files,
        ".dist-info/METADATA",
        "wheel must contain exactly one METADATA file",
    )
    metadata = _metadata_values(message_from_bytes(metadata_bytes))
    _validate_metadata(metadata)
    _validate_wheel_entry_points(files)
    return files, metadata


def _reject_sdist_links(member: tarfile.TarInfo) -> None:
    if member.issym():
        raise ArtifactInspectionError(f"sdist contains a link: {member.name}")
    if member.islnk():
        raise ArtifactInspectionError(f"sdist contains a link: {member.name}")


def _require_regular_sdist_file(member: tarfile.TarInfo) -> None:
    if not member.isfile():
        raise ArtifactInspectionError(f"sdist contains a special file: {member.name}")


def _read_sdist_member(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    extracted = archive.extractfile(member)
    if extracted is None:
        raise ArtifactInspectionError(f"cannot read sdist member: {member.name}")
    return extracted.read()


def _sdist_member(
    archive: tarfile.TarFile, member: tarfile.TarInfo
) -> tuple[str, bytes] | None:
    _safe_archive_path(member.name)
    _reject_sdist_links(member)
    if member.isdir():
        return None
    _require_regular_sdist_file(member)
    data = _read_sdist_member(archive, member)
    scan_content(member.name, data)
    return member.name, data


def _sdist_files(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            extracted = _sdist_member(archive, member)
            if extracted is not None:
                files[extracted[0]] = extracted[1]
    return files


def _read_sdist(path: Path) -> tuple[dict[str, bytes], dict[str, Any]]:
    files = _sdist_files(path)
    validate_sdist_inventory(files)
    _, metadata_bytes = _single_member(
        files, "/PKG-INFO", "sdist must contain exactly one root PKG-INFO"
    )
    metadata = _metadata_values(message_from_bytes(metadata_bytes))
    _validate_metadata(metadata)
    return files, metadata


def _compare_normalized_wheels(original: Path, rebuilt: Path) -> None:
    first, first_metadata = _read_wheel(original)
    second, second_metadata = _read_wheel(rebuilt)
    if first_metadata != second_metadata:
        raise ArtifactInspectionError("rebuilt wheel metadata differs from original")

    def normalized(files: dict[str, bytes]) -> dict[str, bytes]:
        return {
            name: data
            for name, data in files.items()
            if not name.endswith((".dist-info/RECORD", ".dist-info/WHEEL"))
        }

    if normalized(first) != normalized(second):
        raise ArtifactInspectionError(
            "rebuilt wheel governed contents differ from original"
        )


def _artifact_pair(dist_dir: Path) -> tuple[Path, Path]:
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1:
        raise ArtifactInspectionError("expected exactly one wheel and one sdist")
    if len(sdists) != 1:
        raise ArtifactInspectionError("expected exactly one wheel and one sdist")
    return wheels[0], sdists[0]


def _run_twine_check(wheel: Path, sdist: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "twine",
            "check",
            "--strict",
            str(wheel),
            str(sdist),
        ],
        check=True,
    )


def _matching_metadata(wheel: Path, sdist: Path) -> dict[str, Any]:
    _, wheel_metadata = _read_wheel(wheel)
    _, sdist_metadata = _read_sdist(sdist)
    if wheel_metadata != sdist_metadata:
        raise ArtifactInspectionError("wheel and sdist core metadata differ")
    return wheel_metadata


def _rebuild_sdist(wheel: Path, sdist: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="seshat-sdist-rebuild-") as temp:
        rebuilt_dir = Path(temp)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--outdir",
                str(rebuilt_dir),
                str(sdist),
            ],
            check=True,
        )
        rebuilt = sorted(rebuilt_dir.glob("*.whl"))
        if len(rebuilt) != 1:
            raise ArtifactInspectionError(
                "sdist rebuild did not produce exactly one wheel"
            )
        _compare_normalized_wheels(wheel, rebuilt[0])


def inspect_release_artifacts(
    dist_dir: Path,
    *,
    run_twine: bool = True,
    rebuild_sdist: bool = True,
) -> dict[str, Any]:
    """Inspect exactly one wheel and sdist, returning sanitized evidence."""

    wheel, sdist = _artifact_pair(dist_dir)
    if run_twine:
        _run_twine_check(wheel, sdist)
    wheel_metadata = _matching_metadata(wheel, sdist)
    if rebuild_sdist:
        _rebuild_sdist(wheel, sdist)
    return {
        "schema_version": "1.0",
        "status": "pass",
        "version": wheel_metadata["version"],
        "artifacts": [
            {"filename": wheel.name, "sha256": _sha256(wheel), "kind": "wheel"},
            {"filename": sdist.name, "sha256": _sha256(sdist), "kind": "sdist"},
        ],
        "twine_strict": "pass" if run_twine else "not_requested",
        "isolated_sdist_rebuild": "pass" if rebuild_sdist else "not_requested",
        "authority_disclaimer": "Artifact validation does not authorize publication.",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-twine", action="store_true")
    parser.add_argument("--skip-rebuild", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = inspect_release_artifacts(
            args.dist,
            run_twine=not args.skip_twine,
            rebuild_sdist=not args.skip_rebuild,
        )
    except (ArtifactInspectionError, OSError, subprocess.CalledProcessError) as exc:
        print(
            json.dumps({"status": "blocked", "blocking_reasons": [str(exc)]}, indent=2)
        )
        return 1
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
