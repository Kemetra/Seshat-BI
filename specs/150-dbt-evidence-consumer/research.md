# Research: dbt evidence governance consumer

## Repository truth

Verified by direct read on `main` at `07e9907`.

- `RunEvidence` (`src/seshat/dbt/contracts.py:324`) already is the governance
  envelope. It carries `schema_version`, `authority`, `invocation_id`,
  `table_id`, `command`, `outcome`, `seshat_exit_code`, `plan_digest`,
  `project_fingerprint`, `mapping_path`, `mapping_revision`, `runtime`,
  `target`, `selected_unique_ids`, `executed_unique_ids`, `tests`, `parity`,
  `artifacts`, `blocking_reasons`, and `readiness_effect`. Nothing about a
  common cross-executor envelope needs inventing.
- `readiness_effect` already carries the literal
  `"none; named-human approval required"`. Truth separation is authored into the
  record; the missing piece is a reader that honours it.
- `write_evidence()` (`src/seshat/dbt/evidence.py:785`) sanitizes via
  `seshat.dbt.redaction.sanitize()`, schema-validates against
  `schemas/dbt-run-evidence.schema.json`, and atomically writes
  `mappings/<table>/dbt-evidence/<invocation_id>.json`.
- A repo-wide sweep for `dbt-evidence` outside `tests/` returns two non-test
  hits in `src/`: the writer above, and `src/seshat/reset.py`, which deletes it.
  There is no reader.
- `evidence_pack._SECTIONS` (`src/seshat/evidence_pack.py:13-65`) holds ten
  sections; none references `dbt-evidence`.
- `_build_section()` (`src/seshat/evidence_pack.py:184-198`) is a file-presence
  checker. It emits `status: "blocked" if blockers else "pass"`, derived purely
  from whether the source files exist and lack template markers. It has no
  vocabulary for "record present but the build failed" or "record corrupt".
- The ten-section shape is a **documented fixed contract**, not an incidental
  list: `docs/tools/evidence-pack-generator.md:79` titles it "The 10-section
  contract (fixed, ordered)", and `docs/capabilities/capabilities.yaml:777` and
  `src/seshat/cli/parser_core.py:252` restate it. Two live consumers index
  fixed keys across every section (`cli/commands/evidence_pack.py:21` reads
  `section['status']`; `evidence_pack._section_blockers` reads
  `section['sources'][0]`), and `tests/unit/test_evidence_pack.py:77` pins the
  id list. The evidence pack is therefore NOT an extension point, and this spec
  leaves it untouched.
- `portfolio_watch.py:107` already defines `STATE_UNREADABLE = "unreadable"`,
  so the fail-closed state vocabulary exists and is reused rather than respelled.
- `agent_next._is_stopped()` (`src/seshat/agent_next.py:812-816`) treats any
  action string beginning with `STOP` as suppressing downstream guidance; its
  docstring records a past defect where dbt guidance rendered beneath a STOP.
  Caveat wording is therefore semantic, not cosmetic.
- `_STAGE_ORDER` is independently declared in ten modules. The approval-shape
  predicate, by contrast, is correctly centralized in
  `rules/readiness_status.py` and lazily imported by consumers.

## The Dagster contrast

Dagster is the proof that this seam is buildable and that Seshat already knows
how to build it.

- `dagster_adapter/` never imports the `dagster` package. It does not reproduce
  Dagster's event model; it synthesizes `AssetOutcome` records.
- Those records ARE consumed: `portfolio_watch.live_validation_state()`
  (`src/seshat/portfolio_watch.py:715`) reads them and returns
  `pending_live` / `stale` / `blocked` / `uncommitted_evidence`.
- `agent_next._live_validation_next_override()`
  (`src/seshat/agent_next.py:607`) turns that state into a real next-action
  caveat, including the case where evidence exists only in git-ignored scratch
  and is therefore unreviewable.

So Seshat's shipped pattern is: executor produces a record; a read-only state
function classifies it; a governance surface reports it without ever granting a
stage. dbt has the record and lacks the last two steps.

## Power BI truth

- `docs/capabilities/capabilities.yaml` marks `f016-powerbi-execution-adapter`
  as `state: deferred` -- "no mutation path exists yet".
- `src/seshat/pbi_mcp/` documents hard constitutional boundaries: no mutation
  path exists in the package. The `McpTransport` Protocol has no call/execute
  member, and the shipped `MissingRuntimeTransport` always raises
  `RuntimeUnavailable`.
- There is therefore no Power BI execution result to normalize. Adding a Power
  BI normalizer would mean inventing a result for a runtime that cannot produce
  one.

## The execution-word collision

dbt's `outcome` vocabulary contains the literal `pass`. The readiness
four-status vocabulary also contains `pass`. Rendering the former where a reader
expects the latter is the precise mechanism by which execution success would
masquerade as readiness.

The orchestration package already solved this: `_DBT_OUTCOME_TO_EXECUTION`
(`orchestration/dagster/src/tower_bi_orchestration/dbt_build.py:79`) maps dbt
`pass` to the execution word `built`, with an explicit comment that the record
must never carry the readiness token. That mapping is private and lives in a
package that imports from `seshat`, so it cannot be reused upward as-is.

## Conclusion

No new evidence contract is justified. No second readiness authority is
justified. No Power BI normalizer is justified. No evidence-pack change is
justified. The remaining delta is a read-only classifier for an envelope that
already exists, a next-action caveat mirroring the shipped Dagster consumer, and
a single relocation of the outcome-translation mapping so one definition serves
both directions of the dependency.

The reviewer-facing surface (a dbt section in the evidence pack) is a real
remaining gap, deliberately deferred: closing it means amending a documented
fixed contract and updating two consumers, a pinned test, and three documents.
That deserves its own spec and its own ratification, not a side effect of this
one.
