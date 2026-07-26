"""Safety of the commands `seshat next`'s guidance presents as runnable.

A separate subject from *whether* the adapter checkpoint is surfaced (that is
``test_issue_regression_489_adapter_checkpoint.py``): these tests ask whether a
string this surface tells a reader to run is safe to run at all. Three defect
classes found in PR #506 review, each now pinned:

  * a command must never carry an interpolated filesystem path -- there is no
    quoting that is correct across POSIX sh, ``cmd.exe`` and PowerShell, and this
    repo's release lane is Windows;
  * a quoted pip extra must use DOUBLE quotes -- ``cmd.exe`` passes apostrophes
    through literally, so ``pip install 'seshat-bi[dbt]'`` reaches pip as an
    invalid requirement;
  * **nothing runnable may be rendered below a STOP** (P1) -- an agent reads the
    document top to bottom, so an install/init/doctor step under a blocked gate
    reads as "here is what to do next".

Every assertion here is on the emitted STRING. One test executes a command, as a
token list via ``subprocess.run`` (never ``shell=True``), because the fix is only
real if the emitted string actually works.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

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


_HOSTILE_PATH_NAMES = [
    "a$(echo hi)b",
    "a`id`b",
    "a${HOME}b",
    "a;rm -rf x",
    "a&&whoami",
    "a|b",
    "a b",
    "a'b",
    'a"b',
    "a&b",
    "a%PATH%b",
    "plain",
]


@pytest.mark.parametrize("name", _HOSTILE_PATH_NAMES)
def test_emitted_command_never_interpolates_a_path(tmp_path: Path, name: str) -> None:
    """PR #506 review P2: no interpolated path means nothing to mis-quote.

    An earlier fix pre-quoted the path with POSIX `shlex.quote`, which is wrong on
    `cmd.exe` (single quotes are literal there) and not portable PowerShell either
    -- so a "copyable" command carrying a path is broken on some supported shell no
    matter how it is quoted. The command is now always `--repo .`, which is correct
    on every shell. This asserts the STRING; nothing is executed through a shell.

    Driven through ``_orchestration_checkpoint`` directly rather than the filesystem:
    several of these names (``a|b``, ``a"b``) cannot be created as Windows
    directories at all, yet the emitted command must be correct for any root the
    caller hands us.
    """
    from seshat.agent_next import _orchestration_checkpoint
    from seshat.orchestration_assess import build_orchestration_assessment

    root = tmp_path / name
    checkpoint = _orchestration_checkpoint(
        "source_ready", build_orchestration_assessment(tmp_path), root.as_posix()
    )
    assert checkpoint is not None
    command = checkpoint["full_assessment_command"]

    assert command == "seshat orchestration-assess --repo ."
    # The hostile name appears NOWHERE in the command -- not quoted, not escaped.
    assert name not in command
    for metacharacter in ("$(", "`", ";", "|", "&", "'", '"', "%"):
        assert metacharacter not in command, f"{metacharacter!r} reached the command"


def test_workspace_is_named_as_data_not_interpolated_into_a_command(
    tmp_path: Path,
) -> None:
    """Dropping the path must not lose the information the path carried.

    The original finding was that `--repo .` silently assessed the WRONG workspace.
    Naming the workspace is still required -- it is just reported as data, in its
    own field, where no shell ever parses it.
    """
    root = tmp_path / "my project"
    _write_status(root, "orders", "source_ready")

    checkpoint = _document(root)["orchestration_checkpoint"]

    assert checkpoint["repo_path"] == root.as_posix()
    assert "repository root" in checkpoint["command_scope"]
    assert "--repo ." in checkpoint["command_scope"]
    # ...and it is NOT in the command itself.
    assert root.as_posix() not in checkpoint["full_assessment_command"]


# Every string that would MUTATE the environment or the repository if pasted. None
# of these may appear anywhere in a document that says STOP (PR #506 review, P1).
_EXECUTABLE_MARKERS = (
    "pip install",  # substring of `pipx install`, so it catches both forms
    "pipx install",
    "dbt init",
    "dbt doctor",
    "dagster init",
    "dagster doctor",
    "orchestration-assess",
)


def _blocked_workspace(root: Path, focused_status: str) -> Path:
    """Two tables (so the assessor says `consider`) with the focused one at
    ``focused_status`` on ``source_ready`` -- the Dagster-scoped stage."""
    for table, status in (("t0", focused_status), ("t1", "not_started")):
        directory = root / "mappings" / table
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "readiness-status.yaml").write_text(
            textwrap.dedent(f"""\
                table: "{table}"
                current_stage: "source_ready"
                stages:
                  source_ready:
                    status: "{status}"
                    evidence: []
                    blocking_reasons: ["source profile missing"]
                approvals: []
                """),
            encoding="utf-8",
        )
    return root


def test_no_executable_adapter_step_is_rendered_below_a_stop(tmp_path: Path) -> None:
    """P1: a runnable command under a STOP reads as "here is what to do next".

    An agent reads the document top to bottom. With the focused stage `blocked`,
    `next_allowed_action` and `stop_point` both say STOP -- so an adapter block
    carrying install/init/doctor steps invites mutating the environment instead of
    halting. The verdict may stay (it is informational); the steps may not.
    """
    from seshat.cli.commands.next import _render_agent_text

    document = _document(_blocked_workspace(tmp_path, "blocked"))
    text = _render_agent_text(document)

    assert document["outcome"] == "stop_blocked"
    assert "STOP" in document["next_allowed_action"]

    leaked = [marker for marker in _EXECUTABLE_MARKERS if marker in text]
    assert not leaked, f"executable step(s) rendered below a STOP: {leaked}"

    # The verdict survives -- suppression must not silently drop the signal.
    checkpoint = document["orchestration_checkpoint"]
    assert checkpoint is not None
    assert checkpoint["steps_deferred_by_block"] is True
    assert checkpoint["adapters"][0]["recommendation"] == "consider"
    assert checkpoint["adapters"][0]["opt_in_deferred"] is True
    assert "do not install" in checkpoint["adapters"][0]["opt_in_command"]


@pytest.mark.parametrize(
    "stage", ["semantic_model_ready", "dashboard_ready", "publish_ready"]
)
def test_no_post_gold_stop_renders_an_executable_step(
    tmp_path: Path, stage: str
) -> None:
    """Every post-Gold stage says STOP (unverified live validation) and must defer.

    Covers all three regardless of WHICH signal fires -- `semantic_model_ready`
    reaches the stop only through the action string, while the later two also carry
    `approval_required`. The rule is about the STOP, not about the route to it.
    """
    from seshat.cli.commands.next_guidance_render import guidance_lines

    _write_status(tmp_path, "orders", stage)
    document = _document(tmp_path)

    assert document["next_allowed_action"].startswith("STOP")
    guidance = "\n".join(guidance_lines(document))
    leaked = [marker for marker in _EXECUTABLE_MARKERS if marker in guidance]
    assert not leaked, f"{stage}: executable step(s) below a STOP: {leaked}"
    assert document["orchestration_checkpoint"]["steps_deferred_by_block"] is True


@pytest.mark.parametrize("stage", ["semantic_model_ready"])
def test_a_live_validation_stop_also_defers_the_steps(
    tmp_path: Path, stage: str
) -> None:
    """The THIRD stop route, which the outcome/status signals do not see.

    ``_live_validation_next_override`` emits "STOP -- run `retail validate` ...
    [PENDING LIVE PROFILE]" while ``outcome`` stays ``next_action``/``terminal_pass``
    and ``readiness_state`` stays ``not_started``/``pass`` -- so keying only off
    those two missed it, while ``_control_stage`` pulled control back to
    ``gold_ready`` and put dbt in scope. The result was
    ``pip install "seshat-bi[dbt]"`` / ``dbt init`` / ``dbt doctor`` rendered
    directly beneath a STOP. The condition is now derived from the FINAL
    ``next_allowed_action`` string, which is the literal statement of the rule, so
    every branch that emits a STOP is covered -- including future ones.

    Asserted on the GUIDANCE block specifically: the surrounding STOP sentence
    legitimately contains "install the db extra" as the way to SATISFY the stop, so
    a whole-document scan would false-positive on the fix's own success.
    """
    from seshat.cli.commands.next_guidance_render import guidance_lines

    _write_status(tmp_path, "orders", stage)
    document = _document(tmp_path)

    assert document["next_allowed_action"].startswith("STOP")
    # Neither of the first two signals fires here -- that is the whole point.
    assert document["outcome"] not in {"stop_blocked", "approval_required"}
    assert document["readiness_state"] != "blocked"

    guidance = "\n".join(guidance_lines(document))
    leaked = [marker for marker in _EXECUTABLE_MARKERS if marker in guidance]
    assert not leaked, (
        f"{stage}: executable step(s) below a live-validation STOP: {leaked}"
    )

    checkpoint = document["orchestration_checkpoint"]
    assert checkpoint is not None
    assert checkpoint["steps_deferred_by_block"] is True


@pytest.mark.parametrize(
    ("mapping_status", "expected_outcome"),
    [("blocked", "stop_blocked"), ("pass", "approval_required")],
)
def test_map_authoring_guidance_is_withheld_below_a_stop(
    tmp_path: Path, mapping_status: str, expected_outcome: str
) -> None:
    """P1: the #488 signpost is repository-mutating guidance, so it inherits the STOP.

    Its text is an imperative -- "Author source-map.yaml ...", "`seshat
    scaffold-source <table> --repo .`", "add whatever is missing, in place".
    Rendered below a STOP (Mapping blocked, or awaiting a named-human approval) that
    invites writing to the repo instead of resolving the blocker. The signpost is
    only actionable while the map is genuinely being authored.
    """
    directory = tmp_path / "mappings" / "orders"
    directory.mkdir(parents=True)
    (directory / "readiness-status.yaml").write_text(
        textwrap.dedent(f"""\
            table: "orders"
            current_stage: "mapping_ready"
            stages:
              source_ready: {{status: "pass", evidence: ["profile"]}}
              mapping_ready:
                status: "{mapping_status}"
                evidence: []
                blocking_reasons: ["grain unresolved"]
            approvals: []
            """),
        encoding="utf-8",
    )

    document = _document(tmp_path)

    assert document["outcome"] == expected_outcome
    assert document["next_allowed_action"].startswith("STOP")
    assert document["source_map_shape_signpost"] is None
    # No authoring imperative reaches the reader through any guidance channel.
    guidance = "\n".join(
        str(document[key])
        for key in ("source_map_shape_signpost", "orchestration_checkpoint")
        if document.get(key)
    )
    for imperative in ("Author source-map.yaml", "scaffold-source"):
        assert imperative not in guidance, f"{imperative!r} rendered below a STOP"


def test_the_signpost_still_renders_while_the_map_is_being_authored(
    tmp_path: Path,
) -> None:
    """The other half: suppression must be caused by the STOP, not always-on."""
    _write_status(tmp_path, "orders", "mapping_ready")

    document = _document(tmp_path)

    assert not document["next_allowed_action"].startswith("STOP")
    assert document["source_map_shape_signpost"] is not None
    assert "scaffold-source" in document["source_map_shape_signpost"]


def test_stop_detection_reads_the_final_action_string() -> None:
    """Pin the third signal directly, and that a non-STOP override keeps its steps.

    ``_contract_next_override`` says "Run `kpi-contract-builder` ..." -- guidance, not
    a stop -- so it must NOT suppress the steps. Getting that wrong would silently
    hide the checkpoint at the semantic-contract stage.
    """
    from seshat.agent_next import _is_stopped

    running = {"outcome": "next_action"}
    assert _is_stopped(running, "not_started", "STOP -- run `retail validate` ...")
    assert _is_stopped({"outcome": "terminal_pass"}, "pass", "STOP -- live evidence")
    assert not _is_stopped(running, "not_started", "Run `kpi-contract-builder` ...")
    assert not _is_stopped(running, "not_started", "")


def test_an_unblocked_stage_still_renders_the_executable_steps(tmp_path: Path) -> None:
    """The other half of the guard: suppression must be caused by the BLOCK.

    Same workspace shape, focused stage not blocked -- the steps must come back, or
    the test above would pass just as well against a permanently broken renderer.
    """
    from seshat.cli.commands.next import _render_agent_text

    document = _document(_blocked_workspace(tmp_path, "not_started"))
    text = _render_agent_text(document)

    assert document["outcome"] == "next_action"
    assert document["orchestration_checkpoint"]["steps_deferred_by_block"] is False
    for marker in ("dagster init", "dagster doctor", "orchestration-assess"):
        assert marker in text, marker


@pytest.mark.parametrize(
    ("stage", "status"),
    [("source_ready", "blocked"), ("silver_ready", "blocked")],
)
def test_blocked_checkpoint_carries_no_command_field_at_all(
    tmp_path: Path, stage: str, status: str
) -> None:
    """JSON consumers must not find a command to run either.

    Suppressing only the TEXT would leave `--format json` handing an agent the same
    runnable command, so the fields are absent from the document, not just unrendered.
    """
    from seshat.agent_next import _orchestration_checkpoint
    from seshat.orchestration_assess import build_orchestration_assessment

    _blocked_workspace(tmp_path, status)
    checkpoint = _orchestration_checkpoint(
        stage,
        build_orchestration_assessment(tmp_path),
        tmp_path.as_posix(),
        blocked=True,
    )

    assert checkpoint is not None
    assert "full_assessment_command" not in checkpoint
    assert "command_scope" not in checkpoint


def test_approval_required_and_input_defect_also_defer_the_steps(
    tmp_path: Path,
) -> None:
    """A STOP is a STOP: the outcome need not be `stop_blocked` specifically.

    `approval_required` halts on a named-human gate and `input_defect` halts on a
    malformed readiness file; neither may render a runnable adapter step either.
    """
    from seshat.agent_next import _STOP_OUTCOMES, _is_stopped

    assert _STOP_OUTCOMES == {"stop_blocked", "approval_required", "input_defect"}
    for outcome in _STOP_OUTCOMES:
        assert _is_stopped({"outcome": outcome}, "not_started") is True
    # A recorded `blocked` status is a closed gate even when the outcome is phrased
    # as a next action.
    assert _is_stopped({"outcome": "next_action"}, "blocked") is True
    assert _is_stopped({"outcome": "next_action"}, "not_started") is False


def test_emitted_commands_target_the_documented_pipx_install_lane() -> None:
    """P2: the validated lane is pipx, so `python -m` and `pip install` are wrong.

    `docs/install/user-install.md` and `docs/install/agent-install.md` both install
    via `pipx install seshat-bi` -- an ISOLATED environment. There the ambient
    `python` cannot import `seshat` at all, and a bare `pip install` targets the
    ambient interpreter (or is refused as externally-managed, PEP 668). So:

      * invocations must use the installed console script `seshat`, which is what
        pipx puts on PATH (declared in pyproject `[project.scripts]`);
      * an extra must be installed with `pipx install --force "seshat-bi[...]"` --
        agent-install.md documents the bare `pipx install "seshat-bi[dbt]"` for a
        FIRST install, but this guidance is only ever read by someone who ALREADY
        has `seshat` installed, and on an existing venv plain `pipx install`
        refuses to modify it and changes nothing (#510 review, P2).
    """
    from seshat.cli.commands.next_guidance_render import _opt_in_step_lines
    from seshat.orchestration_assess import _DAGSTER_OPT_IN, _DBT_OPT_IN

    steps = [
        line
        for opt_in in (_DBT_OPT_IN, _DAGSTER_OPT_IN)
        for line in _opt_in_step_lines({"opt_in_command": opt_in})
    ]

    assert any('pipx install --force "seshat-bi[dbt]"' in line for line in steps)
    for line in steps:
        assert "python -m seshat" not in line, line
        # `pipx install` is fine; a bare `pip install` is not.
        assert "pip install" not in line.replace("pipx install", ""), line


def test_the_pipx_form_matches_the_repos_own_install_doc() -> None:
    """Match the documented lane verbatim rather than inventing a variant.

    If agent-install.md ever changes its command, this fails and the emitted step is
    reconsidered deliberately instead of drifting.
    """
    from seshat.cli.commands.next_guidance_render import _portable_quoting

    doc = (_REPO_ROOT / "docs" / "install" / "agent-install.md").read_text(
        encoding="utf-8"
    )
    emitted = _portable_quoting("pip install 'seshat-bi[dbt]'")

    # The DISTRIBUTION + EXTRA + quoting must match the documented command; the
    # emitted step adds `--force` because, unlike the doc's first-install example,
    # this guidance is read by someone who already has seshat installed (#510).
    assert emitted == 'pipx install --force "seshat-bi[dbt]"'
    assert 'pipx install "seshat-bi[dbt]"' in doc
    assert emitted.replace("--force ", "") in doc, (
        "emitted install step is not the documented command"
    )


def test_full_assessment_command_uses_the_installed_console_script(
    tmp_path: Path,
) -> None:
    """P2: `python -m seshat.cli ...` cannot work in a pipx install."""
    _write_status(tmp_path, "orders", "source_ready")

    command = _document(tmp_path)["orchestration_checkpoint"]["full_assessment_command"]

    assert command == "seshat orchestration-assess --repo ."
    assert "python -m" not in command


def test_pip_extra_is_double_quoted_for_cmd_exe(tmp_path: Path) -> None:
    """P2: `pip install 'seshat-bi[dbt]'` is broken on the Windows release lane.

    `cmd.exe` passes apostrophes through literally, so pip receives
    `'seshat-bi[dbt]'` and rejects it as an invalid requirement. POSIX sh needs the
    brackets quoted (glob metacharacters), so the portable single form is DOUBLE
    quotes -- valid in cmd.exe, PowerShell and POSIX sh alike. Pinned so it cannot
    regress to single quotes.
    """
    from seshat.cli.commands.next_guidance_render import _opt_in_step_lines
    from seshat.orchestration_assess import _DBT_OPT_IN

    steps = _opt_in_step_lines({"opt_in_command": _DBT_OPT_IN})

    assert steps[0].endswith('pipx install --force "seshat-bi[dbt]"')
    for line in steps:
        assert "'" not in line, f"single quote survived into {line!r}"


def test_portable_quoting_is_surgical_and_idempotent() -> None:
    """It may rewrite a seshat-bi install step and nothing else, never double-apply."""
    from seshat.cli.commands.next_guidance_render import _portable_quoting

    # Both quote styles of the wrong-environment form are rewritten...
    assert (
        _portable_quoting("pip install 'seshat-bi[dbt]'")
        == 'pipx install --force "seshat-bi[dbt]"'
    )
    assert (
        _portable_quoting('pip install "seshat-bi[db]"')
        == 'pipx install --force "seshat-bi[db]"'
    )
    # ...unrelated quoting is left alone...
    assert _portable_quoting("echo 'keep me'") == "echo 'keep me'"
    # ...a step with no install head passes through...
    assert _portable_quoting("seshat dbt init") == "seshat dbt init"
    # ...and an already-correct step is unchanged (idempotent).
    assert (
        _portable_quoting('pipx install --force "seshat-bi[dbt]"')
        == 'pipx install --force "seshat-bi[dbt]"'
    )


def test_no_emitted_opt_in_step_uses_posix_only_quoting() -> None:
    """Sweep every adapter the engine defines, not just dbt.

    Catches the same defect reappearing in a future extra (dagster, dev, ...) rather
    than only pinning the one instance found in review.
    """
    from seshat.cli.commands.next_guidance_render import _opt_in_step_lines
    from seshat.orchestration_assess import _DAGSTER_OPT_IN, _DBT_OPT_IN

    for opt_in in (_DBT_OPT_IN, _DAGSTER_OPT_IN):
        for line in _opt_in_step_lines({"opt_in_command": opt_in}):
            assert "'" not in line, f"POSIX-only quoting in {line!r}"


def test_opt_in_sequence_renders_as_individually_runnable_steps() -> None:
    """PR #506 review P2: `opt_in_command` is a prose composite, not one command.

    The engine's value is e.g. `pip install 'seshat-bi[dbt]'  (then: seshat dbt
    init; seshat dbt doctor)`. Labelling that whole string "opt in with" presented
    it as pasteable, and pasting it fails at the parenthesized `(then: ...)`. Each
    step must be its own line, and no rendered step may still carry the prose
    joiner.
    """
    from seshat.cli.commands.next_guidance_render import _opt_in_step_lines
    from seshat.orchestration_assess import _DAGSTER_OPT_IN, _DBT_OPT_IN

    dbt_steps = _opt_in_step_lines({"opt_in_command": _DBT_OPT_IN})
    assert len(dbt_steps) == 3
    # Double-quoted: portable across cmd.exe / PowerShell / POSIX sh -- see
    # test_pip_extra_is_double_quoted_for_cmd_exe.
    assert dbt_steps[0].endswith('pipx install --force "seshat-bi[dbt]"')
    assert dbt_steps[1].endswith("seshat dbt init")
    assert dbt_steps[2].endswith("seshat dbt doctor")

    assert len(_opt_in_step_lines({"opt_in_command": _DAGSTER_OPT_IN})) == 2

    for line in dbt_steps + _opt_in_step_lines({"opt_in_command": _DAGSTER_OPT_IN}):
        for prose in ("(then:", ";", ")"):
            assert prose not in line, f"{prose!r} survived into {line!r}"


def test_opt_in_step_split_degrades_to_one_step_for_a_plain_command() -> None:
    """If the engine's wording ever drops `(then: ...)`, degrade -- never mangle."""
    from seshat.cli.commands.next_guidance_render import _opt_in_step_lines

    assert _opt_in_step_lines({"opt_in_command": "seshat dbt init"}) == [
        "      opt-in step 1: seshat dbt init"
    ]


def test_rendered_checkpoint_shows_every_opt_in_step(tmp_path: Path) -> None:
    """End-to-end through the text surface an agent actually reads."""
    from seshat.cli.commands.next_guidance_render import guidance_lines

    _write_status(tmp_path, "t0", "silver_ready")
    _write_status(tmp_path, "t1", "silver_ready")
    text = "\n".join(guidance_lines(_document(tmp_path)))

    assert "opt-in step 1:" in text
    assert "opt-in step 2:" in text
    assert "opt in with:" not in text, "the misleading single-command label is back"


def test_source_map_hint_embeds_no_path_either() -> None:
    """The #488 hint emits a command too, and had the same defect.

    Its `scaffold-source` command defaulted to `--repo .` while the reader might be
    elsewhere, so the blank landed in an unrelated directory. It now passes
    `--repo .` explicitly and the hint says to run it from the repository root.

    (The hint once emitted a SECOND command that scaffolded a throwaway reference
    folder and then told the reader to delete it. That whole route is gone -- see
    `test_emitted_guidance_never_instructs_a_delete` -- so only one command remains.)
    """
    from seshat.validate_targets import CANONICAL_SOURCE_MAP_SHAPE_HINT

    assert "FROM THE REPOSITORY ROOT" in CANONICAL_SOURCE_MAP_SHAPE_HINT
    assert "scaffold-source <table> --repo ." in CANONICAL_SOURCE_MAP_SHAPE_HINT
    # No absolute path is baked into the hint (it is a module-level constant, so it
    # could not carry a correct one anyway).
    assert ":/" not in CANONICAL_SOURCE_MAP_SHAPE_HINT


def test_emitted_assessment_command_works_when_run_from_the_repo_root(
    tmp_path: Path,
) -> None:
    """The command is only useful if it really assesses the workspace it belongs to.

    Run as a token LIST (no shell) from the repo root the guidance names, and assert
    it sees this workspace's two tables.
    """
    import os
    import subprocess

    root = tmp_path / "workspace"
    _write_status(root, "t0", "source_ready")
    _write_status(root, "t1", "source_ready")

    checkpoint = _document(root)["orchestration_checkpoint"]
    result = subprocess.run(
        checkpoint["full_assessment_command"].split(),
        cwd=checkpoint["repo_path"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(_REPO_ROOT / "src")},
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "tables onboarded: 2" in result.stdout, result.stdout
