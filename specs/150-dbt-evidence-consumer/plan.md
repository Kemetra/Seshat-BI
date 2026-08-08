# Implementation Plan: dbt evidence governance consumer

**Branch**: `150-dbt-evidence-consumer`

**Status**: ratified -- Ahmed Shaaban, 2026-08-08. Implementation authorized.

**Status history**: draft; NOT ratified. Implementation is not authorized.

## Phase classification

**PARTIALLY-REQUIRED.** Phase 7's stated goal -- connect upstream execution
results to Seshat governance evidence -- is already satisfied for two of its
three links and for one of its three executors.

| Concern | State on `main` | Delta |
| --- | --- | --- |
| Common governance envelope | EXISTS as `RunEvidence` | none; reuse |
| dbt native result parsing | EXISTS (`manifest.json`, `run_results.json`) | none |
| dbt normalization to evidence | EXISTS (`build_evidence` / `write_evidence`) | none |
| dbt evidence read by a governance surface | **ABSENT** | **this spec** |
| Dagster normalization + consumer | EXISTS (`live_validation_state` -> `agent_next`) | none; used as the template |
| Power BI execution result | does not exist; F016 deferred | none; record the absence |

The delta is a reader, not a contract.

## Design history (why this plan changed)

The first draft added an eleventh section to the evidence pack. An adversarial
plan review refuted it with repo evidence, and the refutation was verified
directly:

- `src/seshat/cli/commands/evidence_pack.py:21` reads `section['status']`
  unconditionally for every section. A section without that key raises
  `KeyError`.
- `evidence_pack._section_blockers()` reads `section["sources"][0]` and
  `section["blocking_reasons"]` unconditionally. The proposed section had no
  `sources` key.
- `tests/unit/test_evidence_pack.py:77` pins the sections list to exactly
  `["01".."10"]`.
- `docs/tools/evidence-pack-generator.md:79` titles the invariant "The
  10-section contract (fixed, ordered)"; `docs/capabilities/capabilities.yaml`
  and `src/seshat/cli/parser_core.py:252` restate it.

The "additive, zero blast radius" framing was therefore false: appending a
differently-shaped item to a list that consumers iterate and index is not
additive. This plan drops the pack section and mirrors the shipped Dagster
consumer instead, which touches no fixed contract.

## Smallest remaining delta

1. Publish the outcome-translation mapping once in `src/seshat/dbt/`, and make
   the orchestration package import it instead of keeping a private copy. This
   corrects an existing backwards dependency; it adds no behaviour.
2. Add a read-only classifier -- the dbt analogue of
   `portfolio_watch.live_validation_state()` -- that selects and parses the
   latest committed dbt evidence record and returns one of `absent` / `built` /
   `failed` / `blocked` / `unreadable`, reusing the existing
   `STATE_UNREADABLE` constant.
3. Add a next-action caveat in `agent_next`, mirroring
   `_live_validation_next_override()`, emitted only for the non-clean states.
4. Prove truth separation behaviourally: a record reporting execution success
   changes no readiness status, discharges no approval, and leaves the
   next-action document unchanged.
5. Record the Power BI absence in the adapter documentation rather than
   inventing a normalizer.

## Why not the alternatives

- **An evidence-pack section**: refuted above. Deferred to a follow-on spec that
  can amend the documented 10-section contract on its own merits, rather than
  smuggling a contract amendment into a reader-only spec.
- **Extending `_build_section()`**: it is a file-presence checker shared by all
  ten existing sections. Teaching it new states would route every existing
  section through changed logic for one new caller.
- **A new cross-executor evidence contract**: `RunEvidence` already is one, and
  Power BI has no result to normalize. Building a generic envelope now would be
  a framework for one real caller.

## Truth separation (the risk this plan carries)

The reason this seam was deferred is that a careless reader converts an exit
code into a governance verdict. Three structural guards, in order of strength:

1. The classifier never opens `readiness-status.yaml`. It is incapable of
   altering a stage or an approval.
2. It returns an execution state, never a readiness four-status token, and never
   writes to a `status` key belonging to a stage.
3. `execution_outcome` is the translated execution word (`built`), never dbt's
   raw `pass`.

## Fail-closed posture

| Case | Result |
| --- | --- |
| No `dbt-evidence/` directory | `absent`; no caveat; never success |
| Directory present, no records | `absent`; no caveat |
| Record is not valid JSON | `unreadable`; caveat names the file |
| Record missing envelope fields | `unreadable`; caveat |
| Latest record corrupt, older ones valid | `unreadable` -- filename sort selects deterministically and does not silently fall back to an older, more flattering record |
| `outcome` absent from the mapping | `blocked` |
| dbt never run for the table | `absent`; no caveat |

## Interaction constraints (verified, load-bearing)

- **The dbt signal is additive and never joins the override chain.** This is the
  single most important constraint in the plan, and adversarial review round 2
  is what surfaced it. At `src/seshat/agent_next.py:871`,
  `action = next_override or _next_allowed_action(response)` REPLACES the action
  string; at line 862, `control_outcome = "next_action" if next_override is not
  None else outcome`, and `control_outcome` feeds `stop_point` (line 880). A dbt
  caveat entering that chain on a `stop_blocked` table would overwrite its
  `STOP` sentence and skip its blocked-specific stop point. The existing two
  overrides avoid this only because both are gated to `terminal_pass or
  post_gold_stage` (`_live_validation_next_override` line 618,
  `_contract_next_override` line 589) and so cannot fire on a blocked table.
  The dbt caveat is NOT so gated, and therefore MUST append to the separate
  additive `caveats` list (line 889) instead.
- `agent_next._is_stopped()` (`src/seshat/agent_next.py:812-816`) treats any
  action string beginning with `STOP` as suppressing downstream guidance. Its
  docstring records a past defect where dbt install/init/doctor steps rendered
  directly beneath a STOP. Because the dbt caveat never becomes the action
  string, it does not interact with that mechanism -- but it must still not
  present itself as a stop it cannot impose.
- Existing override precedence is
  `next_override = live_override or contract_override`
  (`src/seshat/agent_next.py:858-860`). It is left exactly as-is.
- `_control_stage()` takes exactly two override parameters and is NOT extended.
  The dbt signal has no stage-control effect by design: it informs, it does not
  close a gate.

## Files expected to change

| File | Reason |
| --- | --- |
| `src/seshat/dbt/` (a module therein) | define public `OUTCOME_TO_EXECUTION` |
| `orchestration/dagster/src/tower_bi_orchestration/dbt_build.py` | import the shared mapping; drop the private copy |
| a NEW sibling read-only module under `src/seshat/` | the dbt evidence classifier. NOT `portfolio_watch.py`, which is already 1227 lines and would be pushed further past the repo's ~800-line convention (spec FR-021) |
| `src/seshat/agent_next.py` | the additive `caveats` entry |
| `tests/unit/` (focused test module(s)) | behavioural tests incl. the truth-separation guarantee |
| `docs/integrations/dbt-adapter.md` | record that dbt evidence now reaches a governance surface |
| `docs/integrations/pbi-mcp-adapter.md` | record the Power BI execution-result absence as deliberate |

Explicitly NOT changed: `src/seshat/evidence_pack.py`,
`src/seshat/cli/commands/evidence_pack.py`,
`tests/unit/test_evidence_pack.py`, `docs/tools/evidence-pack-generator.md`,
`docs/capabilities/capabilities.yaml` section-count language,
`src/seshat/cli/parser_core.py`.

If `docs/` or `skills/` content changes, `python scripts/export_agent_bundles.py --check`
must be re-run and any regeneration committed.

## Scope guard

No change to `RunEvidence`, its writer, or `schemas/dbt-run-evidence.schema.json`
(inherited from `specs/146-dbt-official-delegation` FR-008). No change to the
evidence pack or its documented 10-section contract. No new readiness state
machine. No Power BI execution, refresh, query, or publish capability. No
database connection. No dbt invocation. No dependency change. No `_STAGE_ORDER`
deduplication. No Phase 8 work. No push, PR, merge, or publication.

## Validation

Focused first, then repository gates:

```
pytest tests/unit/test_agent_next.py tests/unit/test_portfolio_watch.py -q
pytest tests/unit/test_evidence_pack.py -q          # must remain green, untouched
pytest orchestration/dagster/tests -q               # the mapping move
pytest tests/unit -q -m unit
python scripts/export_agent_bundles.py --check
python -m seshat.cli check
ruff format --check src tests
ruff check src tests
```

Each result is reported with command, exit code, and a classification of PASS /
NEW REGRESSION / PRE-EXISTING / ENVIRONMENTAL / EXTERNAL-BLOCKED. A fresh
worktree is known to need `PYTHONPATH=src` and gpgsign disabled; failures
attributable to those are ENVIRONMENTAL and must be baselined against `main`
before being attributed to this change.

## Stop point

This plan stops at ratification. No implementation task begins until a named
human records ratification in `spec.md`. The agent cannot self-ratify.
