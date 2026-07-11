"""``retail demo report`` -- render status + evidence + blockers per stage.

The demo's single most safety-critical surface: it renders status/evidence/blockers
ONLY. NEVER a numeric score, NEVER a chart / image / dashboard / PBIP artifact
(FR-013). Illustrative approvals are labeled as such -- never presented as something
the run produced (FR-016, US3).

Cold start (no snapshot yet): computes the cheap OFFLINE-only legs inline so a fresh
"report first" does not error; it never attempts a live-DB leg on its own.
"""

from __future__ import annotations

import json
from pathlib import Path

from .fixtures import work_dir
from .run import _SNAPSHOT_NAME, _load_committed_status, compute_offline_status

_STAGE_ORDER = [
    "source_ready",
    "mapping_ready",
    "silver_ready",
    "gold_ready",
    "semantic_model_ready",
    "dashboard_ready",
    "publish_ready",
]


def _load_snapshot(repo: Path) -> dict:
    """Load the last computed snapshot, or compute offline legs inline (cold start)."""
    snap_path = work_dir(repo) / _SNAPSHOT_NAME
    if snap_path.exists():
        return json.loads(snap_path.read_text(encoding="utf-8"))
    # Cold start: compute the offline-only legs inline (never a live leg).
    committed = _load_committed_status(repo)
    return compute_offline_status(committed, live_reachable=False)


def _approval_for(snapshot: dict, stage: str) -> dict | None:
    for appr in snapshot.get("approvals", []) or []:
        if appr.get("stage") == stage:
            return appr
    return None


def _is_illustrative(approval: dict) -> bool:
    note = (approval.get("note") or "").lower()
    return "illustrative" in note


def render_text(snapshot: dict) -> str:
    """Render the snapshot as a human-readable status/evidence/blockers report."""
    lines: list[str] = []
    lines.append(f"Readiness report -- {snapshot.get('table', '<demo table>')}")
    lines.append(f"mode: {'live' if snapshot.get('live_reachable') else 'offline'}")
    lines.append("")
    stages = snapshot.get("stages", {})
    for name in _STAGE_ORDER:
        block = stages.get(name)
        if block is None:
            continue
        lines.append(f"## {name}: {block['status']}")
        ev = block.get("evidence") or []
        if ev:
            lines.append("  evidence:")
            lines.extend(f"    - {e}" for e in ev)
        br = block.get("blocking_reasons") or []
        if br:
            lines.append("  blocking_reasons:")
            lines.extend(f"    - {r}" for r in br)
        appr = _approval_for(snapshot, name)
        if appr is not None:
            label = (
                " (ILLUSTRATIVE fixture -- not produced by this run)"
                if _is_illustrative(appr)
                else ""
            )
            lines.append(f"  approval: {appr.get('owner')}{label}")
        lines.append("")
    na = snapshot.get("next_action")
    if na:
        lines.append(f"next_action: {na}")
    return "\n".join(lines)


def render_json(snapshot: dict) -> str:
    """Render the snapshot as JSON (status/evidence/blockers only; no score)."""
    out = {
        "table": snapshot.get("table"),
        "mode": "live" if snapshot.get("live_reachable") else "offline",
        "stages": snapshot.get("stages", {}),
        "next_action": snapshot.get("next_action"),
        "approvals": [
            {**a, "illustrative": _is_illustrative(a)}
            for a in (snapshot.get("approvals") or [])
        ],
    }
    return json.dumps(out, indent=2)


def run_report(args) -> int:
    """Render the report (text|json). Exit 0 for any well-formed readiness state."""
    repo = Path(getattr(args, "repo", "."))
    fmt = getattr(args, "format", "text")
    try:
        snapshot = _load_snapshot(repo)
    except Exception as exc:  # malformed committed fixture -> a real usage error
        print(f"error: could not render report: {exc}")
        return 1
    print(render_json(snapshot) if fmt == "json" else render_text(snapshot))
    return 0
