"""Classify changed paths into CI verification depths.

Human-facing text can skip browser, OS and numerical smoke jobs, but it still
drives repository contracts. Images and GitHub contribution templates need only
the always-on governance checks. Everything unknown fails closed to the full
suite.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_DOC_TEXT_SUFFIXES = {".md", ".rst", ".txt"}
_DOC_ASSET_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".svg"}
_ROOT_CONTRACT_DOCS = {
    "changelog.md",
    "code_of_conduct.md",
    "contributing.md",
    "onboarding.md",
    "readme.md",
    "release_notes.md",
    "security.md",
}


@dataclass(frozen=True, order=True)
class ChangeDepth:
    code_changed: bool
    contracts_required: bool


_METADATA_ONLY = ChangeDepth(code_changed=False, contracts_required=False)
_CONTRACTS_ONLY = ChangeDepth(code_changed=False, contracts_required=True)
_FULL_SUITE = ChangeDepth(code_changed=True, contracts_required=True)


def _classify_path(raw_path: str) -> ChangeDepth:
    path = raw_path.replace("\\", "/").lstrip("/").lower()
    suffix = Path(path).suffix

    if path == ".github/pull_request_template.md":
        return _METADATA_ONLY
    if path.startswith(".github/issue_template/"):
        if suffix == ".md":
            return _METADATA_ONLY
    if path.startswith("docs/"):
        if suffix in _DOC_ASSET_SUFFIXES:
            return _METADATA_ONLY
        if suffix in _DOC_TEXT_SUFFIXES:
            return _CONTRACTS_ONLY
    if path in _ROOT_CONTRACT_DOCS:
        return _CONTRACTS_ONLY
    return _FULL_SUITE


def classify_paths(paths: Iterable[str]) -> ChangeDepth:
    return max(
        (_classify_path(path) for path in paths if path),
        default=_FULL_SUITE,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed-files", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    paths = args.changed_files.read_text(encoding="utf-8").splitlines()
    depth = classify_paths(paths)
    print(f"code_changed={str(depth.code_changed).lower()}")
    print(f"contracts_required={str(depth.contracts_required).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
