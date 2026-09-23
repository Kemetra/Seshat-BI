"""``seshat next --exit-code`` maps a STOP to a non-zero exit (audit F153).

Default behaviour stays exit 0 (back-compat). With the opt-in flag, a shell
conductor can halt on status alone: 0 = proceed, 3 = STOP (blocked / approval
required / a STOP-phrased action), 2 = input defect.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

_STAGES = (
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
)


def _write(tmp_path: Path, mapping_status: str, extra: str = "") -> None:
    lines = ['table: "orders"', 'current_stage: "mapping_ready"', "stages:"]
    lines.append('  source_ready: {status: "pass", evidence: ["profile"]}')
    lines.append(f"  mapping_ready: {{status: {mapping_status}{extra}}}")
    lines += [f'  {stage}: {{status: "not_started"}}' for stage in _STAGES[2:]]
    lines += ["approvals: []", 'next_action: "x"']
    path = tmp_path / "mappings" / "orders" / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run(tmp_path: Path, *extra: str) -> int:
    return main(["next", "--repo", str(tmp_path), *extra], prog="seshat")


@pytest.mark.parametrize("table_args", [(), ("--table", "orders")])
def test_default_exit_stays_zero_on_a_stop(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], table_args: tuple[str, ...]
) -> None:
    _write(tmp_path, '"blocked"', ', blocking_reasons: ["grain unproven"]')
    assert _run(tmp_path, *table_args) == 0


@pytest.mark.parametrize("table_args", [(), ("--table", "orders")])
def test_exit_code_flag_maps_blocked_to_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], table_args: tuple[str, ...]
) -> None:
    _write(tmp_path, '"blocked"', ', blocking_reasons: ["grain unproven"]')
    assert _run(tmp_path, "--exit-code", *table_args) == 3


@pytest.mark.parametrize("table_args", [(), ("--table", "orders")])
def test_exit_code_flag_maps_approval_required_to_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], table_args: tuple[str, ...]
) -> None:
    _write(tmp_path, '"pass"', ', evidence: ["map"]')
    assert _run(tmp_path, "--exit-code", *table_args) == 3


@pytest.mark.parametrize("table_args", [(), ("--table", "orders")])
def test_exit_code_flag_maps_input_defect_to_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], table_args: tuple[str, ...]
) -> None:
    _write(tmp_path, '"bogus"')
    assert _run(tmp_path, "--exit-code", *table_args) == 2


@pytest.mark.parametrize("table_args", [(), ("--table", "orders")])
def test_exit_code_flag_keeps_zero_for_a_next_action(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], table_args: tuple[str, ...]
) -> None:
    _write(tmp_path, '"not_started"')
    assert _run(tmp_path, "--exit-code", *table_args) == 0


def test_exit_code_flag_honours_a_stop_phrased_live_validation_action(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """outcome stays ``next_action`` but the action says STOP -> exit 3."""
    from tests.unit._gitfix import commit_all, make_git_repo

    repo = make_git_repo(tmp_path)
    lines = ['table: "orders"', 'current_stage: "semantic_model_ready"', "stages:"]
    lines += [f'  {s}: {{status: "pass", evidence: ["{s}"]}}' for s in _STAGES[:4]]
    lines += [f'  {s}: {{status: "not_started"}}' for s in _STAGES[4:]]
    lines += [
        "approvals:",
        '  - {stage: mapping_ready, owner: "Ada Lovelace (analyst)", at: "2026-07-01"}',
        'next_action: "x"',
    ]
    path = repo / "mappings" / "orders" / "readiness-status.yaml"
    path.parent.mkdir(parents=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    commit_all(repo, "feat: post-gold fixture")

    assert _run(repo, "--exit-code") == 3
    assert "outcome: next_action" in capsys.readouterr().out
