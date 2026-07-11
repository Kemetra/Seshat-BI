"""TDD tests for SC2 -- prose rule-count claim reconciler.

SC2 is the rule-COUNT sibling of SC1 (``src/seshat/rules/status_claims.py``). SC1
reconciles prose status claims (built/planned) against tracked-file evidence; SC2
reconciles a prose "N rules" count claim against the AUTHORITATIVE rule count.

The authoritative count is read from the committed rule-count JSON
(``docs/rules/rules-manifest.json``) with the stdlib ``json`` module -- NEVER by
importing the rules package -- so SC2 keeps the stdlib-only never-execute discipline
of the ``retail check`` core chain (matching SC1).

A hand-curated manifest (``docs/quality/rule-count-claims.yaml``) records each claim
as ``id`` + ``doc`` + ``anchor`` (the literal sentence stating the count) +
``claimed-count`` (the integer the prose asserts). SC2 emits an ERROR when the claimed
count differs from the authoritative count, and fails LOUD (never a vacuous green) on
a missing/malformed manifest, a wrong-shape or incomplete entry, an untracked claiming
doc, an absent anchor, a malformed count, or an unreadable count source. It is
categorical (matches or not) -- no confidence score.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.rule_count_claims import (
    _COUNT_SOURCE,
    _MANIFEST,
    check_rule_count_claims,
)

pytestmark = pytest.mark.unit


def _stage(
    tmp_path: Path,
    manifest_claims: str,
    docs: dict[str, str] | None = None,
    count_source_len: int | None = 7,
    *,
    track_manifest: bool = True,
    count_source_text: str | None = None,
    track_count_source: bool = True,
) -> RuleContext:
    """Stage a synthetic SC2 fixture and return its RuleContext.

    ``manifest_claims`` is the full YAML body written to the rule-count-claims
    manifest. ``docs`` maps a repo-relative doc path -> its full text (must contain
    the anchor for a claim that should resolve). ``count_source_len`` writes a
    synthetic count-source JSON list of that length (its ``len`` is the authoritative
    count); pass ``None`` with ``count_source_text`` to write arbitrary bytes (to
    exercise the unparseable-source branch), or ``track_count_source=False`` to leave
    it untracked.
    """
    tracked: list[str] = []

    mpath = tmp_path / _MANIFEST
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(manifest_claims, encoding="utf-8")
    if track_manifest:
        tracked.append(_MANIFEST)

    for rel, text in (docs or {}).items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        tracked.append(rel)

    if count_source_text is not None:
        cpath = tmp_path / _COUNT_SOURCE
        cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text(count_source_text, encoding="utf-8")
        if track_count_source:
            tracked.append(_COUNT_SOURCE)
    elif count_source_len is not None:
        import json

        cpath = tmp_path / _COUNT_SOURCE
        cpath.parent.mkdir(parents=True, exist_ok=True)
        entries = [{"id": f"R{i}", "title": "x"} for i in range(count_source_len)]
        cpath.write_text(json.dumps(entries), encoding="utf-8")
        if track_count_source:
            tracked.append(_COUNT_SOURCE)

    return RuleContext(repo_root=tmp_path, tracked_files=tuple(tracked))


def _claim(claimed_count: object = 7, anchor: str = "Currently 7 rules") -> str:
    return (
        "claims:\n"
        '  - id: "count-1"\n'
        '    doc: "docs/x.md"\n'
        f'    anchor: "{anchor}"\n'
        f"    claimed-count: {claimed_count}\n"
    )


# --- US1: stale-count detection + accurate-count clean -----------------------


def test_stale_count_fails(tmp_path: Path) -> None:
    # claimed-count (7) != authoritative count (5), anchor present -> 1 ERROR.
    ctx = _stage(
        tmp_path,
        _claim(7),
        docs={"docs/x.md": "Currently 7 rules in the gate\n"},
        count_source_len=5,
    )
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert findings[0].rule_id == "SC2"
    assert findings[0].severity is Severity.ERROR
    assert "count-1" in findings[0].message
    assert "docs/x.md" in findings[0].message
    assert "7" in findings[0].message
    assert "5" in findings[0].message


def test_accurate_count_yields_no_findings(tmp_path: Path) -> None:
    # claimed-count (7) == authoritative count (7), anchor present -> [].
    ctx = _stage(
        tmp_path,
        _claim(7),
        docs={"docs/x.md": "Currently 7 rules in the gate\n"},
        count_source_len=7,
    )
    assert list(check_rule_count_claims(ctx)) == []


# --- US2: per-entry fail-loud branches ---------------------------------------


def test_absent_anchor_fails_loud(tmp_path: Path) -> None:
    # anchor NOT present in the claiming doc -> stale/misplaced ERROR.
    ctx = _stage(
        tmp_path,
        _claim(7, anchor="Currently 7 rules"),
        docs={"docs/x.md": "totally different content\n"},
        count_source_len=7,
    )
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert "anchor" in findings[0].message.lower()


def test_malformed_count_fails(tmp_path: Path) -> None:
    doc = {"docs/x.md": "Currently 7 rules in the gate\n"}

    # (a) missing claimed-count entirely.
    missing = (
        "claims:\n"
        '  - id: "count-1"\n'
        '    doc: "docs/x.md"\n'
        '    anchor: "Currently 7 rules"\n'
    )
    findings = list(check_rule_count_claims(_stage(tmp_path, missing, docs=doc)))
    assert len(findings) == 1
    # missing required field is reported as a missing field OR malformed count.
    assert (
        "claimed-count" in findings[0].message
        or "malformed" in findings[0].message.lower()
    )

    # (b) non-integer value.
    non_int = _claim('"seven"', anchor="Currently 7 rules")
    findings = list(check_rule_count_claims(_stage(tmp_path, non_int, docs=doc)))
    assert len(findings) == 1
    assert "malformed" in findings[0].message.lower()

    # (c) negative value.
    negative = _claim(-3, anchor="Currently 7 rules")
    findings = list(check_rule_count_claims(_stage(tmp_path, negative, docs=doc)))
    assert len(findings) == 1
    assert "malformed" in findings[0].message.lower()


def test_untracked_doc_fails(tmp_path: Path) -> None:
    # doc named but not tracked -> fail loud.
    ctx = _stage(tmp_path, _claim(7), docs=None, count_source_len=7)
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert "docs/x.md" in findings[0].message


def test_missing_field_fails(tmp_path: Path) -> None:
    # entry missing the anchor field -> ERROR.
    manifest = (
        'claims:\n  - id: "count-1"\n    doc: "docs/x.md"\n    claimed-count: 7\n'
    )
    ctx = _stage(tmp_path, manifest, docs={"docs/x.md": "Currently 7 rules\n"})
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert "anchor" in findings[0].message


def test_non_mapping_entry_fails(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "claims:\n  - just_a_string\n")
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert "not a mapping" in findings[0].message


# --- US3: bad manifest / count source fail-loud ------------------------------


def test_missing_manifest_fails_loud(tmp_path: Path) -> None:
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert _MANIFEST in findings[0].message


def test_malformed_yaml_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "claims:\n  - id: [unbalanced\n")
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert "yaml" in findings[0].message.lower()


def test_wrong_shape_fails_loud(tmp_path: Path) -> None:
    ctx = _stage(tmp_path, "not_claims: 1\n")
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert "'claims' list" in findings[0].message


def test_missing_count_source_fails_loud(tmp_path: Path) -> None:
    # count source untracked -> fail loud (cannot establish the authoritative count).
    ctx = _stage(
        tmp_path,
        _claim(7),
        docs={"docs/x.md": "Currently 7 rules\n"},
        track_count_source=False,
    )
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert _COUNT_SOURCE in findings[0].message


def test_unparseable_count_source_fails_loud(tmp_path: Path) -> None:
    # count source is not valid JSON -> fail loud.
    ctx = _stage(
        tmp_path,
        _claim(7),
        docs={"docs/x.md": "Currently 7 rules\n"},
        count_source_len=None,
        count_source_text="{not valid json",
    )
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert _COUNT_SOURCE in findings[0].message

    # count source is valid JSON but not a list -> fail loud.
    ctx = _stage(
        tmp_path,
        _claim(7),
        docs={"docs/x.md": "Currently 7 rules\n"},
        count_source_len=None,
        count_source_text='{"a": 1}',
    )
    findings = list(check_rule_count_claims(ctx))
    assert len(findings) == 1
    assert _COUNT_SOURCE in findings[0].message


# --- live guard --------------------------------------------------------------


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_live_manifest_reconciles_against_real_repo() -> None:
    """The shipped rule-count manifest + corrected prose reconcile clean.

    Proves all three integers agree: the glossary prose count, the claimed-count in
    the manifest entry, and the authoritative count (len of the committed rule-count
    JSON).
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
    findings = list(check_rule_count_claims(ctx))
    assert findings == [], f"live rule-count manifest has contradictions: {findings}"
