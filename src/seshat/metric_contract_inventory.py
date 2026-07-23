"""Validated inventory of owner-approved metric contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

ContractKey = tuple[str, str]
MeasureBinding = tuple[str, str]


def normalize_table_binding(value: str) -> str:
    """Normalize YAML ``schema.table`` and TMDL ``schema table`` identities."""
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


@dataclass(frozen=True)
class MetricContract:
    """One approved contract, normalized for semantic and orchestration gates."""

    name: str
    scope: str
    gold_table: str
    path: Path
    definition: dict
    evidence: tuple[str, ...]

    @property
    def binding(self) -> MeasureBinding:
        return normalize_table_binding(self.gold_table), self.name


@dataclass(frozen=True)
class ContractInventory:
    """Approved contracts plus concrete reasons every invalid input was refused."""

    approved: dict[ContractKey, MetricContract]
    errors: tuple[str, ...]

    def for_scope(self, scope: str) -> dict[str, MetricContract]:
        """Approved contracts for one governed mapping scope, keyed by measure."""
        return {
            name: contract
            for (contract_scope, name), contract in self.approved.items()
            if contract_scope == scope
        }


def _scope_from_path(relative: str) -> str | None:
    parts = PurePosixPath(relative).parts
    for index in range(len(parts) - 3):
        if parts[index] == "mappings" and parts[index + 2] == "metrics":
            return parts[index + 1]
    return None


def _read_mapping(path: Path, relative: str, yaml) -> tuple[dict | None, str | None]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, f"{relative}: unreadable metric contract: {exc}"
    if not isinstance(raw, dict):
        return None, f"{relative}: metric contract must be a mapping"
    return raw, None


def _valid_evidence(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, str) and item.strip() for item in value)


def _named_semantic_approval(
    root: Path, scope: str, contract_name: object, yaml
) -> bool:
    path = root / "mappings" / scope / "readiness-status.yaml"
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return False
    if not isinstance(document, dict):
        return False
    approvals = document.get("approvals")
    if not isinstance(approvals, list):
        return False
    return any(
        _valid_semantic_approval(approval, contract_name) for approval in approvals
    )


def _valid_semantic_approval(approval: object, contract_name: object) -> bool:
    from seshat.rules.readiness_status import _owner_authority

    if not isinstance(approval, dict):
        return False
    if approval.get("stage") != "semantic_model_ready":
        return False
    if _owner_authority(approval.get("owner")) != "metric_owner":
        return False
    if not approval.get("at") or not isinstance(contract_name, str):
        return False
    note = approval.get("note")
    if not isinstance(note, str):
        return False
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(contract_name)}(?![A-Za-z0-9_])"
    return re.search(pattern, note) is not None


def _identity_error(raw: dict, path: Path, relative: str) -> str | None:
    name = raw.get("name")
    if not isinstance(name, str) or name != path.stem:
        return f"{relative}: contract name must equal file stem"
    return None


def _readiness_error(raw: dict, relative: str) -> str | None:
    readiness = raw.get("readiness")
    if not isinstance(readiness, dict) or readiness.get("status") != "pass":
        return f"{relative}: metric contract is not owner-approved pass"
    if not _valid_evidence(readiness.get("evidence")):
        return f"{relative}: approved contract requires evidence[]"
    if readiness.get("blocking_reasons") != []:
        return f"{relative}: approved contract requires empty blocking_reasons[]"
    return None


def _approval_error(raw: dict, relative: str, approved: bool) -> str | None:
    owner = raw.get("owner")
    if not isinstance(owner, str) or not owner.strip():
        return f"{relative}: approved contract requires owner"
    if not approved:
        return (
            f"{relative}: approved contract requires named-human approval with "
            "metric_owner authority whose note names this contract"
        )
    return None


def _definition_error(raw: dict, relative: str) -> str | None:
    definition = raw.get("definition")
    if not isinstance(definition, dict):
        return f"{relative}: approved contract requires definition mapping"
    is_base = definition.get("kind") == "base"
    is_ratio = isinstance(definition.get("denominator"), dict)
    if not (is_base or is_ratio):
        return (
            f"{relative}: approved contract requires a checkable definition "
            "with kind: base or a denominator mapping"
        )
    binding = raw.get("binds_to")
    if not isinstance(binding, dict):
        return f"{relative}: approved contract requires binds_to.gold_table"
    gold_table = binding.get("gold_table")
    if not isinstance(gold_table, str) or not gold_table.strip():
        return f"{relative}: approved contract requires binds_to.gold_table"
    return None


def _contract_error(
    raw: dict, path: Path, relative: str, semantic_approval: bool
) -> str | None:
    errors = (
        _identity_error(raw, path, relative),
        _readiness_error(raw, relative),
        _approval_error(raw, relative, semantic_approval),
        _definition_error(raw, relative),
    )
    return next((error for error in errors if error is not None), None)


def _metric_contract(raw: dict, path: Path, scope: str) -> MetricContract:
    readiness = raw["readiness"]
    return MetricContract(
        name=raw["name"],
        scope=scope,
        gold_table=raw["binds_to"]["gold_table"].strip(),
        path=path,
        definition=raw["definition"],
        evidence=tuple(readiness["evidence"]),
    )


def _resolve_contract(
    path: Path, resolved_root: Path, yaml
) -> tuple[MetricContract | None, str | None]:
    """Parse one path into a validated contract, or the reason it is refused."""
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return None, f"{path}: metric contract escapes repository root"
    scope = _scope_from_path(relative)
    if scope is None:
        return None, f"{relative}: metric contract is outside mappings/<scope>/metrics"
    raw, read_error = _read_mapping(path, relative, yaml)
    if read_error is not None:
        return None, read_error
    assert raw is not None
    semantic_approval = _named_semantic_approval(
        resolved_root, scope, raw.get("name"), yaml
    )
    validation_error = _contract_error(raw, path, relative, semantic_approval)
    if validation_error is not None:
        return None, validation_error
    return _metric_contract(raw, path, scope), None


def _duplicate_error(
    contract: MetricContract,
    resolved_root: Path,
    approved: dict[ContractKey, MetricContract],
    bindings: dict[MeasureBinding, MetricContract],
) -> str | None:
    """Refuse a contract that collides with one already registered."""
    relative = contract.path.resolve().relative_to(resolved_root).as_posix()
    if (contract.scope, contract.name) in approved:
        return (
            f"{relative}: duplicate metric contract name {contract.name!r} "
            f"within scope {contract.scope!r}"
        )
    previous = bindings.get(contract.binding)
    if previous is not None:
        previous_relative = previous.path.resolve().relative_to(resolved_root)
        return (
            f"{relative}: duplicate semantic binding {contract.binding!r}; "
            f"already claimed by {previous_relative.as_posix()}"
        )
    return None


def load_contract_inventory(paths: Iterable[Path], root: Path) -> ContractInventory:
    """Load complete contracts backed by a named approval in their own scope."""
    import yaml

    approved: dict[ContractKey, MetricContract] = {}
    bindings: dict[MeasureBinding, MetricContract] = {}
    errors: list[str] = []
    resolved_root = Path(root).resolve()
    for path in sorted(Path(item) for item in paths):
        contract, error = _resolve_contract(path, resolved_root, yaml)
        if error is not None:
            errors.append(error)
            continue
        assert contract is not None
        duplicate = _duplicate_error(contract, resolved_root, approved, bindings)
        if duplicate is not None:
            errors.append(duplicate)
            continue
        approved[(contract.scope, contract.name)] = contract
        bindings[contract.binding] = contract
    return ContractInventory(approved, tuple(errors))
