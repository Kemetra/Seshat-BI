# Phase 0 Research: Seshat Studio Foundation

**Feature**: 139-seshat-studio-foundation | **Date**: 2026-08-03

The design research resolved the product, packaging, authentication, transport,
security, and authority boundaries required to plan Foundation. Version-specific
external acceptance remains deliberately separate from architectural feasibility.

## R1 - Which user experience should Foundation optimize?

**Decision**: Use a contextual hybrid. The default is a plain-language Command
Room; evidence and decisions open into a denser Analyst Workbench; technical detail
is on demand; client review is a later simplified mode.

**Rationale**: The primary user is an analyst who works with agents but should not
need command names, skill names, protocol messages, or repository structure. A pure
chat hides governed state, while a pure dashboard cannot drive agent work. The
hybrid keeps readiness visible beside the conversation and uses progressive
disclosure for expert detail.

**Alternatives considered**:

- chat-first assistant: rejected because stage, blocker, evidence, and approval
  state become easy to miss;
- operations dashboard: rejected as the default because it exposes implementation
  detail before analyst intent;
- visual workflow canvas: deferred because it suggests users may reorder or bypass
  governed stages.

## R2 - How should the browser backend be packaged?

**Decision**: Add `fastapi` and `uvicorn[standard]` only to a `studio` optional
extra. Serve a prebuilt React/TypeScript application from `seshat.studio.static`.
Expose a dedicated `seshat-studio` entry point outside the existing CLI dispatcher.

**Rationale**: FastAPI provides typed HTTP/SSE contracts and clean dependency
injection. A dedicated package keeps networking imports out of the static checker
chain. Prebuilt assets mean an installed analyst needs Python and a browser, not a
Node toolchain.

**Alternatives considered**:

- add web dependencies to the base package: rejected because static governance is
  intentionally dependency-light;
- put `studio` under the current CLI parser: rejected because B1 protects that
  import path from module-scope networking dependencies;
- generate static HTML only: rejected because the existing dashboard already
  provides that and cannot stream or approve agent turns.

## R3 - How can Studio reuse a Codex subscription without an API key?

**Decision**: Start the official local `codex app-server` process and communicate
over stdio JSON-RPC. Let Codex own and cache ChatGPT subscription authentication.
Studio never opens, parses, copies, persists, or displays its credentials.

**Rationale**: The app-server is Codex's rich-client integration boundary and can
reuse existing CLI login. It supplies thread, turn, streaming, and approval events
without converting subscription use into separate API billing. The stable Studio
protocol insulates the UI from provider-version changes.

**Release posture**: The current official manual and `codex-cli 0.146.0` still
label the app-server command/protocol experimental. Foundation therefore ships the
Codex bridge as a version-gated beta integration: deterministic Studio views remain
fully available, the adapter declares healthy only inside an explicitly tested CLI
range after a successful handshake, and an unknown protocol fails as
`incompatible`. There is no API-key fallback and no claim of a provider stability
guarantee that OpenAI has not made.

**Alternatives considered**:

- OpenAI API key: rejected because the target user may have only a CLI subscription
  and FR-013 forbids a silent billing-path switch;
- shelling out to one noninteractive prompt per message: rejected because it loses
  durable thread state and structured approvals;
- experimental app-server WebSocket: rejected in favor of the documented local
  stdio boundary;
- reading Codex credential files: rejected as unnecessary and unsafe.

**Protocol audit (2026-08-03)**: `codex-cli 0.146.0` is installed and its own
`app-server generate-json-schema --experimental` command was used to inspect the
version-specific v2 contract. It confirms mandatory `initialize` then `initialized`,
stable `thread/start`, `turn/start`, `turn/interrupt`, account and rate-limit reads,
managed `chatgpt` login, streamed public item/turn events, and server-initiated
command/file approval requests. Foundation can remain entirely on the stable API;
it must not opt into `experimentalApi`.

A sanitized read-only process probe then completed the stable handshake and returned
a non-null `chatgpt` account plus a rate-limit response through the already managed
subscription login. The probe read or copied no credential and started no model
turn. See `evidence/codex-protocol-probe.md`.

**Residual acceptance**: record successful subscription login, protocol handshake,
and a streamed fake-safe question on the release platform. Protocol compatibility is
tested from sanitized, version-labelled fixtures before that run. The local schema
audit proves feasibility, not authenticated behavior.

## R4 - Should Claude Code be an embedded second provider in Foundation?

**Decision**: No. Claude Code may launch the deterministic site and provide a native
handoff, but Studio Foundation does not route individual Claude subscription
credentials or embed a Claude process bridge.

**Rationale**: Codex has the rich-client boundary required by this design. Current
Anthropic guidance distinguishes supported first-party subscription use from
third-party products routing subscription credentials. A provider-neutral internal
interface preserves future options without claiming unsupported equivalence.

**Alternative considered**: implement both providers now. Rejected because it
doubles a security-sensitive integration surface and risks an unsupported auth use.

## R5 - What is the correct local security boundary?

**Decision**: One pinned workspace and one loopback process. Bind only to
`127.0.0.1` on an OS-selected port. Put a high-entropy bootstrap token in the first
URL, exchange it once for an HttpOnly `SameSite=Strict` session cookie, immediately
remove it from history, and reject missing/foreign origins before endpoint logic.

**Rationale**: Localhost is reachable by other local browser pages and processes;
"local" is not authentication. Pinning the root before server startup removes an
entire arbitrary-path API class. Same-origin HTTP and SSE simplify browser security.

**Alternatives considered**:

- fixed unauthenticated localhost port: rejected because another local page could
  read or drive the service;
- browser-supplied workspace parameter: rejected because it creates path traversal
  and confused-deputy risk;
- store the token in local storage: rejected because JavaScript does not need it
  after exchange;
- TLS on loopback: deferred; it does not replace session and origin controls and
  adds certificate friction for a single-user local service.

## R6 - How should browser streaming and reconnect work?

**Decision**: Normalize provider events into a closed Studio event set and deliver
them through same-origin Server-Sent Events. Assign a monotonic sequence per thread
and support `Last-Event-ID` replay from a bounded in-memory buffer.

**Rationale**: The dominant flow is server-to-browser. SSE has native reconnect
semantics, works with normal HTTP security, and is simpler than a bidirectional
socket. Mutating actions remain explicit POST requests. Bounded memory matches the
single-process Foundation scope.

**Alternative considered**: WebSocket for all traffic. Rejected because it adds
protocol and CSRF/origin complexity without a v1 requirement.

## R7 - Where does authority live after an agent turn?

**Decision**: Existing committed artifacts, gate outputs, and Python projections
remain authoritative. On every completed, failed, or interrupted turn, Studio
recomputes the workspace snapshot and reports any narrative/state disagreement as
an input or agent defect.

**Rationale**: Agent messages are proposals and explanations, not readiness state.
This preserves the repository's state model and prevents the UI from becoming a
second run-state engine.

**Alternative considered**: optimistically update stages from agent events.
Rejected because a convincing message could visually bypass a failed gate.

## R8 - How are approvals divided?

**Decision**: Foundation supports technical tool consent only. It can show action,
target, reason, scope, and risk, and relay allow/deny to the agent bridge. It cannot
record grain, PII publish-safety, business rollup, sentinel/null, or other named-human
business decisions; it prepares a read-only decision summary for spec 140.

**Rationale**: Tool permission and business authority are different contracts.
Conflating them would let a generic "allow" self-grant a governed decision.

## R9 - What must work without external services?

**Decision**: All workspace views, security checks, UI states, event behavior, and
approval flows are accepted with deterministic fixtures and a fake bridge. Live DB
profiling remains governed by existing deferred mode. Real Codex is one explicit
external acceptance lane.

**Rationale**: CI must be reproducible and must not consume subscription quota or
fabricate live evidence. The release environment currently lacks Python and Codex,
so this separation is also operationally necessary.

## Source Record

- Local repository: constitution, readiness model, governor service, static
  dashboard, capability inventory, packaging metadata, and bundle exporter,
  inspected 2026-08-03.
- OpenAI Codex documentation/manual: ChatGPT subscription login, cached CLI
  authentication, and the app-server rich-client interface, checked 2026-08-03
  from the current official Codex App Server manual; version-specific protocol
  shapes were cross-checked against schemas generated by `codex-cli 0.146.0`.
- Anthropic Claude Code documentation and legal/commercial guidance: subscription
  authentication and third-party credential-routing boundary, checked 2026-08-03
  from official Anthropic material.

External facts are architecture inputs, not acceptance evidence. The release record
must re-check current official documentation and exact installed versions.
