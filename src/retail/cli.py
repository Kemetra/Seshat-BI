"""Deprecated ``python -m retail.cli`` compatibility entry point."""

from seshat.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
