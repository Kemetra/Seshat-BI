"""`retail dashboard-planner` handler for the read-only dashboard planner.

Classifies ONE caller-supplied dashboard proposal for ONE table against the
committed ``mappings/<table>/design/`` corpus and prints a categorical
new/extends/duplicate verdict. Read-only: it PRINTS only, contains no file-write
path, and always exits 0 -- it is not a gate (FR-008 / FR-009).
"""

from __future__ import annotations

import argparse
from pathlib import Path


def _parse_tuple(spec: str) -> tuple[str, str, str]:
    """Parse a ``<question>::<contract>::<dimension>`` --tuple spec.

    ``question`` and ``dimension`` are optional (a bare ``Contract`` or
    ``Contract::::dim`` is accepted); the classifier reduces AS GIVEN.
    """
    parts = spec.split("::")
    question = parts[0].strip() if len(parts) >= 3 else ""
    if len(parts) >= 3:
        contract, dimension = parts[1].strip(), parts[2].strip()
    elif len(parts) == 2:
        contract, dimension = parts[0].strip(), parts[1].strip()
    else:
        contract, dimension = parts[0].strip(), ""
    return (question, contract, dimension)


def _resolve_description(raw: str | None) -> str:
    """A ``@path`` description reads the file as text (a read, never a write)."""
    if not raw:
        return ""
    if raw.startswith("@"):
        try:
            return Path(raw[1:]).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            return ""
    return raw


def dashboard_planner_main(args: argparse.Namespace) -> int:
    from seshat.dashboard_planner import classify_proposal, render

    proposal = {
        "description": _resolve_description(getattr(args, "proposal", None)),
        "tuples": [_parse_tuple(spec) for spec in (getattr(args, "tuple", None) or [])],
    }
    verdict = classify_proposal(args.repo, args.table, proposal)
    print(render(verdict, getattr(args, "output_format", "text")), end="")
    return 0
