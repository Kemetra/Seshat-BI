from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.export_agent_bundles import (
    BuildOptions,
    ExportError,
    _normalize_text,
    build_bundle,
    check_all,
    compare_bundle_trees,
    compare_shared_provenance,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_two_exports_have_identical_paths_and_bytes(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_bundle(
        ROOT,
        "claude",
        first,
        BuildOptions(source_revision="0" * 40, allow_untracked_inputs=True),
    )
    build_bundle(
        ROOT,
        "claude",
        second,
        BuildOptions(source_revision="0" * 40, allow_untracked_inputs=True),
    )
    first_files = {
        path.relative_to(first): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(second): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files


def test_pbip_adoption_router_is_identical_in_claude_and_codex_regeneration(
    tmp_path: Path, monkeypatch
) -> None:
    import scripts.export_agent_bundles as exporter

    allowlist = exporter.load_allowlist(ROOT)
    tracked = {
        str(entry["source"])
        for entry in exporter._all_entries(allowlist)
        if isinstance(entry.get("source"), str)
    }
    monkeypatch.setattr(exporter, "_git_paths", lambda _root: tracked)
    options = BuildOptions(source_revision="0" * 40, allow_untracked_inputs=True)
    claude = tmp_path / "claude"
    codex = tmp_path / "codex"
    build_bundle(ROOT, "claude", claude, options)
    build_bundle(ROOT, "codex", codex, options)
    claude_route = (claude / "skills" / "seshat-bi" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    codex_route = (codex / "skills" / "seshat-bi" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert claude_route == codex_route
    assert "seshat adopt-pbip assess" in claude_route


def test_manifest_digest_and_cross_target_provenance(tmp_path: Path) -> None:
    claude = build_bundle(
        ROOT,
        "claude",
        tmp_path / "claude",
        BuildOptions(source_revision="0" * 40, allow_untracked_inputs=True),
    )
    codex = build_bundle(
        ROOT,
        "codex",
        tmp_path / "codex",
        BuildOptions(source_revision="0" * 40, allow_untracked_inputs=True),
    )
    assert len(claude["manifest_digest"]) == 64
    compare_shared_provenance(claude, codex)
    canonical_entry = next(
        entry
        for entry in codex["entries"]
        if entry["classification"] == "public_knowledge"
    )
    canonical_entry["output_sha256"] = "f" * 64
    with pytest.raises(ExportError, match="provenance differs"):
        compare_shared_provenance(claude, codex)


def test_source_digests_use_normalized_bytes(tmp_path: Path) -> None:
    manifest = build_bundle(
        ROOT,
        "claude",
        tmp_path / "claude",
        BuildOptions(source_revision="0" * 40, allow_untracked_inputs=True),
    )
    for entry in manifest["entries"]:
        source = (ROOT / entry["source"]).read_bytes()
        expected = hashlib.sha256(_normalize_text(source)).hexdigest()
        assert entry["source_sha256"] == expected


def test_committed_bundle_check_rejects_hand_edit_or_unexpected_file(
    tmp_path: Path,
) -> None:
    expected = tmp_path / "expected"
    actual = tmp_path / "actual"
    expected.mkdir()
    actual.mkdir()
    (expected / "file.md").write_text("canonical\n", encoding="utf-8")
    (actual / "file.md").write_text("hand edit\n", encoding="utf-8")
    (actual / "unexpected.json").write_text(
        json.dumps({"purpose": "fixture"}), encoding="utf-8"
    )
    with pytest.raises(ExportError, match="unexpected.json.*file.md"):
        compare_bundle_trees(expected, actual, target="fixture")


def test_committed_bundles_match_clean_regeneration() -> None:
    try:
        check_all(ROOT, allow_untracked_inputs=True)
    except ExportError as exc:
        pytest.fail(str(exc))


def test_generated_bundle_git_attributes_force_lf() -> None:
    paths = [
        "distribution/bundle-templates/claude/.claude-plugin/plugin.json",
        "integrations/claude-code/seshat-bi/.claude-plugin/plugin.json",
        "integrations/codex/seshat-bi/.codex-plugin/plugin.json",
    ]
    result = subprocess.run(
        ["git", "check-attr", "eol", "--", *paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.splitlines() == [f"{path}: eol: lf" for path in paths]


def test_all_five_canonical_entrypoints_and_reviewed_closure_have_provenance() -> None:
    expected_roots = {
        "skills/bi-sql-knowledge/SKILL.md",
        "skills/bi-dax-knowledge/SKILL.md",
        "skills/bi-python-knowledge/SKILL.md",
        "skills/bi-bigdata-knowledge/SKILL.md",
        "skills/retail-kpi-knowledge/SKILL.md",
    }
    claude = json.loads(
        (ROOT / "integrations/claude-code/seshat-bi/bundle-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    codex = json.loads(
        (ROOT / "integrations/codex/seshat-bi/bundle-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    for manifest in (claude, codex):
        sources = {
            entry["source"]
            for entry in manifest["entries"]
            if entry["classification"] == "public_knowledge"
        }
        assert expected_roots <= sources
        for root in expected_roots:
            prefix = root.removesuffix("SKILL.md")
            assert any(source.startswith(prefix) for source in sources)
    compare_shared_provenance(claude, codex)
