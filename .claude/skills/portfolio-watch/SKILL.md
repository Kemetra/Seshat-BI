---
name: portfolio-watch
description: >-
  Show the recurring, read-only portfolio summary for the Seshat BI repo --
  every governed scope's covered-dimension findings (source drift,
  contract/metric drift, dashboard-intent divergence, readiness, approvals,
  review), open blockers, human-attention flag, and ONE prioritized next
  action, plus a baseline diff against the last run (new/resolved/unchanged).
  Use when someone asks "run portfolio watch", "what changed since last week",
  "show me the recurring summary", or "which scopes need a human, and what
  changed". READ-ONLY and invoke-and-present only: it AGGREGATES evidence that
  shipped surfaces already produce (it runs NO new check, re-derives NOTHING);
  it persists a LOCAL baseline snapshot under `.seshat/watch/` so the next run
  can diff; it introduces NO new gate/rule/approval mechanism and emits NO
  fabricated health/confidence/priority score (every line is a shipped
  categorical status, a shipped finding enum, or a measured magnitude traced
  to a committed source).
---

# portfolio-watch

Portfolio Watch answers one recurring question: *since we last looked, what changed,
what still needs a human, and what is the one next thing to do per scope?* It is the
baseline-diffable, multi-dimension EXTENSION of the point-in-time `retail-control-room`
roll-up (F012) -- same read-only, aggregate-never-re-derive posture, plus a persisted
snapshot and the drift/semantic-drift/dashboard-intent-divergence dimensions the control
room does not fold in.

## Scope wall (read first)

- **Aggregates, never re-derives.** Every finding is sourced from a shipped surface's
  already-committed output (`drift.py`/`drift_semantics.py`, `metric_drift.py`,
  `semantic_audit.py`/`report_intent.py`, `readiness_projection.py`/`readiness_classify.py`,
  `approval_inbox.py`, `review_integration.py`/`review_pack_export.py`). It runs NO new
  check and calls NONE of those surfaces' own comparators itself -- it reads what they
  already recorded and cites the path.
- **No new gate / rule / approval mechanism.** This is a Tier-5 read/summarize/derive
  companion (roadmap binding rule), not another governance engine. `seshat check`'s rule
  inventory and exit behavior are unchanged by this skill's existence.
- **No score, ever.** Only the four readiness spine statuses, the shipped categorical
  finding enums (relayed verbatim), and measured magnitudes (counts/rates/deltas) traced
  to a committed source appear anywhere. A health/confidence/priority/quality number is
  never emitted (hard rule #9) -- if asked for one, decline and point here.
- **No live database in the MVP.** The governed-scope set comes from committed
  `mappings/*/readiness-status.yaml` paths (the same set `status_surface` /
  `readiness_projection` already track), never a live metadata query. A dimension whose
  evidence needs a live re-profile with no DSN configured is truthfully `[PENDING LIVE]`.
- **Relays Principle-V, decides none of it.** A grain/PII/returns/rollup/identity/approval
  condition is relayed with a named owner; this skill originates no ruling on any of them.
  `requires_human_attention` fires independently of category rank whenever an unmet
  approval or a relayed Principle-V/PII drift blocker is present -- it can never be buried
  by a higher-ranked, less dangerous condition.
- **"Recurring" = re-runnable + baseline-diffable, not a scheduler.** There is no cron, no
  hosted monitoring, no continuous-run surface here or planned by this skill.

## What it aggregates (the six covered dimensions)

| Dimension | Source it relays | Truthful degradation |
|---|---|---|
| Source drift | `drift.py` / `drift_semantics.py` committed findings | no live re-profile recorded -> `[PENDING LIVE]` |
| Contract/metric drift | `metric_drift.py` verdicts (a committed record of a `retail semantic-check` run) | no recorded run -> `not_applicable_with_reason` |
| Dashboard-intent divergence | `semantic_audit.py` / `report_intent.py` committed findings | no recorded run -> `not_applicable_with_reason` |
| Readiness (+ changed readiness) | `readiness_projection.py` / `readiness_classify.py` | a malformed readiness-status.yaml -> `unreadable` for that scope, never dropped |
| Stale/missing approvals | `approval_inbox.py` | (read directly; always covered or unreadable) |
| Review (tables requiring attention) | `review_integration.py` / `review_pack_export.py` committed result | no recorded result -> `not_applicable_with_reason` |

Every dimension is one of the five closed states: `covered` (cites its evidence) |
`[PENDING LIVE]` | `stale` (cites captured-at vs current HEAD) | `not_applicable_with_reason`
(names why) | `unreadable` (names the unknown schema version / read error). No state is
ever silently upgraded to `covered`, and one scope's read error never aborts the run --
a partial portfolio is summarized for the covered scopes, with the un-evidenced ones
listed in `portfolio.scopes_with_no_evidence`.

## The one prioritized next action per scope

Selected by the SHIPPED fixed `readiness_classify` rank (`approval` > `grain` >
`live_validation` > `artifact` > `readiness`) over that scope's own open readiness
blockers; the `action` text is that scope's own recorded `next_action`, RELAYED verbatim
-- never synthesized. Two scopes tying on the same top category each surface their own
action; the rank is a committed lookup, never broken by an invented number.

## The baseline diff (the genuinely new part over the control room)

Each run reads the prior local snapshot (`.seshat/watch/snapshot.json`), diffs the
current magnitude-free Condition Keys against it, and writes a fresh snapshot:

- No prior snapshot (first run, or a corrupt one) -> every condition is
  `current_condition_no_baseline` -- explicitly NOT `new` -- and the summary states that
  no baseline was available (mirrors `drift.py`'s `observed=None` first-run honesty).
- A prior snapshot exists -> each condition is `new` / `resolved` / `unchanged`. A
  magnitude wiggle on the SAME class/locator never churns as new/resolved (duplicate
  suppression) -- only a genuinely new or genuinely resolved condition moves.
- A scope added/removed between runs is reported as a scope-level change, never
  misattributed as a condition change inside a scope that no longer exists (or does not
  exist yet).

## Run it

Invoke `build_portfolio_watch_summary` / `run_portfolio_watch` from `seshat.portfolio_watch`
(the pure aggregator library), or the one narrow CLI surface for CI/agent-less use:

```
retail watch --format json
retail watch --format text
```

Present the result: per scope, `current_stage`, the covered-dimension findings (state +
class + evidence + owner where relevant), `open_blockers`, `requires_human_attention` (+
owner when set), the one `prioritized_next_action`, and the `change_labels` against the
prior snapshot. Close with the `portfolio` block (measured `scope_count` /
`scopes_requiring_attention_count` / `scopes_with_no_evidence`) and note that the run
wrote a fresh local snapshot for next time.

## No fake confidence (the guardrail)

If asked for "a portfolio health score", "a percent-ready", or "one confidence number",
DECLINE: cite hard rule #9 and this skill's frontmatter, and return the four statuses +
the shipped categorical enums + the measured magnitudes with their source paths instead.

## Read-only proof

After a run, `git status` shows zero modified files under `mappings/` (or any other
committed per-scope artifact) -- the only new/changed path is the local
`.seshat/watch/snapshot.json` (git-ignored by default). No approval is recorded, no
readiness stage moves to `pass`, no database is opened, nothing is published.

## See also

- The closest shipped sibling (same posture, no baseline/no extra dimensions):
  `.claude/skills/retail-control-room/SKILL.md` (F012). Portfolio Watch EXTENDS this
  posture; it does not fork or replace it.
- The aggregator library + snapshot format: `src/seshat/portfolio_watch.py`.
- The tool doc: `docs/tools/portfolio-watch.md`.
- The feature spec: `specs/131-portfolio-watch/spec.md` (+ `data-model.md`, `contracts/`).
- The gates it reads (never re-runs): `retail-govern` / `seshat check`,
  `retail-semantic-check`, `retail-validate`; the readiness model:
  `docs/readiness/readiness-model.md`; the source-drift precedent:
  `docs/readiness/source-drift.md`.
- The ratified CLI-vs-skill decision behind the one narrow `retail watch` surface:
  `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.
