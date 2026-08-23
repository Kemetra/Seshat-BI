"""`seshat check --explain` wires the authored guidance into the text path only.

`run(..., explain=)` is covered in `test_runner_explain.py`; these tests cover the CLI
seam around it -- that the flag exists, reaches `run`, loads its guidance from the
committed `rule-fixes.yaml`, and REFUSES the structured formats instead of silently
doing nothing.

The refusal matters: `--format json|review|sarif` serve tools with their own output
contracts, and widening those is a contract change that needs a reader sweep. A flag
that appears to work but is ignored is the worse failure -- the caller believes it got
guidance it never got.
"""

from __future__ import annotations

import pytest

from seshat.cli.parser import _build_parser


def _parse(*argv: str):
    return _build_parser().parse_args(["check", *argv])


@pytest.mark.unit
def test_check_accepts_explain_and_defaults_it_off():
    """Fails until `--explain` is declared on the check parser."""
    assert _parse("--explain").explain is True
    assert _parse().explain is False


@pytest.mark.unit
def test_explain_is_rejected_with_a_structured_format(capsys):
    """Fails if a structured format silently ignores the flag instead of erroring."""
    from seshat.cli import _run_check

    code = _run_check(_parse("--explain", "--format", "json"))

    assert code == 2, "an unsupported combination must fail, not no-op"
    assert "--explain" in capsys.readouterr().err


@pytest.mark.unit
def test_committed_guidance_loads_and_covers_a_known_rule():
    """Fails if the CLI's guidance source stops resolving against the real repo."""
    from pathlib import Path

    from seshat.rule_fix_table import load_guidance

    guidance = load_guidance(Path("."))

    assert "D8" in guidance, "D8 is a registered rule; its guidance must be authored"
    assert guidance["D8"].get("fix"), "an authored entry must carry a fix line"
