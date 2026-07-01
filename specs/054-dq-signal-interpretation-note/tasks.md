# Tasks: DQ-Signal Interpretation Note (-1 unknown-member counts as business caveat)

**Feature**: `054-dq-signal-interpretation-note`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/template-contract.md](./contracts/template-contract.md)

This is a DOCS/TEMPLATE-ONLY feature -- there is NO code, so there is NO TDD
RED/GREEN cycle. Verification is by inspection against the spec Success Criteria and
the template contract. All paths are repo-relative.

Scope guard (YAGNI / first step): author ONE new generic template file,
`templates/handoff/dq-signal-interpretation.md`, plus minimal cross-reference wiring
in existing docs. Add NO executor, NO validator, NO rule id, NO code, NO new
dependency, NO new number. Do NOT decide the KPI+direction mapping or PII
publish-safety (Principle-V fill-ins). Do NOT invent a readiness stage or an
F-number (OPEN in spec ## Clarifications). Do NOT inline any C086/pharmacy specific.

## Phase 1: Setup

- [ ] T001 Re-read the discipline of the sibling templates
  `templates/handoff/bi-handoff-pack.md` (Known-gaps L59-73), `templates/data-issues.md`
  (the `-1` row L12/L28-30), and `templates/reconciliation-report.md` (the generic
  banner header L1-13) so the new template matches their generic banner, "composes
  never invents", "no fake confidence", and C086-by-reference discipline exactly.

## Phase 2: Author the template (User Story 1 -- P1)

- [ ] T002 Create `templates/handoff/dq-signal-interpretation.md` with the GENERIC
  banner per the contract section "MUST contain #1": copy-per-table instruction,
  count-sourced-by-reference-from-data-issues.md (single source of truth), C086 as a
  linked filled instance only, ASCII / UTF-8 no BOM (`--` and `->`, no glyphs), and
  an explicit "NO numeric confidence / health / readiness score" line.
- [ ] T003 Add the per-signal interpretation table (contract #2) with placeholder
  cells for `dim`, `count (by reference)`, `affected KPI (analyst fill-in)`,
  `direction (understate | overstate | none -- analyst fill-in)`, `plain-language
  caveat`, `owner (named)`, and `PII review (governance if person/customer dim)`.
  Every judgment cell is an angle-bracket `<placeholder>` -- no pre-decided value
  (SC-004).
- [ ] T004 Add the direction-of-distortion semantics note (contract #3) distinguishing
  measure TOTAL (unaffected -- `-1` absorbs the row so the total reconciles) vs a
  SLICED/grouped view (distorted -- the `-1` bucket steals share). Present it as the
  analyst's ruling to state precisely (Principle V); the template does NOT assert the
  claim. Reference spec FR-011 as the OPEN human ruling.

## Phase 3: The no-fabrication + single-source paths (User Story 2 + edges)

- [ ] T005 Add the "None recorded" path (contract #4, FR-004, SC-003): an explicit
  "no recorded -1 signal for this table -- nothing to interpret; zero caveats"
  statement so an empty note is never a fabricated one.
- [ ] T006 Add the feeds-not-duplicates note (contract #5, FR-005, SC-005): the
  confirmed caveat is carried verbatim into the Stage-7 handoff pack Known-gaps
  section (`bi-handoff-pack.md` L59-73); `data-issues.md` stays the single source of
  truth for the number; add the reconciliation edge rule (if the note and
  `data-issues.md` disagree, reconcile to `data-issues.md`, never override it).

## Phase 4: Judgment gates + citations (User Story 3 -- P3)

- [ ] T007 Add the RC14 citation (contract #6, FR-006): name the ratified `-1`
  unknown-member + FK COALESCE default (constitution Principle VI); interpret the
  consequence, do not re-litigate the default, invent no number.
- [ ] T008 Add the PII publish-safety gate (contract #2 PII cell + #7, FR-007): for a
  person/customer dimension, a governance publish-safety sign-off is required before
  the caveat is published; default is defer to governance (Principle V).
- [ ] T009 Add the "See also" block (contract #7): links to `data-issues.md`,
  `bi-handoff-pack.md`, `publish-ready.md` (Stage 7), `gold-ready.md` (Stage 4 where
  the count is produced), the constitution (Principle V / VI, RC14), and C086
  (`docs/worked-examples/c086-pharmacy.md`, `docs/c086-adr0002-compliance.md`) as a
  filled instance.

## Phase 5: Wiring + verification

- [ ] T010 [P] Add a one-line cross-reference to the new template from
  `templates/handoff/bi-handoff-pack.md` Known-gaps section ("the interpretive source
  for this section is `dq-signal-interpretation.md`") and, if a "See also" fits,
  from `docs/readiness/publish-ready.md` -- WITHOUT changing any existing required
  behavior, count, or gate wording.
- [ ] T011 Verify against the contract "Acceptance" + spec SC-001..SC-005 by
  inspection: (a) grep the new template for `salesperson`, `ezaby`, `\b71\b`, and a
  fixed measure name -> zero hits (SC-002); (b) confirm no new/absolute number is
  present (SC-001); (c) confirm the "none recorded" path exists (SC-003); (d) confirm
  every KPI + direction cell is an unfilled owner-gated prompt (SC-004); (e) confirm
  the count is referenced, not duplicated (SC-005); (f) confirm ASCII / UTF-8 no BOM
  and no confidence score.

## Dependencies

- T001 precedes all authoring tasks.
- T002 (file creation) precedes T003-T009 (sections added to that file).
- T010 (wiring) and T011 (verification) run after the template is authored; T010 is
  [P] against T011 only if the template file is complete.

## Out of scope (do NOT do)

- No Python, no rule registration, no `validate.py` change, no `-1` tally check.
- No live query, no DB connection, no F016 Power BI adapter reference as a consumer.
- No decision on the KPI+direction mapping, PII publish-safety, stage-of-record, or
  F-number (all OPEN / Principle-V in spec ## Clarifications).
- No C086/pharmacy specifics inlined.
