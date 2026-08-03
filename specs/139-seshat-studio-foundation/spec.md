# Feature Specification: Seshat Studio Foundation

**Feature Branch**: `studio`

**Created**: 2026-08-03

**Status**: draft

**Input**: Build the first independently useful slice of Seshat Studio: a modern
localhost analyst console that opens from the Seshat agent, reads one workspace
truthfully, and runs plain-language Codex turns through the user's existing CLI
subscription without requiring commands or a separate API key.

## User Scenarios & Testing

### User Story 1 - Open a truthful Command Room (Priority: P1)

An analyst asks the Seshat agent to open Studio. The browser opens a local Command
Room for the current repository and immediately explains the current readiness
stage, blockers, evidence, pending decision count, and one next allowed action in
plain language.

**Why this priority**: This is the minimum product promise. It removes command and
skill-name knowledge while preserving the existing readiness authority.

**Independent Test**: Launch Studio against a fixture workspace containing one
passing table and one blocked table. Confirm the browser projection matches the
existing Seshat Python projections exactly and contains no fabricated score.

**Acceptance Scenarios**:

1. **Given** a valid Seshat workspace, **When** the analyst opens Studio, **Then**
   the service binds to loopback, opens a token-protected browser URL, and shows the
   workspace identity and truthful table journeys.
2. **Given** a table blocked at Mapping, **When** the Command Room renders, **Then**
   it names Mapping as current, shows the concrete blocker and evidence, offers the
   mapping action, and leaves Silver and later work locked.
3. **Given** a workspace with no onboarded tables, **When** Studio opens, **Then**
   it presents a useful first-arrival state and the existing onboarding route,
   without traceback, score, fake profile, or fake pass.
4. **Given** malformed committed readiness input, **When** Studio reads the
   workspace, **Then** it renders an input defect with its source path and never
   silently omits or upgrades it.

---

### User Story 2 - Ask Seshat without commands (Priority: P1)

An analyst asks a plain-language question in the Command Room. Studio connects to
the locally installed Codex app-server, reuses the existing Codex subscription
login, and streams the governed turn into the browser.

**Why this priority**: A status-only site already exists. The Foundation becomes a
new product only when the analyst can interact with the agent without terminal
knowledge.

**Independent Test**: Run the backend with a fake app-server fixture, submit "What
is blocking this table?", and verify the browser receives ordered turn, message,
tool, and completion events. Run external acceptance with a signed-in Codex CLI
and confirm no API key is requested or read.

**Acceptance Scenarios**:

1. **Given** a compatible authenticated Codex CLI, **When** the analyst submits a
   question, **Then** Studio starts a workspace-scoped thread and streams normalized
   events until completion.
2. **Given** a read-only question, **When** Studio starts the turn, **Then** it uses
   read-only sandbox scope and includes current stage, allowed action, forbidden
   scope, and selected table context.
3. **Given** the agent claims a stage advanced, **When** the turn completes,
   **Then** Studio ignores the claim and recomputes readiness from committed
   artifacts and gates.
4. **Given** a browser reconnect with a valid last event id, **When** the active
   process still retains that event, **Then** Studio replays subsequent events in
   order without duplicating completed events.

---

### User Story 3 - Review agent tool approvals safely (Priority: P2)

When Codex requests permission to run a command or change a file, Studio pauses the
turn and presents a specific technical approval request. The analyst can allow or
deny it without seeing provider protocol details.

**Why this priority**: Hiding commands must not mean hiding side effects. A visual
approval boundary is required before Studio can safely operate beyond read-only
questions.

**Independent Test**: Feed a recorded app-server approval request through the fake
bridge. Confirm the UI shows target, reason, scope, and risk; the turn stays paused;
and only the selected allow or deny response is sent back.

**Acceptance Scenarios**:

1. **Given** a tool approval request, **When** it arrives, **Then** Studio labels it
   as a technical permission, shows the proposed side effect, and pauses the turn.
2. **Given** the analyst denies the request, **When** Studio responds, **Then** the
   exact denial is sent to Codex and no browser code performs the side effect.
3. **Given** the request would cross a Seshat hard stop, **When** Studio evaluates
   current forbidden scope, **Then** Studio refuses it even if the user attempts to
   allow the technical tool permission.
4. **Given** a business judgment is required, **When** the agent asks for it,
   **Then** Studio creates a prepared decision item and stops; Foundation does not
   record a business approval.

---

### User Story 4 - Stay useful when the agent is unavailable (Priority: P2)

An analyst without an installed, signed-in, compatible, or available Codex CLI can
still inspect the workspace and understand exactly what is missing.

**Why this priority**: A local admin console must degrade honestly. Missing agent
access must not make deterministic Seshat state inaccessible.

**Independent Test**: Parameterize missing executable, signed-out, incompatible,
quota-limited, and crashed fake bridges. Confirm every state has a named recovery
action, read-only views remain functional, and no state triggers an API-key fallback.

**Acceptance Scenarios**:

1. **Given** no Codex executable, **When** Studio opens, **Then** workspace views
   work in read-only mode and agent controls explain that the connection is absent.
2. **Given** Codex is signed out, **When** the analyst selects Connect, **Then**
   Studio starts the official Codex login flow and never receives the credential.
3. **Given** quota is exhausted, **When** a turn fails with that state, **Then**
   Studio preserves draft input, shows reset information if Codex reported it, and
   offers deterministic read-only work.
4. **Given** the child process crashes, **When** Studio detects EOF, **Then** it
   marks the turn failed, redacts retained events, recomputes workspace state, and
   offers a restart.

---

### User Story 5 - Launch from shipped Seshat integrations (Priority: P3)

An analyst can say "Open Seshat Studio" in a supported installed Seshat bundle.
The agent routes to a shipped Studio skill that validates the workspace, starts the
local service, and opens the browser. A technical launcher remains available for
packaging verification and support.

**Why this priority**: The product is agent-first. Requiring the analyst to learn
`seshat-studio` would reproduce the problem Studio exists to solve.

**Independent Test**: Export clean Codex and Claude bundles, verify the Studio skill
ships as a consumer capability, and exercise the natural-language launch route in a
scratch workspace. Claude launches the deterministic Studio site but does not become
an embedded subscription bridge in this slice.

**Acceptance Scenarios**:

1. **Given** the Studio extra is installed, **When** the user asks Codex to open
   Studio, **Then** the shipped skill starts one instance for the resolved workspace
   and opens the protected URL.
2. **Given** the extra is missing, **When** the launch skill runs, **Then** it reports
   a named two-lane installation remedy without traceback.
3. **Given** an already-running healthy instance for the same workspace, **When**
   launch is requested again, **Then** the browser focuses or opens that instance
   rather than starting a competing writer.
4. **Given** Claude Code launches Studio, **When** the site opens, **Then** it offers
   deterministic workspace views and a native Claude handoff, but never routes
   Claude subscription credentials through Studio.

### Edge Cases

- The requested repository is not a Seshat workspace: refuse by resolved path and
  list the recognized workspace markers and onboarding action.
- The repository path contains spaces or non-ASCII characters: launch and static
  asset delivery remain correct on Windows.
- A second browser without the session token connects to the port: return 401 and
  no workspace data.
- A request carries a foreign `Origin` header: return 403 before endpoint logic.
- A URL or evidence reference escapes the pinned root: return an input-defect
  response without resolving outside the workspace.
- The selected table disappears between requests: return a stale-state conflict and
  refresh the workspace projection.
- Agent events arrive after interruption: keep their sequence but mark them ignored
  for active-state transitions.
- The frontend build is absent from an installed wheel: launcher fails with a named
  packaging defect rather than serving an empty page.
- The browser cannot be opened: print the complete tokenized loopback URL as the
  technical fallback.
- Port allocation races: retry with a fresh OS-assigned loopback port; never fall
  back to a fixed public bind.

## Requirements

### Functional Requirements

- **FR-001**: Studio MUST operate on exactly one resolved Seshat workspace per
  process and MUST NOT accept a workspace path from browser requests.
- **FR-002**: Studio MUST expose a dedicated `seshat-studio` launcher outside the
  existing `seshat`/`retail` CLI dispatch chain.
- **FR-003**: The launcher MUST bind only to `127.0.0.1` on an OS-assigned port in
  v1 and MUST refuse non-loopback binding.
- **FR-004**: Startup MUST generate an ephemeral high-entropy session token,
  exchange it for an HttpOnly SameSite cookie, remove it from browser history, and
  require same-origin requests after exchange.
- **FR-005**: Studio MUST serve a prebuilt React/TypeScript frontend bundled in the
  Python wheel; end users MUST NOT need Node.js.
- **FR-006**: The normal `seshat-bi` install MUST remain free of Studio web
  dependencies; FastAPI and Uvicorn MUST live in a `studio` optional extra.
- **FR-007**: Studio MUST use existing Seshat Python services for readiness, next
  action, blockers, evidence, approvals, and capability state and MUST NOT
  reimplement readiness derivation.
- **FR-008**: Every readiness status shown MUST preserve categorical status,
  evidence, blocking reasons, required authority, next action, and forbidden scope.
- **FR-009**: Studio MUST NOT emit a numeric readiness, health, confidence,
  completeness, or maturity score.
- **FR-010**: Studio MUST render malformed or unreadable committed inputs as named
  input defects and MUST NOT skip them silently.
- **FR-011**: Studio MUST connect to Codex through `codex app-server` over stdio,
  using the user's existing cached CLI authentication.
- **FR-012**: Studio MUST NOT read, copy, serialize, display, or persist Codex
  authentication credentials.
- **FR-013**: Studio MUST NOT request an OpenAI API key or fall back to API-key
  billing when subscription authentication is absent, limited, or exhausted.
- **FR-014**: The Codex integration MUST be hidden behind a version-tolerant
  `AgentBridge` protocol and a deterministic fake implementation for tests.
- **FR-015**: Studio MUST normalize provider events into the stable Studio event
  types declared in `data-model.md` and MUST NOT expose hidden reasoning content.
- **FR-016**: Browser event streaming MUST use same-origin Server-Sent Events with
  ordered sequence numbers and `Last-Event-ID` replay while retained in memory.
- **FR-017**: Read-only analyst questions MUST start in read-only sandbox scope.
- **FR-018**: A turn that needs workspace writes MUST expose its proposed scope and
  pass the existing readiness forbidden-scope check before Studio may ask for a
  technical approval.
- **FR-019**: Tool approval requests MUST pause the turn and MUST show action,
  target, reason, scope, and risk before the analyst may allow or deny them.
- **FR-020**: Browser code MUST never execute a tool or write an artifact directly;
  approvals are responses to the agent bridge only.
- **FR-021**: A technical approval MUST NOT override a Seshat readiness or
  named-human business-decision hard stop.
- **FR-022**: Foundation MUST prepare but MUST NOT record named-human business
  decisions; decision transcription belongs to the next governed-workbench spec.
- **FR-023**: After every completed, failed, or interrupted turn, Studio MUST
  recompute workspace state from committed artifacts and applicable gates rather
  than trust the agent's narrative claim.
- **FR-024**: Missing executable, signed-out, incompatible, quota-limited, crashed,
  and healthy agent states MUST be distinct and carry a recovery action.
- **FR-025**: Deterministic workspace views MUST remain available in every agent
  health state.
- **FR-026**: Studio MUST redact DSNs, passwords, tokens, authorization headers, and
  credential-shaped values before any agent event or error reaches the browser.
- **FR-027**: Studio MUST ship a `seshat-studio` consumer skill in both generated
  bundles and classify it through the canonical capability inventory and export
  pipeline.
- **FR-028**: The shipped skill MUST make natural-language launch primary and name
  the technical launcher only in troubleshooting detail.
- **FR-029**: Claude Code launch MUST remain a deterministic-site and native-handoff
  integration; Foundation MUST NOT embed or route Claude subscription credentials.
- **FR-030**: Studio MUST preserve the existing static `retail dashboard` behavior
  unchanged.
- **FR-031**: The frontend MUST meet WCAG 2.2 AA for keyboard navigation, focus,
  contrast, accessible names, reduced motion, and non-color status communication.
- **FR-032**: The frontend MUST make command names, skill names, protocol messages,
  and raw file paths absent from the primary analyst journey unless technical detail
  is explicitly opened.
- **FR-033**: Studio MUST load no remote fonts, scripts, images, analytics, or other
  browser assets.
- **FR-034**: Studio MUST expose typed `/api/v1` bootstrap, workspace, table,
  decision-summary, agent-thread, event-stream, tool-approval, and health contracts.
- **FR-035**: Studio MUST not introduce a database; committed artifacts remain the
  durable truth and current process events remain in memory in Foundation.
- **FR-036**: Foundation implementation MUST NOT begin until this spec is
  named-human ratified and is the sole active Spec Kit plan.

### Key Entities

- **StudioSession**: One loopback server process, pinned workspace, ephemeral
  browser session, and current agent bridge.
- **WorkspaceSnapshot**: Presentation projection of current committed readiness,
  next action, blockers, evidence, and decision count plus a revision digest.
- **TableJourney**: One table's ordered seven-stage categorical state and evidence.
- **AgentHealth**: One of healthy, missing, signed_out, incompatible,
  quota_limited, crashed, or disabled, with a recovery action.
- **AgentThread**: Workspace-scoped Codex conversation reference.
- **StudioEvent**: Stable normalized event delivered to the browser in sequence.
- **ToolApprovalRequest**: Paused technical permission request with side-effect
  summary; it is not a business approval.
- **PreparedDecisionSummary**: Read-only pointer to a human judgment that remains
  unrecorded in Foundation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A first-time analyst with the Studio extra and authenticated Codex
  can ask the agent to open Studio and reach the Command Room without typing or
  copying a command.
- **SC-002**: For the acceptance fixture, every table stage status, evidence entry,
  blocker, and next action shown by Studio equals the existing Python projection.
- **SC-003**: A plain-language question produces an ordered streamed turn with a
  visible final result using subscription authentication and no API-key prompt.
- **SC-004**: All seven agent health states retain functional deterministic
  workspace views and display a distinct recovery action.
- **SC-005**: A technical approval remains paused until an explicit allow or deny,
  and a denied request produces no repository change.
- **SC-006**: Attempts to connect without a valid session, from a foreign origin,
  to a non-loopback host, or to a path outside the pinned workspace disclose no
  workspace content.
- **SC-007**: Automated browser accessibility checks report no critical or serious
  WCAG violations on Command Room, empty state, blocked state, and approval state.
- **SC-008**: The installed wheel opens Studio with Python and a browser only; no
  Node executable or remote browser asset is required at runtime.
- **SC-009**: Static governance, bundle reconciliation, package contracts, and the
  existing dashboard tests remain green after Studio is added.
- **SC-010**: External Codex acceptance names the CLI version, authentication method
  as subscription, app-server protocol result, and confirms no API credential was
  supplied to Studio.

## Assumptions

- The first fully interactive provider is Codex. Provider neutrality exists at the
  internal bridge boundary, not as multiple v1 implementations.
- Codex app-server stdio is the supported rich-client integration. Its experimental
  WebSocket transport is not used.
- The user has authority to work in the selected local repository but still must
  confirm every technical side effect and every named-human business decision at its
  existing boundary.
- Python 3.13 or newer is required. Node 20 or newer is development-only.
- The current development shell lacks both Python and a `codex` executable, so unit,
  contract, fake-bridge integration, and frontend work can be planned here, while
  live acceptance requires an environment that provides those prerequisites.
- The existing active spec 138 fence remains unchanged while this package is draft.
