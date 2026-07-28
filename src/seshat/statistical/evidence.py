"""Canonical finite evidence construction and atomic artifact writes."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path, PurePath
from types import MappingProxyType
from typing import Mapping

from .contracts import (
    AnalysisEvidence,
    Blocker,
    MethodResult,
    Outcome,
)

_FORBIDDEN_KEYS = {
    "connection_string",
    "credentials",
    "dsn",
    "host",
    "hostname",
    "observations",
    "password",
    "raw_rows",
    "rows",
    "secret",
    "token",
}
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_CONNECTION_URI = re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mssql|snowflake)://")


class NonFiniteResult(ValueError):
    """A numerical library returned a value JSON evidence cannot represent."""


class EvidenceRefused(ValueError):
    """Evidence would violate containment, privacy, or serialization policy."""


def _as_decimal(value: Decimal | float | int) -> Decimal:
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise NonFiniteResult("invalid numerical result") from exc


def _finite_decimal(value: Decimal | float | int) -> Decimal:
    """Convert a numerical result, refusing anything JSON cannot represent."""

    if isinstance(value, bool):
        raise TypeError("boolean values are not numerical evidence")
    if isinstance(value, float) and not math.isfinite(value):
        raise NonFiniteResult("non-finite numerical result")
    number = _as_decimal(value)
    if not number.is_finite():
        raise NonFiniteResult("non-finite numerical result")
    return number


def decimal_text(value: Decimal | float | int) -> str:
    """Return a stable finite decimal string without redundant zeroes."""

    number = _finite_decimal(value)
    if number == 0:
        return "0"
    rendered = format(number.normalize(), "f")
    if "." not in rendered:
        return rendered
    return rendered.rstrip("0").rstrip(".")


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(name): _freeze(item) for name, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class EvidenceRun:
    """When this invocation ran, and which engine ran it."""

    engine_version: str
    invocation_id: str
    started_at: str
    completed_at: str


@dataclass(frozen=True, slots=True)
class EvidenceReferences:
    """The committed artifacts and method this evidence is traced to."""

    analysis: Mapping[str, object]
    governance: Mapping[str, object]
    input_provenance: Mapping[str, object]
    method: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class EvidenceFindings:
    """What the invocation concluded: one outcome, its numbers, its blockers."""

    outcome: Outcome
    result: MethodResult = MethodResult()
    blockers: tuple[Blocker, ...] = ()


def build_evidence(
    run: EvidenceRun, references: EvidenceReferences, findings: EvidenceFindings
) -> AnalysisEvidence:
    """Build immutable evidence without assigning business authority."""

    result = findings.result
    return AnalysisEvidence(
        engine_version=run.engine_version,
        invocation_id=run.invocation_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        analysis=_freeze(references.analysis),
        governance=_freeze(references.governance),
        input_provenance=_freeze(references.input_provenance),
        method=_freeze(references.method),
        outcome=findings.outcome,
        estimates=tuple(result.estimates),
        effect_sizes=tuple(result.effect_sizes),
        intervals=tuple(result.intervals),
        tests=tuple(result.tests),
        diagnostics=tuple(result.diagnostics),
        warnings=tuple(result.warnings),
        blockers=tuple(findings.blockers),
        cautions=tuple(result.interpretation_cautions),
    )


def _assert_safe_mapping(value: Mapping[str, object], path: str) -> None:
    for name, item in value.items():
        key = str(name)
        if key.casefold() in _FORBIDDEN_KEYS:
            raise EvidenceRefused(f"{path}.{key}: prohibited evidence field")
        _assert_safe(item, f"{path}.{key}")


def _assert_safe_text(value: str, path: str) -> None:
    """Refuse a local absolute path or any connection detail in evidence."""

    if _WINDOWS_ABSOLUTE.match(value) or value.startswith(("/", "\\")):
        raise EvidenceRefused(f"{path}: absolute local path is prohibited")
    if _CONNECTION_URI.search(value):
        raise EvidenceRefused(f"{path}: connection details are prohibited")


def _assert_safe_scalar(value: object, path: str) -> None:
    if isinstance(value, PurePath) and value.is_absolute():
        raise EvidenceRefused(f"{path}: absolute local path is prohibited")
    if isinstance(value, str):
        _assert_safe_text(value, path)


def _assert_safe(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        _assert_safe_mapping(value, path)
        return
    if isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _assert_safe(item, f"{path}[{index}]")
        return
    _assert_safe_scalar(value, path)


def _jsonable_dataclass(value: object) -> dict[str, object]:
    """Project a dataclass, renaming input_provenance to its published key."""

    return {
        ("input" if field.name == "input_provenance" else field.name): _jsonable(
            getattr(value, field.name)
        )
        for field in fields(value)
    }


def _jsonable_float(value: float) -> object:
    if not math.isfinite(value):
        raise NonFiniteResult("non-finite numerical result")
    raise EvidenceRefused("floating evidence values must be decimal strings")


def _jsonable_scalar(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, float):
        return _jsonable_float(value)
    if isinstance(value, PurePath):
        return value.as_posix()
    return value


def _jsonable(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable_dataclass(value)
    if isinstance(value, Mapping):
        return {str(name): _jsonable(item) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return _jsonable_scalar(value)


def evidence_payload(evidence: AnalysisEvidence) -> dict[str, object]:
    """Project typed evidence to its canonical JSON-compatible mapping."""

    payload = _jsonable(evidence)
    if not isinstance(payload, dict):  # pragma: no cover - defensive type guard
        raise TypeError("analysis evidence must serialize to an object")
    _assert_safe(payload)
    return payload


def _contained_path(path: Path, repo_root: Path | None) -> Path:
    root = (repo_root if repo_root is not None else path.parent).resolve()
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise EvidenceRefused("output path must resolve under the repository")
    return resolved


def _atomic_write_text(path: Path, content: str, repo_root: Path | None) -> Path:
    final = _contained_path(path, repo_root)
    final.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=final.parent,
            prefix=f".{final.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, final)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    return final


def write_evidence(
    path: Path,
    evidence: AnalysisEvidence,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Atomically write canonical JSON evidence after safety checks."""

    payload = evidence_payload(evidence)
    content = (
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    )
    return _atomic_write_text(path, content, repo_root)
