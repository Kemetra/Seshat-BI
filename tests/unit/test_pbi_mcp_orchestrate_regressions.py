"""Orchestrate regressions: cases a named review or issue put on record.

Split from the behaviour suite because "a review found X, so assert X forever"
is a different responsibility from "the feature guarantees Y" -- which is what
CodeScene measured as Low Cohesion once #660 grew the module to 886 lines.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate, orchestrate
from tests.unit._pbi_mcp_orchestrate_fixtures import (
    ALLOWLIST,
    MUTATED_TMDL,
    OPERATION,
    READINESS,
    TARGET,
    TARGET_PATH,
    _apply,
    _git,
    _mcp_session,
    _write,
)

pytestmark = pytest.mark.unit

# --------------------------------------------------------------------------
# Codex (PR #659): git C-quotes unusual paths, so the snapshot must use -z
# --------------------------------------------------------------------------


def test_snapshot_sees_a_non_ascii_path(tmp_path: Path) -> None:
    """`git ls-files` C-quotes non-ASCII names, and stripping quotes is not decoding.

    `git ls-files` emits `"caf\303\251.tmdl"` for `café.tmdl` by default. Removing
    the surrounding quotes leaves the octal escapes intact, so `_digest` reads a
    path that does not exist, returns None, and the file DISAPPEARS from the
    snapshot -- which is what makes an out-of-scope write to such a file
    invisible to the effect check.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "plain.tmdl").write_text("a\n", encoding="utf-8")
    (tmp_path / "caf\u00e9.tmdl").write_text("b\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")

    snapshot = orchestrate._snapshot(tmp_path)

    assert "caf\u00e9.tmdl" in snapshot, (
        f"the non-ASCII path is missing from the snapshot: {sorted(snapshot)}"
    )
    assert "plain.tmdl" in snapshot


def test_an_out_of_scope_write_to_a_quoted_path_is_caught(tmp_path: Path) -> None:
    """The consequence: such a file must not be a blind spot for the scope check.

    This is the assertion that matters -- a runtime writing outside its authorized
    target is exactly what `_effect_blockers` exists to catch, and a path git
    quotes must not be a way around it.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    target = "authorized.tmdl"
    (tmp_path / target).write_text("original\n", encoding="utf-8")
    sneaky = tmp_path / "caf\u00e9.tmdl"
    sneaky.write_text("before\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")

    before = orchestrate._snapshot(tmp_path)
    # The "runtime" changes BOTH the authorized target and the quoted-path file.
    (tmp_path / target).write_text("mutated\n", encoding="utf-8")
    sneaky.write_text("after\n", encoding="utf-8")
    after = orchestrate._snapshot(tmp_path)

    blockers = orchestrate._effect_blockers(before, after, target)
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers, (
        "an out-of-scope write to a git-quoted path was not detected"
    )


def test_a_pre_launch_runtime_failure_is_blocked_not_failed(ready_repo: Path) -> None:
    """Exit 1 with no mutation is `blocked` per the CLI contract, not `failed`.

    `contracts/cli-contract.md` row for exit 1: "Refused before execution
    (invariant or precondition). Evidence outcome `blocked`. Nothing was mutated."
    When `npx` is absent the runtime never starts, so `mutation_attempted` is
    False and exit 1 is correct -- but the record said `failed`, giving evidence
    consumers a state the contract does not define for that exit code.

    Codex review, PR #659.
    """

    def cannot_launch(argv: list[str], cwd: Path):
        raise FileNotFoundError("npx not found")

    report = _apply(ready_repo, mcp_runner=cannot_launch)

    assert report.exit_code == orchestrate.EXIT_REFUSED
    assert not report.mutation_attempted
    assert report.outcome == "blocked", (
        f"exit 1 with no mutation recorded outcome {report.outcome!r}; the "
        "contract defines that state as 'blocked'"
    )
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["outcome"] == "blocked"
    assert payload["mutation_attempted"] is False


# --------------------------------------------------------------------------
# Review M1 -- the evidence record must not assert a mutation that never happened
# --------------------------------------------------------------------------


def test_a_read_pair_records_no_mutation_attempted(ready_repo: Path) -> None:
    """M1: orchestrate hardcoded mutation_attempted=True, discarding the runner.

    An allowlisted READ pair attempts nothing, issues no flush, and must not
    drive rollback guidance -- the evidence record asserting True for such a run
    tells an auditor a mutation was tried when none was.

    Missed before because this module defined only an `Update` pair.
    """
    read_operation = "measure_operations.List"
    read_allowlist = ALLOWLIST.replace(OPERATION, read_operation)
    _write(ready_repo, gate.TARGET_ALLOWLIST_RELPATH, read_allowlist)
    readiness = READINESS.replace(OPERATION, read_operation)
    _write(ready_repo, f"mappings/{TARGET}/readiness-status.yaml", readiness)
    _git(ready_repo, "add", "-A")
    _git(ready_repo, "commit", "-q", "-m", "read pair", "--no-gpg-sign")

    report = _apply(
        ready_repo,
        operation_id=read_operation,
        mcp_runner=_mcp_session(),
    )
    assert report.mutation_attempted is False, report.blockers
    payload = json.loads(report.evidence_path.read_text(encoding="utf-8"))
    assert payload["mutation_attempted"] is False


# --------------------------------------------------------------------------
# Review C1/H1 -- a FOLDER target: the vendor connects and flushes a directory
# --------------------------------------------------------------------------

FOLDER_TARGET = "Sales.SemanticModel"


#: Siblings inside the model folder, COMMITTED by `_folder_repo`. They must be
#: tracked: `_semantic_files` discovers from git with `include_untracked=False`,
#: so a file created mid-test is invisible to the validator's own corpus.
SIBLINGS = ("dim_customer", "dim_date", "dim_product")


def _sibling_tmdl(name: str) -> str:
    return f"table {name}\n\n\tcolumn Key\n\t\tdataType: string\n"


def _folder_repo(repo: Path) -> Path:
    """Re-point the committed allowlist at the model FOLDER, not one file."""
    _write(
        repo,
        gate.TARGET_ALLOWLIST_RELPATH,
        ALLOWLIST.replace(f"path: {TARGET_PATH}", f"path: {FOLDER_TARGET}"),
    )
    for name in SIBLINGS:
        _write(
            repo,
            f"{FOLDER_TARGET}/definition/tables/{name}.tmdl",
            _sibling_tmdl(name),
        )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "folder target", "--no-gpg-sign")
    return repo


def test_a_folder_target_clears_the_gate(ready_repo: Path) -> None:
    """C1: requiring is_file() made folder targets unusable.

    The vendor binds a TMDL *folder* and flushes it back, so a write target is
    legitimately a directory. Before this fix, a file target cleared the gate but
    could not be connected, and a folder target could be connected but never
    cleared -- the two branches were mutually exclusive and no write could run.
    """
    report = _apply(_folder_repo(ready_repo))
    assert gate.BLOCKER_TARGET_ABSENT not in report.blockers, report.blockers


def test_a_folder_write_touching_many_files_is_in_scope(ready_repo: Path) -> None:
    """H1: ExportToTmdlFolder rewrites the WHOLE folder -- 11 files, measured.

    Scoping a folder write to a single path reports an out-of-scope change on
    every legitimate apply.
    """

    def _rewrite_whole_folder(cwd: Path) -> None:
        # Faithful to the real flush: the authorized artifact AND its siblings in
        # the same model folder are all rewritten. Sibling content is valid TMDL
        # so the post-write validator has real bytes to parse -- an invalid
        # sibling would fail on PBIMCP-VAL-02 (read nothing) and prove nothing
        # about scope, which is what this test is for.
        tables = cwd / FOLDER_TARGET / "definition" / "tables"
        (cwd / TARGET_PATH).write_text(MUTATED_TMDL, encoding="utf-8")
        for name in SIBLINGS:
            (tables / f"{name}.tmdl").write_text(
                _sibling_tmdl(name) + "\tcolumn Extra\n\t\tdataType: int64\n",
                encoding="utf-8",
            )

    report = _apply(
        _folder_repo(ready_repo), mcp_runner=_mcp_session(_rewrite_whole_folder)
    )
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE not in report.blockers, (
        report.blockers
    )
    assert report.succeeded, report.blockers


def test_a_folder_write_escaping_the_subtree_is_STILL_refused(
    ready_repo: Path,
) -> None:
    """Widening to a subtree must not license changes outside it."""

    def _stray(cwd: Path) -> None:
        (cwd / TARGET_PATH).write_text(MUTATED_TMDL, encoding="utf-8")
        (cwd / "README.md").write_text("not in the model folder\n", encoding="utf-8")

    report = _apply(_folder_repo(ready_repo), mcp_runner=_mcp_session(_stray))
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in report.blockers


def test_a_folder_write_that_changes_nothing_is_not_materialized(
    ready_repo: Path,
) -> None:
    """A no-op folder write must not report success."""
    report = _apply(_folder_repo(ready_repo), mcp_runner=_mcp_session())
    assert orchestrate.BLOCKER_TARGET_UNCHANGED in report.blockers
    assert report.succeeded is False


def test_a_prefix_sharing_sibling_is_NOT_admitted_as_in_scope() -> None:
    """Subtree scoping must not become a prefix match.

    `Sales.SemanticModel.backup/x.tmdl` shares a string prefix with the target
    but is a DIFFERENT directory. Admitting it would be a scope escape the old
    exact-match comparison did not have -- a regression introduced by the H1 fix.
    """
    target = "Sales.SemanticModel"
    for stray in (
        "Sales.SemanticModel.backup/x.tmdl",
        "Sales.SemanticModelOther/y.tmdl",
        "Sales.SemanticModel2/z.tmdl",
    ):
        blockers = orchestrate._effect_blockers({stray: "old"}, {stray: "new"}, target)
        assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers, stray


def test_a_file_target_still_authorizes_exactly_itself() -> None:
    """Widening for folders must not loosen a file target."""
    target = "Sales.SemanticModel/definition/x.tmdl"
    sibling = "Sales.SemanticModel/definition/y.tmdl"
    blockers = orchestrate._effect_blockers(
        {target: "a", sibling: "a"}, {target: "b", sibling: "b"}, target
    )
    assert orchestrate.BLOCKER_OUT_OF_SCOPE_CHANGE in blockers
