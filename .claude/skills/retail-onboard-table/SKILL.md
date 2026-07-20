---
name: retail-onboard-table
description: >-
  Walk a NEW raw retail table across the FIRST readiness transition -- Source Ready
  (Stage 1) through Mapping Ready (Stage 2) -- and seed its per-table
  readiness-status, in the Seshat BI repo. Use when someone says
  "onboard <schema>.<table>", "take this new table from nothing to a reviewed map",
  or "start the readiness journey for a table". This is the stage-transition FRONT
  DOOR: it sequences profile -> map -> gate, writes the readiness-status record, and
  STOPS at Mapping Ready. It DELEGATES the five mapping artifacts to the
  `source-mapping` skill (it does not re-implement mapping); it NEVER writes
  `silver.*` SQL, NEVER self-grants the gate approval, and NEVER answers a
  Principle-V judgment call (grain, PII, business rollup, product identity).
---

# retail-onboard-table

The onboarding front door for ONE table's first two readiness stages. The kit
already ships the verb that authors the mapping artifacts (`source-mapping`) and the
conductor that sequences every verb end-to-end (`retail-orchestrate`). This skill is
the stage-scoped composition between them: "I have a new raw table -- walk me from
nothing to a reviewed map." It advances **Source Ready -> Mapping Ready**, seeds the
per-table `readiness-status.yaml`, and STOPS. It is a procedure the agent performs
(agent-first, Principle I); `seshat check` and the read-only profile are gates it
CALLS, not a CLI subcommand.

## Scope boundary (read first)

- **Agent-first, no CLI.** This is a SKILL the agent runs; it adds no `retail`
  subcommand and no Python.
- **ENTERS at Source Ready, EXITS at Mapping Ready.** The terminal state is Mapping
  Ready -- the three gate artifacts committed and either `mapping_ready: blocked`
  (review pending, the common case) or `mapping_ready: pass` (only after a HUMAN has
  recorded approval). Both are successful wizard runs.
- **NEVER crosses into Silver Ready** (Principle IV, roadmap rule #2). It writes no
  `silver.*` SQL, no migration, and never calls `retail-build-warehouse`. Its last
  action is to seed/update the readiness-status, state the next allowed action, and
  STOP.
- **NEVER self-grants approval or invents a judgment call** (Principle V). The four
  reserved seams -- grain, PII publish-safety, business rollup/segment, product
  identity -- are PROPOSED with a data fact and raised as `unresolved-questions.md`
  rows; the wizard stops there.
- **No fake confidence.** Readiness is the four explicit statuses
  (`not_started` | `blocked` | `warning` | `pass`) + `evidence[]` +
  `blocking_reasons[]`. No numeric score (roadmap rule #9).
- **Delegates mapping; does not duplicate it.** Stage 2 invokes `source-mapping` to
  author the five artifacts. This skill owns the WALK and the readiness bookkeeping,
  not the mapping procedure.
- ASCII only, UTF-8 no BOM (`->` arrows, `'' OR NULL`).

## Run-state: read mappings/<table>/ FIRST (no new state file)

Compute the current stage from what is already on disk -- there is NO onboarding
state file to create (mirrors `retail-orchestrate`'s run-state rule):

| What you observe | Current stage / action |
|------------------|------------------------|
| No `mappings/<table>/` dir | Start at **Stage 1** (profile). |
| `source-profile.md` present, no `source-map.yaml` | Resume at **Stage 2** (delegate to `source-mapping`). |
| The five artifacts present, `unresolved-questions.md` shows `Gate status: OPEN` (or open rows) | **STOPPED at the gate** -- report the open questions; do not overwrite, do not advance. |
| `Gate status: CLEARED`, zero open rows, an `approvals[]` entry recorded | **Mapping Ready reached** -- promote `mapping_ready: pass`; state Silver Ready is the next (out-of-scope) stage; STOP. |

Resume from the first incomplete artifact; NEVER clobber a committed (reviewed) one.
You may READ `Gate status`; you may NOT write `CLEARED` yourself (that is the
reviewer's action).

## Stage 1 -- Source Ready (profile + PROPOSE semantics)

Drive the mechanical profile over a READ-ONLY connection and record into
`mappings/<table>/source-profile.md` (definition-of-done = `source-ready.md` `pass`):

- row count + column count;
- per-column missingness measured as `'' OR NULL` (never `IS NULL` alone -- RC5);
- candidate-key uniqueness proof (does the proposed PK hold on the data?);
- returns-column population.

Semantic rows (what each column MEANS) are PROPOSED for human confirmation, never
invented. Record `source_ready: pass` with `source-profile.md` as evidence when the
mechanical numbers are measured; `warning` in deferred-boundary mode (below); or
`blocked` with the concrete reason if a required number is unmeasurable -- and then
do NOT enter Stage 2 (no mapping on an unprofiled source).

## Stage 2 -- Mapping Ready (delegate to source-mapping)

Invoke the `source-mapping` skill to author the five artifacts under
`mappings/<table>/` (definition-of-done = `mapping-ready.md`'s artifact set):

- `source-map.yaml` -- grain, PK, every column's `pii:` flag, gold placement;
- `assumptions.md` -- RC1-RC16 adopted/deviated, each deviation citing a data fact;
- `unresolved-questions.md` -- the open judgment calls (`Gate status: OPEN` until a
  human clears it);
- the `reconciliation-report.md` blank (the live-acceptance run, filled later).

Do NOT duplicate the mapping procedure -- it lives in `source-mapping`. The wizard
sequences the call and then does the readiness bookkeeping below.

## Readiness-status bookkeeping

Seed/update the per-table status from `templates/readiness-status.yaml` at the
canonical `mappings/<table>/readiness-status.yaml` (ADR 0004 -- co-located with the
mapping artifacts, spans all seven stages). The wizard is the FIRST writer of this
file. Set:

- `source_ready`: `pass` (mechanical numbers measured) / `warning` (deferred mode) /
  `blocked` (unmeasurable) -- with `evidence[]` or `blocking_reasons[]`;
- `mapping_ready`: `blocked` (review pending) until a human records approval;
- `current_stage`, `next_action`, `last_checked_at`, `checked_by`.

Every `pass` MUST carry `evidence[]`; every `blocked` MUST carry
`blocking_reasons[]`; emit NO numeric confidence score.

## Human seams -- HARD-STOP (Principle V; the wizard proposes, a human decides)

Each is a judgment call the agent cannot settle from data alone. PROPOSE it with the
supporting data fact, raise an `unresolved-questions.md` row with a NAMED owner, set
the matching `blocking_reasons[]`, and STOP -- NEVER satisfiable by a silent default:

| Seam | Trigger | Propose (with data fact) | Owner |
|------|---------|--------------------------|-------|
| **Grain** | candidate PK not unique on the rows | report the duplicate count; propose the finer grain / composite PK -- never collapse or pick silently | analyst |
| **PII publish-safety** | a `pii:true` candidate column | propose the default (drop before the BI layer, RC4); raise the publish-safety question | governance |
| **Business rollup / segment** | a categorical needing a value->group mapping | NEVER invent the mapping; raise it for the analyst-supplied table; default unmapped -> `UNMAPPED` | analyst |
| **Product identity** | which column authoritatively identifies the entity (or two columns disagree) | report the conflict; never assert identity | analyst / data owner |

**Conflicting answer rule:** if an analyst answer contradicts a profiled data fact,
surface the conflict and STOP to reconcile -- do not proceed (evidence-cross-check).

## Terminal: Mapping Ready -- STOP

When the artifacts are authored and the gate is `OPEN` (review pending): emit the
reconciliation blank, set `mapping_ready: blocked`, state the SINGLE next allowed
action ("human review + approval of the map"), and explicitly confirm the wizard
wrote NO `silver.*` and self-granted NO approval. When `Gate status: CLEARED` +
`approvals[]` already exist (a human approved): promote `mapping_ready: pass`
(evidence = the artifacts + the approval), state "Mapping Ready reached; the next
stage is Silver Ready / `retail-build-warehouse` -- OUT of this wizard's scope", and
STOP. The wizard never authors silver.

## Deferred-boundary mode (no DSN or no `db` extra)

If no DSN is configured or the `db` extra is absent: do NOT traceback and do NOT
fabricate profile numbers. Mark the mechanical rows `[PENDING LIVE PROFILE]`, record
`source_ready: warning` (never `pass`), and print the enable steps:
`pip install 'retail[db]'`, then set `DATABASE_URL` (or `ANALYTICS_DB_*`) in the
git-ignored `.env` -- never commit a real DSN. The semantic stop-and-ask and the gate
stop still run (they need no DB).

## Generic, not C086

This skill and the onboarding checklist are GENERIC (roadmap rule 7). No
C086/pharmacy specifics (billing codes, segment rollups, PII column names, pharmacy
grain keys) appear here -- placeholders only. A worked example is CITED as a filled
instance (see the filled worked examples under `docs/worked-examples/`), never copied.

## See also

- The two stages spanned: `docs/readiness/source-ready.md`,
  `docs/readiness/mapping-ready.md`.
- The reviewable definition-of-done: `docs/readiness/onboarding-checklist.md`.
- The spine + state model: `docs/readiness/readiness-model.md`,
  `docs/readiness/readiness-pipeline.md`; `templates/readiness-status.yaml`.
- The delegated mapping leg: `.claude/skills/source-mapping/SKILL.md`.
- The downstream build verb (out of scope here):
  `.claude/skills/retail-build-warehouse/SKILL.md`.
- The roadmap row: `docs/roadmap/roadmap.md` (F006, Layers 1-2, Source -> Mapping).
- Principles: `.specify/memory/constitution.md` I, IV, V, VII, VIII, IX.

## Orchestration

When a table is driven end-to-end, the `retail-orchestrate` conductor invokes this
wizard as its Source -> Mapping leg (Phases 1-4). This skill does that leg and STOPS
at Mapping Ready; the cross-table self-heal loop (run gate -> classify -> auto-fix
mechanical / HARD-STOP judgment calls -> re-run) lives ONLY in `retail-orchestrate`,
never here. Mapping-gate approval is the reviewer's action; no loop self-grants it.
