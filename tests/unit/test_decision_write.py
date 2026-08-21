"""Phase A -- the Decision Store write path (spec 140, Tasks 1.1-1.5).

The security claim under test: Studio may write a decision into the working tree but
cannot make it authoritative. Authority requires a human commit, after which the gate
reads the decision at HEAD.

Each guard is proven by a test that fails if the guard is removed. Absence-assertions
are avoided deliberately -- they go green when a capability ships in a different shape.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unit import _workbench_fixtures as fixtures  # noqa: E402

from seshat import decision_store, decision_write  # noqa: E402

pytestmark = pytest.mark.unit

_SIGNER = "Ahmed Shaaban (owner)"
_STORE = ".seshat/semantic-decisions.yaml"


def _entry(**overrides: object) -> dict:
    """A well-formed non-critical decision entry, so `authority=None` is legitimate."""
    payload: dict = {
        "decision_id": "d-001",
        # Non-critical on purpose: a critical type additionally needs the authority
        # contract, which is a separate concern from the write path.
        "decision_type": "assumption_note",
        "scope": {"table": "sales"},
    }
    signer = str(overrides.pop("signer", _SIGNER))
    answer = str(overrides.pop("answer", "net_of_returns"))
    payload.update(overrides)  # type: ignore[arg-type]
    return decision_write.build_entry(
        **payload,  # type: ignore[arg-type]
        ruling=decision_write.HumanRuling(signer=signer, answer=answer),
        binding=decision_write.ReviewBinding(
            proposal_hash="h" * 64,
            workspace_revision="r" * 16,
            recorded_at="2026-08-21T10:00:00Z",
            reviewed_scope=_STORE,
        ),
    )


# --- Task 1.1: build a decision entry -------------------------------------------------


def test_build_entry_populates_every_required_approval_field():
    approval = _entry()["approval"]

    missing = [
        k for k in decision_store.APPROVAL_REQUIRED_FIELDS if not approval.get(k)
    ]

    assert missing == []
    assert approval["approved_by"] == _SIGNER


def test_the_built_entry_uses_a_status_the_shipped_reader_recognizes():
    """An unrecognized status is malformed and fails closed at every consumer, so a
    plausible-looking invented value would be a silent defect."""
    entry = _entry()

    assert decision_store.is_known_status(entry["status"])
    assert not decision_store.is_open_status(entry["status"])


def test_the_built_entry_is_accepted_by_the_shipped_validity_predicate():
    """Built from the validators' perspective, not from a hand-written expectation."""
    valid, reason = decision_store.approval_is_valid(_entry(), authority=None)

    assert valid, reason


# --- Task 1.2: refuse what the validators refuse, writing nothing ---------------------


def test_a_malformed_signer_is_refused_and_the_file_is_untouched(tmp_path: Path):
    store = fixtures.store_file(tmp_path)
    original = "decisions:\n  - id: existing\n"
    store.write_text(original, encoding="utf-8")

    # `owner (owner)` fails owner_shape_ok: the name is itself a role token.
    entry = _entry(signer="owner (owner)")

    with pytest.raises(decision_write.WriteRefused):
        decision_write.append_decision(tmp_path, _STORE, entry, authority=None)

    assert store.read_text(encoding="utf-8") == original


def test_a_critical_decision_without_an_authority_contract_is_refused(tmp_path: Path):
    """`authority is None` means eligibility cannot be validated => fail closed."""
    store = fixtures.store_file(tmp_path)
    original = store.read_text(encoding="utf-8")

    critical = sorted(decision_store.CRITICAL_DECISION_TYPES)[0]
    entry = _entry(decision_type=critical)

    with pytest.raises(decision_write.WriteRefused):
        decision_write.append_decision(tmp_path, _STORE, entry, authority=None)

    assert store.read_text(encoding="utf-8") == original


def test_a_successful_write_returns_a_pending_commit_receipt(tmp_path: Path):
    fixtures.store_file(tmp_path)

    receipt = decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)

    assert receipt.state == "pending_commit"
    assert receipt.written_path == _STORE
    assert receipt.decision_id == "d-001"


def test_the_receipt_cannot_represent_an_approved_state():
    """FR-140-021 as a type constraint: the false claim must be unrepresentable, not
    merely discouraged. This fails the moment an `approved` member is added."""
    assert decision_write.RECEIPT_STATES == ("pending_commit",)


# --- Task 1.3: append atomically, preserving what is already there --------------------


def test_append_preserves_existing_entries_and_comments(tmp_path: Path):
    store = fixtures.store_file(tmp_path)
    store.write_text(
        "# provenance: hand-authored, do not reorder\n"
        "decisions:\n"
        "  - id: first\n"
        "  - id: second\n",
        encoding="utf-8",
    )

    decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)

    text = store.read_text(encoding="utf-8")
    assert "# provenance: hand-authored, do not reorder" in text
    assert text.index("id: first") < text.index("id: second") < text.index("id: d-001")


def test_the_appended_document_is_still_readable_by_the_shipped_loader(tmp_path: Path):
    """The real proof that the append did not corrupt the store."""
    fixtures.store_file(tmp_path)

    decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)

    loaded = decision_store.load_store_file(tmp_path, _STORE)
    assert loaded.ok, loaded.problems
    assert [d["id"] for d in loaded.decisions] == ["d-001"]


def test_two_appends_accumulate_rather_than_overwrite(tmp_path: Path):
    fixtures.store_file(tmp_path)

    decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)
    decision_write.append_decision(
        tmp_path, _STORE, _entry(decision_id="d-002"), authority=None
    )

    loaded = decision_store.load_store_file(tmp_path, _STORE)
    assert [d["id"] for d in loaded.decisions] == ["d-001", "d-002"]


def test_an_existing_decision_is_never_mutated(tmp_path: Path):
    """Append-only (FR-140-022): the first entry must survive unchanged."""
    fixtures.store_file(tmp_path)
    decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)
    first = decision_store.load_store_file(tmp_path, _STORE).decisions[0]

    decision_write.append_decision(
        tmp_path, _STORE, _entry(decision_id="d-002", answer="gross"), authority=None
    )

    after = decision_store.load_store_file(tmp_path, _STORE).decisions[0]
    assert after == first


def test_a_refused_write_leaves_no_temporary_file_behind(tmp_path: Path):
    store = fixtures.store_file(tmp_path)

    with pytest.raises(decision_write.WriteRefused):
        decision_write.append_decision(
            tmp_path, _STORE, _entry(signer="owner (owner)"), authority=None
        )

    leftovers = [p.name for p in store.parent.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


# --- Task 1.4: the write reaches the ONE shipped predicate ---------------------------


def test_the_write_path_calls_the_shipped_validity_predicate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Monkeypatch the ONE shared predicate to reject; the write must refuse.

    This fails if a second validity path is ever introduced, because the write would
    then succeed while the shipped predicate says no.
    """
    store = fixtures.store_file(tmp_path)
    original = store.read_text(encoding="utf-8")

    monkeypatch.setattr(
        decision_store,
        "approval_is_valid",
        lambda entry, authority: (False, "stubbed refusal"),
    )

    with pytest.raises(decision_write.WriteRefused):
        decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)

    assert store.read_text(encoding="utf-8") == original


def test_the_refusal_reason_comes_from_the_shipped_predicate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Not just that it refused -- that it refused *because of* that predicate."""
    fixtures.store_file(tmp_path)
    monkeypatch.setattr(
        decision_store,
        "approval_is_valid",
        lambda entry, authority: (False, "sentinel-reason-42"),
    )

    with pytest.raises(decision_write.WriteRefused, match="sentinel-reason-42"):
        decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)


# --- Task 1.5: no git operation in the write path ------------------------------------


def test_the_write_succeeds_with_the_git_runner_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A decision write must neither depend on nor perform any git call (FR-140-023).

    Making the runner raise proves the path never touches it; a grep-only assertion
    would pass even if a git call arrived through an alias or helper.
    """
    from seshat import gitutil

    def _explode(*args: object, **kwargs: object):
        raise AssertionError("the decision write path must not invoke git")

    monkeypatch.setattr(gitutil, "run_subprocess", _explode)
    fixtures.store_file(tmp_path)

    receipt = decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)

    assert receipt.state == "pending_commit"


def test_a_written_decision_is_not_yet_visible_to_the_committed_store_reader(
    tmp_path: Path,
):
    """The boundary itself: a working-tree write is not authority.

    `store_files` selects from TRACKED paths, so an uncommitted decision is absent
    from the gate's view even though the file on disk contains it.
    """
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: empty store")

    decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)

    tracked_at_head = workspace.tracked_files_at_head()
    present = decision_store.store_files(tracked_at_head)
    # The FILE is tracked (committed empty), but its new decision is not at HEAD.
    committed = decision_write.decisions_at_head(workspace, _STORE)
    assert present == [_STORE]
    assert committed == [], "an uncommitted decision must not appear at HEAD"


def test_a_committed_decision_becomes_visible_at_head(tmp_path: Path):
    """The paired positive case. Without it, the test above passes vacuously if
    `decisions_at_head` simply always returns nothing."""
    workspace = fixtures.git_workspace(tmp_path)
    fixtures.store_file(tmp_path)
    workspace.commit_all("test: empty store")
    decision_write.append_decision(tmp_path, _STORE, _entry(), authority=None)

    workspace.commit_all("decision: net of returns")

    committed = decision_write.decisions_at_head(workspace, _STORE)
    assert [d["id"] for d in committed] == ["d-001"]
