# T021 — Codex process lifecycle

**Date:** 2026-08-11
**Spec:** `specs/139-seshat-studio-foundation/` (task T021)
**Requirements:** FR-011, FR-012, FR-013, FR-024
**Status:** Design approved (owner, 2026-08-11)

## Why this task is the gate

Studio can already parse, correlate, normalize, and redact everything Codex
would send. It has never talked to a real Codex process. `app.py:340` still
reads *"the bridge is the deterministic fake until Phase 5"*, and there is no
`Popen` or `create_subprocess` anywhere under `src/seshat/studio/`.

Everything downstream needs a bridge that actually runs Codex: T023's contract
suite against the production adapter, Phase 6's provider approval
normalization, and T036's signed-in acceptance. T021 unblocks all three.

## What already exists (and is NOT re-scoped)

T020 shipped the pure, testable half of the Codex layer. This design builds on
it and changes none of it:

| Component | Status |
| --- | --- |
| `CodexLaunchPlan` — inspectable argv/cwd/handle plan | Done |
| `is_tested_version`, `MINIMUM/MAXIMUM_TESTED_CODEX` | Done |
| `classify_health` — seven contract states | Done |
| `find_codex_executable` | Done |
| `redact_provider_stderr` | Done |
| `CodexProtocolReader`, `classify_inbound`, `normalize_notification` | Done |

T021's task text lists "protocol probe, health classifier" among its items;
both already exist and stay the authority. The genuinely new work is the
process itself.

## Architecture

One new module, `src/seshat/studio/codex_bridge.py`, with two units.

### `CodexSession` — owns the child process

Takes a `CodexLaunchPlan` and spawns it. Responsibilities:

- `subprocess.Popen` with three explicit pipes (`stdin`, `stdout`, `stderr`),
  never inherited and never `DEVNULL`. `CodexLaunchPlan.inherits_any_handle`
  must be `False` for the plan it is given.
- A stdout reader thread feeding a `queue.Queue`. The thread reads bytes and
  hands them to `CodexProtocolReader`; it does not parse frames itself.
- A **separate** stderr drain thread that passes everything through
  `redact_provider_stderr` before any retention. stderr is never merged into
  stdout — it carries credential-shaped strings, and merging would feed those
  to the frame parser.
- Lifecycle: `handshake()`, `send()`, `events()`, `cancel()`, `close()`.

Public surface: those five methods. Consumers do not touch the process,
the threads, or the queue.

### `CodexBridge` — implements `AgentBridge`

`run_turn` stays a **sync generator**, matching the existing Protocol. It
pushes the turn request, then pulls frames off the queue through
`CodexProtocolReader` → `classify_inbound` → `normalize_notification`,
yielding `StudioEvent`s.

Appends itself to `BRIDGE_FACTORIES` as one line, per the pattern T017
established, so it inherits every shared assertion rather than re-deriving
them.

### Concurrency decision

Sync `subprocess.Popen` plus a reader thread; the `AgentBridge` Protocol is
unchanged.

`agent_routes` endpoints are `async def`, but `_record_turn` drives `run_turn`
with a plain `for` loop, and FastAPI already offloads sync work to a
threadpool. The alternative — making `run_turn` an `AsyncIterator` — would
change `AgentBridge`, `FakeAgentBridge`, `_record_turn`, and every test in the
shared suite, for no behaviour the sync form cannot deliver.

The cost is honest: thread-plus-pipe deadlock is a real risk, and this repo has
hit one before (issue #557, subprocess stdin under stdio). That risk is what
the scripted-child pipe test below exists to catch. It is not waved away.

## Out of scope, deliberately

- **Authentication.** "Official login delegation" means shelling to Codex's own
  `codex login`. Studio never implements auth, never handles credentials, and
  never stores a token. Anything else would turn a lifecycle task into a
  security surface.
- **Approval semantics.** `approval_required` normalizes to an event and stops
  there. Allow/deny is T024–T027.
- **The alternate API-key mode.** Shipped in T023a; nothing here may select it
  by inference or in response to any health state (FR-013).
- **T023's contract suite.** Depends on this task; not part of it.

## Verification

Two surfaces, because the environments genuinely differ.

### Unit — CI, no Codex CLI

CI's `check` job installs `.[dev]` and runs `pytest -m unit`; there is no Codex
CLI and no fastapi. Coverage comes from a **scripted fake child**: a real
Python subprocess, over a real pipe, replaying the committed
`tests/fixtures/codex_app_server/*.jsonl`.

Cases: handle discipline, handshake, cancellation mid-turn, clean shutdown
ordering, crash recovery, EOF, malformed frames, and the stdin-deadlock shape.

It must be a real pipe, not a mock. A mocked stream cannot exhibit the deadlock
this design's chosen concurrency model risks, so a mock would verify the wrong
property — the exact failure recorded in `subprocess-stdin-deadlock-under-stdio`.

**Faithfulness guard.** A scripted child that emits what the client expects
passes green while the client is wrong against real Codex. The mitigation is
that the script is not invented here: it replays fixtures T019 derived from
Codex's real generated schema, and `test_codex_fixture_provenance.py` already
guards them against drift. No new fake shape is introduced.

### Integration — local only, real Codex

`codex-cli 0.147.0` is installed on the development machine and sits exactly at
`MAXIMUM_TESTED_CODEX`, so a real handshake is reachable. Marked
`@pytest.mark.integration` so `pytest -m unit` skips it, following the pattern
documented at `.github/workflows/ci.yml:231-233` — integration tests are named
explicitly in their own step rather than left to a marker sweep.

This surface is the only proof that the fixtures match reality. It cannot run
in CI, and the design does not pretend otherwise.

## Two properties to verify during implementation

1. **`MAX_FRAME_BYTES` must be on the real path.** The process layer feeds
   `CodexProtocolReader` rather than parsing frames itself. If it parsed
   directly, the untrusted-output bound would exist only in unit tests.
2. **`ReadOnlyViolation` must fire for the real bridge.** `bridge.py` is
   explicit that the binding read-only refusal lives in
   `agent_routes._record_turn`, not in any bridge. The production bridge's
   output must pass through that guard exactly as the fake's does — a bridge
   that bypassed it would inherit no protection at all.

## Error handling

Every failure maps to an existing `classify_health` state rather than a new
vocabulary: missing executable, untested version, EOF, and crash each already
have a state and a recovery string. A crash mid-turn ends the turn with
`turn_failed` — never a silent truncation, and never a `turn_completed`.

## Success criteria

- `CodexBridge` is in `BRIDGE_FACTORIES` and passes the T017 shared suite
  unmodified.
- The scripted-child suite passes under `pytest -m unit` with no Codex CLI and
  no fastapi installed, verified by blocking the import rather than by a plain
  local green.
- A real handshake against codex-cli 0.147.0 succeeds locally.
- No credential reaches an event, a log, or a retained stderr buffer.
- `retail check` and `semantic-check` stay clean.
