"""Small dependency-free digest helpers shared by evidence writer and renderer."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of the exact bytes stored at ``path``."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
