"""`dashboard` handler: render the readiness status to a static HTML file and
open it in the browser.

Read-only VIEW over committed readiness state. It writes ONE HTML file and
optionally opens it; it never opens a socket, DB, or network connection
(rule B1). ``webbrowser`` is imported LAZILY inside the handler.
"""

from __future__ import annotations

import argparse


def dashboard_main(args: argparse.Namespace) -> int:
    """Handler for ``dashboard``. Writes the dashboard HTML, prints its path
    (ASCII only), and (unless ``--no-open``) opens it. Returns 0 on success,
    1 if the file could not be written."""
    from seshat.dashboard.generate import generate

    repo = getattr(args, "repo", ".")
    out = getattr(args, "out", None)
    try:
        written = generate(repo, out)
    except OSError as exc:
        print(f"error: could not write dashboard: {exc}")
        return 1

    print(f"Dashboard written: {written}")
    if not getattr(args, "no_open", False):
        import webbrowser  # lazy: keep the CLI import chain socket-free (B1)

        webbrowser.open(written.resolve().as_uri())
    return 0
