# Ratify ledger: dbt evidence governance consumer

**Spec**: `specs/150-dbt-evidence-consumer`
**Branch**: `150-dbt-evidence-consumer` (worktree; nothing on `main`)
**Prepared**: 2026-08-08
**Status**: AWAITING RATIFICATION -- not ratified, not implemented

## The seam this ledger guards

Principle V: a stage's approval is a named human action the agent cannot
self-grant. The same rule governs spec ratification. Every sibling in this
program carries a named human in its status line:

- `specs/143-official-first-graph` -- "ratified -- Ahmed Shaaban, 2026-08-07"
- `specs/146-dbt-official-delegation` -- "Phase 4 implementation authorized by
  Ahmed Shaaban on 2026-08-07"
- `specs/147-dagster-official-delegation` -- "Phase 5 implementation authorized
  by Ahmed Shaaban on 2026-08-07"

This spec has no such line. Until a named human writes one, no implementation
task may begin. The agent that prepared this ledger is structurally forbidden
from writing that line itself.

## What is being asked for

Authorization to implement a **read-only** consumer that closes the last link in
the dbt governance chain:

> official executor -> native result -> normalization -> evidence -> **a
> governance surface that reads it** -> earliest truthful next action

Today the chain stops one step short: dbt evidence is produced, schema-validated,
and committed, and nothing reads it back.

## Decision record

| # | Decision | Made by | Basis |
| --- | --- | --- | --- |
| 1 | Phase 7 is PARTIALLY-REQUIRED, not REQUIRED | agent, from repo evidence | `RunEvidence` already is the governance envelope; only the reader is missing |
| 2 | Consumer lives on the next-action surface, not the evidence pack | **owner**, 2026-08-08 | the pack's 10-section contract is documented and load-bearing |
| 3 | Outcome mapping published once in `src/seshat/dbt/` | **owner**, 2026-08-08 | corrects an existing backwards private-symbol dependency |
| 4 | Record selection by filename sort | agent | `invocation_id` is timestamp-prefixed; tolerant of a corrupt sibling |
| 5 | No read-time re-redaction | agent | records are sanitized at write time and schema-closed |
| 6 | No Power BI normalizer | agent, from repo evidence | F016 is `state: deferred`; there is no result to normalize |
| 7 | Caveat is ADDITIVE only; never joins the override chain | agent, from adversarial round 2 | replacement would soften a blocked table's STOP (FR-019/FR-020) |
| 8 | Classifier goes in a new module, not `portfolio_watch.py` | agent, from adversarial round 2 | that file is already 1227 lines (FR-021) |

## What changed during review

Two independent adversarial rounds each found a defect that self-review had
missed. Both were verified directly before being accepted.

**Round 1** refuted the original evidence-pack design.
`cli/commands/evidence_pack.py:21` reads `section['status']` unconditionally,
`_section_blockers` reads `section['sources'][0]`,
`tests/unit/test_evidence_pack.py:77` pins the id list to `01`-`10`, and
`docs/tools/evidence-pack-generator.md:79` documents "The 10-section contract
(fixed, ordered)". The design was redirected, not patched.

**Round 2** refuted the composition of the replacement design. At
`agent_next.py:871`, `action = next_override or _next_allowed_action(response)`
REPLACES the action string, and `control_outcome` (line 862) feeds `stop_point`.
Had the dbt caveat joined that chain, a `stop_blocked` table's `STOP` sentence
would have been displaced by a `CAUTION --` caveat, and no existing test would
have caught it -- no fixture pairs a blocked table with a winning override.

That second defect runs OPPOSITE to the one the spec was written to prevent: not
execution granting readiness, but execution **softening a stop**. It is now
FR-019/FR-020, with T005a testing it by whole-document diff.

Full record in `plan-review.md`.

## Pre-ratification verification

| Command | Exit | Result | Classification |
| --- | --- | --- | --- |
| `python -m seshat.cli check` | 0 | 1 warning: RS1 `last_checked_at` predates latest approval, in `mappings/retail_store_sales/` | PRE-EXISTING -- this branch modifies no file under `mappings/` |
| `python scripts/export_agent_bundles.py --check` | 0 | "generated Claude and Codex bundles match reviewed inputs" | PASS |
| `git diff --stat HEAD` | 0 | empty -- no tracked file modified | PASS |
| `git status --short` | 0 | one untracked dir: `specs/150-dbt-evidence-consumer/` | PASS |
| `python -m seshat.cli next --help` | 0 | `--table` exists | PASS (quickstart spelling verified) |
| `python -m seshat.cli evidence-pack --help` | 0 | `--table` exists | PASS (quickstart spelling verified) |

No test suite was run because no source file was changed. Reporting green test
gates on an unchanged tree would be noise.

## What ratification authorizes

Tasks T001-T014 (incl. T005a) in `tasks.md`, touching only:

- `src/seshat/dbt/` -- publish `OUTCOME_TO_EXECUTION`
- `orchestration/.../dbt_build.py` -- import it, drop the private copy
- a NEW sibling module under `src/seshat/` -- the classifier (NOT
  `portfolio_watch.py`, per FR-021)
- `src/seshat/agent_next.py` -- the additive `caveats` entry only
- `tests/unit/` -- behavioural tests
- `docs/integrations/dbt-adapter.md`, `docs/integrations/pbi-mcp-adapter.md`

## What ratification does NOT authorize

Any change to `RunEvidence`, its writer, or its schema. Any change to the
evidence pack, its consumers, its pinned test, or its documented 10-section
contract. Any Power BI execution, refresh, query, or publish capability. Any
Dagster normalization change. Live database execution. dbt activation.
`_STAGE_ORDER` deduplication. Phase 8 or later. Push, PR, merge, or publication.

## Known residual risks

- The reviewer-facing gap remains open: a human reading an evidence pack still
  cannot see a dbt build. Deliberately deferred to a follow-on spec that can
  amend the 10-section contract on its own merits.
- `blocked` appears in both the execution and readiness vocabularies. Mitigated
  structurally: the classifier never opens `readiness-status.yaml`.
- dbt activation remains `blocked` (`docs/operations/dbt-activation-status.yaml`,
  `owner: UNASSIGNED`). The reader is testable against records today, but no
  live end-to-end proof exists until activation clears.

## To ratify

Replace the status line in `specs/150-dbt-evidence-consumer/spec.md`:

```
**Status**: draft
```

with a named authorization, preserving the previous value per the template's
status-history rule:

```
**Status**: ratified -- <Your Name>, <YYYY-MM-DD>
**Status history**: draft
```

To decline, say so and the branch can be dropped; nothing has been committed and
`main` is untouched.
