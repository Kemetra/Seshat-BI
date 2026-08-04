# Seshat Studio Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a secure localhost Command Room that shows one Seshat workspace's
governed truth and streams interactive Codex turns through the user's existing CLI
subscription without commands or a separate API key.

**Architecture:** A dedicated optional `seshat.studio` FastAPI package adapts existing
Seshat projections and a provider-neutral `AgentBridge` into a same-origin HTTP/SSE
API. A React/TypeScript client renders a contextual hybrid Command Room. Production
uses Codex app-server over stdio; tests use a deterministic fake. Committed artifacts
and gates remain authoritative, while sessions and redacted events live only in
bounded process memory.

**Tech Stack:** Python 3.13, FastAPI, Uvicorn, React, TypeScript, Vite, Vitest,
Testing Library, Playwright, axe-core, pytest, Hatchling, Codex app-server stdio
JSON-RPC.

**Spec:** `specs/139-seshat-studio-foundation/`

## Global Constraints

- Do not begin Task 1 until a named human ratifies the exact spec/plan package and
  `AGENTS.md` points to spec 139 as the sole active implementation plan.
- Preserve all seven readiness stages and existing projection authority. Never infer
  stage movement from agent prose.
- Never self-grant grain, PII publish-safety, business rollup, sentinel/null, or any
  other named-human decision.
- A technical tool approval cannot override readiness forbidden scope.
- Base `seshat-bi` keeps its current dependency floor; Studio web dependencies are
  optional and lazily imported outside `seshat.cli` and `seshat.rules`.
- Codex owns subscription login. Studio reads no credentials and never requests or
  falls back to an API key.
- One resolved workspace per process, loopback only, OS-assigned port, authenticated
  same-origin browser requests, no arbitrary-path API, and no remote browser assets.
- Redact before buffering, logging, exception serialization, or browser delivery.
- Foundation records no durable Studio state and exposes no business-decision
  mutation route.
- The existing static `retail dashboard` remains unchanged.
- Domain-neutral fixtures only; C086 is not a schema.
- Python functions have type annotations; immutable cross-component dataclasses;
  focused files; ASCII-safe terminal output; no secrets in committed fixtures.
- Every implementation task follows RED -> GREEN -> focused regression -> commit.
- Use scope-free commit subjects such as `feat: add Studio session boundary`.

## File Structure

```text
src/seshat/studio/
  __init__.py
  contracts.py
  errors.py
  redaction.py
  workspace.py
  events.py
  sessions.py
  security.py
  app.py
  launcher.py
  agents/__init__.py
  agents/base.py
  agents/fake.py
  agents/jsonrpc.py
  agents/codex.py
  static/<built frontend>

studio-ui/
  package.json
  package-lock.json
  tsconfig.json
  vite.config.ts
  index.html
  src/main.tsx
  src/app.tsx
  src/api.ts
  src/types.ts
  src/styles.css
  src/components/*.tsx
  src/test/*.test.tsx

tests/unit/studio/
tests/integration/studio/
tests/fixtures/studio/
tests/contract/test_studio_package_contract.py
tests/contract/test_studio_capability.py
tests/browser/test_studio_command_room.py
```

## Task 0: Satisfy the Implementation Fence

**Files:**
- Modify: `AGENTS.md` only after named-human direction
- Modify: `specs/139-seshat-studio-foundation/spec.md`
- Modify: `specs/139-seshat-studio-foundation/plan.md`
- Modify: `specs/139-seshat-studio-foundation/checklists/requirements.md`
- Test: active Spec Kit marker contract located by
  `tests/contract/test_active_spec_kit_markers.py` or current equivalent

- [ ] **Step 1: Record the human action exactly**

Transcribe the ratifier's name, date, and explicit scope into spec and plan. Do not
convert a general implementation instruction into ratification.

- [ ] **Step 2: Move the single active fence**

Confirm spec 138 is complete or formally parked. Change the one pointer in
`AGENTS.md` to `specs/139-seshat-studio-foundation/plan.md`; do not add a second
pointer.

- [ ] **Step 3: Verify the marker and checklist**

Run the exact active-marker contract test and confirm the two governance checklist
items can now be checked truthfully.

- [ ] **Step 4: Commit**

```powershell
git add AGENTS.md specs\139-seshat-studio-foundation
git -c commit.gpgsign=false commit -m "docs: ratify Seshat Studio Foundation"
```

## Task 1: Establish Package Isolation and the Dedicated Launcher

**Files:**
- Modify: `pyproject.toml`
- Create: `src/seshat/studio/__init__.py`
- Create: `src/seshat/studio/errors.py`
- Create: `src/seshat/studio/launcher.py`
- Create: `tests/contract/test_studio_package_contract.py`
- Modify: current CLI import-guard test that owns B1/B3 coverage

**Interfaces:**
- console script: `seshat-studio = "seshat.studio.launcher:main"`
- extra: `studio = ["fastapi>=0.116,<1", "uvicorn[standard]>=0.35,<1"]`
- `StudioDependencyError` with the exact two-lane remedy:
  `pipx inject seshat-bi "seshat-bi[studio]"` and
  `pip install "seshat-bi[studio]"`
- `main(argv: Sequence[str] | None = None) -> int`

- [ ] **Step 1: Write failing package-contract tests**

Assert the script and extra exist, importing `seshat`, `seshat.cli`, and
`seshat.rules` does not import FastAPI/Uvicorn, and a simulated absent extra returns
exit 2 with both install remedies and no traceback.

- [ ] **Step 2: Run RED**

```powershell
py -3.13 -m pytest tests\contract\test_studio_package_contract.py -q
```

Expected: failures for absent entry point, extra, and package.

- [ ] **Step 3: Implement the smallest lazy launcher**

Add the package and entry point. Parse only technical support options:
`--repo PATH`, `--no-browser`, and `--agent {codex,fake,disabled}`. Resolve the
workspace before lazily importing `seshat.studio.app`. Do not add `seshat studio` to
the existing parser.

- [ ] **Step 4: Run GREEN and import guards**

Run the package contract plus the repository's B1/B3 import guard tests.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml src\seshat\studio tests\contract\test_studio_package_contract.py
git -c commit.gpgsign=false commit -m "feat: add isolated Studio launcher"
```

## Task 2: Define Immutable Contracts and Redaction

**Files:**
- Create: `src/seshat/studio/contracts.py`
- Create: `src/seshat/studio/redaction.py`
- Create: `tests/unit/studio/test_contracts.py`
- Create: `tests/unit/studio/test_redaction.py`

**Interfaces:**
- closed enums and frozen dataclasses exactly matching `data-model.md`
- `redact_text(value: str) -> str`
- `redact_value(value: object) -> object`
- `safe_relative_ref(root: Path, raw: str) -> str`
- `RedactionFailure` converts unsafe/unserializable input to a withheld message

- [ ] **Step 1: Write RED tests**

Cover DSNs with embedded passwords, bearer/basic authorization, API keys, cookies,
token assignments, credential URLs, multiline environment output, absolute Windows
and POSIX paths, non-secret words containing `token`, nested objects, and values whose
string conversion raises.

- [ ] **Step 2: Run RED**

```powershell
py -3.13 -m pytest tests\unit\studio\test_contracts.py tests\unit\studio\test_redaction.py -q
```

- [ ] **Step 3: Implement closed immutable models and fail-closed redaction**

Do not log raw input on failure. Resolve paths and verify containment before returning
a normalized workspace-relative reference.

- [ ] **Step 4: Run GREEN and static lint**

```powershell
py -3.13 -m pytest tests\unit\studio\test_contracts.py tests\unit\studio\test_redaction.py -q
py -3.13 -m ruff check src\seshat\studio tests\unit\studio
```

- [ ] **Step 5: Commit**

```powershell
git add src\seshat\studio tests\unit\studio
git -c commit.gpgsign=false commit -m "feat: define Studio contracts and redaction"
```

## Task 3: Pin the Workspace and Authenticate the Browser

**Files:**
- Create: `src/seshat/studio/security.py`
- Create: `src/seshat/studio/sessions.py`
- Create: `src/seshat/studio/app.py`
- Create: `tests/unit/studio/test_security.py`
- Create: `tests/integration/studio/test_session_api.py`

**Interfaces:**
- frozen `LaunchConfig(workspace_root: Path, host: Literal["127.0.0.1"], port: int,
  open_browser: bool, agent_kind: str)`
- `resolve_workspace(candidate: Path) -> Path`
- `create_session(workspace_root: Path, now: datetime) -> SessionBootstrap`
- `require_studio_session(request: Request) -> StudioSession`
- `create_app(config: LaunchConfig, bridge: AgentBridge) -> FastAPI`

- [ ] **Step 1: Write security boundary tests**

Test unsupported workspace, path with spaces/non-ASCII, forced public bind, token
entropy, single-use exchange, URL cleanup bootstrap response, missing/forged/expired
cookie, foreign/null Origin, manipulated Host, request-body limit, and required
security headers. Assert rejected bodies contain no workspace identity.

- [ ] **Step 2: Run RED**

```powershell
py -3.13 -m pytest tests\unit\studio\test_security.py tests\integration\studio\test_session_api.py -q
```

- [ ] **Step 3: Implement process and middleware boundary**

Bind only `127.0.0.1`; choose port 0 before launch; store token/cookie digests only;
use a `seshat_studio_session` HttpOnly SameSite=Strict cookie; do not enable CORS.
Keep `/api/v1/health` public and content-free. All other routes pass middleware in
the order defined by `contracts/security-boundary.md`.

- [ ] **Step 4: Run GREEN**

Run both tests and verify the OpenAPI route set matches
`contracts/studio-api.yaml` at this slice.

- [ ] **Step 5: Commit**

```powershell
git add src\seshat\studio tests\unit\studio tests\integration\studio
git -c commit.gpgsign=false commit -m "feat: secure the Studio loopback session"
```

## Task 4: Adapt Existing Readiness Truth into the Studio API

**Files:**
- Create: `src/seshat/studio/workspace.py`
- Create: `tests/fixtures/studio/workspace-empty/`
- Create: `tests/fixtures/studio/workspace-blocked/`
- Create: `tests/fixtures/studio/workspace-ready/`
- Create: `tests/fixtures/studio/workspace-malformed/`
- Create: `tests/unit/studio/test_workspace_projection.py`
- Create: `tests/integration/studio/test_workspace_api.py`
- Modify: `src/seshat/studio/app.py`

**Interfaces:**
- `WorkspaceProjectionService.snapshot() -> WorkspaceSnapshot`
- `WorkspaceProjectionService.table(table_id: str) -> TableJourney`
- `WorkspaceProjectionService.decisions() -> tuple[PreparedDecisionSummary, ...]`
- `WorkspaceProjectionService.forbidden_scope(table_id: str | None) -> tuple[str, ...]`

- [ ] **Step 1: Create domain-neutral fixtures and parity tests**

Use synthetic `orders`, `customers`, and `calendar` artifacts. Obtain expected values
by calling the existing authoritative projections in the same test, not by copying
readiness rules into fixtures. Test pass evidence, Mapping blocker, pending live
profile, no tables, malformed YAML, missing file, and escaped relative reference.

- [ ] **Step 2: Run RED**

```powershell
py -3.13 -m pytest tests\unit\studio\test_workspace_projection.py tests\integration\studio\test_workspace_api.py -q
```

- [ ] **Step 3: Implement the adapter**

Call existing Seshat services directly. Convert their results to Studio immutable
contracts, preserve every categorical status/evidence/blocker/authority, derive one
revision digest from consumed committed inputs, and return named input defects.

- [ ] **Step 4: Implement GET endpoints**

Add bootstrap state, workspace, table, decisions, and agent health routes. Browser
models contain no root path and no numeric health/readiness field.

- [ ] **Step 5: Run GREEN and score/path guard searches**

Run the tests, then use repository text search to assert the new browser contract
contains no `readiness_score`, `confidence_score`, `health_score`, or absolute fixture
root.

- [ ] **Step 6: Commit**

```powershell
git add src\seshat\studio tests\fixtures\studio tests\unit\studio tests\integration\studio
git -c commit.gpgsign=false commit -m "feat: project workspace truth into Studio"
```

## Task 5: Build and Package the Command Room UI

**Files:**
- Create: `studio-ui/package.json`, `package-lock.json`, `tsconfig.json`,
  `vite.config.ts`, `index.html`
- Create: `studio-ui/src/main.tsx`, `app.tsx`, `api.ts`, `types.ts`, `styles.css`
- Create: `studio-ui/src/components/AppShell.tsx`
- Create: `studio-ui/src/components/CommandRoom.tsx`
- Create: `studio-ui/src/components/TableJourney.tsx`
- Create: `studio-ui/src/components/WorkspaceState.tsx`
- Create: `studio-ui/src/test/command-room.test.tsx`
- Modify: `pyproject.toml`
- Modify: `tests/contract/test_studio_package_contract.py`

**Interfaces:**
- one build command copies `studio-ui/dist` to `src/seshat/studio/static`
- `StudioApi` methods mirror `studio-api.yaml`
- `App` states: loading, ready, empty, input_defect, session_expired

- [ ] **Step 1: Write component RED tests**

Test workspace name, current stage, seven-stage order, concrete blocker, evidence,
one next action, pending decision count, empty arrival, input defect, all agent health
states, and the absence of command/skill/path detail in the primary surface.

- [ ] **Step 2: Run RED**

```powershell
cd studio-ui
npm test -- --run
cd ..
```

- [ ] **Step 3: Implement the contextual hybrid shell**

Use local system fonts and CSS variables. On wide screens show navigation, main
Command Room, and contextual side panel; on narrow screens collapse context below
the main task. Status uses text plus icon/shape, never color alone. Technical detail
opens explicitly.

- [ ] **Step 4: Build and package assets**

Configure Vite with relative/local assets, no CDN, deterministic filenames or a
manifest consumed by the backend, and a production base compatible with loopback.
Force-include the generated static directory in wheel/sdist packaging.

- [ ] **Step 5: Run GREEN and wheel-content test**

```powershell
cd studio-ui
npm test -- --run
npm run build
cd ..
py -3.13 -m pytest tests\contract\test_studio_package_contract.py -q
```

- [ ] **Step 6: Commit**

```powershell
git add studio-ui src\seshat\studio\static pyproject.toml tests\contract\test_studio_package_contract.py
git -c commit.gpgsign=false commit -m "feat: add the Studio Command Room"
```

## Task 6: Implement Ordered Events and the Fake Bridge

**Files:**
- Create: `src/seshat/studio/events.py`
- Create: `src/seshat/studio/agents/__init__.py`
- Create: `src/seshat/studio/agents/base.py`
- Create: `src/seshat/studio/agents/fake.py`
- Create: `tests/unit/studio/test_events.py`
- Create: `tests/unit/studio/test_fake_bridge.py`
- Create: `tests/integration/studio/test_agent_sse.py`
- Modify: `src/seshat/studio/app.py`

**Interfaces:**
- `EventBuffer.append(event: PendingStudioEvent) -> StudioEvent`
- `EventBuffer.after(sequence: int) -> tuple[StudioEvent, ...]`
- `EventBuffer.subscribe(after: int) -> AsyncIterator[StudioEvent]`
- `AgentBridge` protocol exactly as `contracts/agent-bridge.md`

- [ ] **Step 1: Write state-machine and replay RED tests**

Cover monotonic sequence, bounded eviction, replay, expired sequence conflict,
concurrent subscriber delivery, duplicate provider event, late event after terminal,
cancelled subscriber cleanup, and redaction-before-retention.

- [ ] **Step 2: Write shared bridge contract tests**

Parameterize health, start thread/turn, event order, approval response, interruption,
and cleanup over a bridge factory. The fake is the first factory.

- [ ] **Step 3: Run RED, implement, run GREEN**

```powershell
py -3.13 -m pytest tests\unit\studio\test_events.py tests\unit\studio\test_fake_bridge.py tests\integration\studio\test_agent_sse.py -q
```

Implement bounded deques and async conditions without a database. SSE `id` equals
sequence; data is only the serialized normalized event.

- [ ] **Step 4: Commit**

```powershell
git add src\seshat\studio tests\unit\studio tests\integration\studio
git -c commit.gpgsign=false commit -m "feat: stream stable Studio agent events"
```

## Task 7: Add Interactive Turn UX on the Fake Bridge

**Files:**
- Create: `studio-ui/src/components/AgentComposer.tsx`
- Create: `studio-ui/src/components/AgentTimeline.tsx`
- Create: `studio-ui/src/components/AgentHealthBanner.tsx`
- Create: `studio-ui/src/test/agent-turn.test.tsx`
- Create: `tests/browser/test_studio_command_room.py`
- Modify: `studio-ui/src/api.ts`, `types.ts`, `app.tsx`

- [ ] **Step 1: Write UI and browser RED tests**

Test submit, visible streaming, reconnect with last event id, interruption, preserved
draft after quota failure, final snapshot refresh, no rendering of hidden reasoning,
and useful deterministic controls while disabled/missing/signed out/incompatible/
quota-limited/crashed.

- [ ] **Step 2: Run RED**

```powershell
cd studio-ui
npm test -- --run
cd ..
py -3.13 -m pytest tests\browser\test_studio_command_room.py -q
```

- [ ] **Step 3: Implement interaction**

Create a thread from the current snapshot revision, submit read-only by default,
connect `EventSource`, render only stable public events, and refetch `/workspace` on
completed/failed/interrupted. On 409 stale state, refresh before asking the user to
resubmit.

- [ ] **Step 4: Run GREEN and commit**

```powershell
cd studio-ui
npm test -- --run
cd ..
py -3.13 -m pytest tests\browser\test_studio_command_room.py -q
git add studio-ui tests\browser\test_studio_command_room.py
git -c commit.gpgsign=false commit -m "feat: make Studio turns interactive"
```

## Task 8: Implement the Codex App-Server Adapter

**Files:**
- Create: `src/seshat/studio/agents/jsonrpc.py`
- Create: `src/seshat/studio/agents/codex.py`
- Create: `tests/fixtures/studio/codex_app_server/*.jsonl`
- Create: `tests/unit/studio/test_jsonrpc.py`
- Create: `tests/unit/studio/test_codex_bridge.py`
- Create: `tests/integration/studio/test_codex_process_fixture.py`

**Interfaces:**
- `JsonRpcClient.start(command: Sequence[str], cwd: Path) -> None`
- `JsonRpcClient.request(method: str, params: object) -> object`
- `JsonRpcClient.notifications() -> AsyncIterator[JsonRpcMessage]`
- `CodexAgentBridge` implements the stable `AgentBridge`
- executable argv is a sequence beginning `("codex", "app-server")`; no shell

- [ ] **Step 1: Commit safe protocol fixtures and RED tests**

Record `codex --version`, generate the version-specific app-server JSON schema into
a temporary directory, and derive only minimal sanitized fixtures from it; do not
commit the full schema bundle. Fixtures cover the required `initialize` response
followed by `initialized`, `account/read`, `account/rateLimits/read`, managed
`chatgpt` login, thread start, read-only turn start, public messages, plan, tool
lifecycle, file proposal, JSON-RPC-correlated command/file approval requests,
completion, sign-out, quota, incompatible or experimental required method,
malformed JSON, out-of-order response, injected stderr secret, EOF, and
cancellation. Remove all real paths/ids/tokens before commit.

- [ ] **Step 2: Run RED**

```powershell
py -3.13 -m pytest tests\unit\studio\test_jsonrpc.py tests\unit\studio\test_codex_bridge.py tests\integration\studio\test_codex_process_fixture.py -q
```

- [ ] **Step 3: Implement JSON-RPC transport**

Correlate request ids, separate notifications, enforce message-size bounds, redact
stderr before diagnostics, fail pending futures on EOF, terminate then kill only the
owned child on shutdown timeout, and never include the full child environment in an
error.

- [ ] **Step 4: Implement version adapter and health mapping**

Probe before healthy; send exactly one `initialize` and then `initialized`; remain
on the stable API without `experimentalApi`; map provider ids internally; normalize
only public events; delegate login with `account/login/start` type `chatgpt`; and map
every failure category from the contract. Start read-only work with
`approvalPolicy: on-request`, thread sandbox `read-only`, and turn sandbox policy
`{type: readOnly, networkAccess: false}`. Do not inspect auth files or API-key
variables.

Treat the publicly experimental app-server boundary as a version-gated beta. Record
the tested minimum and maximum Codex CLI versions in one adapter compatibility
constant and in acceptance evidence. An untested version is `incompatible` until
its generated schema and handshake fixtures pass; do not infer compatibility from
nearby semantic versions.

Correlate command and file approvals by JSON-RPC request id, not by a provider
`approvalId`. Map Studio `allow_once` only to provider `accept` and `deny` only to
`decline`; never expose `acceptForSession`, policy amendments, external-token login,
or experimental additional permissions.

- [ ] **Step 5: Run shared bridge contract and GREEN**

Run the same bridge contract suite against the recorded process fixture and fake.

- [ ] **Step 6: Commit**

```powershell
git add src\seshat\studio\agents tests\fixtures\studio\codex_app_server tests\unit\studio tests\integration\studio
git -c commit.gpgsign=false commit -m "feat: connect Studio to Codex app-server"
```

## Task 9: Enforce Technical Approval and Business-Decision Separation

**Files:**
- Modify: `src/seshat/studio/events.py`, `sessions.py`, `workspace.py`, `app.py`
- Create: `studio-ui/src/components/ToolApprovalPanel.tsx`
- Create: `studio-ui/src/components/PreparedDecisionCard.tsx`
- Create: `studio-ui/src/test/approval.test.tsx`
- Create: `tests/unit/studio/test_approval_policy.py`
- Create: `tests/integration/studio/test_approval_api.py`
- Modify: `tests/browser/test_studio_command_room.py`

**Interfaces:**
- `evaluate_tool_scope(snapshot, request) -> ApprovalPolicyResult`
- `respond_to_approval(thread_id, approval_id, decision) -> None`
- OpenAPI contains technical approval POST only; `/decisions` remains GET-only

- [ ] **Step 1: Write approval RED tests**

Cover visible action/target/reason/scope/risk, paused turn, allow-once, deny, repeated
response, expiry, mismatched thread, Silver operation while Mapping blocked, Power BI
adapter before Semantic Model, and grain/PII/rollup/sentinel business questions.

- [ ] **Step 2: Run RED and implement backend policy**

Compute forbidden scope from the current authoritative snapshot immediately before
display and again before relay. If prohibited, force deny and show the governing
reason. A business question creates only `PreparedDecisionSummary(status="prepared")`.

- [ ] **Step 3: Implement accessible approval UI**

Move focus into the panel, explain that this is technical permission, make deny
visually equal or safer than allow, return focus after response, and show no generic
"approve" wording for business decisions.

- [ ] **Step 4: Run GREEN and API negative assertion**

Assert route enumeration has no POST/PUT/PATCH/DELETE under `/decisions`.

- [ ] **Step 5: Commit**

```powershell
git add src\seshat\studio studio-ui tests
git -c commit.gpgsign=false commit -m "feat: govern Studio technical approvals"
```

## Task 10: Ship the Agent-First Launch Capability

**Files:**
- Create: `.claude/skills/seshat-studio/SKILL.md`
- Modify: `docs/capabilities/capabilities.yaml`
- Modify: canonical export/allowlist inputs as required by spec 138's completed
  inventory contract
- Regenerate: `integrations/claude-code/seshat-bi/`
- Regenerate: `integrations/codex/seshat-bi/`
- Create: `tests/contract/test_studio_capability.py`

**Interfaces:**
- capability id `seshat-studio`
- `ships: true`
- `ship_classification: consumer-capability`
- requirement `optional-dependency`
- primary routing phrase: open/start/launch Seshat Studio

- [ ] **Step 1: Write capability RED tests**

Assert one canonical skill owner, correct classification, both bundle copies,
natural-language launch before command detail, missing-extra two-lane remedy,
single-workspace reuse, Codex interaction, Claude deterministic/native handoff, and
no Claude credential bridge claim.

- [ ] **Step 2: Run RED, author source, regenerate bundles**

Use the canonical export pipeline established by spec 138. Never hand-edit generated
bundle copies.

- [ ] **Step 3: Run GREEN and clean regeneration**

```powershell
py -3.13 -m pytest tests\contract\test_studio_capability.py tests\contract\test_generated_agent_bundles.py -q
py -3.13 scripts\export_agent_bundles.py
git diff --exit-code -- integrations\claude-code integrations\codex distribution\public-knowledge-allowlist.yaml
```

- [ ] **Step 4: Commit**

```powershell
git add .claude\skills\seshat-studio docs\capabilities distribution integrations tests\contract
git -c commit.gpgsign=false commit -m "feat: ship the Seshat Studio launch skill"
```

## Task 11: Accessibility, Wheel, and Security Acceptance

**Files:**
- Modify: `studio-ui/src/styles.css` and affected components/tests
- Modify: `tests/browser/test_studio_command_room.py`
- Modify: `tests/contract/test_studio_package_contract.py`
- Create: `tests/integration/studio/test_security_corpus.py`
- Create: `docs/quality/studio-foundation-acceptance.md`

- [ ] **Step 1: Add acceptance tests before fixes**

Test keyboard-only flow, focus order/return, accessible names, landmarks, non-color
status, reduced motion, narrow layout, axe critical/serious results, no network asset
request, security negative corpus, built wheel assets, base-wheel isolation, Studio
wheel with Node removed from PATH, and missing-asset named failure.

- [ ] **Step 2: Run tests and fix only demonstrated failures**

```powershell
cd studio-ui
npm test -- --run
npm run build
cd ..
py -3.13 -m pytest tests\browser\test_studio_command_room.py tests\integration\studio\test_security_corpus.py tests\contract\test_studio_package_contract.py -q
```

- [ ] **Step 3: Build and inspect distributions**

Build sdist/wheel, inspect archive contents, install base and `[studio]` into separate
clean virtual environments, and record exact commands/results. No Node process or
remote request may appear in runtime acceptance.

- [ ] **Step 4: Run dashboard regression**

Locate and run all existing `retail dashboard` unit/contract/browser tests without
changing their expected output except for independently justified pre-existing drift.

- [ ] **Step 5: Commit**

```powershell
git add studio-ui src\seshat\studio\static tests docs\quality\studio-foundation-acceptance.md
git -c commit.gpgsign=false commit -m "test: harden Studio release acceptance"
```

## Task 12: External Codex Acceptance and Final Requirement Audit

**Files:**
- Modify: `docs/quality/studio-foundation-acceptance.md`
- Modify only if evidence requires: implementation/test files responsible for a
  demonstrated acceptance failure

- [ ] **Step 1: Verify prerequisites without exposing credentials**

Record OS, Python, Seshat, Studio build, and Codex versions. Confirm Codex reports a
signed-in subscription through its official user-facing flow. Start Studio with no
API key supplied to its environment.

- [ ] **Step 2: Run safe external scenarios**

Natural-language launch, one read-only question, reconnect, interrupt, and one denied
technical approval. Compare repository status before/after the denial. Record only
normalized event types and redacted outcomes.

- [ ] **Step 3: Run complete fresh verification**

```powershell
py -3.13 -m ruff format --check src tests
py -3.13 -m ruff check src tests
py -3.13 -m pytest -m unit -x -q
py -3.13 -m pytest -m integration -x -q
seshat check
seshat semantic-check
git diff --check
git status --short
```

Run browser, package, bundle, and active-marker gates explicitly if their markers are
not included above.

- [ ] **Step 4: Audit every requirement**

Create a table in the acceptance record mapping FR-001 through FR-036 and SC-001
through SC-010 to tests, command output, or external acceptance. Do not mark a live
or unavailable boundary passed.

- [ ] **Step 5: Request code review and resolve findings**

Use `superpowers:requesting-code-review`. Re-run the affected focused tests after each
accepted fix and the full verification after the last fix.

- [ ] **Step 6: Final commit**

```powershell
git add docs\quality\studio-foundation-acceptance.md
git -c commit.gpgsign=false commit -m "docs: record Studio Foundation acceptance"
```

Do not claim the complete three-spec Studio mission here. Foundation completion
unlocks spec 140; it does not include governed business-decision transcription,
Operations, or Client Review.
