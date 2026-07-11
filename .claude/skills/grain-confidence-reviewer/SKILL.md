---
name: grain-confidence-reviewer
description: >-
  Surface grain-uniqueness CONFIDENCE as evidence and DIFF two source-map.yaml
  versions for a Mapping Ready reviewer in the Seshat BI repo. Use when
  someone asks "is the grain confident?", "what changed in this map?", or is about to
  review/approve a table's mapping. It READS the already-measured PK-uniqueness signal
  (PkProof from profile.py / the committed source-profile.md) and reads two map
  versions from git, then RENDERS a grain-confidence card + a semantic diff and STOPS
  for the human. "Confidence" here is status + evidence + blockers, NEVER a numeric
  score. It NEVER approves the gate, NEVER edits source-map.yaml, NEVER picks a new
  PK/grain, and NEVER auto-resolves a grain/PII/rollup judgment call (Principle V).
---

# grain-confidence-reviewer

The Mapping Ready gate turns on one load-bearing fact: **is the declared grain
actually unique on the data?** That fact is already measured (`profile.py`'s
`PkProof`) and the diff inputs are two committed `source-map.yaml` versions. This skill
SURFACES both for a reviewer -- a grain-confidence card and a semantic mapping diff --
and STOPS at the human seam. It deepens the shipped mapping gate (roadmap Layer 3); it
adds no new gate, no new Python, no numeric score.

## Scope boundary (read first)

- **Surfaces and STOPS.** It RENDERS evidence (a card, a diff) for a human reviewer; it
  does NOT write an approval, does NOT write `Gate status: CLEARED`, does NOT edit
  `source-map.yaml` to clear a finding, and does NOT pick a new candidate PK or widen a
  grain on the human's behalf.
- **"Confidence" is evidence + status + blockers, NEVER a number.** No `0.87`, no auto
  high/medium/low label. Grain confidence is reported as exactly ONE of the four
  readiness statuses (`not_started` | `blocked` | `warning` | `pass`) with the measured
  signal cited as evidence and any blockers attached (roadmap rule #9; "No fake
  confidence", readiness-model.md).
- **Reuses the measured signal; re-implements nothing.** It reads `PkProof`
  (`total`, `distinct_pk`, `null_pk`, `is_unique`); it never writes its own uniqueness
  query.
- **Judgment calls are the human's** (Principle V): grain ambiguity, PII publish-safety,
  business rollups -- surfaced, never auto-resolved.
- Cite Principles IV (mapping gate), V (human seam), VII (generic), VIII (live deferred).
- ASCII only, UTF-8 no BOM.

## US1 -- Grain confidence card

### Read the measured signal
Read the Candidate-grain/PK numbers from `mappings/<table>/source-profile.md`; OR, at
the deferred live boundary, re-run `src/seshat/profile.py` over a READ-ONLY connection
(`resolve_dsn` + `make_psycopg2_runner`, the `db` extra). Reuse `PkProof`
(`total`, `distinct_pk`, `null_pk`, `is_unique`) -- do NOT re-implement the uniqueness
query.

### Render the card
Show the four numbers as cited `evidence[]`, plus any `blocking_reasons[]`, and render
exactly ONE readiness status. NO numeric score, NO high/medium/low label.

```
Grain confidence -- <schema>.<table>
  declared grain : <one row = one ...>
  PK columns     : [<pk_col_a>, <pk_col_b>]
  total          : <COUNT(*)>
  distinct_pk    : <COUNT(DISTINCT pk)>
  null_pk        : <NULLs in any PK column>
  is_unique      : <true|false>
  status         : <not_started | blocked | warning | pass>
  evidence       : ["source-profile.md Candidate-grain/PK", total/distinct_pk/null_pk]
  blocking_reasons: [<concrete reason(s), or empty>]
  note           : human approval in approvals[] is still required (the skill never self-grants)
```

### Status mapping (explicit, evidence-only)

| Signal | Status | Reason |
|--------|--------|--------|
| `is_unique=true` AND `null_pk=0` | supports `pass` | the grain holds on the data -- but a human must still record approval in `approvals[]` |
| `is_unique=false` (i.e. `distinct_pk < total`) | `blocked` | "grain not confirmed unique on data: COUNT(DISTINCT pk) < COUNT(*)" -> raise the grain question |
| `null_pk > 0` | `blocked` | "NULLs present in PK columns" -> raise the grain question |
| No live profile yet (no DSN / no `db` extra) | `blocked` | evidence is `[PENDING LIVE PROFILE]` -> print enable steps; never fabricate |
| A human-recorded, data-justified deviation (e.g. an accepted known-duplicate handled in silver) | `warning` | recorded caveat; NEVER auto-promoted to `pass` |

### Record into the readiness status
The card's evidence/blockers are recorded into the Mapping Ready stage of
`mappings/<table>/readiness-status.yaml` (ADR 0004; shaped to
`templates/readiness-status.yaml`) as `evidence[]` / `blocking_reasons[]` -- no new
state field. If a numeric `score` is ever shown it MUST be marked OPTIONAL and cite the
evidence it derives from (default: omit it).

### Deferred / live-boundary mode
No DSN / no `db` extra: report `[PENDING LIVE PROFILE]` and status `blocked` (evidence
missing); print the enable steps (`pip install 'retail[db]'`; set `DATABASE_URL` or
`ANALYTICS_DB_*` in the gitignored `.env`; never commit a real DSN). Do NOT fabricate a
result (Principle VIII).

## US2 -- Mapping diff (two source-map.yaml versions)

### Read two versions
Identify each `source-map.yaml` version by a git ref and/or path. If only one version
exists (the first map), degrade gracefully to "initial version -- nothing to diff" and
still render the US1 card.

### Semantic grouping (foreground the load-bearing fields)
Group changes under these headings; list additions / removals / moves per group:

- **`meta.grain`** -- any change to the grain statement.
- **`meta.primary_key`** -- PK column added/removed; a PK column `rename_to` change; a
  composite-PK reorder (surface it, note uniqueness is unchanged, the human confirms).
- **column `pii:` flags** -- every `false->true` / `true->false` flip.
- **`gold_placement`** -- every move (e.g. `fact_measure -> dim:...`, a degenerate-dim
  move, a `gold_star` reshape adding/removing a dimension).

List non-load-bearing edits (a comment, a `reason:` wording change) SEPARATELY, for the
audit trail.

### Re-approval flag
Any change to `meta.grain`, `meta.primary_key`, or a `pii:` flag is flagged
**"REQUIRES RE-APPROVAL"** -- it invalidates any prior Mapping Ready `approvals[]`
entry; the gate MUST be re-reviewed. Non-load-bearing edits state no re-approval is
forced, but are still listed.

### PII-regression guard
A `pii:true` column whose `decision` is no longer `drop` after the edit is raised as a
GOVERNANCE `blocking_reason` (Principle V PII seam) -- never passed through silently.

### Diff edge cases
- **No prior version** -> "initial version -- nothing to diff"; still render the card.
- **PK column renamed** -> surface under `primary_key`; flag re-approval.
- **Composite-PK reorder only** -> surface; note uniqueness unchanged; human confirms intent.
- **Profile stale vs current map** -> if the committed profile's PK columns no longer
  match `source-map.yaml`'s `primary_key`, report the mismatch as a BLOCKER (the
  measured signal does not back the current grain claim).
- **`gold_star` reshape** -> surface under `gold_placement`; the human judges impact.

## US3 -- Judgment calls HARD-STOP (Principle V; surface, never resolve)

Each HARD-STOPS and is raised to / points at `mappings/<table>/unresolved-questions.md`
with the NAMED owner; none is satisfiable by a silent default:

| Trigger | Action | Owner |
|---------|--------|-------|
| Grain not unique on data (`is_unique=false` / `null_pk>0`) | raise the grain question; NEVER auto-pick a new PK or widen the grain | analyst |
| A `pii:` flag moving toward publish, or a `pii:true` column no longer `drop` | route to governance sign-off; NEVER declare a column publish-safe | governance |
| A business-rollup / segment change | the analyst supplies the value->group table; NEVER invent it | analyst |
| Any request to "just approve" the gate | surface evidence + blockers; state approval is the human's recorded `approvals[]` action | human (analyst/governance) |

The skill never writes an approval, never writes `Gate status: CLEARED`, never edits
`source-map.yaml` to clear a finding, and never picks a new candidate PK or grain. It
surfaces and stops.

## Generic, not C086

All examples and placeholders are GENERIC (roadmap rule 7). No C086/pharmacy specifics
(billing codes, segment names, PII column names, per-table grain keys) appear here.
C086 is CITED as the first filled instance, never copied inline.

## See also

- The stage this advances: `docs/readiness/mapping-ready.md`; the model + "No fake
  confidence" rule: `docs/readiness/readiness-model.md`.
- The measured signal reused as evidence: `src/seshat/profile.py` (`PkProof`); the
  profile artifact: `templates/source-profile.md` (Candidate grain & PK section).
- The map being diffed + its human seam: `templates/source-map.yaml`,
  `templates/unresolved-questions.md` (`Gate status`); the verdict shape:
  `templates/readiness-status.yaml`.
- The verbs this sits beside: `.claude/skills/source-mapping/SKILL.md`,
  `.claude/skills/retail-orchestrate/SKILL.md`; the live sibling:
  `.claude/skills/retail-validate/SKILL.md`.
- Principles: `.specify/memory/constitution.md` IV (mapping gate), V (human seam), VII
  (generic), VIII (live deferred); roadmap: `docs/roadmap/roadmap.md` (F008). A filled
  instance: a worked example under `docs/worked-examples/`.

## Orchestration

When a table is driven end-to-end, the `retail-orchestrate` conductor may call this
reviewer at the Mapping Ready review seam to surface the grain-confidence card + the
mapping diff before a human approves. This skill stays single-purpose: it surfaces
evidence and the diff, then STOPS at the human seam. The self-heal loop (run gate ->
classify -> auto-fix mechanical / HARD-STOP judgment calls -> re-run) lives ONLY in
`retail-orchestrate`, never here; and the gate approval is the reviewer's recorded
`approvals[]` action, which no loop self-grants.
