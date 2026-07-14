"""The structured adoption ``fact`` record and PBIP component helpers.

``_Fact`` is a frozen record rather than a wide constructor function: callers
name only the fields they need, and ``as_dict`` applies the shared name and
detail redaction once, at the boundary where facts become assessment output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._safety import _FileRecord, _safe_detail, _safe_name


@dataclass(frozen=True)
class _Fact:
    id: str
    classification: str
    category: str
    subject: str
    detail: str
    artifact: str | None = None
    reason: str | None = None
    rule_id: str | None = None
    required_authority: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "classification": self.classification,
            "category": self.category,
            "subject": _safe_name(self.subject, fallback="PBIP adoption fact"),
            "detail": _safe_detail(
                self.detail, fallback="No safe detail is available."
            ),
            "artifact": self.artifact,
            "reason": _safe_detail(self.reason, fallback="No reason is available.")
            if self.reason
            else None,
            "rule_id": self.rule_id,
            "required_authority": self.required_authority,
        }


def _component(
    kind: str,
    identity: str,
    record: _FileRecord,
    support: str = "supported",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "identity": _safe_name(identity, fallback=kind),
        "artifact": record.artifact,
        "sha256": record.sha256,
        "support": support if record.readable else "unreadable",
    }


def _component_fact(component: dict[str, Any]) -> _Fact:
    support = component["support"]
    if support == "supported":
        return _Fact(
            id=f"observed:{component['kind']}:{component['artifact']}",
            classification="observed",
            category="coverage",
            subject=f"{component['kind']} {component['identity']}",
            detail="Supported PBIP structure was observed.",
            artifact=component["artifact"],
        )
    classification = (
        "unavailable_with_reason"
        if support in {"unreadable", "unsupported"}
        else "missing"
    )
    return _Fact(
        id=f"coverage:{support}:{component['kind']}:{component['artifact']}",
        classification=classification,
        category="coverage",
        subject=f"{component['kind']} {component['identity']}",
        detail="PBIP structure is outside the supported assessment coverage.",
        artifact=component["artifact"],
        reason=f"Component support is {support}.",
    )
