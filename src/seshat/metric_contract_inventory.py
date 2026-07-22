"""Validated inventory of owner-approved metric contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MetricContract:
    """One approved contract, normalized for semantic and orchestration gates."""

    name: str
    path: Path
    definition: dict
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ContractInventory:
    """Approved contracts plus concrete reasons every invalid input was refused."""

    approved: dict[str, MetricContract]
    errors: tuple[str, ...]


def load_contract_inventory(paths: Iterable[Path], root: Path) -> ContractInventory:
    """Load only complete, owner-approved metric contracts below ``root``.

    YAML stays a boundary dependency: importing this module does not require it.
    Invalid files are collected as concrete errors so consumers can fail closed
    without choosing an approval or silently skipping a contract.
    """
    import yaml

    approved: dict[str, MetricContract] = {}
    errors: list[str] = []
    seen_names: set[str] = set()
    resolved_root = Path(root).resolve()
    for path in sorted(Path(item) for item in paths):
        resolved_path = path.resolve()
        try:
            relative = resolved_path.relative_to(resolved_root).as_posix()
        except ValueError:
            errors.append(f"{path}: metric contract escapes repository root")
            continue
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            errors.append(f"{relative}: unreadable metric contract: {exc}")
            continue
        if not isinstance(raw, dict):
            errors.append(f"{relative}: metric contract must be a mapping")
            continue
        name = raw.get("name")
        readiness = raw.get("readiness")
        definition = raw.get("definition")
        if not isinstance(name, str) or name != path.stem:
            errors.append(f"{relative}: contract name must equal file stem")
            continue
        if name in seen_names:
            errors.append(f"{relative}: duplicate metric contract name {name!r}")
            continue
        seen_names.add(name)
        if not isinstance(readiness, dict) or readiness.get("status") != "pass":
            errors.append(f"{relative}: metric contract is not owner-approved pass")
            continue
        evidence = readiness.get("evidence")
        if (
            not isinstance(evidence, list)
            or not evidence
            or not all(isinstance(item, str) and item.strip() for item in evidence)
        ):
            errors.append(f"{relative}: approved contract requires evidence[]")
            continue
        if not isinstance(definition, dict):
            errors.append(f"{relative}: approved contract requires definition mapping")
            continue
        approved[name] = MetricContract(name, path, definition, tuple(evidence))
    return ContractInventory(approved, tuple(errors))
