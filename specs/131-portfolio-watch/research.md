# Phase 0 Research: Portfolio Watch

All decisions resolve plan-time unknowns the spec deferred. Each cites a shipped
pattern (Principle VI: defaults then deviations). No NEEDS CLARIFICATION remain.

---

## D1 -- Composition shape: a pure library module composing shipped readers

- **Decision**: Implement the aggregator as a single pure, stdlib-only module
  `src/seshat/portfolio_watch.py` that COMPOSES the shipped readers, and an
  agent-facing skill `.claude/skills/portfolio-watch/` that invokes and presents it.
- **Rationale**: This is exactly the shipped pattern in `agent_next.py`, whose
  docstring says "This module is a COMPOSITION, not a second source of truth" and
  reuses `run_next.build_run_next_response` + `status_surface.build_status_projection`
  verbatim. `readiness_projection.py` does the same over `agent_next` + `status_surface`
  + `disclosure`. Portfolio Watch is the portfolio-level sibling: it joins the existing
  per-scope reader outputs, never re-derives a check (FR-003).
- **Alternatives considered**: (a) A new skill with no library -- rejected: the
  new/resolved/unchanged diff and the deterministic next-action selection must be
  unit-testable and byte-deterministic (SC-006), which a prose skill cannot guarantee.
  (b) Extending `retail-control-room` in place -- rejected: the control room is a
  shipped skill (a doc, hard rule #8) with no library and no baseline; adding a
  persisted diff there would fork its scope. Watch reuses its posture, not its file.

## D2 -- Local artifact location + git disposition

- **Decision**: Write the summary and the prior-run snapshot under `.seshat/watch/`
  (the existing kit-state namespace). The snapshot is a **local baseline**; whether it
  is git-ignored or committed is resolved as: the snapshot MAY be committed so the diff
  is reproducible in CI/review, but MUST carry no secret/DSN (SEC-002) and no fabricated
  data (SEC-003). Default: git-ignore the machine-local run output, allow an opt-in
  committed snapshot for teams that want a reviewable baseline. Final gitignore line is
  a tasks-level detail; the constitution's PBIP gitignore baseline is untouched.
- **Rationale**: `.seshat/` is the shipped location for kit state (Decision Store,
  approval state). Modeling the snapshot as a baseline mirrors `drift.py`'s
  baseline/observed split. Keeping it local honors "LOCAL ARTIFACTS ONLY" (FR-018).
- **Alternatives considered**: A new top-level dir (rejected -- proliferates state
  locations); per-scope files under `mappings/<table>/` (rejected -- Watch is
  portfolio-level and must never write a per-scope artifact, SC-008).

## D3 -- The baseline diff (new/resolved/unchanged) modeled on drift.py

- **Decision**: The change classifier is a pure set-diff of stable **condition keys**
  between the current summary and the prior snapshot: `new` = key present now, absent
  before; `resolved` = absent now, present before; `unchanged` = present in both. The
  FIRST run (no snapshot) or an unreadable snapshot yields "current condition, no
  baseline" -- explicitly NOT `new` -- exactly the `observed=None` branch in
  `drift.classify_drift` (which fabricates no findings when there is nothing to compare).
- **Rationale**: `drift.py` already establishes the honest-diff pattern: an absent
  comparison target produces no fabricated result, not a guess. Reusing that shape makes
  FR-009 and duplicate-suppression (FR-010) fall out of the diff, and determinism
  (FR-012) is a property of a pure sorted set-diff over stable keys.
- **Condition key**: a stable tuple of (scope id, dimension, categorical class, subject
  locator) -- e.g. `(bronze.orders, source_drift, column_removed, order_note)`. It carries
  NO magnitude in the key (a magnitude change on the SAME class is reported as the same
  `unchanged` condition with an updated measured value, not a spurious new alert). This is
  the deliberate duplicate-suppression rule.
- **Alternatives considered**: keying on the full finding text incl. magnitude (rejected:
  a 3.1% -> 3.2% missingness wiggle would re-alert as new/resolved churn -- the opposite
  of duplicate suppression). Hashing the whole per-scope block (rejected: too coarse; one
  changed field would relabel every condition in the scope).

## D4 -- The "one prioritized next action per scope": the shipped fixed rank

- **Decision**: Select the one next action per scope by the SHIPPED fixed categorical
  rank in `readiness_classify` (`approval` > `grain` > `live_validation` > `artifact` >
  `readiness`), then RELAY that scope's own recorded `next_action` (from the readiness
  projection / `agent_next` per-table document). Watch never composes or synthesizes a
  new action string.
- **Rationale**: `readiness_classify`'s module docstring says "The category ORDER is the
  load-bearing artifact ... a committed lookup, never a computed/synthesized value (hard
  rule #9)"; `approver_view.py` already orders a signer's view by this exact rank. Reusing
  it makes FR-005 satisfiable without a score, and the relayed `next_action` already
  exists per scope (`readiness_projection._table_projection` -> `next_action`).
- **Alternatives considered**: a numeric severity weight (rejected -- a score, forbidden
  by FR-020/hard rule #9); most-recent-first (rejected -- recency is not priority and is
  not committed). Ties on the top category are REPORTED (both scopes surface their own
  action), never broken by a synthesized number (spec Edge Cases).

## D5 -- Dimension -> shipped source map + truthful degradation

- **Decision**: Each covered dimension is sourced from exactly one shipped surface and
  carries a truthful state when its evidence is not cleanly available:
  - source drift -> `drift.py` / `drift_semantics.py` committed findings; live re-profile
    absent -> `[PENDING LIVE]` (per `docs/readiness/source-drift.md`).
  - contract/metric drift -> `metric_drift.py` verdicts over committed contracts + TMDL;
    an ESCALATE verdict is relayed as an escalation condition.
  - dashboard-intent divergence -> `semantic_audit.py` + `report_intent.py` categorical
    findings (committed artifacts only, no DB).
  - readiness / changed readiness -> `readiness_projection.py` (four-status, evidence,
    blocking_reasons, next_action).
  - stale/missing approvals -> `approval_inbox.py` open/invalid seams.
  - tables requiring attention / review -> `review_integration.py` change-review result.
  - governed-scope set -> the readiness paths the spine tracks (NOT the live
    `portfolio_enumerate` DB path, which needs a DSN; see D6).
- **Degradation states** (the closed set, all truthful): `covered` (with citation) |
  `[PENDING LIVE]` (live leg unavailable) | `stale` (evidence predates HEAD/source_revision)
  | `not_applicable_with_reason` (no producer / no evidence yet) | `unreadable` (schema
  version unknown). No state is ever silently upgraded to covered/clean.
- **Rationale**: Directly satisfies FR-013..FR-017 and SC-002 by binding every dimension
  to a verified shipped producer (capability classification) and reusing the
  already-shipped `[PENDING LIVE]` honesty. `not_applicable_with_reason` is a member of the
  shipped `semantic_audit` closed enum, so the vocabulary is not invented.
- **Alternatives considered**: silently omit an unavailable dimension (rejected -- reads as
  clean, violates FR-015); block the whole run on any partial coverage (rejected --
  violates FR-017).

## D6 -- No live DB in the MVP; scope set from committed readiness paths

- **Decision**: The MVP reads committed evidence + pure readers only; it does NOT open a
  connection. The governed-scope set is enumerated from the committed readiness-status
  paths the spine already tracks (the same source `status_surface`/`readiness_projection`
  use), NOT from `portfolio_enumerate`'s live DB-metadata path.
- **Rationale**: SEC-001 + Principle VIII. `portfolio_enumerate` is a live surface
  (`requirements: [database, optional-dependency]`); using it would put a DSN in Watch's
  path. The committed readiness paths already define "the scopes the spine tracks"
  (FR-002). Any opt-in live leg is a separate later concern (FR-024).
- **Alternatives considered**: use `portfolio_enumerate` for the scope set (rejected --
  drags in the DB requirement + DSN-redaction surface for no MVP benefit; the committed
  paths are the authoritative governed-scope set anyway).

## D7 -- Interface: skill-driven + at most one narrow read-only CLI surface

- **Decision**: Ship the agent-facing interface as the `portfolio-watch` skill (sibling of
  `retail-control-room`). Add AT MOST ONE narrow, read-only, machine-readable surface
  (e.g. `retail watch --format json`) mirroring the ratified `status --format json`
  precedent, for CI/agent-less consumption. Do NOT add a `watch` verb family.
- **Rationale**: `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md` RATIFIES Option B
  (skill-driven; CLI stays a narrow gate) and explicitly blesses "one deliberate CLI
  addition being a small machine-readable status surface (`status --format json`) -- NOT a
  broad verb surface." FR-023 encodes this. The shipped read-only projection verbs
  (`retail next --format json`, `retail approvals`) are the precedent shape.
- **Alternatives considered**: a full `seshat watch build/show/diff` family (rejected --
  cuts against hard rule #1 and the ratified decision); skill-only with no machine surface
  (acceptable fallback, but the one JSON surface is the sanctioned exception for CI use).

## D8 -- No new gate/rule/approval; scheduling deferred

- **Decision**: Add NO `retail check` rule, NO gate, NO approval mechanism. Watch is a
  Tier-5 read/summarize/derive companion. "Recurring" in the MVP = re-runnable +
  baseline-diffable; any scheduler / hosted monitoring is a separate, later, explicitly
  scoped spec.
- **Rationale**: FR-019/FR-024 + the roadmap Tier-5 binding rule ("a module/adapter may
  READ, SUMMARIZE, VISUALIZE, write DERIVED evidence ... but MUST NOT create truth").
  `retail-control-room`'s skill states the same: "introduces no new validator and no new
  gate (roadmap rule 8; Principle VIII)." A scheduler is not a repo feature and would
  over-scope.
- **Alternatives considered**: a `WATCH1` static rule that fails CI when the summary is
  stale (rejected -- that IS a new gate/governance engine, the exact thing the goal
  forbids); an in-repo cron (rejected -- FR-024, out of MVP).

---

## Summary of resolved unknowns

| Unknown (spec-deferred) | Resolved by |
|---|---|
| Composition shape / where the logic lives | D1 (pure module + skill, per `agent_next`) |
| Snapshot storage location + git disposition | D2 (`.seshat/watch/`, local; opt-in commit) |
| How new/resolved/unchanged is computed without churn | D3 (stable condition-key set-diff, magnitude-free key) |
| How "one next action" is prioritized without a score | D4 (shipped `readiness_classify` fixed rank + relayed `next_action`) |
| Which surface feeds each dimension + degradation | D5 (dimension->source map + closed degradation set) |
| Whether the MVP touches a live DB | D6 (no; scope set from committed readiness paths) |
| CLI vs skill interface | D7 (skill + at most one narrow JSON surface, ratified Option B) |
| New gate/rule/approval? scheduling? | D8 (none; recurring = re-runnable, scheduler deferred) |
