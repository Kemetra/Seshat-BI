"""The opt-in Fabric/Power BI/dbt/Dagster installer.

Three properties carry the governance weight and each has a test here:

1. The default is a **network-free plan** -- nothing is cloned, written, or
   installed until a human approves.
2. The installer **never mutates the ambient Python interpreter**. A missing dbt
   is reported, not silently pip-installed over the operator's environment.
3. It is reachable **only through its own verb**, and that verb **validates
   `--repo`** rather than trusting it -- so no other command can trigger an
   install, and no non-workspace directory gets seeded with one.
"""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from seshat import gitutil, integrations_setup
from seshat.cli.commands.integrations import integrations_main
from seshat.integrations_setup import (
    DBT_SKILLS,
    FABRIC_SKILLS,
    INTEGRATIONS_DIR,
    MCP_CONFIG,
    IntegrationResult,
    SkillBundle,
    needs_operator_action,
    render_results,
    setup_integrations,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _workspace(tmp_path: Path) -> Path:
    """A directory the workspace resolver recognises as a Seshat workspace."""
    (tmp_path / ".seshat").mkdir()
    return tmp_path


def _install(root: Path, bundle: SkillBundle) -> None:
    """Pretend `bundle` was already cloned, with every required skill present."""
    for relative in bundle.required:
        path = root / bundle.directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("name: test\n", encoding="utf-8")


def _by_name(results: list[IntegrationResult]) -> dict[str, IntegrationResult]:
    return {item.name: item for item in results}


def _nothing_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integrations_setup.shutil, "which", lambda _: None)


def _everything_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integrations_setup.shutil, "which", lambda name: f"/bin/{name}")


def _no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*args: object, **kwargs: object) -> None:
        pytest.fail(f"the installer ran a subprocess: {args!r}")

    monkeypatch.setattr(integrations_setup.subprocess, "run", _fail)


def _silent_clone(monkeypatch: pytest.MonkeyPatch) -> None:
    """A `git clone` that reports success without touching the network."""

    def _ok(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(integrations_setup.subprocess, "run", _ok)


# --------------------------------------------------------------------------- #
# 1. The default is a plan
# --------------------------------------------------------------------------- #


def test_setup_defaults_to_a_network_free_plan(tmp_path: Path) -> None:
    """No clone, no config, no install -- whatever is on this machine's PATH.

    Asserted on the bundles rather than on a fixed result order, because the MCP
    rows legitimately read `unavailable` on a runner without Node or uv.
    """
    results = _by_name(setup_integrations(tmp_path))
    assert results["fabric-skills"].status == "planned"
    assert results["dbt-skills"].status == "planned"
    assert not (tmp_path / INTEGRATIONS_DIR).exists()


def test_planned_render_names_the_dry_run_and_stays_ascii(tmp_path: Path) -> None:
    rendered = render_results(setup_integrations(tmp_path))
    assert "Dry run only" in rendered
    assert rendered.isascii()


def test_existing_fabric_bundle_is_detected(tmp_path: Path) -> None:
    _install(tmp_path, FABRIC_SKILLS)
    assert _by_name(setup_integrations(tmp_path))["fabric-skills"].status == "present"


def test_existing_dbt_bundle_is_detected(tmp_path: Path) -> None:
    _install(tmp_path, DBT_SKILLS)
    assert _by_name(setup_integrations(tmp_path))["dbt-skills"].status == "present"


def test_a_partial_bundle_is_not_reported_as_present(tmp_path: Path) -> None:
    path = tmp_path / FABRIC_SKILLS.directory / FABRIC_SKILLS.required[0]
    path.parent.mkdir(parents=True)
    path.write_text("name: test\n", encoding="utf-8")
    assert _by_name(setup_integrations(tmp_path))["fabric-skills"].status == "planned"


# --------------------------------------------------------------------------- #
# 2. The ambient interpreter is never mutated
# --------------------------------------------------------------------------- #


def test_dbt_runtime_never_installs_into_the_active_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _nothing_on_path(monkeypatch)
    _no_subprocess(monkeypatch)

    result = _by_name(setup_integrations(tmp_path, apply=True))["dbt-runtime"]

    assert result.status == "unavailable"
    assert "active interpreter" in result.detail
    assert "dbt-core==1.12.0" in result.detail


def test_dbt_runtime_is_present_when_dbt_is_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        integrations_setup.shutil,
        "which",
        lambda name: "/bin/dbt" if name == "dbt" else None,
    )
    assert _by_name(setup_integrations(tmp_path))["dbt-runtime"].status == "present"


# --------------------------------------------------------------------------- #
# 3. MCP registration merges rather than clobbers
# --------------------------------------------------------------------------- #


def test_mcp_registration_preserves_unrelated_servers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _everything_on_path(monkeypatch)
    _silent_clone(monkeypatch)
    config_path = tmp_path / MCP_CONFIG
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps({"mcpServers": {"existing": {"command": "keep-me"}}}),
        encoding="utf-8",
    )

    setup_integrations(tmp_path, apply=True)

    servers = json.loads(config_path.read_text(encoding="utf-8"))["mcpServers"]
    assert set(servers) == {"existing", "powerbi-modeling-mcp", "dbt-mcp"}
    assert servers["existing"] == {"command": "keep-me"}


def test_unparseable_mcp_config_fails_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _everything_on_path(monkeypatch)
    _silent_clone(monkeypatch)
    config_path = tmp_path / MCP_CONFIG
    config_path.parent.mkdir(parents=True)
    config_path.write_text("{ not json", encoding="utf-8")

    results = _by_name(setup_integrations(tmp_path, apply=True))

    assert results["powerbi-modeling-mcp"].status == "failed"
    assert config_path.read_text(encoding="utf-8") == "{ not json"


def test_powerbi_mcp_is_registered_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _everything_on_path(monkeypatch)
    _silent_clone(monkeypatch)

    setup_integrations(tmp_path, apply=True)

    entry = json.loads((tmp_path / MCP_CONFIG).read_text(encoding="utf-8"))
    assert "--readonly" in entry["mcpServers"]["powerbi-modeling-mcp"]["args"]


# --------------------------------------------------------------------------- #
# 4. Nothing is offered unprompted
# --------------------------------------------------------------------------- #


def test_no_other_command_can_trigger_the_installer() -> None:
    """The installer is reachable only through its own verb.

    A read-only governance verb must stay read-only: `seshat check` must not be
    able to end in a third-party clone. Enforced structurally -- the CLI entry
    point does not import this module at all -- because a guard inside the
    installer would still leave the call site in place for the next edit to
    widen. A first-arrival offer belongs to `first-hour-compass` instead.
    """
    entry_point = (_REPO_ROOT / "src" / "seshat" / "cli" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert "integrations_setup" not in entry_point
    assert "offer_first_run" not in entry_point


def test_the_installer_exposes_no_ambient_entry_point() -> None:
    """No module-level hook survives that another command could call."""
    assert not hasattr(integrations_setup, "offer_first_run")


# --------------------------------------------------------------------------- #
# 5. The CLI verb
# --------------------------------------------------------------------------- #


def test_cli_refuses_a_directory_that_is_not_a_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--repo` is validated, not trusted: no workspace, no `.seshat/` seeded."""
    _no_subprocess(monkeypatch)
    args = Namespace(repo=str(tmp_path), apply=True, yes=True, as_json=False)

    assert integrations_main(args) == 2

    assert "is not a Seshat workspace" in capsys.readouterr().err
    assert not (tmp_path / ".seshat").exists()


def test_cli_reports_operator_action_with_a_nonzero_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _nothing_on_path(monkeypatch)
    _no_subprocess(monkeypatch)
    args = Namespace(
        repo=str(_workspace(tmp_path)), apply=False, yes=False, as_json=True
    )

    code = integrations_main(args)

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert "dbt-runtime" in {item["name"] for item in payload}


def test_cli_default_run_installs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _no_subprocess(monkeypatch)
    root = _workspace(tmp_path)
    args = Namespace(repo=str(root), apply=False, yes=False, as_json=False)

    integrations_main(args)

    capsys.readouterr()
    assert not (root / FABRIC_SKILLS.directory).exists()
    assert not (root / MCP_CONFIG).exists()


@pytest.mark.parametrize("flag", ["apply", "yes"])
def test_an_explicit_flag_approves_without_any_prompt(
    flag: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _nothing_on_path(monkeypatch)
    _no_subprocess(monkeypatch)
    monkeypatch.setattr(
        "seshat.cli.commands.integrations._prompted",
        lambda _: pytest.fail(f"--{flag} still prompted"),
    )
    args = Namespace(
        repo=str(_workspace(tmp_path)), apply=False, yes=False, as_json=False
    )
    setattr(args, flag, True)

    assert integrations_main(args) == 1
    assert "git is not on PATH" in capsys.readouterr().out


def test_an_attended_client_is_asked_before_anything_installs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _nothing_on_path(monkeypatch)
    _no_subprocess(monkeypatch)
    monkeypatch.setattr("seshat.cli.commands.integrations._attended", lambda: True)
    monkeypatch.setattr(integrations_setup, "confirm", lambda _: False)
    root = _workspace(tmp_path)
    args = Namespace(repo=str(root), apply=False, yes=False, as_json=False)

    assert integrations_main(args) == 1

    assert "Dry run only" in capsys.readouterr().out
    assert not (root / MCP_CONFIG).exists()


def test_needs_operator_action_only_counts_failed_and_unavailable() -> None:
    ok = [IntegrationResult("a", "present", ""), IntegrationResult("b", "planned", "")]
    assert needs_operator_action(ok) is False
    assert needs_operator_action([*ok, IntegrationResult("c", "failed", "")]) is True
    assert (
        needs_operator_action([*ok, IntegrationResult("d", "unavailable", "")]) is True
    )


# --------------------------------------------------------------------------- #
# 6. Installer output is machine-local
# --------------------------------------------------------------------------- #


def test_installer_output_is_git_ignored() -> None:
    """Cloned third-party bundles and the generated MCP config are run output.

    Committing them would put two vendored upstream repositories in this tree and
    dirty every adopter's `git status` -- the same reasoning that ignores
    `.seshat/watch/` and `.seshat/dagster/`.
    """
    for path in (
        f"{INTEGRATIONS_DIR.as_posix()}/mcp.json",
        f"{FABRIC_SKILLS.directory.as_posix()}/README.md",
        f"{DBT_SKILLS.directory.as_posix()}/README.md",
    ):
        assert gitutil.git_check_ignore(_REPO_ROOT, path) is True, path


# --------------------------------------------------------------------------- #
# 7. The apply path fails loudly and never clobbers
# --------------------------------------------------------------------------- #


def test_a_failed_clone_is_reported_not_swallowed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _everything_on_path(monkeypatch)

    def _boom(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            command, 128, "", "fatal: repository not found"
        )

    monkeypatch.setattr(integrations_setup.subprocess, "run", _boom)

    result = _by_name(setup_integrations(tmp_path, apply=True))["fabric-skills"]

    assert result.status == "failed"
    assert "repository not found" in result.detail


def test_a_clone_that_lands_no_skills_is_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A green exit code is not evidence: the required skills must be on disk."""
    _everything_on_path(monkeypatch)
    _silent_clone(monkeypatch)

    result = _by_name(setup_integrations(tmp_path, apply=True))["fabric-skills"]

    assert result.status == "failed"
    assert "missing required skills" in result.detail


def test_an_incomplete_existing_directory_is_never_clobbered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _everything_on_path(monkeypatch)
    _install(tmp_path, DBT_SKILLS)  # so the only clone candidate is the stray one
    _no_subprocess(monkeypatch)
    stray = tmp_path / FABRIC_SKILLS.directory / "leftover.txt"
    stray.parent.mkdir(parents=True)
    stray.write_text("keep\n", encoding="utf-8")

    result = _by_name(setup_integrations(tmp_path, apply=True))["fabric-skills"]

    assert result.status == "failed"
    assert "incomplete existing directory" in result.detail
    assert stray.read_text(encoding="utf-8") == "keep\n"


def _dagster_project(root: Path) -> Path:
    project = root / integrations_setup.DAGSTER_PROJECT
    project.mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return project


def test_dagster_runtime_is_planned_when_the_project_has_no_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _nothing_on_path(monkeypatch)
    _dagster_project(tmp_path)

    result = _by_name(setup_integrations(tmp_path))["dagster-runtime"]

    assert result.status == "planned"
    assert ".venv" in result.detail


def test_dagster_runtime_needs_uv_to_provision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _nothing_on_path(monkeypatch)
    _no_subprocess(monkeypatch)
    _dagster_project(tmp_path)

    result = _by_name(setup_integrations(tmp_path, apply=True))["dagster-runtime"]

    assert result.status == "unavailable"
    assert "uv is not on PATH" in result.detail


def test_bundled_dagster_skill_is_detected(tmp_path: Path) -> None:
    skill = (
        tmp_path
        / "integrations/claude-code/seshat-bi/skills/dagster-workflows/SKILL.md"
    )
    skill.parent.mkdir(parents=True)
    skill.write_text("name: dagster-workflows\n", encoding="utf-8")

    assert _by_name(setup_integrations(tmp_path))["dagster-skills"].status == "present"


def test_an_accepted_prompt_reaches_the_install_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A "yes" reaches the apply pass, and a missing prerequisite still reports."""
    _nothing_on_path(monkeypatch)
    _no_subprocess(monkeypatch)
    monkeypatch.setattr("seshat.cli.commands.integrations._attended", lambda: True)
    monkeypatch.setattr(integrations_setup, "confirm", lambda _: True)
    args = Namespace(
        repo=str(_workspace(tmp_path)), apply=False, yes=False, as_json=False
    )

    assert integrations_main(args) == 1

    assert "git is not on PATH" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# 8. Rendering and the prompt
# --------------------------------------------------------------------------- #


def test_render_summarises_an_all_present_run() -> None:
    assert "are present" in render_results([IntegrationResult("a", "present", "x")])


def test_render_summarises_an_action_needed_run() -> None:
    assert "operator action" in render_results([IntegrationResult("a", "failed", "x")])


def test_json_render_is_machine_readable() -> None:
    rendered = render_results([IntegrationResult("a", "present", "x")], as_json=True)
    assert json.loads(rendered) == [{"detail": "x", "name": "a", "status": "present"}]


def test_confirm_accepts_only_an_explicit_yes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: " Yes ")
    assert integrations_setup.confirm("?") is True
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert integrations_setup.confirm("?") is False


def test_confirm_reads_an_interrupted_prompt_as_no(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _interrupted(_: str) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", _interrupted)
    assert integrations_setup.confirm("?") is False
