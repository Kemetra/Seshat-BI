# Contract: Studio AgentBridge v1

**Feature**: 139-seshat-studio-foundation | **Status**: proposed

`AgentBridge` is the only boundary through which Studio controls an interactive
agent. Browser routes and components must not import provider-specific models.

## Stable Python Protocol

```python
class AgentBridge(Protocol):
    def health(self) -> AgentHealth: ...

    async def start_thread(self, workspace: Path) -> ThreadRef: ...

    async def start_turn(
        self,
        thread_id: str,
        request: AgentRequest,
    ) -> None: ...

    async def respond_to_approval(
        self,
        thread_id: str,
        approval_id: str,
        decision: ToolApprovalDecision,
    ) -> None: ...

    async def interrupt(self, thread_id: str) -> None: ...

    def events(self, thread_id: str) -> AsyncIterator[StudioEvent]: ...
```

All argument and result types are immutable values from `seshat.studio.contracts`.
Implementations may retain provider identifiers internally but never expose raw
provider envelopes.

## Required Implementations

### FakeAgentBridge

- consumes recorded scenario steps, not network or local credentials;
- emits deterministic events with controllable timing;
- supports every health state and state transition;
- records approval responses and interruptions for assertions;
- can emit malformed, duplicated, late, and out-of-order provider fixtures so the
  normalization layer is tested fail-closed.

### CodexAgentBridge

- discovers the `codex` executable without a shell command string;
- launches `codex app-server` as a child process with the pinned workspace as its
  working directory;
- communicates through newline-delimited stdio JSON-RPC supported by the installed
  app-server version;
- lets Codex own login and cached ChatGPT subscription credentials;
- never reads credential files or environment API-key values;
- maintains explicit provider-to-Studio thread/turn/approval mappings;
- handles EOF, malformed messages, incompatible methods, quota errors, and process
  cancellation as categorical health/turn states;
- terminates the owned child process during Studio shutdown.

## Event Normalization

The bridge yields only the closed `StudioEventType` set in `data-model.md`.

| Provider observation | Studio event | Required browser payload |
|---|---|---|
| thread initialized | `thread_started` | Studio thread id only |
| turn accepted | `turn_started` | Studio turn id, requested mode |
| visible assistant text | `agent_message` | rendered text, citations if safe |
| visible plan update | `plan_updated` | ordered public steps and states |
| tool begins | `tool_started` | safe label and sanitized target |
| tool ends | `tool_completed` | outcome and safe summary |
| file change proposed | `file_change_proposed` | relative files and summary |
| permission requested | `approval_required` | ToolApprovalRequest fields |
| turn completes | `turn_completed` | safe final summary |
| turn/protocol fails | `turn_failed` | category and recovery action |
| process/auth/quota changes | `connection_state` | AgentHealth fields |

Provider reasoning summaries may be mapped only when explicitly public and safe.
Hidden chain-of-thought, encrypted reasoning, raw protocol frames, credentials,
environment dumps, and absolute paths are discarded.

## Turn Context Contract

Every request sent through the production bridge includes:

- pinned workspace context supplied out of band by process working directory;
- current selected table, if any;
- current readiness stage and categorical statuses;
- existing evidence and concrete blockers;
- one next allowed action;
- current forbidden scope;
- whether the request is read-only or proposes changes;
- a reminder that technical permission cannot grant a business approval.

The request never embeds a DSN, token, authorization header, browser cookie, or raw
credential-bearing environment value.

## Approval Contract

1. The bridge emits a provider request as `approval_required` but does not answer it.
2. Studio redacts it and evaluates proposed scope against current readiness.
3. Prohibited scope is denied automatically with a governed explanation.
4. Otherwise Studio pauses and waits for one explicit `allow_once` or `deny`.
5. The bridge maps that response to the exact outstanding provider approval.
6. Unknown, stale, repeated, or mismatched responses raise a typed conflict and send
   no provider message.

There is no "always allow" and no business-decision response in v1.

## Compatibility Contract

- Startup negotiates or probes the installed protocol before declaring healthy.
- The release records the minimum and maximum Codex CLI versions exercised. A CLI
  outside that tested range remains `incompatible` until its generated schema and
  handshake fixtures pass; semantic-version proximity alone is not compatibility
  evidence.
- The Codex adapter sends exactly one `initialize` request with Studio client
  metadata, waits for its response, then sends `initialized` before any account,
  thread, or turn request.
- Foundation uses the stable v2 surface and does not set
  `capabilities.experimentalApi`. A feature that requires that flag is unavailable
  rather than silently enabled.
- Unknown notification methods are ignored only when they carry no required state;
  their names are recorded in redacted diagnostics.
- Unknown required request methods make the adapter `incompatible` and stop new
  turns.
- Provider-specific parsing lives in version adapters under `agents/codex.py` or a
  focused sibling module; the `AgentBridge` protocol does not change for a provider
  release unless Studio semantics change.
- Fixtures identify their source protocol version and are safe to commit.

### Codex 0.146.0 provider mapping (verified 2026-08-03)

The installed CLI's own `codex app-server generate-json-schema --experimental`
output and the current official App Server manual confirm this mapping for the
stable v2 methods present in that build. The app-server surface itself remains
publicly labelled experimental; this table is tested compatibility evidence, not a
stability promise. The generated schema is version-specific audit input and is not
committed wholesale.

| Studio operation | Stable Codex method or event | Adapter rule |
|---|---|---|
| initialize | `initialize`, then `initialized` | identify `seshat_studio`; do not opt into experimental API |
| health | `account/read`, `account/rateLimits/read` | distinguish signed out and quota-limited without reading auth storage |
| login | `account/login/start` with `type: chatgpt` | open returned `authUrl`; never send `apiKey` or `chatgptAuthTokens` variants |
| start thread | `thread/start` | pin `cwd`; use `approvalPolicy: on-request` and `sandbox: read-only` initially |
| start read-only turn | `turn/start` | send `sandboxPolicy: {type: readOnly, networkAccess: false}` |
| interrupt | `turn/interrupt` | require both provider thread and active turn ids |
| visible streaming | `turn/*`, `item/started`, `item/completed`, `item/agentMessage/delta`, `turn/plan/updated` | normalize only the public subset |
| command approval | `item/commandExecution/requestApproval` | correlate by JSON-RPC request id; absolute `cwd` is relativized or rejected |
| file approval | `item/fileChange/requestApproval` | correlate by JSON-RPC request id; `grantRoot` must remain under the pinned workspace |
| approval resolved | `serverRequest/resolved` | close exactly one pending Studio approval |

Studio maps `allow_once` to provider decision `accept` and `deny` to `decline`.
Provider decisions `acceptForSession` and any exec-policy/network-policy amendment
are not exposed in Foundation. `cancel` is reserved for interruption or shutdown.
The adapter must not assume a provider `approvalId`: it is optional for command
requests and absent from the stable file-change request; the JSON-RPC request id is
the correlation authority.

Reasoning delta/summary notifications, raw response items, absolute paths, and
experimental `additionalPermissions` never reach the Studio event model. Because
Foundation does not enable the experimental API, receiving an experimental required
request is classified as incompatible rather than handled opportunistically.

## Failure Contract

| Condition | AgentHealth / result | Required behavior |
|---|---|---|
| executable absent | `missing` | deterministic views stay enabled; show install remedy |
| login required | `signed_out` | delegate official login; receive no credential |
| unsupported protocol | `incompatible` | refuse turns; name supported/observed versions |
| subscription limit | `quota_limited` | preserve draft and reported reset detail |
| unexpected EOF | `crashed` | fail active turn, redact, recompute snapshot, offer restart |
| deliberately disabled | `disabled` | deterministic views only |

No condition triggers an AUTOMATIC API-key fallback. Every row above stays a reported
health state with a recovery action; none of them may switch the bridge to a billed
path on its own (FR-013).

An API-key or access-token bridge is permitted only as an EXPLICITLY
operator-configured alternate implementation of this same `AgentBridge` protocol
(FR-013a, amended 2026-08-04). When active it MUST be named in the interface and in
`GET /bootstrap`. It is never selected by inference, by degradation, or as a response
to any condition in this table.
