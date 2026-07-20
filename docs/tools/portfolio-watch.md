# Portfolio Watch -- usage and boundary

- **Status:** Runtime slice shipped: `retail watch` + the `portfolio-watch` skill
  (spec 131).
- **Authority category:** aggregation/summary layer / `advisory`, `read-only`.

## What it does

Portfolio Watch answers one recurring question: *since we last looked, what
changed, what still needs a human, and what is the one next thing to do per
scope?* It is a **read-only aggregation/summary layer**, not a new governance
engine: it derives every finding from evidence the shipped surfaces already
produce, adds no new gate, no new `seshat check` rule, and no new approval
mechanism.

It is the multi-dimension, baseline-diffable EXTENSION of the point-in-time
`retail-control-room` roll-up (F012): same read-only, aggregate-never-re-derive
posture, plus (a) a persisted local baseline snapshot so the next run can
distinguish `new` from `unchanged` and can report `resolved`, and (b) coverage
of the source-drift, contract/metric-drift, and dashboard-intent-divergence
dimensions the control room does not fold in today.

```bash
retail watch --format json
retail watch --format text
```

## What it aggregates (never re-derives)

| Dimension | Shipped source it relays |
|---|---|
| `source_drift` | `drift.py` / `drift_semantics.py` committed findings |
| `contract_metric_drift` | `metric_drift.py` verdicts (a committed record of a `retail semantic-check` run) |
| `dashboard_intent_divergence` | `semantic_audit.py` / `report_intent.py` committed findings |
| `readiness` (+ changed readiness) | `readiness_projection.py` / `readiness_classify.py` |
| `approvals` (stale/missing) | `approval_inbox.py` |
| `review` | `review_integration.py` / `review_pack_export.py` committed result |

The governed-scope set is enumerated from the committed
`mappings/*/readiness-status.yaml` paths -- the SAME set `status_surface` /
`readiness_projection` already track (FR-002). It is NOT the live
`portfolio_enumerate` DB path: the MVP opens no database connection.

## The four degradation states (the closed, truthful set)

Every dimension is exactly one of:

- **`covered`** -- evidence read cleanly; carries a citation (evidence path +
  `source_surface`) and, when applicable, a shipped categorical `class` +
  a measured magnitude.
- **`[PENDING LIVE]`** -- the dimension's evidence needs a live re-profile/DB
  leg and none is configured (consistent with `docs/readiness/source-drift.md`).
  Never a fabricated comparison.
- **`stale`** -- evidence captured at a revision older than the current
  HEAD/`source_revision`; cites captured-at vs current. Never presented as a
  current condition.
- **`not_applicable_with_reason`** -- no shipped producer for this scope, or no
  evidence has been produced yet; names the reason. Never counted covered/clean.
- **`unreadable`** -- the evidence artifact declares a schema version this
  feature cannot parse, or a per-scope read error occurred; names the unknown
  version/error. Never guessed, never upgraded to `covered`.

A per-scope/per-dimension read error degrades only that one cell; it never
aborts the whole run -- a partial portfolio (some scopes fully evidenced, some
empty) is always summarized, with the empty ones listed in
`portfolio.scopes_with_no_evidence`.

## The one prioritized next action per scope

Selected by the SHIPPED fixed `readiness_classify` category rank (`approval` >
`grain` > `live_validation` > `artifact` > `readiness`) -- a committed lookup,
never a computed priority. The `action` text is that scope's own recorded
`next_action` (the readiness projection's computed field), RELAYED verbatim,
never synthesized. Two scopes tying on the same top category each surface
their own action; a tie is reported, never broken by an invented number.

`requires_human_attention` is set INDEPENDENTLY of that rank whenever a scope
carries an unmet/invalid approval OR a relayed Principle-V drift blocker
(including a `pii_surface_drift`-flavored condition) -- always naming the
responsible owner. This independence matters because the shipped
`readiness_classify` rank has no PII bucket: without it, a PII blocker could
keyword-fall to the lowest-ranked bucket and be buried under a higher-ranked,
less dangerous condition.

## The baseline diff -- "recurring" means re-runnable + baseline-diffable

Each run reads the prior local snapshot (`.seshat/watch/snapshot.json`, a
magnitude-free set of Condition Keys `(scope_id, dimension, class,
subject_locator)`), diffs the current run's keys against it, and writes a
fresh snapshot:

- **No prior snapshot** (first run, or a corrupt/unreadable one) -- every
  condition is `current_condition_no_baseline`, explicitly NOT `new`; the
  summary states no baseline was available (mirrors `drift.py`'s
  `observed=None` first-run honesty -- never a fabricated diff).
- **A prior snapshot exists** -- each condition is `new` (present now, absent
  before) / `resolved` (absent now, present before) / `unchanged` (present in
  both -- reported once, never re-alerted). The key is deliberately
  magnitude-free: a measured value changing on the SAME class/locator does
  not churn as new/resolved (duplicate suppression).
- **A scope added/removed between runs** is reported as a scope-level change
  (`scope_added` / `scope_removed`), never misattributed as a condition change
  inside a scope that does not exist in one of the two runs.

There is **no scheduler and no hosted/continuous-monitoring surface** here or
planned by this feature. "Recurring" means exactly: re-runnable, and
diffable against the last local run -- nothing more.

## No fake confidence / no gate / no DB (the guardrails)

- No numeric health/confidence/priority/quality score appears anywhere --
  only the four readiness spine statuses, the shipped categorical finding
  enums (relayed verbatim), and measured magnitudes traceable to a committed
  source (hard rule #9).
- No new `seshat check` rule, gate, or approval mechanism is introduced;
  `seshat check`'s rule inventory and exit behavior are unchanged.
- No live database connection is opened in the MVP; a dimension needing one
  degrades truthfully to `[PENDING LIVE]`.
- No Principle-V ruling (grain, PII publish-safety, business-rollup/segment
  mapping, returns identity, product identity, approval sign-off) originates
  here -- every relayed condition names the responsible owner.

## Read-only proof

After a run, `git status` shows zero modified files under `mappings/` (or any
other committed per-scope artifact); the only new/changed path is the local
`.seshat/watch/snapshot.json` (git-ignored by default -- see `.gitignore`). No
approval is recorded, no readiness stage moves to `pass`, no database is
refreshed, nothing is published.

## See also

- The agent-facing skill: `.claude/skills/portfolio-watch/SKILL.md`.
- The aggregator library + snapshot format: `src/seshat/portfolio_watch.py`.
- The CLI surface: `src/seshat/cli/commands/watch.py` (`retail watch`).
- The feature spec: `specs/131-portfolio-watch/spec.md` (+ `data-model.md`,
  `contracts/portfolio-watch-summary.md`, `contracts/portfolio-watch-snapshot.md`).
- The closest shipped sibling (point-in-time, no baseline):
  `.claude/skills/retail-control-room/SKILL.md` (F012). Portfolio Watch EXTENDS
  this posture; it does not fork or replace it.
- The ratified CLI-vs-skill decision behind the one narrow `retail watch`
  surface: `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.
