from __future__ import annotations

import copy
from pathlib import Path

import pytest

from scripts.export_agent_bundles import (
    BuildOptions,
    ExportError,
    build_bundle,
    load_allowlist,
    validate_allowlist,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_repository_allowlist_has_literal_reviewed_entries() -> None:
    document = load_allowlist(ROOT)
    entries = validate_allowlist(ROOT, document, allow_untracked_inputs=True)
    assert len(entries) > 100
    assert all("*" not in str(entry["source"]) for entry in entries)


def test_canonical_roots_cannot_be_redefined_by_the_allowlist() -> None:
    document = copy.deepcopy(load_allowlist(ROOT))
    document["canonical_roots"][0] = "skills/other/SKILL.md"
    with pytest.raises(ExportError, match="five Seshat skills"):
        validate_allowlist(ROOT, document, allow_untracked_inputs=True)


@pytest.mark.parametrize("source", ["skills/**", "../secret.md", "C:/secret.md"])
def test_unsafe_source_paths_fail_closed(source: str) -> None:
    document = copy.deepcopy(load_allowlist(ROOT))
    document["entries"][0]["source"] = source
    with pytest.raises(ExportError, match="literal POSIX|escapes|drive"):
        validate_allowlist(ROOT, document, allow_untracked_inputs=True)


def test_untracked_and_symlink_inputs_fail_closed(tmp_path: Path) -> None:
    document = copy.deepcopy(load_allowlist(ROOT))
    with pytest.raises(ExportError, match="not tracked"):
        validate_allowlist(ROOT, document, tracked_paths=set())
    source = tmp_path / "source.md"
    source.write_text("safe\n", encoding="utf-8")
    link = tmp_path / "link.md"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    minimal = copy.deepcopy(document)
    minimal["entries"][0]["source"] = "link.md"
    with pytest.raises(ExportError, match="symlink"):
        validate_allowlist(
            tmp_path,
            minimal,
            tracked_paths={"link.md"},
            allow_untracked_inputs=True,
        )


def test_secret_marker_is_rejected_before_export(tmp_path: Path) -> None:
    source = (
        ROOT
        / "distribution"
        / "bundle-templates"
        / "shared"
        / "portable-operating-contract.md"
    )
    original = source.read_bytes()
    try:
        source.write_bytes(original + b"\nghp_abcdefghijklmnopqrstuvwxyz123456\n")
        with pytest.raises(ExportError, match="GitHub token"):
            build_bundle(
                ROOT,
                "claude",
                tmp_path / "bundle",
                BuildOptions(allow_untracked_inputs=True),
            )
    finally:
        source.write_bytes(original)


def test_missing_transitive_markdown_reference_fails_closed(tmp_path: Path) -> None:
    source = (
        ROOT
        / "distribution"
        / "bundle-templates"
        / "shared"
        / "portable-operating-contract.md"
    )
    original = source.read_bytes()
    try:
        source.write_bytes(original + b"\n[missing](missing-public-file.md)\n")
        with pytest.raises(ExportError, match="transitive reference"):
            build_bundle(
                ROOT,
                "codex",
                tmp_path / "bundle",
                BuildOptions(allow_untracked_inputs=True),
            )
    finally:
        source.write_bytes(original)
