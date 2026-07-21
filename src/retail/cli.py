"""Deprecated ``python -m retail.cli`` compatibility entry point."""

from seshat.cli import main

if __name__ == "__main__":
    # Pass the brand explicitly: argv[0] here is ``cli`` (this file), not the
    # command name, so preserve the deprecated ``retail`` identity for the output
    # prefixes rather than letting it normalize to ``seshat`` (PR #403 review).
    raise SystemExit(main(prog="retail"))
