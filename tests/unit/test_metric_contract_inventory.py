"""Tests for the scope-aware, owner-approved metric-contract inventory."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.metric_contract_inventory import load_contract_inventory

pytestmark = pytest.mark.unit


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_approval(
    root: Path,
    scope: str,
    contract_names: tuple[str, ...] = ("TotalSales",),
    authority: str = "metric_owner",
) -> None:
    approved_names = ", ".join(contract_names)
    _write(
        root / "mappings" / scope / "readiness-status.yaml",
        "approvals:\n"
        "  - stage: semantic_model_ready\n"
        f'    owner: "Ada Lovelace ({authority})"\n'
        '    at: "2026-07-22"\n'
        f'    note: "approved metric contracts: {approved_names}"\n',
    )


def _contract_path(root: Path, scope: str, suffix: str = ".yaml") -> Path:
    return root / "mappings" / scope / "metrics" / f"TotalSales{suffix}"


def _approved(name: str = "TotalSales", gold_table: str = "gold.sales") -> str:
    return f'''\
name: "{name}"
owner: metric_owner
binds_to:
  gold_table: "{gold_table}"
definition:
  kind: base
  aggregation: sum
  filter: []
readiness:
  status: pass
  evidence: ["approved by the named metric owner on 2026-07-22"]
  blocking_reasons: []
'''


def test_approved_contract_is_indexed_by_scope_and_name(tmp_path: Path) -> None:
    _write_approval(tmp_path, "sales")
    path = _write(_contract_path(tmp_path, "sales"), _approved())

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.errors == ()
    contract = inventory.approved[("sales", "TotalSales")]
    assert contract.scope == "sales"
    assert contract.gold_table == "gold.sales"
    assert contract.binding == ("gold sales", "TotalSales")
    assert inventory.for_scope("sales") == {"TotalSales": contract}


def test_zero_contracts_is_an_empty_valid_inventory(tmp_path: Path) -> None:
    inventory = load_contract_inventory([], tmp_path)
    assert inventory.approved == {}
    assert inventory.errors == ()


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("definition: [not valid", "unreadable metric contract"),
        (_approved("OtherName"), "name must equal file stem"),
        (
            _approved().replace(
                "definition:\n  kind: base\n  aggregation: sum\n  filter: []\n", ""
            ),
            "requires definition mapping",
        ),
        (
            _approved().replace(
                "definition:\n  kind: base\n  aggregation: sum\n  filter: []\n",
                "definition: {}\n",
            ),
            "requires a checkable definition",
        ),
        (
            _approved().replace("status: pass", "status: blocked"),
            "not owner-approved pass",
        ),
        (
            _approved().replace(
                'evidence: ["approved by the named metric owner on 2026-07-22"]',
                "evidence: []",
            ),
            "requires evidence[]",
        ),
        (_approved().replace("owner: metric_owner\n", ""), "requires owner"),
        (
            _approved().replace(
                "blocking_reasons: []", "blocking_reasons: [still blocked]"
            ),
            "empty blocking_reasons[]",
        ),
        (
            _approved().replace('gold_table: "gold.sales"', 'gold_table: ""'),
            "binds_to.gold_table",
        ),
    ],
)
def test_invalid_contract_never_enters_approved_inventory(
    tmp_path: Path, body: str, expected: str
) -> None:
    _write_approval(tmp_path, "sales")
    path = _write(_contract_path(tmp_path, "sales"), body)

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.approved == {}
    assert any(expected in error for error in inventory.errors)


def test_pass_contract_without_named_scope_approval_is_rejected(tmp_path: Path) -> None:
    path = _write(_contract_path(tmp_path, "sales"), _approved())

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.approved == {}
    assert any("named-human approval" in error for error in inventory.errors)


@pytest.mark.parametrize(
    "authority", ("analyst", "governance", "data_owner", "report_owner")
)
def test_contract_approval_requires_metric_owner_authority(
    tmp_path: Path, authority: str
) -> None:
    _write_approval(tmp_path, "sales", authority=authority)
    path = _write(_contract_path(tmp_path, "sales"), _approved())

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.approved == {}
    assert any("metric_owner authority" in error for error in inventory.errors)


def test_approval_for_another_contract_does_not_approve_new_metric(
    tmp_path: Path,
) -> None:
    _write_approval(tmp_path, "sales", ("ExistingMetric",))
    path = _write(_contract_path(tmp_path, "sales"), _approved())

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.approved == {}
    assert any("note names this contract" in error for error in inventory.errors)


def test_duplicate_name_within_one_scope_is_rejected(tmp_path: Path) -> None:
    _write_approval(tmp_path, "sales")
    first = _write(_contract_path(tmp_path, "sales"), _approved())
    second = _write(_contract_path(tmp_path, "sales", ".yml"), _approved())

    inventory = load_contract_inventory([first, second], tmp_path)

    assert set(inventory.approved) == {("sales", "TotalSales")}
    assert any("within scope 'sales'" in error for error in inventory.errors)


def test_same_measure_name_in_different_scopes_is_valid(tmp_path: Path) -> None:
    paths = []
    for scope, table in (("sales", "gold.sales"), ("returns", "gold.returns")):
        _write_approval(tmp_path, scope)
        paths.append(
            _write(_contract_path(tmp_path, scope), _approved(gold_table=table))
        )

    inventory = load_contract_inventory(paths, tmp_path)

    assert inventory.errors == ()
    assert set(inventory.approved) == {
        ("sales", "TotalSales"),
        ("returns", "TotalSales"),
    }


def test_same_semantic_binding_in_different_scopes_is_rejected(
    tmp_path: Path,
) -> None:
    paths = []
    for scope in ("sales", "returns"):
        _write_approval(tmp_path, scope)
        paths.append(_write(_contract_path(tmp_path, scope), _approved()))

    inventory = load_contract_inventory(paths, tmp_path)

    assert len(inventory.approved) == 1
    assert any("duplicate semantic binding" in error for error in inventory.errors)


def test_contract_outside_the_repository_is_rejected(tmp_path: Path) -> None:
    path = _write(tmp_path.parent / "outside" / "TotalSales.yaml", _approved())

    inventory = load_contract_inventory([path], tmp_path)

    assert inventory.approved == {}
    assert any("escapes repository root" in error for error in inventory.errors)
