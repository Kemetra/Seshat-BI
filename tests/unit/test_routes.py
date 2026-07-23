"""TDD tests for A1 -- route registry resolution.

A1 reads `docs/routing/routes.yaml` and fails the gate when a route's contract
is broken: a `built` target that does not resolve, or a `planned` target that
now exists (stale marker). The manifest is parsed via a lazy `import yaml`, so a
malformed/missing manifest fails loud rather than passing vacuously.

The synthetic-manifest tests stage a manifest under tmp_path; the last test
guards the LIVE manifest against the real repo so the shipped routes.yaml is
proven to resolve end-to-end.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.routes import _MANIFEST, check_routes_resolve

pytestmark = pytest.mark.unit


def _stage(
    tmp_path: Path, manifest_text: str, extra_files: tuple[str, ...] = ()
) -> RuleContext:
    """Write a manifest at tmp_path/_MANIFEST and return a context tracking it.

    ``extra_files`` are additional repo-relative paths to mark as tracked (and
    materialize on disk) so route targets can be made to resolve or not.
    """
    manifest_path = tmp_path / _MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest_text, encoding="utf-8")

    tracked = [_MANIFEST]
    for rel in extra_files:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
        tracked.append(rel)

    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


def test_built_route_with_resolving_target_passes(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        "routes:\n"
        '  - id: "1"\n'
        '    task: "x"\n'
        '    targets: ["skills/a/SKILL.md"]\n'
        "    status: built\n",
        extra_files=("skills/a/SKILL.md",),
    )
    assert list(check_routes_resolve(ctx)) == []


def test_built_route_with_missing_target_fails(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        "routes:\n"
        '  - id: "1"\n'
        '    task: "x"\n'
        '    targets: ["skills/a/MISSING.md"]\n'
        "    status: built\n",
    )
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "A1"
    assert findings[0].severity is Severity.ERROR
    assert "MISSING.md" in findings[0].message
    assert "broken" in findings[0].message.lower()


def test_seed_route_with_resolving_target_passes(tmp_path: Path) -> None:
    # A 'seed' target that EXISTS passes -- seed means "exists but is an initial
    # cut"; the only mechanical guarantee (like built) is existence.
    ctx = _stage(
        tmp_path,
        "routes:\n"
        '  - id: "1"\n'
        '    task: "x"\n'
        '    targets: ["skills/a/SKILL.md"]\n'
        "    status: seed\n",
        extra_files=("skills/a/SKILL.md",),
    )
    assert list(check_routes_resolve(ctx)) == []


def test_seed_route_with_missing_target_fails(tmp_path: Path) -> None:
    # A 'seed' route whose target does not exist is broken, exactly like 'built'.
    ctx = _stage(
        tmp_path,
        "routes:\n"
        '  - id: "1"\n'
        '    task: "x"\n'
        '    targets: ["skills/a/MISSING.md"]\n'
        "    status: seed\n",
    )
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "A1"
    assert findings[0].severity is Severity.ERROR
    assert "MISSING.md" in findings[0].message
    assert "broken" in findings[0].message.lower()


def test_seed_route_with_no_targets_fails(tmp_path: Path) -> None:
    # A 'seed' route pointing at nothing fails, never passes vacuously.
    ctx = _stage(
        tmp_path,
        'routes:\n  - id: "1"\n    task: "x"\n    targets: []\n    status: seed\n',
    )
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "A1"
    assert "no targets" in findings[0].message.lower()


def test_planned_route_with_unresolved_target_passes(tmp_path: Path) -> None:
    # A planned target that does NOT resolve yet is the honest deferral.
    ctx = _stage(
        tmp_path,
        "routes:\n"
        '  - id: "99"\n'
        '    task: "future"\n'
        '    targets: ["skills/future/SKILL.md"]\n'
        "    status: planned\n",
    )
    assert list(check_routes_resolve(ctx)) == []


def test_planned_route_with_existing_target_fails_as_stale(tmp_path: Path) -> None:
    # The file got built but the manifest still says planned -> stale marker.
    ctx = _stage(
        tmp_path,
        "routes:\n"
        '  - id: "99"\n'
        '    task: "future"\n'
        '    targets: ["skills/future/SKILL.md"]\n'
        "    status: planned\n",
        extra_files=("skills/future/SKILL.md",),
    )
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert "stale" in findings[0].message.lower()
    assert "built" in findings[0].message.lower()


def test_non_dict_route_entry_fails(tmp_path: Path) -> None:
    # A routes list entry that is not a mapping (e.g. a bare string).
    ctx = _stage(tmp_path, 'routes:\n  - "not-a-dict"\n')
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert "not a mapping" in findings[0].message


def test_non_list_targets_fails(tmp_path: Path) -> None:
    # `targets` given as a bare string instead of a list.
    ctx = _stage(
        tmp_path,
        "routes:\n"
        '  - id: "1"\n'
        '    task: "x"\n'
        '    targets: "skills/a/SKILL.md"\n'
        "    status: built\n",
    )
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert "'targets' must be a list" in findings[0].message


def test_built_route_with_no_targets_fails(tmp_path: Path) -> None:
    # A 'built' route that lists nothing points at nothing -> not a vacuous pass.
    ctx = _stage(
        tmp_path,
        'routes:\n  - id: "1"\n    task: "x"\n    targets: []\n    status: built\n',
    )
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert "no targets" in findings[0].message.lower()


def test_invalid_status_fails(tmp_path: Path) -> None:
    ctx = _stage(
        tmp_path,
        'routes:\n  - id: "1"\n    task: "x"\n    targets: []\n    status: maybe\n',
    )
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert "invalid status" in findings[0].message.lower()


def test_malformed_yaml_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "routes:\n  - id: [unbalanced\n")
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert "yaml" in findings[0].message.lower()


def test_manifest_not_a_routes_mapping_fails(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "not_routes: 1\n")
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert "'routes' list" in findings[0].message


def test_missing_manifest_fails_loud(tmp_path: Path) -> None:
    # No manifest tracked at all -> the gate must not pass vacuously.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert _MANIFEST in findings[0].message
    assert (
        "missing" in findings[0].message.lower()
        or "untracked" in findings[0].message.lower()
    )


def test_tracked_but_deleted_on_disk_still_fails_loud(tmp_path: Path) -> None:
    # #430 + Codex P1: TRACKED (listed by `git ls-files`) but deleted-but-unstaged
    # -> the presence-required gate must emit its fail-closed finding, not crash
    # and not pass vacuously.
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(_MANIFEST,))
    findings = list(check_routes_resolve(ctx))
    assert len(findings) == 1
    assert _MANIFEST in findings[0].message


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_live_manifest_resolves_against_real_repo() -> None:
    """The shipped routes.yaml must resolve end-to-end against the real repo.

    This is the production guard: every `built` route in the committed manifest
    points at a real tracked file, and no `planned` route is stale. It shells out
    to ``git ls-files`` (skipped when git is unavailable) — closest to how the
    rule runs under ``retail check`` in CI.
    """
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
    findings = list(check_routes_resolve(ctx))
    assert findings == [], f"live route manifest has unresolved routes: {findings}"
