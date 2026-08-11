"""T022: turn context construction (FR-017, FR-018, FR-026).

The Turn Context Contract lists what every production request carries: selected
table, readiness stage and categorical statuses, evidence and concrete blockers, the
one next allowed action, current forbidden scope, the read-only/propose-changes mode,
and a reminder that technical permission cannot grant a business approval.

It also lists what the request must NEVER embed: a DSN, token, authorization header,
browser cookie, or raw credential-bearing environment value.

The tests below are split accordingly. The inclusion tests are ordinary. The
exclusion tests are the ones that matter, and they are written to fail if the
redaction step is removed -- an exclusion assertion passes for two indistinguishable
reasons (the redactor removed it, or it was never there), so each one drives a
secret through a field that genuinely reaches the rendered context.
"""

from __future__ import annotations

import pytest

from seshat.studio.projection import (
    ActionSummary,
    AgentHealth,
    BlockingReason,
    EvidenceRef,
    StageState,
    TableJourney,
    WorkspaceIdentity,
    WorkspaceSnapshot,
)
from seshat.studio.turn_context import (
    BUSINESS_APPROVAL_REMINDER,
    RedactionScope,
    build_turn_context,
    render_turn_context,
)

pytestmark = pytest.mark.unit


def _snapshot(*, table: TableJourney | None = None) -> WorkspaceSnapshot:
    return WorkspaceSnapshot(
        identity=WorkspaceIdentity(
            display_name="demo-workspace",
            root_fingerprint="abc123",
            branch="main",
            revision="deadbeef",
        ),
        generated_at="2026-08-11T12:00:00Z",
        agent_health=AgentHealth(
            state="healthy",
            summary="Codex is signed in and responding.",
            recovery_action="",
            provider="codex",
            version="0.147.0",
        ),
        tables=(table,) if table is not None else (),
    )


def _table(**overrides) -> TableJourney:
    defaults = dict(
        table_id="sales_c086",
        display_name="Retail sales",
        current_stage="mapping_ready",
        stages=(
            StageState(
                stage="source_ready",
                status="pass",
                evidence=(
                    EvidenceRef(
                        label="source profile",
                        source_ref="profiles/sales.yaml",
                        kind="profile",
                        live_state="committed",
                    ),
                ),
            ),
            StageState(
                stage="mapping_ready",
                status="blocked",
                blocking_reasons=(
                    BlockingReason(
                        code="MAP001",
                        message="the grain declaration is missing",
                        source_ref="mappings/source-map.yaml",
                    ),
                ),
                required_authority=("named_human",),
            ),
        ),
        next_action=ActionSummary(
            id="declare_grain",
            label="declare the grain",
            explanation="mapping cannot clear without it",
            requires_agent=False,
            requires_named_human=True,
        ),
        forbidden_scope=("write silver.*", "grant approval"),
    )
    defaults.update(overrides)
    return TableJourney(**defaults)


# -- what the context MUST carry --------------------------------------------------- #


def test_context_names_the_selected_table_and_its_stage() -> None:
    context = build_turn_context(
        _snapshot(table=_table()), table_id="sales_c086", requested_mode="read_only"
    )
    assert context.table_id == "sales_c086"
    assert context.current_stage == "mapping_ready"


def test_context_carries_categorical_statuses_evidence_and_blockers() -> None:
    context = build_turn_context(
        _snapshot(table=_table()), table_id="sales_c086", requested_mode="read_only"
    )
    rendered = render_turn_context(context)
    assert "source_ready" in rendered and "pass" in rendered
    assert "the grain declaration is missing" in rendered
    assert "profiles/sales.yaml" in rendered


def test_context_carries_one_next_action_and_the_forbidden_scope() -> None:
    context = build_turn_context(
        _snapshot(table=_table()), table_id="sales_c086", requested_mode="read_only"
    )
    assert context.next_action is not None
    assert "declare the grain" in context.next_action
    assert "write silver.*" in context.forbidden_scope
    assert "grant approval" in context.forbidden_scope


@pytest.mark.parametrize("mode", ["read_only", "propose_changes"])
def test_context_states_the_requested_mode(mode: str) -> None:
    context = build_turn_context(
        _snapshot(table=_table()), table_id="sales_c086", requested_mode=mode
    )
    assert context.requested_mode == mode
    assert mode in render_turn_context(context)


def test_context_always_reminds_that_permission_is_not_business_approval() -> None:
    """A technical allow must never read as a governance ruling."""
    for mode in ("read_only", "propose_changes"):
        context = build_turn_context(
            _snapshot(table=_table()), table_id="sales_c086", requested_mode=mode
        )
        assert BUSINESS_APPROVAL_REMINDER in render_turn_context(context)


def test_a_workspace_with_no_selected_table_still_builds_a_context() -> None:
    context = build_turn_context(_snapshot(), table_id=None, requested_mode="read_only")
    assert context.table_id is None
    assert BUSINESS_APPROVAL_REMINDER in render_turn_context(context)


def test_an_unknown_table_id_is_refused_rather_than_silently_ignored() -> None:
    """Silently building a context for a table that is not there would ask the agent
    to reason about a workspace it cannot see."""
    with pytest.raises(KeyError):
        build_turn_context(
            _snapshot(table=_table()),
            table_id="not_a_table",
            requested_mode="read_only",
        )


# -- what the context must NEVER carry --------------------------------------------- #


def test_a_dsn_in_a_blocker_never_reaches_the_rendered_context() -> None:
    """Driven through `message`, which the renderer genuinely echoes."""
    leaky = _table(
        stages=(
            StageState(
                stage="mapping_ready",
                status="blocked",
                blocking_reasons=(
                    BlockingReason(
                        code="DB001",
                        message=(
                            "connect failed: "
                            "postgresql://svc:hunter2pass@db.example.invalid:5432/app"
                        ),
                    ),
                ),
            ),
        )
    )
    rendered = render_turn_context(
        build_turn_context(
            _snapshot(table=leaky), table_id="sales_c086", requested_mode="read_only"
        )
    )
    assert "hunter2pass" not in rendered
    assert "db.example.invalid" not in rendered
    assert "connect failed:" in rendered, "redaction destroyed the blocker"


def test_an_absolute_path_in_evidence_is_relativized_not_leaked(tmp_path) -> None:
    inside = tmp_path / "mappings" / "source-map.yaml"
    leaky = _table(
        stages=(
            StageState(
                stage="source_ready",
                status="pass",
                evidence=(
                    EvidenceRef(
                        label="source map",
                        source_ref=str(inside),
                        kind="map",
                        live_state="committed",
                    ),
                ),
            ),
        )
    )
    rendered = render_turn_context(
        build_turn_context(
            _snapshot(table=leaky),
            table_id="sales_c086",
            requested_mode="read_only",
            redaction=RedactionScope(workspace_root=tmp_path),
        )
    )
    assert str(tmp_path) not in rendered
    assert "mappings/source-map.yaml" in rendered


def test_a_bearer_token_in_a_recovery_action_never_reaches_the_context() -> None:
    leaky = _table(
        stages=(
            StageState(
                stage="mapping_ready",
                status="blocked",
                blocking_reasons=(
                    BlockingReason(
                        code="AUTH1",
                        message=(
                            "the upstream refused; retry with Authorization: Bearer "
                            "eyJhbGciOiJIUzI1NiJ9.PAYLOAD.SIGNATURE"
                        ),
                    ),
                ),
            ),
        )
    )
    rendered = render_turn_context(
        build_turn_context(
            _snapshot(table=leaky), table_id="sales_c086", requested_mode="read_only"
        )
    )
    assert "eyJhbGciOiJIUzI1NiJ9.PAYLOAD.SIGNATURE" not in rendered
    assert "the upstream refused" in rendered, "redaction destroyed the blocker"


def test_the_session_token_is_never_embedded_in_a_context() -> None:
    """The browser's own credential must not travel to the provider."""
    token = "a" * 48
    context = build_turn_context(
        _snapshot(table=_table()),
        table_id="sales_c086",
        requested_mode="read_only",
        redaction=RedactionScope(secrets=(token,)),
    )
    assert token not in render_turn_context(context)
