"""Generate the static status-dashboard HTML file.

The ONLY disk-touching unit. Reads the existing read-only status projection,
renders it via the pure renderer, and writes ONE self-contained HTML file.
No socket, no network, no DB (rule B1). UTF-8 without BOM.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from seshat.dashboard.render import render_page
from seshat.status_surface import build_status_projection


def generate(
    repo_root: Path | str = ".",
    out_path: Path | str | None = None,
    generated_at: str | None = None,
) -> Path:
    """Render the dashboard for ``repo_root`` and write it to ``out_path``.

    Defaults ``out_path`` to ``<repo_root>/reports/dashboard/index.html``.
    Creates parent directories. Returns the written path. Raises ``OSError``
    if the path cannot be created/written (the caller renders a clean error).

    This is the impure boundary: it stamps ``generated_at`` (the honest render
    time) unless the caller supplies one, then injects it into the pure
    renderer. Reading the clock lives here, never in ``render_page``.
    """
    root = Path(repo_root)
    target = (
        Path(out_path)
        if out_path is not None
        else root / "reports" / "dashboard" / "index.html"
    )
    stamp = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    projection = build_status_projection(root)
    document = render_page(projection, generated_at=stamp)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding="utf-8")  # utf-8 (no BOM)
    return target
