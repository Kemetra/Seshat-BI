"""`python -m scripts.adopter_sim` entry point."""

from __future__ import annotations

import sys

from scripts.adopter_sim.cli import main

if __name__ == "__main__":
    sys.exit(main())
