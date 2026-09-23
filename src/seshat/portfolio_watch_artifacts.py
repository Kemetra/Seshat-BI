"""Committed-artifact reading rules for Portfolio Watch (sibling of portfolio_watch).

Three rules, each a truthful-degradation guard:

  * ``normalize_artifact`` -- a ``drift-findings.json`` written straight from
    ``seshat drift --format json`` (the native ``drift.to_findings_dict``
    shape) is translated through the producer's own adapter
    (``drift.to_portfolio_artifact``) instead of being reported unreadable.
  * ``artifact_stale_reason`` -- an artifact is current only when it records
    the revision it was captured at AND that revision equals HEAD. A missing
    revision, or a HEAD that cannot be established, is stale -- never covered.
  * ``valid_item_entries`` -- malformed items are counted, not silently
    dropped (a dropped item would otherwise read as a resolved condition).

Stdlib-only; no I/O.
"""

from __future__ import annotations

from typing import Any

__all__ = ["artifact_stale_reason", "normalize_artifact", "valid_item_entries"]


def normalize_artifact(
    dimension: str, data: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(portfolio-shaped data, None)`` or ``(None, unreadable reason)``."""
    native = "schema_version" not in data and "findings" in data
    if dimension != "source_drift" or not native:
        return data, None
    from .drift import to_portfolio_artifact

    try:
        return to_portfolio_artifact(data), None
    except (KeyError, TypeError, AttributeError) as exc:
        return None, f"native drift document is malformed ({exc.__class__.__name__})"


def artifact_stale_reason(
    captured_at: object, source_revision: str | None
) -> str | None:
    """Why an artifact cannot be treated as current, or None when it is."""
    if source_revision is None:
        return "cannot establish the current revision (HEAD); freshness unproven"
    if not isinstance(captured_at, str) or not captured_at:
        return "no captured_at_revision recorded; freshness unproven"
    if captured_at != source_revision:
        return f"captured_at_revision={captured_at} vs current={source_revision}"
    return None


def valid_item_entries(raw: object) -> tuple[list[dict[str, Any]], int]:
    """Well-formed item entries plus the count of malformed ones."""
    if raw is None:
        return [], 0
    if not isinstance(raw, list):
        return [], 1
    valid = [
        entry
        for entry in raw
        if isinstance(entry, dict)
        and isinstance(entry.get("class"), str)
        and isinstance(entry.get("subject_locator"), str)
    ]
    return valid, len(raw) - len(valid)
