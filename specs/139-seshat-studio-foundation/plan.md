# Implementation Plan: Seshat Studio Foundation

**Branch**: `studio` | **Date**: 2026-08-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/139-seshat-studio-foundation/spec.md`

**Status**: planning package authored; implementation is blocked until a named
human ratifies this exact package and it becomes the sole active Spec Kit plan.

## Summary

Build the first independently useful Seshat Studio slice: a token-protected,
loopback-only localhost application that projects one workspace's existing Seshat
readiness truth into a modern Command Room and streams governed Codex turns through
the user's existing CLI subscription. The backend is an optional FastAPI service in
`seshat.studio`; the browser is a prebuilt React/TypeScript application bundled in
the wheel. A provider-neutral `AgentBridge` isolates the Codex app-server protocol,
and a deterministic fake bridge makes the full browser flow testable without a
subscription or network access.

Studio remains downstream of Core Authority. It does not derive readiness, execute
tools in browser code, record named-human business decisions, introduce a database,
or silently switch to API-key billing. The existing static `retail dashboard` stays
unchanged.

## Technical Context

**Language/Version**: Python 3.13; TypeScript 5.x and Node 20+ for frontend
development only.

**Primary Dependencies**: `fastapi`, `uvicorn[standard]` in a new `studio`
optional extra; React, TypeScript, Vite, Testing Library, Vitest, Playwright, and
axe-core in the nested frontend development package. Codex is an external local
executable, not a Python dependency.

**Storage**: committed Seshat workspace artifacts remain durable truth. Session,
thread, approval, and redacted event state is bounded in-memory process state only.

**Testing**: pytest unit/contract/integration tests; Vitest component tests;
Playwright plus axe-core browser tests; wheel-install smoke test; external Codex
subscription acceptance recorded separately.

**Target Platform**: Windows 11 with Python 3.13 is the release gate. macOS and
Linux are best-effort beta. Modern Chromium, Firefox, and WebKit are browser targets.

**Project Type**: optional local web application inside the existing Python package,
with a nested frontend source tree and packaged static assets.

**Performance Goals**:

- first deterministic Command Room render in <= 2 seconds for the acceptance
  fixture on the release platform;
- first streamed agent event visible in <= 1 second after the bridge emits it;
- workspace refresh after a completed turn in <= 1 second for the fixture;
- event replay remains ordered for the configured in-memory retention window.

These are latency measurements, never readiness or quality scores.

**Constraints**:

- One resolved workspace per process; the browser cannot choose a filesystem path.
- Loopback only, OS-assigned port, ephemeral bootstrap token, HttpOnly session
  cookie, strict same-origin checks, and no remote browser assets.
- Read-only questions start read-only; write scope is explicit and cannot cross a
  readiness hard stop.
- No credential access, persistence, display, or API-key fallback.
- Provider messages are normalized and redacted before browser delivery; hidden
  reasoning is never exposed.
- Base installs retain only their current dependencies; web dependencies remain
  lazy and optional.
- C086 and all pharmacy-specific content remain examples, never product schema.
- No implementation until FR-036 is satisfied.

**Scale/Scope**: one active workspace; tens to low hundreds of tables; one local
analyst; one Codex process; one active turn per thread; bounded event buffers. This
feature is not a multi-user server.

## Constitution Check

*GATE: evaluated before research and re-evaluated after contracts.*

| Principle | Bearing on this feature | Verdict |
|---|---|---|
| **I. Agent-First, Gate-Enforced** | Natural-language agent launch is primary. Studio calls existing gates and presents their result; the browser does not replace them. | Pass |
| **II. Depend, Never Fork** | Readiness and next-action projections are imported from existing services. Provider details are isolated behind `AgentBridge`; no Seshat logic is copied into TypeScript. | Pass |
| **III. Medallion, Gold-Only** | Studio visualizes the seven stages and cannot unlock a forbidden later stage. It adds no data-source or Power BI execution path. | Pass |
| **IV. Source Mapping Before Silver** | Forbidden scope is computed from current readiness; a technical approval cannot permit Silver work before Mapping is cleared. | Pass |
| **V. Agent Stops at Judgment Calls** | Foundation prepares business decisions but cannot record or self-grant them. Technical tool consent is explicitly a separate authority. | Pass |
| **VI. Defaults Then Deviations** | Studio displays existing defaults and deviations; it invents none. | Pass |
| **VII. C086 Is An Example** | API types and fixtures are domain-neutral. No pharmacy schema enters the frontend contract. | Pass |
| **VIII. Static-First Governance** | Deterministic views work without a live DB or agent. A green static check remains necessary but not proof of live correctness. | Pass |
| **IX. Secrets and Reproducibility** | Tokens and credential-shaped data are redacted. Static assets are local and wheel contents are reproducible. | Pass |
| **Readiness spine** | Studio is a projection and orchestration surface. It does not add a stage or alternate state engine. | Pass |
| **No fabricated score** | Only categorical states, facts, counts, and measured latency are shown. | Pass |

**Result: no constitutional exception.** FR-036 remains an external implementation
gate and is not satisfied by this document.

## Project Structure

### Documentation (this feature)

```text
specs/139-seshat-studio-foundation/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- tasks.md
|-- checklists/
|   `-- requirements.md
`-- contracts/
    |-- studio-api.yaml
    |-- agent-bridge.md
    `-- security-boundary.md
```

### Source Code (repository root)

```text
src/seshat/studio/
|-- __init__.py
|-- contracts.py
|-- errors.py
|-- workspace.py
|-- redaction.py
|-- events.py
|-- sessions.py
|-- security.py
|-- app.py
|-- launcher.py
|-- agents/
|   |-- __init__.py
|   |-- base.py
|   |-- fake.py
|   |-- jsonrpc.py
|   `-- codex.py
`-- static/                    # generated frontend output, shipped in wheel

studio-ui/
|-- package.json
|-- package-lock.json
|-- tsconfig.json
|-- vite.config.ts
|-- index.html
`-- src/
    |-- main.tsx
    |-- app.tsx
    |-- api.ts
    |-- types.ts
    |-- styles.css
    |-- components/
    `-- test/

.claude/skills/seshat-studio/
`-- SKILL.md

tests/
|-- unit/studio/
|-- integration/studio/
|-- contract/test_studio_package_contract.py
|-- contract/test_studio_capability.py
`-- browser/test_studio_command_room.py
```

**Structure Decision**: `seshat.studio` is outside `seshat.cli` and
`seshat.rules`, so optional networking imports never enter the static checker path
guarded by B1. The frontend has one source tree; only its generated `dist` content
is copied into `src/seshat/studio/static`. Browser components consume typed API
contracts and contain no readiness derivation.

## Component Boundaries

```text
Browser UI
   | same-origin HTTP + SSE
   v
Studio API ----> WorkspaceProjectionService ----> existing Seshat services
   |
   `----------> AgentBridge ----> Codex app-server (stdio JSON-RPC)

All browser-bound errors/events pass through redaction.
All post-turn state is re-read from committed artifacts and gates.
```

- `workspace.py` adapts existing Python projections into `WorkspaceSnapshot`; it
  does not parse readiness YAML independently.
- `sessions.py` owns bounded runtime state and SSE replay sequence numbers.
- `security.py` owns bootstrap-token exchange, session cookies, origin checks, and
  loopback enforcement.
- `agents/base.py` owns only stable Studio protocol types.
- `agents/codex.py` owns Codex protocol compatibility and process lifecycle.
- `app.py` composes dependencies and exposes only the versioned API contract.
- `launcher.py` resolves and pins the workspace before starting the server.

## Delivery Sequence

1. Establish packaging, optional-dependency, launcher, and security contracts.
2. Build the deterministic workspace projection and Command Room.
3. Build stable event storage, SSE replay, and the fake agent bridge.
4. Add Codex app-server JSON-RPC/process adaptation and health states.
5. Add plain-language turns, interruption, technical tool approvals, and
   readiness forbidden-scope enforcement.
6. Add natural-language launch capability and generated bundle reconciliation.
7. Complete accessibility, wheel, regression, and external acceptance evidence.

Each slice starts with a failing test and ends with a focused commit. Detailed
steps live in `docs/superpowers/plans/2026-08-03-seshat-studio-foundation.md`.

## Verification Gates

- Unit and component tests pass without Codex, network, database, or Node at
  runtime.
- The fake-bridge browser journey covers healthy, unavailable, paused approval,
  failure, replay, and interruption states.
- Static checker import guards prove base installs do not import web dependencies.
- Built wheel contains prebuilt assets and opens without a Node executable.
- Generated Codex and Claude bundles reconcile byte-for-byte from canonical sources.
- Existing static dashboard tests remain unchanged and green.
- External acceptance names Python, Studio, and Codex versions; confirms subscription
  authentication; and records that Studio received no API key.

## Implementation Gate

Planning and review may continue while spec 138 is active. Production code,
frontend source, dependency edits, capability edits, and generated bundle changes
may begin only after both conditions are true:

1. a named human ratifies this exact spec and plan; and
2. `AGENTS.md` points to this plan as the repository's only active Spec Kit plan.

The implementing agent records that evidence; it never infers or self-grants it.
