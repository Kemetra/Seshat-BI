"""Canonical finite evidence construction and atomic artifact writes."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from dataclasses import fields, is_dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path, PurePath
from types import MappingProxyType
from typing import Mapping, Sequence

from .contracts import (
    AnalysisEvidence,
    Blocker,
    Diagnostic,
    Estimate,
    Interval,
    Outcome,
    TestStatistic,
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


def decimal_text(value: Decimal | float | int) -> str:
    """Return a stable finite decimal string without redundant zeroes."""

    if isinstance(value, bool):
        raise TypeError("boolean values are not numerical evidence")
    if isinstance(value, float) and not math.isfinite(value):
        raise NonFiniteResult("non-finite numerical result")
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise NonFiniteResult("invalid numerical result") from exc
    if not number.is_finite():
        raise NonFiniteResult("non-finite numerical result")
    if number == 0:
        return "0"
    rendered = format(number.normalize(), "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(name): _freeze(item) for name, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def build_evidence(
    *,
    engine_version: str,
    invocation_id: str,
    started_at: str,
    completed_at: str,
    analysis: Mapping[str, object],
    governance: Mapping[str, object],
    input_provenance: Mapping[str, object],
    method: Mapping[str, object],
    outcome: Outcome,
    estimates: Sequence[Estimate] = (),
    effect_sizes: Sequence[Estimate] = (),
    intervals: Sequence[Interval] = (),
    tests: Sequence[TestStatistic] = (),
    diagnostics: Sequence[Diagnostic] = (),
    warnings: Sequence[str] = (),
    blockers: Sequence[Blocker] = (),
    cautions: Sequence[str] = (),
) -> AnalysisEvidence:
    """Build immutable evidence without assigning business authority."""

    return AnalysisEvidence(
        engine_version=engine_version,
        invocation_id=invocation_id,
        started_at=started_at,
        completed_at=completed_at,
        analysis=_freeze(analysis),
        governance=_freeze(governance),
        input_provenance=_freeze(input_provenance),
        method=_freeze(method),
        outcome=outcome,
        estimates=tuple(estimates),
        effect_sizes=tuple(effect_sizes),
        intervals=tuple(intervals),
        tests=tuple(tests),
        diagnostics=tuple(diagnostics),
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        cautions=tuple(cautions),
    )


def _assert_safe(value: object, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for name, item in value.items():
            key = str(name)
            if key.casefold() in _FORBIDDEN_KEYS:
                raise EvidenceRefused(f"{path}.{key}: prohibited evidence field")
            _assert_safe(item, f"{path}.{key}")
        return
    if isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _assert_safe(item, f"{path}[{index}]")
        return
    if isinstance(value, PurePath):
        if value.is_absolute():
            raise EvidenceRefused(f"{path}: absolute local path is prohibited")
        return
    if isinstance(value, str):
        if _WINDOWS_ABSOLUTE.match(value) or value.startswith(("/", "\\")):
            raise EvidenceRefused(f"{path}: absolute local path is prohibited")
        if _CONNECTION_URI.search(value):
            raise EvidenceRefused(f"{path}: connection details are prohibited")


def _jsonable(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, object] = {}
        for field in fields(value):
            name = "input" if field.name == "input_provenance" else field.name
            result[name] = _jsonable(getattr(value, field.name))
        return result
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(name): _jsonable(item) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return decimal_text(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise NonFiniteResult("non-finite numerical result")
        raise EvidenceRefused("floating evidence values must be decimal strings")
    if isinstance(value, PurePath):
        return value.as_posix()
    return value


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
