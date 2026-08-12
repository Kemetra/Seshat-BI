# T021 Codex Process Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spawn and manage a real Codex app-server process so Studio's bridge stops being the deterministic fake.

**Architecture:** One new module `src/seshat/studio/codex_bridge.py` with two units — `CodexSession` owning a `subprocess.Popen` child plus stdout/stderr reader threads, and `CodexBridge` implementing the existing `AgentBridge` Protocol as a sync generator. Nothing in `codex_process.py`, `codex_protocol.py`, `bridge.py`, or `agent_routes.py` changes shape; the new bridge appends itself to `BRIDGE_FACTORIES` and inherits the T017 shared contract suite.

**Tech Stack:** Python 3.13, `subprocess`, `threading`, `queue`, pytest. No new dependencies.

## Global Constraints

- **Python:** 3.13. Type annotations on every function signature. `from __future__ import annotations` at the top of every module.
- **CI `check` job installs `.[dev]` only** — no `fastapi`, no Codex CLI. Any unit test importing `seshat.studio.agent_routes`/`app`/`bridge`/`session` must call `pytest.importorskip("fastapi")` first.
- **Never route the child through `gitutil.run_subprocess`** — it sets `stdin=DEVNULL` and a timeout cap, both wrong for a long-lived process that must be written to. See `codex_process.py` module docstring.
- **Never inherit a handle.** All three streams explicit pipes (issue #557).
- **stderr is never merged into stdout.** It carries credential-shaped strings.
- **No credential may reach an event, a log, or a retained buffer** (FR-026).
- **Formatting gate:** `ruff format --check src tests` and `ruff check src tests` must pass.
- **Test env:** run pytest with `PYTHONPATH=src` and `--no-cov` locally.
- **Commits:** unsigned (`--no-gpg-sign`), `<type>: <description>` subject.

## File Structure

| File | Responsibility |
| --- | --- |
| `src/seshat/studio/codex_bridge.py` (create) | `CodexSession` (process + threads) and `CodexBridge` (`AgentBridge` impl) |
| `tests/unit/_codex_child_script.py` (create) | Scripted fake child: replays a committed `.jsonl` fixture over real stdout |
| `tests/unit/test_studio_codex_session.py` (create) | Lifecycle over a REAL pipe: handshake, cancel, shutdown, crash, EOF, deadlock |
| `tests/unit/test_studio_codex_bridge.py` (create) | `CodexBridge.run_turn` event mapping against the scripted child |
| `tests/integration/test_studio_codex_real.py` (create) | Marked `integration`; real codex-cli 0.147.0 handshake |
| `tests/unit/test_studio_agent_bridge.py` (modify) | Append `CodexBridge` to `BRIDGE_FACTORIES` |
| `specs/139-seshat-studio-foundation/tasks.md` (modify) | Mark T021 complete on verified deliverable |

---

### Task 1: Scripted fake child that speaks over a real pipe

**Files:**
- Create: `tests/unit/_codex_child_script.py`
- Test: `tests/unit/test_studio_codex_session.py`

**Interfaces:**
- Consumes: committed fixtures at `tests/fixtures/codex_app_server/*.jsonl`
- Produces: a module runnable as `python -m` target via `[sys.executable, script_path, fixture_name]`, writing each fixture line to stdout followed by `\n` and flushing; exits 0 at EOF. Supports `--crash-after N` (exit 1 after N lines) and `--hang` (sleep without writing).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_studio_codex_session.py
"""Lifecycle tests over a REAL pipe.

A mocked stream cannot exhibit the pipe deadlock this design's concurrency model
risks, so these drive an actual child process. The child replays fixtures T019
derived from Codex's real generated schema -- it does not invent a shape.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).parent / "_codex_child_script.py"


def test_the_scripted_child_emits_fixture_lines_over_a_real_pipe() -> None:
    proc = subprocess.Popen(
        [sys.executable, str(_SCRIPT), "thread_turn"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, _ = proc.communicate(timeout=30)
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) >= 5, f"expected the fixture replayed, got {len(lines)} lines"
    assert '"jsonrpc"' in lines[0]
    assert proc.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_session.py -q --no-cov`
Expected: FAIL — the child script does not exist yet (non-zero returncode / empty stdout).

- [ ] **Step 3: Write the child script**

```python
# tests/unit/_codex_child_script.py
"""A fake Codex app-server child, for lifecycle tests over a real pipe.

Deliberately NOT a mock. The concurrency model under test uses a reader thread and
OS pipes; a mocked stream cannot deadlock, so it would verify the wrong property.

The replayed content comes from the committed fixtures T019 derived from Codex's
REAL generated schema (guarded by `test_codex_fixture_provenance.py`), so this
child cannot drift into emitting whatever the client happens to expect.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "codex_app_server"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture")
    parser.add_argument("--crash-after", type=int, default=None)
    parser.add_argument("--hang", action="store_true")
    args = parser.parse_args()

    if args.hang:
        time.sleep(60)
        return 0

    path = _FIXTURES / f"{args.fixture}.jsonl"
    written = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        written += 1
        if args.crash_after is not None and written >= args.crash_after:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_session.py -q --no-cov`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/_codex_child_script.py tests/unit/test_studio_codex_session.py
git commit --no-gpg-sign -m "test: add a scripted Codex child that speaks over a real pipe"
```

---

### Task 2: `CodexSession` — spawn, read, and shut down cleanly

**Files:**
- Create: `src/seshat/studio/codex_bridge.py`
- Test: `tests/unit/test_studio_codex_session.py` (append)

**Precondition — Windows line endings.** The Task 1 review flagged that Windows
text-mode stdout emits `\r\n` where the framing contract says `\n`. Task 1's own
test cannot see it (`text=True` on `Popen` translates on read), but this task's
reader must. Open the child's streams in TEXT mode (`text=True`), which applies
universal-newline translation — do NOT read the pipe in binary and hand raw bytes
to `CodexProtocolReader`, or a trailing `\r` rides on every frame. If binary
framing is ever needed, add `sys.stdout.reconfigure(newline="\n")` to
`_codex_child_script.py` rather than stripping `\r` in the parser.

**Interfaces:**
- Consumes: `CodexLaunchPlan` (`argv: tuple[str, ...]`, `cwd: Path`, `inherits_any_handle: bool`) and `redact_provider_stderr(raw: str, *, workspace_root: Path | None = None) -> str` from `seshat.studio.codex_process`; `CodexProtocolReader` (`.feed(chunk: str) -> Iterator[dict]`) from `seshat.studio.codex_protocol`.
- Produces:
  - `class CodexSession` with `__init__(self, plan: CodexLaunchPlan, *, spawn: Callable[..., Any] | None = None) -> None`
  - `.start() -> None`
  - `.frames(timeout: float = 30.0) -> Iterator[dict[str, Any]]` — yields parsed frames until EOF
  - `.send(frame: dict[str, Any]) -> None`
  - `.stderr_text() -> str` — redacted, accumulated
  - `.close(timeout: float = 5.0) -> int | None` — terminate, join threads, return returncode
  - `.is_running -> bool`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/unit/test_studio_codex_session.py
from seshat.studio.codex_process import CodexLaunchPlan


def _plan(tmp_path: Path, fixture: str, *extra: str) -> CodexLaunchPlan:
    return CodexLaunchPlan(
        argv=(sys.executable, str(_SCRIPT), fixture, *extra), cwd=tmp_path
    )


def test_a_session_reads_every_frame_then_sees_eof(tmp_path: Path) -> None:
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "thread_turn"))
    session.start()
    try:
        frames = list(session.frames())
    finally:
        session.close()

    assert frames, "no frames were read from the child"
    assert all(frame.get("jsonrpc") == "2.0" for frame in frames)


def test_a_session_never_inherits_a_handle(tmp_path: Path) -> None:
    """Issue #557: an inherited stdin under `seshat mcp` is the client's live pipe."""
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "handshake"))
    assert session.plan.inherits_any_handle is False


def test_closing_a_hung_child_does_not_block_forever(tmp_path: Path) -> None:
    """The deadlock shape: a child that never writes must not wedge shutdown."""
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "handshake", "--hang"))
    session.start()
    returncode = session.close(timeout=5.0)

    assert session.is_running is False
    assert returncode is not None


def test_stderr_is_redacted_before_retention(tmp_path: Path) -> None:
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "handshake"))
    session.start()
    session.close()
    assert "sk-" not in session.stderr_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_session.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.studio.codex_bridge'`

- [ ] **Step 3: Write the implementation**

```python
# src/seshat/studio/codex_bridge.py
"""The live Codex app-server session and the bridge built on it (T021).

`codex_process` stops at an inspectable PLAN so handle discipline is unit-testable
without a Codex CLI. This module is where that plan is actually spawned.

**Why sync `Popen` and a reader thread.** `agent_routes` endpoints are `async def`,
but `_record_turn` drives `AgentBridge.run_turn` with a plain `for` loop and FastAPI
already offloads sync work to a threadpool. Making `run_turn` an `AsyncIterator`
would change the Protocol, `FakeAgentBridge`, `_record_turn`, and every test in the
shared suite, for no behaviour this form cannot deliver. The cost is that
thread-plus-pipe deadlock is a real risk -- which is why the tests drive an actual
child over an actual pipe rather than a mock.

**stdout is never parsed here.** Bytes go to `CodexProtocolReader`, which owns the
framing rules and the `MAX_FRAME_BYTES` bound on untrusted provider output. Parsing
inline would leave that bound existing only in the protocol module's own tests.

**stderr is drained on its own thread and redacted before retention.** It carries
credential-shaped strings; merging it into stdout would feed those to the frame
parser and into any diagnostic that kept the stream.
"""

from __future__ import annotations

import queue
import subprocess
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from seshat.studio.codex_process import CodexLaunchPlan, redact_provider_stderr
from seshat.studio.codex_protocol import CodexProtocolReader

__all__ = ["CodexSession"]

#: Sentinel pushed onto the frame queue when the reader thread sees EOF.
_EOF = object()


class CodexSession:
    """Owns one Codex app-server child process and its two reader threads."""

    def __init__(
        self, plan: CodexLaunchPlan, *, spawn: Callable[..., Any] | None = None
    ) -> None:
        self.plan = plan
        self._spawn = spawn or subprocess.Popen
        self._process: Any | None = None
        self._frames: queue.Queue[Any] = queue.Queue()
        self._stderr_parts: list[str] = []
        self._threads: list[threading.Thread] = []

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        """Spawn the child with three explicit pipes and start both readers."""
        if self.plan.inherits_any_handle:
            raise ValueError(
                "refusing to spawn: the launch plan would inherit a handle (#557)"
            )
        self._process = self._spawn(
            list(self.plan.argv),
            cwd=str(self.plan.cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._start_thread(self._read_stdout)
        self._start_thread(self._read_stderr)

    def _start_thread(self, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        self._threads.append(thread)

    def _read_stdout(self) -> None:
        reader = CodexProtocolReader()
        stream = self._process.stdout if self._process else None
        if stream is None:
            self._frames.put(_EOF)
            return
        try:
            for chunk in iter(stream.readline, ""):
                for frame in reader.feed(chunk):
                    self._frames.put(frame)
        except Exception as error:  # surfaced as a frame, never swallowed
            self._frames.put(error)
        finally:
            self._frames.put(_EOF)

    def _read_stderr(self) -> None:
        stream = self._process.stderr if self._process else None
        if stream is None:
            return
        for chunk in iter(stream.readline, ""):
            self._stderr_parts.append(
                redact_provider_stderr(chunk, workspace_root=self.plan.cwd)
            )

    def frames(self, timeout: float = 30.0) -> Iterator[dict[str, Any]]:
        """Yield parsed frames until the child closes stdout."""
        while True:
            item = self._frames.get(timeout=timeout)
            if item is _EOF:
                return
            if isinstance(item, Exception):
                raise item
            yield item

    def send(self, frame: dict[str, Any]) -> None:
        """Write one JSON-RPC frame to the child's stdin."""
        import json

        if self._process is None or self._process.stdin is None:
            raise RuntimeError("session is not started")
        self._process.stdin.write(json.dumps(frame) + "\n")
        self._process.stdin.flush()

    def stderr_text(self) -> str:
        """Everything the child wrote to stderr, already redacted."""
        return "".join(self._stderr_parts)

    def close(self, timeout: float = 5.0) -> int | None:
        """Terminate the child and join both readers. Safe to call twice."""
        if self._process is None:
            return None
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=timeout)
        for stream in (
            self._process.stdin,
            self._process.stdout,
            self._process.stderr,
        ):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        for thread in self._threads:
            thread.join(timeout=timeout)
        return self._process.returncode
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_session.py -q --no-cov`
Expected: PASS (4 tests)

- [ ] **Step 5: Verify formatting and lint**

Run: `ruff format src tests && ruff check --fix src tests && ruff format --check src tests && ruff check src tests`
Expected: "All checks passed!"

- [ ] **Step 6: Commit**

```bash
git add src/seshat/studio/codex_bridge.py tests/unit/test_studio_codex_session.py
git commit --no-gpg-sign -m "feat: add the live Codex session with piped stdio and redacted stderr"
```

---

### Task 3: Crash and EOF map to a terminal state, never a silent success

**Files:**
- Modify: `src/seshat/studio/codex_bridge.py`
- Test: `tests/unit/test_studio_codex_session.py` (append)

**Interfaces:**
- Consumes: `CodexSession.close()`, `ProbeObservations(executable_found: bool, version: str | None, signed_in: bool, rate_limit_reached: bool = False, resets_at: int | None = None, saw_eof: bool = False, disabled: bool = False)` and `classify_health(observations: ProbeObservations) -> AgentHealth` from `seshat.studio.codex_process`.
- Produces: `CodexSession.health(version: str | None, *, signed_in: bool) -> AgentHealth` — reports `saw_eof=True` when the child died.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/unit/test_studio_codex_session.py
def test_a_crashed_child_reports_an_eof_health_state(tmp_path: Path) -> None:
    """A crash must not read as a healthy session with a short answer."""
    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(_plan(tmp_path, "thread_turn", "--crash-after", "2"))
    session.start()
    list(session.frames())
    session.close()

    health = session.health("0.147.0", signed_in=True)
    assert health.state != "ready", "a crashed child was reported as ready"
    assert health.provider in {"codex", "disabled"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_session.py::test_a_crashed_child_reports_an_eof_health_state -q --no-cov`
Expected: FAIL — `AttributeError: 'CodexSession' object has no attribute 'health'`

- [ ] **Step 3: Write the implementation**

Add to `CodexSession` in `src/seshat/studio/codex_bridge.py`, and extend the import line to `from seshat.studio.codex_process import (CodexLaunchPlan, ProbeObservations, classify_health, redact_provider_stderr)`:

```python
    def health(self, version: str | None, *, signed_in: bool) -> AgentHealth:
        """Classify this session, reporting a dead child as EOF.

        Delegates to `classify_health` rather than inventing a second vocabulary:
        that function owns the seven contract states and the FR-013 rule that no
        health condition may switch Studio to a billed path.
        """
        died = self._process is not None and self._process.poll() not in (None, 0)
        return classify_health(
            ProbeObservations(
                executable_found=True,
                version=version,
                signed_in=signed_in,
                saw_eof=died,
            )
        )
```

Add `from seshat.studio.projection import AgentHealth` to the imports.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_session.py -q --no-cov`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/seshat/studio/codex_bridge.py tests/unit/test_studio_codex_session.py
git commit --no-gpg-sign -m "feat: report a crashed Codex child as an EOF health state"
```

---

### Task 4: `CodexBridge` implements `AgentBridge` and joins the shared suite

**Files:**
- Modify: `src/seshat/studio/codex_bridge.py`
- Create: `tests/unit/test_studio_codex_bridge.py`
- Modify: `tests/unit/test_studio_agent_bridge.py:35`

**Interfaces:**
- Consumes: `validate_turn_request(prompt: str, requested_mode: str) -> str` and `_event(event_type: str, payload: dict[str, Any], turn_id: str, sequence: int) -> StudioEvent` from `seshat.studio.bridge`; `NormalizationContext(workspace_root: Path | None, secrets: Sequence[str | None] = (), delta_buffer: _DeltaBuffer = ...)` and `normalize_notification(frame: dict[str, Any], *, context: NormalizationContext) -> Iterator[tuple[str, dict[str, Any]]]` from `seshat.studio.codex_protocol`.
- Produces: `class CodexBridge` with `describe() -> dict[str, Any]` and `run_turn(*, prompt: str, turn_id: str, requested_mode: str) -> Iterator[StudioEvent]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_studio_codex_bridge.py
"""`CodexBridge` maps a real child's frames onto Studio events.

Driven against the scripted child, so the mapping is exercised over a real pipe
rather than a hand-built frame list.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = Path(__file__).parent / "_codex_child_script.py"


def _bridge(tmp_path: Path, fixture: str = "thread_turn"):
    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    plan = CodexLaunchPlan(argv=(sys.executable, str(_SCRIPT), fixture), cwd=tmp_path)
    return CodexBridge(plan)


def test_a_turn_starts_and_ends_with_exactly_one_terminal(tmp_path: Path) -> None:
    events = list(
        _bridge(tmp_path).run_turn(
            prompt="Summarise the readiness spine",
            turn_id="turn-1",
            requested_mode="read_only",
        )
    )

    assert events, "the bridge produced no events"
    assert events[0].type == "turn_started"
    terminals = [e for e in events if e.type in {"turn_completed", "turn_failed"}]
    assert len(terminals) == 1, f"expected one terminal, got {len(terminals)}"
    assert events[-1].type in {"turn_completed", "turn_failed"}


def test_the_bridge_describes_itself_as_codex(tmp_path: Path) -> None:
    described = _bridge(tmp_path).describe()
    assert described["provider"] == "codex"


def test_an_unknown_mode_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        list(
            _bridge(tmp_path).run_turn(
                prompt="hello", turn_id="t", requested_mode="wat"
            )
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_bridge.py -q --no-cov`
Expected: FAIL — `ImportError: cannot import name 'CodexBridge'`

- [ ] **Step 3: Write the implementation**

Append to `src/seshat/studio/codex_bridge.py` and add `"CodexBridge"` to `__all__`:

```python
class CodexBridge:
    """`AgentBridge` over a live Codex app-server.

    A sync generator on purpose -- see the module docstring. Frames are normalized by
    `codex_protocol`, never mapped here: one normalization authority is what keeps the
    allowlist (and its refusal to pass through reasoning) in a single place.
    """

    def __init__(self, plan: CodexLaunchPlan) -> None:
        self._plan = plan

    def describe(self) -> dict[str, Any]:
        return {"bridge": "codex", "provider": "codex", "deterministic": False}

    def run_turn(
        self, *, prompt: str, turn_id: str, requested_mode: str
    ) -> Iterator[StudioEvent]:
        cleaned = validate_turn_request(prompt, requested_mode)
        sequence = 0

        def emit(event_type: str, payload: dict[str, Any]) -> StudioEvent:
            nonlocal sequence
            sequence += 1
            return _event(event_type, payload, turn_id, sequence)

        yield emit("turn_started", {"prompt_echo": cleaned[:200]})

        session = CodexSession(self._plan)
        context = NormalizationContext(workspace_root=self._plan.cwd)
        saw_terminal = False
        session.start()
        try:
            for frame in session.frames():
                for event_type, payload in normalize_notification(
                    frame, context=context
                ):
                    if event_type == "turn_started":
                        # The envelope above already opened the turn.
                        continue
                    if event_type in {"turn_completed", "turn_failed"}:
                        saw_terminal = True
                    yield emit(event_type, payload)
        finally:
            session.close()

        if not saw_terminal:
            # EOF without a terminal frame is a failure, never a quiet success.
            yield emit(
                "turn_failed",
                {
                    "category": "provider_error",
                    "detail": "the provider ended the session without completing the turn",
                },
            )
```

Extend the imports at the top of the module:

```python
from seshat.studio.bridge import _event, validate_turn_request
from seshat.studio.codex_protocol import (
    CodexProtocolReader,
    NormalizationContext,
    normalize_notification,
)
from seshat.studio.events import StudioEvent
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_bridge.py -q --no-cov`
Expected: PASS (3 tests)

- [ ] **Step 5: Join the shared contract suite**

In `tests/unit/test_studio_agent_bridge.py`, replace line 35:

```python
BRIDGE_FACTORIES: list[tuple[str, Callable[[], Any]]] = [("fake", _fake_bridge)]
```

with:

```python
def _codex_bridge() -> Any:
    """The production bridge, driven against the scripted child.

    Appended here rather than given its own assertions so it inherits every property
    the fake is held to -- the difference between a real protocol and two classes that
    share method names.
    """
    import sys
    from pathlib import Path

    from seshat.studio.codex_bridge import CodexBridge
    from seshat.studio.codex_process import CodexLaunchPlan

    script = Path(__file__).parent / "_codex_child_script.py"
    return CodexBridge(
        CodexLaunchPlan(
            argv=(sys.executable, str(script), "thread_turn"),
            cwd=Path(__file__).resolve().parents[2],
        )
    )


BRIDGE_FACTORIES: list[tuple[str, Callable[[], Any]]] = [
    ("fake", _fake_bridge),
    ("codex", _codex_bridge),
]
```

- [ ] **Step 6: Run the shared suite for BOTH bridges**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_agent_bridge.py -q --no-cov`
Expected: PASS. Every assertion now runs twice — once per bridge. If the codex parametrization fails, fix `CodexBridge`, never the shared assertion.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/studio/codex_bridge.py tests/unit/test_studio_codex_bridge.py tests/unit/test_studio_agent_bridge.py
git commit --no-gpg-sign -m "feat: implement CodexBridge and enrol it in the shared contract suite"
```

---

### Task 5: Prove the read-only refusal binds the real bridge

**Files:**
- Test: `tests/unit/test_studio_codex_bridge.py` (append)

**Interfaces:**
- Consumes: `WRITE_INTENT_TYPES` and `ReadOnlyViolation` from `seshat.studio.agent_routes` (requires fastapi — guard with `importorskip`).

- [ ] **Step 1: Write the failing test**

The test must DRIVE the guard, not assert around it. A test that only checked
event-type membership would duplicate Task 4 while its name claimed to verify the
refusal — coverage the code does not actually have.

```python
# append to tests/unit/test_studio_codex_bridge.py
def test_write_intent_from_the_real_bridge_is_refused_under_read_only(
    tmp_path: Path,
) -> None:
    """`bridge.py` is explicit that the BINDING refusal lives in `_record_turn`.

    A bridge that never passed through it would inherit no protection at all -- the
    exact defect that docstring records for an earlier revision. So this drives the
    real route helper with a stream that DOES carry write intent and asserts the
    refusal fires, rather than inspecting the bridge's output and inferring safety.
    """
    pytest.importorskip("fastapi")
    from seshat.studio.agent_routes import (
        ReadOnlyViolation,
        TurnRequest,
        _record_turn,
    )
    from seshat.studio.bridge import _event
    from seshat.studio.events import ThreadEvents

    class _WriteIntentBridge:
        """Stands in for a provider that proposes a change during `read_only`."""

        def describe(self) -> dict[str, object]:
            return {"bridge": "codex", "provider": "codex", "deterministic": False}

        def run_turn(self, *, prompt: str, turn_id: str, requested_mode: str):
            yield _event("turn_started", {"prompt_echo": prompt[:200]}, turn_id, 1)
            yield _event(
                "file_change_proposed",
                {"paths": ["silver/model.sql"], "summary": "1 file change proposed"},
                turn_id,
                2,
            )

    thread = ThreadEvents("thread-1")
    request = TurnRequest(
        prompt="Propose the silver model", turn_id="t1", requested_mode="read_only"
    )

    with pytest.raises(ReadOnlyViolation):
        _record_turn(thread, _WriteIntentBridge(), request)


def test_the_guard_is_what_refuses_not_the_bridge(tmp_path: Path) -> None:
    """Prove the refusal comes from the route, by disabling only the guard.

    If the assertion above passed because the bridge declined to emit write intent,
    this would still pass -- so it monkeypatches `WRITE_INTENT_TYPES` to empty and
    asserts the SAME stream is then recorded without complaint. That is the positive
    evidence that `_record_turn` is the thing doing the refusing.
    """
    pytest.importorskip("fastapi")
    import seshat.studio.agent_routes as routes
    from seshat.studio.bridge import _event
    from seshat.studio.events import ThreadEvents

    class _WriteIntentBridge:
        def describe(self) -> dict[str, object]:
            return {"bridge": "codex", "provider": "codex", "deterministic": False}

        def run_turn(self, *, prompt: str, turn_id: str, requested_mode: str):
            yield _event("turn_started", {"prompt_echo": prompt[:200]}, turn_id, 1)
            yield _event(
                "file_change_proposed",
                {"paths": ["silver/model.sql"], "summary": "1 file change proposed"},
                turn_id,
                2,
            )

    original = routes.WRITE_INTENT_TYPES
    try:
        routes.WRITE_INTENT_TYPES = frozenset()
        thread = ThreadEvents("thread-2")
        request = routes.TurnRequest(
            prompt="Propose the silver model", turn_id="t2", requested_mode="read_only"
        )
        recorded = routes._record_turn(thread, _WriteIntentBridge(), request)
    finally:
        routes.WRITE_INTENT_TYPES = original

    assert any(event.type == "file_change_proposed" for event in recorded), (
        "with the guard disabled the write intent should have been recorded; if it "
        "was not, the first test proved nothing about the guard"
    )
```

- [ ] **Step 2: Run the tests**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_studio_codex_bridge.py -q --no-cov`
Expected: PASS. If the first test FAILS, `_record_turn` is not enforcing the refusal —
that is a real defect, fix the route, never the assertion. If the SECOND test fails,
the first one is passing for the wrong reason and proves nothing.

If `ThreadEvents("thread-1")` does not match the real constructor signature, read
`src/seshat/studio/events.py` and use the real one — do not stub the class.

- [ ] **Step 3: Verify the test is skipped, not failed, without fastapi**

```bash
PYTHONPATH=src python -c "
import sys
class B:
    def find_module(self, n, p=None):
        if n == 'fastapi' or n.startswith('fastapi.'): return self
    def load_module(self, n): raise ImportError('blocked')
sys.meta_path.insert(0, B())
import pytest
sys.exit(pytest.main(['tests/unit/test_studio_codex_bridge.py','-q','--no-cov','-p','no:cacheprovider']))
"
```

Expected: all tests pass, with the guarded one reported as skipped. A plain local green proves nothing about CI — the unit job has no fastapi.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_studio_codex_bridge.py
git commit --no-gpg-sign -m "test: pin the read-only guard binding for the production bridge"
```

---

### Task 6: Real Codex handshake, marked as integration

**Files:**
- Create: `tests/integration/test_studio_codex_real.py`

**Interfaces:**
- Consumes: `find_codex_executable() -> str | None`, `CodexLaunchPlan.for_workspace(workspace: Path, *, executable: str) -> CodexLaunchPlan`, `CodexSession`.

- [ ] **Step 1: Write the test**

```python
# tests/integration/test_studio_codex_real.py
"""The only proof that the committed fixtures match a real Codex build.

Marked `integration` so `pytest -m unit` in the CI `check` job never reaches it --
that job has no Codex CLI. Skips cleanly when the CLI is absent, so it is safe to
run anywhere.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_a_real_codex_app_server_completes_a_handshake(tmp_path: Path) -> None:
    from seshat.studio.codex_process import (
        CodexLaunchPlan,
        find_codex_executable,
        is_tested_version,
    )

    executable = find_codex_executable()
    if executable is None:
        pytest.skip("the Codex CLI is not installed on this machine")

    import subprocess

    version = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, timeout=30
    ).stdout.strip()
    reported = version.split()[-1] if version else ""
    if not is_tested_version(reported):
        pytest.skip(f"codex {reported!r} is outside the tested range")

    from seshat.studio.codex_bridge import CodexSession

    session = CodexSession(CodexLaunchPlan.for_workspace(tmp_path, executable=executable))
    session.start()
    try:
        session.send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "seshat-studio", "version": "1"}},
            }
        )
        first = next(session.frames(timeout=60.0), None)
    finally:
        session.close()

    assert first is not None, "the real app-server produced no frame"
    assert first.get("jsonrpc") == "2.0"
    assert "sk-" not in session.stderr_text()
```

- [ ] **Step 2: Run it against the installed CLI**

Run: `PYTHONPATH=src python -m pytest tests/integration/test_studio_codex_real.py -q --no-cov -rs`
Expected: PASS against codex-cli 0.147.0. If it SKIPS, report that plainly — a skip is not a pass.

- [ ] **Step 3: Verify `pytest -m unit` does not reach it**

Run: `PYTHONPATH=src python -m pytest tests/integration/test_studio_codex_real.py -m unit -q --no-cov`
Expected: "no tests ran" / all deselected.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_studio_codex_real.py
git commit --no-gpg-sign -m "test: add the real Codex handshake as a marked integration test"
```

---

### Task 7: Full gates and mark T021 complete

**Files:**
- Modify: `specs/139-seshat-studio-foundation/tasks.md:293-297`

- [ ] **Step 1: Run the full unit suite**

Run: `PYTHONPATH=src GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=false python -m pytest tests/unit -q --no-cov`
Expected: all pass except the known-environmental `test_version_resolver_matches_pyproject_when_installed` (installed 0.8.1 vs pyproject 0.8.2). Confirm any other failure is pre-existing by stashing before blaming the diff.

- [ ] **Step 2: Run the formatting, lint, and governance gates**

```bash
ruff format --check src tests
ruff check src tests
PYTHONPATH=src python -m seshat.cli check
PYTHONPATH=src python -m seshat.cli semantic-check
```

Expected: format/lint clean; `check` shows only the known non-blocking RS1 warning; `semantic-check` reports 0 findings.

- [ ] **Step 3: Verify the unit suite passes with fastapi blocked**

```bash
PYTHONPATH=src python -c "
import sys
class B:
    def find_module(self, n, p=None):
        if n == 'fastapi' or n.startswith('fastapi.'): return self
    def load_module(self, n): raise ImportError('blocked')
sys.meta_path.insert(0, B())
import pytest
sys.exit(pytest.main(['tests/unit/test_studio_codex_bridge.py','tests/unit/test_studio_codex_session.py','tests/unit/test_studio_agent_bridge.py','-q','--no-cov','-p','no:cacheprovider']))
"
```

Expected: PASS. This mirrors the CI `check` job, which installs `.[dev]` only.

- [ ] **Step 4: Mark T021 complete**

In `specs/139-seshat-studio-foundation/tasks.md`, change `- [ ] **T021**` to `- [x] **T021**` and append a note recording what shipped, following the style of the T015–T018 entries. Mark it ONLY on the verified deliverable — never sweep checkboxes.

- [ ] **Step 5: Commit and open a PR**

```bash
git add specs/139-seshat-studio-foundation/tasks.md
git commit --no-gpg-sign -m "docs: mark T021 complete on the verified Codex session"
git push -u origin studio-t021
gh pr create --title "feat: spawn and manage the real Codex app-server process (T021)" --body "..."
```

The PR title needs a `type:` prefix — squash-merge uses it as the commit subject.

## Self-Review

**Spec coverage.** Architecture → Tasks 2/4. `CodexSession` five methods → Tasks 2/3. `CodexBridge` + `BRIDGE_FACTORIES` → Task 4. Scripted fake child from committed fixtures → Task 1. Real-Codex integration → Task 6. `MAX_FRAME_BYTES` on the real path → Task 2 (reader feeds `CodexProtocolReader`, asserted by the module docstring and exercised by every session test). `ReadOnlyViolation` binding → Task 5. Error handling via `classify_health` → Task 3. Success criteria → Task 7.

**Placeholders.** None. Every code step carries real code; the only `"..."` is the PR body, filled at Task 7 Step 5.

**Type consistency.** `CodexSession.__init__(plan, *, spawn=None)`, `.start()`, `.frames(timeout=30.0)`, `.send(frame)`, `.stderr_text()`, `.close(timeout=5.0)`, `.health(version, *, signed_in)`, `.is_running`, `.plan` — used identically in Tasks 2, 3, 4, 6. `CodexBridge(plan)` with `.describe()`/`.run_turn(*, prompt, turn_id, requested_mode)` matches the `AgentBridge` Protocol exactly.

**Known risk.** Task 4's `_event` and `validate_turn_request` are private/module-level in `bridge.py`. If importing `_event` across modules trips a lint rule, promote it to `build_event` in `bridge.py` and update both call sites — do not duplicate it.
