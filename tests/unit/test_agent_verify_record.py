"""Unit tests for VerifyRecord assembly, serialization, and the owner-
controlled publication gate (spec 129, US3/US4).

Covers: the per-verdict invariant (never coerced), no aggregate/score/rank
key anywhere in the rendered document (SC-003), output containment under
`.seshat-output/` (SC-004), the disclosure scan blocking a seeded secret /
absolute path (SC-006), and the seeded-drift / footprint fixtures (US3).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from seshat.agent_verify import checks
from seshat.agent_verify.model import PerCheckResult
from seshat.agent_verify.record import (
    build_record,
    disclosure_report,
    publish_record,
    tool_version,
    write_record,
)
from seshat.agent_verify.targets import resolve_target

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_FORBIDDEN_KEYS = ("score", "rank", "pass_rate", "grade", "overall", "certified")


def _pass(check_id: str, evidence_class: str = "per_target") -> PerCheckResult:
    return PerCheckResult(
        check_id=check_id,
        verdict="PASS",
        evidence_class=evidence_class,
        evidence=("ok",),
    )


def _blocked(check_id: str, evidence_class: str = "per_target") -> PerCheckResult:
    return PerCheckResult(
        check_id=check_id,
        verdict="BLOCKED",
        evidence_class=evidence_class,
        blocking_reasons=("something is wrong",),
    )


def _unavailable(check_id: str, evidence_class: str = "per_target") -> PerCheckResult:
    return PerCheckResult(
        check_id=check_id,
        verdict="UNAVAILABLE",
        evidence_class=evidence_class,
        unavailable_reason="no surface",
    )


# --- PerCheckResult invariant (never coerced) -------------------------------


def test_pass_requires_nonempty_evidence_and_no_reasons() -> None:
    with pytest.raises(ValueError):
        PerCheckResult(check_id="x", verdict="PASS", evidence_class="per_target")
    with pytest.raises(ValueError):
        PerCheckResult(
            check_id="x",
            verdict="PASS",
            evidence_class="per_target",
            evidence=("e",),
            blocking_reasons=("nope",),
        )


def test_blocked_requires_at_least_one_reason() -> None:
    with pytest.raises(ValueError):
        PerCheckResult(check_id="x", verdict="BLOCKED", evidence_class="per_target")


def test_unavailable_requires_a_reason_and_no_blocking_reasons() -> None:
    with pytest.raises(ValueError):
        PerCheckResult(check_id="x", verdict="UNAVAILABLE", evidence_class="per_target")
    with pytest.raises(ValueError):
        PerCheckResult(
            check_id="x",
            verdict="UNAVAILABLE",
            evidence_class="per_target",
            unavailable_reason="no surface",
            blocking_reasons=("also this",),
        )


def test_verdict_and_evidence_class_are_closed_vocabularies() -> None:
    with pytest.raises(ValueError):
        PerCheckResult(
            check_id="x",
            verdict="PARTIAL_PASS",
            evidence_class="per_target",
            evidence=("e",),
        )
    with pytest.raises(ValueError):
        PerCheckResult(
            check_id="x", verdict="PASS", evidence_class="global", evidence=("e",)
        )


# --- record assembly and no-aggregate truthfulness (SC-003) ---------------


def test_build_record_reads_tool_version_from_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    record = build_record("claude", [_pass("install_discovery")], repo_root=tmp_path)
    assert record.tool_version == "9.9.9"
    assert record.target == "claude"


def test_tool_version_never_fabricated_when_pyproject_absent(tmp_path: Path) -> None:
    assert tool_version(tmp_path) == "unknown"


@pytest.mark.parametrize(
    "results",
    [
        [_pass("a"), _pass("b", "shared_baseline")],
        [_pass("a"), _blocked("b")],
        [_pass("a"), _unavailable("b", "shared_baseline")],
        [_blocked("a"), _unavailable("b")],
        [_pass("a"), _blocked("b"), _unavailable("c", "shared_baseline")],
    ],
)
def test_document_has_no_aggregate_score_rank_or_certified_key_in_any_combination(
    results: list[PerCheckResult],
) -> None:
    record = build_record(
        "claude", results, repo_root=_REPO, generated_at="2026-07-14T00:00:00+00:00"
    )
    document = record.to_document()
    rendered = json.dumps(document).lower()
    for forbidden in _FORBIDDEN_KEYS:
        assert forbidden not in rendered, (
            f"found forbidden token {forbidden!r} in record"
        )
    assert set(document.keys()) == {
        "schema_version",
        "target",
        "tool_version",
        "generated_at",
        "static_vs_live_boundary",
        "results",
    }
    for item in document["results"]:
        assert set(item.keys()) == {
            "check_id",
            "verdict",
            "evidence_class",
            "evidence",
            "blocking_reasons",
            "unavailable_reason",
        }


def test_record_carries_static_vs_live_boundary_and_generation_time() -> None:
    record = build_record(
        "codex", [_pass("a")], repo_root=_REPO, generated_at="2026-07-14T12:00:00+00:00"
    )
    document = record.to_document()
    assert document["generated_at"] == "2026-07-14T12:00:00+00:00"
    assert "static" in document["static_vs_live_boundary"]
    assert document["target"] == "codex"


# --- output containment (SC-004) --------------------------------------------


def test_write_record_stays_under_seshat_output(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    record = build_record("claude", [_pass("a")], repo_root=tmp_path)
    written = write_record(
        record, repo_root=tmp_path, output=".seshat-output/agent-verify/record.json"
    )
    assert written.is_relative_to(tmp_path / ".seshat-output")
    document = json.loads(written.read_text(encoding="utf-8"))
    assert document["target"] == "claude"


def test_write_record_refuses_an_uncontained_output_path(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    record = build_record("claude", [_pass("a")], repo_root=tmp_path)
    with pytest.raises(ValueError):
        write_record(record, repo_root=tmp_path, output="somewhere-else/record.json")


# --- disclosure scan + owner-controlled publication (SC-006) --------------


def test_disclosure_report_passes_for_a_clean_record() -> None:
    record = build_record(
        "claude",
        [_pass("install_discovery")],
        repo_root=_REPO,
        generated_at="2026-07-14T00:00:00Z",
    )
    report = disclosure_report(record)
    assert report["status"] == "pass"
    assert report["findings"] == []


def test_publish_refused_without_explicit_intent() -> None:
    record = build_record("claude", [_pass("a")], repo_root=_REPO)
    with pytest.raises(ValueError):
        publish_record(record, requested=False)


def test_publish_refused_when_evidence_embeds_a_secret_or_absolute_path() -> None:
    seeded = PerCheckResult(
        check_id="install_discovery",
        verdict="BLOCKED",
        evidence_class="per_target",
        blocking_reasons=("connection string leaked: postgres://user:pw@host/db",),
    )
    record = build_record("claude", [seeded], repo_root=_REPO)
    report = disclosure_report(record)
    assert report["status"] == "blocked"
    with pytest.raises(ValueError):
        publish_record(record, requested=True)


def test_publish_refused_for_seeded_absolute_path_finding() -> None:
    seeded = PerCheckResult(
        check_id="uninstall_integrity",
        verdict="PASS",
        evidence_class="per_target",
        evidence=("/Users/example-owner/Seshat_BI/integrations/claude-code",),
    )
    record = build_record("claude", [seeded], repo_root=_REPO)
    with pytest.raises(ValueError):
        publish_record(record, requested=True)


def test_publish_confirmed_when_intent_given_and_disclosure_clean() -> None:
    record = build_record("codex", [_pass("a")], repo_root=_REPO)
    outcome = publish_record(record, requested=True)
    assert outcome["status"] == "publish_intent_confirmed"
    assert outcome["disclosure"]["status"] == "pass"


# --- US3: seeded drift + footprint fixtures against the real check ---------


def test_seeded_drift_fixture_makes_update_integrity_blocked_and_names_path(
    tmp_path: Path,
) -> None:
    target_spec = resolve_target("claude")
    bundle_root = tmp_path / target_spec.provenance_manifest
    bundle_root.parent.mkdir(parents=True, exist_ok=True)
    generated_file = bundle_root.parent / "commands" / "seshat-check.md"
    generated_file.parent.mkdir(parents=True, exist_ok=True)
    generated_file.write_bytes(b"original content\n")
    manifest = {
        "entries": [
            {
                "destination": "commands/seshat-check.md",
                "output_sha256": hashlib.sha256(
                    generated_file.read_bytes()
                ).hexdigest(),
            }
        ]
    }
    bundle_root.write_text(json.dumps(manifest), encoding="utf-8")

    # Seed drift: edit one generated file's content without touching the manifest.
    generated_file.write_bytes(b"hand-edited drift\n")

    result = checks.update_integrity_check(target_spec, tmp_path)
    assert result.verdict == "BLOCKED"
    assert any(
        "commands/seshat-check.md" in reason for reason in result.blocking_reasons
    )

    record = build_record("claude", [result], repo_root=_REPO)
    document = record.to_document()
    assert any(
        "commands/seshat-check.md" in reason
        for reason in document["results"][0]["blocking_reasons"]
    )


def test_footprint_enumeration_fixture_lists_installed_paths(tmp_path: Path) -> None:
    target_spec = resolve_target("codex")
    manifest_path = tmp_path / target_spec.footprint_source
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"entries": [{"destination": "skills/seshat-bi/SKILL.md"}]}),
        encoding="utf-8",
    )
    result = checks.uninstall_integrity_check(target_spec, tmp_path)
    assert result.verdict == "PASS"
    assert "skills/seshat-bi/SKILL.md" in result.evidence
