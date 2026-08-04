# Seshat Studio program design

**Date:** 2026-08-03

**Status:** product direction and architecture approved in brainstorming; written-design review and named-human Spec Kit ratification pending

**Working branch:** `studio` in `.worktrees/studio`
**Proposed delivery:** three sequential specs, beginning with spec 139 after the active spec 138 fence is cleared

## Purpose

Seshat Studio is a professional localhost operations console for analysts who want
to work with Seshat BI, AI, and agents without learning command names, skill names,
or terminal workflows. It turns the existing agent-first product into a guided
visual workspace without replacing the agent or creating a second source of
readiness truth.

The primary user is an analyst wearing both analytical and technical hats. A
secondary user is the analyst's client or business owner, who needs plain-language
progress, evidence, deliverables, and clearly framed decisions without operational
noise.

Studio answers five questions at all times:

1. What is Seshat working on?
2. What is the next allowed action?
3. What is blocked, and why?
4. What evidence supports the recommendation?
5. What requires a named human decision?

## Locked product decisions

| Decision | Choice |
|---|---|
| Workspace scope | One selected Seshat repository per running Studio instance |
| Primary UX | Hybrid: Guided Command Room for orientation, Analyst Workbench for detailed work |
| Primary user | Analyst who should not need commands or internal Seshat vocabulary |
| Client experience | Simplified Client Review generated from the same committed evidence |
| AI connection | Codex-first through the locally installed Codex app-server and existing ChatGPT/Codex subscription authentication |
| Separate API billing | Not required, never enabled as a hidden fallback |
| Claude Code | Marketplace and native handoff remain supported; no embedded subscription-credential bridge in this program without a separately reviewed compliant path |
| Hosting | True localhost service bound only to loopback, protected by an ephemeral session token |
| Truth source | Existing Seshat Python projections and committed workspace artifacts |
| Human decisions | Studio may transcribe an explicit named-human decision through the governed agent workflow after evidence and the exact diff are reviewed |
| Delivery shape | Three sequential specs, never concurrent implementation stories |

> **Amended 2026-08-04 (owner).** Two rows above are superseded by the owner amendment
> recorded in `specs/139-seshat-studio-foundation/spec.md`. "Separate API billing: not
> required, never enabled as a hidden fallback" now forbids only a SILENT or automatic
> switch to billed access; an explicitly operator-configured API-key or access-token
> bridge is permitted as a clearly labelled alternate mode (FR-013 / FR-013a).
> Subscription sign-in remains the default and the only certified path. The reason is
> recorded in that spec's "Provider authentication compliance -- OPEN QUESTION" section:
> the Codex subscription path is NOT established as compliant, OpenAI's own
> documentation directs programmatic use to API keys, and OpenAI declined to clarify the
> question when asked directly. This table is kept as the record of what was ratified on
> 2026-08-03, not as current state.

## User experience

### Command Room

The home surface is agent-led but not chat-only. It presents:

- the current table or subject area;
- the seven-stage journey with the current stage clearly marked;
- one recommended mission in plain language;
- why that mission matters to downstream analytics;
- pending human decisions and their consequences;
- a persistent plain-language Seshat composer;
- workspace health and technical details behind progressive disclosure.

The analyst never chooses a CLI verb. Studio recomputes the current state and
offers only actions allowed by that state. Forbidden later-stage work remains
visible as locked with the concrete prerequisite, not hidden or silently skipped.

### Analyst Workbench

The detailed surface is canvas-led. It places related evidence and decisions side
by side:

- source profile facts and mapping proposals;
- metric contracts, bindings, and lineage;
- artifact previews and exact repository diffs;
- decision queue with required authority;
- stage evidence and blockers;
- contextual Seshat conversation attached to the active table, artifact, or
  decision.

The workbench uses progressive disclosure. Business meaning is first, evidence is
one action away, and raw files, logs, tool events, and technical diagnostics appear
only when requested or when a failure makes them relevant.

### Review Inbox

The inbox contains only judgments a human must make. Every item shows:

- the question in business language;
- the recommendation and its evidence;
- alternatives and downstream consequences;
- the required authority or owner role;
- the exact proposed artifact change;
- the current workspace revision used to prepare the proposal.

To record a decision, the user supplies or confirms the signer's name, chooses the
answer, reviews the diff, and explicitly confirms ownership of the decision. Studio
then asks the agent to transcribe the answer through the existing governed workflow.
It never writes an approval receipt directly from browser logic and never converts
an agent recommendation into approval.

### Operations

Operations is secondary to analyst work. It exposes:

- Codex connection and authentication health without reading or displaying the
  credential;
- current and recent Studio runs;
- normalized agent events, tool activity, file changes, and approval requests;
- optional dependency and live-boundary diagnostics;
- capability, pack, MCP, and adapter availability;
- failures with a plain-language recovery action;
- raw technical detail on demand.

### Client Review

Client Review is read-only and uses plain business language. It shows delivery
scope, current progress, decisions awaiting the client, evidence supporting the
result, validation boundaries, and available deliverables. It exposes no secrets,
raw prompts, reasoning traces, terminal commands, or internal capability names.
It is printable and exportable as a self-contained review document in the final
program slice.

## Architecture

Studio is a dedicated product module and adapter, not a new branch of the static
Seshat CLI. The end-user opens it by asking a supported agent to "Open Seshat
Studio." A technical `seshat-studio` launcher exists as a fallback and packaging
contract, not as the primary product experience.

```text
Browser on 127.0.0.1
  Command Room | Workbench | Review Inbox | Operations | Client Review
                 |
                 v
Seshat Studio local ASGI host
  Workspace API | SSE event stream | safety coordinator | static assets
          |                                      |
          v                                      v
Existing Seshat Python services          Codex bridge over stdio
  readiness, next action, blockers,        codex app-server
  evidence, approvals, capabilities              |
          |                                      v
          +------------------------- Seshat skills and bundled MCP
                                   existing Codex subscription auth
```

### Package boundary

The backend lives in a focused `seshat.studio` package and is launched by a
dedicated `seshat-studio` entry point. The existing `seshat` and `retail` CLI
import chains remain static. No ASGI, HTTP-server, browser-host, or Codex-client
import is added at module scope under `src/seshat/cli/` or `src/seshat/rules/`.

Studio ships behind an optional `studio` Python extra. The wheel contains the
prebuilt frontend, so end users need the Python package and a browser, not Node.js.
Node.js is development-only for the frontend build.

### Backend

The backend is Python 3.13, FastAPI, and Uvicorn. It binds to `127.0.0.1` on an
available port and refuses a non-loopback bind in v1. On startup it generates a
high-entropy session token, opens a tokenized URL, exchanges the token for an
HttpOnly SameSite cookie, removes the token from browser history, and requires
same-origin requests thereafter.

The launcher pins one resolved workspace root for the process lifetime. API
requests never accept arbitrary repository roots or filesystem paths. Evidence
and artifact references are resolved through the existing within-workspace path
guards.

The backend reads state by calling existing Python services directly. It does not
shell out to Seshat CLI commands and does not duplicate readiness derivation.
Initial read operations wrap the shipped governor service and existing projection
builders; later endpoints add typed presentation projections without changing
their authority.

### Frontend

The frontend is React and TypeScript built with Vite. It uses a restrained,
daylight product theme with Seshat's ink, warm gold, and muted green roles. The UI
must meet WCAG 2.2 AA for keyboard operation, focus visibility, contrast, status
communication, and reduced motion. Status is always expressed by text and shape,
never color alone.

The application has two responsive desktop layouts rather than one universal
screen:

- Command Room uses persistent navigation, mission focus, visible journey, a
  decision inspector, and the agent composer.
- Workbench uses top navigation, a larger evidence canvas, and a persistent review
  queue.

At narrow widths the inspector becomes an inline drawer. Mobile authoring is out
of scope, but review and status remain readable.

### Codex bridge

Studio starts `codex app-server` as a child process using its default stdio JSONL
transport. The child reuses the user's cached Codex authentication. Studio never
reads, copies, serializes, or displays Codex credentials.

The bridge initializes once, starts or resumes a thread scoped to the pinned
workspace, starts turns, consumes streamed notifications, and maps app-server
approval requests into Studio review controls. Studio does not use the
experimental Codex WebSocket listener.

The bridge normalizes version-specific Codex messages behind a narrow internal
interface:

```python
class AgentBridge(Protocol):
    def health(self) -> AgentHealth: ...
    async def start_thread(self, workspace: Path) -> ThreadRef: ...
    async def start_turn(self, thread_id: str, request: AgentRequest) -> None: ...
    async def respond_to_approval(
        self, thread_id: str, approval_id: str, decision: ApprovalDecision
    ) -> None: ...
    async def interrupt(self, thread_id: str) -> None: ...
    def events(self, thread_id: str) -> AsyncIterator[StudioEvent]: ...
```

Production uses `CodexAppServerBridge`; tests use `FakeAgentBridge`. An unavailable,
signed-out, incompatible, quota-limited, or crashed Codex process is a typed health
state, never a traceback and never a trigger for API-key billing.

### Browser API

The browser API is versioned under `/api/v1` and returns typed JSON envelopes.
Foundation endpoints are:

- `GET /bootstrap`: workspace identity, Studio version, session capabilities, and
  agent health;
- `GET /workspace`: readiness summary, next allowed action, global blockers, and
  pending decision count;
- `GET /tables` and `GET /tables/{table_id}`: table journey and evidence;
- `GET /decisions`: prepared review items only;
- `POST /agent/threads` and `POST /agent/threads/{thread_id}/turns`: plain-language
  agent work;
- `GET /agent/threads/{thread_id}/events`: Server-Sent Events of normalized
  `StudioEvent` objects;
- `POST /agent/threads/{thread_id}/approvals/{approval_id}`: response to a Codex
  tool approval request;
- `GET /health`: local service and adapter diagnostics.

The governed-workbench slice adds proposal preview and confirmation endpoints.
Every preview returns a `proposal_hash` and `workspace_revision`. Confirmation
requires both values, the decision answer, the signer's name, and an explicit
ownership acknowledgment. Stale proposals return a conflict and must be reviewed
again.

### Event model

Studio events have a stable envelope independent of Codex wire versions:

```text
event_id, thread_id, sequence, event_type, occurred_at,
summary, detail, status, approval_request, file_changes, error
```

The public event types are `thread_started`, `turn_started`, `agent_message`,
`plan_updated`, `tool_started`, `tool_completed`, `file_change_proposed`,
`approval_required`, `turn_completed`, `turn_failed`, and `connection_state`.
Reasoning internals and secret-bearing environment data are never sent to the
browser.

### State and persistence

Committed workspace artifacts remain the only durable source of readiness truth.
Studio has no database in v1.

- The browser holds view state only.
- Codex owns conversation history through its normal local store.
- Studio keeps current process events in memory for the Foundation slice.
- The Operations slice may write redacted run indexes to a machine-local,
  git-ignored Studio runtime directory; those records are diagnostic evidence,
  never readiness authority.
- Signer display-name preference may be remembered locally, but every decision
  still requires explicit confirmation and writes the name into the canonical
  decision artifact.

## Governed data flows

### Read flow

1. Resolve and validate the single workspace at launch.
2. Build readiness, next-action, blocker, approval, and evidence projections from
   existing Seshat services.
3. Add presentation-only labels and links.
4. Return the projection with a workspace revision digest.
5. Refresh after filesystem changes or completed agent turns.

Studio never turns a missing artifact into a pass, a deferred live check into a
success, or categorical state into a numeric health score.

### Agent turn

1. The analyst submits plain-language intent from the current UI context.
2. Studio attaches structured workspace, table, stage, selected evidence, allowed
   scope, and forbidden scope.
3. The Codex bridge starts a turn with workspace-write permissions only when the
   requested mission requires it; read-only is the default.
4. Studio streams normalized events.
5. Codex approval requests pause the turn and appear as explicit UI requests.
6. On completion, Studio discards any agent claim about readiness and recomputes
   state from committed artifacts and gates.

### Named-human decision

1. Studio prepares a decision review from committed evidence.
2. The analyst reviews alternatives, consequences, and the exact proposed diff.
3. The analyst supplies a signer name and explicit ownership acknowledgment.
4. Studio verifies the proposal hash and workspace revision have not changed.
5. The agent invokes the responsible official workflow skill and transcribes the
   answer into the canonical artifact.
6. Studio runs the applicable static checks and rereads readiness.
7. A stage changes only if the existing canonical workflow and evidence allow it.

### Live and external boundaries

Studio may display live database readiness and setup guidance, but it never fakes a
live result. Database-backed operations still require the existing optional driver
extra and a DSN in the gitignored `.env`. Power BI execution remains disabled until
its separate execution-adapter feature and readiness gate permit it.

## Failure behavior

- **No Codex executable:** open in useful read-only mode; explain how to connect a
  supported agent without showing internal command names on the primary screen.
- **Codex signed out:** show a connection action that launches the official login
  flow; Studio never asks for or stores the credential.
- **Quota exhausted:** preserve the workspace and draft input, display the provider
  reset information if reported, and offer read-only work. Never switch to API
  billing.
- **Codex protocol mismatch:** mark the adapter incompatible, name detected and
  supported versions, and leave deterministic Studio views operational.
- **Agent child crashes:** end the active turn as failed, retain redacted events,
  recompute workspace state, and offer restart.
- **Browser disconnects:** the turn continues in the backend; reconnect resumes the
  SSE stream from the last event id while the in-memory event buffer exists.
- **Workspace changes during review:** reject confirmation with a conflict and
  regenerate the proposal.
- **Malformed committed artifact:** render an input defect with its path and route
  to the canonical repair surface; never skip it silently.
- **Output contains a possible secret:** redact before browser delivery and mark the
  event as redacted.
- **Host or port exposure request:** refuse non-loopback binding in v1.
- **Write or gate failure:** show the actual failed step and repository diff; never
  claim completion or advance readiness.

## Delivery sequence

Seshat Studio is a program, not one oversized implementation story. Each spec is
independently useful and becomes the sole active implementation before work begins.

### Proposed spec 139: Studio Foundation

- optional Studio package extra and dedicated launcher;
- loopback host, token exchange, bundled frontend, and workspace pinning;
- read-only Workspace API over existing projections;
- Command Room and seven-stage journey;
- Codex app-server bridge, plain-language turns, SSE events, and tool approvals;
- read-only degradation when Codex is absent or unavailable;
- marketplace skill that lets the analyst ask the agent to open Studio.

Independent success: an analyst can ask Codex to open Studio, see the truthful next
action for one workspace, ask a plain-language question, watch the governed turn,
and never use a Seshat command or API key.

### Proposed spec 140: Governed Analyst Workbench

- mapping, metric, lineage, evidence, and artifact-review canvases;
- prepared decision inbox;
- proposal hashes and workspace revision checks;
- exact diff preview;
- named-human decision transcription through the responsible official skill;
- post-write checks and readiness recomputation.

Independent success: an analyst can review one real blocking decision, understand
its evidence and impact, record it explicitly under their name, and see the verified
workspace state update without Studio self-approving anything.

### Proposed spec 141: Operations and Client Review

- adapter, dependency, capability, pack, MCP, and live-boundary diagnostics;
- redacted run history and recovery controls;
- client-facing review surface and self-contained export;
- responsive and accessibility hardening across all Studio surfaces.

Independent success: an analyst can diagnose a failed run and produce a client-safe
review package from the same committed evidence without exposing commands, secrets,
or agent internals.

## Testing strategy

### Unit and contract

- every API projection preserves status, evidence, blockers, required authority,
  next action, and forbidden scope from the existing service;
- path resolution cannot escape the pinned workspace;
- session token exchange, cookie enforcement, origin enforcement, and non-loopback
  refusal;
- complete Codex message normalization using recorded protocol fixtures;
- quota, signed-out, missing binary, crash, timeout, and protocol-mismatch health
  states;
- secret redaction before event delivery;
- workspace revision and proposal-hash conflict handling;
- decision confirmation rejects a missing signer, missing acknowledgment, stale
  proposal, or unsupported authority;
- no UI or backend code writes readiness directly or emits a numeric readiness
  score.

### Integration

- ASGI tests with `FakeAgentBridge` cover thread start, SSE replay, approval pause,
  approval response, file-change proposal, completion, and failure;
- a temporary git workspace proves truthful empty, blocked, warning, and pass states;
- one governed decision runs through preview, explicit named confirmation, fake
  agent transcription, static check, and recomputation;
- package tests prove the optional Studio extra and prebuilt frontend ship while
  the normal static import path remains dependency-light;
- B1 and the capability inventory remain green.

### Browser

- Playwright covers first arrival, Command Room, Workbench review, keyboard-only
  decision confirmation, reconnect, narrow review layout, and Client Review;
- accessibility checks cover landmarks, names, focus order, contrast, reduced
  motion, and text alternatives for every status;
- no remote asset, analytics, font, or script request occurs;
- no command name appears in the primary analyst journey unless technical detail is
  explicitly opened.

### External acceptance

- Codex acceptance runs on a machine with a supported Codex CLI and subscription
  login, because the current development shell does not expose a `codex` executable;
- acceptance proves app-server startup, existing-login reuse, streaming, approval
  round trip, interruption, quota degradation, and no API-key request;
- Claude Code acceptance covers marketplace launch and native handoff only.

## Governance and repository fit

- Studio Foundation may be specified while spec 138 remains active, but no Studio
  implementation begins until spec 138 is complete or formally parked, the Studio
  spec is named-human ratified, and the single active-plan marker points only to it.
- Studio is not a new readiness stage and does not weaken any existing stage gate.
- The local web host and Codex bridge are explicit adapter surfaces. They stay out
  of the static CLI import chain and declare their connectivity and authority.
- Studio does not create metrics, mappings, semantic logic, or dashboard designs.
  It presents proposals and routes explicit human answers to the existing official
  workflows.
- No real host, DSN, credential, auth token, or client data enters tracked files.
- The existing static `retail dashboard` remains a lightweight offline status
  export. Studio is a separate interactive product surface and does not silently
  change that command's behavior.
- The current `studio` worktree contains a narrow `.gitignore` addition for
  `.superpowers/brainstorm/`, preserving committed `.superpowers` reports while
  excluding generated visual-companion sessions.

## Explicit non-goals

- Multiple repositories in one Studio process.
- Remote hosting, LAN binding, multi-user accounts, SSO, or cloud synchronization.
- A new model provider, direct OpenAI API billing, or stored LLM API keys.
- Embedded Claude subscription execution without a separately reviewed compliant
  integration.
- Direct database administration, warehouse SQL execution before gates, or Power BI
  execution.
- A visual workflow graph that lets users bypass readiness order.
- Numeric readiness, health, confidence, or maturity scores.
- Mobile authoring and native desktop packaging in the first three specs.

## References

- `AGENTS.md` and `.specify/memory/constitution.md`: agent-first operation, hard
  stops, named-human judgment, and static/live boundaries.
- `docs/architecture/product-modules.md` and
  `docs/architecture/core-vs-modules-and-adapters.md`: authority and adapter
  classification.
- `src/seshat/governor/service.py`: existing transport-neutral read-only operations.
- `src/seshat/governor/mcp_server.py`: bundled MCP projection surface.
- `src/seshat/status_surface.py`, `src/seshat/agent_next.py`, and
  `src/seshat/approval_inbox.py`: authoritative presentation inputs.
- `docs/superpowers/specs/2026-07-19-localhost-status-dashboard-design.md`: existing
  static status view and the reason it remains separate.
- [Codex authentication and app-server manual](https://developers.openai.com/codex/codex-manual.md): subscription authentication and rich-client app-server surface.
- [Claude Code authentication](https://code.claude.com/docs/en/authentication) and
  [legal guidance](https://code.claude.com/docs/en/legal-and-compliance): native
  subscription use and the boundary on third-party credential routing.
