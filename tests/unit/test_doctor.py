"""Tests for E7 -- ``retail doctor`` read-only drift digest.

Doctor aggregates existing read-only checks + a load-bearing-doc probe into a
findings digest. It reads and reports, never fixes; emits no numeric score; is
advisory (exit 0) by default and only fails under --strict. It adds no @register
rule.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from seshat.core import RuleContext
from seshat.doctor import collect_findings, format_digest, run_doctor
from tests.unit._gitfix import make_kit_self_repo

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap(repo: Path) -> None:
    """Make `repo` look like the KIT ITSELF so the KIT_SELF checks run (#377).

    Since Spec A, doctor SKIPS the aggregated kit-self checks in a repo that is not
    the kit (to agree with `check` and not over-report on a foreign repo). So a test
    that wants to see GENUINE drift must shape the fixture as the kit. Substrate
    alone no longer qualifies -- `seshat init` writes that into consumer repos too
    (issue #486).
    """
    (repo / ".seshat").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        _REPO_ROOT / ".seshat" / "kit-source.yaml", repo / ".seshat" / "kit-source.yaml"
    )
    shutil.copyfile(
        _REPO_ROOT / ".seshat" / "compass.yaml", repo / ".seshat" / "compass.yaml"
    )
    make_kit_self_repo(repo)


def _ctx_missing_everything(tmp_path: Path) -> RuleContext:
    # A BOOTSTRAPPED repo that is nonetheless missing its manifests -> genuine
    # drift the checks fire on (fail-loud), giving a non-empty digest.
    _bootstrap(tmp_path)
    return RuleContext(repo_root=tmp_path, tracked_files=())


def test_collect_findings_on_bootstrapped_repo_with_drift_reports_it(
    tmp_path: Path,
) -> None:
    findings = collect_findings(_ctx_missing_everything(tmp_path))
    assert findings, "a bootstrapped repo missing its manifests should surface drift"
    # the load-bearing probe must flag the missing glossary
    assert any("glossary.md" in f.message for f in findings)


def test_format_digest_lists_findings_and_no_score(tmp_path: Path) -> None:
    findings = collect_findings(_ctx_missing_everything(tmp_path))
    text = format_digest(findings)
    assert "finding(s)" in text
    # no numeric score / percentage in the digest (hard rule #9)
    assert "%" not in text
    assert "score" not in text.lower()


def test_format_digest_clean_message() -> None:
    assert "no drift found" in format_digest([])


def test_run_doctor_advisory_exits_zero_even_with_findings(tmp_path: Path) -> None:
    # default (advisory): exit 0 despite findings -> never a second gate.
    assert run_doctor(tmp_path, strict=False) == 0


def test_run_doctor_strict_exits_nonzero_on_findings(tmp_path: Path) -> None:
    # Bootstrap so the kit-self checks run and surface genuine drift (missing
    # manifests) -- strict must then exit non-zero. A non-bootstrapped repo is
    # covered separately in test_doctor_kit_self_skip.py (strict stays 0).
    _bootstrap(tmp_path)
    assert run_doctor(tmp_path, strict=True) == 1


def test_run_doctor_on_real_repo_is_clean_and_advisory() -> None:
    # Against the real committed tree, the aggregated checks should be clean and
    # doctor exits 0. (If this ever fails, the repo genuinely has drift -- which is
    # exactly what doctor is meant to surface.)
    repo_root = Path(__file__).resolve().parents[2]
    assert run_doctor(repo_root, strict=True) == 0


def test_doctor_adds_no_register_rule() -> None:
    # E7 is a CLI helper, not a rule: DOCTOR must not appear in the rule registry.
    import importlib

    import seshat.rules  # noqa: F401
    from seshat import registry

    importlib.reload(seshat.rules)
    ids = {r.id for r in registry.all_rules()}
    assert "DOCTOR" not in ids


# ---------------------------------------------------------------------------
# M8 -- machine-readable output (deliverable 1)
# ---------------------------------------------------------------------------


def test_doctor_json_payload_reuses_the_finding_serializer(tmp_path: Path) -> None:
    """M8 deliverable 1: a machine-readable digest.

    Reuses the SHIPPED `Finding.to_dict()` / `FindingDict` shape that
    `check --format json` already emits, so an agent parses one vocabulary
    across both verbs rather than two.
    """
    from seshat.doctor import build_digest_payload

    findings = collect_findings(_ctx_missing_everything(tmp_path))
    payload = build_digest_payload(findings)

    # Non-vacuity: an empty payload must NOT satisfy this test.
    assert payload["findings"], (
        "the fixture has genuine drift; findings must be present"
    )
    assert any("glossary.md" in f["message"] for f in payload["findings"])
    # every entry is the shipped FindingDict shape, not a new one
    for entry in payload["findings"]:
        assert set(entry) >= {"rule_id", "severity", "message", "locator"}
    # hard rule #9: categorical only, never a numeric health score
    assert "score" not in payload
    assert "percent" not in payload


def test_doctor_json_is_valid_json_and_advisory_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--format json` prints parseable JSON and stays advisory (exit 0)."""
    import json

    _bootstrap(tmp_path)
    code = run_doctor(tmp_path, strict=False, output_format="json")
    out = capsys.readouterr().out

    assert code == 0
    parsed = json.loads(out)  # raises if the payload is not valid JSON
    assert parsed["findings"], "bootstrapped-but-empty repo has drift to report"


def test_doctor_cli_accepts_format_json() -> None:
    """M8: the CLI surface must expose the machine-readable format.

    Measured 2026-08-16 and again 2026-08-21: `doctor --format json` exited 2
    because the subparser accepted only --repo/--strict. This asserts the flag
    parses AND that the choice set is constrained (a free-form string would let
    a typo silently fall back to text).
    """
    from seshat.cli import _build_parser

    parser = _build_parser("seshat")
    args = parser.parse_args(["doctor", "--format", "json"])
    assert getattr(args, "output_format", None) == "json"


def test_doctor_cli_default_format_is_text() -> None:
    """Backward compatibility: the default surface must not become JSON."""
    from seshat.cli import _build_parser

    parser = _build_parser("seshat")
    args = parser.parse_args(["doctor"])
    assert getattr(args, "output_format", "text") == "text"


# ---------------------------------------------------------------------------
# M8 -- grouping + repair hints (deliverables 2 and 3)
# ---------------------------------------------------------------------------


def test_digest_groups_findings_by_rule_area(tmp_path: Path) -> None:
    """M8 deliverable 2: grouped, not one flat severity list.

    Grouping is DERIVED from the existing `rule_id`, deliberately not a new
    parallel classification system.
    """
    findings = collect_findings(_ctx_missing_everything(tmp_path))
    text = format_digest(findings)

    rule_ids = {f.rule_id for f in findings}
    assert len(rule_ids) > 1, "fixture must span >1 rule for grouping to mean anything"
    # every distinct rule area appears as its own group header line
    for rid in rule_ids:
        assert f"{rid}:" in text, f"no group header for {rid}"


def test_every_finding_carries_a_repair_hint(tmp_path: Path) -> None:
    """M8 deliverable 3: actionable, non-mutating repair hints."""
    from seshat.doctor import build_digest_payload

    payload = build_digest_payload(collect_findings(_ctx_missing_everything(tmp_path)))
    assert payload["findings"]
    for entry in payload["findings"]:
        assert entry.get("repair_hint"), f"no repair hint for {entry['rule_id']}"


def test_repair_hints_differ_per_rule_area(tmp_path: Path) -> None:
    """Non-vacuity: one constant hint string would satisfy a presence check.

    A hint that says the same thing for every rule is not actionable, so assert
    the hints actually DISCRIMINATE between rule areas.
    """
    from seshat.doctor import build_digest_payload

    payload = build_digest_payload(collect_findings(_ctx_missing_everything(tmp_path)))
    by_rule = {e["rule_id"]: e["repair_hint"] for e in payload["findings"]}
    assert len(by_rule) > 1, "fixture must span >1 rule"
    assert len(set(by_rule.values())) > 1, "hints are a constant, not per-area guidance"


def test_repair_hints_are_inert_text_not_commands_to_run(tmp_path: Path) -> None:
    """A hint must never mutate anything: doctor reads and reports, never fixes.

    Guards the M8 constraint "repair hints that do not modify files" at the data
    level -- the hint is a string, and building the payload runs no subprocess.
    """
    import subprocess

    from seshat.doctor import build_digest_payload

    called: list[object] = []
    real_run = subprocess.run

    def _tripwire(*a: object, **k: object):  # pragma: no cover - must not fire
        called.append(a)
        return real_run(*a, **k)  # type: ignore[arg-type]

    subprocess.run = _tripwire  # type: ignore[assignment]
    try:
        payload = build_digest_payload(
            collect_findings(_ctx_missing_everything(tmp_path))
        )
    finally:
        subprocess.run = real_run  # type: ignore[assignment]

    assert payload["findings"]
    assert not called, "building the digest executed a subprocess"
    for entry in payload["findings"]:
        assert isinstance(entry["repair_hint"], str)


# ---------------------------------------------------------------------------
# M8 -- agent-safe next action (deliverable 4)
# ---------------------------------------------------------------------------


def test_digest_names_a_next_allowed_action() -> None:
    """M8 deliverable 4 / Desired Output: "next allowed action: ...".

    The 2026-08-16 measurement recorded the gap precisely: the digest "ends by
    pointing at `seshat check`, not at a next action". This asserts the digest
    NAMES the action.
    """
    repo_root = Path(__file__).resolve().parents[2]
    from seshat.doctor import format_digest_with_next_action

    text = format_digest_with_next_action([], repo_root)
    assert "next allowed action:" in text


def test_next_action_reuses_the_shipped_readiness_vocabulary() -> None:
    """Reuse `next`'s answer -- never a second readiness model.

    Circular-fixture guard: the expectation is read from the SHIPPED producer
    against the REAL repo, not hand-written here, so this test cannot silently
    agree with a wrong implementation.
    """
    repo_root = Path(__file__).resolve().parents[2]
    from seshat.agent_next import build_agent_next_document
    from seshat.doctor import next_allowed_action

    expected = build_agent_next_document(repo_root, None).get("next_allowed_action")
    assert expected, "the shipped producer must yield an action on the real repo"
    assert next_allowed_action(repo_root) == expected


def test_digest_keeps_the_gate_authority_pointer() -> None:
    """The `check` pointer is deliberate governance, not noise.

    doctor must never read as a second gate (Principle I): the digest says the
    `check` exit code remains the authority. M8 adds a next action; it does not
    license removing that boundary marker.
    """
    repo_root = Path(__file__).resolve().parents[2]
    from seshat.doctor import format_digest_with_next_action

    text = format_digest_with_next_action([], repo_root)
    assert "check" in text and "authority" in text


def test_doctor_next_action_grants_no_approval_and_moves_no_stage() -> None:
    """Naming an action must not BE the action (Principle V)."""
    repo_root = Path(__file__).resolve().parents[2]
    from seshat.doctor import format_digest_with_next_action

    text = format_digest_with_next_action([], repo_root).lower()
    for forbidden in ("approved", "granted", "advanced to", "now passes"):
        assert forbidden not in text, f"digest implies authority it lacks: {forbidden}"
