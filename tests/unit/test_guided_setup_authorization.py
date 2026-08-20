"""Authorization and delegated execution for the derived scope (spec 155, US2).

Every test here answers one question: can anything other than a committed,
named-human `governance` approval covering the EXACT derived scope cause an
install? The answer must be no -- including when the caller supplies every signal
available to it at once.

The repo fixture is a real git repository, because the gate reads HEAD. A fake
tree would exercise nothing: an approval that is not committed must not
authorize, and that is only observable against real git state.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

APPROVALS = "contracts/provisioning-approvals.yaml"
_SCOPE = ("connectorx", "powerbi-modeling-mcp", "fabric-skills")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git repo carrying a Postgres + Power BI project."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / ".seshat").mkdir()
    (tmp_path / "contracts").mkdir()
    table = tmp_path / "mappings" / "sales"
    table.mkdir(parents=True)
    (table / "source-map.yaml").write_text(
        "meta:\n  table_id: sales\n  source_system: kaggle_retail\n", encoding="utf-8"
    )
    (tmp_path / "powerbi").mkdir()
    (tmp_path / "powerbi" / "Sales.pbip").write_text("{}", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "seed", "--no-gpg-sign")
    return tmp_path


def _commit_approval(
    repo: Path, components: list[str], *, owner: str | None = None
) -> None:
    body = (
        "approvals:\n"
        "  - stage: provisioning\n"
        f'    owner: "{owner or "Ahmed Shaaban (governance)"}"\n'
        '    at: "2026-08-20"\n'
        f"    components: {components!r}\n"
    )
    (repo / APPROVALS).write_text(body, encoding="utf-8")
    _git(repo, "add", APPROVALS)
    _git(repo, "commit", "-qm", "approval", "--no-gpg-sign")


def _args(root: Path, **overrides) -> Namespace:
    base = dict(
        repo=str(root),
        profile=None,
        refresh=True,
        apply=True,
        yes=True,
        as_json=False,
        harness=[],
        derived=True,
    )
    base.update(overrides)
    return Namespace(**base)


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Capture what the CLI hands to the installer, without installing.

    `live_resolvers` raising is the network assertion: a refusal path that
    touched it would fail loudly rather than quietly reaching the index.
    """
    import seshat.integrations_setup as setup

    seen: dict = {"apply_calls": [], "resolver_calls": 0}

    def _apply(root, **kwargs):
        seen["apply_calls"].append(kwargs)
        from seshat.integrations.installer import SetupOutcome

        return SetupOutcome(profile="derived")

    def _resolvers():
        seen["resolver_calls"] += 1
        return object()

    monkeypatch.setattr(setup, "apply_profile", _apply)
    monkeypatch.setattr(setup, "live_resolvers", _resolvers)
    return seen


def _requested(spy: dict) -> tuple[str, ...]:
    kwargs = spy["apply_calls"][0]
    return tuple(item.id for item in kwargs["components"])


# --------------------------------------------------------------------------- #
# T029: no committed approval, every caller-controlled signal supplied.
# --------------------------------------------------------------------------- #


def test_no_approval_refuses_with_every_signal_supplied(
    repo: Path, spy: dict, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """T029 (FR-012, US2 AS1, SC-005, scenario F).

    Intent, non-interactivity, machine-readable mode, a piped answer and a
    simulated terminal, together. None of them is authority.
    """
    import io
    import sys

    from seshat.cli.commands.integrations import integrations_main

    monkeypatch.setattr(sys, "stdin", io.StringIO("y\n"))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True, raising=False)

    code = integrations_main(_args(repo, as_json=True))
    err = capsys.readouterr().err

    assert code == 2
    assert spy["apply_calls"] == []
    assert spy["resolver_calls"] == 0
    assert "committed named-human approval" in err
    assert not (repo / ".seshat" / "integrations").exists()


def test_an_agent_instruction_asserting_approval_is_not_approval(
    repo: Path, spy: dict, capsys
) -> None:
    """T029 (FR-012): an extra namespace attribute confers nothing."""
    from seshat.cli.commands.integrations import integrations_main

    args = _args(repo)
    args.approved = True  # an agent asserting its own authority
    args.authorized = True

    assert integrations_main(args) == 2
    assert spy["apply_calls"] == []


def test_an_uncommitted_approval_authorizes_nothing(
    repo: Path, spy: dict, capsys
) -> None:
    """T029 (FR-012, US2 AS1): authority is read at HEAD only."""
    from seshat.cli.commands.integrations import integrations_main

    (repo / APPROVALS).write_text(
        "approvals:\n"
        "  - stage: provisioning\n"
        '    owner: "Ahmed Shaaban (governance)"\n'
        '    at: "2026-08-20"\n'
        f"    components: {list(_SCOPE)!r}\n",
        encoding="utf-8",
    )

    assert integrations_main(_args(repo)) == 2
    assert spy["apply_calls"] == []


# --------------------------------------------------------------------------- #
# T030-T032: scope binding.
# --------------------------------------------------------------------------- #


def test_a_narrower_approval_does_not_authorize_the_wider_scope(
    repo: Path, spy: dict, capsys
) -> None:
    """T030 (FR-013, US2 AS2, SC-006, scenario G): both scopes are named."""
    from seshat.cli.commands.integrations import integrations_main

    _commit_approval(repo, ["connectorx"])

    code = integrations_main(_args(repo))
    err = capsys.readouterr().err

    assert code == 2
    assert spy["apply_calls"] == []
    assert "connectorx" in err
    assert "fabric-skills" in err


def test_an_exact_approval_authorizes_execution(repo: Path, spy: dict) -> None:
    """T031 (FR-012, US2 AS3, scenario H): the installer may run this scope."""
    from seshat.cli.commands.integrations import integrations_main

    _commit_approval(repo, list(_SCOPE))
    integrations_main(_args(repo))

    assert len(spy["apply_calls"]) == 1
    assert set(_requested(spy)) == set(_SCOPE)


def test_a_superset_approval_authorizes_the_derived_subset(
    repo: Path, spy: dict
) -> None:
    """T032 (edge case): a wider recorded scope covers a narrower request."""
    from seshat.cli.commands.integrations import integrations_main

    _commit_approval(repo, [*_SCOPE, "dbt-core", "dagster"])
    integrations_main(_args(repo))

    assert len(spy["apply_calls"]) == 1


def test_a_wrong_authority_class_refuses(repo: Path, spy: dict, capsys) -> None:
    """T031 (FR-012): shape validity is necessary, not sufficient."""
    from seshat.cli.commands.integrations import integrations_main

    _commit_approval(repo, list(_SCOPE), owner="Ahmed Shaaban (analyst)")

    assert integrations_main(_args(repo)) == 2
    assert spy["apply_calls"] == []
    assert "governance" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# T033-T035: blockers, refusal shape, and what is never installed.
# --------------------------------------------------------------------------- #


def test_a_blocked_plan_refuses_before_authority_is_consulted(
    repo: Path, spy: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T033 (FR-005, US2 AS5): no approval can clear a blocker.

    `evaluate` is replaced with a landmine rather than merely asserted unused:
    consulting authority for a plan that must not run would be the wrong order
    of operations even if the outcome happened to be a refusal.
    """
    from seshat.cli.commands.integrations import integrations_main
    from seshat.integrations import approval

    def _landmine(*args, **kwargs):
        raise AssertionError("authority was consulted for a blocked plan")

    monkeypatch.setattr(approval, "evaluate", _landmine)
    (repo / "contracts" / "capability-declines.yaml").write_text(
        "declines:\n  - capability: powerbi-integration\n", encoding="utf-8"
    )
    _commit_approval(repo, list(_SCOPE))

    assert integrations_main(_args(repo)) == 1
    assert spy["apply_calls"] == []


def test_the_refusal_is_machine_readable_with_a_next_action(
    repo: Path, spy: dict, capsys
) -> None:
    """T034 (FR-014, US2 AS6, SC-008): a categorical reason and a next action."""
    import json

    from seshat.cli.commands.integrations import integrations_main

    integrations_main(_args(repo, as_json=True, apply=False))
    payload = json.loads(capsys.readouterr().out)
    row = next(
        item
        for item in payload["capabilities"]
        if item["id"] == "database-connectivity"
    )

    assert row["approval_required"] is True
    assert row["approval_met"] is False
    assert row["post_execution_status"] == "not-attempted"


def test_a_not_required_capability_is_never_handed_to_the_installer(
    repo: Path, spy: dict
) -> None:
    """T035 (FR-021, US2 AS4, scenario B): no orchestration provider, ever."""
    from seshat.cli.commands.integrations import integrations_main
    from seshat.integrations.derivation import CAPABILITY_COMPONENTS

    _commit_approval(repo, list(_SCOPE))
    integrations_main(_args(repo))
    requested = set(_requested(spy))

    for capability in ("orchestration", "transformation-engine"):
        assert not requested & set(CAPABILITY_COMPONENTS[capability])


def test_apply_without_refresh_refuses_before_installing(
    repo: Path, spy: dict, capsys
) -> None:
    """T036 (FR-015): the existing exact-resolution precondition is not removed."""
    from seshat.cli.commands.integrations import integrations_main

    _commit_approval(repo, list(_SCOPE))

    assert integrations_main(_args(repo, refresh=False)) == 2
    assert spy["apply_calls"] == []
    assert "--refresh" in capsys.readouterr().err
