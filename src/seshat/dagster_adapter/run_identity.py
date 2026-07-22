"""Validation and containment for Dagster run identifiers and evidence paths."""

from __future__ import annotations

import re
from pathlib import Path

_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def validate_run_id(value: str) -> str:
    """Return a path-safe run id or refuse path syntax and overlong values."""
    if not isinstance(value, str) or not _RUN_ID_RE.fullmatch(value):
        raise ValueError(
            "run id must be 1-128 ASCII letters, digits, dot, underscore, or dash"
        )
    return value


def contained_path(root: Path, *parts: str) -> Path:
    """Resolve a path and refuse any intermediate symlink traversal outside root."""
    base = Path(root).resolve()
    candidate = base.joinpath(*parts).resolve(strict=False)
    if candidate != base and not candidate.is_relative_to(base):
        raise ValueError("run evidence path escapes its governed root")
    return candidate
