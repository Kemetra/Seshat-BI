# Seshat Studio — the technical approval panel (T026) and the road to Foundation complete

**Date**: 2026-08-13
**Spec**: `specs/139-seshat-studio-foundation/` (Phases 6–8)
**Status**: design — agent-authored under owner delegation, NOT owner-ratified

## Authority note — read this first

The owner delegated decision authority for this session and is asleep. This
document is therefore written under delegation, and the `brainstorming` skill's
approval gate was satisfied by that delegation rather than by a design review.

That delegation has a hard edge, and this document respects it: it **records**
design decisions, it does not **ratify** them, and it does not self-grant any
approval the governance model reserves for a named human. Spec 139 is already
ratified; this is the missing layer *underneath* T026, not a new spec. No
requirement is added, removed, or reinterpreted here.

One task in the remaining work (T036) is owner-gated by construction and is
excluded from autonomous execution — see "What a human must do".

## Why this document exists

T026 is one line of task text:

> Implement the accessible technical approval panel and one-time relay; browser
> code performs no side effect. [FR-019, FR-020]

That line is the keystone of Phase 6 and it under-specifies the hardest part.
Two findings from reading the shipped code make that concrete, and neither is
visible from the task text.

### Finding 1 — the browser cannot see the readiness verdict (blocking)

FR-021 requires that an allow control is not offered when readiness forbids the
scope. The backend computes exactly that, in `approvals.py:58-86`:

```python
@dataclass(frozen=True)
class ApprovalEnvelope:
    approval_id: str
    authority: str
    allow_permitted: bool
    forbidden_reasons: tuple[str, ...]
    ...
```

`allow_permitted` and `forbidden_reasons` **never leave Python**. The
`approval_required` SSE payload carries `approval_id`, `required_authority`,
`action`, `target`, `reason`, `scope`, `risk`, and `provider_request_id` — and
nothing else. The verdict the requirement turns on is absent from the wire.

A panel built on today's payload could only discover a forbidden scope by
offering Allow, having the analyst click it, and rendering the 403 that comes
back. That is the precise inversion of FR-021: the control must be **absent**,
not present-then-retracted.

**Decision: widen the payload before building the panel.** `allow_permitted`
and `forbidden_reasons` join the `approval_required` payload; the contract yaml
and generated types follow. This is tracked as its own task and blocks T026.

The alternative — a second `GET` the panel issues per approval to ask "may I
allow this?" — was rejected. It adds a round trip, and more importantly it
creates a second read path for a fact the event already knows, which is the
`second-trust-path` shape this repo has been burned by before.

**Also drop `provider_request_id` from the wire.** It is an internal JSON-RPC
correlation id that reaches the browser today only because
`agent_routes.py:573-575` passes one dict to both `register_approval` and
`thread.append`. The browser has no use for it and it is a provider-internal
detail.

### Finding 2 — the Phase 6 boundary test does not guard the boundary

The test that pins approvals as inert is declared at `Conversation.test.tsx:242`
and makes its load-bearing assertion at `:265`:

```tsx
expect(
  screen.queryByRole("button", { name: /approve|apply|reject/i }),
).not.toBeInTheDocument();
```

The contract's decision enum is `allow_once` / `deny`
(`studio-api.yaml:234-236`). A panel whose buttons read **"Allow once"** and
**"Deny"** satisfies that assertion while doing exactly what the assertion was
written to forbid. The test would stay green as the boundary is crossed.

**Consequence for the plan:** this test cannot be treated as a signal that
tells us when the panel arrives. T026 must *deliberately rewrite* it, and the
rewrite must assert the new invariants in their positive form. A task list step
of "wait for the red test" would silently never fire.

### Finding 3 — `/decisions` promises a schema nothing produces

An adversarial review of the first draft of this design found a third gap, and
it refuted a task this work had already checked off.

T027 reads "Implement read-only prepared decision summaries with no mutation
route and assert OpenAPI contains no business-approval endpoint." The second
clause ships and is well tested. The first does not exist:

```python
@app.get(f"{API_PREFIX}/decisions")
async def decisions() -> Any:
    """Read-only by construction: there is no mutation route to omit."""
    return {"items": []}
```

`app.py:320-322` is the entire implementation — a hardcoded empty list with no
producer anywhere in `src/`. Meanwhile `studio-api.yaml:84-100` defines a
required `items` array of `PreparedDecisionSummary`. The contract promises a
shape the code never builds, and the only test asserts the path exposes `get`
and nothing else — a claim about the HTTP method, never about content.

FR-022 places the business ruling itself outside Studio permanently, and that is
correct. But "prepared summaries are visible read-only" and "an empty list is
returned forever" are different promises, and only the weaker one is kept. Note
that `register_approval` already registers `named_human` items *specifically* so
they are visible as prepared summaries — the backend collects the data and then
discards it at the boundary.

**Decision: T027 is unchecked and its summaries clause is scoped into the panel
work.** The panel renders a `named_human` approval as a prepared summary with
Deny-only, which is the same information `/decisions` is contracted to list. The
endpoint is fed from the pending-approvals ledger it already populates, or the
contract is narrowed to match the code. Either resolution is honest; shipping a
promise with no producer is not.

## The two payload shapes problem

`FakeAgentBridge` (`bridge.py:187-192`) emits `{approval_id, question,
required_authority}`. Real Codex (`codex_protocol.py:407-450`) emits
`{approval_id, required_authority, action, target, reason, scope, risk,
provider_request_id}` — **no `question`**.

Today's renderer narrows on `question` only (`eventPayload.ts:74-75`), so every
*real* Codex approval already renders the fallback string "A decision is being
prepared." The UI is built against the fake and has never displayed a real
approval.

This is a trap for T024's "exact scope display": a panel tested only against the
fake's shape proves nothing about the path that matters. Per the repo's
`fixtures-must-come-from-the-real-producer` rule, panel tests must use payloads
derived from the real producer — `tests/fixtures/codex_app_server/approvals.jsonl`
is the committed real capture.

**Decision:** the panel renders from the real shape (`action`/`target`/`scope`/
`risk`), and the fake bridge is widened to emit the same fields so the two
producers stop disagreeing. `question` stays supported as an optional
human-readable line, not as the field the display depends on.

## What the panel is

An approval is rendered by a dedicated component, not by the generic activity
row. Its states:

**Decidable** (`required_authority === "technical"` and `allow_permitted`):
renders the exact scope, and offers **Allow once** and **Deny**.

**Not Studio's to grant** (`required_authority === "named_human"`): renders the
scope and offers **Deny only**. This asymmetry is deliberate and mirrors the
backend (`approval_delivery.py:84-88`): refusing to grant a governance ruling is
not the same as refusing to answer the provider, and an unanswered request
blocks the turn either way. The panel says who *can* decide it, and does not
imply Studio can.

**Readiness forbids the scope** (`allow_permitted === false` with
`forbidden_reasons`): **no allow control exists in the DOM** — not disabled,
absent. The reasons are rendered as the governance sentences the backend
produced. Deny remains available.

**Decided**: the controls are replaced by what was decided. The id is spent; the
ledger burns it on allow *and* deny.

### Error handling

The route returns more codes than the contract documents. A frontend built from
the yaml alone would not handle two of them:

| Code | Meaning | What the panel does |
|---|---|---|
| 204 | recorded and delivered | show the decision |
| 403 | allow impermissible | replace controls with the reason; do not retry |
| 404 | unknown thread | surface as a thread-level failure |
| 409 | not awaiting a decision | the approval is stale — say so, remove controls |
| **422** | unrecognized decision value | a bug in our own client; generic failure |
| **502** | recorded but NOT delivered | the id is spent and the provider was never answered — say the turn cannot continue and the decision cannot be re-sent |

502 is the one that matters most and is the easiest to get wrong: the decision
succeeded locally and failed on the wire. Reporting it as a generic error would
tell the analyst to retry something that can never succeed.

**The contract yaml must be widened to document 422 and 502.** An undocumented
response code is a contract defect regardless of the panel.

### Accessibility

The panel establishes a pattern the codebase does not yet have: **focus
management**. There is currently no `.focus()`, `autoFocus`, `tabIndex`, or
focus trap anywhere in `studio-ui/src`. An approval arriving mid-stream is an
interruption that a keyboard or screen-reader user must not have to hunt for.

- The approval is announced via a live region. `role="alert"` is not correct
  here — the existing convention reserves `alert` for failures
  (`Conversation.tsx:198`) and uses `role="status"` for state
  (`AgentHealth.tsx:105`). An approval is a state that needs attention, so it
  is announced with `role="status"` and an explicit heading, and focus is moved
  to the panel heading rather than stealing it onto a button. Moving focus onto
  Allow would put a destructive-ish control under an unaware keypress.
- Never color-alone (FR-031). `risk: high` pairs a glyph and a
  `.visually-hidden` sentence, matching `StatusBadge.tsx`.
- Tokens from `tokens.css` only; no new color literals, both themes explicit.
- Buttons carry accessible names that survive `getByRole`, following the
  existing query discipline.
- `axe` is **not currently a dependency** — SC-007 demands automated browser
  accessibility checks, so it must be added. This is a real gap, not an
  oversight in the plan.

### The no-side-effect rule (FR-020)

Browser code performs no side effect: the panel calls one new client function,
`respondToToolApproval`, which POSTs the decision. It does not write files, does
not touch the provider, and does not decide anything locally. The one-time
property is the **server's** ledger, not a disabled button — the button is
disabled during flight only to prevent a double POST, and the authoritative
refusal of a replay is the 409 the server returns.

## Sequencing

Two ordering facts drive the shape.

**`awaiting_technical_approval` is in the enum, set by nothing — and is
DEFERRED, deliberately.** It exists in the contract, the generated types, and
`THREAD_STATES`, but no production code assigns it; the only state ever emitted
is `"ready"`.

The first plan for this work was to wire it as a prerequisite for the panel.
Reading the code disproved that, and the deferral is the more defensible
outcome:

- `state` is not stored anywhere. `ThreadEvents` holds an event log, not a
  status field, and `state` appears exactly once — as a literal in the
  create-thread response (`agent_routes.py:181`).
- `AgentThreadRef` is referenced in exactly **one** place in the whole contract
  (`studio-api.yaml:148`): the `201` response to `POST /agent/threads`. A thread
  that has just been created cannot be awaiting an approval, so no response the
  contract defines could ever legitimately carry this state. There is no
  GET-thread route.

Making the value reachable therefore means inventing new API surface — a state
store plus a read route — that the ratified contract never asked for. Worse, it
would give the panel a *second* way to learn something the event stream already
tells it: `approval_required` arriving on the SSE stream **is** the pause
signal, and it is the signal the browser already subscribes to. A parallel read
path for the same fact is the shape this repo reverted a PR over (the
second-trust-path antipattern).

The state machine at `data-model.md:240` is satisfied by the event stream: turn
lifecycle in this codebase is expressed as events (`turn_started`,
`turn_completed`, `_TERMINAL_EVENTS`), not as a queryable field.
`awaiting_technical_approval` stays legitimately **typed but unreachable**, and
the panel derives the pause from the event. If a future spec adds a GET-thread
route, that route is the channel and the wiring belongs with it.

**No task builds this. The deferral and its reason are the deliverable.**

**The frontend toolchain does not exist locally.** `studio-ui/node_modules` is
absent. Node 24.14.0 / npm 11.9.0 are available, so this is an install, not a
blocker — but nothing frontend can be verified until it is done.

```
Wave 0  (docs)      refresh the stale Phase 6 evidence record      [DONE]
Wave 1  1a          awaiting_technical_approval — DEFERRED, no channel exists
        1b          npm ci + test baseline + add axe               [DONE: 105 green]
        1d -> 1c    widen the payload, THEN regenerate types once
Wave 2  (keystone)  T026 the approval panel                        needs 1b, 1d
Wave 3  (parallel)  T028-T031 skill + capability registration      file-disjoint
Wave 4  (parallel)  4a T033 wheel ships the built frontend
                    4b T032+T034 accessibility + security corpus
Wave 5              T035 regression, T037 requirement review
Wave 5b             T036 external Codex acceptance — OWNER-GATED
```

**1d must precede 1c.** Widening the `approval_required` payload edits
`studio-api.yaml`; regenerating `types.ts` reads it. Running them in the other
order regenerates twice and leaves the drift test red in between.

The frontend baseline is measured, not assumed: `npm ci` installed 182 packages
with 0 vulnerabilities and `npx vitest run` reports **105 passed across 6 test
files** on `e069e46d`. Any frontend red after this point is ours.

Wave 3 is genuinely parallel to Wave 2 — skill authoring and yaml registration
touch no React file. But T030 regenerates both bundles, and this repo has a
recorded `capabilities.yaml` collision when two bundle-touching branches are
open at once. That is a **merge-order** constraint, not a build-order one: a
Wave 3 PR and any other bundle-touching PR must not sit open for merge
simultaneously.

## Risks

**The wheel may ship no UI.** FR-005 says built JS ships in the wheel and end
users never need Node. Issue #623 says `release.yml` builds the wheel without
the Studio frontend. This repo has a recorded scar (#609) where hatchling
honoured VCS ignore and silently dropped a gitignored generated directory from
the wheel while every unit test stayed green. `studio-ui/dist/` is generated.
The only test that can prove this is one that **opens a real wheel** and asserts
the built assets are inside — a `pip wheel` run, not a unit test.

**`agent_turns` is `False`** in `_bootstrap_capabilities()` while
`technical_approvals` is `True`. A flag that under-reports a shipped seam is the
mirror of the over-reporting bug #628 fixed. It blocks nothing today, but T037
maps SC-001..SC-010 to fresh evidence and cannot pass honestly while a
capability flag contradicts the code — so this is resolved as part of Wave 5
rather than discovered at the end. Either the flag is wrong, or turns are not
actually shipped and something else is over-claimed.

**Stale global install.** A pipx `seshat-bi` shadows the checkout and produces
phantom version failures. Run with `PYTHONPATH=src`.

## What a human must do

**T036 — external signed-in Codex acceptance.** It requires a human signed into
a real Codex subscription, producing versioned redacted evidence containing no
API credential (SC-001, SC-003, SC-010). No agent can do this. Spec 139's own
2026-08-04 amendment already records provider authentication compliance as an
open question whose closure is a named-human action.

Everything else in Phases 6–8 is autonomously executable. T036 is the single
item handed back.

## Explicitly out of scope

Per the owner's "finish studio first": no branch/worktree cleanup, no unrelated
open issues (#603, #514, #469, #618), no version bump, no release. Issue #623 is
in scope only because T033 cannot be honest without it.
