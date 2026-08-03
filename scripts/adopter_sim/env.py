"""Construct the client agent's environment as an allow-list.

A subtractive scrub is not enough: whatever `.env` exports (DSN, DATABASE_URL,
PG*) would otherwise reach the run, connecting a sandbox advertised as blind to
a real database AND turning step 4's working hard stop into a false regression.
So the environment is built up from nothing.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from scripts.adopter_sim.model import AdopterSimError

# Keys a client machine legitimately has. Nothing else is inherited or added.
ALLOWED_KEYS = frozenset(
    {
        "PATH",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
        "LANG",
        "CLAUDE_CONFIG_DIR",
    }
)

# Substrings that mark a key as carrying credentials or a data-source handle.
CREDENTIAL_PATTERNS = (
    "DSN",
    "DATABASE",
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "APIKEY",
    "API_KEY",
    "CREDENTIAL",
    "CONNECTIONSTRING",
    "CONNECTION_STRING",
    "PGHOST",
    "PGUSER",
    "PGPASS",
    "PGDATABASE",
    "SESHAT_",
)

# Carried through only because the OS genuinely needs them: Windows shells break
# without SYSTEMROOT/COMSPEC/PATHEXT.
_OS_REQUIRED = ("SYSTEMROOT", "COMSPEC", "PATHEXT", "LANG")


def build_client_env(
    *,
    workspace: Path,
    venv_bin: Path,
    config_dir: Path,
    parent: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a fresh environment holding only what a client machine has."""
    source = dict(parent if parent is not None else os.environ)
    env: dict[str, str] = {}

    for key in _OS_REQUIRED:
        value = source.get(key)
        if value:
            env[key] = value

    workspace_str = str(workspace)
    env["HOME"] = workspace_str
    env["USERPROFILE"] = workspace_str
    env["TEMP"] = str(workspace / ".tmp")
    env["TMP"] = env["TEMP"]
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)

    separator = ";" if os.name == "nt" else ":"
    minimal = [
        part
        for part in source.get("PATH", "").split(separator)
        if part and "site-packages" not in part
    ]
    env["PATH"] = separator.join([str(venv_bin), *minimal])
    return env


def assert_no_credentials(env: Mapping[str, str], repo_root: Path) -> None:
    """Blindness assertion 6: no stray keys, no credentials, no REPO_ROOT."""
    stray = sorted(key for key in env if key not in ALLOWED_KEYS)
    if stray:
        raise AdopterSimError(
            f"client environment carries keys outside the allow-list: {stray}"
        )
    offenders = sorted(
        key
        for key in env
        if any(pattern in key.upper() for pattern in CREDENTIAL_PATTERNS)
    )
    if offenders:
        raise AdopterSimError(
            f"client environment carries credential/data-source keys: {offenders}"
        )
    root = str(repo_root)
    leaking = sorted(key for key, value in env.items() if root and root in value)
    if leaking:
        raise AdopterSimError(
            f"client environment leaks REPO_ROOT in values for: {leaking}"
        )
    return None
