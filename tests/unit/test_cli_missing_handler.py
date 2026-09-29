"""A parsed command with no dispatch row fails loud (audit finding F154).

``main`` used to return 0 for a subcommand the parser accepts but ``_DISPATCH``
does not wire, so a new gate verb registered without its row would report
success while doing nothing.
"""

from __future__ import annotations

import pytest

from seshat import cli

pytestmark = pytest.mark.unit


def test_parsed_command_without_handler_exits_non_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dispatch = {k: v for k, v in cli._DISPATCH.items() if k != "doctor"}
    monkeypatch.setattr(cli, "_DISPATCH", dispatch)

    code = cli.main(["doctor"], prog="retail")

    assert code == 2
    err = capsys.readouterr().err
    assert err.startswith("retail:")
    assert "doctor" in err
