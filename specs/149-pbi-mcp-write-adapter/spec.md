# Feature Specification: Approval-Gated Power BI MCP Write Adapter (F016 slice 5)

**Feature Branch**: `149-pbi-mcp-write-adapter`

**Created**: 2026-08-18

**Status**: Ratified (Ahmed Shaaban, 2026-08-18)

**Input**: User description: "Slice 5 of F016: the approval-gated Power BI MCP write adapter, authorized by ADR 0018 (RATIFIED by Ahmed Shaaban 2026-08-18). Pipeline: write operations -> approval gate -> target allowlist -> git safety -> Microsoft MCP execution -> post-write validation -> rollback/evidence."

**Authorizing decision**: `docs/decisions/0018-unpark-f016-power-bi-mcp-execution-adapter.md` —
**Accepted -- RATIFIED by Ahmed Shaaban (owner) on 2026-08-18**. ADR decision 8 authorizes
authoring this spec; the mutation path ships only under this spec's own tests and review.
All eight ADR decisions bind together and **none is severable**.

**Binding contract**: `templates/pbi-mcp-adapter-contract.md` (Execution Adapter,
`publish-capable`, execution-only).

---

## Why this exists (the problem in one paragraph)

Today a Seshat user who has taken a semantic model all the way to an approved, signed-off
state must still leave the governed workflow and apply the change by hand in Power BI
Desktop. The last mile is ungoverned: nothing records what was applied, to which target, on
whose authority, or whether the artifact still validated afterwards. Microsoft now ships an
official Power BI MCP that *can* apply such changes — but its own documentation warns that
autonomous or misconfigured clients may perform destructive actions and that its safety
flags are non-standard and client-dependent. So the gap is not "we lack a tool"; it is "the
available tool's safety model is weaker than the approval spine we already run." This
feature closes the last mile by placing Seshat's recorded, named-human approval **above**
the vendor tool rather than trusting the vendor's prompts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Apply an approved model change through the governed path (Priority: P1)

A data owner has an approved semantic-model edit (for example a parameter definition or a
partition repoint) that Core Authority already decided upstream. Semantic Model Ready is
`pass` for the target scope, and a named human has recorded a `publish_ready` approval whose
note names the intended target. The owner asks Seshat to apply it. Seshat verifies every
precondition, applies the change through Microsoft's official MCP, validates the touched
artifacts, and records what ran — without ever deciding that the change was *correct* or
advancing any readiness stage on the strength of a successful write.

**Why this priority**: This is the entire point of the slice and the only story that
delivers the last mile. Shipped alone it is a complete, useful, governed capability.

**Independent Test**: Fully testable with a stubbed MCP runtime and a fixture repo whose
`readiness-status.yaml` carries a passing `semantic_model_ready` plus a target-naming
`publish_ready` approval: assert the artifact changed, an evidence record was written, and
no stage moved.

**Acceptance Scenarios**:

1. **Given** all four write preconditions hold, **When** the owner requests a write,
   **Then** the change is applied, post-write validation runs and passes, an evidence record
   is written naming tool/mode/target/timestamp/result, and **no readiness stage changes**.
2. **Given** a successful write, **When** the evidence record is inspected, **Then** it
   carries a fixed authority label and typed blockers and **no numeric, maturity, or
   confidence score** of any kind.
3. **Given** a successful write, **When** `publish_ready` is re-read, **Then** it is
   unchanged — a green write is not an approval and never becomes one.

---

### User Story 2 - Be refused, clearly, when authority is missing (Priority: P1)

An operator attempts a write while one precondition is absent — the stage is not `pass`, the
approval is missing or does not name this target, the target is not allowlisted, or the
working tree is dirty with no declared backup. Seshat refuses and names the specific missing
authority. It never proceeds "because a human is probably fine with it", and it never
downgrades the refusal to a warning that a script could ignore.

**Why this priority**: Equal-P1 with Story 1. A write path without a provably fail-closed
refusal path is a liability, not a feature; the refusal is the governance, and it is the
half most likely to be silently weakened later.

**Independent Test**: Parameterized over each of the four preconditions independently — hold
three, break one, assert refusal every time and assert the reported blocker names the
*specific* missing item. Also assert refusal when readiness state is absent or unreadable
(fail-closed, not fail-open).

**Acceptance Scenarios**:

1. **Given** `semantic_model_ready` is not `pass`, **When** a write is attempted, **Then**
   it is refused with that stage named as the blocker.
2. **Given** a `publish_ready` approval exists but its note does **not** name the intended
   target, **When** a write is attempted, **Then** it is refused — a generic approval never
   authorizes an unnamed target.
3. **Given** readiness state is absent, malformed, or unreadable, **When** a write is
   attempted, **Then** it is refused (fail-closed); an unreadable gate is never treated as a
   passing gate.
4. **Given** the working tree is dirty and no backup was explicitly declared, **When** a
   write is attempted, **Then** it is refused with rollback-safety named as the blocker.
5. **Given** any refusal, **When** the outcome is inspected, **Then** it is a blocking
   result — never a warning, and never a partial write left behind.

---

### User Story 3 - Recover safely when a write leaves the artifact invalid (Priority: P2)

A write succeeds at the MCP level, but post-write validation finds the touched artifacts no
longer valid. Rather than reporting success because the tool returned zero, Seshat reports a
blocking finding, tells the operator exactly how to roll back, and records the failure as
evidence.

**Why this priority**: P2 because it presupposes the Story 1 path exists, but it is what
makes the capability trustworthy in production: a write that validates nothing afterwards is
indistinguishable from a write that corrupted the model.

**Independent Test**: Force a validation failure against an already-mutated fixture and
assert the outcome is blocking, that concrete rollback guidance is present, and that an
evidence record exists for the *failed* run.

**Acceptance Scenarios**:

1. **Given** post-write validation fails, **When** the run reports, **Then** the result is a
   blocking finding **with** rollback guidance — never a warning.
2. **Given** a failed run, **When** evidence is inspected, **Then** a record exists for the
   failure (evidence is written on **both** the success and failure paths).
3. **Given** a rollback was performed per the guidance, **When** the artifact is re-checked,
   **Then** it returns to its pre-write validating state.

---

### User Story 4 - Detect vendor preview drift before it is trusted (Priority: P3)

Both official Microsoft servers are public preview with no published release. Before relying
on a runtime, the operator is told when the detected capability set, flag set, or schema has
drifted from what the compatibility record supports.

**Why this priority**: P3 — the read-only preflight from slices 1–4 already exists to build
on, and drift is a correctness risk rather than a blocker to first value.

**Independent Test**: Feed a fixture describing an unexpected capability/flag/schema and
assert preflight reports a blocker rather than proceeding.

**Acceptance Scenarios**:

1. **Given** detected capabilities differ from the supported record, **When** preflight
   runs, **Then** drift is reported as a blocker.
2. **Given** no published release exists to pin, **When** the supported range is consulted,
   **Then** it reads `unknown` and `unknown` is **never** treated as compatible.

---

### Edge Cases

- **`--skipconfirmation` present anywhere** — in a committed config, an ad-hoc invocation,
  read-only mode, or a test fixture: hard refusal in every case. This is a standing
  invariant checked before any invocation, not a branch inside write mode.
- **Mode defaulting** — an invocation that names no mode resolves to read-only. Write mode is
  never reached by omission, and `--readwrite` is never the default.
- **Approval names a different target than the one requested** — refused (Story 2, scenario 2).
- **Approval was recorded, then the model changed underneath it** — the approval names a
  target, not a snapshot; post-write validation is what catches divergence.
- **Two writes requested against the same target concurrently** — the second must not
  interleave; the git-safety precondition is re-evaluated per invocation, not cached.
- **MCP process dies mid-write** — the artifact may be partially modified: treated as a
  failed run with rollback guidance and an evidence record, never as success.
- **MCP returns success but touched nothing** — validation still runs; a no-op is reported
  honestly rather than as an applied change.
- **Target is allowlisted but does not exist on disk** — refused as an undefined artifact;
  the adapter never invents the definition.
- **Read-only invocations** still require Semantic Model Ready = `pass`, but do **not**
  additionally require `publish_ready`.
- **Secrets in output** — no host, tenant, credential, or user path may appear in any
  committed evidence record or log.

## Requirements *(mandatory)*

### Functional Requirements

**Resting state and mode**

- **FR-001**: The adapter MUST default to read-only on every invocation; write mode MUST be
  an explicit, reviewed opt-in and MUST NOT be reachable by omission or defaulting.
- **FR-002**: The adapter MUST refuse, in **every** mode including read-only and including
  in tests, any configuration or invocation carrying `--skipconfirmation`. This check MUST be
  evaluated before any runtime invocation.
- **FR-003**: The adapter MUST NOT default to `--readwrite` in any committed example,
  generated config, or invocation.

**The four write preconditions (all required, none severable)**

- **FR-004**: Before any write, the adapter MUST verify the target scope's
  `semantic_model_ready = pass`, read via the committed gate-reader pattern.
- **FR-005**: The adapter MUST fail closed when readiness state is absent, malformed, or
  unreadable — an unreadable gate MUST NEVER be treated as a passing gate.
- **FR-006**: Before any write, the adapter MUST verify an explicit named-human
  `publish_ready` approval row whose note **names the intended target**. A generic or
  unnamed approval MUST NOT authorize a write.
- **FR-007**: Before any write, the adapter MUST verify the target is a declared, allowlisted
  artifact.
- **FR-008**: Before any write, the adapter MUST verify the git working state is clean or that
  a backup was explicitly declared.
- **FR-009**: When ANY precondition is unmet the adapter MUST refuse and report the specific
  missing item as a blocker. It MUST NOT degrade to a warning, MUST NOT proceed partially,
  and MUST NOT infer or self-grant the missing authority.

**Execution boundary**

- **FR-010**: Mutation MUST occur only through this bounded adapter as bound by
  `templates/pbi-mcp-adapter-contract.md`. The DEFINE/CHECK core (the static rules and
  `seshat check`) MUST NOT drive any mutation.
- **FR-011**: The adapter MUST execute only an already-approved definition. It MUST NOT
  define metrics, mappings, semantic logic, or dashboard design, and MUST NOT invent a
  definition that is absent.
- **FR-011a**: The requested operation MUST be **resolved from** the committed approved
  definition set for the target, never accepted as free-form input. An operation identifier
  that does not resolve is a refusal.
- **FR-011b**: The resolved definition MUST be verified against the content the approval
  covers (a content hash recorded at approval time). A mismatch — the definition changed after
  sign-off — is a refusal, not a warning.
- **FR-011c**: An approval naming a target MUST NOT authorize an arbitrary mutation of that
  target. Target-naming and operation-binding are two distinct checks, and both are required.
- **FR-012**: The adapter MUST consume the vendor runtime as an external, unforked dependency
  and MUST NOT vendor it into the distributed package.

**Post-write validation**

- **FR-013**: Every mutation MUST be followed by offline validation of the touched artifacts:
  the `seshat check` R-family; binding validation where a report is in scope; and value
  validation where an expected value exists and a data leg is available.
- **FR-014**: A failed post-write validation MUST be a blocking finding accompanied by
  rollback guidance, never a warning.

**Evidence is not approval**

- **FR-015**: The adapter MUST write a derived run-evidence record — what ran, in which mode,
  against which target, when, and with what result — on **both** the success and failure
  paths.
- **FR-016**: The evidence record MUST mirror the existing run-evidence shape: a fixed
  authority label and typed blockers.
- **FR-017**: The evidence record MUST NOT contain any numeric, maturity, or confidence
  score.
- **FR-018**: A successful mutation MUST NOT move `publish_ready` — or any readiness stage —
  to `pass`. The readiness decision remains a named human's recorded act, before and after
  the write.

**Preview drift**

- **FR-019**: A capability, flag, or schema drift discovered at preflight MUST be reported as
  a blocker.
- **FR-020**: The supported-version record MUST remain the authority on compatibility, and an
  `unknown` range MUST NEVER be treated as compatible.

**Secrets**

- **FR-021**: The adapter MUST NOT commit real hostnames, tenant identifiers, credentials, or
  user paths; every committed record and example MUST be redacted or placeholder-only.

**Non-regression**

- **FR-022**: The existing read-only family (`doctor`, `generate-config`, `preflight`) MUST
  continue to work unchanged.

### Key Entities

- **Write request**: an intent to mutate one declared target — carries the target identity and
  the requested mode; is inert until every precondition clears.
- **Approval reference**: the named-human `publish_ready` record whose note names the target;
  read, never written, by this feature.
- **Readiness state**: the committed per-scope stage record supplying `semantic_model_ready`;
  read-only to this feature, and unreadable-means-refuse.
- **Target allowlist**: the declared set of artifacts a write may touch; anything outside it is
  refused.
- **Run-evidence record**: derived, score-free proof of what ran and how it ended; written on
  both outcomes and never an approval.
- **Validation outcome**: the post-write verdict on touched artifacts; a failure is blocking
  and carries rollback guidance.
- **Runtime capability profile**: what the detected preview server actually supports; drift
  against the supported record is a blocker.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An owner with a fully approved change can apply it through the governed path
  without leaving the workflow, and the applied change is confirmed by validation before the
  run is reported as successful.
- **SC-002**: **100%** of write attempts missing any one of the four preconditions are
  refused, and each refusal names the specific missing authority. Zero refusals are
  expressible as warnings.
- **SC-003**: **Zero** readiness stages change as a result of any run, successful or failed —
  verifiable by comparing stage state before and after every scenario.
- **SC-004**: **Every** run, successful or failed, produces exactly one evidence record, and
  **zero** records contain a numeric, maturity, or confidence score.
- **SC-005**: An invocation or config carrying the confirmation-bypass flag is refused in
  **100%** of modes, including read-only and including in test fixtures.
- **SC-006**: Every failed post-write validation yields actionable rollback guidance, and
  following that guidance returns the artifact to its pre-write validating state.
- **SC-007**: The three existing read-only commands continue to pass their current tests
  unchanged.
- **SC-008**: No committed artifact produced by this feature contains a real host, tenant,
  credential, or user path.

## Assumptions

- **Ratification is authority to author, not to build**: ADR decision 8 authorizes this
  spec/plan/tasks; the mutation path ships only under this spec's own tests and review. No
  write code is authorized outside it.
- **Slice 6 (the remote, query-only server) is out of scope** and remains gated on ADR
  decision 7. Nothing here may make remote query results an input to any readiness stage.
- **The read-only foundation exists**: slices 1–4 shipped in PRs #464/#467 and are the base
  this builds on rather than replaces.
- **`npx`-style external invocation is the distribution default**: vendoring the runtime is a
  rejected alternative under ADR 0018 (external, unforked, independently upgradeable; the
  preview binary is not shippable payload).
- **Approved definitions already exist upstream**: this feature executes decisions Core
  Authority made; it never originates them.
- **Test doubles stand in for the vendor runtime**: acceptance is provable without a live
  tenant. No live database provisioning and no tenant-state changes are in scope.
- **Both servers remain public preview** with no published release to pin, so the supported
  range legitimately reads `unknown` for the life of this spec.
- **Approval and readiness records are read-only inputs** here; this feature never writes to
  `approvals[]` or to any stage field.

## Out of Scope

- Slice 6: the remote query-only server (ADR decision 7).
- Any change that would let a tool result grant, imply, or advance an approval.
- Authoring metrics, mappings, semantic logic, or dashboard design.
- Live database provisioning, tenant configuration, or workspace administration.
- Making the DEFINE/CHECK core capable of driving a mutation.
- Advancing the F032 supported-version range beyond `unknown` (externally blocked until
  Microsoft publishes a release and a smoke run passes).

## Dependencies

- `docs/decisions/0018-unpark-f016-power-bi-mcp-execution-adapter.md` — ratified authority.
- `templates/pbi-mcp-adapter-contract.md` — the contract this spec instantiates.
- `docs/integrations/pbi-mcp-adapter.md` — the three-MCP-senses disambiguation.
- The shipped read-only family from slices 1–4 (PRs #464/#467).
- The committed gate-reader pattern and the existing run-evidence shape used by the dbt and
  Dagster adapters.
- `docs/operations/adapter-compatibility-matrix.md` (the supported-range record) and its
  named-human review lane.
