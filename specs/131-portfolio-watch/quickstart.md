# Quickstart: exercise the Portfolio Watch MVP

Goal: run the recurring summary twice on a generic multi-scope fixture and read the
baseline diff (`new` / `resolved` / `unchanged`). Read-only; no live DB; no scheduler.

This walks the MVP (US1 summary + US2 baseline diff + US3 truthful degradation). It is
generic -- any repo with governed scopes works; a filled worked example is cited as a
reference, never the schema (Principle VII).

## Preconditions

- A repo with several governed scopes at mixed readiness stages (committed
  `readiness-status.yaml` paths the spine tracks).
- Some committed evidence across dimensions: at least one source-drift-findings artifact,
  one approval seam, one dashboard-intent/semantic-audit input. Some scopes deliberately
  have NO evidence for a dimension (to exercise truthful degradation).
- No DSN configured (the MVP is offline; live-only dimensions must degrade to
  `[PENDING LIVE]`).

## Step 1 -- first run (writes the baseline)

Invoke the `portfolio-watch` skill (or the one narrow surface, e.g.
`retail watch --format json`). Expect:

- ONE summary listing EVERY governed scope with `current_stage`, per-dimension findings,
  `open_blockers`, `requires_human_attention`, and exactly one `prioritized_next_action`.
- Every `covered` finding cites a committed evidence path (INV-2).
- A dimension needing a live re-profile is `[PENDING LIVE]` (INV-3, FR-013); a scope with
  no evidence for a dimension is `not_applicable_with_reason` (FR-015).
- EVERY condition labeled `current_condition_no_baseline` -- explicitly NOT `new` -- and a
  stated note that no baseline was available (FR-009).
- A local snapshot written under `.seshat/watch/` (SNAP-1). No per-scope artifact changed
  (SC-008).
- NO numeric health/confidence/priority score anywhere (INV-1, FR-020).

## Step 2 -- change some committed evidence

Between runs, change the committed state to create each change class:

- Resolve one blocker (remove/clear its evidence) -> expect `resolved`.
- Introduce one new condition (e.g. a new committed drift finding) -> expect `new`.
- Leave one standing condition untouched -> expect `unchanged` (NOT re-alerted as new).
- Nudge a magnitude on a standing condition (e.g. missingness 3.1% -> 3.4%) -> still
  `unchanged`, with the measured value updated (SNAP-4, duplicate suppression FR-010).
- Optionally add/remove a scope -> expect a scope-level `scope_added`/`scope_removed`, not
  a misattributed condition change (FR-011).

## Step 3 -- second run (diffs against the baseline)

Invoke again. Expect:

- Each condition labeled `new` / `resolved` / `unchanged` by diffing the current keys
  against Step-1's snapshot (FR-008).
- The standing condition appears once as `unchanged` (SC-005), never re-alerted as new.
- A fresh snapshot written for the next run.
- Running Step 3 twice on the SAME committed state + SAME prior snapshot yields
  byte-identical labels (determinism, SC-006).

## Step 4 -- truthful-degradation checks (US3)

Confirm on the same run:

- Live-only dimension, no DSN -> `[PENDING LIVE]`, no fabricated comparison (FR-013).
- Evidence older than current HEAD -> `stale`, citing captured-at vs current (FR-014).
- An evidence file with an unknown schema version -> `unreadable`, naming the version;
  excluded from any clean claim (FR-016).
- A partial portfolio does NOT fail the run; empty scopes are listed (FR-017).

## What you should NOT be able to do

- No approval is recorded, no readiness stage moves to `pass`, no DB is refreshed, nothing
  is published (SC-008, FR-018).
- No grain/PII/returns/approval ruling ORIGINATES in Watch -- such conditions are relayed
  with a named owner (FR-021, SC-010).
- No `retail check` rule/gate is added; `retail check` exit behavior is unchanged
  (SC-009).

## Success = the MVP slice is useful offline

A re-runnable, baseline-diffable, truthfully-degrading read-only summary -- no scheduler,
no live DB (SC-011).
