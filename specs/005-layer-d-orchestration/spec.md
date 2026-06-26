# Feature Specification: Layer-D orchestration -- the conductor skill

**Feature Branch**: `005-layer-d-orchestration` (work on `main` per session convention; located via `.specify/feature.json`)

**Created**: 2026-06-24

**Status**: Shipped (retail-orchestrate conductor skill landed)

**Input**: "Build toward orchestration (Layer D). Claude Code IS the orchestrator (confirmed -- no standalone runtime). Author ONE conductor skill that sequences the existing verb-skills (source-mapping, retail-govern, retail-validate, pbip-workflow) across the medallion phases and self-heals against the gate exit code, stopping at the two human seams. Demonstrate the self-heal loop on the gate that fully exists today (`retail check`), replayable over the c086 worked example. No new Python; static core stays stdlib-only."

## Why this feature exists

The architecture names Layer D the **primary surface** ("an agent runs the playbook
conversationally ... and self-heals against the gate") but marks the orchestration
**shape** as **open decision #3 -- "Still open ... the runtime is a later slice."**
The two verb-skills shipped in feature 001's follow-up (`source-mapping`,
`retail-validate`) were framed as "the prerequisite that unblocks orchestration
later." This feature is that later slice -- the **conductor** that composes the four
existing verbs into the fixed medallion sequence and runs the self-heal loop.

It resolves open decision #3 in the **agent-as-conductor** form: the runtime is the
agent reading a skill, NOT a daemon, scheduler, or fix-applying subagent. "Building
toward orchestration" here means authoring agent-facing instructions, not building a
Python orchestration engine.

## The posture this records (the amendment)

- **Open decision #3 (agent orchestration shape) is resolved as: a Markdown
  conductor skill; the agent is the runtime.** A standalone orchestration runtime
  (daemon / state machine / counter-owning loop subagent) remains explicitly
  **rejected for this slice**, not merely deferred -- it would re-introduce the
  runtime the kit parks.
- Constitution Principle I (agent proposes, gate disposes) and Principle VIII
  (static-first, live deferred) are unchanged; this feature operates within them.

## Architecture (no new code; one skill composes existing verbs)

```
  retail-orchestrate  (NEW: .claude/skills/retail-orchestrate/SKILL.md)
        | reads mappings/<table>/ as resumable run-state (the Gate status field)
        | sequences, never executes a loop FOR the agent
        v
  source-mapping --> [HUMAN SEAM: mapping gate] --> [SEAM: silver/gold builder]
        --> retail-validate --> [SEAM: pbi-cli build] --> pbip-workflow
        |                                   ^
        +-- self-heal loop -----------------+
            run gate -> read EXIT CODE (sole authority) -> exit 0 advance
            -> non-zero: classify each finding auto-fixable vs HARD-STOP
            -> apply one mechanical fix -> re-run; bound by max-iter + no-progress
```

- **The agent is the runtime.** The skill is procedure text; the agent reading it in
  context is what "runs." No persisted counter, no loop subagent, no daemon.
- **The gate exit code is the sole pass authority** (`retail check` / `retail
  validate`). The loop NEVER declares compliance from prose -- only a literal exit 0
  advances a phase. (`runner.py` sets exit 1 iff any `Severity.ERROR`.)
- **Two hard human seams** the loop must STOP at:
  1. Principle IV mapping gate -- read the EXISTING `Gate status: CLEARED` +
     zero-open-rows signal in `mappings/<table>/unresolved-questions.md`; never
     advance to silver otherwise, never self-grant approval.
  2. Principle V judgment calls -- grain ambiguity, PII publish-safety, business
     rollup, sentinel-vs-null, and any build-blocking question escalate to a human.
- **Named [SEAM] nodes** (deferred by design, the conductor reports + parks, never
  fakes a pass): the silver/gold SQL builder (DB writes -- own spec), pbi-cli (later
  adapter, Principle II), the live `retail validate` run (needs the `db` extra + a
  user DSN, Principle VIII).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The agent drives the sequence and self-heals against the static gate (Priority: P1)

Given a repo state, the conductor computes the current phase from
`mappings/<table>/`, drives the next verb, and on a gate failure runs the self-heal
loop until `retail check` exits 0 -- mapping each finding id to its one fix.

**Why this priority**: this is the orchestration keystone -- the loop that treats
the exit code as authority and converges to green is the thing the feature exists to
provide. It is demonstrable today on `retail check` (no DB, no creds).

**Independent Test**: introduce a deliberate static violation in a tracked artifact;
invoke the conductor; it runs `retail check`, reads the non-zero exit, applies the
single id->fix, re-runs, and converges to a literal exit 0 -- replayable over the
c086 worked example (whose silver+gold SQL already exist in `warehouse/migrations/`).

**Acceptance Scenarios**:

1. **Given** a tracked TMDL/SQL artifact with one mechanical violation (e.g. a
   measure missing a `displayFolder`, D2), **When** the conductor runs the loop,
   **Then** it applies the single fix at the locator, re-runs `retail check`, and
   stops at exit 0.
2. **Given** `retail check` already exits 0, **When** the conductor reaches a gate
   node, **Then** it advances without making any change (no-op on green).
3. **Given** the loop hits the same finding id+locator twice (no progress) OR the
   max-iteration cap, **Then** it STOPS and escalates to a human with an
   `unresolved-questions.md` owner row -- it does not loop forever.

### User Story 2 - Judgment-implicating findings hard-stop, never auto-fix (Priority: P1)

The loop classifies findings per-rule. Mechanical findings auto-heal; findings that
imply a human judgment call (grain, returns column, PII, business rollup) HARD-STOP.

**Why this priority**: the most dangerous failure is an agent "fixing" a
judgment-call finding -- e.g. dedup'ing rows to clear a `V-RC2` PK violation, which
silently makes the grain decision Principle V reserves for a human. The
classification is the safety boundary.

**Independent Test**: present the loop a `V-RC2` (PK-not-unique) or `D6`
(bidirectional relationship "or justify") finding; assert it routes to HARD-STOP +
escalation, NOT a mechanical dedup/auto-edit.

**Acceptance Scenarios**:

1. **Given** a `V-RC2` PK-not-unique finding, **When** the loop classifies it,
   **Then** it HARD-STOPS (grain is a Principle-V human decision) -- never dedups.
2. **Given** a `D2` missing-displayFolder finding, **When** the loop classifies it,
   **Then** it auto-fixes (mechanical, single locator, no judgment).
3. **Given** a finding id the loop cannot confidently classify, **Then** it defaults
   to escalate, not auto-fix.

### User Story 3 - The mapping gate is honored from existing run-state (Priority: P2)

The conductor reads `mappings/<table>/unresolved-questions.md` `Gate status` to
decide whether silver may proceed -- it does not invent a new approval marker and
does not self-grant approval.

**Independent Test**: with `Gate status: OPEN`, the conductor refuses to advance past
the mapping gate; with `Gate status: CLEARED` + zero open rows, it resumes at the
silver [SEAM] node.

**Acceptance Scenarios**:

1. **Given** `Gate status: OPEN`, **When** the conductor reaches the gate, **Then**
   it STOPS and reports the map is not yet approved -- no silver.
2. **Given** `Gate status: CLEARED` and no open rows, **When** the conductor
   resumes, **Then** it advances to the silver [SEAM] node (which is itself
   deferred this slice) -- it does not re-run the mapping phase.

### Edge Cases

- No `mappings/<table>/` dir -> the conductor starts at Phase 1 (source-mapping).
- `retail check` stdout format drift -> the loop keys pass/fail strictly off the
  EXIT CODE; finding-text parsing is best-effort; an unmappable id escalates.
- No DSN / no `db` extra at a live node -> report the deferred boundary, mark numbers
  `[PENDING LIVE PROFILE]`, never traceback, never fake a pass (Principle VIII).
- A `C2` secret finding -> the file edit is mechanical, but secret ROTATION is a
  human/ops action; the loop never claims rotation done.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add `.claude/skills/retail-orchestrate/SKILL.md` -- ASCII-only, UTF-8
  no BOM, valid `name`/`description` frontmatter matching the other verb-skills.
- **FR-002**: The skill sequences the medallion phases by delegating to the existing
  verbs (`source-mapping`, `retail-govern`, `retail-validate`, `pbip-workflow`); it
  adds NO new Python and does NOT duplicate their logic.
- **FR-003**: The skill defines the self-heal loop as a written contract: run gate ->
  read exit code (sole authority) -> exit 0 advance / non-zero classify+fix+re-run,
  bounded by a max-iteration cap AND a no-progress detector (same id+locator twice).
- **FR-004**: The skill carries a per-rule auto-fixable-vs-HARD-STOP classification.
  HARD-STOP at minimum: `V-RC2` (grain), `V-RC15`/`V-RC16` implying a business/grain
  choice, `D6`, `D5`, `D3` (judgment), `C2` rotation, business rollup, PII,
  sentinel-vs-null. Unknown findings default to escalate.
- **FR-005**: The skill reads `mappings/<table>/unresolved-questions.md` `Gate
  status` as the machine-legible GO signal and the resumable run-state; it MUST NOT
  invent a new approval marker and MUST NOT self-grant approval.
- **FR-006**: The deferred middle/end of the loop is rendered as explicit [SEAM]
  nodes (silver/gold builder, pbi-cli, live validate run) the conductor reports and
  parks at -- never fakes a pass, never tracebacks.
- **FR-007**: The skill appends a one-paragraph `## Orchestration` pointer to each of
  the four verb-skills naming `retail-orchestrate` as the conductor -- with NO change
  to the verbs' existing no-auto-loop language (the loop lives only in the conductor).
- **FR-008**: No new runtime: no daemon, scheduler, persisted counter file, or
  fix-applying loop subagent. The agent reading the skill is the runtime.
- **FR-009**: The static core stays stdlib-only/driver-free; `retail check` exits 0
  on the repo after this feature (the skill is under `.claude/`, not a model artifact).

### Key Entities

- **Conductor skill** (`retail-orchestrate`): agent-procedure text; the sequencer +
  self-heal loop contract + per-rule classification + seam map.
- **Self-heal loop**: a written contract the agent follows in-context; gate exit code
  is the authority; bounded; escalates judgment calls.
- **Run-state**: `mappings/<table>/` artifacts + `Gate status` + `warehouse/
  migrations/` presence -- read to compute the current phase. No new state file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `.claude/skills/retail-orchestrate/SKILL.md` exists, ASCII + no BOM,
  valid frontmatter; the harness registers it as an available skill.
- **SC-002**: `retail check` still exits 0 (26 rules) with the skill present; full
  unit suite stays green.
- **SC-003**: All cross-linked paths in the skill resolve.
- **SC-004**: The self-heal loop is demonstrated end-to-end on `retail check`: a
  planted mechanical violation converges to a literal exit 0; a planted
  judgment-class finding (`V-RC2`/`D6`) HARD-STOPS instead of auto-fixing.
- **SC-005**: No new Python module is added; `dependencies = []` unchanged; no
  daemon/counter/loop-subagent introduced.

## Assumptions

- Agent-as-conductor is the confirmed orchestration model (user confirmation +
  architecture open decision #3). A standalone runtime is rejected this slice.
- The demonstrable loop runs on the static gate (`retail check`) -- the one gate
  fully present today; c086's silver+gold SQL already exists to replay over.
- The silver/gold builder, pbi-cli wiring, and the live validate run remain deferred
  seams with their own future specs -- one conductor invocation does NOT yet produce
  a finished Power BI deliverable, by design.

## Deferred decisions (future specs / issues -- recorded, not built)

- **Silver/gold SQL builder verb** -- writing `warehouse/` SQL implies DB writes and
  crosses the foundation's "no new warehouse tables / no DB writes" boundary; needs
  its own spec/amendment. Largest middle-of-loop seam.
- **pbi-cli wiring** -- the deferred Power BI authoring adapter (Principle II); the
  conductor terminates at this seam.
- **Live `retail validate` run** -- needs the `db` extra + a user DSN (Principle VIII,
  open decision #4); runs only when creds are provided.
- **A G-namespace static rule (e.g. `G6`)** that fails closed if `silver.*` SQL
  exists for a table whose `unresolved-questions.md` lacks `Gate status: CLEARED` --
  moves approval enforcement off the agent onto the gate (the real hardening of
  FR-005); a checker change for a later slice now that `warehouse/migrations/` exists.

## See also

- The verbs the conductor composes: `.claude/skills/{source-mapping,retail-govern,
  retail-validate,pbip-workflow}/SKILL.md`.
- The method: `docs/medallion-playbook.md` (7 phases + per-phase exit gates).
- The open decision this resolves: `docs/architecture/tower-bi-agent-kit.md` Sec 8
  (open decision #3); `.specify/memory/constitution.md` Principles I, IV, V, VIII.
- The replay reference: `docs/worked-examples/c086-pharmacy.md`.
- The GO signal field: `templates/unresolved-questions.md` (`Gate status`).
