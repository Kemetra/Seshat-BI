"""Tests for the owner-approved metric-contract inventory."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.metric_contract_inventory import load_contract_inventory

pytestmark = pytest.mark.unit


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _approved(name: str = "TotalSales") -> str:
    return f'''\
name: "{name}"
definition:
  additive: true
  numerator: {{aggregation: sum, filter: []}}
  denominator: null
readiness:
  status: pass
  evidence: ["approved by Metric Owner on 2026-07-22"]
  blocking_reasons: []
'''


def test_approved_contract_is_indexed_with_definition_and_evidence(
    tmp_path: Path,
) -> None:
    path = _write(tmp_path / "metrics" / "TotalSales.yaml", _approved())

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.errors == ()
    contract = inventory.approved["TotalSales"]
    assert contract.path == path
    assert contract.definition["additive"] is True
    assert contract.evidence == ("approved by Metric Owner on 2026-07-22",)


def test_zero_contracts_is_an_empty_valid_inventory(tmp_path: Path) -> None:
    inventory = load_contract_inventory([], tmp_path)
    assert inventory.approved == {}
    assert inventory.errors == ()


@pytest.mark.parametrize(
    ("filename", "body", "expected"),
    [
        ("Broken.yaml", "definition: [not valid", "unreadable metric contract"),
        ("TotalSales.yaml", _approved("OtherName"), "name must equal file stem"),
        (
            "TotalSales.yaml",
            "name: TotalSales\nreadiness: {status: pass, evidence: [ok]}\n",
            "requires definition mapping",
        ),
        (
            "TotalSales.yaml",
            "name: TotalSales\ndefinition: {}\nreadiness: {status: blocked}\n",
            "not owner-approved pass",
        ),
        (
            "TotalSales.yaml",
            "name: TotalSales\ndefinition: {}\n"
            "readiness: {status: pass, evidence: []}\n",
            "requires evidence[]",
        ),
    ],
)
def test_invalid_contract_never_enters_approved_inventory(
    tmp_path: Path, filename: str, body: str, expected: str
) -> None:
    path = _write(tmp_path / "metrics" / filename, body)

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.approved == {}
    assert any(expected in error for error in inventory.errors)


def test_duplicate_contract_names_are_rejected(tmp_path: Path) -> None:
    first = _write(tmp_path / "a" / "metrics" / "TotalSales.yaml", _approved())
    second = _write(tmp_path / "b" / "metrics" / "TotalSales.yaml", _approved())

    inventory = load_contract_inventory([first, second], tmp_path)

    assert set(inventory.approved) == {"TotalSales"}
    assert any("duplicate metric contract name" in error for error in inventory.errors)


def test_contract_outside_the_repository_is_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path.parent / "outside" / "TotalSales.yaml", _approved())

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.approved == {}
    assert any("escapes repository root" in error for error in inventory.errors)
