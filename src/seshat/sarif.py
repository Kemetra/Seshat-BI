"""Deterministic SARIF 2.1.0 projection of Seshat findings."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any

from .core import Finding, Severity

_LOCATION = re.compile(r"^(?P<path>.+?)(?::(?P<line>\d+))?(?::(?P<column>\d+))?$")
_LEVELS = {Severity.ERROR: "error", Severity.WARNING: "warning", Severity.INFO: "note"}


def finding_fingerprint(finding: Finding) -> str:
    material = "\0".join(
        (finding.rule_id, finding.severity.value, finding.locator, finding.message)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _location(locator: str) -> dict[str, Any] | None:
    normalized = locator.replace("\\", "/")
    if normalized.startswith("(") or normalized.startswith("<"):
        return None
    match = _LOCATION.match(normalized)
    if not match:
        return None
    location: dict[str, Any] = {
        "physicalLocation": {
            "artifactLocation": {"uri": match.group("path")},
        }
    }
    if match.group("line"):
        region = {"startLine": int(match.group("line"))}
        if match.group("column"):
            region["startColumn"] = int(match.group("column"))
        location["physicalLocation"]["region"] = region
    return location


def sarif_document(findings: Iterable[Finding]) -> dict[str, Any]:
    ordered = sorted(
        findings,
        key=lambda finding: (
            finding.rule_id,
            finding.locator,
            finding.message,
            finding.severity.value,
        ),
    )
    rule_ids = sorted({finding.rule_id for finding in ordered})
    results: list[dict[str, Any]] = []
    for finding in ordered:
        result: dict[str, Any] = {
            "ruleId": finding.rule_id,
            "level": _LEVELS[finding.severity],
            "message": {"text": finding.message},
            "partialFingerprints": {"seshatFinding/v1": finding_fingerprint(finding)},
        }
        location = _location(finding.locator)
        if location:
            result["locations"] = [location]
        results.append(result)
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Seshat BI",
                        "informationUri": "https://github.com/ahmed-shaaban-94/Seshat_BI",
                        "rules": [
                            {"id": rule_id, "shortDescription": {"text": rule_id}}
                            for rule_id in rule_ids
                        ],
                    }
                },
                "results": results,
            }
        ],
    }
