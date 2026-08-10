"""Compatibility contracts for the legacy integrations setup module.

The catalog-backed ``seshat.integrations`` package owns planning, installation,
validation, and locking.  This module tests only the deliberately retained
Python/CLI facade; operational installer behavior belongs in the curated-stack
tests.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from seshat import gitutil, integrations_setup
from seshat.cli.commands.integrations import integrations_main
from seshat.integrations.compat import BASELINE_PINS
from seshat.integrations.installer import ComponentPlan, SetupOutcome
from seshat.integrations_setup import (
    DBT_CORE_PIN,
    DBT_SKILLS,
    FABRIC_SKILLS,
    INTEGRATIONS_DIR,
    LOCK_FILE,
    IntegrationResult,
    needs_operator_action,
    render_results,
    setup_integrations,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".seshat").mkdir()
    return tmp_path


def _args(root: Path, **overrides: object) -> Namespace:
    values: dict[str, object] = {
        "repo": str(root),
        "profile": "analytics-full",
        "refresh": False,
        "apply": False,
        "yes": False,
        "as_json": False,
    }
    values.update(overrides)
    return Namespace(**values)


def _canonical_outcome(*, status: str = "planned") -> SetupOutcome:
    return SetupOutcome(
        profile="analytics-full",
        rows=[
            ComponentPlan(
                component="fabric-skills",
                profile="powerbi-fabric",
                channel="stable",
                pinned="v3.0.0",
                source="github-microsoft-fabric",
                status=status,
                detail="canonical result",
            )
        ],
    )


def test_compatibility_plan_delegates_and_projects_canonical_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: dict[str, object] = {}

    def _plan(root: Path, *, profile: str, resolvers=None) -> SetupOutcome:
        called.update(root=root, profile=profile, resolvers=resolvers)
        return _canonical_outcome()

    monkeypatch.setattr(integrations_setup, "plan_profile", _plan)

    results = setup_integrations(tmp_path, profile="powerbi-fabric")

    assert called == {
        "root": tmp_path.resolve(),
        "profile": "powerbi-fabric",
        "resolvers": None,
    }
    assert results == [
        IntegrationResult("fabric-skills", "planned", "canonical result")
    ]


def test_compatibility_apply_requires_explicit_resolvers(tmp_path: Path) -> None:
    results = setup_integrations(tmp_path, apply=True)

    assert results == [
        IntegrationResult(
            "integration-apply",
            "failed",
            "exact resolvers are required for apply; no changes were made",
        )
    ]


def test_compatibility_apply_delegates_with_injected_resolvers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel_resolvers = object()
    sentinel_runner = object()
    called: dict[str, object] = {}

    def _apply(root: Path, *, profile: str, resolvers, runner=None) -> SetupOutcome:
        called.update(root=root, profile=profile, resolvers=resolvers, runner=runner)
        return _canonical_outcome(status="installed")

    monkeypatch.setattr(integrations_setup, "apply_profile", _apply)

    results = setup_integrations(
        tmp_path,
        apply=True,
        resolvers=sentinel_resolvers,
        runner=sentinel_runner,
    )

    assert called == {
        "root": tmp_path.resolve(),
        "profile": "analytics-full",
        "resolvers": sentinel_resolvers,
        "runner": sentinel_runner,
    }
    assert results == [
        IntegrationResult("fabric-skills", "installed", "canonical result")
    ]


def test_compatibility_metadata_is_derived_from_canonical_truth() -> None:
    source = Path(integrations_setup.__file__).read_text(encoding="utf-8")

    assert FABRIC_SKILLS.name == "fabric-skills"
    assert DBT_SKILLS.name == "dbt-agent-skills"
    assert FABRIC_SKILLS.required
    assert DBT_SKILLS.required
    assert DBT_CORE_PIN == f"dbt-core=={BASELINE_PINS['dbt-core']}"
    assert "https://github.com/microsoft/skills-for-fabric.git" not in source
    assert "https://github.com/dbt-labs/dbt-agent-skills.git" not in source
    assert 'DBT_CORE_PIN = "dbt-core==1.12.0"' not in source


def test_compatibility_facade_contains_no_operational_installer() -> None:
    source = Path(integrations_setup.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "subprocess.run",
        "def _clone(",
        "def _register(",
        "def _provision_dagster(",
        "def _skill_bundle(",
        "def _mcp_server(",
    ):
        assert forbidden not in source


def test_facade_exposes_no_ambient_entry_point() -> None:
    entry_point = (_REPO_ROOT / "src/seshat/cli/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "integrations_setup" not in entry_point
    assert "offer_first_run" not in entry_point
    assert not hasattr(integrations_setup, "offer_first_run")


def test_legacy_render_and_operator_action_contracts() -> None:
    planned = [IntegrationResult("a", "planned", "x")]
    assert "Dry run only" in render_results(planned)
    assert render_results(planned).isascii()
    assert needs_operator_action(planned) is False

    failed = [IntegrationResult("a", "failed", "x")]
    assert "operator action" in render_results(failed)
    assert needs_operator_action(failed) is True

    rendered = render_results([IntegrationResult("a", "present", "x")], as_json=True)
    assert json.loads(rendered) == [{"detail": "x", "name": "a", "status": "present"}]


@pytest.mark.parametrize("status", ["not-installed", "activation-required", "stale"])
def test_projected_discovery_blockers_are_operator_action(status: str) -> None:
    """A requested official skill that is not discoverable needs a human.

    The projection flattens discovery rows into the same list as component
    plans, so a status set covering only component-plan tokens let an
    undiscoverable skill render as "everything is present" (Codex P2, #597).
    Asserted on the APPLY-path wording, because the plan path short-circuits on
    "planned" and would hide the defect.
    """
    results = [
        IntegrationResult("fabric-skills", "present", "installed"),
        IntegrationResult(
            f"fabric-skills/{status}-harness", status, "not discoverable"
        ),
    ]
    assert needs_operator_action(results) is True
    assert "operator action" in render_results(results)
    assert "Integration runtimes and configuration are present." not in render_results(
        results
    )


def test_an_unchecked_harness_is_not_an_outstanding_operator_action() -> None:
    """Not asking about a harness is not the same as a blocked one: only an
    explicitly requested-and-undiscoverable skill demands human action."""
    results = [
        IntegrationResult("fabric-skills", "present", "installed"),
        IntegrationResult("fabric-skills/codex", "not-checked", "not requested"),
    ]
    assert needs_operator_action(results) is False
    assert "present" in render_results(results)


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


def test_cli_refuses_a_directory_that_is_not_a_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert integrations_main(_args(tmp_path, apply=True, yes=True)) == 2
    assert "is not a Seshat workspace" in capsys.readouterr().err
    assert not (tmp_path / ".seshat").exists()


def test_cli_default_is_a_plan_and_never_applies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _workspace(tmp_path)
    monkeypatch.setattr(
        integrations_setup, "plan_profile", lambda *a, **k: _canonical_outcome()
    )
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: pytest.fail("a default plan reached apply"),
    )

    assert integrations_main(_args(root)) == 0
    assert "fabric-skills" in capsys.readouterr().out
    assert not (root / LOCK_FILE).exists()


def test_cli_apply_without_refresh_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _workspace(tmp_path)
    monkeypatch.setattr(
        integrations_setup, "plan_profile", lambda *a, **k: _canonical_outcome()
    )
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: pytest.fail("apply ran without exact resolvers"),
    )

    assert integrations_main(_args(root, apply=True, yes=True)) == 2
    assert "needs --refresh" in capsys.readouterr().err


def test_cli_yes_alone_never_enables_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _workspace(tmp_path)
    monkeypatch.setattr(
        integrations_setup, "plan_profile", lambda *a, **k: _canonical_outcome()
    )
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: pytest.fail("--yes enabled apply"),
    )

    assert integrations_main(_args(root, yes=True)) == 0


def test_cli_refresh_apply_delegates_to_canonical_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _workspace(tmp_path)
    resolvers = object()
    calls: list[str] = []
    monkeypatch.setattr(integrations_setup, "live_resolvers", lambda: resolvers)
    monkeypatch.setattr(
        integrations_setup,
        "plan_profile",
        lambda *a, **k: calls.append("plan") or _canonical_outcome(),
    )
    monkeypatch.setattr(
        integrations_setup,
        "apply_profile",
        lambda *a, **k: calls.append("apply") or _canonical_outcome(status="installed"),
    )

    assert integrations_main(_args(root, refresh=True, apply=True, yes=True)) == 0
    assert calls == ["plan", "apply"]


def test_installer_output_is_git_ignored() -> None:
    for path in (
        f"{INTEGRATIONS_DIR.as_posix()}/mcp.json",
        f"{FABRIC_SKILLS.directory.as_posix()}/README.md",
        f"{DBT_SKILLS.directory.as_posix()}/README.md",
    ):
        assert gitutil.git_check_ignore(_REPO_ROOT, path) is True, path
