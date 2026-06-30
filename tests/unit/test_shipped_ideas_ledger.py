"""Guard test for the IL1 shipped-ideas ledger (docs/roadmap/shipped-ideas.yaml).

The ledger is the structured memory seam the idea-engine Memory stage reads as
authoritative known-history. This test enforces the load-bearing parts of the field
contract (contracts/shipped-ideas.schema.md) on the COMMITTED ledger so a malformed or
under-specified entry fails the gate rather than silently corrupting the engine's
memory. It also exercises the validator on synthetic bad inputs so the rules are
proven, not just asserted against the one happy-path file.

This is a docs/data guard (pytest over a committed YAML), not a registered retail-check
rule -- the optional IL1 static rule is out of scope for feature 052.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

_LEDGER = (
    Path(__file__).resolve().parents[2] / "docs" / "roadmap" / "shipped-ideas.yaml"
)

_VALID_STATUS = {"shipped", "settled"}
_REQUIRED_KEYS = {"status", "pr_sha", "f_row"}


def _validate(data: object) -> list[str]:
    """Return a list of contract violations for a parsed ledger (empty = valid)."""
    errors: list[str] = []
    if data is None:
        return errors  # absent/empty ledger is honest "no structured history"
    if not isinstance(data, dict):
        return ["ledger top level must be a mapping of idea-id -> entry"]
    for key, entry in data.items():
        if not isinstance(entry, dict):
            errors.append(f"{key}: entry must be a mapping")
            continue
        keys = set(entry)
        if keys != _REQUIRED_KEYS:
            errors.append(f"{key}: keys must be exactly {sorted(_REQUIRED_KEYS)}")
            continue
        if entry["status"] not in _VALID_STATUS:
            errors.append(f"{key}: status must be one of {sorted(_VALID_STATUS)}")
        if not isinstance(entry["pr_sha"], str) or not entry["pr_sha"].strip():
            errors.append(f"{key}: pr_sha must be a non-empty string (evidence)")
        f_row = entry["f_row"]
        if not isinstance(f_row, str) or not f_row.strip():
            errors.append(f"{key}: f_row must be a string (an F-row label or 'none')")
    return errors


def test_committed_ledger_is_valid() -> None:
    """The shipped ledger on disk satisfies the field contract."""
    assert _LEDGER.exists(), f"{_LEDGER} must exist"
    data = yaml.safe_load(_LEDGER.read_text(encoding="utf-8"))
    errors = _validate(data)
    assert errors == [], f"ledger contract violations: {errors}"


def test_committed_ledger_has_no_domain_tokens() -> None:
    # Generic governance identifiers only -- no domain/C086 leak.
    text = _LEDGER.read_text(encoding="utf-8").lower()
    for token in ("pharmacy", "c086", "billing", "patient", "prescri"):
        assert token not in text, f"ledger must not contain domain token {token!r}"


def test_validator_rejects_bad_status() -> None:
    assert _validate({"X1": {"status": "done", "pr_sha": "PR #1", "f_row": "none"}})


def test_validator_rejects_missing_key() -> None:
    assert _validate({"X1": {"status": "shipped", "f_row": "none"}})  # no pr_sha


def test_validator_rejects_extra_key() -> None:
    assert _validate(
        {"X1": {"status": "shipped", "pr_sha": "PR #1", "f_row": "none", "extra": 1}}
    )


def test_validator_rejects_empty_evidence() -> None:
    assert _validate({"X1": {"status": "shipped", "pr_sha": "  ", "f_row": "none"}})


def test_validator_accepts_settled_and_f_row() -> None:
    ok = {
        "A1": {"status": "shipped", "pr_sha": "PR #62 abbbd73", "f_row": "none"},
        "F5": {"status": "settled", "pr_sha": "PARK rationale", "f_row": "none"},
        "X9": {"status": "shipped", "pr_sha": "PR #9", "f_row": "F062"},
    }
    assert _validate(ok) == []


def test_validator_rejects_list_toplevel() -> None:
    # A ledger that parses to a list (not a mapping) is malformed -> fail loud.
    errors = _validate([{"status": "shipped"}])
    assert errors and "mapping" in errors[0]


def test_validator_treats_absent_as_honest_empty() -> None:
    # safe_load of an empty file returns None -> no structured history, not an error.
    assert _validate(None) == []
