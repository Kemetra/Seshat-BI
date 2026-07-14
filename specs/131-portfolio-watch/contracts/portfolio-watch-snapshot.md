# Contract: Portfolio Watch Prior-Run Snapshot (baseline)

**Kind**: local baseline artifact (NOT a gate, NOT a source of truth).
**Producer**: `src/seshat/portfolio_watch.py` -- written at the end of every run.
**Consumer**: the NEXT run's change classifier (the baseline it diffs against).

Modeled on `drift.py`'s baseline/observed split (research D3). The snapshot is the one
new entity that makes `new` / `resolved` / `unchanged` and duplicate-suppression possible.

## Required content (per FR-007..FR-012)

- `schema_version` -- so a future reader can mark an old/foreign snapshot `unreadable`
  and degrade to first-run behavior rather than guess (FR-016/FR-022).
- `captured_at_revision` -- the git HEAD at capture (for the summary's staleness compare).
- `conditions[]` -- the stable, magnitude-free Condition Keys present this run:
  `(scope_id, dimension, class, subject_locator)`. Magnitude is deliberately NOT in the
  key so a measured wiggle does not churn as new/resolved (research D3, duplicate
  suppression FR-010).
- The scope set implied by `conditions[]` (plus any explicitly-tracked empty scopes) so a
  scope added/removed between runs is a scope-level change, not a condition change inside a
  missing scope (FR-011).

## Diff rules (the classifier, deterministic)

Given `prior` (snapshot) and `current` (this run's keys):

- `new` = `current - prior` (only when `prior` is a usable snapshot).
- `resolved` = `prior - current`.
- `unchanged` = `current & prior`.
- If `prior` is absent OR unreadable: every current condition is
  `current_condition_no_baseline` -- explicitly NOT `new` (FR-009); the run states no
  baseline was available.

Determinism: a sorted set-diff over stable keys; identical `prior` + `current` -> identical
labels (FR-012).

## Invariants

- **SNAP-1 (local only)**: the snapshot is a local artifact under `.seshat/watch/`; it is
  never published/sent anywhere (FR-018).
- **SNAP-2 (no secret / no data)**: no DSN/secret (SEC-002); no fabricated business result
  value (SEC-003) -- it stores categorical keys + a revision, nothing more.
- **SNAP-3 (fail-closed read)**: an unreadable/corrupt prior snapshot degrades to
  "no usable baseline" (first-run behavior), never a fabricated diff (FR-009/FR-022).
- **SNAP-4 (magnitude-free key)**: a magnitude change on the same class is `unchanged`
  (reported once with an updated measured value), never a spurious new/resolved pair
  (FR-010, research D3).

## Explicitly NOT in this contract

- The snapshot is NOT a readiness `pass`, NOT an approval, NOT evidence a gate reads. It is
  a diff baseline for the recurring summary only.
- Git disposition (ignore vs opt-in commit) is a tasks-level detail (research D2); either
  way SNAP-2 holds.
