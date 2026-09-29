"""Validated inventory of owner-approved metric contracts."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

from seshat.metric_contract_bindings import definition_binding_errors

ContractKey = tuple[str, str]
MeasureBinding = tuple[str, str]
#: Reads one repo-relative file; ``None`` means absent/unreadable/not committed.
TextReader = Callable[[str], "str | None"]

# A prose note that records a refusal must never read as an approval (audit F014).
_REFUSAL_RE = re.compile(
    r"\b(reject(ed|s)?|revoked?|withdrawn|retracted|not\s+approved|do\s+not\s+use)\b",
    re.IGNORECASE,
)


def worktree_reader(root: Path) -> TextReader:
    """Read files from the working tree (the static, CI-committed default)."""

    def read(relative: str) -> str | None:
        try:
            return (root / relative).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return None

    return read


def committed_reader(root: Path) -> TextReader:
    """Read a file only as COMMITTED (tracked, clean, HEAD content).

    Approval-bearing gates use this so an uncommitted, agent-authored approval
    row or contract edit can never authorize anything (#334)."""
    from seshat.gitstate import committed_text

    def read(relative: str) -> str | None:
        text = committed_text(root, relative)
        return text.lstrip("\ufeff") if text is not None else None

    return read


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
    columns: tuple[str, ...] = ()
    comparison_gold_table: str | None = None
    comparison_columns: tuple[str, ...] = ()
    pii_sensitive: bool = False
    grain: str = ""
    unit: str | None = None
    time_additivity: str | None = None

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


def _read_mapping(
    relative: str, read: TextReader, yaml
) -> tuple[dict | None, str | None]:
    text = read(relative)
    if text is None:
        return None, f"{relative}: metric contract is unreadable or not committed"
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return None, f"{relative}: unreadable metric contract: {exc}"
    if not isinstance(raw, dict):
        return None, f"{relative}: metric contract must be a mapping"
    return raw, None


def _valid_evidence(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, str) and item.strip() for item in value)


def _named_semantic_approval(
    read: TextReader, scope: str, contract_name: object, yaml
) -> bool:
    text = read(f"mappings/{scope}/readiness-status.yaml")
    if text is None:
        return False
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError:
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
    """A semantic_model_ready approval by an eligible (metric_owner) named human
    with an ISO ``at:`` date -- the ONE shared predicate -- that binds this
    contract. Binding is the structured ``contracts: [Name]`` list when present;
    the prose note is a narrowed legacy fallback (audit F014)."""
    from seshat.rules.readiness_status import stage_approval_valid

    if not isinstance(contract_name, str):
        return False
    if not stage_approval_valid("semantic_model_ready", approval):
        return False
    assert isinstance(approval, dict)
    contracts = approval.get("contracts")
    if contracts is not None:
        return isinstance(contracts, list) and contract_name in contracts
    return _note_lists_contract(approval.get("note"), contract_name)


def _note_lists_contract(note: object, contract_name: str) -> bool:
    """Legacy binding: the note LISTS the contract as a delimited item.

    The name must stand as a list item (after ``:``, ``,``, ``;`` or ``(``, and
    before ``,``, ``;``, ``)``, ``.`` or the end), so "approved Net Sales only"
    does not approve ``Sales``; a note carrying a refusal marker binds nothing.
    Prefer the structured ``contracts:`` field for new approvals."""
    if not isinstance(note, str) or _REFUSAL_RE.search(note):
        return False
    name = re.escape(contract_name)
    pattern = rf"(?:^|[:,;(])\s*{name}\s*(?=[,;).]|$)"
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
            "metric_owner authority whose note names this contract (or whose "
            "contracts: list includes it)"
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
    binding_errors = definition_binding_errors(raw)
    if binding_errors:
        return f"{relative}: {binding_errors[0]}"
    return None


def _statistical_binding_error(raw: dict, relative: str) -> str | None:
    binding = raw.get("binds_to")
    if not isinstance(binding, dict):
        return None
    columns = binding.get("columns")
    if columns is not None and (
        not isinstance(columns, list)
        or not columns
        or not all(isinstance(item, str) and item.strip() for item in columns)
    ):
        return f"{relative}: binds_to.columns must be non-empty strings"
    pii_sensitive = binding.get("pii_sensitive")
    if pii_sensitive is not None and not isinstance(pii_sensitive, bool):
        return f"{relative}: binds_to.pii_sensitive must be boolean"
    for name in ("grain", "unit", "time_additivity"):
        value = raw.get(name)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            return f"{relative}: {name} must be a non-empty string"
    return None


def _contract_error(
    raw: dict, path: Path, relative: str, semantic_approval: bool
) -> str | None:
    errors = (
        _identity_error(raw, path, relative),
        _readiness_error(raw, relative),
        _approval_error(raw, relative, semantic_approval),
        _definition_error(raw, relative),
        _statistical_binding_error(raw, relative),
    )
    return next((error for error in errors if error is not None), None)


def _metric_contract(raw: dict, path: Path, scope: str) -> MetricContract:
    readiness = raw["readiness"]
    binding = raw["binds_to"]
    comparison = raw.get("compares_to")
    comparison_binding = comparison if isinstance(comparison, dict) else {}
    return MetricContract(
        name=raw["name"],
        scope=scope,
        gold_table=binding["gold_table"].strip(),
        path=path,
        definition=raw["definition"],
        evidence=tuple(readiness["evidence"]),
        columns=tuple(item.strip() for item in binding.get("columns", [])),
        comparison_gold_table=(
            comparison_binding["gold_table"]
            if isinstance(comparison_binding.get("gold_table"), str)
            else None
        ),
        comparison_columns=tuple(
            item.strip() for item in comparison_binding.get("columns", [])
        ),
        pii_sensitive=(
            binding.get("pii_sensitive") is True
            or comparison_binding.get("pii_sensitive") is True
        ),
        grain=raw.get("grain", "").strip(),
        unit=raw.get("unit"),
        time_additivity=raw.get("time_additivity"),
    )


def _resolve_contract(
    path: Path, resolved_root: Path, read: TextReader, yaml
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
    raw, read_error = _read_mapping(relative, read, yaml)
    if read_error is not None:
        return None, read_error
    assert raw is not None
    semantic_approval = _named_semantic_approval(read, scope, raw.get("name"), yaml)
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


def load_contract_inventory(
    paths: Iterable[Path], root: Path, *, committed: bool = False
) -> ContractInventory:
    """Load complete contracts backed by a named approval in their own scope.

    The single answer to "is this contract approved?" -- every dashboard, report,
    statistical and PBIP surface asks here (no second approval-trust path).
    ``committed=True`` reads each contract and the readiness approvals at HEAD
    and refuses anything untracked or dirty; approval-bearing gates use it."""
    import yaml

    approved: dict[ContractKey, MetricContract] = {}
    bindings: dict[MeasureBinding, MetricContract] = {}
    errors: list[str] = []
    resolved_root = Path(root).resolve()
    read = (
        committed_reader(resolved_root) if committed else worktree_reader(resolved_root)
    )
    for path in sorted(Path(item) for item in paths):
        contract, error = _resolve_contract(path, resolved_root, read, yaml)
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


def metric_contract_paths(root: Path, scope: str | None = None) -> list[Path]:
    """Contract files under ``mappings/<scope>/metrics/`` (every scope if None)."""
    pattern = f"{scope}/metrics/*.yaml" if scope else "*/metrics/*.yaml"
    return sorted((Path(root) / "mappings").glob(pattern))


def approved_contracts_for_scope(
    root: Path, scope: str, *, committed: bool = False
) -> tuple[dict[str, MetricContract], tuple[str, ...]]:
    """Approved contracts (by name) for one mapping scope, plus refusal reasons."""
    inventory = load_contract_inventory(
        metric_contract_paths(root, scope), root, committed=committed
    )
    return inventory.for_scope(scope), inventory.errors
