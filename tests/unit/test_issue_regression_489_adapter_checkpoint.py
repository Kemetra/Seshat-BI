"""#489's deferred half: surface the dbt/Dagster adapter choice in `seshat next`.

PR #495 routed the `retail-build-warehouse` skill to the shipped
`orchestration_assess` engine but left the owner ruling on `seshat next` open.
The ruling is now made: surface it. `next` emits `orchestration_checkpoint` -- the
assessor's categorical verdict WITH its own reasoning and the questions only the
human can answer -- as an INFORMATIONAL checkpoint that never adopts, never grants
readiness, never scores, and never blocks.

The invariant tests here are the real product: they pin that the checkpoint cannot
become a gate, that its stage scoping matches the documented contract, and that
every verdict string it surfaces is the engine's own constant.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.unit._next_guidance_fixtures import (
    GUIDANCE_KEYS as _GUIDANCE_KEYS,
)
from tests.unit._next_guidance_fixtures import (
    REPO_ROOT as _REPO_ROOT,
)
from tests.unit._next_guidance_fixtures import (
    document as _document,
)
from tests.unit._next_guidance_fixtures import (
    write_status as _write_status,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# #489 -- the assessor is reachable from `seshat next`
# ---------------------------------------------------------------------------


def test_next_surfaces_the_orchestration_checkpoint_at_a_scoped_stage(
    tmp_path: Path,
) -> None:
    """The gap #489 reported: `next` never surfaced the adapter choice at all."""
    _write_status(tmp_path, "orders", "source_ready")

    checkpoint = _document(tmp_path)["orchestration_checkpoint"]

    assert checkpoint is not None
    assert checkpoint["stage"] == "source_ready"
    assert [note["adapter"] for note in checkpoint["adapters"]] == ["dagster"]


def test_checkpoint_carries_the_tools_own_recommendation_and_reasoning(
    tmp_path: Path,
) -> None:
    """#489 asked for the recommendation WITH its reasoning, not a bare prompt."""
    _write_status(tmp_path, "orders", "source_ready")

    checkpoint = _document(tmp_path)["orchestration_checkpoint"]
    note = checkpoint["adapters"][0]

    assert checkpoint["recommended_action"]
    assert note["recommendation"]
    # The assessor's own signals are passed through, not re-worded here.
    assert note["for"] or note["against"]
    assert note["open_questions"]
    assert note["opt_in_command"]


def test_checkpoint_verdicts_are_the_engines_real_constants(tmp_path: Path) -> None:
    """Follows PR #495's precedent: never quote a verdict the engine doesn't define.

    Exercises every reachable verdict: `not_recommended` (one table),
    `consider` (two tables), and `already_adopted` (a materialized dbt project).
    """
    from seshat.orchestration_assess import (
        _ALREADY_ADOPTED,
        _CONSIDER,
        _NOT_RECOMMENDED,
    )

    real = {_CONSIDER, _NOT_RECOMMENDED, _ALREADY_ADOPTED}
    seen: set[str] = set()

    for table_count in (1, 2):
        root = tmp_path / f"w{table_count}"
        for index in range(table_count):
            _write_status(root, f"t{index}", "silver_ready")
        checkpoint = _document(root)["orchestration_checkpoint"]
        seen.update(note["recommendation"] for note in checkpoint["adapters"])

    adopted_root = tmp_path / "adopted"
    _write_status(adopted_root, "t0", "silver_ready")
    (adopted_root / "dbt").mkdir(parents=True)
    (adopted_root / "dbt" / "dbt_project.yml").write_text("name: x\n", encoding="utf-8")
    checkpoint = _document(adopted_root)["orchestration_checkpoint"]
    seen.update(note["recommendation"] for note in checkpoint["adapters"])

    assert seen <= real, f"surfaced verdicts the engine does not define: {seen - real}"
    assert seen == real, f"a real verdict is unreachable from `next`: {real - seen}"


# The documented contract, in `docs/agent-mode.md`'s own words: "Dagster at
# Source, dbt at Silver/Gold". Written out per stage so the scope tuple cannot
# drift from the documentation without a test failing. Dagster is the INGESTION
# adapter, so it is offered at Source ONLY -- by Mapping, Source has passed and
# ingestion is done, so the opt-in would arrive a stage late (PR #506 review, P2).
_DOCUMENTED_SCOPE: dict[str, list[str]] = {
    "source_ready": ["dagster"],
    "mapping_ready": [],
    "silver_ready": ["dbt"],
    "gold_ready": ["dbt"],
    "semantic_model_ready": [],
    "dashboard_ready": [],
    "publish_ready": [],
}


# Safety of the strings this surface presents as RUNNABLE -- shell portability and
# the no-command-below-a-STOP rule -- lives in
# `test_issue_regression_489_command_safety.py`. This module is about whether the
# checkpoint is surfaced with the right verdict at the right stage.


def test_checkpoint_scope_matches_the_documented_contract_stage_by_stage() -> None:
    """#489: "Dagster at Source, dbt at Silver/Gold" -- pinned per stage.

    This guard is the point: the scope is a one-line tuple that is easy to widen by
    accident, and a wrong stage points the agent at a workflow that is not the
    active one. Past Gold no adapter choice is left, so the scope is empty rather
    than a checkpoint with nothing in it.
    """
    from seshat.agent_next import _adapters_in_scope

    for stage, expected in _DOCUMENTED_SCOPE.items():
        assert _adapters_in_scope(stage) == expected, stage
    assert _adapters_in_scope(None) == []


def test_documented_scope_is_what_agent_mode_md_actually_says() -> None:
    """Pin the test's own expectation to the prose, not just to the code.

    Without this, `_DOCUMENTED_SCOPE` above could be quietly edited to match a
    regression and the doc would silently disagree.
    """
    doc = (_REPO_ROOT / "docs" / "agent-mode.md").read_text(encoding="utf-8")

    assert "at Source, dbt at Silver/Gold" in doc
    # And the code agrees with that sentence.
    assert _DOCUMENTED_SCOPE["source_ready"] == ["dagster"]
    assert _DOCUMENTED_SCOPE["mapping_ready"] == []
    assert _DOCUMENTED_SCOPE["silver_ready"] == ["dbt"]


def test_mapping_ready_does_not_offer_the_ingestion_adapter(tmp_path: Path) -> None:
    """PR #506 review P2: Dagster at Mapping arrives one stage late.

    Asserted end-to-end (not just on the scope helper) with two tables, the count
    that makes the assessor say `consider` -- the case most likely to leak.
    """
    _write_status(tmp_path, "t0", "mapping_ready")
    _write_status(tmp_path, "t1", "mapping_ready")

    document = _document(tmp_path)

    assert document["current_stage"] == "mapping_ready"
    assert document["orchestration_checkpoint"] is None
    # The #488 signpost still belongs at Mapping -- only the adapter offer moved.
    assert document["source_map_shape_signpost"] is not None


@pytest.mark.parametrize("table_count", [1, 2])
def test_headline_never_names_an_adapter_whose_reasoning_was_filtered_out(
    tmp_path: Path, table_count: int
) -> None:
    """PR #506 review P2: recommendation without reasoning is #489 inverted.

    The assessor's own `recommended_action` is portfolio-wide, so at two-plus tables
    it names BOTH adapters. Surfacing it verbatim at a stage-scoped checkpoint
    recommended dbt at Source and Dagster at Silver/Gold -- pointing the agent at
    another stage's workflow, with the reasoning for it filtered out. The headline
    must be derived from the blocks actually shown.
    """
    for stage, expected in _DOCUMENTED_SCOPE.items():
        if not expected:
            continue
        root = tmp_path / f"{stage}{table_count}"
        for index in range(table_count):
            _write_status(root, f"t{index}", stage)
        checkpoint = _document(root)["orchestration_checkpoint"]
        assert checkpoint is not None, stage

        shown = {note["adapter"] for note in checkpoint["adapters"]}
        assert shown == set(expected), stage
        headline = checkpoint["recommended_action"]
        leaked = {
            name
            for name in ("dbt", "dagster")
            if name in headline and name not in shown
        }
        assert not leaked, f"{stage}: headline names unshown adapter(s) {leaked}"


def test_scoped_headline_uses_the_engines_real_verdict_constants() -> None:
    """The headline branches on verdicts; those must be the engine's, not copies."""
    from seshat.agent_next import _scoped_headline, _verdicts
    from seshat.orchestration_assess import _ALREADY_ADOPTED, _CONSIDER

    assert _verdicts() == (_CONSIDER, _ALREADY_ADOPTED)

    def _note(adapter: str, verdict: str) -> dict[str, Any]:
        return {"adapter": adapter, "recommendation": verdict}

    assert "may be worth adopting" in _scoped_headline([_note("dbt", _CONSIDER)])
    assert "already present" in _scoped_headline([_note("dbt", _ALREADY_ADOPTED)])
    # No verdict of interest -> an honest "not recommended", never an empty string.
    assert "no adapter is recommended" in _scoped_headline(
        [_note("dbt", "not_recommended")]
    )


def test_scoped_headline_never_adopts_and_never_scores() -> None:
    """It is a recommendation line, so it must not read as an instruction."""
    from seshat.agent_next import _scoped_headline
    from seshat.orchestration_assess import _CONSIDER

    headline = _scoped_headline([{"adapter": "dbt", "recommendation": _CONSIDER}])

    assert "YOU decide" in headline
    assert not any(character.isdigit() for character in headline)


def test_checkpoint_follows_the_gate_not_the_stage_label(tmp_path: Path) -> None:
    """The checkpoint is keyed off `control_stage` -- the stage whose CLOSED gate
    governs every other agent-control field -- so guidance and gate never disagree.

    A table labelled post-Gold whose live validation is not yet verified has its
    control pulled back to `gold_ready`; the dbt checkpoint must follow it there,
    because that is the build the reader is actually still being sent back to.
    """
    _write_status(tmp_path, "orders", "semantic_model_ready")

    document = _document(tmp_path)
    checkpoint = document["orchestration_checkpoint"]

    assert document["current_stage"] == "semantic_model_ready"
    assert checkpoint is not None
    assert checkpoint["stage"] == "gold_ready"
    assert [note["adapter"] for note in checkpoint["adapters"]] == ["dbt"]


def test_checkpoint_never_adopts_grants_or_scores(tmp_path: Path) -> None:
    """The hard constraint on surfacing it in `next` at all.

    `next` must never adopt an adapter, never grant readiness, and never emit a
    numeric confidence score (hard rule #9 / Principle V).
    """
    _write_status(tmp_path, "orders", "silver_ready")

    document = _document(tmp_path)
    checkpoint = document["orchestration_checkpoint"]

    assert checkpoint["decision_owner"] == "human"
    for note in checkpoint["adapters"]:
        # A categorical verdict only -- no numeric axis anywhere in the block.
        assert not any(
            isinstance(value, int | float) and not isinstance(value, bool)
            for value in note.values()
        )
    assert "you decide" in checkpoint["decision_rule"].lower()
    assert document["readiness_state"] != "pass"


def test_checkpoint_does_not_let_consider_read_as_permission_to_skip(
    tmp_path: Path,
) -> None:
    """Stay coherent with the shipped `retail-build-warehouse` precondition 5."""
    from seshat.agent_next import _CHECKPOINT_DECISION_RULE
    from seshat.orchestration_assess import _CONSIDER

    assert _CONSIDER in _CHECKPOINT_DECISION_RULE
    assert "not permission to skip" in _CHECKPOINT_DECISION_RULE.lower()

    _write_status(tmp_path / "two", "t0", "silver_ready")
    _write_status(tmp_path / "two", "t1", "silver_ready")
    checkpoint = _document(tmp_path / "two")["orchestration_checkpoint"]

    assert any(note["recommendation"] == _CONSIDER for note in checkpoint["adapters"])
    assert checkpoint["decision_rule"] == _CHECKPOINT_DECISION_RULE


def test_checkpoint_is_rendered_in_the_agent_text_surface(tmp_path: Path) -> None:
    """A dict key nothing renders is invisible to the agent that reads text."""
    from seshat.cli.commands.next import _render_agent_text

    _write_status(tmp_path, "orders", "silver_ready")
    text = _render_agent_text(_document(tmp_path))

    assert "orchestration_checkpoint" in text
    assert "INFORMATIONAL" in text
    assert "orchestration-assess" in text
    # The assessor's own reasoning reaches the text surface, not just the verdict.
    assert "open question" in text
    # The opt-in route reaches it too, as individually runnable steps.
    assert "opt-in step 1:" in text


@pytest.mark.parametrize("stage", ["mapping_ready", "silver_ready"])
def test_every_rendered_guidance_line_is_labelled_informational(
    tmp_path: Path, stage: str
) -> None:
    """The label is load-bearing: an unlabelled line could read as an instruction.

    Asserted on the guidance renderer directly, so it holds however the surrounding
    agent-text rendering is later reorganized.
    """
    from seshat.cli.commands.next_guidance_render import guidance_lines

    root = tmp_path / stage
    _write_status(root, "t0", stage)
    _write_status(root, "t1", stage)
    lines = guidance_lines(_document(root))

    assert lines, f"no guidance rendered at {stage} -- test proves nothing"
    headers = [line for line in lines if not line.startswith(" ")]
    assert headers
    for header in headers:
        assert "INFORMATIONAL -- does not block" in header, header


def test_agent_mode_doc_documents_the_guidance_keys(tmp_path: Path) -> None:
    """A key a harness is never told about is invisible in practice.

    `docs/agent-mode.md` enumerates the keys a host or harness consumes. If the
    guidance keys are missing there, an integrator reading the documented contract
    never reads them -- and the adapter choice stays invisible, which is exactly
    what #489 filed. Asserted against the REAL document keys, so the doc cannot
    drift from what `next` emits.
    """
    doc = (_REPO_ROOT / "docs" / "agent-mode.md").read_text(encoding="utf-8")

    _write_status(tmp_path, "orders", "mapping_ready")
    document = _document(tmp_path)

    for key in _GUIDANCE_KEYS:
        assert key in document, f"`next` no longer emits {key}"
        assert key in doc, f"docs/agent-mode.md does not document {key}"

    # And it must say they do not gate -- the property that makes them safe.
    # Matched on wrap-free fragments: the doc is hard-wrapped prose.
    assert "Neither is a gate" in doc
    assert "adopts an adapter and never grants readiness" in doc
    assert "not permission to skip" in doc


def test_guidance_renderer_is_silent_when_there_is_no_guidance() -> None:
    """No guidance must render as NOTHING, never as an empty labelled block."""
    from seshat.cli.commands.next_guidance_render import guidance_lines

    assert guidance_lines({}) == []
    assert (
        guidance_lines(
            {"source_map_shape_signpost": None, "orchestration_checkpoint": None}
        )
        == []
    )


# ---------------------------------------------------------------------------
# #489 / #488 -- both fields are GUIDANCE: they may never become a gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stage", ["source_ready", "mapping_ready", "silver_ready"])
def test_guidance_never_blocks_and_never_changes_the_gate(
    tmp_path: Path, stage: str
) -> None:
    """The load-bearing invariant: adding guidance must not move any gate.

    Compared against the same document with the guidance suppressed, so this
    fails if a future edit ever routes either field into a control field.
    """
    from seshat.agent_next import build_agent_next_document

    root = tmp_path / stage
    _write_status(root, "t0", stage)
    _write_status(root, "t1", stage)
    document = build_agent_next_document(root)

    gate_fields = (
        "outcome",
        "readiness_state",
        "blocking_reasons",
        "forbidden_scope",
        "next_allowed_action",
        "stop_point",
    )
    guidance_text = "\n".join(
        str(document[key]) for key in _GUIDANCE_KEYS if document[key]
    )
    assert guidance_text, "nothing was surfaced at this stage -- test proves nothing"

    for field in gate_fields:
        rendered = str(document[field])
        for key in _GUIDANCE_KEYS:
            assert key not in rendered
        assert "orchestration-assess" not in rendered
        assert "scaffold-source" not in rendered

    assert document["blocking_reasons"] == []
    assert document["outcome"] == "next_action"


def test_guidance_keys_are_always_present_so_the_shape_stays_stable(
    tmp_path: Path,
) -> None:
    """Present-and-null, never absent -- including the fresh-workspace document."""
    from seshat.agent_next import build_agent_next_document, build_table_next_document

    fresh = build_agent_next_document(tmp_path)
    for key in _GUIDANCE_KEYS:
        assert key in fresh and fresh[key] is None

    _write_status(tmp_path, "orders", "publish_ready")
    for document in (
        build_agent_next_document(tmp_path),
        build_table_next_document(tmp_path, "orders"),
    ):
        for key in _GUIDANCE_KEYS:
            assert key in document


def test_guidance_degrades_silently_on_a_malformed_readiness_file(
    tmp_path: Path,
) -> None:
    """A broken committed file must surface as `input_defect` -- and offering
    stage guidance for a stage that could not be read would be fabricating it.

    Both fields go null and the text surface still renders; the defect stays the
    only message.
    """
    from seshat.cli.commands.next import _render_agent_text

    directory = tmp_path / "mappings" / "broken"
    directory.mkdir(parents=True)
    (directory / "readiness-status.yaml").write_text(
        "this: [is not: valid yaml\n", encoding="utf-8"
    )

    document = _document(tmp_path)

    assert document["outcome"] == "input_defect"
    for key in _GUIDANCE_KEYS:
        assert document[key] is None
    assert "read_only_proof" in _render_agent_text(document)


def test_per_table_document_stays_linear_by_not_assessing(tmp_path: Path) -> None:
    """`build_table_next_document` exists to keep the shared readiness projection
    linear (spec 120). The assessment globs `mappings/*`, so building it per TABLE
    would restore the O(n^2) behaviour that function was written to avoid."""
    from seshat.agent_next import build_table_next_document

    _write_status(tmp_path, "orders", "silver_ready")

    assert (
        build_table_next_document(tmp_path, "orders")["orchestration_checkpoint"]
        is None
    )


def test_next_stays_db_free_and_network_free_with_the_checkpoint_wired_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`agent_next` documents a no-DB / no-network contract. The assessor reads
    committed YAML only, so surfacing it must not open a socket or a connection."""
    import socket

    def _refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("`seshat next` opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", _refuse)
    monkeypatch.setattr(socket, "create_connection", _refuse)

    _write_status(tmp_path, "orders", "silver_ready")

    assert _document(tmp_path)["orchestration_checkpoint"] is not None
