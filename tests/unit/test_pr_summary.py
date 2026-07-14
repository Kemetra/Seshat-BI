"""Fixture-driven tests for the Friendly PR Reviewer presentation layer (spec 130).

Covers: ``mask()`` on each detectable shape + the DSN-URL non-coverage pin;
``pick_next_action()``; ``render_summary()`` on blocked / ok-with-warnings /
absent-envelope / empty-next-actions / absent-readiness inputs; determinism;
end-to-end redaction; ``classify_changes()``; the no-base honesty branch;
``compose_comment()``; ``find_existing()``.

No network, no DB, no clock -- every timestamp is an explicit argument.
"""

from __future__ import annotations

import copy

import pytest

from seshat.core import Finding, Severity
from seshat.pr_summary import (
    MARKER,
    NO_NEXT_ACTION,
    classify_changes,
    compose_comment,
    find_existing,
    mask,
    pick_next_action,
    render_summary,
)
from seshat.sarif import finding_fingerprint

pytestmark = pytest.mark.unit


# --- shared fixtures ---------------------------------------------------------


def _finding(
    rule_id: str = "S1",
    severity: Severity = Severity.ERROR,
    message: str = "mapping is not cleared",
    locator: str = "warehouse/silver/x.sql:12:3",
) -> dict:
    return Finding(rule_id, severity, message, locator).to_dict()


def _blocked_envelope() -> dict:
    return {
        "schema_version": "1.0",
        "outcome": "blocked",
        "checks_run": ["S1", "S2"],
        "changed_files": ["warehouse/silver/x.sql", "mappings/orders/source-map.yaml"],
        "changed_readiness_state": [],
        "affected_stages": ["mapping_ready", "gold_ready"],
        "findings": [
            _finding(
                "S1",
                Severity.ERROR,
                "grain is not confirmed",
                "mappings/orders/source-map.yaml:4",
            ),
            _finding(
                "S2",
                Severity.ERROR,
                "gold migration missing reconciliation",
                "warehouse/gold/orders.sql:9",
            ),
        ],
        "blocking_findings": [
            _finding(
                "S1",
                Severity.ERROR,
                "grain is not confirmed",
                "mappings/orders/source-map.yaml:4",
            ),
            _finding(
                "S2",
                Severity.ERROR,
                "gold migration missing reconciliation",
                "warehouse/gold/orders.sql:9",
            ),
        ],
        "next_actions": [
            "resolve the open grain question before silver work",
            "clear a named human approval for mapping_ready",
        ],
        "run_boundary": {
            "static_checks": "blocked",
            "live_validation": "not_run",
            "semantic_correctness_claimed": False,
        },
        "result_digest": "deadbeef",
    }


def _ok_with_warnings_envelope() -> dict:
    return {
        "schema_version": "1.0",
        "outcome": "ok",
        "checks_run": ["W1"],
        "changed_files": ["warehouse/gold/orders.sql"],
        "changed_readiness_state": [],
        "affected_stages": ["gold_ready"],
        "findings": [
            _finding(
                "W1",
                Severity.WARNING,
                "column naming deviates from convention",
                "warehouse/gold/orders.sql:3",
            ),
        ],
        "blocking_findings": [],
        "next_actions": ["review the naming deviation before next release"],
        "run_boundary": {
            "static_checks": "pass",
            "live_validation": "not_run",
            "semantic_correctness_claimed": False,
        },
        "result_digest": "cafebabe",
    }


def _readiness_fixture() -> dict:
    return {
        "table": "silver.orders",
        "source_id": "orders",
        "current_stage": "mapping_ready",
        "stages": {
            "source_ready": {
                "status": "pass",
                "evidence": ["x"],
                "blocking_reasons": [],
            },
            "mapping_ready": {
                "status": "blocked",
                "evidence": [],
                "blocking_reasons": ["grain is not confirmed for the source-map"],
            },
            "gold_ready": {
                "status": "blocked",
                "evidence": [],
                "blocking_reasons": ["gold migration missing reconciliation"],
            },
        },
        "evidence": [],
        "blocking_reasons": [],
        "approvals": [],
    }


# --- mask() -------------------------------------------------------------


def test_mask_redacts_email() -> None:
    assert (
        mask("contact jane.doe@example.com for help") == "contact [REDACTED] for help"
    )


def test_mask_redacts_ssn_like_number() -> None:
    assert mask("SSN on file: 123-45-6789") == "SSN on file: [REDACTED]"


def test_mask_redacts_long_digit_run() -> None:
    masked = mask("card 4111111111111111 flagged")
    assert "4111111111111111" not in masked
    assert "[REDACTED]" in masked


def test_mask_redacts_secret_assignment() -> None:
    assert mask("config had password: hunter2trustme") == "config had [REDACTED]"
    assert mask("token=abc123xyz999") == "[REDACTED]"


def test_mask_leaves_clean_text_unchanged() -> None:
    clean = "the mapping gate is blocked on grain certainty"
    assert mask(clean) == clean


def test_mask_is_idempotent() -> None:
    text = "email jane@example.com and token: abc123"
    once = mask(text)
    twice = mask(once)
    assert once == twice


def test_mask_does_not_cover_bare_dsn_url() -> None:
    """Documented v1 non-coverage (FR-009): a bare DSN/connection-URL is NOT
    masked by mask(). This PINS the known gap; it does not assert removal.

    Uses an IP host (not a letter-based TLD) so the credential segment does
    not incidentally collide with the reused email SHAPE (``user@host.tld``)
    -- that incidental overlap is a property of the DSN's own syntax, not a
    dedicated DSN detector, and is orthogonal to the documented gap this
    test pins: no DSN-URL-specific masking exists in v1.
    """
    dsn_message = (
        "connection failed for postgresql://svc_etl:s3cr3t@10.0.0.5:5432/warehouse"
    )
    assert mask(dsn_message) == dsn_message


# --- pick_next_action() ---------------------------------------------------


def test_pick_next_action_selects_exactly_one_by_rank() -> None:
    actions = [
        "resolve the open grain question before silver work",
        "clear a named human approval for mapping_ready",
    ]
    chosen = pick_next_action(actions)
    # "approval" category outranks "grain" in the refutation-first rank.
    assert chosen == "clear a named human approval for mapping_ready"


def test_pick_next_action_returns_none_on_empty() -> None:
    assert pick_next_action([]) is None


def test_pick_next_action_never_returns_two() -> None:
    actions = ["a missing artifact needs authoring", "a readiness blocker is recorded"]
    chosen = pick_next_action(actions)
    assert isinstance(chosen, str)
    assert "\n" not in chosen


def test_pick_next_action_is_deterministic_regardless_of_order() -> None:
    actions = ["z action mentions grain", "a action mentions approval sign-off"]
    assert pick_next_action(actions) == pick_next_action(list(reversed(actions)))


# --- render_summary(): blocked envelope -----------------------------------


def test_render_summary_blocked_names_stages_and_blockers() -> None:
    summary = render_summary(_blocked_envelope(), _readiness_fixture())
    assert summary.outcome == "blocked"
    assert "mapping_ready" in summary.text
    assert "gold_ready" in summary.text
    stage_names = {ss.stage for ss in summary.stage_statuses}
    assert stage_names == {"mapping_ready", "gold_ready"}
    for ss in summary.stage_statuses:
        assert ss.status == "blocked"  # verbatim from readiness fixture
    # two blockers listed in words (present-group since no base supplied)
    present_group = next(g for g in summary.blocker_groups if g.label == "present")
    assert len(present_group.lines) == 2
    assert any("grain is not confirmed" in line for line in present_group.lines)
    assert any("reconciliation" in line for line in present_group.lines)
    # required authority named, never self-granted
    assert summary.required_authority
    assert any("mapping_ready" in line for line in summary.required_authority)
    # exactly one next action
    assert summary.next_action == "clear a named human approval for mapping_ready"
    assert "clear a named human approval for mapping_ready" in summary.text
    # no merge-ready boolean field/value, no score anywhere (the boundary
    # note that this is a narrative, not a verdict, legitimately NAMES the
    # concept in prose -- it never emits a merge_ready field or value)
    assert "merge_ready" not in summary.text
    assert "%" not in summary.text


def test_render_summary_blocked_no_numeric_score_field() -> None:
    summary = render_summary(_blocked_envelope(), _readiness_fixture())
    for value in vars(summary).values():
        assert not isinstance(value, (int, float))


# --- render_summary(): ok-with-warnings envelope --------------------------


def test_render_summary_ok_with_warnings_is_not_blocked() -> None:
    readiness = {
        "table": "silver.orders",
        "current_stage": "gold_ready",
        "stages": {
            "gold_ready": {
                "status": "warning",
                "evidence": ["x"],
                "blocking_reasons": [],
            }
        },
        "approvals": [],
        "blocking_reasons": [],
    }
    summary = render_summary(_ok_with_warnings_envelope(), readiness)
    assert summary.outcome == "ok"
    assert "NOT blocked" in summary.text
    assert summary.warnings
    assert "worth a look" in summary.text.lower()
    assert not any(ss.status == "blocked" for ss in summary.stage_statuses)
    assert summary.next_action == "review the naming deviation before next release"
    assert "%" not in summary.text
    assert "merge_ready" not in summary.text


# --- honesty branches ------------------------------------------------------


def test_render_summary_absent_envelope_stops_honestly() -> None:
    summary = render_summary(None, _readiness_fixture())
    assert summary.outcome == "unproducible"
    assert summary.affected_artifacts == ()
    assert summary.stage_statuses == ()
    assert any("could not be produced" in u for u in summary.undetermined)
    assert "could not be produced" in summary.text


def test_render_summary_empty_next_actions_states_none_produced() -> None:
    envelope = _ok_with_warnings_envelope()
    envelope["next_actions"] = []
    summary = render_summary(envelope, _readiness_fixture())
    assert summary.next_action == NO_NEXT_ACTION
    assert any(NO_NEXT_ACTION in u for u in summary.undetermined)


def test_render_summary_absent_readiness_reports_unknown() -> None:
    summary = render_summary(_blocked_envelope(), None)
    assert all(ss.status == "unknown" for ss in summary.stage_statuses)
    assert any("absent" in u for u in summary.undetermined)
    assert "pass" not in [ss.status for ss in summary.stage_statuses]


def test_render_summary_non_file_locator_described_in_words() -> None:
    envelope = _blocked_envelope()
    envelope["findings"] = [
        _finding(
            "P2",
            Severity.ERROR,
            "commit message missing ticket ref",
            "(commit message)",
        )
    ]
    envelope["blocking_findings"] = envelope["findings"]
    summary = render_summary(envelope, _readiness_fixture())
    assert "a non-file check" in summary.text
    assert "(commit message)" in summary.text


def test_render_summary_surfaces_conflict_not_resolved() -> None:
    envelope = _blocked_envelope()
    readiness = _readiness_fixture()
    readiness["stages"]["mapping_ready"]["status"] = "pass"
    summary = render_summary(envelope, readiness)
    assert summary.conflicts
    assert any(
        "mapping_ready" in c and "pass" in c and "blocked" in c
        for c in summary.conflicts
    )


# --- determinism -----------------------------------------------------------


def test_render_summary_is_byte_identical_on_repeat_calls() -> None:
    envelope = _blocked_envelope()
    readiness = _readiness_fixture()
    first = render_summary(envelope, readiness, timestamp="2026-07-14T00:00:00Z")
    second = render_summary(
        copy.deepcopy(envelope),
        copy.deepcopy(readiness),
        timestamp="2026-07-14T00:00:00Z",
    )
    assert first.text == second.text
    assert first == second


# --- redaction end-to-end ---------------------------------------------------


def test_render_summary_masks_adversarial_finding_messages() -> None:
    envelope = _blocked_envelope()
    envelope["findings"] = [
        _finding(
            "S9",
            Severity.ERROR,
            "owner email jane.doe@example.com leaked in commit",
            "x.sql:1",
        ),
        _finding(
            "S9", Severity.ERROR, "SSN 123-45-6789 found in sample data", "x.sql:2"
        ),
        _finding("S9", Severity.ERROR, "card number 4111111111111111 found", "x.sql:3"),
        _finding(
            "S9", Severity.ERROR, "config leaked password: hunter2trustme", "x.sql:4"
        ),
        _finding(
            "S9",
            Severity.ERROR,
            "dsn leaked: postgresql://svc:s3cr3t@10.0.0.9/db",
            "x.sql:5",
        ),
    ]
    envelope["blocking_findings"] = envelope["findings"]
    summary = render_summary(envelope, _readiness_fixture())
    assert "jane.doe@example.com" not in summary.text
    assert "123-45-6789" not in summary.text
    assert "4111111111111111" not in summary.text
    assert "hunter2trustme" not in summary.text
    assert "[REDACTED]" in summary.text
    # documented v1 gap: the DSN URL (IP host, no email-shape collision)
    # passes through un-redacted (pinned, not fixed)
    assert "postgresql://svc:s3cr3t@10.0.0.9/db" in summary.text


# --- classify_changes() ------------------------------------------------------


def test_classify_changes_disjoint_and_covers_union() -> None:
    shared = Finding("S1", Severity.ERROR, "shared finding", "a.sql:1")
    head_only = Finding("S2", Severity.ERROR, "new finding", "b.sql:1")
    base_only_fp = finding_fingerprint(
        Finding("S3", Severity.ERROR, "old finding", "c.sql:1")
    )
    base = {finding_fingerprint(shared), base_only_fp}
    head = [shared, head_only]

    result = classify_changes(base, head)

    assert set(result.new) == {finding_fingerprint(head_only)}
    assert set(result.resolved) == {base_only_fp}
    assert set(result.carried_over) == {finding_fingerprint(shared)}
    # pairwise disjoint
    assert not (set(result.new) & set(result.resolved))
    assert not (set(result.new) & set(result.carried_over))
    assert not (set(result.resolved) & set(result.carried_over))
    # covers the union of base and head fingerprints
    head_fps = {finding_fingerprint(f) for f in head}
    union = base | head_fps
    covered = set(result.new) | set(result.resolved) | set(result.carried_over)
    assert covered == union


def test_classify_changes_keyed_on_fingerprint_identity() -> None:
    base_finding = Finding("S1", Severity.ERROR, "password: abc123 leaked", "a.sql:1")
    head_finding = Finding("S1", Severity.ERROR, "[REDACTED] leaked", "a.sql:1")
    base = {finding_fingerprint(base_finding)}
    result = classify_changes(base, [head_finding])
    # different message text (masked position) -> different fingerprint identity,
    # honestly reported as new + resolved, not silently carried over.
    assert finding_fingerprint(base_finding) != finding_fingerprint(head_finding)
    assert set(result.new) == {finding_fingerprint(head_finding)}
    assert set(result.resolved) == {finding_fingerprint(base_finding)}
    assert result.carried_over == ()


def test_render_summary_with_base_labels_new_resolved_pre_existing() -> None:
    envelope = _blocked_envelope()
    findings = [
        Finding(
            **{k: v for k, v in f.items() if k != "severity"},
            severity=Severity(f["severity"]),
        )
        for f in envelope["findings"]
    ]
    shared_fp = finding_fingerprint(findings[0])
    base_only_fp = finding_fingerprint(
        Finding("S9", Severity.ERROR, "an old resolved finding", "z.sql:1")
    )
    base = [shared_fp, base_only_fp]
    summary = render_summary(envelope, _readiness_fixture(), base_fingerprints=base)
    labels = {g.label for g in summary.blocker_groups}
    assert labels == {"new", "resolved", "carried_over"}
    assert "NEW in this PR" in summary.text
    assert "RESOLVED by this PR" in summary.text
    assert "Pre-existing / carried over" in summary.text
    carried = next(g for g in summary.blocker_groups if g.label == "carried_over")
    assert carried.lines  # the shared finding shows up as carried-over


def test_render_summary_no_base_states_undeterminable_never_all_new() -> None:
    summary = render_summary(
        _blocked_envelope(), _readiness_fixture(), base_fingerprints=None
    )
    assert any("could not be determined" in u for u in summary.undetermined)
    labels = {g.label for g in summary.blocker_groups}
    assert labels == {"present"}
    assert "new" not in labels


# --- compose_comment() / find_existing() ------------------------------------


def test_compose_comment_carries_stable_marker_and_is_deterministic() -> None:
    summary = render_summary(_blocked_envelope(), _readiness_fixture())
    first = compose_comment(summary)
    second = compose_comment(render_summary(_blocked_envelope(), _readiness_fixture()))
    assert first.marker == MARKER
    assert MARKER in first.body
    assert first.body == second.body


def test_compose_comment_masks_secrets() -> None:
    envelope = _blocked_envelope()
    envelope["findings"] = [
        _finding("S9", Severity.ERROR, "token: abc123def456 exposed", "x.sql:1")
    ]
    envelope["blocking_findings"] = envelope["findings"]
    summary = render_summary(envelope, _readiness_fixture())
    comment = compose_comment(summary)
    assert "abc123def456" not in comment.body


def test_find_existing_targets_matching_marker_for_update() -> None:
    prior = ["some other comment", f"{MARKER}\nold body"]
    action, index = find_existing(prior)
    assert action == "update"
    assert index == 1


def test_find_existing_creates_when_no_marker_present() -> None:
    action, index = find_existing(["totally unrelated comment"])
    assert action == "create"
    assert index is None


def test_find_existing_never_creates_second_when_marker_matches() -> None:
    prior = [f"{MARKER}\nfirst"]
    action, _index = find_existing(prior)
    assert action == "update"
