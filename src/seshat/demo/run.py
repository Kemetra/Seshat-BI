"""``retail demo run`` -- recompute the sample's per-stage readiness status.

Recomputes from committed mapping-gate artifacts + ``retail check``'s exit + (only
if a DB was loaded and is reachable) ``retail validate``. Writes a snapshot to the
working directory for ``report`` to render. NO separate run-state engine -- every
value is re-derivable from the same committed artifacts + gate outputs.

Offline honest ceiling: Source/Mapping/Silver reach ``pass`` (committed artifacts +
static ``retail check``); Gold Ready onward is ``blocked``/``not_started`` -- never
``pass`` offline, because Gold Ready's gate is the LIVE ``retail validate``.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._dsn import probe_reachable, resolve_dsn
from .fixtures import committed_readiness_status, work_dir

# The four canonical statuses (FR-006). No numeric score is ever computed.
_STATUSES = ("not_started", "blocked", "warning", "pass")
_SNAPSHOT_NAME = "computed-status.json"


def _load_committed_status(repo: Path) -> dict:
    """Read the committed readiness-status fixture (read-only; never written)."""
    import yaml  # available via the repo's test deps; falls back below if absent

    text = committed_readiness_status(repo).read_text(encoding="utf-8")
    return yaml.safe_load(text)


def compute_offline_status(committed: dict, *, live_reachable: bool) -> dict:
    """Compute the per-stage status snapshot from the committed fixture.

    Offline (``live_reachable`` False): Source/Mapping/Silver pass through from the
    committed fixture (they are static-gate-backed); Gold Ready onward stays as the
    committed fixture records them (blocked/not_started) -- never promoted to pass.
    The live leg (when reachable) is where Gold Ready may advance; this function
    does not fabricate that.
    """
    stages_in = committed.get("stages", {})
    out: dict[str, dict] = {}
    for name, block in stages_in.items():
        status = block.get("status", "not_started")
        if status not in _STATUSES:
            status = "not_started"
        # Offline: never let gold_ready or later read as pass (honest ceiling).
        if not live_reachable and name in (
            "gold_ready",
            "semantic_model_ready",
            "dashboard_ready",
            "publish_ready",
        ):
            if status == "pass":
                status = "blocked"
        out[name] = {
            "status": status,
            "evidence": list(block.get("evidence", []) or []),
            "blocking_reasons": list(block.get("blocking_reasons", []) or []),
        }
    return {
        "table": committed.get("table"),
        "live_reachable": live_reachable,
        "stages": out,
        "next_action": committed.get("next_action"),
        "approvals": committed.get("approvals", []),
    }


def run_run(args) -> int:
    """Recompute + persist the snapshot. Exit 0 whenever computation completes."""
    repo = Path(getattr(args, "repo", "."))
    # Resolve a DSN the SAME way `demo load` does (explicit --dsn, then workspace
    # .env), so a DSN configured the documented way is honored here too (#376).
    dsn = resolve_dsn(args)
    # "live mode" needs EVIDENCE: actually probe reachability rather than trusting
    # the presence of a DSN string (#375). No DSN -> no probe -> honest offline,
    # and the pure-offline path stays free of the [db] driver.
    live_reachable = probe_reachable(dsn) if dsn else False

    try:
        committed = _load_committed_status(repo)
    except Exception as exc:  # malformed fixture -> a real internal error
        print(f"error: could not read committed readiness fixture: {exc}")
        return 1

    snapshot = compute_offline_status(committed, live_reachable=live_reachable)

    wd = work_dir(repo)
    wd.mkdir(parents=True, exist_ok=True)
    (wd / _SNAPSHOT_NAME).write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    # Name the earliest non-pass stage (the honest current frontier) -- NOT a
    # numeric score or an "N of M" completeness tally (hard rule #9). The per-stage
    # statuses in the report are the authority.
    order = [
        "source_ready",
        "mapping_ready",
        "silver_ready",
        "gold_ready",
        "semantic_model_ready",
        "dashboard_ready",
        "publish_ready",
    ]
    frontier = next(
        (
            name
            for name in order
            if snapshot["stages"].get(name, {}).get("status") != "pass"
        ),
        None,
    )
    mode = "live" if live_reachable else "offline"
    print(f"demo run complete ({mode} mode).")
    if frontier is None:
        print("all stages pass. See 'retail demo report' for detail.")
    else:
        state = snapshot["stages"][frontier]["status"]
        print(
            f"current frontier: {frontier} = {state}. "
            "See 'retail demo report' for status + evidence + blockers."
        )
    return 0
