"""Spec 149 T040-T044 -- the CLI write legs, contract-tested.

The exit-code matrix is contract, not cosmetics: exits 2 (validation failed) and
3 (indeterminate) must stay distinct, or a caller cannot tell a clean failure
from a possibly-corrupted artifact.

These tests RUN the CLI as a subprocess rather than asserting on strings, because
a shape assertion goes green while the command is broken.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate

pytestmark = pytest.mark.unit

#: Absolute, resolved once: pytest's cwd is not guaranteed to be the repo root.
SRC = Path(__file__).resolve().parents[2] / "src"


TARGET = "sales_model"
OPERATION = "update_measure"
TARGET_PATH = f"models/{TARGET}.tmdl"
OWNER = "Ahmed Shaaban (data_owner)"

READINESS = (
    "stages:\n"
    "  semantic_model_ready:\n    status: pass\n"
    "  publish_ready:\n    status: not_started\n"
    "approvals:\n"
    "  - stage: publish_ready\n"
    f"    owner: {OWNER!r}\n"
    "    at: '2026-08-18'\n"
    f"    note: 'approved for {TARGET}: {OPERATION}'\n"
)
ALLOWLIST = (
    f"targets:\n  - target_id: {TARGET}\n"
    f"    path: {TARGET_PATH}\n"
    f"    operations:\n      - {OPERATION}\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _write(repo: Path, relpath: str, text: str) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def ready_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    _write(tmp_path, f"mappings/{TARGET}/readiness-status.yaml", READINESS)
    _write(tmp_path, gate.TARGET_ALLOWLIST_RELPATH, ALLOWLIST)
    _write(tmp_path, TARGET_PATH, "// original\n")
    _write(tmp_path, "README.md", "fixture\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")
    return tmp_path


def _run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Actually RUN the CLI. A string-shape assertion proves nothing (T044)."""
    return subprocess.run(
        [sys.executable, "-m", "seshat.cli", "pbi-mcp", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )


# --------------------------------------------------------------------------
# T040 -- the legs exist and are reachable
# --------------------------------------------------------------------------


def test_plan_write_leg_is_registered() -> None:
    from seshat.cli import _build_parser

    parser = _build_parser("seshat")
    parsed = parser.parse_args(
        ["pbi-mcp", "plan-write", "--target", TARGET, "--operation", OPERATION]
    )
    assert parsed.pbi_mcp_cmd == "plan-write"


def test_apply_leg_is_registered() -> None:
    from seshat.cli import _build_parser

    parser = _build_parser("seshat")
    parsed = parser.parse_args(
        ["pbi-mcp", "apply", "--target", TARGET, "--operation", OPERATION]
    )
    assert parsed.pbi_mcp_cmd == "apply"


# --------------------------------------------------------------------------
# T043a -- argument PARITY between the two legs
# --------------------------------------------------------------------------


def _choice_maps(holder: object) -> Iterator[dict[str, object]]:
    """Every ``choices`` dict directly on ``holder``'s argparse actions."""
    for action in getattr(holder, "_actions", []):
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            yield choices


def _subparser_choices(parser: object) -> dict[str, object]:
    """The subcommand map under the ``pbi-mcp`` group, or an empty map."""
    for choices in _choice_maps(parser):
        if "pbi-mcp" not in choices:
            continue
        for sub_choices in _choice_maps(choices["pbi-mcp"]):
            return sub_choices
    return {}


def _accepted_options(leg: str) -> set[str]:
    """Every option string the named write leg actually accepts."""
    from seshat.cli import _build_parser

    legs = _subparser_choices(_build_parser("seshat"))
    if leg not in legs:
        raise AssertionError(f"leg {leg!r} not found")
    return {
        option
        for entry in legs[leg]._actions  # type: ignore[attr-defined]
        for option in entry.option_strings
    }


def test_plan_write_and_apply_take_the_same_precondition_inputs() -> None:
    """Without parity the recommended dry run is unusable as a preflight.

    ``plan-write`` would report a backed-up dirty tree as blocked while ``apply``
    accepted it (Codex review, PR #656).
    """
    assert _accepted_options("plan-write") == _accepted_options("apply")


@pytest.mark.parametrize("leg", ["plan-write", "apply"])
@pytest.mark.parametrize(
    "option", ["--target", "--operation", "--backup-ref", "--json"]
)
def test_both_legs_accept_every_precondition_option(leg: str, option: str) -> None:
    assert option in _accepted_options(leg)


# --------------------------------------------------------------------------
# T041 -- no escape-hatch flag
# --------------------------------------------------------------------------


@pytest.mark.parametrize("leg", ["plan-write", "apply"])
def test_no_escape_hatch_flag_registered(leg: str) -> None:
    """Pins the parser's ACTUAL accepted arguments, not a constant's absence.

    ``--allow`` is included: a caller-supplied allowlist on a WRITE leg would
    mean the requester supplies their own permission.
    """
    options = _accepted_options(leg)
    for forbidden in (
        "--force",
        "--yes",
        "-y",
        "--skip-gate",
        "--skip-validation",
        "--skipconfirmation",
        "--no-verify",
        "--allow",
        "--backup-declared",
    ):
        assert forbidden not in options, f"{leg} must not accept {forbidden}"


@pytest.mark.parametrize("leg", ["plan-write", "apply"])
def test_target_and_operation_are_both_required(leg: str) -> None:
    """Neither may default: a write with no named operation resolves to nothing."""
    from seshat.cli import _build_parser

    parser = _build_parser("seshat")
    with pytest.raises(SystemExit):
        parser.parse_args(["pbi-mcp", leg, "--target", TARGET])
    with pytest.raises(SystemExit):
        parser.parse_args(["pbi-mcp", leg, "--operation", OPERATION])


# --------------------------------------------------------------------------
# T044 -- RUN the commands; T042 -- a refusal changes nothing
# --------------------------------------------------------------------------


def test_plan_write_runs_and_reports_a_verdict(ready_repo: Path) -> None:
    result = _run_cli(
        ready_repo, "plan-write", "--target", TARGET, "--operation", OPERATION, "--json"
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "deferred"
    assert payload["mutation_attempted"] is False


def test_plan_write_mutates_nothing(ready_repo: Path) -> None:
    before = (ready_repo / TARGET_PATH).read_text(encoding="utf-8")
    _run_cli(ready_repo, "plan-write", "--target", TARGET, "--operation", OPERATION)
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == before


def test_refusal_exits_one_and_leaves_the_artifact_byte_identical(
    ready_repo: Path,
) -> None:
    before = (ready_repo / TARGET_PATH).read_text(encoding="utf-8")
    result = _run_cli(
        ready_repo, "apply", "--target", TARGET, "--operation", "not_approved", "--json"
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert (ready_repo / TARGET_PATH).read_text(encoding="utf-8") == before
    payload = json.loads(result.stdout)
    assert payload["blockers"]


def test_an_unknown_target_is_refused(ready_repo: Path) -> None:
    result = _run_cli(
        ready_repo, "apply", "--target", "no_such_model", "--operation", OPERATION
    )
    assert result.returncode == 1


def test_a_refusal_names_its_blocker_on_stderr(ready_repo: Path) -> None:
    result = _run_cli(
        ready_repo, "apply", "--target", TARGET, "--operation", "not_approved"
    )
    assert gate.BLOCKER_OPERATION_UNBOUND in result.stderr


# --------------------------------------------------------------------------
# T043 -- the lazy-import boundary holds
# --------------------------------------------------------------------------


def test_importing_the_root_cli_does_not_import_the_write_adapter() -> None:
    """The DEFINE/CHECK core must not pull in the mutation package.

    Run in a FRESH interpreter: asserting on the current process would pass or
    fail depending on which tests ran first.
    """
    probe = (
        "import sys; import seshat.cli; print('seshat.pbi_mcp_adapter' in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert result.stdout.strip() == "False", result.stdout + result.stderr


# --------------------------------------------------------------------------
# T047 -- the group help must not claim F016 is parked
# --------------------------------------------------------------------------


def test_group_help_no_longer_claims_no_mutation_path_exists() -> None:
    """A help string that misdescribes the tool's authority is a governance bug.

    It read "F016 stays parked -- no mutation path exists here", which became
    false the moment a write leg registered.
    """
    from seshat.cli import _build_parser

    parser = _build_parser("seshat")
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and "pbi-mcp" in choices:
            help_text = next(
                entry.help
                for entry in action._choices_actions
                if entry.dest == "pbi-mcp"
            )
            assert "no mutation path exists" not in help_text
            assert "stays parked" not in help_text
            return
    raise AssertionError("pbi-mcp group not found")


# --------------------------------------------------------------------------
# HIGH: the CONFIG half of the bypass guard must be live on the write path
# --------------------------------------------------------------------------


def test_a_config_carrying_the_bypass_flag_refuses_apply(ready_repo: Path) -> None:
    """FR-002 covers BOTH arrival routes, not just argv.

    ``orchestrate.apply_write`` accepted ``config_state`` but the CLI never
    supplied it, so a machine-local ``.mcp.json`` carrying ``--skipconfirmation``
    was undetected on a write -- while the same verdict was already computed for
    the read-only legs. The branch was TESTED and unreachable in production: the
    injected-seam-needs-a-populated-registry defect.

    Run as a subprocess, so this exercises the real handler wiring rather than a
    library call.
    """
    _write(
        ready_repo,
        ".mcp.json",
        json.dumps(
            {
                "mcpServers": {
                    "powerbi": {
                        "command": "npx",
                        "args": [
                            "@microsoft/powerbi-modeling-mcp",
                            "--skipconfirmation",
                        ],
                    }
                }
            }
        ),
    )
    result = _run_cli(ready_repo, "apply", "--target", TARGET, "--operation", OPERATION)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "skipconfirmation" in (result.stdout + result.stderr).lower()


def test_a_clean_config_does_not_block_apply(ready_repo: Path) -> None:
    """The positive control -- a read-only config must not be refused."""
    _write(
        ready_repo,
        ".mcp.json",
        json.dumps(
            {
                "mcpServers": {
                    "powerbi": {
                        "command": "npx",
                        "args": ["@microsoft/powerbi-modeling-mcp", "--readonly"],
                    }
                }
            }
        ),
    )
    _git(ready_repo, "add", "-A")
    _git(ready_repo, "commit", "-q", "-m", "config", "--no-gpg-sign")
    result = _run_cli(
        ready_repo, "plan-write", "--target", TARGET, "--operation", OPERATION, "--json"
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_plan_write_twice_still_sees_a_clean_tree(ready_repo: Path) -> None:
    """The evidence artifact must not dirty the tree it later reports as clean.

    Otherwise plan-write -> apply leaves the second invocation seeing a dirty
    tree, pushing the operator toward --backup-ref on a self-inflicted dirty
    state. Requires the evidence path to be gitignored.
    """
    first = _run_cli(
        ready_repo, "plan-write", "--target", TARGET, "--operation", OPERATION, "--json"
    )
    assert first.returncode == 0, first.stderr
    second = _run_cli(
        ready_repo, "plan-write", "--target", TARGET, "--operation", OPERATION, "--json"
    )
    assert second.returncode == 0, second.stdout + second.stderr
    payload = json.loads(second.stdout)
    assert payload["blockers"] == []


def test_neither_output_form_emits_an_absolute_evidence_path(tmp_path: Path) -> None:
    """The CLI guarantee is "no user path in stdout/stderr" (cli-contract.md:155).

    `report.evidence_path` is absolute whenever `--repo` is, so emitting
    `as_posix()` leaked `C:/Users/<name>/project/...` into both the JSON `evidence`
    field and the human `evidence` line -- bypassing the output scanner. The
    artifact lives at a FIXED repo-relative path, so that is what callers need.

    Codex review, PR #659.
    """
    from seshat.cli.commands import pbi_mcp as command
    from seshat.pbi_mcp_adapter import evidence, orchestrate

    absolute = tmp_path / evidence.ARTIFACT_RELPATH
    report = orchestrate.WriteReport(
        exit_code=0,
        outcome="materialized",
        blockers=(),
        rollback_guidance=(),
        evidence_path=absolute,
        mutation_attempted=True,
    )

    payload = command._write_leg_payload(report)
    emitted = str(payload["evidence"])
    assert emitted == evidence.ARTIFACT_RELPATH, (
        f"JSON leaked an absolute evidence path: {emitted!r}"
    )
    assert tmp_path.as_posix() not in emitted
    assert not Path(emitted).is_absolute()
