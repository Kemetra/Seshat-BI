# Adversarial Plan Review: Activate the dagster-dbt Engine Seam

**Reviewer**: Fable (independent adversarial pass over spec.md, plan.md,
tasks.md, analysis.md at commit a06c455/9520ee3, grounded against the committed
`seshat.dbt` control layer, `gates.py`, and the living docs).

**Posture**: every finding below was formed by attacking the plan (where could
this self-grant approval, masquerade a green run as readiness, break unattended,
or leave a stale claim), then verified against the committed code before being
recorded. Findings the author's own analysis already surfaced (F1..F6) are
credited, not re-counted.

**Disposition**: all findings FIXED in the same branch (see "Fixes applied");
none were dismissed.

## Findings

### R1 (HIGH) -- the accept-plan digest degrades to a self-handshake on the unattended path

Spec 133's accept-plan flow has a human moment: `seshat dbt plan` -> a human
reviews the plan -> the human passes the digest to `build --accept-plan`.
Clarification Q3 has the unattended asset recompute the plan and pass its own
digest. The drift-guard survives (a stale digest still refuses), but the digest
no longer records that ANY human saw the plan -- plan and build happen in one
process, seconds apart; drift between them is nearly impossible. The review
moment is silently deleted, and nothing in the spec named the compensating
control.

**Failure scenario**: an operator flips a table to `engine: dbt` via a config
nobody reviews (see R2/F2); from then on every unattended run plans AND accepts
its own plans forever. The spec-133 review seam is structurally gone for that
table, and no artifact records that it is gone.

**Fix required (applied)**: (a) spec states explicitly that under the dbt
engine the digest functions as a DRIFT-GUARD ONLY, not a review record; (b) the
COMPENSATING CONTROL is named: the engine flag MUST live in the table's
human-reviewed committed working set (`mappings/<table>/`), so flipping the
engine -- the moment that authorizes standing self-recompute -- is itself a
reviewed, committed, attributable change; (c) run evidence MUST record that the
plan was self-accepted-by-recompute so the ledger is honest about the missing
per-run review.

### R2 (HIGH) -- a green dbt-engine run does not refresh the real warehouse, and nothing said so

Under `engine: dbt` the build writes ISOLATED SHADOW schemas only (spec 133
FR-005 -- correct and non-negotiable). Consequence the spec did not state: the
REAL `silver`/`gold` relations are NOT rebuilt by that run, while every
downstream asset (semantic checks, validate) continues to gate against the REAL
warehouse. Two traps follow:

- **Whole-table dbt**: a full-sequence run reports `silver_tables`/`gold_tables`
  materialized, but the warehouse the downstream assets just validated was last
  built by some EARLIER migrations run. An operator reading the run evidence
  reasonably -- and wrongly -- concludes this run refreshed gold.
- **Mixed engines** (Clarification Q7 allowed it "independently" with no
  warning): `silver: dbt` + `gold: migrations` means the migrations gold build
  reads real silver that THIS run never rebuilt -- gold built from stale silver
  under a green run.

**Failure scenario**: nightly dbt-engine runs go green for a month; the real
gold serving Power BI is a month stale; every run's evidence looks healthy.

**Fix required (applied)**: (a) spec states the downstream semantics truth: the
dbt engine is a governed REHEARSAL into shadow schemas; the real warehouse is
unchanged by that asset, and downstream assets validate the migration-built
warehouse; (b) run evidence MUST record `warehouse_updated: false` (or the
equivalent measured field) under the dbt engine; (c) doctor MUST emit a WARNING
finding for any table whose layers resolve to MIXED engines, and the evidence
record marks the mix; (d) Clarification Q7 amended accordingly.

### R3 (MEDIUM) -- no early proof that the four pins co-resolve in one venv

T001 adds `seshat-bi[dbt]` (dbt-core 1.12.0 + dbt-postgres 1.10.2) into the
venv that already pins dagster 1.13.14 + dagster-dbt 0.29.14. dagster-dbt
declares its own dbt-core compatibility range; if 0.29.14 excludes dbt-core
1.12.0, the install SOLVE fails and the entire feature is unbuildable -- yet no
task proves the solve before Phase 3 builds on it.

**Fix required (applied)**: T001 extended -- prove the fresh-venv resolution of
all four pins FIRST and record the solver output as evidence; on failure STOP
and surface to the owner (bumping either pinned pair is a spec-133/134
governance decision, never an implementer improvisation).

### R4 (MEDIUM) -- the stale-claim sweep is too narrow

FR-013/T018 reconcile only `docs/integrations/dagster-adapter.md`. Grounding
found `orchestration/dagster/README.md` also carries the seam-as-future claim.
Frozen artifacts (spec 134 dir, CHANGELOG history, docs/releases/*) must NOT be
reworded (they are history), but every LIVING doc still claiming the seam is
documentation-only becomes a lie the moment this merges.

**Fix required (applied)**: T018 broadened -- grep-sweep living docs
(`orchestration/dagster/README.md` included; frozen specs/releases/CHANGELOG
excluded) for "activates after spec 133" / seam-as-future claims and reconcile
each.

### R5 (MEDIUM) -- the no-pass-through oracle does not sit on the bypass risk

T006 asserts "no raw dbt selector/argument" through a fake runner -- an oracle
ADJACENT to the risk. The actual bypass risk is the bridge (or anything in
`tower_bi_orchestration`) invoking the `dagster-dbt` execution API
(`DbtCliResource` / `@dbt_assets`) or the dbt binary directly, skipping
`seshat.dbt` planning/gate entirely. A fake-runner test cannot see that.

**Fix required (applied)**: a STATIC oracle added to T019: assert no module in
`tower_bi_orchestration` imports `dagster_dbt` execution APIs and the bridge
invokes dbt ONLY through `seshat.dbt.runner`. Cheap, mechanical, directly on
the bypass path. (Complements analysis F1's readiness-no-write oracle, which is
also promoted to an explicit task.)

### R6 (LOW) -- lock semantics under unattended kill are unstated

The bridge inherits `seshat.dbt.runner`'s bounded cross-process lock
(`.seshat/dbt/locks/<table>-<target>.lock`). Unattended runs get killed
(timeouts, CI cancellation). The plan never states what a subsequent run sees:
bounded wait then a concrete `LockUnavailable` blocker naming the holder -- or
an eternal stale-lock wall.

**Fix required (applied)**: T012 extended -- assert lock contention surfaces as
a concrete redacted `blocking_reason` (never a traceback, never a silent hang)
per `seshat.dbt` lock semantics; if a stale-lock gap is found in `seshat.dbt`,
STOP and surface it (owned by spec 133's surface, not silently patched here).

### Adopted from the author's own analysis (verified, promoted to fixes)

- **F1 (MEDIUM)**: readiness-no-write negative test on the dbt path -- promoted
  from recommendation to an explicit task (git-diff oracle on readiness-truth
  fields after a dbt-engine run, the spec-134 US3 pattern).
- **F2 (MEDIUM)**: engine-flag location -- resolved in the STRICT direction (the
  human-reviewed per-table working set, committed; env vars and runtime flags
  MUST NOT select the engine), which is also R1's compensating control.
- **F4 (LOW)**: redaction fixture on the dbt-engine path -- folded into T012.
- **F5 (LOW)**: commit-subject P2 conflict -- accepted as recorded; branch
  commits vanish at squash-merge and the PR title carries the compliant subject.

## What was attacked and held

- The identical-gate claim (FR-004): verified against `_build_layer` -- the gate
  call and STOP topology genuinely sit outside the engine branch. Holds.
- The naming-vs-mechanism note (dagster-dbt named, `seshat.dbt` executed):
  internally consistent and the ONLY route that preserves FR-023/FR-025. Holds.
- The open-for-human list: correctly refuses to answer the FR-007 switch,
  dbt-as-default, real-gold writes, and migration retirement. Holds.
- Evidence-schema stability (FR-008): `measured` is an open object in the
  committed schema; adding `engine`/`warehouse_updated` keys inside `measured`
  is schema-clean. Holds (verified against the schema).

## Verdict

APPROVE WITH REQUIRED FIXES -- all fixes applied on this branch in the same
review cycle (spec/plan/tasks amended; see the commit trail). The activation
reading (selectable engine, shadow-only, migrations default, gate unchanged) is
the only reading consistent with committed governance. With R1/R2 stated
honestly and their controls named, the plan is safe to implement.

Findings: HIGH 2 (R1, R2 -- both fixed), MEDIUM 3 (R3, R4, R5 -- fixed),
LOW 1 (R6 -- fixed), plus 4 adopted analysis items (F1, F2, F4 fixed; F5
accepted-as-recorded).

This review is not a ratification. RATIFICATION is a named-human edit of the
spec Status line.
