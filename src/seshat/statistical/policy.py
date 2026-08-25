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
# Only an explicit exit status proves a live run succeeded. A bare verdict word
# also matches its own negation ("retail validate did not pass"), which would let
# failed -- or merely narrated -- validation clear the live-proof gate.
_LIVE_SUCCESS = re.compile(r"\bexit\s*0\b", re.IGNORECASE)
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


def _names_a_column(key: str) -> bool:
    return key.casefold().endswith(("column", "columns"))


def _definition_columns(value: object, key: str = "") -> set[str]:
    """Collect every column name a contract definition mentions, at any depth."""

    if isinstance(value, dict):
        return set().union(
            *(
                _definition_columns(child, str(child_key))
                for child_key, child in value.items()
            ),
            set(),
        )
    if isinstance(value, (list, tuple)):
        return set().union(*(_definition_columns(child, key) for child in value), set())
    if isinstance(value, str) and _names_a_column(key):
        return {value}
    return set()


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


def _gold_binding_blocker(contracts: tuple[MetricContract, ...]) -> list[Blocker]:
    tables = (
        table
        for contract in contracts
        for table in (contract.gold_table, contract.comparison_gold_table)
        if table is not None
    )
    outside_gold = any(not table.casefold().startswith("gold.") for table in tables)
    if not contracts or not outside_gold:
        return []
    return [
        _blocker(
            "STAT_NON_GOLD_BINDING",
            "At least one approved metric contract binds outside gold.*.",
            "Bind the metric contract to a validated Gold relation.",
        )
    ]


def _role_column_blocker(
    spec: AnalysisSpec, contracts: tuple[MetricContract, ...]
) -> list[Blocker]:
    """Every analysis role must read a column an approved contract already names."""

    approved: set[str] = set()
    for contract in contracts:
        approved.update(contract.columns)
        approved.update(_definition_columns(contract.definition))
    requested = {binding.column for binding in spec.roles.values()}
    if not contracts or requested.issubset(approved):
        return []
    missing = ", ".join(sorted(requested - approved))
    return [
        _blocker(
            "STAT_CONTRACT_NOT_APPROVED",
            f"Analysis roles use columns outside approved contracts: {missing}.",
            "Add the columns to an approved contract or revise the analysis roles.",
        )
    ]


def _pii_blocker(
    repo_root: Path, spec: AnalysisSpec, contracts: tuple[MetricContract, ...]
) -> list[Blocker]:
    sensitive = any(contract.pii_sensitive for contract in contracts)
    if not sensitive or _pii_evidence_exists(repo_root, spec):
        return []
    return [
        _blocker(
            "STAT_PII_APPROVAL_MISSING",
            "PII-sensitive statistical inputs lack cited approval evidence.",
            "Cite an existing repo-relative PII approval artifact.",
        )
    ]


def _add_contract_authority(
    approved_columns: dict[str, set[str]], contract: MetricContract
) -> None:
    primary = approved_columns.setdefault(contract.gold_table, set())
    primary.update(contract.columns)
    if contract.comparison_gold_table is None:
        primary.update(_definition_columns(contract.definition))
        return
    approved_columns.setdefault(contract.comparison_gold_table, set()).update(
        contract.comparison_columns
    )


def _grain_blocker(
    spec: AnalysisSpec, contracts: tuple[MetricContract, ...]
) -> list[Blocker]:
    declared = _normalized_grain(spec.population.get("grain"))
    approved = {
        _normalized_grain(contract.grain) for contract in contracts if contract.grain
    }
    if not approved:
        return []
    agreed = len(approved) == 1 and declared in approved
    if agreed:
        return []
    return [
        _blocker(
            "STAT_GRAIN_CONFLICT",
            "The analysis observation grain conflicts with its approved contract.",
            "Align population.grain with the named approved metric contracts.",
        )
    ]


def _contract_policy_blockers(
    repo_root: Path, spec: AnalysisSpec, contracts: tuple[MetricContract, ...]
) -> list[Blocker]:
    """Apply every contract-derived gate in its recorded reporting order."""

    return [
        *_gold_binding_blocker(contracts),
        *_role_column_blocker(spec, contracts),
        *_pii_blocker(repo_root, spec, contracts),
        *_grain_blocker(spec, contracts),
    ]


def _is_live_proof(item: object) -> bool:
    """A single evidence line proves a live run only if it names one and its exit."""

    if not isinstance(item, str):
        return False
    return bool(_LIVE_COMMAND.search(item)) and bool(_LIVE_SUCCESS.search(item))


def _has_live_proof(evidence: object) -> bool:
    if not isinstance(evidence, list):
        return False
    return any(_is_live_proof(item) for item in evidence)


def _readiness_blockers(table: dict | None) -> list[Blocker]:
    gold = _stage(table, "gold_ready")
    semantic = _stage(table, "semantic_model_ready")
    has_live_validation = _has_live_proof(gold.get("evidence", []))
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
        _add_contract_authority(approved_columns, contract)
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
        approved_tables=frozenset(approved_columns),
        approved_columns=frozen_columns,
    )
    return PolicyDecision(allowed=True, blockers=(), context=context)
