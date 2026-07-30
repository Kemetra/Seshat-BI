# Tasks: Finance GL Budget-vs-Actual Genericity Proof

**Feature**: `137-finance-gl-genericity-proof` | **Date**: 2026-07-30
**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**IMPLEMENTATION IS NOT STARTED.** No task below may begin until the owner ratifies the
planning package (spec + plan + tasks). Slice A starts only after that ratification.

## Task labels used here

| Label | Meaning |
|---|---|
| `[P]` | Parallelizable -- different files, no dependency on an incomplete task |
| `[US1]`..`[US4]` | The user story from `spec.md` this task serves |
| `mechanical` | Deterministic authoring/verification an agent completes alone |
| `human_only` | Requires a human action an agent cannot perform |
| `approval_gated` | BLOCKED until a named human records a decision; never self-granted |

Slice letters (A-F) from the feature brief are noted per phase.

---

## Phase 1: Setup (Slice A start)

- [ ] T001 Create the fixture package directory `tests/fixtures/finance_gl/` with an empty `excerpts/` subdirectory -- `mechanical`
- [ ] T002 Add the generated-output path to `.gitignore` so full generated CSVs are never committed, per the measured storage decision in `plan.md` -- `mechanical`
- [ ] T003 [P] Record the pre-flight baseline in `specs/137-finance-gl-genericity-proof/ledger-baseline.md`: current branch, `git log -1 --oneline`, `git status --short`, and the byte sizes of the three existing committed fixtures cited in `research.md` R3 -- `mechanical`

## Phase 2: Foundational -- the generator (Slice A; BLOCKS every later phase)

**No downstream artifact may be authored from a non-reproducible fixture.**

- [ ] T004 Implement the clean-variant generator in `tests/fixtures/finance_gl/generate.py` honoring every determinism obligation in `contracts/generator-contract.md` (single `random.Random(20260730)`, no clock, no uuid4, `Decimal` amounts, declared sort order, explicit `\n`) -- `mechanical`
- [ ] T005 Emit the five clean sources per `contracts/fixture-schema.md` column order: `finance_gl_actuals.csv`, `finance_gl_budget.csv`, `accounts.csv`, `departments.csv`, `fiscal_calendar.csv` -- `mechanical`
- [ ] T006 Enforce the generator's content invariants in code: one of debit/credit non-zero per line, every journal entry balances, unique (`journal_entry_id`, `line_id`), every `posting_date` inside a declared fiscal period, P&L accounts only -- `mechanical`
- [ ] T007 Write the determinism unit test in `tests/unit/test_finance_gl_generator.py`: generate twice into two temp dirs, compare bytes AND per-file SHA-256, assert equality -- `mechanical`
- [ ] T008 [P] Write the schema/grain unit test asserting declared PK uniqueness for both sources and the FK closure of `account_code` / `department_code` / `cost_center_code` against the reference files -- `mechanical`
- [ ] T009 [P] Commit the tiny excerpts `tests/fixtures/finance_gl/excerpts/finance_gl_actuals.head.csv` and `finance_gl_budget.head.csv` (tens of rows) for documentation citation -- `mechanical`
- [ ] T010 Verify no new dependency was introduced: confirm `pyproject.toml` is byte-unchanged -- `mechanical`

**Checkpoint**: fixtures regenerate byte-identically; no dependency added. Slice A done.

---

## Phase 3: User Story 1 -- non-retail domain through the existing spine (Priority: P1) (Slice C)

**Goal**: both finance sources reach Mapping Ready, then Silver/Gold SQL is authored, using
only existing templates -- with every obstruction recorded as it is hit.

**Independent test**: a fresh agent given only the clean fixtures and the existing generic
templates produces the five mapping artifacts per table without inventing a template and
without editing kit code; every place it wanted to edit kit code is a ledger row.

- [ ] T011 [US1] Create `docs/worked-examples/finance-gl-genericity-ledger.md` with the row schema from `data-model.md` Section 5 and an explicitly empty row set -- open it FIRST so obstructions are recorded as encountered, not reconstructed later -- `mechanical`
- [ ] T012 [P] [US1] Author `mappings/finance_gl_actuals/source-profile.md` from the generated clean fixture (column types, cardinalities, grain candidates); mark every live-DB leg `[PENDING LIVE PROFILE]` -- `mechanical`
- [ ] T013 [P] [US1] Author `mappings/finance_gl_budget/source-profile.md` the same way, at ITS own grain -- `mechanical`
- [ ] T014 [US1] Author `mappings/finance_gl_actuals/source-map.yaml` declaring grain (journal entry x line) and PK, using the existing template with zero new fields -- `mechanical`
- [ ] T015 [US1] Author `mappings/finance_gl_budget/source-map.yaml` declaring grain (fiscal quarter x account x dept x version) and PK -- distinct from actuals; no merged grain anywhere -- `mechanical`
- [ ] T016 [P] [US1] Author `assumptions.md` for both tables, including the calendar-aligned fiscal-year fixture simplification and the single-currency clean-fixture assumption, each with its triggering data fact -- `mechanical`
- [ ] T017 [P] [US1] Author `unresolved-questions.md` for both tables carrying OD-1 (sign convention), OD-2 (baseline), OD-3 (allocation) as open, named, blocking questions -- `mechanical`
- [ ] T018 [US1] Record every deviation from the ratified cleaning defaults (`docs/decisions/0002-retail-cleaning-defaults.md`) with the data fact that triggered it -- `mechanical`
- [ ] T019 [US1] Author `mappings/finance_gl_actuals/readiness-status.yaml` and `mappings/finance_gl_budget/readiness-status.yaml` following the shape observed in `mappings/retail_store_sales/readiness-status.yaml`; Stage 2 stays blocked pending approval -- `mechanical`
- [ ] T020 [US1] Raise the mapping-gate approval request per table (existing approval-request template); do NOT record any approval -- `mechanical`
- [ ] T021 [US1] **STOP**: obtain the named-human mapping-gate approval for each finance table -- `approval_gated` `human_only` (OD-4)
- [ ] T022 [US1] Author `warehouse/migrations/0006_create_silver_finance_gl_actuals.sql` -- authoring only, never executed -- `mechanical` (blocked by T021)
- [ ] T023 [US1] Author `warehouse/migrations/0007_create_silver_finance_gl_budget.sql` -- `mechanical` (blocked by T021)
- [ ] T024 [US1] Author `warehouse/migrations/0008_create_gold_finance_gl_star.sql`: two facts (`fact_gl_actuals`, `fact_gl_budget`) + conformed `dim_date`/`dim_account`/`dim_department` with the existing surrogate-key and unknown-member conventions -- `mechanical`
- [ ] T024a [US1] Verify the authored gold SQL against FR-010: no statement spreads, allocates, divides, or otherwise disaggregates `budget_amount` to a finer grain than fiscal quarter; record the inspected statements as evidence -- `mechanical`
- [ ] T024b [US1] Verify the authored gold SQL against FR-011: `budget_version` is part of `fact_gl_budget`'s key, and no statement updates, deletes, or overwrites a prior version's rows -- `mechanical`
- [ ] T025 [US1] Run `python -m seshat.cli check` and record the exact output; fix authored SQL/docs only -- never a kit module -- `mechanical`
- [ ] T026 [US1] Append every obstruction encountered in T012-T025 to the ledger with location, classification, minimal resolution, `core_change_required`, and evidence -- `mechanical`

**Checkpoint**: US1 delivers the genericity verdict for stages 1-4 on its own.

---

## Phase 4: User Story 2 -- the gate on a domain it was never built for (Priority: P1) (Slice B)

**Goal**: 13 isolated defect variants, each with a declared expected outcome and an observed
outcome, including the deliberate over-refusal trap.

**Independent test**: every variant's observed behaviour is compared to its declared
expected behaviour from the existing categorical set, and mismatches -- including
over-refusals -- are reported rather than tuned away.

- [ ] T027 [US2] Extend `tests/fixtures/finance_gl/generate.py` with named data variants D1-D7, D10, D12 per `contracts/fixture-schema.md`; each differs from clean in exactly one respect; unknown variant raises -- `mechanical`
- [ ] T028 [P] [US2] Unit-test that each data variant differs from clean in exactly the intended way and remains deterministic -- `mechanical`
- [ ] T029 [US2] Author `benchmark/scenarios/finance-gl-judgment.yaml` in the EXISTING scenario format for D8-D13, each declaring one behaviour from `("proceed", "refuse", "block_for_evidence", "request_human_decision")` plus its observable evidence -- `mechanical`
- [ ] T030 [US2] Run each structural variant D1-D7 through the existing static gate and mapping checks; record declared vs observed outcome verbatim -- `mechanical`
- [ ] T031 [US2] Run the judgment scenarios D8-D13 and record declared vs observed outcome verbatim -- `mechanical`
- [ ] T032 [US2] Verify D12 (actuals with no budget row) yields `proceed`; if the gate refuses it, record `over_refusal` as a FINDING and do not adjust the scenario to make it pass -- `mechanical`
- [ ] T033 [US2] For any variant that fires nothing at all, record a ledger row (the gate is silent where a general analytical gate arguably should speak) rather than deleting the variant -- `mechanical`
- [ ] T034 [US2] Confirm no rule was added or modified anywhere in this phase: `src/seshat/rules/` byte-unchanged -- `mechanical`

**Checkpoint**: refusal behaviour on a non-retail domain is observable and repeatable.

---

## Phase 5: User Story 3 -- finish in a committed, data-bound page (Priority: P2) (Slices D + E)

**Goal**: seven approved metric contracts, then one committed PBIR page whose every visual
binds to exactly one contract.

**Independent test**: one committed page exists; binding validation passes; no visual
references an unapproved or non-existent measure.

- [ ] T035 [P] [US3] Author the Actual Amount and Budget Amount contracts from `templates/metric-contract.yaml` with zero new/renamed fields -- `mechanical`
- [ ] T036 [P] [US3] Author the Variance Amount and Variance % contracts, citing `docs/patterns/target-budget-fact.md` Section 3 for post-aggregation ratio computation and prohibiting averaged percentages in the stated intent -- `mechanical`
- [ ] T037 [P] [US3] Author the Actual YTD and Budget YTD contracts at the declared comparison grain -- `mechanical`
- [ ] T038 [P] [US3] Author the Missing Budget Flag contract, making missing distinguishable from zero -- `mechanical`
- [ ] T039 [US3] Populate each contract's ambiguity ledger and blocking reasons with OD-1/OD-2 where applicable; invent no RAG threshold, no sign policy, no preferred budget version -- `mechanical`
- [ ] T040 [US3] **STOP**: obtain named-human rulings on OD-1 (sign/presentation) and OD-2 (baseline) -- `approval_gated` `human_only`
- [ ] T041 [US3] Finalize the affected contracts using the recorded rulings, citing approver and date -- `mechanical` (blocked by T040)
- [ ] T042 [US3] Author the semantic model TMDL so every measure traces to exactly one approved contract; keep PBIP names short for the Windows path limit -- `mechanical`
- [ ] T043 [US3] Author the page blueprint and the visual-to-contract binding map for all 8 visuals in `plan.md`'s classification table -- `mechanical`
- [ ] T044 [US3] **STOP**: a named human authors the "Executive P&L Overview" page in Power BI Desktop and commits the PBIR -- `human_only` (OD-5; the adapter cannot create or bind visuals)
- [ ] T045 [US3] Run PBIR binding validation against the committed page; confirm every visual resolves to an approved contract -- `mechanical` (blocked by T044)
- [ ] T046 [US3] Apply theme, formatting, and geometry through the supported adapter surfaces only, preserving data bindings byte-for-byte -- `mechanical`
- [ ] T047 [US3] Recompute readiness; record Dashboard Ready from committed evidence and leave Publish Ready explicitly out of scope and unclaimed -- `mechanical`

**Checkpoint**: `find powerbi -name "visual.json"` returns a non-zero count for the first time in this repository.

---

## Phase 6: User Story 4 -- example growth, not capability growth (Priority: P2) (Slice F)

- [ ] T048 [US4] Author `docs/worked-examples/finance-gl-budget-vs-actual.md` following the existing example's SECTION STRUCTURE without copying its answers -- `mechanical`
- [ ] T049 [US4] Complete the ledger: classify every row (`no_leak` | `nominal_leak` | `documentation_leak` | `semantic_leak` | `authority_leak`), resolve nominal/semantic ties to `semantic_leak`, collapse repeat sightings into one row with multiple cited locations -- `mechanical`
- [ ] T050 [US4] Write the ledger's CATEGORICAL conclusion and its consequence: `no_leak`/`nominal_leak` only -> positioning and documentation follow-on; any `semantic_leak` -> a separately approved feature MAY propose a minimal seam; any `authority_leak` -> raise for explicit human decision. No count threshold, no score -- `mechanical`
- [ ] T051 [US4] State plainly in the ledger and the worked example that the kit's capability surface did not change and that "Seshat now supports finance" is NOT a claim this feature makes -- `mechanical`
- [ ] T052 [P] [US4] Add exactly ONE index row to `docs/worked-examples/README.md` (domain, spine depth, best-read-for) -- `mechanical`
- [ ] T053 [P] [US4] Determine from each registry's own completeness contract whether `docs/quality/status-claims.yaml` and `docs/capabilities/capabilities.yaml` require an entry; add only what their contracts require, declaring no capability that does not exist -- `mechanical`
- [ ] T054 [US4] Produce the negative-proof diff evidence: no rule module added/removed/renamed, no CLI verb added/renamed, no skill directory added/renamed, `pyproject.toml` unchanged -- `mechanical`
- [ ] T054a [US4] Satisfy SC-009: for every readiness stage the example did NOT reach, record the blocker with its evidence in that table's `readiness-status.yaml` AND a corresponding ledger row, so an incomplete traversal is legible as a finding rather than an omission -- `mechanical`
- [ ] T055 [US4] Confirm no bundle regeneration is required by showing `skills/**` and `.claude/skills/**` are unchanged; if either changed, run `python scripts/export_agent_bundles.py --repo .` and explain why the change was unavoidable -- `mechanical`

---

## Phase 7: Polish and cross-cutting verification

- [ ] T056 Run `python -m seshat.cli check` on the complete branch and record exact output -- `mechanical`
- [ ] T057 [P] Run `python -m pytest -m unit -q` on a quiescent tree and record exact output; do not edit files during the run -- `mechanical`
- [ ] T058 [P] Sweep every artifact this feature added for a numeric confidence/health/maturity/readiness/genericity score and remove any found -- `mechanical`
- [ ] T059 [P] Sweep for self-granted approvals: every `approvals[]` entry names a human and a date, and none was recorded by the authoring agent -- `mechanical`
- [ ] T060 [P] Sweep for secrets, real company data, personal data, and local absolute paths in all added files -- `mechanical`
- [ ] T061 [P] Confirm UTF-8 without BOM, ASCII-only in manifest-style YAML, and that no added path breaks the Windows path-length limit -- `mechanical`
- [ ] T062 Confirm every live leg reads `[PENDING LIVE PROFILE]` and that no live-validated number is claimed anywhere -- `mechanical`
- [ ] T063 Score the example against spec 084's repo-only completeness tier and record the result categorically -- `mechanical`

---

## Dependencies and execution order

```text
Phase 1 (Setup)
  └── Phase 2 (Generator, Slice A)   <-- BLOCKS everything
        ├── Phase 3 (US1, Slice C) ──┬── T021 approval gate ── T022-T026
        └── Phase 4 (US2, Slice B)   │   (US2 needs only the generator, so it runs
                                     │    IN PARALLEL with US1)
              Phase 5 (US3, Slices D+E) <-- needs US1's gold model
                    ├── T040 approval gate ── T041
                    └── T044 human authoring ── T045-T047
                          Phase 6 (US4, Slice F) <-- needs the ledger rows from US1+US2
                                Phase 7 (Polish)
```

- **US1 and US2 are genuinely independent** after Phase 2: US2 exercises the gate against
  variants and needs no mapping artifacts.
- **US3 depends on US1** (it needs the gold model and contracts) and on two human actions.
- **US4 depends on US1 + US2** (the ledger must have its rows) but NOT on US3; if US3 stalls
  on the human authoring step, US4 still completes with US3 recorded as blocked.

## Parallel opportunities

- Phase 2: T008, T009 in parallel after T005.
- Phase 3: T012/T013 in parallel; T016/T017 in parallel.
- Phase 4: runs in parallel with Phase 3 in its entirety.
- Phase 5: T035-T038 in parallel.
- Phase 6: T052, T053 in parallel.
- Phase 7: T057-T061 in parallel.

## Implementation strategy

**MVP = Phase 2 + Phase 3 + Phase 4.** That combination already answers the question the
feature exists to answer: does the existing spine run a non-retail domain, and does the gate
behave correctly there. Phases 5-6 make the corpus finished and the result legible; Phase 5
cannot complete without two human actions and must never be simulated.

**Stop conditions** (halt and raise rather than proceed):
- A kit module edit looks unavoidable -> ledger row + owner decision, not an edit.
- An approval is missing -> the stage stays blocked; never self-grant.
- A business judgment has no ruling -> leave it open and blocking; never default it.

## Task count summary

| Phase | Tasks | Notes |
|---|---|---|
| 1 Setup | T001-T003 (3) | |
| 2 Foundational (A) | T004-T010 (7) | blocks all |
| 3 US1 (C) | T011-T026 incl. T024a/T024b (18) | 1 approval gate |
| 4 US2 (B) | T027-T034 (8) | parallel with US1 |
| 5 US3 (D+E) | T035-T047 (13) | 1 approval gate + 1 human authoring |
| 6 US4 (F) | T048-T055 incl. T054a (9) | |
| 7 Polish | T056-T063 (8) | |
| **Total** | **66** | `approval_gated`: T021, T040 (2). `human_only`: T021, T040, T044 (3) -- T021 and T040 carry both labels. |
