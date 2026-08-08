# Tasks: dbt evidence governance consumer

**Status**: draft; NOT ratified. No task below may begin until a named human
records ratification in `spec.md`.

Tasks are TDD-ordered: the failing test precedes the implementation it forces.

- [ ] T001 Baseline the focused suites at the branch point and record the
      result, so any later failure can be classified against a known-good
      baseline rather than guessed at. Include
      `tests/unit/test_evidence_pack.py` and `orchestration/dagster/tests`,
      both of which this change must leave green.
- [ ] T002 Write the failing truth-separation test first (US2): a dbt record
      with `outcome: pass` present for a table leaves the recorded stage status,
      the outstanding approval, and the whole next-action document identical to
      the same fixture without the record. The oracle must read readiness from
      the readiness surface, not from the code under test.
- [ ] T003 Write the failing fail-closed tests (US3): corrupt JSON, missing
      envelope fields, and an absent directory each produce their documented
      state and never produce a success state. Assert absent emits NO caveat.
- [ ] T004 Write the failing caveat tests (US1): `failed` and `blocked` records
      each produce a caveat naming the translated execution word, the
      `invocation_id`, and the record path; `blocking_reasons` are surfaced.
- [ ] T005 Write the failing prefix test (FR-017): an informational dbt caveat
      does not begin with `STOP`. Assert against `_is_stopped()` itself, not
      against a copy of its rule.
- [ ] T005a Write the failing NO-SOFTENING test (FR-019/FR-020), the highest-risk
      guarantee in this spec and one no existing fixture covers: for a table
      whose `outcome` is `stop_blocked`, and again for `approval_required`,
      assert that adding a dbt evidence record leaves `next_allowed_action`,
      `stop_point`, `outcome`, and `forbidden_scope` byte-identical, with the
      added `caveats` entry as the ONLY document difference. The oracle must
      diff the two whole documents, not spot-check fields.
- [ ] T006 Publish `OUTCOME_TO_EXECUTION` as a public mapping in
      `src/seshat/dbt/`, with the unknown-outcome default resolving to
      `blocked`.
- [ ] T007 Point `orchestration/.../dbt_build.py` at the shared mapping and
      delete its private `_DBT_OUTCOME_TO_EXECUTION`; re-run
      `orchestration/dagster/tests` since this inverts an existing dependency.
- [ ] T008 Implement the read-only classifier in a NEW sibling module, not in
      `portfolio_watch.py` (FR-021): deterministic filename-sort selection, JSON
      parse, envelope-field check, and the five-state result. Reuse
      `STATE_UNREADABLE`; declare no new `_STAGE_ORDER` (FR-015).
- [ ] T009 Implement the next-action caveat in `agent_next` as an ADDITIVE entry
      on the `caveats` list (FR-019). It must not join the `next_override`
      chain, must not touch `_control_stage`, and must leave the existing
      `live_override or contract_override` precedence untouched (FR-018).
- [ ] T010 Assert the negative guarantees explicitly: the classifier returns no
      readiness four-status token; the evidence pack's output and its ten
      sections are byte-identical to the baseline; `_build_section` and
      `_section_blockers` are untouched (FR-016).
- [ ] T011 Update `docs/integrations/dbt-adapter.md` and
      `docs/integrations/pbi-mcp-adapter.md`: dbt evidence now reaches a
      governance surface; Power BI execution results remain absent by design and
      gain no normalizer.
- [ ] T012 Re-run `python scripts/export_agent_bundles.py --check` and commit any
      required regeneration if T011 changed bundled content.
- [ ] T013 Run the repository gates (`pytest -m unit`, `seshat check`,
      `ruff format --check src tests`, `ruff check src tests`) and report each
      with command, exit code, and classification.
- [ ] T014 Review the full diff file-by-file; every changed file must have a
      stated reason. Confirm no evidence-pack file appears in the diff. Remove
      speculative or incidental edits.

Marking a task complete requires the verified deliverable in hand. Do not sweep
checkboxes.

Explicitly excluded: evidence-schema or envelope change, any evidence-pack
change, Power BI execution or publish capability, Dagster normalization change,
live database execution, dbt activation, `_STAGE_ORDER` deduplication, Phase 8
work, push, PR, merge, or publication.
