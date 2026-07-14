"""Unit tests for the `seshat agent verify` CLI wiring and exit-code contract
(spec 129, US1/US4).

Covers: parser wiring (`agent verify --target ...`), unknown-target refusal
(exit 2), the stable exit-code contract (0 all-PASS / 1 any-BLOCKED / 2 input
defect / 3 any-UNAVAILABLE-none-BLOCKED), the UNAVAILABLE-only-is-not-0
boundary (SC-002), and the text/JSON truthfulness guarantee that no output
form ever contains a score/rank/percentage/"certified" token (SC-003).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from seshat.cli import main
from seshat.cli.parser import _build_parser

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]
_FORBIDDEN_TEXT = re.compile(
    r"\b(?:score|rank(?:ing)?|percentage|certified|pass.?rate|grade|leaderboard|winner)\b",
    re.IGNORECASE,
)


def _cleanup(*paths: Path) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def test_parser_wires_agent_verify_with_expected_defaults() -> None:
    args = _build_parser().parse_args(["agent", "verify", "--target", "claude"])
    assert args.command == "agent"
    assert args.agent_command == "verify"
    assert args.target == "claude"
    assert args.output == ".seshat-output/agent-verify/record.json"
    assert args.output_format == "text"
    assert args.publish is False


def test_parser_requires_target() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["agent", "verify"])


def test_parser_rejects_unsupported_target_choice() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["agent", "verify", "--target", "gemini"])


def test_unknown_target_refused_with_supported_list() -> None:
    # argparse's own `choices` gate refuses an unsupported --target before the
    # handler even runs; `main()` swallows argparse's SystemExit and returns
    # its code, so this is exit 2 either way (FR-001's refusal contract).
    assert main(["agent", "verify", "--target", "gemini"]) == 2


def test_agent_verify_main_itself_refuses_an_unknown_target(
    capsys: pytest.CaptureFixture,
) -> None:
    """Exercise the handler's own typed-error path directly (bypassing
    argparse's `choices`), so `resolve_target`'s refusal is proven, not just
    argparse's -- both layers must agree on exit 2 (FR-001)."""
    import argparse

    from seshat.cli.commands.agent_verify import agent_verify_main

    args = argparse.Namespace(
        agent_command="verify",
        repo=str(_REPO),
        target="gemini",
        output=".seshat-output/agent-verify/unused.json",
        output_format="text",
        publish=False,
    )
    exit_code = agent_verify_main(args)
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "claude" in captured.out and "codex" in captured.out


def test_exit_0_when_every_required_check_passes(tmp_path: Path) -> None:
    output = f".seshat-output/agent-verify/test-cli-codex-{tmp_path.name}.json"
    written = _REPO / output
    try:
        exit_code = main(
            [
                "agent",
                "verify",
                "--target",
                "codex",
                "--repo",
                str(_REPO),
                "--output",
                output,
            ]
        )
        assert exit_code == 0
        document = json.loads(written.read_text(encoding="utf-8"))
        assert all(item["verdict"] == "PASS" for item in document["results"])
    finally:
        _cleanup(written)


def test_exit_3_when_only_unavailable_and_never_reads_as_pass(tmp_path: Path) -> None:
    """claude's bundle declares no IDE surface, so a clean run against the
    real repo yields exactly one UNAVAILABLE check and zero BLOCKED -- the
    SC-002 no-false-pass boundary: this must never be exit 0."""
    output = f".seshat-output/agent-verify/test-cli-claude-{tmp_path.name}.json"
    written = _REPO / output
    try:
        exit_code = main(
            [
                "agent",
                "verify",
                "--target",
                "claude",
                "--repo",
                str(_REPO),
                "--output",
                output,
            ]
        )
        assert exit_code == 3
        assert exit_code != 0
        document = json.loads(written.read_text(encoding="utf-8"))
        verdicts = {item["verdict"] for item in document["results"]}
        assert "BLOCKED" not in verdicts
        assert "UNAVAILABLE" in verdicts
    finally:
        _cleanup(written)


def test_exit_1_when_any_required_check_is_blocked(tmp_path: Path) -> None:
    # An empty repo root has no plugin manifests, no provenance, no scenario
    # manifests -- several required checks BLOCK.
    exit_code = main(
        [
            "agent",
            "verify",
            "--target",
            "claude",
            "--repo",
            str(tmp_path),
            "--output",
            ".seshat-output/agent-verify/record.json",
        ]
    )
    assert exit_code == 1


def test_exit_2_on_uncontained_output_path(tmp_path: Path) -> None:
    exit_code = main(
        [
            "agent",
            "verify",
            "--target",
            "claude",
            "--repo",
            str(tmp_path),
            "--output",
            "outside/record.json",
        ]
    )
    assert exit_code == 2


def test_publish_without_disclosure_findings_confirms_locally(tmp_path: Path) -> None:
    output = f".seshat-output/agent-verify/test-cli-publish-{tmp_path.name}.json"
    written = _REPO / output
    try:
        exit_code = main(
            [
                "agent",
                "verify",
                "--target",
                "codex",
                "--repo",
                str(_REPO),
                "--output",
                output,
                "--publish",
            ]
        )
        assert exit_code == 0
    finally:
        _cleanup(written)


# --- SC-003 truthfulness: no score/rank/percentage/"certified" token ever --


def test_text_summary_contains_no_forbidden_token_for_all_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    output = f".seshat-output/agent-verify/test-cli-text-pass-{tmp_path.name}.json"
    written = _REPO / output
    try:
        main(
            [
                "agent",
                "verify",
                "--target",
                "codex",
                "--repo",
                str(_REPO),
                "--output",
                output,
            ]
        )
        captured = capsys.readouterr()
        assert not _FORBIDDEN_TEXT.search(captured.out)
    finally:
        _cleanup(written)


def test_text_summary_contains_no_forbidden_token_for_mixed_verdicts(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    output = f".seshat-output/agent-verify/test-cli-text-mixed-{tmp_path.name}.json"
    written = _REPO / output
    try:
        main(
            [
                "agent",
                "verify",
                "--target",
                "claude",
                "--repo",
                str(_REPO),
                "--output",
                output,
            ]
        )
        captured = capsys.readouterr()
        assert not _FORBIDDEN_TEXT.search(captured.out)
    finally:
        _cleanup(written)


def test_json_output_contains_no_forbidden_token(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    output = f".seshat-output/agent-verify/test-cli-json-{tmp_path.name}.json"
    written = _REPO / output
    try:
        main(
            [
                "agent",
                "verify",
                "--target",
                "codex",
                "--repo",
                str(_REPO),
                "--output",
                output,
                "--format",
                "json",
            ]
        )
        captured = capsys.readouterr()
        rendered = captured.out.split("written:", 1)[0]
        assert not _FORBIDDEN_TEXT.search(rendered)
    finally:
        _cleanup(written)
