"""TDD tests for DF1 -- parked-on dependency-edge reconciler.

DF1 reconciles a hand-curated manifest (``docs/quality/parked-on.yaml``) of parked-on
edges against tracked-file evidence. Each edge: ``blocked`` + ``parked_on`` + ``doc`` +
``anchor`` (literal sentence asserting the park) + ``evidence`` (tracked file), with an
OPTIONAL ``shipped_when_tracked`` path. DF1 fails LOUD on a missing/malformed manifest,
a wrong-shape/incomplete edge, an untracked doc, an absent anchor, untracked evidence,
or a parked-but-shipped contradiction (shipped_when_tracked now tracked).

Mirrors the SC1 test pattern: synthetic generic edges, a fake RuleContext, opens
nothing. Categorical (no confidence score).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.parked_on import _MANIFEST, check_parked_on

pytestmark = pytest.mark.unit


def _stage(
    tmp_path: Path,
    manifest_text: str,
    docs: dict[str, str] | None = None,
    evidence: tuple[str, ...] = (),
    *,
    track_manifest: bool = True,
) -> RuleContext:
    tracked: list[str] = []

    mpath = tmp_path / _MANIFEST
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(manifest_text, encoding="utf-8")
    if track_manifest:
        tracked.append(_MANIFEST)

    for rel, text in (docs or {}).items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        tracked.append(rel)

    for rel in evidence:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        tracked.append(rel)

    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


def _edge(
    *,
    anchor: str = "feature Y is parked on F016",
    evidence: str = "docs/deferred.md",
    shipped: str | None = None,
) -> str:
    lines = [
        "edges:",
        '  - id: "edge-1"',
        '    blocked: "feature Y"',
        '    parked_on: "F016"',
        '    doc: "docs/roadmap.md"',
        f'    anchor: "{anchor}"',
        f'    evidence: "{evidence}"',
    ]
    if shipped is not None:
        lines.append(f'    shipped_when_tracked: "{shipped}"')
    return "\n".join(lines) + "\n"


_DOC = {"docs/roadmap.md": "feature Y is parked on F016 until later\n"}


# --- honest edge -------------------------------------------------------------


def test_honest_edge_yields_no_findings(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, _edge(), docs=_DOC, evidence=("docs/deferred.md",))
    assert list(check_parked_on(ctx)) == []


# --- parked-but-shipped contradiction (US1) ----------------------------------


def test_parked_but_shipped_fails(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        _edge(shipped="src/shipped.py"),
        docs=_DOC,
        evidence=("docs/deferred.md", "src/shipped.py"),
    )
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "DF1"
    assert findings[0].severity is Severity.ERROR
    assert "shipped" in findings[0].message.lower()


def test_shipped_signal_absent_is_honest(tmp_path: Path) -> None:
    # shipped_when_tracked declared but NOT tracked -> still honestly parked.
    ctx = _stage(
        tmp_path,
        _edge(shipped="src/shipped.py"),
        docs=_DOC,
        evidence=("docs/deferred.md",),
    )
    assert list(check_parked_on(ctx)) == []


# --- fail-loud branches (US2) ------------------------------------------------


def test_missing_manifest_fails_loud(tmp_path: Path) -> None:
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert _MANIFEST in findings[0].message


def test_tracked_but_deleted_on_disk_still_fails_loud(tmp_path: Path) -> None:
    # #430 + Codex P1: the manifest is TRACKED (`git ls-files` still lists it)
    # but deleted-but-unstaged (absent on disk). This presence-required rule must
    # emit its documented fail-closed finding -- NOT crash on the read, and NOT
    # pass vacuously by skipping.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(_MANIFEST,))
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert _MANIFEST in findings[0].message


def test_malformed_yaml_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "edges:\n  - id: [unbalanced\n")
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert "yaml" in findings[0].message.lower()


def test_wrong_shape_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "not_edges: 1\n")
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert "'edges' list" in findings[0].message


def test_non_mapping_edge_fails(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "edges:\n  - just_a_string\n")
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert "not a mapping" in findings[0].message


def test_missing_field_fails(tmp_path: Path) -> None:
    manifest = (
        "edges:\n"
        '  - id: "edge-1"\n'
        '    blocked: "feature Y"\n'
        '    parked_on: "F016"\n'
        '    doc: "docs/roadmap.md"\n'
        '    anchor: "feature Y is parked on F016"\n'  # no evidence
    )
    ctx = _stage(tmp_path, manifest, docs=_DOC)
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert "evidence" in findings[0].message


def test_untracked_doc_fails(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, _edge(), docs=None, evidence=("docs/deferred.md",))
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert "docs/roadmap.md" in findings[0].message


def test_absent_anchor_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        _edge(anchor="this exact sentence is absent"),
        docs={"docs/roadmap.md": "totally different content\n"},
        evidence=("docs/deferred.md",),
    )
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert "anchor" in findings[0].message.lower()


def test_untracked_evidence_fails(tmp_path: Path) -> None:
    # evidence path not tracked -> the park cites a nonexistent blocker record.
    ctx = _stage(tmp_path, _edge(), docs=_DOC, evidence=())
    findings = list(check_parked_on(ctx))
    assert len(findings) == 1
    assert "evidence" in findings[0].message.lower()


# --- live guard ---------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_live_manifest_resolves_against_real_repo() -> None:
    """The shipped parked-on manifest reconciles clean against the real repo."""
    repo_root = Path(__file__).resolve().parents[2]
    tracked = tuple(
        line
        for line in subprocess.run(
            ["git", "ls-files"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if line
    )
    ctx = RuleContext(repo_root=repo_root, tracked_files=tracked)
    findings = list(check_parked_on(ctx))
    assert findings == [], f"live parked-on manifest has contradictions: {findings}"
