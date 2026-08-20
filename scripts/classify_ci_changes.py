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


@dataclass(frozen=True)
class ChangeDepth:
    code_changed: bool
    contracts_required: bool


def classify_paths(paths: Iterable[str]) -> ChangeDepth:
    normalized = [path.replace("\\", "/").lstrip("/") for path in paths if path]
    if not normalized:
        return ChangeDepth(code_changed=True, contracts_required=True)

    contracts_required = False
    for path in normalized:
        lower = path.lower()
        suffix = Path(lower).suffix

        if lower == ".github/pull_request_template.md" or (
            lower.startswith(".github/issue_template/") and suffix == ".md"
        ):
            continue
        if lower.startswith("docs/") and suffix in _DOC_ASSET_SUFFIXES:
            continue
        if (
            lower.startswith("docs/") and suffix in _DOC_TEXT_SUFFIXES
        ) or lower in _ROOT_CONTRACT_DOCS:
            contracts_required = True
            continue

        return ChangeDepth(code_changed=True, contracts_required=True)

    return ChangeDepth(
        code_changed=False,
        contracts_required=contracts_required,
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
