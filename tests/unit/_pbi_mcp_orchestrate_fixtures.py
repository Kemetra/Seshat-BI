"""Shared scaffolding for the pbi-mcp orchestrate suites.

The constants, builders and the `ready_repo` fixture used by both the behaviour
suite and the regression suite. Extracted when #660 grew the single module from
626 to 886 lines and CodeScene measured its responsibilities rising 1 -> 5
(Low Cohesion, threshold 4): the scaffolding is one responsibility and now sits
in one place, following the `_dep_coresolve_fixtures` convention already used by
this suite.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat.pbi_mcp_adapter import gate, orchestrate, protocol

TARGET = "sales_model"
#: A (tool, operation) PAIR, per #660: the vendor dispatches on both, and the
#: pre-#660 single token encoded a `--operation` CLI flag that never existed.
#:
#: `Rename`, not `Update`: the server documents Create/Update as requiring a
#: `Definitions` payload, which this adapter is forbidden to invent, so those
#: pairs are REFUSED with PBIMCP-RUN-09 (re-review C2). `Rename` uses
#: `RenameDefinitions` and is a genuine write needing no approved definition, so
#: it exercises the connect/operate/flush path honestly.
OPERATION = "measure_operations.Rename"
#: Under `*.SemanticModel/definition/`, because that is the ONLY corpus
#: `seshat semantic-check` discovers. A fixture at `models/*.tmdl` is never
#: examined by the validator, so post-write validation could not really pass --
#: previously masked by the injected validator stub (Codex review, PR #659).
TARGET_PATH = f"Sales.SemanticModel/definition/{TARGET}.tmdl"

#: Real TMDL, not a placeholder comment. ``seshat semantic-check`` skips a
#: ``*.tmdl`` with no top-level ``table`` block, so a fixture using
#: ``// original`` gave the validator nothing to parse -- invisible here only
#: because these tests inject a validator stub returning 0.
#: ``validation._target_was_examined`` reads the artifact itself, so the content
#: has to be honest (Codex review, PR #659).
BASELINE_TMDL = "table sales_model\n\n\tcolumn Amount\n\t\tdataType: double\n"
MUTATED_TMDL = BASELINE_TMDL + "\n\tmeasure Total = SUM(sales_model[Amount])\n"
STAMP = "2026-08-18T00:00:00Z"
OWNER = "Ahmed Shaaban (data_owner)"

READINESS = (
    "stages:\n"
    "  semantic_model_ready:\n    status: pass\n"
    "  publish_ready:\n    status: not_started\n"
    "approvals:\n"
    "  - stage: publish_ready\n"
    f"    owner: {OWNER!r}\n"
    "    at: '2026-08-18'\n"
    f"    note: 'approved for {TARGET}: {OPERATION}'\n"
)

ALLOWLIST = (
    f"targets:\n  - target_id: {TARGET}\n"
    f"    path: {TARGET_PATH}\n"
    f"    operations:\n      - {OPERATION}\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _write(repo: Path, relpath: str, text: str) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def ready_repo(tmp_path: Path) -> Path:
    """A repo where every precondition holds, all state COMMITTED."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@e.invalid")
    _git(tmp_path, "config", "user.name", "T")
    _write(tmp_path, f"mappings/{TARGET}/readiness-status.yaml", READINESS)
    _write(tmp_path, gate.TARGET_ALLOWLIST_RELPATH, ALLOWLIST)
    _write(tmp_path, TARGET_PATH, BASELINE_TMDL)
    _write(tmp_path, "README.md", "fixture\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline", "--no-gpg-sign")
    return tmp_path


def _mcp(returncode: int = 0, mutates: str | None = None):
    """A stub MCP SESSION that optionally edits the artifact, like the real one.

    Shaped to the #660 contract: the runtime is an MCP stdio server, so the
    injected double is a session factory, not a subprocess invoker. It writes the
    artifact on the ``ExportToTmdlFolder`` call rather than on the operation --
    faithful to the real vendor, which mutates an in-memory model and only
    touches disk on the explicit flush (verified 2026-08-20).
    """

    class _Session:
        def __init__(self, cwd: Path):
            self._cwd = Path(cwd)
            self.calls: list[tuple[str, dict]] = []

        def handshake(self) -> dict:
            return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

        def call(self, tool: str, request: dict):
            self.calls.append((tool, request))
            operation = request.get("operation")
            if operation == "ExportToTmdlFolder" and mutates is not None:
                (self._cwd / TARGET_PATH).write_text(mutates, encoding="utf-8")
            ok = returncode == 0
            return protocol.ToolOutcome(
                ok=ok,
                # The vendor annotates per call: reads/connect/flush true, the
                # mutating operation false.
                read_only_hint=operation != "Rename",
                payload=None,
                raw_text="ok",
                error=None if ok else "the vendor reported isError",
            )

        def close(self) -> None:
            return None

    def factory(*, argv: list[str], cwd: Path, **_extra: object):  # noqa: ARG001
        return _Session(cwd)

    return factory


def _mcp_session(on_flush=None, *, returncode: int = 0, on_call=None):
    """Build a session-factory double from a side effect.

    ``on_flush(cwd)`` runs when the flush call arrives -- the only point at which
    the real vendor touches disk. ``on_call(cwd)`` runs on every call, for tests
    that need to observe ordering rather than disk state.
    """

    class _Session:
        def __init__(self, cwd: Path):
            self._cwd = Path(cwd)

        def handshake(self) -> dict:
            return {"name": "powerbi-modeling-mcp", "version": "0.5.0.0"}

        def call(self, tool: str, request: dict):
            operation = request.get("operation")
            if on_call is not None:
                on_call(self._cwd)
            if operation == "ExportToTmdlFolder" and on_flush is not None:
                on_flush(self._cwd)
            ok = returncode == 0
            return protocol.ToolOutcome(
                ok=ok,
                read_only_hint=operation != "Rename",
                payload=None,
                raw_text="ok" if ok else "",
                error=None if ok else "the vendor reported isError",
            )

        def close(self) -> None:
            return None

    def factory(*, argv: list[str], cwd: Path, **_extra: object):  # noqa: ARG001
        return _Session(cwd)

    return factory


def _validator(returncode: int = 0):
    def run(repo_root: Path, args: tuple[str, ...]):
        return subprocess.CompletedProcess(args=list(args), returncode=returncode)

    return run


def _apply(repo: Path, **kwargs: object) -> orchestrate.WriteReport:
    params: dict[str, object] = {
        "target_id": TARGET,
        "operation_id": OPERATION,
        "timestamp": STAMP,
        "tree_clean": True,
        "mcp_runner": _mcp(mutates=MUTATED_TMDL),
        "validator": _validator(0),
    }
    params.update(kwargs)
    return orchestrate.apply_write(repo, **params)  # type: ignore[arg-type]
