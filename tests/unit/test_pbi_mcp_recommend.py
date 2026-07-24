"""One test per issue-#450 section-7 recommendation case, plus the advisory
record's write-once contract. Pure-function tests: facts in, record out."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.pbi_mcp import recommend as rec_mod
from seshat.pbi_mcp.detect import (
    ABSENT,
    APPROVAL_ABSENT,
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
        "semantic_model_ready": READINESS_PASS,
        "semantic_ready_tables": ("orders",),
        "publish_ready_approval": APPROVAL_ABSENT,
    }
    base.update(overrides)
    return DetectedFacts(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# section-7 cases 1..8, each a DISTINCT surface
# --------------------------------------------------------------------------- #


def test_case1_model_edit_ready_routes_to_local_modeling_mcp() -> None:
    result = recommend("model-edit", _facts())
    assert result.surface == "local-modeling-mcp"
    assert not result.blocked
    assert result.missing_prerequisites == ()


def test_case2_published_query_routes_to_remote_server() -> None:
    result = recommend("published-query", _facts())
    assert result.surface == "remote-powerbi-mcp"
    joined = " ".join(result.missing_prerequisites)
    assert "tenant setting" in joined
    assert "Build permission" in joined
    assert "Copilot license" in joined
    assert "stop" in result.next_human_step


def test_case3_formatting_stays_on_the_pbir_adapter() -> None:
    result = recommend("report-formatting", _facts())
    assert result.surface == "pbir-authoring-adapter"
    assert not result.blocked


def test_case4_desktop_verification_routes_to_desktop_bridge() -> None:
    result = recommend("desktop-verification", _facts())
    assert result.surface == "desktop-bridge"
    assert "never in CI" in " ".join(result.missing_prerequisites)


def test_case5_db_connectivity_routes_to_gateway_and_service() -> None:
    result = recommend("db-connectivity", _facts())
    assert result.surface == "gateway-and-service"


def test_case6_readiness_not_passed_blocks_and_names_the_gate() -> None:
    result = recommend("model-edit", _facts(semantic_model_ready=READINESS_NOT_PASS))
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


def test_all_eight_surfaces_are_distinct() -> None:
    surfaces = {recommend(intent, _facts()).surface for intent in INTENTS}
    surfaces.add(
        recommend("model-edit", _facts(semantic_model_ready="missing")).surface
    )
    assert len(surfaces) == 8


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
    assert not result.blocked  # prerequisites, not a refusal


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
    assert "schema_version: 1" in text
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
