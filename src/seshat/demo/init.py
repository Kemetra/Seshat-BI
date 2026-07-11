"""``retail demo init`` -- materialize the committed fixtures into .demo-work/."""

from __future__ import annotations

from pathlib import Path

from .fixtures import materialize, work_dir


def run_init(args) -> int:
    """Materialize the demo fixtures into the working directory (idempotent).

    ``--force`` refreshes an existing working dir from the committed fixtures.
    Exit 0 on success; never writes a tracked file.
    """
    repo = Path(getattr(args, "repo", "."))
    force = bool(getattr(args, "force", False))
    wd = work_dir(repo)
    already = (wd / "demo_sample_orders" / "readiness-status.yaml").exists()

    materialize(repo, force=force)

    if already and not force:
        print(f"demo already initialized at {wd} (use --force to refresh)")
    else:
        print(f"demo initialized at {wd}")
    print(
        "next: retail demo run   (offline)   or   retail demo load --dsn ... (live leg)"
    )
    return 0
