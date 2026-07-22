"""The shell-free, closed-argv child-process runner (spec 134 US4, FR-008).

``seshat dagster run`` never imports dagster: it launches the orchestration
environment's interpreter with EXACTLY the argv below -- no shell, no raw
pass-through arguments, no selectors. Table scoping travels via the
``SESHAT_DAGSTER_TABLES`` environment variable (the definitions module's
closed discovery seam), never via argv.
"""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from . import ALLOWED_JOBS
from .doctor import orchestration_python
from .environment import allowed_child_environment
from .redaction import redact_and_tail
from .source_mode import DEFAULT_SOURCE_MODE, SOURCE_MODE_ENV, normalize_source_mode

_TAIL_CHARS = 4000
_RUN_TIMEOUT_SECONDS = 7200


class RunnerError(RuntimeError):
    """A preflight-shaped runner failure (missing environment, bad job)."""


@dataclass(frozen=True)
class RunResult:
    run_id: str
    exit_code: int
    output: str


def new_run_id() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-" + uuid.uuid4().hex[:8]


def build_run_argv(python: Path, job: str) -> list[str]:
    if job not in ALLOWED_JOBS:
        raise ValueError(f"job must be one of {sorted(ALLOWED_JOBS)}, got: {job!r}")
    return [
        str(python),
        "-m",
        "dagster",
        "job",
        "execute",
        "-m",
        "tower_bi_orchestration.definitions",
        "-j",
        job,
    ]


def _child_env(
    root: Path, run_id: str, table: str | None, resolved_mode: str
) -> dict[str, str]:
    """Build the allowlisted child environment plus run-scoped discovery seams.

    The table and source-mode seams are set only when non-empty/non-default, so
    a default (CSV, no-table) run leaves both vars absent. Ambient variables do
    not cross the process boundary unless they are explicit runtime or governed
    connection variables.
    """
    env = allowed_child_environment(os.environ)
    env["SESHAT_DAGSTER_RUN_ID"] = run_id
    env["SESHAT_REPO_ROOT"] = str(root)
    # Force the CHILD to EMIT UTF-8, not just decode it in the parent (#404).
    # The `python -m dagster` child does not run seshat's stdio reconfig, so on
    # Windows it would otherwise write via the legacy code page (cp1252) and
    # UnicodeEncodeError on non-Latin-1 governed values (e.g. Arabic). Pairing
    # the child's UTF-8 output with the parent's UTF-8 decode also stops
    # `errors="replace"` from silently corrupting cp1252-encoded chars like `é`.
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    if table:
        env["SESHAT_DAGSTER_TABLES"] = table
    else:
        env.pop("SESHAT_DAGSTER_TABLES", None)
    if resolved_mode != DEFAULT_SOURCE_MODE:
        env[SOURCE_MODE_ENV] = resolved_mode
    else:
        env.pop(SOURCE_MODE_ENV, None)
    return env


def execute_run(
    root: Path,
    job: str,
    table: str | None = None,
    source_mode: str | None = None,
) -> RunResult:
    """Run one job in the orchestration environment; return the redacted result.

    The child's evidence lands under ``.seshat/dagster/runs/<run_id>/`` because
    the run id is injected via ``SESHAT_DAGSTER_RUN_ID`` -- the parent then
    finalizes and renders it (evidence.py).

    ``source_mode`` selects the Bronze source adapter (#404/#405). It travels
    via the ``SESHAT_DAGSTER_SOURCE_MODE`` env var -- the same closed discovery
    seam ``SESHAT_DAGSTER_TABLES`` uses, never argv -- and is validated
    fail-closed against the closed set. The var is set ONLY when non-default so
    the DEFAULT (CSV) run's child environment stays byte-identical to the
    pre-feature runner."""
    root = Path(root)
    python = orchestration_python(root)
    if python is None:
        raise RunnerError(
            "orchestration environment absent -- run `seshat dagster doctor` "
            "for the install remedy"
        )
    try:
        resolved_mode = normalize_source_mode(source_mode)
    except ValueError as error:
        raise RunnerError(str(error)) from error
    argv = build_run_argv(python, job)
    run_id = new_run_id()
    env = _child_env(root, run_id, table, resolved_mode)
    try:
        proc = subprocess.run(
            argv,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            # Decode the child's stdout/stderr as UTF-8, NOT the platform default
            # (cp1252 on Windows). The Dagster child ingests governed data whose
            # values can be non-Latin-1 (e.g. Arabic `billing_type`); with
            # `text=True` alone the reader thread decodes via
            # locale.getpreferredencoding() and raises UnicodeDecodeError mid-run
            # on Windows (#404). `errors="replace"` keeps a stray byte from
            # crashing the capture. Same class as the #322 stdio fix, one layer
            # down at the subprocess-read boundary.
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=_RUN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        # Fail closed: a hung child is a FAILED run, never an exception the
        # caller might swallow into a green result (review finding).
        return RunResult(
            run_id=run_id,
            exit_code=124,
            output=f"child run timed out after {_RUN_TIMEOUT_SECONDS}s (killed)",
        )
    combined = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    # Redact BEFORE truncating (#362 leak #2): slicing first can cut a DSN's
    # `scheme://` into the discarded front, leaving a schemeless credential
    # remainder that every redaction pass then misses. Redacting the full string
    # first, then trimming to the tail, closes that.
    return RunResult(
        run_id=run_id,
        exit_code=proc.returncode,
        output=redact_and_tail(combined, _TAIL_CHARS),
    )
