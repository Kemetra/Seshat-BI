# Readiness decay -- the stale-pass demotion pattern

> **Pattern doc, doc-only -- no rule code, no `retail check` rule id.** This
> document names the CONCEPT `docs/readiness/source-drift.md:74` already
> promises in prose ("a `warning`/`blocked` drift at Source Ready makes
> downstream `pass` stages SUSPECT ... the human/agent re-runs the stage
> gate") and gives it a generic, agent-followable shape: a `stale_pass`
> SIGNAL a human or agent can raise by hand today, without a live DB, a
> drift-detection runtime, or a new `retail check` rule. It is intentionally
> NOT wired into `src/seshat/rules/` here -- the reserved id (`HR3`) and the
> mechanical, git-history-backed enforcement of this pattern are a SEPARATE,
> not-yet-landed piece of work. Treat everything below as the vocabulary and
> procedure a human/agent applies manually until that enforcement exists.

## Why this pattern exists

The readiness spine has a documented hole. `docs/readiness/source-drift.md`
states the rule plainly: a `blocked`/`warning` drift at Source Ready makes
every downstream `pass` stage suspect, and the detector "FLAGS this" without
auto-demoting -- "the human/agent re-runs the stage gate." That sentence
describes the correct behavior but nothing mechanically enforces it yet: a
table can drift at Source Ready, nothing downstream ever gets
re-confirmed, and `retail check` stays green throughout, because no rule
watches for exactly that condition today.

This pattern also covers a second, related gap: a `pass` stage's approval
can go stale even without any drift at Source Ready, simply because the
evidence a human approved was edited again afterward and nobody re-signed.
Both gaps share the same shape (a `pass` that no longer reflects what a
human actually reviewed) and the same resolution discipline (the human
decides; nothing here scores, demotes, or re-passes on its own), so this
document treats them together.

## The two staleness conditions

### 1. Drift-triggered staleness

`stages.source_ready.status` is `warning` or `blocked` (the committed
source-drift signal, per `docs/readiness/source-drift.md`) while one or
more downstream stages are recorded `pass`. Every such downstream `pass` is
stale: it was built against a source shape that has since been measured as
different. A table with N stale downstream `pass` stages has N separate
stale conditions -- one per stage, never rolled up into a single "this table
is stale" signal (no fake confidence, hard rule #9).

This condition does NOT fire when `source_ready.status` is `not_started`
(that is a separate, RS1-adjacent stage-order oddity, not a drift signal)
or `pass` (a clean, re-confirmed source).

### 2. Approval-lag staleness

An approval-bearing stage (`mapping_ready`, `semantic_model_ready`,
`dashboard_ready`, `publish_ready`, or a file-source `source_ready`) is
`pass` with a recorded `approvals[]` entry, but a piece of evidence that
`pass` cites has a LATER commit date than the approval's `at:` date. The
thing the human signed off on has changed since they signed it. When a
stage carries more than one `approvals[]` entry, the MOST RECENT (latest
`at`) entry is the one evidence must not have outrun -- a fresh re-approval
clears a prior staleness signal.

**Same-day is not stale.** A day-granularity tie (the evidence's commit
date and the approval date fall on the same calendar date) is NOT treated
as staleness -- this is the conservative direction for a coarse-grained
signal and avoids false positives from a legitimate approve-and-commit-
same-day workflow.

**A mechanical stage has no approval-lag condition.** `silver_ready` and
`gold_ready` carry no `approvals[]` concept, so approval-lag staleness does
not apply to them. They remain covered by drift-triggered staleness
(condition 1) when applicable -- a mechanical `pass` built on a drifted
source is exactly as suspect as an approval-bearing one.

**A stage can be stale under both conditions at once**, e.g.
`source_ready` is `blocked` AND that same downstream stage's own cited
evidence was independently edited after its own approval. Both conditions
are recorded independently -- they name different root causes (an upstream
drift signal vs. a specific evidence path outrunning its own approval) and
clear through different human actions, so collapsing them into one signal
would hide which cause remains unresolved.

## What counts as "the evidence that changed"

Only a stage's `evidence[]` entry that names an actual, resolvable,
committed file path is a citation this pattern can date-compare. A stage's
`evidence[]` is ordinary free text today, and much of it is prose with no
path at all (e.g. a narrative check-run summary). Applying this pattern
means distinguishing three cases:

- **A citation** -- the entry names a path that exists among the repo's
  tracked files. This is what gets date-compared against the approval.
- **A stale/broken citation** -- the entry names something that LOOKS like a
  path inside a real, tracked directory, but the specific file is not
  there (e.g. it was renamed or deleted). This is its own distinct signal
  (the citation cannot be date-compared at all, which is itself worth
  surfacing) -- never silently treated as "not changed."
- **Prose, not a citation** -- the entry is a directory-shaped reference, a
  narrative sentence, a rule-id list, or a formatted number that happens to
  contain a slash or a decimal point. This is NOT a citation and produces
  no staleness signal of any kind. Being conservative here matters: a
  pattern that is unsure whether a token is a real citation or prose should
  treat it as prose rather than risk a false staleness signal against
  innocuous text.

## The `stale_review` reaffirmation entry (a shape, not a schema mandate)

Rather than re-running a full approval from scratch, a named human can
reaffirm that a specific stale (stage, evidence-path) pair is still sound.
This pattern names the generic shape such a reaffirmation would take,
structurally parallel to the existing `approvals[]` list:

```yaml
# Generic shape -- illustrative field names only, no domain specifics.
stale_review:
  - stage: "<stage_name>"              # one of the seven readiness stage
                                        #   names (source_ready, mapping_ready,
                                        #   silver_ready, gold_ready,
                                        #   semantic_model_ready,
                                        #   dashboard_ready, publish_ready)
    evidence: "<repo-relative-path>"   # the SPECIFIC evidence path being
                                        #   reaffirmed -- must match the
                                        #   path that triggered the
                                        #   approval-lag staleness signal
    reviewer: "<Person Name> (<authority_class>)"
                                        # REQUIRED shape-valid form --
                                        #   "Person Name (authority_class)",
                                        #   the same owner shape the
                                        #   readiness spine's approvals[]
                                        #   already requires; authority_class
                                        #   in {analyst, governance,
                                        #   data_owner, metric_owner}
    at: "YYYY-MM-DD"                   # ISO date; must be on or after the
                                        #   triggering evidence path's
                                        #   commit date to reaffirm the pair
    note: "<optional short free-text note>"
                                        # OPTIONAL; not validated for shape,
                                        #   carries no score
```

**Field semantics:**

- `stage` + `evidence` together identify the SPECIFIC (stage, evidence
  path) pair being reaffirmed -- one entry reaffirms exactly one such pair,
  never a whole stage's or a whole table's worth of staleness signals at
  once (no batch reaffirmation; the "no rolled-up finding" discipline
  extends to "no rolled-up clearing" as well).
- `reviewer` MUST pass the same shape check the spine already applies to
  `approvals[].owner`: a non-empty person name plus exactly one
  parenthesized authority class. A bare role token (`"data_owner"`), a name
  with no class (`"Ada Lovelace"`), a role masquerading as a name
  (`"owner (data_owner)"`), or an unknown class all FAIL this check. An
  entry whose `reviewer` fails does NOT count as a reaffirmation.
- `at` MUST be on or after the triggering evidence path's commit date. An
  entry dated strictly before does not reaffirm anything -- a reaffirmation
  cannot predate the thing it reaffirms.
- **Scope (an explicitly open question -- see below).** A `stale_review`
  entry, as this pattern currently states it, reaffirms an approval-lag
  staleness signal (condition 2) for its named (stage, evidence) pair only.
  It does NOT, under this pattern, clear a drift-triggered staleness signal
  (condition 1) -- that one clears only via a human edit to
  `stages.source_ready.status` (re-confirming or demoting) or to the stale
  downstream stage's own status.

## The human-only-reviewer rule (Principle V)

An agent MAY draft the `stage`, `evidence`, and `note` fields of a
candidate `stale_review` entry for a human to complete -- it has enough
committed information to identify which pair is stale and describe why.
The agent MUST leave the `reviewer` name for a human to supply, and MUST
NOT commit a `stale_review` entry without a human-supplied reviewer name.
This is the same "never self-grant a readiness pass" discipline that
already governs `approvals[]`: reaffirming that a stale pass is still sound
is itself a judgment call, not a mechanical inference the agent can make on
the evidence's behalf.

## No fake confidence (hard rule #9)

Nothing in this pattern computes or emits a numeric decay, staleness, or
confidence score, and nothing emits a completeness or "N of M" count. Every
staleness signal names a specific stage and, where applicable, a specific
evidence path and the two dates being compared -- never a rolled-up numeric
measure of "how stale" a table is. A `stale_review` entry likewise carries
no score field.

## What this pattern does not do

- It does not define a new `retail check` rule id, does not add a wiring
  surface, and does not change any existing rule's behavior. The
  mechanical, git-history-backed enforcement of this pattern (comparing an
  approval date against a cited evidence path's actual commit history) is
  future work, tracked separately from this document.
- It does not reopen or restate the drift TAXONOMY
  (`docs/readiness/source-drift.md`) -- it consumes the existing
  `stages.source_ready.status` signal exactly as already defined.
- It does not decide the open question of whether a `stale_review` entry
  should ALSO be able to clear a drift-triggered staleness signal (condition
  1), in addition to an approval-lag signal (condition 2). See "Open
  question," below.
- It does not assume a live database connection, a drift-detection
  runtime, or a `retail drift` CLI -- none exists. This pattern operates
  purely on already-committed, already-tracked text and (once mechanically
  enforced) git history.

## Open question (Principle V -- not resolved here)

**Does a `stale_review` entry reaffirm a drift-triggered staleness signal
(condition 1) in addition to an approval-lag signal (condition 2), or is
`stale_review` scoped to approval-lag reaffirmation only?** This document
states the narrower reading (approval-lag only) as the current default,
matching condition 1's own resolution path (a human edit to
`stages.source_ready.status` or the stale stage's own status). Whether a
future revision should widen `stale_review` to also cover a drift-triggered
signal -- e.g. "I re-confirmed this downstream stage is still sound despite
the upstream drift, without yet resolving the drift itself" -- is a
product-scope decision about what the reaffirmation escape hatch is FOR,
not a default this document should silently pick. Left OPEN for the
feature owner.

## See also

- `docs/readiness/source-drift.md` -- the drift taxonomy and the
  Downstream-invalidation rule (line ~74) this pattern is the enforcement
  half of; NOT edited by this document.
- `docs/readiness/readiness-model.md` -- the four-status vocabulary and the
  "no fake confidence" rule this pattern inherits.
- `docs/readiness/readiness-pipeline.md` -- the seven-stage fixed order
  referenced by `stage` values above.
- `docs/checklists/readiness-decay.md` -- the operator checklist for
  raising and clearing a stale-pass signal by hand.
- `.claude/skills/approval-console/SKILL.md` -- the tool a named human uses
  to record an `approvals[]` entry; a `stale_review` entry follows the same
  transcribe-never-author discipline once a console-style surface is built
  for it.
- `.claude/skills/run-next-readiness/SKILL.md` -- reads
  `readiness-status.yaml`'s stage statuses and approval shapes today; a
  future revision could surface a stale-pass signal as an additional
  caveat once this pattern's mechanical enforcement exists.
