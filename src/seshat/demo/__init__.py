"""Local demo harness (spec 083): the ``retail demo`` verb group.

Proves the readiness spine end-to-end on a small, invented, GENERIC sample dataset
shipped with the kit -- fully OFFLINE by default, with an optional live leg when a
local Postgres DSN is already reachable. It reuses existing primitives
(``retail check``, ``retail validate``'s ``QueryRunner``/``resolve_dsn``, the
``readiness-status.yaml`` shape); it adds no new governance rule and no new
dependency.

Pinned naming choices (decided once here, per tasks T001):
- Sample table committed name: ``demo_sample_orders``.
- Committed source CSV: ``tests/fixtures/demo/demo_sample_orders.csv``.
- Committed mapping-gate + readiness fixtures: ``mappings/demo_sample_orders/``.
- Git-ignored throwaway working directory: ``.demo-work/`` (a demo run NEVER writes
  a tracked file -- it operates on a copy here).
- Demo-scoped DB object marker (for the live leg's safety guard): the
  ``_seshat_demo`` suffix / ``demo_`` prefix on any schema/table it writes.

The four verbs (each a thin handler, dispatched from ``cli.py``):
- ``init``   -- materialize the committed fixtures into ``.demo-work/`` (idempotent).
- ``load``   -- offline: report the no-DSN skip reason (exit 0); live: write the
                demo-scoped sample into a reachable Postgres (idempotent).
- ``run``    -- recompute per-stage status from committed artifacts + ``retail
                check`` + (if loaded + reachable) ``retail validate``. No separate
                run-state engine; every value is re-derivable.
- ``report`` -- render status + evidence + blockers per stage (text | json).
                NEVER a numeric score, NEVER a chart/dashboard/PBIP artifact.

Honest offline ceiling: Source/Mapping/Silver reach ``pass`` from committed
artifacts + static ``retail check``; Gold Ready onward is ``blocked``-deferred
(its gate is the LIVE ``retail validate``). The demo shows the spine truthfully --
it never fakes a live pass and never auto-invents a dashboard.
"""

from __future__ import annotations

SAMPLE_NAME = "demo_sample_orders"
WORK_DIR = ".demo-work"
DEMO_MARKER = "_seshat_demo"
SAMPLE_CSV = "tests/fixtures/demo/demo_sample_orders.csv"
MAPPINGS_DIR = f"mappings/{SAMPLE_NAME}"


def run_demo(args) -> int:
    """Dispatch a ``retail demo <subcommand>`` invocation to its handler.

    Lazy-imports each handler so importing this package (and the stdlib-only
    ``retail check`` chain) never pulls in the demo verbs' machinery.
    """
    sub = getattr(args, "demo_command", None)
    if sub == "init":
        from .init import run_init

        return run_init(args)
    if sub == "load":
        from .load import run_load

        return run_load(args)
    if sub == "run":
        from .run import run_run

        return run_run(args)
    if sub == "report":
        from .report import run_report

        return run_report(args)
    # No subcommand: argparse should have required one; be defensive.
    print("error: a demo subcommand is required (init|load|run|report)")
    return 2
