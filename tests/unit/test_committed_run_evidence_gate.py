"""A `verified` live state must rest on the COMMITTED record, not the scratch.

Issue #493. ``.seshat/dagster/runs/`` is git-ignored (``.gitignore:111``, whose
own comment names ``orchestration/dagster/run-evidence/<run-id>.md`` as the
committed record), yet ``portfolio_watch._dagster_run_states`` read only that
scratch and could return ``verified`` -- and ``verified`` is the state that
SILENCES the ``[PENDING LIVE PROFILE]`` caveat in
``agent_next._live_validation_next_override``. So an untracked machine-local file
could silence a safety caveat on a shared read-only surface.

Plus the #485 option-B honest caveat on the human-readable `status` render.
"""

from __future__ import annotations

import json
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


def test_committed_run_evidence_restores_verified(tmp_path: Path) -> None:
    """With the reviewable committed record present, `verified` is honest."""
    _repo_with_live_run(tmp_path)
    write_run_evidence(tmp_path, "run-live-001")

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == "verified"


def test_committed_record_that_disagrees_is_not_verified(tmp_path: Path) -> None:
    """A committed record that does not reproduce the raw records is rejected."""
    _repo_with_live_run(tmp_path)
    committed = write_run_evidence(tmp_path, "run-live-001")
    committed.write_text(
        committed.read_text(encoding="utf-8").replace("materialized", "deferred"),
        encoding="utf-8",
    )

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


def test_committed_record_for_a_different_run_does_not_verify(tmp_path: Path) -> None:
    """The committed record must be THIS run's, not merely some committed file."""
    _repo_with_live_run(tmp_path, "run-live-001")
    _finalize_live_run(tmp_path, "run-live-002")
    # Render run-001's record only after both runs exist, so run-002 is judged on
    # its own missing record rather than on a dirtied workspace.
    write_run_evidence(tmp_path, "run-live-001")

    # run-live-002 is the latest run and is uncommitted.
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
    # otherwise rendering run-001's record dirties the tree and run-002 reads
    # `stale`, which would mask what this test is actually about.
    _finalize_live_run(tmp_path, "run-live-002")
    write_run_evidence(tmp_path, "run-live-001")

    scope = _scope_doc(tmp_path)

    # The newer, uncommitted run wins the selection -- the older committed one
    # must NOT be substituted for it.
    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


def test_crlf_committed_record_still_verifies(tmp_path: Path) -> None:
    """core.autocrlf=true checkouts must not read as a disagreement."""
    _repo_with_live_run(tmp_path)
    committed = write_run_evidence(tmp_path, "run-live-001")
    committed.write_bytes(
        committed.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8")
    )

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == "verified"


def test_unreadable_committed_record_is_not_verified(tmp_path: Path) -> None:
    """A committed path that is not a readable file fails closed."""
    _repo_with_live_run(tmp_path)
    out_path = evidence_out_path(tmp_path, "run-live-001")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.mkdir()

    scope = _scope_doc(tmp_path)

    assert scope["live_validation_state"] == pw.STATE_UNCOMMITTED_EVIDENCE


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
    write_run_evidence(tmp_path, "run-live-001")
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
    """The closed schema / verbatim projection contract stays intact (#485)."""
    import jsonschema

    from seshat.status_surface import build_status_projection

    write_readiness_status(tmp_path, _SCOPE, current_stage="gold_ready")
    projection = build_status_projection(tmp_path)

    schema = json.loads(
        (
            Path(__file__).resolve().parents[2] / "schemas" / "agent-status.schema.json"
        ).read_text(encoding="utf-8")
    )
    jsonschema.validate(projection, schema)

    for table in projection["tables"]:
        assert "caveats" not in table
