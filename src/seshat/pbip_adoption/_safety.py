"""Path-containment, redaction, and fingerprint primitives for PBIP adoption.

Every value that leaves this module has already been made safe: names are
sanitized, operational prose is stripped of source literals, and paths are
proven to stay inside the selected project root.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

SCHEMA_VERSION = "1.0"
MANIFEST_PATH = ".seshat/adoption/pbip-adoption.yaml"

# Detection patterns: a boolean "does this text look like a credential or a
# literal connection detail" used to raise a governance fact.  They match only
# the key and delimiter deliberately, so detection stays broad.
_CREDENTIAL_LITERAL = re.compile(
    r"(?i)\b(?:password|passwd|pwd|token|api[_ -]?key|accountkey)\s*[=:]"
)
_CONNECTION_LITERAL = re.compile(
    r"(?i)\b(?:server|host|data[ _]?source|initial[ _]?catalog)\s*=\s*['\"]"
)
# Redaction patterns: these also consume the assigned value (quoted or bare) so
# ``_safe_detail`` removes the secret itself, not just its key.
_CREDENTIAL_REDACT = re.compile(
    r"(?i)\b(?:password|passwd|pwd|token|api[_ -]?key|accountkey)\s*[=:]\s*"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s;,]+)"
)
_CONNECTION_REDACT = re.compile(
    r"(?i)\b(?:server|host|data[ _]?source|initial[ _]?catalog)\s*=\s*"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s;,]+)"
)
_CONNECTION_URL = re.compile(
    r"(?i)(?:postgres(?:ql)?|mysql|mssql|sqlserver|snowflake)://\S+"
)
_LOCAL_PATH = re.compile(r"[A-Za-z]:[\\/][^ ]+")
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


def canonical_assessment_digest(assessment: dict[str, object]) -> str:
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
    text = _CREDENTIAL_REDACT.sub("credential=<redacted>", text)
    text = _CONNECTION_REDACT.sub("connection=<redacted>", text)
    text = _CONNECTION_URL.sub("<redacted-connection>", text)
    text = _LOCAL_PATH.sub("<redacted-path>", text)
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


def _pbix_target(supplied: Path) -> tuple[Path, bool]:
    if supplied.suffix.lower() == ".pbix":
        return supplied.resolve(), True
    raise PbipAdoptionError("project must be a PBIP directory or a .pbix file")


def _target_path(project: Path | str) -> tuple[Path, bool]:
    supplied = Path(project).expanduser()
    if not supplied.exists():
        raise PbipAdoptionError("project path does not exist")
    if supplied.is_file():
        return _pbix_target(supplied)
    if not supplied.is_dir():
        raise PbipAdoptionError("project must be a PBIP directory or a .pbix file")
    root = supplied.resolve()
    if not root.is_dir():
        raise PbipAdoptionError("project directory could not be resolved safely")
    return root, False


def _reject_unsafe_link(root: Path, path: Path) -> None:
    if path.is_symlink() and not _is_within(root, path):
        raise PbipAdoptionError(
            "project contains a linked path outside the selected root"
        )


def _reject_escaping_file(root: Path, path: Path) -> None:
    if not _is_within(root, path):
        raise PbipAdoptionError("project contains a file outside the selected root")


def _safe_files(root: Path) -> list[Path]:
    """Return ordinary files after proving each encountered link stays in root."""
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if ".git" in path.relative_to(root).parts:
            continue
        _reject_unsafe_link(root, path)
        if path.is_file():
            _reject_escaping_file(root, path)
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
