"""Portfolio Watch baseline snapshot + change classifier (spec 131, US2).

Split out of ``portfolio_watch.py`` (which stayed a COMPOSITION over these
seams) purely to keep that module's line count down -- this is genuinely a
separable concern: reading/writing the local ``.seshat/watch/snapshot.json``
baseline artifact and diffing the current magnitude-free Condition Key set
against it. Nothing here reads a shipped surface's own output; it only knows
about ``ConditionChange``/the closed change-label set and the JSON snapshot
shape (SNAP-1..SNAP-3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SNAPSHOT_SCHEMA_VERSION = "1.0"

# The closed change-label set (data-model.md entity 5). No label is invented
# ad hoc anywhere else in this module.
LABEL_NEW = "new"
LABEL_RESOLVED = "resolved"
LABEL_UNCHANGED = "unchanged"
LABEL_NO_BASELINE = "current_condition_no_baseline"

CHANGE_LABELS: frozenset[str] = frozenset(
    {LABEL_NEW, LABEL_RESOLVED, LABEL_UNCHANGED, LABEL_NO_BASELINE}
)

_SNAPSHOT_FILENAME = "snapshot.json"


@dataclass(frozen=True)
class ConditionChange:
    """The per-condition new/resolved/unchanged/no-baseline label."""

    key: tuple[str, str, str, str]
    label: str

    def __post_init__(self) -> None:
        if self.label not in CHANGE_LABELS:
            raise ValueError(f"invalid change label: {self.label!r}")


def condition_keys_from_summary(
    summary: dict[str, Any],
) -> frozenset[tuple[str, str, str, str]]:
    """Re-derive the magnitude-free Condition Key set from an already-built
    summary dict (e.g. one produced by
    :func:`portfolio_watch.build_portfolio_watch_summary`). A magnitude wiggle
    in ``measured`` never changes a key (research D3)."""
    keys: set[tuple[str, str, str, str]] = set()
    for scope in summary.get("scopes", []):
        scope_id = scope["scope_id"]
        for dim in scope.get("dimensions", []):
            for item in dim.get("items", []):
                keys.add(
                    (scope_id, dim["dimension"], item["class"], item["subject_locator"])
                )
    return frozenset(keys)


def _snapshot_path(root: Path) -> Path:
    return root / ".seshat" / "watch" / _SNAPSHOT_FILENAME


def _read_snapshot_document(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        return None
    return data


def _valid_condition_key(entry: object) -> bool:
    return (
        isinstance(entry, list)
        and len(entry) == 4
        and all(isinstance(x, str) for x in entry)
    )


def _condition_keys_from_snapshot(
    conditions: list[Any],
) -> frozenset[tuple[str, str, str, str]] | None:
    if not all(_valid_condition_key(entry) for entry in conditions):
        return None
    return frozenset(tuple(entry) for entry in conditions)


def read_prior_snapshot(repo_root: Path | str = ".") -> dict[str, Any] | None:
    """Read the prior-run snapshot. Returns ``None`` (no usable baseline) on
    any absence/read/parse/shape failure -- fail-closed, never a fabricated
    diff (FR-009, SNAP-3)."""
    root = Path(repo_root).resolve()
    path = _snapshot_path(root)
    if not path.is_file():
        return None
    data = _read_snapshot_document(path)
    if data is None:
        return None

    conditions = data.get("conditions")
    scope_set = data.get("scope_set")
    if not isinstance(conditions, list) or not isinstance(scope_set, list):
        return None
    if not all(isinstance(s, str) for s in scope_set):
        return None

    keys = _condition_keys_from_snapshot(conditions)
    if keys is None:
        return None

    return {
        "conditions": keys,
        "scopes": frozenset(scope_set),
        "captured_at_revision": data.get("captured_at_revision"),
    }


def write_snapshot(
    repo_root: Path | str,
    condition_keys: frozenset[tuple[str, str, str, str]],
    scope_ids: frozenset[str],
    revision: str | None,
) -> Path:
    """Write the fresh local baseline snapshot (SNAP-1: local artifact only;
    the only write beyond the summary itself, SC-008)."""
    root = Path(repo_root).resolve()
    path = _snapshot_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "captured_at_revision": revision,
        "conditions": sorted(list(key) for key in condition_keys),
        "scope_set": sorted(scope_ids),
    }
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _no_baseline_changes(
    current_keys: frozenset[tuple[str, str, str, str]],
) -> tuple[list[ConditionChange], list[dict[str, str]]]:
    conditions = [
        ConditionChange(key=key, label=LABEL_NO_BASELINE)
        for key in sorted(current_keys)
    ]
    return conditions, []


def _scope_level_changes(
    added_scopes: set[str], removed_scopes: set[str]
) -> list[dict[str, str]]:
    return [{"scope_id": s, "change": "scope_added"} for s in sorted(added_scopes)] + [
        {"scope_id": s, "change": "scope_removed"} for s in sorted(removed_scopes)
    ]


def _condition_level_changes(
    current_keys: frozenset[tuple[str, str, str, str]],
    prior_keys: frozenset[tuple[str, str, str, str]],
    added_scopes: set[str],
    removed_scopes: set[str],
) -> list[ConditionChange]:
    filtered_current = {k for k in current_keys if k[0] not in added_scopes}
    filtered_prior = {k for k in prior_keys if k[0] not in removed_scopes}

    new = sorted(filtered_current - filtered_prior)
    resolved = sorted(filtered_prior - filtered_current)
    unchanged = sorted(filtered_current & filtered_prior)

    return (
        [ConditionChange(key=k, label=LABEL_NEW) for k in new]
        + [ConditionChange(key=k, label=LABEL_RESOLVED) for k in resolved]
        + [ConditionChange(key=k, label=LABEL_UNCHANGED) for k in unchanged]
    )


def classify_changes(
    current_keys: frozenset[tuple[str, str, str, str]],
    current_scopes: frozenset[str],
    prior: dict[str, Any] | None,
) -> tuple[list[ConditionChange], list[dict[str, str]]]:
    """Pure, deterministic sorted set-diff (FR-008, FR-012, SC-006).

    ``prior`` absent/unreadable -> every current condition is
    ``current_condition_no_baseline`` (FR-009). A scope added/removed between
    runs is reported as a scope-level change; its conditions are EXCLUDED from
    the condition-level diff so they are never misattributed as new/resolved
    conditions inside a missing scope (FR-011).
    """
    if prior is None:
        return _no_baseline_changes(current_keys)

    prior_keys = prior["conditions"]
    prior_scopes = prior["scopes"]
    added_scopes = current_scopes - prior_scopes
    removed_scopes = prior_scopes - current_scopes

    conditions = _condition_level_changes(
        current_keys, prior_keys, added_scopes, removed_scopes
    )
    scope_changes = _scope_level_changes(added_scopes, removed_scopes)
    return conditions, scope_changes


__all__ = [
    "SNAPSHOT_SCHEMA_VERSION",
    "CHANGE_LABELS",
    "LABEL_NEW",
    "LABEL_RESOLVED",
    "LABEL_UNCHANGED",
    "LABEL_NO_BASELINE",
    "ConditionChange",
    "condition_keys_from_summary",
    "read_prior_snapshot",
    "write_snapshot",
    "classify_changes",
]
