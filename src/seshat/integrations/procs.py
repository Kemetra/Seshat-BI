"""Subprocess running, tree removal and output scrubbing for integrations.

One runner serves the installer AND discovery, so the hardening cannot drift
between two copies:

* ``stdin`` is closed and a timeout is set (via :func:`seshat.gitutil.run_subprocess`)
  so a credential prompt or a stalled child fails loudly instead of hanging;
* git is invoked with the shared :data:`seshat.gitutil.GIT_HARDENING` flags, so a
  global ``core.hooksPath`` or fsmonitor does not execute during a clone or
  checkout in staging;
* ``GIT_TERMINAL_PROMPT=0`` and ``GCM_INTERACTIVE=never`` turn a credential
  challenge (a renamed or private repository) into an error.

Every string that can reach an output surface passes through :func:`scrub`.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from seshat.gitutil import GIT_HARDENING, run_subprocess

# Sized for a full clone or a dependency install, not for a status query.
INSTALL_TIMEOUT = 1800

_NON_INTERACTIVE_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}

# `scheme://token@host` -- userinfo with no password separator, which the shared
# secret patterns (they need `user:password@`) do not match.
_BARE_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s/@<>]+@")


def _argv(command: list[str]) -> list[str]:
    if command and command[0] == "git":
        return ["git", *GIT_HARDENING, *command[1:]]
    return list(command)


def run(
    command: list[str], cwd: Path, *, timeout: int = INSTALL_TIMEOUT
) -> subprocess.CompletedProcess:
    """Run a fixed argv (no shell), hardened; failures become a nonzero result."""
    try:
        return run_subprocess(
            _argv(command),
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
            env={**os.environ, **_NON_INTERACTIVE_ENV},
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            command, 124, "", f"{command[0]} timed out after {timeout}s"
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            command, 127, "", f"{command[0]} could not be started: {exc}"
        )


# The installer's historical name for the runner seam.
_run = run


def scrub(text: str) -> str:
    """Remove credentials from ``text`` before it reaches any output surface.

    Layer one is the DSN redactor; layer two is the shared secret-shape table
    (URL ``user:password@``, tenant GUIDs, credential assignments); the last
    pass removes a bare ``scheme://token@`` userinfo, which neither covers.
    """
    from seshat.pbi_mcp_adapter.evidence import redact, scrub_secret_shaped

    scrubbed, _labels = scrub_secret_shaped(redact(text))
    return _BARE_USERINFO.sub(r"\1[REDACTED]@", scrubbed)


def _detail(result: subprocess.CompletedProcess, fallback: str) -> str:
    return scrub((result.stderr or result.stdout or "").strip()) or fallback


def _make_writable_and_retry(func, path, _exc) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_tree(path: Path) -> str | None:
    """Delete ``path``; ``None`` when it is gone, else a detail naming the leftover.

    Git for Windows marks pack files read-only, which a plain
    ``rmtree(ignore_errors=True)`` silently leaves behind. Read-only entries are
    made writable and retried, and the result is VERIFIED rather than assumed.
    """
    if not path.exists():
        return None
    try:
        shutil.rmtree(path, onexc=_make_writable_and_retry)
    except OSError:
        pass
    if path.exists():
        return f"could not remove {path}; delete it by hand and retry"
    return None
