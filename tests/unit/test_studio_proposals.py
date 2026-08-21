"""Phase C -- proposals (spec 140, US2, Tasks 3.1-3.2).

A proposal binds a reviewed change to the exact content and workspace revision it was
prepared from. That binding is what makes a later decision refusable when either moves:
without it, a human could sign one thing and a different thing could be applied.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seshat.studio import proposals  # noqa: E402

pytestmark = pytest.mark.unit

_REVISION = "r" * 16
_TARGET = ".seshat/kpi-contracts.yaml"


def _proposal(**overrides):
    payload = {
        "target_artifact": _TARGET,
        "diff": "- net_sales\n+ net_sales_of_returns\n",
        "fields": (),
        "workspace_revision": _REVISION,
        "question": "Should net sales be reported net of returns?",
        "allowed_answers": ("net_of_returns", "gross"),
        "required_authority": "owner",
    }
    payload.update(overrides)
    return proposals.build_proposal(**payload)  # type: ignore[arg-type]


# --- Task 3.1: hashed, revision-bound ------------------------------------------------


def test_a_proposal_binds_its_hash_to_its_content():
    first = _proposal()
    second = _proposal(diff="- net_sales\n+ gross_sales\n")

    assert first.proposal_hash != second.proposal_hash


def test_the_same_content_hashes_identically():
    """Content-addressed, not random: a re-prepared identical proposal must match, or
    staleness checks would fire on every refresh."""
    assert _proposal().proposal_hash == _proposal().proposal_hash


def test_the_hash_covers_the_workspace_revision():
    """Same diff prepared from a different revision is a DIFFERENT proposal."""
    assert (
        _proposal().proposal_hash
        != _proposal(workspace_revision="z" * 16).proposal_hash
    )


def test_the_hash_covers_the_target_artifact():
    other = _proposal(target_artifact=".seshat/semantic-decisions.yaml")

    assert _proposal().proposal_hash != other.proposal_hash


def test_a_proposal_is_immutable():
    """FR-140-008: scope is immutable after review; a change makes a NEW proposal."""
    proposal = _proposal()

    with pytest.raises(Exception):
        proposal.diff = "tampered"  # type: ignore[misc]


def test_a_proposal_carries_its_question_and_closed_answer_set():
    """FR-140-009 depends on this: an answer outside the set is refusable, so the agent
    cannot smuggle in a judgement by phrasing."""
    proposal = _proposal()

    assert proposal.question
    assert proposal.allowed_answers == ("net_of_returns", "gross")
    assert proposal.required_authority == "owner"


# --- Task 3.2: staleness --------------------------------------------------------------


def test_a_moved_revision_makes_the_proposal_stale():
    proposal = _proposal()

    assert proposals.is_stale(proposal, current_revision=_REVISION) is False
    assert proposals.is_stale(proposal, current_revision="z" * 16) is True


def test_field_provenance_kinds_are_a_closed_set():
    """FR-140-006: `inference` and `default` must never be presentable as an
    `existing_decision`, so the vocabulary cannot be an open string."""
    assert proposals.PROVENANCE_KINDS == (
        "discovered_fact",
        "existing_decision",
        "default",
        "inference",
        "new_human_judgment",
    )


def test_an_unknown_provenance_kind_is_refused():
    with pytest.raises(ValueError, match="provenance"):
        proposals.FieldProvenance(
            field="net_sales", kind="looks_fine", source_ref="mappings/sales.yaml"
        )


def test_a_known_provenance_kind_is_accepted():
    """The inverse: proves the validator accepts the real vocabulary rather than
    rejecting everything."""
    provenance = proposals.FieldProvenance(
        field="net_sales", kind="inference", source_ref="mappings/sales.yaml"
    )

    assert provenance.kind == "inference"
