"""``seshat analyze`` names what failed instead of pointing at absent logs (F149).

The unexpected-failure branches used to discard the exception and tell the user
to "inspect local logs" that the command never writes. They must now report the
exception class (and, where no live connection is involved, a scrubbed message)
and must never leak a credential.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from seshat.cli.commands import analyze

pytestmark = pytest.mark.unit

_DSN = "postgresql://analyst:hunter2@db.internal.example:5432/sales"


def _blocker_text(payload: dict[str, object]) -> str:
    blockers = payload["blockers"]
    assert isinstance(blockers, list) and blockers
    return " ".join(f"{b['message']} {b['recovery']}" for b in blockers)


def test_validate_failure_names_the_exception_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(root: Path, raw: str) -> None:
        raise KeyError("policy_row")

    monkeypatch.setattr(analyze, "_load_spec", _boom)
    payload = analyze._validate_command(tmp_path, argparse.Namespace(spec="a.yaml"))

    text = _blocker_text(payload)
    assert payload["outcome"] == "failed"
    assert "KeyError" in text
    assert "policy_row" in text
    assert "Inspect local logs" not in text


def test_validate_failure_detail_is_scrubbed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(root: Path, raw: str) -> None:
        raise RuntimeError(f"could not open {_DSN}")

    monkeypatch.setattr(analyze, "_load_spec", _boom)
    payload = analyze._validate_command(tmp_path, argparse.Namespace(spec="a.yaml"))

    text = _blocker_text(payload)
    assert "RuntimeError" in text
    assert "hunter2" not in text


def test_long_message_is_scrubbed_before_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(root: Path, raw: str) -> None:
        raise RuntimeError("x" * 159 + f" could not open {_DSN}")

    monkeypatch.setattr(analyze, "_load_spec", _boom)
    payload = analyze._validate_command(tmp_path, argparse.Namespace(spec="a.yaml"))

    text = _blocker_text(payload)
    assert "hunter2" not in text
    assert "hunt" not in text


def test_execution_failure_reports_class_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(root: Path, spec: object, args: object) -> None:
        raise ConnectionError(f"server at db.internal.example refused {_DSN}")

    monkeypatch.setattr(analyze, "_local_csv_evidence", _boom)
    spec = SimpleNamespace(analysis_id="a1")
    args = argparse.Namespace(provider="local_csv", input="x.csv")
    evidence, payload = analyze._evidence(tmp_path, spec, args)

    assert evidence is None
    text = _blocker_text(payload)
    assert "ConnectionError" in text
    assert "hunter2" not in text
    assert "db.internal.example" not in text
    assert "Inspect local logs" not in text
