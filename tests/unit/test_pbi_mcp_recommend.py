"""One test per issue-#450 section-7 recommendation case, plus the advisory
record's write-once contract. Pure-function tests: facts in, record out."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbi_mcp import recommend as rec_mod
from seshat.pbi_mcp.detect import (
    ABSENT,
    APPROVAL_ABSENT,
    APPROVAL_RECORDED,
    CONFIG_ABSENT,
    CONFIG_FORBIDDEN_FLAG,
    CONFIG_READ_ONLY,
    CONFIG_WRITE_MODE,
    PRESENT,
    READINESS_NOT_PASS,
    READINESS_PASS,
    DetectedFacts,
)
from seshat.pbi_mcp.recommend import (
    ADVISORY_RELPATH,
    INTENTS,
    AdvisoryWriteError,
    Recommendation,
    recommend,
    render_advisory,
    write_advisory,
)

pytestmark = pytest.mark.unit


def _facts(**overrides: object) -> DetectedFacts:
    base = {
        "node_runtime": PRESENT,
        "vendored_runtime": PRESENT,
        "mcp_config": CONFIG_READ_ONLY,
        "pbip_project": PRESENT,
        "target": "orders",
        "semantic_model_ready": READINESS_PASS,
        "semantic_ready_tables": ("orders",),
        "target_semantic_model_ready": READINESS_PASS,
        "dashboard_ready": READINESS_PASS,
        "dashboard_ready_tables": ("orders",),
        "dashboard_design_approval": APPROVAL_RECORDED,
        "publish_ready_approval": APPROVAL_ABSENT,
        "official_report_skills": (
            "powerbi-report-design",
            "powerbi-report-authoring",
        ),
    }
    base.update(overrides)
    return DetectedFacts(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# section-7 cases 1..8, each a DISTINCT surface
# --------------------------------------------------------------------------- #


def test_case1_model_edit_ready_names_local_mcp_but_stays_parked() -> None:
    result = recommend("model-edit", _facts())
    assert result.surface == "local-modeling-mcp"
    assert result.blocked
    assert "F016 remains parked" in " ".join(result.missing_prerequisites)


def test_model_edit_requires_an_exact_target() -> None:
    result = recommend("model-edit", _facts(target=None))
    assert result.blocked
    assert "--target" in " ".join(result.missing_prerequisites)


def test_case2_published_query_routes_to_remote_server() -> None:
    result = recommend("published-query", _facts())
    assert result.surface == "remote-powerbi-mcp"
    joined = " ".join(result.missing_prerequisites)
    assert "tenant setting" in joined
    assert "Build permission" in joined
    assert "Copilot license" in joined
    assert "stop" in result.next_human_step
    assert result.blocked


def test_case3_formatting_stays_on_the_pbir_adapter() -> None:
    result = recommend("report-formatting", _facts())
    assert result.surface == "pbir-authoring-adapter"
    assert not result.blocked


def test_native_report_authoring_allows_compatible_discovered_skill() -> None:
    result = recommend("report-authoring", _facts())
    assert result.surface == "official-powerbi-report-authoring"
    assert result.blocked is False
    assert result.missing_prerequisites == ()
    assert "PBIR" in result.next_human_step


def test_report_authoring_blocks_without_compatible_discovery() -> None:
    result = recommend("report-authoring", _facts(official_report_skills=()))
    assert result.blocked
    assert "discoverable" in " ".join(result.missing_prerequisites)


def test_report_authoring_requires_an_exact_target() -> None:
    result = recommend("report-authoring", _facts(target=None))
    assert result.blocked
    assert "--target" in " ".join(result.missing_prerequisites)


def test_report_authoring_fails_closed_without_design_approval() -> None:
    result = recommend(
        "report-authoring",
        _facts(dashboard_design_approval=APPROVAL_ABSENT),
    )
    assert result.surface == "official-powerbi-report-authoring"
    assert result.blocked
    assert "dashboard_ready approval" in " ".join(result.missing_prerequisites)


def test_report_authoring_refuses_a_dashboard_pass_without_its_semantic_stage() -> None:
    """A later stage can never stand in for the one before it (Codex P2, #597).

    The record is internally inconsistent: the target claims dashboard_ready =
    pass while no semantic_model_ready pass names it. Routing authoring here
    would skip a readiness stage on the strength of a hand-edited later stage.
    """
    result = recommend(
        "report-authoring",
        _facts(target_semantic_model_ready=READINESS_NOT_PASS),
    )
    assert result.blocked
    joined = " ".join(result.missing_prerequisites)
    assert "semantic_model_ready" in joined
    assert "mappings/orders/readiness-status.yaml" in joined
    assert "stages cannot be skipped" in result.why


def test_report_authoring_refuses_another_tables_semantic_pass() -> None:
    """The repo-wide semantic fold reads `pass` whenever ANY table passes, so a
    target-scoped gate must check membership, not the folded status."""
    result = recommend(
        "report-authoring",
        _facts(
            semantic_model_ready=READINESS_PASS,
            semantic_ready_tables=("returns",),
            target_semantic_model_ready=READINESS_NOT_PASS,
        ),
    )
    assert result.blocked
    assert "semantic_model_ready" in " ".join(result.missing_prerequisites)


def test_report_authoring_gate_sentence_names_semantic_and_approval() -> None:
    result = recommend("report-authoring", _facts())
    assert "semantic_model_ready = pass" in result.why
    assert "dashboard_ready approval" in result.why
    assert result.blocked is False


def test_report_formatting_requires_target_semantic_and_design_approval() -> None:
    result = recommend(
        "report-formatting",
        _facts(
            target_semantic_model_ready=READINESS_NOT_PASS,
            dashboard_design_approval=APPROVAL_ABSENT,
        ),
    )
    assert result.blocked
    joined = " ".join(result.missing_prerequisites)
    assert "semantic_model_ready" in joined
    assert "dashboard_ready approval" in joined


def test_case4_desktop_verification_routes_to_desktop_bridge() -> None:
    result = recommend("desktop-verification", _facts())
    assert result.surface == "desktop-bridge"
    assert "never in CI" in " ".join(result.missing_prerequisites)


def test_case5_db_connectivity_routes_to_gateway_and_service() -> None:
    result = recommend("db-connectivity", _facts())
    assert result.surface == "gateway-and-service"


def test_case6_readiness_not_passed_blocks_and_names_the_gate() -> None:
    result = recommend(
        "model-edit",
        _facts(target_semantic_model_ready=READINESS_NOT_PASS),
    )
    assert result.surface == "blocked-on-semantic-readiness"
    assert result.blocked
    assert "semantic_model_ready" in result.why


def test_case7_ci_routes_to_deterministic_file_validation() -> None:
    result = recommend("ci-validation", _facts(node_runtime=ABSENT))
    assert result.surface == "pbip-file-validation"
    assert "never" in result.why  # Desktop is never required
    assert "graceful skip" in result.why


def test_case8_sensitive_production_routes_to_hardened_read_only() -> None:
    result = recommend("sensitive-production", _facts())
    assert result.surface == "read-only-hardened"
    assert "Service Principal" in result.why or "Service-Principal" in result.why


def test_all_intent_surfaces_are_distinct_except_blocked_variants() -> None:
    surfaces = {recommend(intent, _facts()).surface for intent in INTENTS}
    surfaces.add(
        recommend("model-edit", _facts(target_semantic_model_ready="missing")).surface
    )
    assert len(surfaces) == 9


# --------------------------------------------------------------------------- #
# prerequisites + hard refusals inside case 1
# --------------------------------------------------------------------------- #


def test_missing_runtime_and_config_become_prerequisites() -> None:
    result = recommend(
        "model-edit",
        _facts(node_runtime=ABSENT, vendored_runtime=ABSENT, mcp_config=CONFIG_ABSENT),
    )
    joined = " ".join(result.missing_prerequisites)
    assert "Node.js 20+" in joined
    assert ".mcp.json.example" in joined
    assert result.blocked


def test_write_mode_config_is_a_prerequisite_naming_readonly() -> None:
    result = recommend("model-edit", _facts(mcp_config=CONFIG_WRITE_MODE))
    assert "--readonly" in " ".join(result.missing_prerequisites)


def test_skipconfirmation_config_blocks_the_recommendation() -> None:
    result = recommend("model-edit", _facts(mcp_config=CONFIG_FORBIDDEN_FLAG))
    assert result.blocked
    assert "--skipconfirmation" in " ".join(result.missing_prerequisites)


def test_unknown_intent_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown intent"):
        recommend("publish-everything", _facts())


def test_parser_intent_choices_match_the_library_vocabulary() -> None:
    from seshat.cli.parser_pbi_mcp import _INTENT_CHOICES

    assert _INTENT_CHOICES == INTENTS


# --------------------------------------------------------------------------- #
# advisory record: explicit, write-once, grants nothing, no score
# --------------------------------------------------------------------------- #


def _any_rec() -> Recommendation:
    return recommend("model-edit", _facts())


def test_advisory_written_once_then_refused(tmp_path: Path) -> None:
    written = write_advisory(
        tmp_path, _facts(), _any_rec(), generated_at="2026-07-24T00:00:00Z"
    )
    assert written == tmp_path / ADVISORY_RELPATH
    text = written.read_text(encoding="utf-8")
    assert "schema_version: 2" in text
    assert "grants no approval" in text
    with pytest.raises(AdvisoryWriteError, match="write-once"):
        write_advisory(
            tmp_path, _facts(), _any_rec(), generated_at="2026-07-24T00:00:01Z"
        )


def test_advisory_render_is_deterministic_ascii_yaml() -> None:
    stamp = "2026-07-24T00:00:00Z"
    first = render_advisory(_facts(), _any_rec(), stamp)
    second = render_advisory(_facts(), _any_rec(), stamp)
    assert first == second
    assert first.isascii()
    import yaml

    parsed = yaml.safe_load(first)
    assert parsed["schema_version"] == rec_mod.SCHEMA_VERSION
    assert parsed["recommendation"]["surface"] == "local-modeling-mcp"
    assert parsed["detected"]["semantic_model_ready"] == "pass"
    assert parsed["detected"]["dashboard_ready"] == "pass"
    assert "score" not in first.lower()


def test_advisory_parses_with_blocked_case_and_prerequisites(
    tmp_path: Path,
) -> None:
    facts = _facts(semantic_model_ready=READINESS_NOT_PASS)
    blocked = recommend("model-edit", facts)
    written = write_advisory(
        tmp_path, facts, blocked, generated_at="2026-07-24T00:00:00Z"
    )
    import yaml

    parsed = yaml.safe_load(written.read_text(encoding="utf-8"))
    assert parsed["recommendation"]["blocked"] is True
    assert parsed["recommendation"]["missing_prerequisites"]
