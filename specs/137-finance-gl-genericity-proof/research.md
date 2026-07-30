# Phase 0 Research: Finance GL Budget-vs-Actual Genericity Proof

**Feature**: 137-finance-gl-genericity-proof | **Date**: 2026-07-30

Every decision below is recorded as Decision / Rationale / Alternatives. Repository facts
were read from the tree on 2026-07-30; external modelling guidance is cited as a design
reference only and no external data is committed.

---

## R1. Is a second worked example even needed, or is this already covered?

**Decision**: needed, and it is not covered. Proceed as a NEW feature that executes spec
084's recipe rather than editing 084, 095, or 091.

**Rationale** (verified in the tree):
- `docs/worked-examples/README.md` lists exactly ONE example (`retail-store-sales.md`).
- `specs/084-worked-example-factory` (status `Draft`) defines the PROCESS and states
  explicitly: "It does not execute the recipe."
- `specs/095-actuals-vs-target-budget-fact` (status `Draft`) produced a PATTERN
  (`docs/patterns/target-budget-fact.md`) and a CONTRACT SHAPE
  (`templates/metric-contract-shape.variance-vs-target.yaml`); the pattern doc's own
  header says "No target/budget fact exists anywhere in this kit today," and 095's spec
  says its walkthrough "MUST stay a pattern/shape walkthrough (no live target rows)."
- `specs/091-semi-additive-snapshot-grain` (status `Draft`) owns semi-additive grain.

So the pattern exists on paper and has never been instantiated with rows, in any domain.
This feature is the first instantiation and the first non-retail one.

**Alternatives considered**:
- *Implement 095 directly* -- rejected: 095 is scoped to a hypothetical target fact
  conformed to the RETAIL actuals star, so implementing it would prove nothing about
  domain-generality and would silently rewrite another spec's scope.
- *Extend the retail example with a budget fact* -- rejected for the same reason: same
  domain, so Principle VII stays untested.

---

## R2. Which structural difference from retail is actually being tested?

**Decision**: grain mismatch, variance-baseline ambiguity, and budget-version identity.
NOT semi-additivity.

**Rationale**: retail sales are additive transaction facts, so an additive second domain
would test almost nothing. Finance P&L introduces a deliberate grain mismatch (journal-line
actuals vs quarter budgets) plus a genuine business ambiguity about what "budget" means.
Semi-additive balances would be a fourth axis, but modelling a balance inside a
journal-line fact is wrong modelling, and spec 091 already owns that axis. Excluding it
keeps this feature honest and non-overlapping.

**External design reference** (shape only, no data): balance amounts are the canonical
semi-additive case -- additive across every dimension except time -- which is precisely why
they belong to a snapshot fact rather than a journal-line fact; and budget-vs-actual is
conventionally modelled as separate facts at their native grains joined through conformed
dimensions rather than forced into one table. See the Sources section.

**Consequence recorded in the spec**: the ledger MUST NOT claim semi-additive handling was
proven generic.

---

## R3. Commit the generated CSVs, or generate them at verification time?

**Decision**: do NOT commit the full CSVs. Commit the generator plus tiny excerpts; write
full outputs to a git-ignored directory during verification.

**Rationale** -- measured, not preferred:

| Existing committed fixture | Size |
|---|---|
| `tests/fixtures/demo/demo_sample_orders.csv` | 1,801 bytes |
| `distribution/synthetic-retail/source.csv` | 447 bytes |
| `benchmark/scenarios/fixtures/synthetic-orders.csv` | 343 bytes |

The largest data fixture the repository has ever committed is ~1.8 KB. A ~5,000-line
journal-line CSV is two orders of magnitude larger. Committing it would establish a
bulk-data-in-tree precedent that the repo's own raw-data posture argues against, for no
review benefit (nobody reads 5,000 rows). Excerpts give reviewers something concrete to
read; the generator plus a determinism test gives CI something exact to verify.

**Alternatives considered**:
- *Commit everything* -- rejected on the size evidence above.
- *Commit nothing at all* -- rejected: documentation needs a citable sample, and a
  reviewer should be able to see the column shape without running code.
- *Shrink the fixture to ~200 lines so it can be committed* -- rejected: the grain-mismatch
  and missing-budget scenarios need enough departments x quarters x accounts to be
  realistic; shrinking to fit a storage preference would weaken the experiment.

---

## R4. How should refusal behaviour be observed?

**Decision**: reuse the EXISTING benchmark scenario format for the six business-judgment
cases. Add no new format, no new runner, no new participant kind.

**Rationale**: `src/seshat/benchmark/model.py` already defines exactly the vocabulary this
feature needs -- `BEHAVIORS = ("proceed", "refuse", "block_for_evidence",
"request_human_decision")`, observed behaviours including `unparseable`, and categorical
comparison outcomes `("match", "over_refusal", "mismatch")` with the in-code comment
"never aggregated into a score". `over_refusal` as a first-class outcome is what makes the
paralysis failure mode visible, and `benchmark/scenarios/hard-stops.yaml` plus
`retail-semantics.yaml` show the shape a scenario file takes.

**Alternatives considered**:
- *Assert governance behaviour only in prose in the worked example* -- rejected: not
  runnable, so it decays.
- *Write a bespoke finance test harness* -- rejected: a second harness is drift, and the
  existing one already grades exactly what matters.

---

## R5. What can the PBIR adapter actually do, and what must a human do?

**Decision**: all eight visuals are `human_only` for creation and data binding; the agent
authors the blueprint, binding map, theme, formatting, geometry, and runs binding
validation.

**Rationale**: `docs/integrations/pbir-adapter.md` states the adapter's increments and
their limits directly -- per-visual formatting (B) and geometry (D) operate on an EXISTING
`visual.json` with "data binding preserved byte-for-byte", the adapter performs "No data
bindings / measures / DAX / relationships / semantic-model edits", and it "does not
populate an empty page or author visuals". There is therefore no supported path for an
agent to create a data-bound visual today.

Corroborating repo fact: `find powerbi -name "visual.json"` returns **0** -- the existing
`powerbi/RetailStoreSales.Report` has `definition/pages/<id>/page.json` and no visuals at
all. So no committed report visual has ever existed in this repo, by any means.

**Alternatives considered**:
- *Assume the adapter can create bound visuals* -- rejected: contradicted by its own docs;
  planning on it would produce an undeliverable task list.
- *Wait for the Power BI MCP execution adapter (F016)* -- rejected: ADR-0018 is
  `Proposed -- NOT ratified`, so F016 authorizes nothing today.

---

## R6. Where do the finance artifacts live?

**Decision**: new sibling paths beside the existing ones, following observed conventions:
`mappings/<table>/` per source table, `warehouse/migrations/NNNN_*.sql` continuing the
existing sequence (next free number is 0006), `benchmark/scenarios/*.yaml`,
`docs/worked-examples/*.md`, `tests/fixtures/<subject>/`.

**Rationale**: read from the tree -- `mappings/retail_store_sales/` contains
`source-profile.md`, `source-map.yaml`, `assumptions.md`, `unresolved-questions.md`,
`readiness-status.yaml` (plus approval requests/decisions, narrative, reconciliation,
`metrics/`, `design/`, `handoff/`); `warehouse/migrations/` currently holds `0003`-`0005`;
`packs/reference/*/fixtures/synthetic-*.csv` and `distribution/synthetic-retail/source.csv`
establish the `synthetic-*` naming habit for generated data.

**Alternatives considered**: a single `finance/` top-level tree -- rejected: it would
fragment the spine's per-table conventions and make the readiness projection unable to find
the records.

---

## R7. Does anything here require a new rule or a kit change?

**Decision**: no, by design. The feature adds zero rules and edits no kit module. Any
obstruction that seems to demand one is a ledger row plus an owner decision.

**Rationale**: the rules the finance domain naturally exercises already exist and are
domain-neutral by name and by content -- `conformed_dimension`, `date_spine`,
`currency_unit`, `additivity_consistency`, `comparison_baseline`, `assumption_coherence`
(all under `src/seshat/rules/`). Adding a rule inside this feature would also break the
experiment: a rule written FOR finance cannot be evidence that the existing gate was
already general.

**Nominal-vs-semantic note for the ledger's baseline**: the CLI already renamed --
`pyproject.toml` declares `seshat = "seshat.cli:main"` as the primary console script with
`retail` kept as a "deprecated compatibility alias ... for one deprecation cycle". So a
`retail-*` name encountered during the walk is usually a `nominal_leak` against an
already-in-progress rename, not a live semantic constraint. Classify accordingly and cite
this fact.

---

## R8. What does "done" mean when no live database exists?

**Decision**: score against spec 084's **repo-only completeness tier**; mark every live leg
`[PENDING LIVE PROFILE]`.

**Rationale**: spec 084's acceptance scenario for User Story 2 states that a candidate
reaching Gold Ready with no live DB is "scored against the repo-only completeness tier
(artifacts authored, `retail check` clean, live legs explicitly `[PENDING LIVE PROFILE]`)
rather than being rejected outright or silently marked complete." Constitution Principle
VIII independently defers live runs. This feature therefore claims no live-validated
numbers.

---

## Sources

Repository (read 2026-07-30): `.specify/memory/constitution.md`;
`specs/084-worked-example-factory/spec.md`;
`specs/095-actuals-vs-target-budget-fact/spec.md`;
`specs/091-semi-additive-snapshot-grain/spec.md`; `docs/patterns/target-budget-fact.md`;
`templates/metric-contract-shape.variance-vs-target.yaml`;
`docs/integrations/pbir-adapter.md`; `src/seshat/benchmark/model.py`;
`src/seshat/rules/`; `mappings/retail_store_sales/`; `warehouse/migrations/`;
`docs/worked-examples/README.md`; `pyproject.toml`.

External design references (shape only; no data committed):
- Kimball Group, "Additive, Semi-Additive, Non-Additive Facts" --
  https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/
- Kimball forum, "Actual Vs Budget Amount in Sales DW" --
  https://kimballgroup.forumotion.net/t789-actual-vs-budget-amount-in-sales-dw
- Star Schema, "Know your facts Part 1: Power BI, Financial Statements & Kimball" --
  https://www.starschema.co.uk/post/know-your-facts-part-1-power-bi-financial-statements-kimball
- US Standard General Ledger account structure (chart-of-accounts SHAPE reference) --
  https://huggingface.co/datasets/leeroy-jankins/US-Standard-General-Ledger-Accounts-And-Definitions
- U.S. Treasury Fiscal Data, Summary General Ledger Balances (period/structure reference) --
  https://fiscaldata.treasury.gov/datasets/fbp-summary-general-ledger-balances-report/
