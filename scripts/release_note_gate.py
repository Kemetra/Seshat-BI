"""Resolve and validate the governed release note for a stable SemVer."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_STABLE_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def governed_release_note_version(version: str) -> str:
    """Return the version token used by the governed release-note file.

    Initial minor releases preserve the historical series-note convention:
    ``0.4.0`` uses ``docs/releases/v0.4.md``. Later patch releases require an
    exact patch note: ``0.4.1`` uses ``docs/releases/v0.4.1.md``.
    """

    match = _STABLE_SEMVER.fullmatch(version)
    if match is None:
        raise ValueError(
            "version must be stable SemVer MAJOR.MINOR.PATCH without a leading v"
        )
    major, minor, patch = match.groups()
    if patch == "0":
        return f"{major}.{minor}"
    return version


def governed_release_note_path(version: str) -> Path:
    return Path("docs/releases") / f"v{governed_release_note_version(version)}.md"


def validate_release_note(repo_root: Path, version: str) -> Path:
    note_version = governed_release_note_version(version)
    note_path = governed_release_note_path(version)
    absolute_path = repo_root / note_path
    if not absolute_path.is_file():
        raise ValueError(f"missing release note: {note_path.as_posix()}")
    content = absolute_path.read_text(encoding="utf-8")
    if re.search(rf"(?m)^# .*\bv{re.escape(note_version)}(?:\b|\.)", content) is None:
        raise ValueError(
            f"release note has no v{note_version} heading: {note_path.as_posix()}"
        )
    return note_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        note_path = validate_release_note(args.repo_root, args.version)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(note_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
