#!/usr/bin/env python3
"""Verify the one-way export boundary for a future Marketplace wrapper."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTION_ROOT = ROOT / "integrations" / "github-action"
REQUIRED = ("action.yml", "entrypoint.ps1", "README.md")


def _hash_required_files() -> dict[str, str]:
    files: dict[str, str] = {}
    for name in REQUIRED:
        path = ACTION_ROOT / name
        if not path.is_file():
            raise ValueError(f"missing action export source: {name}")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def _check_action_contract(action: str) -> None:
    if "seshat-version" not in action or "required: true" not in action:
        raise ValueError("action must require an immutable Seshat version")
    if "pull-requests: write" in action or "github-token" in action.lower():
        raise ValueError("action export must remain read-only and comment-free")


def verify_export_source() -> dict[str, str]:
    files = _hash_required_files()
    _check_action_contract((ACTION_ROOT / "action.yml").read_text(encoding="utf-8"))
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = {"schema_version": "1.0", "files": verify_export_source()}
    if args.output:
        output = args.output.resolve()
        allowed = (ROOT / ".seshat-output").resolve()
        if not output.is_relative_to(allowed):
            parser.error("output must be below .seshat-output")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
