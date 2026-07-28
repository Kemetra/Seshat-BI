"""Read-only authority gates for governed statistical analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import yaml

from seshat.metric_contract_inventory import MetricContract, load_contract_inventory
from seshat.status_surface import build_status_projection

from .contracts import AnalysisSpec, Blocker

_LIVE_COMMAND = re.compile(r"\b(?:seshat|retail)\s+validate\b", re.IGNORECASE)
_LIVE_SUCCESS = re.compile(r"(?:\bexit\s*0\b|\bpass\b)", re.IGNORECASE)
_CODE_ORDER = (
    "STAT_GOLD_NOT_READY",
    "STAT_LIVE_VALIDATION_MISSING",
    "STAT_SEMANTIC_NOT_READY",
    "STAT_CONTRACT_NOT_APPROVED",
    "STAT_NON_GOLD_BINDING",
    "STAT_PII_APPROVAL_MISSING",
    "STAT_GRAIN_CONFLICT",
)


@dataclass(frozen=True, slots=True)
class PolicyContext:
    """Approved inputs that a statistical provider may use."""

    subject: str
    readiness_path: Path
    readiness_revision: str
    contracts: tuple[MetricContract, ...]
    approved_tables: frozenset[str]
    approved_columns: Mapping[str, frozenset[str]]


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """A deterministic allow/refuse decision with concrete recovery actions."""

    allowed: bool
    blockers: tuple[Blocker, ...]
    context: PolicyContext | None


def _blocker(code: str, message: str, recovery: str) -> Blocker:
    return Blocker(code=code, message=message, recovery=recovery)


def _readiness_document(path: Path) -> dict:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, yaml.YAMLError):
        return {}
    return document if isinstance(document, dict) else {}


def _stage(table: dict | None, name: str) -> dict:
    if not isinstance(table, dict):
        return {}
    stages = table.get("stages")
    if not isinstance(stages, dict):
        return {}
    stage = stages.get(name)
    return stage if isinstance(stage, dict) else {}


def _definition_columns(value: object, key: str = "") -> set[str]:
    columns: set[str] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            columns.update(_definition_columns(child, str(child_key)))
    elif isinstance(value, (list, tuple)):
        for child in value:
            columns.update(_definition_columns(child, key))
    elif isinstance(value, str) and (
        key.casefold().endswith("column") or key.casefold().endswith("columns")
    ):
        columns.add(value)
    return columns


def _normalized_grain(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _pii_evidence_exists(repo_root: Path, spec: AnalysisSpec) -> bool:
    evidence = spec.pii.get("approval_evidence")
    if not isinstance(evidence, tuple) or not evidence:
        return False
    root = repo_root.resolve()
    for item in evidence:
        if not isinstance(item, str):
            return False
        path = (root / Path(*item.split("/"))).resolve(strict=False)
        if not path.is_relative_to(root) or not path.is_file():
            return False
    return True


def _contract_authority(
    repo_root: Path, spec: AnalysisSpec
) -> tuple[tuple[MetricContract, ...], list[Blocker]]:
    paths = [repo_root / Path(*path.parts) for path in spec.metric_contracts]
    inventory = load_contract_inventory(paths, repo_root)
    contracts = tuple(
        sorted(
            inventory.for_scope(spec.subject).values(),
            key=lambda contract: contract.path.as_posix(),
        )
    )
    approved_paths = {contract.path.resolve() for contract in contracts}
    requested_paths = {path.resolve() for path in paths}
    blockers: list[Blocker] = []
    if inventory.errors or approved_paths != requested_paths:
        detail = "; ".join(inventory.errors) or (
            "every named contract must be approved in the analysis subject"
        )
        blockers.append(
            _blocker(
                "STAT_CONTRACT_NOT_APPROVED",
                f"Metric-contract authority is incomplete: {detail}",
                "Obtain named metric-owner approval for every cited contract.",
            )
        )
    return contracts, blockers


def _contract_policy_blockers(
    repo_root: Path, spec: AnalysisSpec, contracts: tuple[MetricContract, ...]
) -> list[Blocker]:
    blockers: list[Blocker] = []
    if contracts and any(
        not contract.gold_table.casefold().startswith("gold.") for contract in contracts
    ):
        blockers.append(
            _blocker(
                "STAT_NON_GOLD_BINDING",
                "At least one approved metric contract binds outside gold.*.",
                "Bind the metric contract to a validated Gold relation.",
            )
        )

    approved_role_columns: set[str] = set()
    for contract in contracts:
        approved_role_columns.update(contract.columns)
        approved_role_columns.update(_definition_columns(contract.definition))
    requested_role_columns = {binding.column for binding in spec.roles.values()}
    if contracts and not requested_role_columns.issubset(approved_role_columns):
        missing = ", ".join(sorted(requested_role_columns - approved_role_columns))
        blockers.append(
            _blocker(
                "STAT_CONTRACT_NOT_APPROVED",
                f"Analysis roles use columns outside approved contracts: {missing}.",
                "Add the columns to an approved contract or revise the analysis roles.",
            )
        )

    if any(contract.pii_sensitive for contract in contracts) and not (
        _pii_evidence_exists(repo_root, spec)
    ):
        blockers.append(
            _blocker(
                "STAT_PII_APPROVAL_MISSING",
                "PII-sensitive statistical inputs lack cited approval evidence.",
                "Cite an existing repo-relative PII approval artifact.",
            )
        )

    declared_grain = _normalized_grain(spec.population.get("grain"))
    approved_grains = {
        _normalized_grain(contract.grain) for contract in contracts if contract.grain
    }
    if approved_grains and (
        len(approved_grains) != 1 or declared_grain not in approved_grains
    ):
        blockers.append(
            _blocker(
                "STAT_GRAIN_CONFLICT",
                "The analysis observation grain conflicts with its approved contract.",
                "Align population.grain with the named approved metric contracts.",
            )
        )
    return blockers


def _readiness_blockers(table: dict | None) -> list[Blocker]:
    gold = _stage(table, "gold_ready")
    semantic = _stage(table, "semantic_model_ready")
    evidence = gold.get("evidence", [])
    has_live_validation = isinstance(evidence, list) and any(
        isinstance(item, str)
        and _LIVE_COMMAND.search(item)
        and _LIVE_SUCCESS.search(item)
        for item in evidence
    )
    blockers: list[Blocker] = []
    if gold.get("status") != "pass":
        blockers.append(
            _blocker(
                "STAT_GOLD_NOT_READY",
                "Gold readiness is not pass for this analysis subject.",
                "Complete and approve the Gold stage before statistical analysis.",
            )
        )
    if not has_live_validation:
        blockers.append(
            _blocker(
                "STAT_LIVE_VALIDATION_MISSING",
                "Gold evidence lacks a successful seshat/retail validate run.",
                "Run live validation and commit its successful evidence.",
            )
        )
    if semantic.get("status") != "pass":
        blockers.append(
            _blocker(
                "STAT_SEMANTIC_NOT_READY",
                "Semantic-model readiness is not pass for this analysis subject.",
                "Complete named-human semantic approval before statistical analysis.",
            )
        )
    return blockers


def _ordered(blockers: list[Blocker]) -> tuple[Blocker, ...]:
    first_by_code: dict[str, Blocker] = {}
    for blocker in blockers:
        first_by_code.setdefault(blocker.code, blocker)
    return tuple(first_by_code[code] for code in _CODE_ORDER if code in first_by_code)


def evaluate_policy(repo_root: Path, spec: AnalysisSpec) -> PolicyDecision:
    """Evaluate all authority gates without mutating readiness or approvals."""

    root = repo_root.resolve()
    readiness_path = (root / Path(*spec.readiness_status.parts)).resolve(strict=False)
    projection = build_status_projection(root)
    source_path = spec.readiness_status.as_posix()
    table = next(
        (
            item
            for item in projection.get("tables", [])
            if isinstance(item, dict) and item.get("source_path") == source_path
        ),
        None,
    )

    blockers = _readiness_blockers(table)
    contracts, contract_blockers = _contract_authority(root, spec)
    blockers.extend(contract_blockers)
    blockers.extend(_contract_policy_blockers(root, spec, contracts))
    ordered = _ordered(blockers)
    if ordered:
        return PolicyDecision(allowed=False, blockers=ordered, context=None)

    readiness = _readiness_document(readiness_path)
    approved_columns: dict[str, set[str]] = {}
    for contract in contracts:
        approved_columns.setdefault(contract.gold_table, set()).update(contract.columns)
        approved_columns[contract.gold_table].update(
            _definition_columns(contract.definition)
        )
    frozen_columns = MappingProxyType(
        {
            table_name: frozenset(columns)
            for table_name, columns in sorted(approved_columns.items())
        }
    )
    context = PolicyContext(
        subject=spec.subject,
        readiness_path=readiness_path,
        readiness_revision=str(readiness.get("mapping_version", "")),
        contracts=contracts,
        approved_tables=frozenset(contract.gold_table for contract in contracts),
        approved_columns=frozen_columns,
    )
    return PolicyDecision(allowed=True, blockers=(), context=context)
