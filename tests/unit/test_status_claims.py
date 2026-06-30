"""TDD tests for SC1 -- stale-marker sweep / status-claim reconciler.

SC1 reconciles a hand-curated manifest (``docs/quality/status-claims.yaml``) of prose
status CLAIMS against tracked-file evidence. Each claim names a ``doc`` + ``anchor``
(the literal sentence making the claim), a ``claimed-artifact``, and a
``claimed-status`` (``built`` | ``planned``):

* ``built``   -> the artifact MUST be a tracked file; a false ``built`` (artifact
  absent) is an ERROR.
* ``planned`` -> the artifact must NOT exist yet; a ``planned`` claim whose artifact
  is now tracked is a STALE marker (ERROR) -- the doc says planned but it shipped.

This is A1's resolver shape applied to prose claims instead of routing targets. The
manifest is parsed with a lazy ``import yaml``; a missing/malformed manifest, a
wrong-shape entry, an untracked claiming doc, or an anchor absent from the doc all
fail LOUD (never a vacuous green). SC1 is categorical (claim matches evidence or not)
-- it emits no confidence score, and it only checks claims explicitly listed in the
manifest, so it never free-scans prose.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.status_claims import _MANIFEST, check_status_claims

pytestmark = pytest.mark.unit


def _stage(
    tmp_path: Path,
    manifest_text: str,
    docs: dict[str, str] | None = None,
    artifacts: tuple[str, ...] = (),
    *,
    track_manifest: bool = True,
) -> RuleContext:
    """Write a status-claims manifest, claiming docs, and artifact files.

    ``docs`` maps a repo-relative doc path -> its full text (must contain the anchor
    for a claim that should resolve). ``artifacts`` are repo-relative paths to
    materialize + track (so a claimed-artifact can be made to resolve or not).
    """
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

    for rel in artifacts:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        tracked.append(rel)

    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


def _claim(status: str, artifact: str = "src/x.py", anchor: str = "feature X") -> str:
    return (
        "claims:\n"
        '  - id: "claim-1"\n'
        '    doc: "docs/x.md"\n'
        f'    anchor: "{anchor}"\n'
        f'    claimed-artifact: "{artifact}"\n'
        f'    claimed-status: "{status}"\n'
    )


# --- US1: stale planned marker -----------------------------------------------


def test_stale_planned_marker_fails(tmp_path: Path) -> None:
    # planned + artifact tracked + anchor present -> stale marker ERROR.
    ctx = _stage(
        tmp_path,
        _claim("planned"),
        docs={"docs/x.md": "feature X is planned for later\n"},
        artifacts=("src/x.py",),
    )
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "SC1"
    assert findings[0].severity is Severity.ERROR
    assert "src/x.py" in findings[0].message
    assert "claim-1" in findings[0].message


def test_honest_planned_yields_no_findings(tmp_path: Path) -> None:
    # planned + artifact NOT tracked + anchor present -> honest, no finding.
    ctx = _stage(
        tmp_path,
        _claim("planned"),
        docs={"docs/x.md": "feature X is planned for later\n"},
        artifacts=(),
    )
    assert list(check_status_claims(ctx)) == []


# --- US2: false built + fail-loud branches -----------------------------------


def test_honest_built_yields_no_findings(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        _claim("built"),
        docs={"docs/x.md": "feature X is built and shipped\n"},
        artifacts=("src/x.py",),
    )
    assert list(check_status_claims(ctx)) == []


def test_false_built_fails(tmp_path: Path) -> None:
    # built + artifact NOT tracked -> false built ERROR.
    ctx = _stage(
        tmp_path,
        _claim("built"),
        docs={"docs/x.md": "feature X is built and shipped\n"},
        artifacts=(),
    )
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "src/x.py" in findings[0].message


def test_missing_manifest_fails_loud(tmp_path: Path) -> None:
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert _MANIFEST in findings[0].message


def test_malformed_yaml_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "claims:\n  - id: [unbalanced\n")
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "yaml" in findings[0].message.lower()


def test_wrong_shape_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "not_claims: 1\n")
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "'claims' list" in findings[0].message


def test_non_mapping_entry_fails(tmp_path: Path) -> None:
    # A claims-list entry that is not a mapping (e.g. a bare string) -> ERROR.
    ctx = _stage(tmp_path, "claims:\n  - just_a_string\n")
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "not a mapping" in findings[0].message


def test_invalid_status_fails(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        _claim("shipped"),  # not in {built, planned}
        docs={"docs/x.md": "feature X\n"},
    )
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "invalid" in findings[0].message.lower()


def test_missing_field_fails(tmp_path: Path) -> None:
    manifest = (
        "claims:\n"
        '  - id: "claim-1"\n'
        '    doc: "docs/x.md"\n'
        '    anchor: "feature X"\n'
        '    claimed-status: "built"\n'  # no claimed-artifact
    )
    ctx = _stage(tmp_path, manifest, docs={"docs/x.md": "feature X\n"})
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "claimed-artifact" in findings[0].message


def test_untracked_doc_fails(tmp_path: Path) -> None:
    # The claiming doc is named but not tracked -> fail loud.
    ctx = _stage(tmp_path, _claim("planned"), docs=None, artifacts=())
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "docs/x.md" in findings[0].message


def test_absent_anchor_fails_loud(tmp_path: Path) -> None:
    # The anchor sentence is NOT present in the claiming doc -> stale/misplaced ERROR.
    ctx = _stage(
        tmp_path,
        _claim("planned", anchor="this exact sentence is absent"),
        docs={"docs/x.md": "totally different content\n"},
    )
    findings = list(check_status_claims(ctx))
    assert len(findings) == 1
    assert "anchor" in findings[0].message.lower()


# --- live guard ---------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_live_manifest_resolves_against_real_repo() -> None:
    """The shipped status-claims manifest reconciles clean against the real repo."""
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
    findings = list(check_status_claims(ctx))
    assert findings == [], f"live status-claims manifest has contradictions: {findings}"
