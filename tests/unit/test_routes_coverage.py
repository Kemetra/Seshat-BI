"""TDD tests for A3 -- route-registry coverage reconciler.

A3 verifies a bijection: the id set of the knowledge map's "Route by task" table
equals the id set of the routing manifest (``docs/routing/routes.yaml``). Drift in
either direction is an ERROR; an unreadable input (missing/untracked manifest,
malformed YAML, wrong shape, or an unlocatable map table) fails LOUD rather than
passing vacuously. The bijection holds on the real repo today, so the live guard
at the bottom proves the shipped map+manifest are in bijection end-to-end.

A3 is the sibling of A1 (``routes.py``): same rule contract, same lazy ``import
yaml``, same fail-loud posture. A1 validates manifest targets resolve; A3 validates
the map<->manifest id boundary that A1 never reads.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.routes_coverage import _MANIFEST, _MAP, check_route_coverage

pytestmark = pytest.mark.unit


def _stage(
    tmp_path: Path,
    map_ids: tuple[str, ...] | None,
    manifest_text: str | None,
    *,
    map_text: str | None = None,
    track_manifest: bool = True,
    track_map: bool = True,
) -> RuleContext:
    """Stage a synthetic knowledge-map + routing manifest under tmp_path.

    ``map_ids`` builds a minimal "Route by task" table with those leading ids
    (generic ids only). Pass ``map_text`` to write raw map content instead (e.g.
    a map with no "Route by task" section). ``manifest_text`` is written verbatim
    as routes.yaml. ``track_*`` flags control whether each file is marked tracked.
    """
    tracked: list[str] = []

    if map_text is None and map_ids is not None:
        rows = "\n".join(f"| {mid}. Task {mid} | Route | `x` | y |" for mid in map_ids)
        map_text = (
            "# Knowledge map\n\n"
            "## Route by task\n\n"
            "| Task | Route | Open first | End on |\n"
            "|---|---|---|---|\n"
            f"{rows}\n\n"
            "## Route by symptom\n\n"
            "| 999. Should be ignored | Route | `z` | w |\n"
        )
    if map_text is not None:
        p = tmp_path / _MAP
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(map_text, encoding="utf-8")
        if track_map:
            tracked.append(_MAP)

    if manifest_text is not None:
        p = tmp_path / _MANIFEST
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(manifest_text, encoding="utf-8")
        if track_manifest:
            tracked.append(_MANIFEST)

    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


def _manifest_with(ids: tuple[str, ...]) -> str:
    body = "".join(f'  - id: "{i}"\n    status: planned\n' for i in ids)
    return "routes:\n" + body


# --- US1: drift between map and manifest fails the gate -----------------------


def test_bijection_holds_yields_no_findings(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, ("1", "2", "99"), _manifest_with(("1", "2", "99")))
    assert list(check_route_coverage(ctx)) == []


def test_map_id_missing_from_manifest_fails(tmp_path: Path) -> None:
    # Map has "2"; manifest lacks it.
    ctx = _stage(tmp_path, ("1", "2"), _manifest_with(("1",)))
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "A3"
    assert findings[0].severity is Severity.ERROR
    assert "2" in findings[0].message
    msg = findings[0].message.lower()
    assert "map" in msg and "manifest" in msg


def test_manifest_id_missing_from_map_fails(tmp_path: Path) -> None:
    # Manifest has "2"; map lacks it.
    ctx = _stage(tmp_path, ("1",), _manifest_with(("1", "2")))
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "A3"
    assert "2" in findings[0].message
    msg = findings[0].message.lower()
    assert "manifest" in msg and "map" in msg


def test_sublettered_ids_compare_exactly(tmp_path: Path) -> None:
    # "12a" on both sides matches; the extractor must NOT normalize "12a" -> "12".
    ctx_ok = _stage(tmp_path, ("12a",), _manifest_with(("12a",)))
    assert list(check_route_coverage(ctx_ok)) == []

    # "12a" in map vs "12" in manifest is a real two-way drift, not a match.
    ctx_drift = _stage(tmp_path, ("12a",), _manifest_with(("12",)))
    findings = list(check_route_coverage(ctx_drift))
    assert len(findings) == 2
    ids_named = " ".join(f.message for f in findings)
    assert "12a" in ids_named and "12" in ids_named


# --- US2: malformed or missing inputs fail loud -------------------------------


def test_missing_manifest_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, ("1",), _manifest_with(("1",)), track_manifest=False)
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 1
    assert _MANIFEST in findings[0].message
    msg = findings[0].message.lower()
    assert "missing" in msg or "untracked" in msg


def test_manifest_not_routes_mapping_fails(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, ("1",), "not_routes: 1\n")
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 1
    assert "'routes' list" in findings[0].message


def test_malformed_yaml_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, ("1",), "routes:\n  - id: [unbalanced\n")
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 1
    assert "yaml" in findings[0].message.lower()


def test_map_table_not_locatable_fails_loud(tmp_path: Path) -> None:
    # A map whose "Route by task" section is absent -> ERROR naming the map source,
    # never a vacuous empty comparison.
    ctx = _stage(
        tmp_path,
        None,
        _manifest_with(("1",)),
        map_text="# Knowledge map\n\n## Something else\n\nno task table here\n",
    )
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 1
    assert _MAP in findings[0].message


def test_empty_routes_list_is_not_vacuous_green(tmp_path: Path) -> None:
    # routes: [] is valid shape but empty -> every map id is manifest-only drift,
    # never a vacuous green.
    ctx = _stage(tmp_path, ("1", "2"), "routes: []\n")
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 2
    assert all(f.rule_id == "A3" for f in findings)
    named = " ".join(f.message for f in findings)
    assert "1" in named and "2" in named


def test_empty_map_table_is_not_vacuous_green(tmp_path: Path) -> None:
    # A locatable "Route by task" section with only header+separator (no data
    # rows) -> every manifest id is map-only drift, never a vacuous green.
    map_text = (
        "# Knowledge map\n\n"
        "## Route by task\n\n"
        "| Task | Route | Open first | End on |\n"
        "|---|---|---|---|\n\n"
        "## Route by symptom\n"
    )
    ctx = _stage(tmp_path, None, _manifest_with(("1", "2")), map_text=map_text)
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 2
    assert all(f.rule_id == "A3" for f in findings)


def test_separator_logic_does_not_drop_dash_containing_ids(tmp_path: Path) -> None:
    # A real data id like "1-a" contains a dash but is NOT a separator row; it must
    # be extracted. A pure "---" first cell IS a separator and must be skipped.
    map_text = (
        "# Knowledge map\n\n"
        "## Route by task\n\n"
        "| Task | Route | Open first | End on |\n"
        "|---|---|---|---|\n"
        "| 1-a Task | Route | `x` | y |\n"
        "## Route by symptom\n"
    )
    ctx = _stage(tmp_path, None, _manifest_with(("1-a",)), map_text=map_text)
    assert list(check_route_coverage(ctx)) == []


def test_multiple_bad_routes_all_reported(tmp_path: Path) -> None:
    # Two malformed manifest entries -> two findings (accumulate, not abort),
    # mirroring A1's per-route error idiom.
    manifest = 'routes:\n  - "not-a-dict"\n  - other: 1\n'
    ctx = _stage(tmp_path, ("1",), manifest)
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 2
    assert all(f.rule_id == "A3" for f in findings)


def test_missing_map_fails_loud(tmp_path: Path) -> None:
    # Map file not tracked at all -> fail loud naming the map.
    ctx = _stage(tmp_path, ("1",), _manifest_with(("1",)), track_map=False)
    findings = list(check_route_coverage(ctx))
    assert len(findings) == 1
    assert _MAP in findings[0].message


# --- US3 / Polish: live guard against the real repo ---------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_live_map_and_manifest_in_bijection_against_real_repo() -> None:
    """The shipped map "Route by task" id set == routes.yaml id set, end-to-end.

    Mirrors ``test_routes.py::test_live_manifest_resolves_against_real_repo``: shells
    to ``git ls-files``, builds a real RuleContext over the repo root, and asserts
    A3 emits zero findings -- proving the bijection holds on the committed repo.
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
    findings = list(check_route_coverage(ctx))
    assert findings == [], f"live map<->manifest bijection broken: {findings}"
