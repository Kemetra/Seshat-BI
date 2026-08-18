# Implementation Plan: Approval-Gated Power BI MCP Write Adapter (F016 slice 5)

**Branch**: `149-pbi-mcp-write-adapter` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/149-pbi-mcp-write-adapter/spec.md`

**Authority**: `docs/decisions/0018-unpark-f016-power-bi-mcp-execution-adapter.md` —
**RATIFIED by Ahmed Shaaban (owner) on 2026-08-18** (commit `ef7f55a0`). ADR decision 8
authorizes this plan; the mutation path ships only under this spec's own tests and review.

## Summary

Build the governed last mile: apply an already-approved Power BI semantic-model change
through Microsoft's official Power BI Modeling MCP, with Seshat's recorded named-human
approval sitting **above** the vendor tool rather than trusting its own confirmation flags.

The technical approach is deliberately unoriginal: `src/seshat/dagster_adapter/` is already
an Execution Adapter with exactly the module decomposition this feature needs
(`gate.py` / `runner.py` / `evidence.py` / `redaction.py` / `doctor.py`). We mirror that
shape as `src/seshat/pbi_mcp_adapter/` rather than inventing a parallel design. The novel
surface is small and entirely about refusal: a four-precondition gate, a
bypass-flag chokepoint, and a post-write validation step that blocks.

## Technical Context

**Language/Version**: Python 3.13 (stdlib-only for anything the DEFINE/CHECK core imports)

**Primary Dependencies**: none added. The vendor runtime (`@microsoft/powerbi-modeling-mcp`)
is external, unforked, and invoked via `npx` — never vendored, never a Python dependency
(ADR 0018 rejected alternative; Principle II). `seshat check` keeps `dependencies = []`.

**Storage**: committed files only — `readiness-status.yaml` (read for the gate, appended for
derived evidence), a declared target allowlist, and the git-ignored `.mcp.json` for local
launcher config. No database.

**Testing**: pytest, `-m unit`. A **stubbed MCP runtime** stands in for the vendor server;
no live tenant, no live database, no network. The CI unit job runs without app extras, so any
optional import is guarded with `importorskip`.

**Target Platform**: developer workstation (Windows/macOS/Linux) with Power BI Desktop or an
on-disk PBIP/TMDL project; local stdio process boundary only.

**Project Type**: CLI + agent skill inside the existing `seshat` package (single project).

**Performance Goals**: not a throughput feature. The only timing requirement is that a
stalled vendor process must not hang a run indefinitely — bounded wait with a typed
`blocked` outcome.

**Constraints**:
- Read-only is the resting state; write mode is an armed exception requiring all four
  preconditions.
- `--skipconfirmation` refused in every mode, including read-only and including in tests.
- No new `seshat check` rule; no new readiness stage.
- Evidence carries a fixed authority label and typed blockers, and **no numeric, maturity, or
  confidence score** (hard rule #9).
- No committed host, tenant, credential, or user path (Principle IX).
- Subprocess calls use `stdin=subprocess.DEVNULL` plus a **workload-sized** timeout, following
  `dagster_adapter/runner.py`. **Not** `gitutil.run_subprocess` — its docstring explicitly
  excludes the execution runners, because its short shared cap would abort legitimately long
  user workloads (see [research.md](./research.md) R4). Never call `subprocess` bare.

**Scale/Scope**: one adapter package (~6 modules), one CLI verb group extending the existing
`pbi-mcp` family, one agent skill, and the tests that prove each refusal. Slice 6 (remote,
query-only) is out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Requirement | How this plan complies |
|---|---|---|
| **I. Agent-First, Gate-Enforced** | capability arrives behind a gate | The adapter is unreachable for writes until four preconditions clear; the gate is the feature. |
| **II. Depend, Never Fork** | external tools consumed, not vendored | `npx`-invoked official Microsoft MCP; no fork, no vendored binary, no new Python dependency. |
| **III. Medallion, Gold-Only** | not applicable | No warehouse layer is touched; this operates on semantic-model artifacts. |
| **IV. Source Mapping Before Silver** | not applicable | No silver/gold SQL authored. |
| **V. Agent Stops at Judgment Calls** | never self-grant approval | The adapter **reads** `publish_ready`; it can neither write `approvals[]` nor move a stage. A successful write changes no stage (FR-018). |
| **VI. Defaults Then Deviations** | safe default, explicit deviation | Read-only is the default and write mode cannot be reached by omission (FR-001, FR-003). |
| **VII. C086 Is An Example** | no schema hardcoding | Targets come from a declared allowlist, not a baked-in model shape. |
| **VIII. Static-First, Live Deferred** | offline provable | Every acceptance test runs against a stubbed runtime; post-write validation is offline (`seshat check` R-family). |
| **IX. Secrets & Reproducibility** | nothing sensitive committed | Evidence passes through `redaction_core`; launcher config stays in git-ignored `.mcp.json`; the committed example is placeholder-only and read-only. |

**Hard rule #9 (no score)**: the evidence record carries a fixed authority label and typed
blockers only. No numeric, maturity, or confidence value is emitted anywhere.

**Result: PASS, no violations.** Complexity Tracking is therefore omitted — nothing needed
justifying.

**Post-Phase-1 re-check: PASS.** The design added no dependency, no rule, and no stage; the
one new external boundary (local stdio to the vendor process) was already enumerated in
`templates/pbi-mcp-adapter-contract.md`.

## Project Structure

### Documentation (this feature)

```text
specs/149-pbi-mcp-write-adapter/
├── spec.md              # authored
├── plan.md              # this file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── cli-contract.md
├── checklists/
│   └── requirements.md  # authored, all items pass
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/seshat/pbi_mcp/                  # EXISTING (slices 1-4) — EXTENDED, not replaced
└── detect.py                        # the ALREADY-SHIPPED bypass-flag chokepoint;
                                     # gains argv inspection (config-only today)

src/seshat/pbi_mcp_adapter/          # NEW — mirrors src/seshat/dagster_adapter/
├── __init__.py                      # status vocabulary + public surface
├── gate.py                          # the four write preconditions, fail-closed
├── target.py                        # declared target allowlist resolution
├── git_safety.py                    # clean-or-declared-backup check
├── runner.py                        # npx stdio invocation; stdin=DEVNULL + own timeout
├── validation.py                    # post-write validation, blocking + rollback guidance
└── evidence.py                      # derived run record, both paths, score-free

src/seshat/cli/                      # EXTENDED — the existing pbi-mcp verb family
└── (pbi-mcp apply / plan-write legs added alongside doctor|generate-config|preflight)

.claude/skills/pbi-mcp-write-adapter/  # NEW — the agent-facing skill (adapter precedent)
└── SKILL.md

tests/unit/
├── test_pbi_mcp_detect.py           # EXISTING — extended: bypass flag in argv too
├── test_pbi_mcp_gate.py             # each precondition broken independently
├── test_pbi_mcp_runner.py           # stubbed runtime; no live tenant
├── test_pbi_mcp_validation.py       # failure is blocking + carries rollback guidance
└── test_pbi_mcp_evidence.py         # both paths, no score, no stage moved
```

**Structure Decision**: a dedicated `src/seshat/pbi_mcp_adapter/` package mirroring the
shipped `src/seshat/dagster_adapter/` layout. That adapter already solved this exact
problem shape — gate reading, bounded subprocess execution, redaction, and derived evidence —
so copying its decomposition keeps reviewer intuition transferable and avoids a second,
divergent adapter idiom. The CLI legs extend the **existing** `pbi-mcp` group rather than
creating a new top-level verb, because slices 1–4 already established that namespace.

**Correction after verifying against shipped code**: an earlier draft of this plan proposed a
new `invariants.py` module for the bypass-flag prohibition. That is **cancelled**. The
enforcement already exists at `src/seshat/pbi_mcp/detect.py:51` (`_FORBIDDEN_FLAG`,
`_WRITE_FLAGS` covering **both** `--readwrite` and `--read-write`), consumed by `preflight.py`
and `recommend.py` and already under test. A second module would be a second enforcement path
for one rule — the `no-second-approval-trust-path` defect. The real gap is narrower: the
shipped check inspects `.mcp.json` **config args only** and never invocation **argv**, because
until now nothing could be invoked in write mode. Slice 5 extends that one matcher.

## Phase 0: Research

**Output**: [research.md](./research.md)

Five questions the plan cannot answer from the ADR alone, each resolved against committed
code rather than assumption:

1. What is the real evidence status vocabulary? (Answer: **five** values, not four —
   `materialized`, `failed`, `skipped`, `blocked`, `deferred`, per
   `src/seshat/dagster_adapter/__init__.py:44`.)
2. What is the committed gate-reader pattern for a stage, and what does it do on an
   unreadable file?
3. How is a named-human approval row located and matched to a target?
4. What is the exact `gitutil.run_subprocess` contract, and how does it avoid the stdio
   stdin-deadlock?
5. What does `redaction_core` guarantee, and does it handle a whole `key=value` span rather
   than a fragment?

## Phase 1: Design & Contracts

**Prerequisites**: research.md complete

**Outputs**: [data-model.md](./data-model.md), [contracts/cli-contract.md](./contracts/cli-contract.md), [quickstart.md](./quickstart.md)

1. **data-model.md** — the seven entities from the spec as frozen dataclasses, with their
   validation rules and the one state machine that matters: `requested → refused` (any
   precondition unmet) or `requested → armed → executed → validated | invalidated`, with an
   evidence record emitted from both terminal states.

2. **contracts/cli-contract.md** — the CLI surface contract: the new write legs, their
   arguments, their exit codes, and the refusal messages. This is the external interface a
   user and CI both bind to, so it is contract-tested.

3. **quickstart.md** — the operator walkthrough: what must be approved before a write is even
   attemptable, what a refusal looks like for each missing precondition, and how to roll back.

4. **Agent context update** — point the `<!-- SPECKIT START -->` / `<!-- SPECKIT END -->`
   block in `CLAUDE.md` at this plan.

## Implementation Sequencing (the TDD spine)

Tests come first, and each test must sit on the actual risk. Two traps this repo has been
bitten by, called out so `/speckit-tasks` inherits them:

- **No absence-assertions.** A test asserting a capability is *missing* goes green when the
  capability ships in a different shape. Pin the *behavior* (a refusal happened, with this
  blocker named), not the absence of a symbol.
- **No vacuous branches.** A test that can silently stop exercising its precondition (because
  the fixture made the branch unreachable) proves nothing. Each of the four preconditions gets
  a *hold-three-break-one* test, and the suite asserts the refusal count so a
  never-taken branch is visible.

Ordering, each step green before the next:

1. **Extend `pbi_mcp/detect.py` + its tests** — the bypass-flag chokepoint **already exists**
   there (`_FORBIDDEN_FLAG`, `_WRITE_FLAGS` covering both `--readwrite` and `--read-write`).
   Add argv inspection to that one matcher; do NOT create a second module or constant. First
   because it is the one rule with no exceptions, and everything else runs behind it.
2. **`gate.py` + tests** — the four preconditions, parameterized hold-three-break-one, plus
   the fail-closed-on-unreadable case. Prove refusal before building anything that can write.
3. **`target.py`, `git_safety.py`** — the two preconditions with their own resolution logic.
4. **`evidence.py` + tests** — before the runner, so the runner has somewhere honest to
   report. Assert score-free, both paths, and **no stage moved**.
5. **`runner.py` + tests** — stubbed runtime, `stdin=DEVNULL` and a workload-sized timeout
   (research R4); a stall becomes a typed `blocked` outcome, never an unbounded hang.
6. **`validation.py` + tests** — failure is blocking and carries rollback guidance.
7. **CLI legs + contract tests** — the emitted commands must be *executed* in tests, not
   string-matched (a shape assertion goes green while the command is broken).
8. **The skill + docs**, then the full gate set.

## Verification Gates

Every one of these must pass before the PR is reviewable:

```bash
ruff format --check src/ tests/
ruff check src/ tests/
pytest -m unit -x -q
seshat check
seshat semantic-check
```

Plus three feature-specific proofs:

- **Fail-open proof**: monkeypatch out *only* the gate and assert the old (permissive) verdict
  returns — proving the guard is what produces the refusal, not incidental behavior.
- **Score-free proof**: scan every emitted evidence record for numeric fields.
- **Redaction proof**: assert no host/tenant/credential/user-path token survives into a
  committed record.

## Risks

| Risk | Mitigation |
|---|---|
| Vendor preview drift silently changes flag or capability names | Drift is a preflight blocker (FR-019); the supported range stays `unknown` and `unknown` is never compatible. |
| A future callsite invokes the runtime without the gate | `pbi_mcp/detect.py` (bypass flag) + `pbi_mcp_adapter/gate.py` (the four preconditions) are the only entry path; a test asserts the runner refuses when called with an uncleared gate object, and another asserts every write-capable path resolves its flag verdict through `detect.py`. |
| Evidence starts looking like approval | FR-018 plus an explicit before/after stage comparison in the evidence tests. |
| Partial write after a mid-run process death | Treated as `failed` with rollback guidance and an evidence record; never reported as success. |
| The stubbed runtime diverges from the real server | The stub is built from the real preflight artifact shape (`.seshat/powerbi-mcp-preflight.json`), not hand-invented — avoids a circular fixture that proves only itself. |
