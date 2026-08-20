"""Honest results, reuse, and state for a derived scope (spec 155, US3).

These tests run the REAL installer with an injected runner, because the
properties under test are about what the installer is asked to do and what the
control plane says afterwards -- neither of which a stub of the installer could
show. Nothing here touches a network or a real package index: the only indexes in
the object graph are the fakes.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from seshat.integrations.catalog import ENV_DIR, LOCK_FILE
from seshat.integrations.resolvers import Resolvers
from tests.unit._curated_stack_fixtures import (
    FakeGitHub,
    FakeNpm,
    FakePypi,
    _no_network,
    _release,
    _tools_on_path,
)

pytestmark = pytest.mark.unit

_SCOPE = ("connectorx", "powerbi-modeling-mcp", "fabric-skills")


def _project(root: Path) -> Path:
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    table = root / "mappings" / "sales"
    table.mkdir(parents=True)
    (table / "source-map.yaml").write_text(
        "meta:\n  table_id: sales\n  source_system: kaggle_retail\n", encoding="utf-8"
    )
    (root / "powerbi").mkdir()
    (root / "powerbi" / "Sales.pbip").write_text("{}", encoding="utf-8")
    return root


def _resolvers() -> Resolvers:
    return Resolvers(
        pypi=FakePypi({"connectorx": {"releases": {"0.4.4": _release("0.4.4")}}}),
        npm=FakeNpm(
            {"@microsoft/powerbi-modeling-mcp": {"dist-tags": {"latest": "1.2.3"}}}
        ),
        github=FakeGitHub(
            release={"tag_name": "v0.4.0"}, commits={"v0.4.0": {"sha": "a" * 40}}
        ),
        python_version=(3, 13),
    )


class Runner:
    """A subprocess seam that records argv and can fail chosen components.

    A clone command also WRITES the payload the catalog declares required, the
    way a real clone would. Without that the installer's payload validation
    fails every GitHub component, so "one succeeded and one failed" could never
    be set up -- and a partial-failure test in which everything fails proves
    nothing about partial failure.
    """

    def __init__(self, fail_on: str = "") -> None:
        self.commands: list[list[str]] = []
        self.fail_on = fail_on

    def __call__(self, command: list[str], cwd: Path):
        self.commands.append(command)
        joined = " ".join(command)
        failed = bool(self.fail_on) and self.fail_on in joined
        if not failed and "clone" in command:
            self._write_payload(command)
        return subprocess.CompletedProcess(
            command, 1 if failed else 0, "", "boom" if failed else ""
        )

    @staticmethod
    def _write_payload(command: list[str]) -> None:
        from seshat.integrations.catalog import DEFAULT_PROFILE, PROFILES

        destination = Path(command[-1])
        for item in PROFILES[DEFAULT_PROFILE]:
            if item.coordinate not in " ".join(command):
                continue
            for relative in item.required_paths:
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# payload\n", encoding="utf-8")

    def mentions(self, token: str) -> bool:
        return any(token in " ".join(command) for command in self.commands)


def _derived_apply(root: Path, runner: Runner, monkeypatch) -> object:
    from seshat.integrations.catalog import component
    from seshat.integrations.installer import apply

    _no_network(monkeypatch)
    _tools_on_path(monkeypatch)
    return apply(
        root,
        components=tuple(component(cid) for cid in _SCOPE),
        resolvers=_resolvers(),
        runner=runner,
    )


# --------------------------------------------------------------------------- #
# T039, T042: environments and reuse.
# --------------------------------------------------------------------------- #


def test_a_component_installs_into_its_own_base_profile_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T039 (FR-015, research R2): no isolation target is invented.

    Asserted on the argv the installer actually built, not on a returned label:
    the environment is where the package lands, so argv is the only place the
    claim is observable.
    """
    runner = Runner()
    _derived_apply(_project(tmp_path), runner, monkeypatch)

    assert runner.mentions((ENV_DIR / "analytics-core").as_posix())
    assert not runner.mentions((ENV_DIR / "analytics-full").as_posix())


def test_a_component_a_previous_profile_run_installed_is_not_reinstalled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T042 (FR-018, US3 AS3, SC-010, scenario K): reuse, observed on the runner.

    The previous run is simulated the way the control plane detects one -- the
    distribution metadata inside the `analytics-full` environment -- so this
    exercises the real presence check rather than a flag.
    """
    root = _project(tmp_path)
    site = root / ENV_DIR / "analytics-full" / "lib" / "python3.13" / "site-packages"
    site.mkdir(parents=True)
    (site / "connectorx-0.4.4.dist-info").mkdir()
    (root / ENV_DIR / "analytics-full" / "bin").mkdir(parents=True, exist_ok=True)
    (root / ENV_DIR / "analytics-full" / "bin" / "python").write_text(
        "", encoding="utf-8"
    )

    runner = Runner()
    outcome = _derived_apply(root, runner, monkeypatch)
    row = next(row for row in outcome.rows if row.component == "connectorx")

    assert row.status == "present"
    assert not runner.mentions("connectorx==")


# --------------------------------------------------------------------------- #
# T040, T041: readiness is verification, and partial failure is honest.
# --------------------------------------------------------------------------- #


def test_install_success_without_verification_is_not_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T040 (FR-016, US3 AS1, SC-008, scenario I).

    Every install command returns zero and NOTHING lands on disk. A run that
    read the install status would call this ready; readiness comes from the
    control plane's own presence check, so it must not.
    """
    from seshat.integrations.guided_setup import derive_scope, readiness_from

    root = _project(tmp_path)
    runner = Runner()
    outcome = _derived_apply(root, runner, monkeypatch)
    readiness, next_actions = readiness_from(root, derive_scope(root), outcome)

    assert readiness["database-connectivity"] != "ready"
    assert next_actions["database-connectivity"]


def test_one_failed_component_leaves_the_other_capability_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T041 (FR-017, US3 AS2, SC-009, scenario J): both outcomes stay visible."""
    from seshat.integrations.guided_setup import derive_scope, readiness_from

    root = _project(tmp_path)
    runner = Runner(fail_on="connectorx")
    outcome = _derived_apply(root, runner, monkeypatch)
    readiness, next_actions = readiness_from(root, derive_scope(root), outcome)
    statuses = {row.component: row.status for row in outcome.rows}

    assert readiness["database-connectivity"] == "failed"
    assert readiness["powerbi-integration"] == "ready"
    assert statuses["connectorx"] == "failed"
    assert statuses["fabric-skills"] == "installed"
    assert next_actions["database-connectivity"]
    assert "powerbi-integration" not in next_actions


def test_a_partial_run_is_never_reported_successful(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T041 (FR-017, SC-009): succeeded and failed remain distinguishable."""
    root = _project(tmp_path)
    outcome = _derived_apply(root, Runner(fail_on="connectorx"), monkeypatch)

    assert outcome.needs_action
    assert {row.status for row in outcome.rows} != {"installed"}


def test_the_status_renders_the_failure_and_its_next_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T040/T045 (FR-016, FR-017): the user is told what failed and what to do."""
    from seshat.integrations.guided_setup import (
        capability_statuses,
        derive_scope,
        readiness_from,
        render_json,
    )

    root = _project(tmp_path)
    outcome = _derived_apply(root, Runner(fail_on="connectorx"), monkeypatch)
    scope = derive_scope(root)
    readiness, next_actions = readiness_from(root, scope, outcome)
    statuses = capability_statuses(
        scope, approval_met=True, readiness=readiness, next_actions=next_actions
    )
    payload = json.loads(render_json(scope, statuses))
    row = next(
        item
        for item in payload["capabilities"]
        if item["id"] == "database-connectivity"
    )

    assert row["post_execution_status"] == "failed"
    assert row["next_action"]


# --------------------------------------------------------------------------- #
# T043: the state record.
# --------------------------------------------------------------------------- #


def test_a_derived_apply_keeps_out_of_scope_lock_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T043 (FR-019, US3 AS4, SC-011): a narrower run discards nothing."""
    from seshat.integrations.lockfile import SCHEMA

    root = _project(tmp_path)
    (root / LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
    (root / LOCK_FILE).write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "profile": "analytics-full",
                "resolved_at": "2026-08-19T00:00:00Z",
                "components": {"dbt-core": {"version": "1.12.0"}},
            }
        ),
        encoding="utf-8",
    )

    _derived_apply(root, Runner(), monkeypatch)
    written = json.loads((root / LOCK_FILE).read_text(encoding="utf-8"))

    assert "dbt-core" in written["components"]
    assert written["profile"] == "derived"


def test_a_derived_apply_does_not_claim_a_curated_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T043 (FR-019): the selection basis is reported truthfully."""
    outcome = _derived_apply(_project(tmp_path), Runner(), monkeypatch)

    assert outcome.profile == "derived"
