"""The committed provisioning-approval gate (spec 154, issue #671).

Every test here answers one question: can anything other than a committed,
named-human, `governance`-class approval covering the requested components make
`evaluate()` return `authorized`? The answer must be no.

Fixtures are built from the real artifact shape documented in
`specs/154-secure-provisioning-approval/research.md`, never from a dict that only
these tests believe in.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git repo -- the gate reads HEAD, so a fake tree cannot exercise it."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "T")
    (tmp_path / "contracts").mkdir()
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "seed.txt")
    _git(tmp_path, "commit", "-qm", "seed", "--no-gpg-sign")
    return tmp_path


APPROVALS = "contracts/provisioning-approvals.yaml"


def _row(
    owner: str = "Ahmed Shaaban (governance)",
    at: str = "2026-08-20",
    components: str = '["duckdb", "polars"]',
    extra: str = "",
) -> str:
    return (
        "approvals:\n"
        "  - stage: provisioning\n"
        f'    owner: "{owner}"\n'
        f'    at: "{at}"\n'
        f"    components: {components}\n"
        f"{extra}"
    )


def _write(repo: Path, text: str) -> None:
    (repo / APPROVALS).write_text(text, encoding="utf-8")


def _commit(repo: Path, text: str) -> None:
    _write(repo, text)
    _git(repo, "add", APPROVALS)
    _git(repo, "commit", "-qm", "approval", "--no-gpg-sign")


# --------------------------------------------------------------------------
# T010-T015: the gate refuses everything that is not a committed approval
# --------------------------------------------------------------------------


def test_absent_approval_file_is_not_authorized(repo: Path) -> None:
    """T010 (FR-013): no artifact at all -> `absent`, never authorized."""
    from seshat.integrations.approval import evaluate

    verdict = evaluate(repo, ("duckdb",))
    assert verdict.reason == "absent"
    assert verdict.authorized is False
    assert verdict.next_action


def test_uncommitted_approval_grants_nothing(repo: Path) -> None:
    """T011 (FR-002): a worktree-only approval is invisible to the gate.

    This is the defect class the Power BI MCP gate was hardened against
    (bug #334): a worktree-reading gate lets the agent author its own approval.
    """
    from seshat.integrations.approval import evaluate

    _write(repo, _row())  # written, deliberately NOT committed
    verdict = evaluate(repo, ("duckdb",))
    assert verdict.authorized is False
    assert verdict.reason == "uncommitted"


def test_committed_then_dirtied_approval_grants_nothing(repo: Path) -> None:
    """T012 (FR-002): committed but since modified -> refused, not last-good."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row())
    _write(repo, _row(components='["duckdb", "polars", "dagster"]'))
    verdict = evaluate(repo, ("dagster",))
    assert verdict.authorized is False
    assert verdict.reason == "uncommitted"


@pytest.mark.parametrize(
    ("label", "owner", "at"),
    [
        ("bare role as the name", "governance", "2026-08-20"),
        ("name without a class", "Ahmed Shaaban", "2026-08-20"),
        ("unparseable date", "Ahmed Shaaban (governance)", "not-a-date"),
    ],
)
def test_malformed_approval_shapes_are_refused(
    repo: Path, label: str, owner: str, at: str
) -> None:
    """T013 (FR-003, FR-004): delegated shape validation, one case each."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(owner=owner, at=at))
    verdict = evaluate(repo, ("duckdb",))
    assert verdict.authorized is False, label
    assert verdict.reason == "invalid_shape", label


def test_undated_approval_is_refused(repo: Path) -> None:
    """T013 (FR-003): a missing `at:` is not a shape-valid approval."""
    from seshat.integrations.approval import evaluate

    _commit(
        repo,
        'approvals:\n  - stage: provisioning\n    owner: "Ahmed Shaaban (governance)"\n'
        '    components: ["duckdb"]\n',
    )
    verdict = evaluate(repo, ("duckdb",))
    assert verdict.authorized is False
    assert verdict.reason == "invalid_shape"


def test_non_governance_authority_class_is_refused(repo: Path) -> None:
    """T014 (FR-004a): `analyst` is shape-VALID but not the provisioning authority.

    `approval_is_shape_valid` accepts any of the five authority classes, so this
    requirement is NOT covered by delegating shape validation -- the gate must
    check the class itself. Verified by probe, recorded in research.md R3.
    """
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(owner="Ahmed Shaaban (analyst)"))
    verdict = evaluate(repo, ("duckdb",))
    assert verdict.authorized is False
    assert verdict.reason == "wrong_authority"


def test_unparseable_yaml_fails_closed(repo: Path) -> None:
    """T015 (FR-013): malformed YAML is a typed refusal, never a raised error."""
    from seshat.integrations.approval import evaluate

    _commit(repo, "approvals: [unclosed\n")
    verdict = evaluate(repo, ("duckdb",))
    assert verdict.authorized is False
    assert verdict.reason == "unparseable"


# --------------------------------------------------------------------------
# T017-T020: scope binding
# --------------------------------------------------------------------------


def test_covered_scope_is_authorized(repo: Path) -> None:
    """T017 (FR-010): the whole point -- a real approval authorizes its scope."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row())
    verdict = evaluate(repo, ("duckdb", "polars"))
    assert verdict.authorized is True
    assert verdict.reason == "authorized"
    assert verdict.owner == "Ahmed Shaaban (governance)"


def test_scope_mismatch_names_both_scopes(repo: Path) -> None:
    """T018 (FR-011): refused, and the reason names approved AND requested."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(components='["duckdb"]'))
    verdict = evaluate(repo, ("dagster",))
    assert verdict.authorized is False
    assert verdict.reason == "scope_mismatch"
    assert "dagster" in verdict.next_action
    assert "duckdb" in verdict.next_action


def test_capability_added_after_approval_is_not_authorized(repo: Path) -> None:
    """T019 (FR-012): an approval never stretches to cover a newly added id."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(components='["duckdb"]'))
    verdict = evaluate(repo, ("duckdb", "polars"))
    assert verdict.authorized is False
    assert verdict.reason == "scope_mismatch"


def test_superset_approval_authorizes_a_subset_request(repo: Path) -> None:
    """T020: a subset is materially within what the human approved."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(components='["duckdb", "polars", "dagster"]'))
    assert evaluate(repo, ("polars",)).authorized is True


def test_two_narrow_rows_do_not_combine_into_wider_authority(repo: Path) -> None:
    """T018/T021 (FR-011): one ROW must cover the whole request.

    The `_authorizing_approval` rule from the Power BI MCP gate, applied here:
    two narrow approvals must not combine into an authority no human granted.
    """
    from seshat.integrations.approval import evaluate

    _commit(
        repo,
        "approvals:\n"
        "  - stage: provisioning\n"
        '    owner: "Ahmed Shaaban (governance)"\n'
        '    at: "2026-08-20"\n'
        '    components: ["duckdb"]\n'
        "  - stage: provisioning\n"
        '    owner: "Ahmed Shaaban (governance)"\n'
        '    at: "2026-08-20"\n'
        '    components: ["polars"]\n',
    )
    verdict = evaluate(repo, ("duckdb", "polars"))
    assert verdict.authorized is False
    assert verdict.reason == "scope_mismatch"


# --------------------------------------------------------------------------
# T022-T026: standing-until-scope-change lifetime
# --------------------------------------------------------------------------


def test_repeat_run_of_the_same_scope_stays_authorized(repo: Path) -> None:
    """T022/T023 (FR-012a/b): standing, not single-use.

    The gate is stateless with respect to prior runs: a retry after a partial
    failure and a repeat after success are the same call. Nothing consumes it.
    """
    from seshat.integrations.approval import evaluate

    _commit(repo, _row())
    assert evaluate(repo, ("duckdb",)).authorized is True
    assert evaluate(repo, ("duckdb",)).authorized is True


def test_material_scope_change_requires_a_new_approval(repo: Path) -> None:
    """T024 (FR-012c): a changed request is not the approved request."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(components='["duckdb"]'))
    assert evaluate(repo, ("duckdb",)).authorized is True
    assert evaluate(repo, ("duckdb", "snowflake")).authorized is False


def test_revoked_approval_ceases_to_authorize(repo: Path) -> None:
    """T025 (FR-012d): revocation is reported distinctly from absence."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(extra="    revoked: true\n"))
    verdict = evaluate(repo, ("duckdb",))
    assert verdict.authorized is False
    assert verdict.reason == "revoked"


def test_an_old_approval_is_not_expired_by_age(repo: Path) -> None:
    """T026 (FR-012e): the ISO date is audit metadata, not an expiry clock."""
    from seshat.integrations.approval import evaluate

    _commit(repo, _row(at="2019-01-01"))
    assert evaluate(repo, ("duckdb",)).authorized is True


# --------------------------------------------------------------------------
# T033a / T037: the gate cannot be talked into authorizing
# --------------------------------------------------------------------------


def test_evaluate_takes_no_caller_supplied_authorization(repo: Path) -> None:
    """T033a (FR-004b, FR-005): no boolean parameter can stand in for approval.

    A precondition the caller supplies is not a gate. `evaluate` must expose no
    parameter an agent could set to obtain authority -- its inputs are the repo
    root and the requested components, both derived, never asserted.
    """
    import inspect

    from seshat.integrations.approval import evaluate

    params = inspect.signature(evaluate).parameters
    assert list(params) == ["repo_root", "components"]
    for name, param in params.items():
        assert param.annotation is not bool, name
        assert param.default is inspect.Parameter.empty, name


def test_no_verdict_reason_or_next_action_leaks_a_secret(repo: Path) -> None:
    """T037 (FR-015): refusals must not echo credential-shaped content."""
    from seshat.integrations.approval import evaluate

    _commit(
        repo,
        _row(
            owner="Ahmed Shaaban (governance)",
            components='["duckdb"]',
            extra='    note: "password=hunter2 token=abc123"\n',
        ),
    )
    verdict = evaluate(repo, ("dagster",))
    blob = f"{verdict.reason} {verdict.next_action}"
    assert "hunter2" not in blob
    assert "abc123" not in blob
