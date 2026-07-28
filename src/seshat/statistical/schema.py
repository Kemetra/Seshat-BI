"""Strict specification loading and packaged statistical schema resolution."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
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


def _is_local_absolute(value: str) -> bool:
    if value.startswith(("/", "\\")):
        return True
    return bool(_WINDOWS_ABSOLUTE.match(value)) or "\\" in value


def _traverses(pure: PurePosixPath) -> bool:
    if pure.is_absolute():
        return True
    return ".." in pure.parts or "." in pure.parts


def _repo_relative_path(
    value: object,
    repo_root: Path,
    field: str,
    errors: list[str],
) -> PurePosixPath | None:
    """Accept only a repo-relative path that still resolves under the repository."""

    if not isinstance(value, str) or not value:
        errors.append(f"{field}: path must be a non-empty repo-relative string")
        return None
    if _is_local_absolute(value):
        errors.append(f"{field}: path must be repo-relative")
        return None
    pure = PurePosixPath(value)
    if _traverses(pure):
        errors.append(f"{field}: path must be repo-relative without traversal")
        return None
    root = repo_root.resolve()
    if not (root / Path(*pure.parts)).resolve(strict=False).is_relative_to(root):
        errors.append(f"{field}: path must resolve under the repository")
        return None
    return pure


@dataclass(frozen=True, slots=True)
class _DeclaredPaths:
    """Every repo-relative path a specification declares, plus its path errors."""

    readiness: PurePosixPath | None
    metric_contracts: tuple[PurePosixPath, ...]
    outputs: Mapping[str, PurePosixPath]
    errors: list[str]


def _listed_paths(
    document: Mapping[str, Any], repo_root: Path, field: str, errors: list[str]
) -> tuple[PurePosixPath, ...]:
    """Path-check one declared list, keeping only the entries that hold."""

    raw = document.get(field.rsplit(".", 1)[-1], [])
    if not isinstance(raw, list):
        return ()
    checked = (
        _repo_relative_path(value, repo_root, f"{field}[{index}]", errors)
        for index, value in enumerate(raw)
    )
    return tuple(path for path in checked if path is not None)


def _output_paths(
    document: Mapping[str, Any], repo_root: Path, errors: list[str]
) -> Mapping[str, PurePosixPath]:
    raw_outputs = document.get("outputs")
    if not isinstance(raw_outputs, Mapping):
        return MappingProxyType({})
    checked = {
        name: _repo_relative_path(
            raw_outputs.get(name), repo_root, f"$.outputs.{name}", errors
        )
        for name in ("evidence", "review")
    }
    return MappingProxyType(
        {name: path for name, path in checked.items() if path is not None}
    )


def _check_pii_evidence(
    document: Mapping[str, Any], repo_root: Path, errors: list[str]
) -> None:
    """Path-check the PII approval evidence, which is cited but never returned."""

    raw_pii = document.get("pii")
    if not isinstance(raw_pii, Mapping):
        return
    _listed_paths(
        {"approval_evidence": raw_pii.get("approval_evidence", [])},
        repo_root,
        "$.pii.approval_evidence",
        errors,
    )


def _collect_paths(document: Mapping[str, Any], repo_root: Path) -> _DeclaredPaths:
    errors: list[str] = []
    readiness = _repo_relative_path(
        document.get("readiness_status"), repo_root, "$.readiness_status", errors
    )
    contracts = _listed_paths(document, repo_root, "$.metric_contracts", errors)
    outputs = _output_paths(document, repo_root, errors)
    _check_pii_evidence(document, repo_root, errors)
    return _DeclaredPaths(readiness, contracts, outputs, errors)


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


@dataclass(frozen=True, slots=True)
class _Source:
    """Where the loaded specification came from, and its committed digest."""

    path: PurePosixPath | None
    sha256: str


def _normalize(
    document: Mapping[str, Any],
    paths: _DeclaredPaths,
    readiness: PurePosixPath,
    source: _Source,
) -> AnalysisSpec:
    method = document["method"]
    missing_data = document["missing_data"]
    metric_contracts = paths.metric_contracts
    outputs = paths.outputs
    source_path = source.path
    source_sha256 = source.sha256
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
    errors = validate_json_contract(document, _load_schema(repo_root))
    paths = _collect_paths(document, repo_root)
    errors.extend(paths.errors)
    if errors:
        raise SpecRefused(tuple(errors))
    if paths.readiness is None:
        raise SpecRefused(("$.readiness_status: path is required",))
    return _normalize(document, paths, paths.readiness, _source(path, repo_root))


def _source(path: Path, repo_root: Path) -> _Source:
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
        source_path = PurePosixPath(relative)
    except ValueError:
        source_path = None
    try:
        return _Source(source_path, hashlib.sha256(path.read_bytes()).hexdigest())
    except OSError as exc:
        raise SpecRefused((f"$: cannot hash analysis specification: {exc}",)) from exc
