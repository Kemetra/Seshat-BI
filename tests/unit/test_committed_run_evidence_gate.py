"""A `verified` live state must rest on the record COMMITTED AT ``HEAD``.

Issue #493. ``.seshat/dagster/runs/`` is git-ignored (``.gitignore:111``, whose
own comment names ``orchestration/dagster/run-evidence/<run-id>.md`` as the
committed record), yet ``portfolio_watch._dagster_run_states`` read only that
scratch and could return ``verified`` -- and ``verified`` is the state that
SILENCES the ``[PENDING LIVE PROFILE]`` caveat in
``agent_next._live_validation_next_override``. So an untracked machine-local file
could silence a safety caveat on a shared read-only surface.

Two properties are pinned here, and they had to be solved TOGETHER:

  1. Rendering alone is not enough. The content is read from ``HEAD``, so an
     untracked (or tracked-but-modified) record cannot grant ``verified`` -- a
     reviewer must be able to obtain it from Git.
  2. The render-plus-commit workflow must actually REACH ``verified``. Committing
     the record necessarily advances ``HEAD`` past the run's ``commit_sha``, so a
     bare equality check would call the honest path stale forever. Requiring (1)
     without fixing (2) leaves a gate no real operator can pass.

Plus the #485 option-B honest caveat on the human-readable `status` render.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from seshat import portfolio_watch as pw
from seshat.dagster_adapter import evidence
from seshat.dagster_adapter.evidence_render import evidence_out_path, write_run_evidence
from tests.fixtures.portfolio_watch.builders import (
    init_git_repo,
    write_readiness_status,
)

pytestmark = pytest.mark.unit

_SCOPE = "scope_alpha"
_EVIDENCE_DIR = "orchestration/dagster/run-evidence"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)


def _commit_run_evidence(root: Path, run_id: str = "run-live-001") -> Path:
    """Render the committed record AND actually commit it -- the real workflow.

    Rendering without committing is what the pre-fix tests did, and it is exactly
    why the deadlock in property (2) above stayed invisible: the file existed in
    the worktree, so a worktree read accepted it, and ``HEAD`` never moved.
    Committing it on its own is the documented operator path.
    """
    out_path = write_run_evidence(root, run_id)
    _git(root, "add", f"{_EVIDENCE_DIR}/{run_id}.md")
    _git(root, "commit", "--no-gpg-sign", "-m", f"evidence: record {run_id}")
    return out_path


def _finalize_live_run(
    root: Path, run_id: str = "run-live-001", *, scope: str = _SCOPE
) -> None:
    """One succeeded run with a materialized `live_validate` row, scratch only."""
    writer = evidence.EvidenceWriter(root, run_id)
    writer.record(
        evidence.AssetOutcome(
            asset="live_validate",
            table=scope,
            gate_command="seshat validate",
            exit_code=0,
            measured={},
            outcome="materialized",
        )
    )
    evidence.finalize_run(
        root,
        run_id,
        [scope],
        evidence.RunMeta(started="2026-07-22T00:00:00Z"),
    )


def _scope_doc(root: Path) -> dict:
    return pw.build_portfolio_watch_summary(root)["scopes"][0]


def _repo_with_live_run(tmp_path: Path, run_id: str = "run-live-001") -> Path:
    write_readiness_status(tmp_path, _SCOPE, current_stage="gold_ready")
    init_git_repo(tmp_path)
    _finalize_live_run(tmp_path, run_id)
    return tmp_path


# --- #493: the scratch alone must not read as `verified` ----------------------


def test_scratch_only_live_run_is_not_verified(tmp_path: Path) -> None:
    """The git-ignored run records alone must NOT grant `verified`."""
    _repo_with_live_run(tmp_path)

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE
    # The run itself DID succeed -- only the live state is downgraded, so `watch`
    # and `next` keep agreeing at the one choke point.
    assert scope["last_dagster_run"] == "verified"


def test_rendered_but_uncommitted_record_is_not_verified(tmp_path: Path) -> None:
    """An UNTRACKED rendered record must not grant `verified` (finding 1).

    Running `seshat dagster evidence` writes the file into the worktree but
    commits nothing. A worktree read accepted that, so an operator who never
    committed still silenced the caveat -- while no reviewer could obtain the
    record from Git. That is precisely the state this gate exists to reject, so
    the content is read from `HEAD` instead.
    """
    _repo_with_live_run(tmp_path)
    write_run_evidence(tmp_path, "run-live-001")  # rendered, deliberately NOT committed

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


def test_render_plus_commit_workflow_reaches_verified(tmp_path: Path) -> None:
    """The documented render-plus-commit workflow must actually reach `verified`.

    The regression guard for finding 2, and the reason findings 1 and 2 had to be
    fixed together. Committing the record necessarily advances `HEAD` beyond the
    run's recorded `commit_sha`, so a bare equality check reports `stale` and the
    committed record is never even examined. Requiring "tracked at HEAD" without
    exempting the evidence commit therefore yields a gate NO operator can pass:
    the only way to satisfy the requirement is the very commit that trips it.

    A test that merely RENDERS the file cannot see this -- `HEAD` never moves --
    which is exactly how the deadlock passed CI.
    """
    _repo_with_live_run(tmp_path)
    _commit_run_evidence(tmp_path)

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == "verified"
    # The run's own state is untouched by the evidence commit.
    assert scope["last_dagster_run"] == "verified"


def test_committed_run_evidence_restores_verified(tmp_path: Path) -> None:
    """With the reviewable record committed at `HEAD`, `verified` is honest."""
    _repo_with_live_run(tmp_path)
    _commit_run_evidence(tmp_path)

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == "verified"


def test_committed_record_that_disagrees_is_not_verified(tmp_path: Path) -> None:
    """A record committed at `HEAD` that does not reproduce the raw records.

    The tampered content is COMMITTED, not merely written: otherwise this would
    pass for the wrong reason (nothing at `HEAD` at all) and would not test
    disagreement.
    """
    _repo_with_live_run(tmp_path)
    committed = write_run_evidence(tmp_path, "run-live-001")
    committed.write_text(
        committed.read_text(encoding="utf-8").replace("materialized", "deferred"),
        encoding="utf-8",
    )
    _git(tmp_path, "add", f"{_EVIDENCE_DIR}/run-live-001.md")
    _git(tmp_path, "commit", "--no-gpg-sign", "-m", "evidence: tampered record")

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


def test_verified_follows_head_not_a_local_edit_of_the_record(tmp_path: Path) -> None:
    """A local edit to an already-committed record does NOT change the answer.

    Deliberate, and the direction matters. The comparison reads `HEAD`, so a
    worktree edit is invisible to it: the state stays `verified` because the
    record a REVIEWER fetches from Git is still the correct one. A local scribble
    cannot revoke evidence that is properly committed.

    Note this is the SAFE direction of the HEAD read. The unsafe direction --
    a local edit CREATING a pass -- is impossible for the same reason, and is
    pinned by `test_rendered_but_uncommitted_record_is_not_verified` and
    `test_committed_record_that_disagrees_is_not_verified`. (`workspace_dirty` is
    recorded by `finalize_run` at run time, not sampled live, so it does not and
    should not react to post-run edits.)
    """
    _repo_with_live_run(tmp_path)
    committed = _commit_run_evidence(tmp_path)
    assert _scope_doc(tmp_path)["live_validation_state"] == "verified"

    committed.write_text("locally edited, never committed\n", encoding="utf-8")

    assert _scope_doc(tmp_path)["live_validation_state"] == "verified"


def test_committed_record_for_a_different_run_does_not_verify(tmp_path: Path) -> None:
    """The committed record must be THIS run's, not merely some committed file."""
    _repo_with_live_run(tmp_path, "run-live-001")
    _finalize_live_run(tmp_path, "run-live-002")
    # Commit run-001's record only after both runs exist, so run-002 is judged on
    # its own missing record rather than on a dirtied workspace.
    _commit_run_evidence(tmp_path, "run-live-001")

    # run-live-002 is the latest run and has no committed record.
    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


def test_latest_run_is_selected_before_the_committed_requirement(
    tmp_path: Path,
) -> None:
    """Selection order: newest run FIRST, then require it be committed.

    Filtering to committed runs before the max would silently prefer an older
    committed run over a newer uncommitted one -- hiding that a newer run
    happened. The newer run must win and then be reported uncommitted.
    """
    _repo_with_live_run(tmp_path, "run-live-001")
    # Finalize the newer run FIRST so both runs see the same workspace state --
    # otherwise committing run-001's record moves HEAD and run-002 reads `stale`,
    # which would mask what this test is actually about.
    _finalize_live_run(tmp_path, "run-live-002")
    _commit_run_evidence(tmp_path, "run-live-001")

    scope = _scope_doc(tmp_path)

    # The newer run with no committed record wins the selection -- the older
    # committed one must NOT be substituted for it.
    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


def test_crlf_committed_record_still_verifies(tmp_path: Path) -> None:
    """core.autocrlf=true checkouts must not read as a disagreement.

    The CRLF form is what gets committed here; `git show HEAD:<path>` hands back
    the blob, so this pins that the comparison survives the round trip.
    """
    _repo_with_live_run(tmp_path)
    committed = write_run_evidence(tmp_path, "run-live-001")
    committed.write_bytes(
        committed.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8")
    )
    _git(tmp_path, "add", f"{_EVIDENCE_DIR}/run-live-001.md")
    _git(tmp_path, "commit", "--no-gpg-sign", "-m", "evidence: crlf record")

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == "verified"


def test_unreadable_committed_record_is_not_verified(tmp_path: Path) -> None:
    """A record path that is not a committed blob fails closed.

    A directory at the record's path cannot be committed as a file, so
    `git show HEAD:<path>` fails and the gate reports uncommitted -- no worktree
    stat is involved any more.
    """
    _repo_with_live_run(tmp_path)
    out_path = evidence_out_path(tmp_path, "run-live-001")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.mkdir()

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


def test_evidence_commit_bundled_with_unrelated_changes_is_stale(
    tmp_path: Path,
) -> None:
    """The HEAD exemption covers ONLY the evidence record, nothing bundled with it.

    Documented consequence: the record must be committed on its own. Bundling
    unrelated files into that commit means HEAD moved for reasons the run cannot
    account for, so the run is stale -- which keeps the exemption from being
    widened by simply adding files to the same commit.
    """
    _repo_with_live_run(tmp_path)
    write_run_evidence(tmp_path, "run-live-001")
    (tmp_path / "unrelated.txt").write_text("something else\n", encoding="utf-8")
    _git(tmp_path, "add", f"{_EVIDENCE_DIR}/run-live-001.md", "unrelated.txt")
    _git(tmp_path, "commit", "--no-gpg-sign", "-m", "evidence plus unrelated change")

    assert _scope_doc(tmp_path)["live_validation_state"] == "stale"


def test_bundled_rename_into_the_evidence_dir_is_stale(tmp_path: Path) -> None:
    """A rename INTO the evidence directory must not bypass the revision check.

    Git's rename detection collapses `R100 source/x.md
    orchestration/dagster/run-evidence/x.md` to only the destination path under
    `--name-only`. Every reported path would then satisfy the evidence prefix and
    the run would be exempted from staleness -- even though a file left `source/`
    in that same commit. `--no-renames` surfaces the deletion as its own path.

    Needs a real `.gitignore` for `.seshat/`, as any actual repo has: otherwise
    the scratch gets committed too and the run reads stale for that reason
    instead, masking what this test is about.
    """
    (tmp_path / ".gitignore").write_text(".seshat/\n", encoding="utf-8")
    source = tmp_path / "source"
    source.mkdir(parents=True)
    # Content long enough that git scores the move as a rename.
    (source / "unrelated.md").write_text("x" * 400 + "\n", encoding="utf-8")
    _repo_with_live_run(tmp_path)

    write_run_evidence(tmp_path, "run-live-001")
    _git(
        tmp_path,
        "mv",
        "source/unrelated.md",
        f"{_EVIDENCE_DIR}/unrelated.md",
    )
    _git(
        tmp_path,
        "add",
        f"{_EVIDENCE_DIR}/run-live-001.md",
        f"{_EVIDENCE_DIR}/unrelated.md",
        "source",
    )
    _git(tmp_path, "commit", "--no-gpg-sign", "-m", "evidence plus bundled rename")

    assert _scope_doc(tmp_path)["live_validation_state"] == "stale"


def _is_git_argv(argv: object) -> bool:
    """Whether a `subprocess.run` first argument is a git argv list."""
    if not isinstance(argv, list):
        return False
    return bool(argv) and argv[0] == "git"


def test_evidence_git_reads_opt_into_safe_directory(tmp_path: Path) -> None:
    """Every evidence git read must carry `-c safe.directory=<root>`.

    A checkout owned by a different UID -- the norm for container-mounted
    workspaces -- makes git refuse for "dubious ownership". `_git_try` converts
    any failure to `None`, so without this option a correctly committed record
    would report as unverifiable forever: the same unpassable-gate failure mode
    as the staleness deadlock. `_source_revision` already opts in, so the two
    revision-reading paths must agree.
    """
    seen: list[list[str]] = []
    real_run = subprocess.run

    def spy(argv, *args, **kwargs):  # type: ignore[no-untyped-def]
        if _is_git_argv(argv):
            seen.append(argv)
        return real_run(argv, *args, **kwargs)

    _repo_with_live_run(tmp_path)
    _commit_run_evidence(tmp_path)

    expected = f"safe.directory={tmp_path.as_posix()}"
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pw.subprocess, "run", spy)
        assert _scope_doc(tmp_path)["live_validation_state"] == "verified"

    evidence_reads = [
        argv for argv in seen if {"show", "merge-base", "diff"} & set(argv)
    ]
    assert evidence_reads, "expected the HEAD/revision reads to run"
    for argv in evidence_reads:
        assert expected in argv, f"missing safe.directory opt-in: {argv}"


def test_state_is_in_the_declared_vocabulary(tmp_path: Path) -> None:
    """The new state joins the module's closed state set, not an ad-hoc string."""
    assert pw.STATE_UNCOMMITTED_EVIDENCE in pw.LIVE_VALIDATION_STATES

    _repo_with_live_run(tmp_path)

    assert _scope_doc(tmp_path)["live_validation_state"] in pw.LIVE_VALIDATION_STATES


# --- #493 amendment: stale-input detection must stay EQUIVALENTLY STRONG -----


def test_modified_recorded_inputs_are_not_verified_even_when_committed(
    tmp_path: Path,
) -> None:
    """Condition 2 of the amended ruling: reviewability must not cost staleness.

    The rendered committed record carries only a COUNT of ``input_artifacts``
    (``evidence_render.py:321-322``), never the per-path SHA-256 digests that
    ``_run_inputs_are_stale`` compares. So the committed markdown can NEVER be
    the sole source for `verified`: doing so would lose stale-input detection
    entirely -- a worse fail-open than #493 itself.

    The fix therefore ADDS the committed record as a NECESSARY condition on top
    of every existing scratch check, and removes none of them. Here a recorded
    input is modified after the run AND the committed record is present: the
    state must still not be `verified`.
    """
    _repo_with_live_run(tmp_path)
    _commit_run_evidence(tmp_path)
    # Sanity: with inputs untouched this repo IS verified, so the assertion
    # below is caused by the input edit and nothing else.
    assert _scope_doc(tmp_path)["live_validation_state"] == "verified"

    summary_path = (
        tmp_path / ".seshat" / "dagster" / "runs" / "run-live-001" / "summary.json"
    )
    recorded_inputs = json.loads(summary_path.read_text(encoding="utf-8"))[
        "input_artifacts"
    ]
    assert recorded_inputs, "the run must record at least one input artifact"
    target = tmp_path / next(iter(sorted(recorded_inputs)))
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# modified after the run\n",
        encoding="utf-8",
    )

    state = _scope_doc(tmp_path)["live_validation_state"]

    assert state != "verified"
    # And the caveat must not be silenced for a stale-input run either.
    assert state in pw.LIVE_VALIDATION_STATES


# --- #493: the caveat is downgraded, never silenced --------------------------


def _next_document(root: Path) -> dict:
    from seshat.agent_next import build_agent_next_document

    return build_agent_next_document(root)


def test_next_downgrades_rather_than_silences_on_uncommitted_evidence(
    tmp_path: Path,
) -> None:
    """The scratch-only run must NOT silence the live caveat on `next`."""
    write_readiness_status(
        tmp_path,
        _SCOPE,
        current_stage="gold_ready",
        stage_status={
            name: "pass"
            for name in (
                "source_ready",
                "mapping_ready",
                "silver_ready",
                "gold_ready",
                "semantic_model_ready",
                "dashboard_ready",
                "publish_ready",
            )
        },
        approvals=[
            {
                "stage": stage,
                "owner": "Ada Lovelace (data_owner)",
                "at": "2026-07-22",
                "note": "approved",
            }
            for stage in (
                "mapping_ready",
                "semantic_model_ready",
                "dashboard_ready",
                "publish_ready",
            )
        ],
    )
    init_git_repo(tmp_path)
    _finalize_live_run(tmp_path)

    action = _next_document(tmp_path)["next_allowed_action"]

    assert "CAUTION" in action
    assert "machine-local and unreviewable" in action
    assert ".seshat/dagster/runs/" in action
    assert "orchestration/dagster/run-evidence/" in action
    # It must NOT be the pending_live text: that tells the reader to install the
    # db extra, which is false when validation actually ran locally.
    assert "PENDING LIVE PROFILE" not in action


# --- #485 option B: the honest caveat on the human-readable status render -----


def test_status_text_states_the_provenance_limit_for_live_stages() -> None:
    """`status --format text` must say the evidence carries no DB provenance."""
    from seshat.cli.commands.status import _render_text

    projection = {
        "tables": [
            {
                "table": "bronze.sales",
                "source_path": "mappings/sales/readiness-status.yaml",
                "current_stage": "gold_ready",
                "stages": {
                    "silver_ready": {
                        "status": "pass",
                        "evidence": ["migration applied"],
                        "blocking_reasons": [],
                    }
                },
                "blocking_reasons": [],
                "next_action": None,
            }
        ]
    }

    rendered = _render_text(projection)

    assert "unverified_db_provenance" in rendered
    assert "machine-checkable database identity" in rendered


def test_status_text_stays_silent_when_no_live_stage_passes() -> None:
    """The caveat qualifies a live-materialization `pass`, not every table."""
    from seshat.cli.commands.status import _render_text

    projection = {
        "tables": [
            {
                "table": "bronze.sales",
                "source_path": "mappings/sales/readiness-status.yaml",
                "current_stage": "mapping_ready",
                "stages": {
                    "source_ready": {
                        "status": "pass",
                        "evidence": ["profiled"],
                        "blocking_reasons": [],
                    },
                    "silver_ready": {
                        "status": "not_started",
                        "evidence": [],
                        "blocking_reasons": [],
                    },
                },
                "blocking_reasons": [],
                "next_action": None,
            }
        ]
    }

    assert "unverified_db_provenance" not in _render_text(projection)


def test_status_text_and_next_use_one_shared_wording() -> None:
    """One condition, one sentence -- #487's drift failure must not recur."""
    from seshat.run_next import _provenance_caveat, provenance_caveat_for_stages

    stages = {
        "silver_ready": {"status": "pass", "evidence": ["x"], "blocking_reasons": []},
        "gold_ready": {"status": "pass", "evidence": ["y"], "blocking_reasons": []},
    }

    caveat = provenance_caveat_for_stages(stages)

    # First live-materialization pass in spine order, at most once.
    assert caveat == _provenance_caveat("silver_ready")


def test_status_json_projection_is_unchanged_by_the_caveat(tmp_path: Path) -> None:
    """The closed schema / verbatim projection contract stays intact (#485).

    Uses this repo's stdlib-only ``_schema_check`` helper, not ``jsonschema``:
    CI installs `pip install -e ".[dev]"` on a clean runner and that extra does
    not declare ``jsonschema``, so importing it fails the gate.
    """
    from seshat.status_surface import build_status_projection
    from tests.unit._schema_check import assert_matches_schema

    write_readiness_status(tmp_path, _SCOPE, current_stage="gold_ready")
    projection = build_status_projection(tmp_path)

    schema = json.loads(
        (
            Path(__file__).resolve().parents[2] / "schemas" / "agent-status.schema.json"
        ).read_text(encoding="utf-8")
    )
    assert_matches_schema(projection, schema)

    for table in projection["tables"]:
        assert "caveats" not in table
