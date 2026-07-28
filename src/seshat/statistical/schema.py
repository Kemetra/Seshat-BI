"""Strict specification loading and packaged statistical schema resolution."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from seshat.ecosystem_contracts import validate_json_contract

from .contracts import AnalysisSpec, ColumnBinding, MethodSpec

_SCHEMA_NAMES = {
    "statistical-analysis-spec.schema.json",
    "statistical-analysis-evidence.schema.json",
}
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


class SpecRefused(ValueError):
    """A statistical specification failed one or more concrete checks."""

    def __init__(self, errors: tuple[str, ...]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def resolve_statistical_schema(repo_root: Path, name: str) -> Path:
    """Resolve a known schema from a development checkout or installed wheel."""

    if name not in _SCHEMA_NAMES:
        raise FileNotFoundError(f"unknown statistical schema: {name}")
    development = repo_root.resolve() / "schemas" / name
    if development.is_file():
        return development
    editable_checkout = Path(__file__).resolve().parents[3] / "schemas" / name
    if editable_checkout.is_file():
        return editable_checkout
    packaged = Path(__file__).resolve().parent / "schemas" / name
    if packaged.is_file():
        return packaged
    raise FileNotFoundError(f"statistical schema is unavailable: {name}")


def _load_yaml_mapping(path: Path) -> Mapping[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SpecRefused((f"$: cannot read analysis specification: {exc}",)) from exc
    if not isinstance(document, Mapping):
        raise SpecRefused(("$: analysis specification must be a mapping",))
    return document


def _load_schema(repo_root: Path) -> Mapping[str, Any]:
    path = resolve_statistical_schema(
        repo_root, "statistical-analysis-spec.schema.json"
    )
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecRefused((f"$: cannot read statistical schema: {exc}",)) from exc
    if not isinstance(schema, Mapping):
        raise SpecRefused(("$: statistical schema must be an object",))
    return schema


def _repo_relative_path(
    value: object,
    repo_root: Path,
    field: str,
    errors: list[str],
) -> PurePosixPath | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field}: path must be a non-empty repo-relative string")
        return None
    if value.startswith(("/", "\\")) or _WINDOWS_ABSOLUTE.match(value) or "\\" in value:
        errors.append(f"{field}: path must be repo-relative")
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        errors.append(f"{field}: path must be repo-relative without traversal")
        return None
    root = repo_root.resolve()
    resolved = (root / Path(*pure.parts)).resolve(strict=False)
    if not resolved.is_relative_to(root):
        errors.append(f"{field}: path must resolve under the repository")
        return None
    return pure


def _collect_paths(
    document: Mapping[str, Any], repo_root: Path
) -> tuple[
    PurePosixPath | None,
    tuple[PurePosixPath, ...],
    Mapping[str, PurePosixPath],
    list[str],
]:
    errors: list[str] = []
    readiness = _repo_relative_path(
        document.get("readiness_status"), repo_root, "$.readiness_status", errors
    )
    contracts: list[PurePosixPath] = []
    raw_contracts = document.get("metric_contracts", [])
    if isinstance(raw_contracts, list):
        for index, value in enumerate(raw_contracts):
            path = _repo_relative_path(
                value, repo_root, f"$.metric_contracts[{index}]", errors
            )
            if path is not None:
                contracts.append(path)
    outputs: dict[str, PurePosixPath] = {}
    raw_outputs = document.get("outputs")
    if isinstance(raw_outputs, Mapping):
        for name in ("evidence", "review"):
            path = _repo_relative_path(
                raw_outputs.get(name), repo_root, f"$.outputs.{name}", errors
            )
            if path is not None:
                outputs[name] = path
    raw_pii = document.get("pii")
    if isinstance(raw_pii, Mapping):
        approvals = raw_pii.get("approval_evidence", [])
        if isinstance(approvals, list):
            for index, value in enumerate(approvals):
                _repo_relative_path(
                    value,
                    repo_root,
                    f"$.pii.approval_evidence[{index}]",
                    errors,
                )
    return readiness, tuple(contracts), MappingProxyType(outputs), errors


def _frozen_mapping(value: Mapping[str, Any]) -> Mapping[str, object]:
    frozen: dict[str, object] = {}
    for name, item in value.items():
        if isinstance(item, Mapping):
            frozen[name] = _frozen_mapping(item)
        elif isinstance(item, list):
            frozen[name] = tuple(
                _frozen_mapping(element) if isinstance(element, Mapping) else element
                for element in item
            )
        else:
            frozen[name] = item
    return MappingProxyType(frozen)


def _column_bindings(value: Mapping[str, Any]) -> Mapping[str, ColumnBinding]:
    return MappingProxyType(
        {
            name: ColumnBinding(
                column=str(binding["column"]),
                logical_type=binding["logical_type"],
            )
            for name, binding in value.items()
            if isinstance(binding, Mapping)
        }
    )


def _normalize(
    document: Mapping[str, Any],
    readiness: PurePosixPath,
    metric_contracts: tuple[PurePosixPath, ...],
    outputs: Mapping[str, PurePosixPath],
    source_path: PurePosixPath | None,
    source_sha256: str,
) -> AnalysisSpec:
    method = document["method"]
    missing_data = document["missing_data"]
    return AnalysisSpec(
        schema_version=str(document["schema_version"]),
        analysis_id=str(document["analysis_id"]),
        revision=int(document["revision"]),
        subject=str(document["subject"]),
        question=str(document["question"]),
        cadence=str(document["cadence"]),
        owner=str(document["owner"]),
        readiness_status=readiness,
        metric_contracts=metric_contracts,
        provider=_frozen_mapping(document["provider"]),
        population=_frozen_mapping(document["population"]),
        roles=_column_bindings(document["roles"]),
        method=MethodSpec(
            method_id=str(method["id"]),
            version=str(method["version"]),
            parameters=_frozen_mapping(method["parameters"]),
        ),
        missing_policy=str(missing_data["policy"]),
        minimum_data=MappingProxyType(
            {str(name): int(value) for name, value in document["minimum_data"].items()}
        ),
        random_seed=int(document["random_seed"]),
        pii=_frozen_mapping(document["pii"]),
        outputs=outputs,
        source_path=source_path,
        source_sha256=source_sha256,
    )


def load_analysis_spec(path: Path, repo_root: Path) -> AnalysisSpec:
    """Load, validate, path-check, and normalize a governed analysis spec."""

    document = _load_yaml_mapping(path)
    schema = _load_schema(repo_root)
    errors = validate_json_contract(document, schema)
    readiness, metric_contracts, outputs, path_errors = _collect_paths(
        document, repo_root
    )
    errors.extend(path_errors)
    if errors:
        raise SpecRefused(tuple(errors))
    if readiness is None:
        raise SpecRefused(("$.readiness_status: path is required",))
    try:
        source_path = PurePosixPath(
            path.resolve().relative_to(repo_root.resolve()).as_posix()
        )
    except ValueError:
        source_path = None
    try:
        source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise SpecRefused((f"$: cannot hash analysis specification: {exc}",)) from exc
    return _normalize(
        document,
        readiness,
        metric_contracts,
        outputs,
        source_path,
        source_sha256,
    )
