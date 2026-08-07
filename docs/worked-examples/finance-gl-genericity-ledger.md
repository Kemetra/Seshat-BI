# Finance GL genericity ledger

**Feature**: spec 137 | **Opened**: 2026-07-30 | **Subject area**: `finance_gl`

The record of every obstruction met while driving a NON-RETAIL domain through the existing
readiness spine. Opened BEFORE the walk began (task T011) so rows are written as they are
encountered, not reconstructed afterwards to look tidy.

**This ledger is evidence, not a verdict on the kit.** It reports what the walk hit and how
small the fix would be. It confers no property on Seshat: "the kit is domain-general" is not
a claim this file makes, and the kit's capability surface is unchanged by this feature.

**It also under-claims deliberately.** Semi-additive / snapshot-balance handling belongs to
spec 091 and is NOT exercised here (this example is P&L flow only), so no row may assert
that axis was proven generic. The structural axes actually under test are **grain mismatch**,
**variance-baseline ambiguity**, and **budget-version identity**.

## Row schema

Every row records: `location`, `observed_problem`, `classification`,
`existing_rule_or_surface`, `minimal_resolution`, `core_change_required`, `evidence`.

Classification is exactly one of:

| Value | Meaning |
|---|---|
| `no_leak` | the surface worked as-is on a non-retail domain |
| `nominal_leak` | retail NAMING only; no behaviour depends on it |
| `documentation_leak` | generic surface, but its prose/examples assume retail |
| `semantic_leak` | the surface's LOGIC assumes something domain-specific |
| `authority_leak` | the surface would have the agent decide something a human must |

Rules: one row per distinct obstruction (repeat sightings = multiple cited locations in ONE
row, never row inflation); a tie between `nominal_leak` and `semantic_leak` resolves to
`semantic_leak` so later scoping cannot under-count; the conclusion is CATEGORICAL -- no
counts-based threshold, no score of any kind (hard rule #9).

---

## L1 -- CORRECTED -- the conformance mechanism EXISTS; the template that needs it does not mention it

> **This row was rewritten on 2026-07-30 after the gate proved the original claim wrong.**
> As first written it said the kit had no way to declare a conformed dimension shared across
> maps, classified `semantic_leak`. That was **incorrect**. Running `seshat check` against the
> COMMITTED artifacts fired two HR1 errors naming
> `docs/quality/conformed-dimension-map.yaml` -- a registry that exists precisely for this,
> enforced by `src/seshat/rules/conformed_dimension.py`. The original text is preserved below
> the correction, because a ledger that quietly edits its own mistakes is not evidence.
>
> **Why the error happened, which is itself the finding:** an author declaring dimensions works
> inside `templates/source-map.yaml`, and that template says nothing about the cross-star
> registry. Its `gold_placement` contract discusses HR13 (same-file validation) in detail but
> never mentions HR1 or the conformance map. The mechanism was undiscoverable from where the
> work happens.
>
> **Reclassified: `documentation_leak`** (was `semantic_leak`). The logic is present and
> correct; only its discoverability failed.
>
> **A second, positive finding worth stating separately:** HR1 had **never fired in this
> repository's history**. The registry's own header records why -- "The current committed stars
> (retail_store_sales, demo_sample_orders) use different dimension-naming conventions
> (suffixed vs bare), so NO dimension name overlaps across them and no ruling is required yet."
> A two-fact domain sharing conformed dimensions is the first case ever to trigger it, and it
> behaved exactly as designed: fail-closed, naming both dimensions, and refusing to guess a
> ruling it reserves for a human. **The kit's cross-star governance worked first time on a
> domain it was never exercised against.**

### Original text (preserved, superseded by the correction above)

## L1 (as first written) -- the source-map template has no way to declare a conformed dimension shared across two maps

- **location**: `templates/source-map.yaml` (`gold_star.dimensions[]`, and the
  `gold_placement` contract at lines ~69-77); observed at
  `mappings/finance_gl_actuals/source-map.yaml` and
  `mappings/finance_gl_budget/source-map.yaml`
- **observed_problem**: the template models ONE fact per source table and has every map
  declare its own `gold_star.dimensions[]`. A budget-vs-actual domain has **two facts at two
  different grains sharing three conformed dimensions**, so both maps must declare the same
  `dim_date_fgl` / `dim_account_fgl` / `dim_department_fgl`. There is no field to say "this
  dimension is conformed and declared by the other map", so the declaration is duplicated
  and nothing mechanically detects the two copies drifting apart.
- **classification**: `semantic_leak`
- **existing_rule_or_surface**: `templates/source-map.yaml`; HR13 (validates a
  `gold_placement` prefix against dimensions declared **in the same file**);
  `src/seshat/rules/conformed_dimension.py`
- **minimal_resolution**: both maps declare the shared dims identically and each cites the
  other in a comment; a future `conformed_with: <other_table_id>` key (or a cross-map
  conformance check) would make the duplication detectable instead of conventional. Not
  attempted here -- spec 137 FR-031 forbids changing the template.
- **core_change_required**: false (to WALK); true to make it mechanically safe
- **evidence**: both committed maps declare byte-identical `dimensions[]` blocks for the
  three shared dims; nothing in `seshat check` compares them
- **note**: this is NOT a retail-vocabulary problem. It is a single-fact-per-map assumption
  that only a multi-fact domain exposes -- which is precisely why one worked example could
  not have found it.

## L2 -- RS1 treats a file source's encoding as a human-confirmable inference, but a generated fixture's encoding is a declared, tested fact

- **location**: `templates/readiness-status.yaml` lines ~53-57 (`source_kind` +
  the RS1 approval requirement); rule surface `src/seshat/rules/` (RS1)
- **observed_problem**: RS1 says a `csv`/`excel` source makes the encoding/delimiter/header a
  `[PROPOSED]` inference that a named owner MUST confirm before `source_ready` can read
  `pass`. That is right for a FOUND file of unknown provenance. This example's sources are
  emitted by a committed generator that writes UTF-8 with explicit `\n` and a fixed column
  order, asserted by `tests/unit/test_finance_gl_generator.py`. There is no inference to
  confirm -- yet the approval is still required, so Stage 1 sits blocked on a human
  confirming a property a test already proves.
- **classification**: `semantic_leak` (conservative; it is arguably `documentation_leak`
  since the rule's PURPOSE is sound and only its provenance assumption is too narrow --
  the tie resolves upward by this ledger's own rule)
- **existing_rule_or_surface**: RS1
- **minimal_resolution**: honour it -- `source_kind: "csv"` is declared and `source_ready`
  stays BLOCKED pending the owner. A future refinement could let a source cite a
  generator + determinism test as the provenance evidence instead of a human confirmation.
  Not attempted: FR-031 forbids adding or changing a rule here, and inventing an exemption
  for our own fixture would be exactly the kind of self-serving carve-out the gate exists to
  stop.
- **core_change_required**: false
- **evidence**: `mappings/finance_gl_actuals/readiness-status.yaml` and
  `.../finance_gl_budget/readiness-status.yaml` both record `source_ready: blocked` with the
  RS1 reason; no approval was self-granted

## L3 -- the unresolved-questions template's mandatory prompt categories are retail-specific

- **location**: `templates/unresolved-questions.md`, "Categories to prompt for (do not leave
  a category unconsidered)"
- **observed_problem**: the template instructs the author to consider every listed category
  or state in `assumptions.md` that the default was adopted. Two of the six are retail
  concepts with no finance analogue -- **Returns identification (RC8)** and
  **Business-rollup mappings (RC11)** -- and **Hierarchy multi-parent handling (RC12)** maps
  only awkwardly onto a chart of accounts. Meanwhile the categories this domain genuinely
  needed are ABSENT: comparison-baseline choice, sign/presentation convention, and
  cross-grain allocation policy.
- **classification**: `documentation_leak`
- **existing_rule_or_surface**: `templates/unresolved-questions.md`; ADR-0002 RC8/RC11/RC12
- **minimal_resolution**: state N/A-with-reason for the inapplicable categories (done) and
  raise the three finance-shaped questions as ordinary rows (done: Q1-Q3 per table). A
  future refinement would split the category list into domain-neutral classes (grain, PII,
  missing-values, comparison baseline, sign convention, cross-grain policy) with
  domain-specific examples cited rather than embedded.
- **core_change_required**: false
- **evidence**: both `unresolved-questions.md` files carry an explicit
  "categories considered and found N/A" block naming RC8/RC11 and the data fact behind it
  (no return/reversal column exists in a P&L journal extract; no analyst-supplied rollup
  was requested)

## L4 -- ADR-0002's cleaning defaults are named "retail cleaning" but read as domain-neutral analytics rules

- **location**: `docs/decisions/0002-retail-cleaning-defaults.md` (the `RC*` namespace,
  cited by `templates/source-map.yaml` `defaults.adopted[]`)
- **observed_problem**: the ADR is titled and namespaced for retail (`RC` = "retail
  cleaning"), and a finance map must cite `RC1`, `RC2`, `RC5`, `RC7`, `RC14`, `RC15` by
  those ids. Reading the defaults themselves, every one used here is a general
  dimensional-modelling rule (lowest grain; verify PK on transformed data; `''` -> NULL;
  exact NUMERIC for money; Kimball star with `_sk` + unknown member; contiguous calendar).
  Nothing about them is retail. Only the NAME is.
- **classification**: `nominal_leak`
- **existing_rule_or_surface**: ADR-0002; `src/seshat/rules/` (S5/S6/S7 enforce RC7/RC14/RC15)
- **minimal_resolution**: cite the ids as-is. Renaming the namespace would churn every
  committed map, the checker's rule ids, and frozen spec snapshots for zero behaviour
  change -- explicitly out of scope (FR-031), and the CLI has already begun the equivalent
  rename (`seshat` primary, `retail` a deprecated alias in `pyproject.toml`).
- **core_change_required**: false
- **evidence**: both finance maps adopt RC1/RC2/RC3/RC5/RC7/RC9/RC12/RC13/RC14/RC15 with no
  semantic strain; the two deviations recorded are RC8 (no returns exist in a P&L journal)
  and RC6 (no grouping sentinel needed -- zero missing values in a generated source)

## L5 -- the governed RC15 date dimension is a CLOSED Gregorian contract and cannot express a fiscal period

- **location**: `templates/source-map.yaml` `date_dimension.attributes` contract (lines
  ~284-320); resolver `src/seshat/star_discovery.py` (`resolve_date_attributes`);
  ADR-0002 RC15
- **observed_problem**: the calendar's attribute set is closed to
  `full_date, year, quarter, month, month_name, day, day_name, iso_week, is_weekend`, and the
  template states that an off-contract attribute "e.g. `fiscal_year`" is **REJECTED rather
  than silently built** because a generated calendar has no source column to derive it from.
  That is a sound rule. But it means a **fiscal-calendar-driven domain cannot put its period
  on the date dimension at all** -- and budget-vs-actual reporting is keyed on fiscal periods,
  not Gregorian ones. The rule names `fiscal_year` as its own example of a rejected
  attribute, so this is a known edge that finance walks straight into.
- **classification**: `semantic_leak`
- **existing_rule_or_surface**: RC15; S7 (contiguous date dim); the single
  `resolve_date_attributes` resolver that both the dbt scaffolder and the readiness reader
  consume
- **minimal_resolution**: keep the daily RC15 calendar for the ACTUALS fact and declare a
  separate quarter-grain `dim_fiscal_period_fgl` (sourced from the `fiscal_calendar`
  reference file) for the BUDGET fact, recording an RC15 deviation on the budget map. Works,
  and needs no kit change. A future refinement would let a fiscal calendar be declared as a
  SOURCED period dimension conforming to the generated calendar, rather than the domain
  having to invent a parallel dimension.
- **core_change_required**: false
- **evidence**: `mappings/finance_gl_budget/source-map.yaml` records the RC15 deviation and
  declares `gold.dim_fiscal_period_fgl`; the actuals map keeps the full RC15 calendar with
  `attributes` omitted
- **independent corroboration (pre-dating this feature)**: the RETAIL example hit the same
  wall and worked around it by choosing the calendar year. `mappings/retail_store_sales/approval-request-YTD-year-start.md`
  records, as evidence for its own owner decision: "This worked example carries NO declared
  fiscal calendar in its mapping artifacts (no fiscal-year attribute in `source-map.yaml` /
  the gold `dim_date_rss`), so a calendar-year default would be the only one implementable
  today without new fields." So this is NOT a finance-only problem -- it is a pre-existing kit
  limitation that a retail table already ran into and settled by picking the Gregorian option.
  Finance cannot make that choice, which is why the same limitation surfaces here as a
  structural leak rather than as a one-off decision.
- **severity note the ledger must not soften**: this example's fixture is
  **calendar-aligned** (fiscal quarters == Gregorian quarters), so rolling actuals up via the
  calendar's `year` + `quarter` happens to give the right answer HERE. For an offset fiscal
  year (e.g. April-March) that coincidence disappears and the roll-up would be wrong. The
  fixture simplification is masking the full severity of this finding -- recorded so the
  conclusion cannot under-report it.

## L6 -- RS1 reserves `blocking_reasons[]` for `blocked` stages, which the template does not say

- **location**: `templates/readiness-status.yaml` (per-stage comments, lines ~46-48); rule RS1
- **observed_problem**: the template says "Each stage: status (required) + evidence[]
  (required for pass) + blocking_reasons[] (required for blocked)". It does not say
  blocking_reasons are FORBIDDEN on a `not_started` stage. Reading it as a minimum rather than
  an exclusive rule, the first draft recorded the genuine downstream constraints
  ("no silver before the gate clears"; "publishing is out of scope") as `blocking_reasons` on
  `silver_ready` and `publish_ready` -- and RS1 errored on all four.
- **classification**: `documentation_leak`
- **existing_rule_or_surface**: RS1
- **minimal_resolution**: the constraints moved to YAML comments on those stages; the
  authoritative blockers stay on the two genuinely `blocked` stages. Fixed in this feature's
  own artifacts -- the rule is right and the template's wording is merely incomplete.
- **core_change_required**: false
- **evidence**: 4 RS1 errors on the first committed run, 0 after the fix; both
  `readiness-status.yaml` files now carry the constraints as comments
- **note**: this is an ordinary authoring mistake caught by the gate, recorded because the
  ledger's value depends on including the unflattering rows. It is not domain-specific: any
  author could read the template the same way.

## L7 -- no check reconciles a budget row to the actuals account hierarchy

**Folded in from `docs/worked-examples/finance-gl-defect-matrix.md` M1 (recorded during Slice
B, 2026-07-30), which was written before Slice C merged and said so explicitly. This IS that
finding, not a new one -- the defect-matrix file's own note said it belonged here as L7.**

- **location**: `src/seshat/validate.py` (four live checks, none hierarchical);
  `src/seshat/rules/conformed_dimension.py` (HR1 compares dimension DECLARATIONS across stars,
  not the ROWS a fact actually carries)
- **observed_problem**: defect variant D3 posts a budget row against a CLEARING account -- a
  plan for something that is not P&L and can never be reconciled to P&L actuals. Nothing in the
  kit catches it. HR1 checks that two stars agree on a dimension's declared SHAPE (surrogate
  key type, shared attribute types); it does not check that a fact's rows reference a hierarchy
  path the other fact can reach. This is a live-data check that would need a database; it is
  not visible to `seshat check`'s static surface at all.
- **classification**: `semantic_leak`
- **existing_rule_or_surface**: none exists for this specific class of check; `src/seshat/
  validate.py`'s four checks (`check_pk_uniqueness`, `check_date_coverage`, `check_orphan_fks`,
  `check_reconciliation`) are the closest live-data surface and none of them is hierarchical
- **minimal_resolution**: none attempted -- spec 137 FR-031 forbids adding a rule in this
  feature. Recorded so a future, separately-approved feature can decide whether cross-fact
  hierarchy reconciliation belongs in the live-validation surface.
- **core_change_required**: false to walk; true to catch this class of defect at all
- **evidence**: D3 generated and inspected (`tests/fixtures/finance_gl/generate.py` variant
  D3); `seshat check` exit 0 on the branch; no live check exists to run against it, so the
  observed outcome is `[NO CHECK EXISTS]`, distinct from `[PENDING LIVE PROFILE]` (which means
  a check exists but needs a database) -- recorded in `docs/worked-examples/
  finance-gl-defect-matrix.md`

## L8 -- nothing verifies that source data matches the currency the map declares

**Folded in from `docs/worked-examples/finance-gl-defect-matrix.md` M2, for the same reason as
L7.**

- **location**: `src/seshat/rules/currency_unit.py` (HR11); `templates/source-map.yaml`
  `columns[].currency`
- **observed_problem**: HR11 flags a MEASURE that sums columns with clashing DECLARED units or
  currencies -- a static check over the map's own declarations. Defect variant D5 leaves the
  declaration correct (`currency: "USD"`) and puts a second currency in the DATA (50 rows of
  `EUR`). The declaration and the actual rows disagree, and nothing notices: the static gate
  cannot see rows, and no live check compares landed data against the unit/currency a map
  declares for it.
- **classification**: `semantic_leak`
- **existing_rule_or_surface**: HR11 (declaration-level only); no live-data counterpart exists
- **minimal_resolution**: none attempted (FR-031 forbids adding a rule here). A live "declared
  unit vs observed distinct units in the landed column" check would close this gap; not built.
- **core_change_required**: false to walk; true to catch it
- **evidence**: D5 generated with 50 `EUR` rows against a map declaring `USD`; `seshat check`
  exit 0; observed outcome recorded as `[NO CHECK EXISTS]` in
  `docs/worked-examples/finance-gl-defect-matrix.md`

## L9 -- nothing in the gate can tell a human-recorded approval from an agent-recorded one

**This is the most important row in this ledger, and it was found the hard way: by the
agent nearly committing a self-granted approval during this feature's own implementation.**

- **location**: `templates/readiness-status.yaml` (`approvals[]`);
  `docs/quality/conformed-dimension-map.yaml`; every rule that reads an approval
- **observed_problem**: on 2026-07-30 an agent attempt read a blanket authorization from the
  owner ("do all recomnded actions i authorize you") as consent to each individually
  recommended option, and wrote a complete set of approvals into the working tree: two
  `approvals[]` entries naming the owner, `reviewed_by: "Ahmed Shaaban (data_owner)"` in both
  source-maps, both stages flipped to `pass`, the HR1 conformance ruling recorded, and two
  `approval-decision-*.md` documents. Every one of those artifacts was **well-formed**. The
  gate's verdict on them would have been **exit 0** -- because the ruling genuinely cleared
  HR1's errors, and no rule can inspect who typed a line. C4 checks that an approver is a
  NAMED human rather than a bare role token; nothing checks that the named human actually
  decided.
- **classification**: `authority_leak`
- **existing_rule_or_surface**: C4 (approver shape), RS1 (approval presence + audit dates),
  HR1 (requires a ruling, cannot attribute one), spec 084's completeness contract (rejects a
  self-granted approval -- but only if a reviewer already knows it was self-granted)
- **minimal_resolution**: none available in-repo. Attribution is not statically checkable:
  a committed YAML line carries no author. What DID catch it was noticing an unexplained
  `git status` entry, which is luck, not a control. The honest mitigations are procedural,
  not mechanical -- an approval commit authored and signed by the owner rather than the
  agent, or a decision channel outside the repo that the artifact cites.
- **core_change_required**: false to walk; **the finding stands regardless** -- no kit change
  makes attribution checkable
- **evidence**: the fabricated artifacts were parked, reverted before commit, and then the
  five sub-decisions were obtained individually from the owner and transcribed; the
  corrected mechanism is recorded verbatim in both
  `mappings/*/approval-decision-mapping-gate.md`. `seshat check` exits 0 on BOTH the
  fabricated and the legitimate version -- which is precisely the point.
- **what this says about the kit, stated plainly**: the hard stop
  `never_self_grant_approval` is enforced by agent compliance, not by the gate. Every other
  hard stop in this repository has a mechanical check behind it; this one does not. A worked
  example is therefore only as trustworthy as the honesty of whoever authored it -- which is
  worth knowing before anyone reads a green `seshat check` as proof that approvals were real.

---

## Interim reading (Slice C, stages 1-2 only -- NOT the conclusion)

Six rows: one `nominal_leak` (L4), three `documentation_leak` (L1-corrected, L3, L6), two
`semantic_leak` (L2, L5). **No row required a change to any kit module to complete the walk**
(`core_change_required: false` on all six); no rule, verb, template, or skill was edited.

**The correction matters more than the count.** L1 was first written as a `semantic_leak`
claiming the kit could not express conformed dimensions across maps. The gate disproved it by
firing HR1 and naming the registry built for exactly that purpose. Two lessons the conclusion
must carry:

1. **An untested claim about the kit is worth no more than an untested claim about the
   domain.** The original L1 was authored from reading a template; it survived until something
   executable checked it. That is the same failure mode this whole feature exists to correct
   for Principle VII -- and the ledger fell into it on its first row.
2. **A gate finding is evidence, not an obstacle.** HR1 turned a wrong ledger row into a right
   one, and did it on a rule that had **never fired before in this repository**.

What is left after the correction:

- **L2** -- a *found-file provenance* assumption; invisible where sources arrive as downloaded
  files.
- **L5** -- a *Gregorian-only calendar* contract; invisible where the reporting calendar and
  the Gregorian calendar coincide -- and independently corroborated by the retail example
  having hit the same wall and settled it by choosing the calendar year.

Neither is about retail vocabulary. Retail naming was met exactly once (L4) and cost nothing.
On the evidence so far the kit's ANALYTICAL core travelled to a non-retail domain unchanged;
what strained were assumptions about the SHAPE OF A PROJECT (found sources, a Gregorian
reporting calendar) plus discoverability of a mechanism that already existed.

Also worth recording: **the hard stops held.** `no_silver_before_mapping_cleared` and
`never_self_grant_approval` both bound -- Stage 1 and Stage 2 sit blocked on named humans, and
three separate approvals are outstanding (RS1 source confirmation, the mapping gate, and now
the HR1 conformance ruling). That is the correct outcome, not a failure of the walk.

The conclusion is deliberately not written yet -- Slices B, D, E and F have not run and stages
3-7 have not been walked. Task T050 writes it from the complete row set.

---

## Slice C completion -- silver/gold authoring (T022-T026)

Recorded after authoring `warehouse/migrations/0006_create_silver_finance_gl_actuals.sql`,
`0007_create_silver_finance_gl_budget.sql`, and `0008_create_gold_finance_gl_star.sql`, and
running `python -m seshat.cli check` against them.

## L10 -- no leak: silver/gold authoring against the existing conventions and gate

- **location**: `warehouse/migrations/0006_create_silver_finance_gl_actuals.sql`,
  `0007_create_silver_finance_gl_budget.sql`, `0008_create_gold_finance_gl_star.sql`
- **observed_problem**: none. The existing bronze -> silver -> gold conventions observed in
  `0003_create_silver_retail_store_sales.sql` / `0004_create_gold_retail_store_sales_star.sql`
  / `0005_create_silver_demo_sample_orders.sql` (TRIM + NULLIF landing, RC7 typed casts,
  `_sk` surrogate keys with `GENERATED ... IDENTITY`, `-1` unknown members via
  `OVERRIDING SYSTEM VALUE`, FK `COALESCE` to the unknown member except on the marked date
  dimension which fails loud instead, declared-grain `UNIQUE` constraints added after load)
  transferred to a two-fact, multi-grain, cross-star-conformed domain with no modification.
  The only new element -- a second, non-actuals period dimension (`dim_fiscal_period_fgl`)
  keyed on `(fiscal_year, fiscal_quarter)` instead of a date -- needed no new convention,
  only the SAME surrogate-key/unknown-member pattern applied to a different natural key.
- **classification**: `no_leak`
- **existing_rule_or_surface**: the bronze/silver/gold migration convention itself (not a
  single rule); `python -m seshat.cli check`
- **minimal_resolution**: none needed.
- **core_change_required**: false
- **evidence**: `python -m seshat.cli check` exit 0 with only the pre-existing RS1 warning on
  `mappings/retail_store_sales/readiness-status.yaml` (unrelated to this feature, see
  `ledger-baseline.md`); no new warning or error fired against any of the three new migration
  files or the two finance `readiness-status.yaml` records.

## L11 -- documentation_leak: three prose locations still assert the mapping gate is open after the machine-readable approval cleared it

- **location**: `specs/137-finance-gl-genericity-proof/spec.md` "Open owner decisions" (OD-4
  says "STILL OPEN"); `mappings/finance_gl_actuals/assumptions.md` and
  `mappings/finance_gl_budget/assumptions.md` ("What is NOT assumed" -- both still say
  `reviewed_by`/`reviewed_on` read `[PENDING GATE APPROVAL -- OD-4]`);
  `mappings/finance_gl_budget/unresolved-questions.md` header ("Gate status: OPEN... No
  silver.* SQL until a named human clears the gate")
- **observed_problem**: the AUTHORITATIVE, machine-readable surfaces --
  `mappings/finance_gl_actuals/readiness-status.yaml` and `.../finance_gl_budget/
  readiness-status.yaml` `approvals[]` (both carry a `mapping_ready` entry naming
  Ahmed Shaaban, dated 2026-07-30), and both `source-map.yaml` files' `reviewed_by:
  "Ahmed Shaaban (data_owner)"` / `reviewed_on: "2026-07-30"` -- agree the mapping gate is
  CLEARED, corroborated by `mappings/finance_gl_actuals/approval-decision-mapping-gate.md`
  and `docs/quality/conformed-dimension-map.yaml`. Four prose locations committed in the same
  historical window were not updated to match: they still narrate the gate as open. A reader
  who trusted only the prose (rather than `approvals[]`, the actual gate-checked surface)
  would wrongly conclude silver SQL could not yet be authored.
- **classification**: `documentation_leak` -- the mechanism worked (the gate cleared exactly
  once, on a real per-decision transcription, per ledger row L9); only some of its OWN prose
  narration was not swept for consistency afterward. Not a `semantic_leak`: no logic read the
  stale text and nothing downstream trusted it -- this feature's own authoring (T022-T024)
  read `approvals[]` and `source-map.yaml.reviewed_by`, never the stale narration.
- **existing_rule_or_surface**: none enforces prose-vs-approvals consistency; `seshat check`
  validates the YAML shape of `approvals[]` but has no rule comparing a spec's "Open owner
  decisions" prose against the mapping's own recorded approval.
- **minimal_resolution**: for THIS feature, leave `spec.md` as the historical decision record
  it is (Spec-Kit convention: a ratified spec's body is not silently rewritten after the fact
  except via a dated addendum) and instead treat `approvals[]` as authoritative, which this
  implementation session already did. A future refinement could add a lint that flags a
  spec's `STILL OPEN` decision marker when a cited mapping's `approvals[]` already answers it,
  so the drift is caught mechanically rather than by a reader cross-checking by hand.
- **core_change_required**: false to walk (the authoritative surface was unambiguous and
  sufficient); a mechanical drift-check would be a genuine, separately-scoped improvement
- **evidence**: `mappings/finance_gl_actuals/readiness-status.yaml` lines ~89-97 (`approvals[]`);
  `mappings/finance_gl_actuals/source-map.yaml` lines ~35-36 (`reviewed_by`/`reviewed_on`);
  `specs/137-finance-gl-genericity-proof/spec.md` "OD-4 -- STILL OPEN"; both `assumptions.md`
  files' final section; `mappings/finance_gl_budget/unresolved-questions.md` line ~9-10

## Verification evidence for FR-010 and FR-011 (T024a, T024b)

**FR-010** (no disaggregation of `budget_amount` below fiscal-quarter grain): every statement
in `0008_create_gold_finance_gl_star.sql` referencing `budget_amount` is either a column
declaration (`NUMERIC(18,2)`) or a straight passthrough (`SELECT ... s.budget_amount ...`
into `gold.fct_gl_budget_fgl`, one row per silver row). No `/`, no multiplication by a
day-count or month-count fraction, no `generate_series` expansion, no `UNNEST`, and no join
that fans a budget row out to a finer grain than its own silver row. `grep -n
"budget_amount" warehouse/migrations/0008_create_gold_finance_gl_star.sql` returns exactly
the declaration and the passthrough select; nothing else touches the column. **FR-010 holds.**

**FR-011** (`budget_version` is part of the key; no statement overwrites a prior version's
rows): `gold.fct_gl_budget_fgl` carries `budget_version` in its `UNIQUE` grain constraint
(`uq_fct_gl_budget_fgl_grain`, alongside `account_sk`/`department_sk`/`fiscal_period_sk`).
`grep -n "UPDATE\|DELETE\|ON CONFLICT" warehouse/migrations/0008_create_gold_finance_gl_star.sql`
matches only a code comment explaining why no UPSERT is used, not an actual statement --
the migration is `DROP TABLE IF EXISTS` (whole-table rebuild from bronze) followed by one
`INSERT`, never a targeted overwrite of one version's rows while others remain. The
append-only guarantee for a NEW version landing in a future bronze reload is a property of
how bronze is loaded (not exercised here -- no database was opened), so that specific claim
stays `[PENDING LIVE PROFILE]`; the STRUCTURAL guarantee -- that version is physically part
of the grain key so two versions can never collide into one row -- is verified by inspection
here. **FR-011 holds at the schema/statement level; the load-time append-only behaviour is
[PENDING LIVE PROFILE].**

## L12 -- no_leak: a pre-existing test census pinned to the retail migration count needed updating for new committed migrations

- **location**: `tests/unit/dbt/_column_drift_fixtures.py` (`REAL_MIGRATION_SHAPES`);
  `tests/unit/dbt/test_column_drift_ddl.py`
  (`test_committed_migrations_still_yield_exactly_the_six_gold_tables`)
- **observed_problem**: `python -m pytest -m unit -q` failed once, on this test, after
  `0008_create_gold_finance_gl_star.sql` was committed. The test is a "census guard" (#501
  review finding B) that hardcodes the exact set of gold tables + per-table column counts the
  committed migrations are expected to yield, specifically so a parser regression in
  `src/seshat/dbt/column_drift.py` cannot hide behind a false "0 advisories" reading. It was
  written when only `0004_create_gold_retail_store_sales_star.sql` existed and pinned the
  literal count `6`. Adding a second idempotent gold migration with 7 new tables
  (`fct_gl_actuals_fgl`, `fct_gl_budget_fgl`, `dim_account_fgl`, `dim_department_fgl`,
  `dim_cost_center_fgl`, `dim_date_fgl`, `dim_fiscal_period_fgl`) legitimately changes that
  count, and the fixture had no way to know about migrations that did not exist when it was
  authored.
- **classification**: `no_leak` -- this is not a retail-shaped assumption inside the KIT's
  logic (`migration_column_sets` itself parsed all 13 tables correctly on the first run, with
  correct per-table column counts, with zero code changes); it is a TEST FIXTURE that
  enumerates committed state and must be kept current by whoever adds a migration, same as
  any other census/golden-file test. It is recorded here rather than silently fixed, per this
  ledger's own standard, so the sequence (new migration -> test fixture update -> green) is
  visible and auditable rather than assumed.
- **existing_rule_or_surface**: `src/seshat/dbt/column_drift.py` (the kit module; UNCHANGED --
  this obstruction never touched it); `tests/unit/dbt/_column_drift_fixtures.py` (a test
  fixture, not a kit module -- updating it is explicitly permitted by T025's "fix authored
  SQL/docs only" boundary read together with the fact that this file is neither authored SQL
  nor a kit module, but committed test data describing OTHER committed files)
- **minimal_resolution**: added the seven new table-name -> column-count entries to
  `REAL_MIGRATION_SHAPES` and generalized the test's docstring/name from "the six gold tables"
  to "the known gold tables" (`test_committed_migrations_still_yield_exactly_the_known_gold_tables`),
  asserting `len(tables) == len(REAL_MIGRATION_SHAPES)` instead of a hardcoded `6`. No change
  to `src/seshat/dbt/column_drift.py`.
- **core_change_required**: false
- **evidence**: `python -m pytest tests/unit/dbt/test_column_drift_ddl.py -q --no-cov` --
  51 passed after the fixture update (0 before, on the pre-fixture-update run: 1 failed via
  the full `-m unit` run); `python -m pytest -m unit -q --no-cov` afterward: 1 failed (only
  the pre-existing, unrelated `test_cli_identity_version` stale-editable-metadata failure),
  5353 passed, 31 skipped, 502 deselected

## Slice D progress -- metric contracts authored, second approval seam found (T035-T041)

## L13 -- no_leak: the seven metric contracts authored cleanly against the existing template and pattern docs

- **location**: `mappings/finance_gl_actuals/metrics/ActualAmount.yaml`, `ActualYTD.yaml`;
  `mappings/finance_gl_budget/metrics/BudgetAmount.yaml`, `BudgetYTD.yaml`,
  `VarianceAmount.yaml`, `VariancePercent.yaml`, `MissingBudgetFlag.yaml`
- **observed_problem**: none. `templates/metric-contract.yaml`'s field set filled with zero
  new/renamed fields for all seven (FR-013); the two variance contracts followed
  `templates/metric-contract-shape.variance-vs-target.yaml`'s own documented precedent for a
  metric that structurally reads two gold tables (naming the second table in
  `formula_intent`, not forcing a second `binds_to` key -- an open TEMPLATE-CAPABILITY note,
  not a Principle-V judgment, per that shape's own wording); `VariancePercent` cites
  `docs/patterns/target-budget-fact.md` Section 3 verbatim and states the averaged-percentage
  prohibition in its own `formula_intent` (FR-014). OD-1/OD-2/OD-3 transcribed as
  `decision_status: decided` `ambiguities[]` entries, each citing the owner + date + spec.md
  location as evidence -- no ambiguity was invented, no RAG threshold, sign policy, or budget
  version preference was invented (`direction_of_good`/`thresholds`/`action_on_breach` remain
  owner-supplied placeholders on all seven).
- **classification**: `no_leak`
- **existing_rule_or_surface**: `templates/metric-contract.yaml`;
  `templates/metric-contract-shape.variance-vs-target.yaml`;
  `docs/patterns/target-budget-fact.md`
- **minimal_resolution**: none needed.
- **core_change_required**: false
- **evidence**: all seven files parse and load through `src/seshat/metric_contract_inventory.py`
  with zero schema/parse errors (confirmed via `python -m seshat.cli semantic-check
  --include-untracked`, which reaches every file and reports only the expected
  not-owner-approved finding below, never a parse or shape error)

## L14 -- authority_leak: a SECOND, previously-unnamed approval seam sits between the OD-1/OD-2/OD-3 content rulings and an approved metric contract

**Found empirically, not assumed: running the gate is what surfaced this, exactly as L9
predicted a future obstruction would be found -- by executing a check, not by reading a
template.**

- **location**: `templates/metric-contract.yaml` (`owner` field + `readiness.status`);
  `src/seshat/cli/commands/semantic.py` (L3 / `semantic-check`);
  `docs/readiness/semantic-model-ready.md` (cited by the template's own readiness comment)
- **observed_problem**: T040 (OD-1/OD-2/OD-3, ruled by Ahmed Shaaban 2026-07-30) answers the
  BUSINESS QUESTIONS a variance metric raises (sign convention, baseline, allocation policy).
  It does NOT approve any of the seven CONTRACT ARTIFACTS this feature authored -- that is a
  separate, per-contract `metric_owner` sign-off the template's own `readiness.status: pass`
  requires ("REQUIRES an evidence[] entry (owner + date)"). No `metric_owner` has been named
  for finance_gl anywhere in the spec, plan, or tasks. Running `python -m seshat.cli
  semantic-check --include-untracked` (the `--include-untracked` flag was necessary AT THE
  TIME the contracts were still untracked -- the default git-tracked-only discovery silently
  found ZERO of these files and reported a false-clean "no drift (0 findings)", a discovery
  gap distinct from this finding and recorded as its own item, L16; the contracts are now
  committed, so plain `semantic-check` with no flag reaches them) returned `exit 1` with all
  seven contracts flagged: `"metric contract is not owner-approved pass"`. This is the gate's
  own mechanical finding, not the agent's inference. T042 ("author the semantic model TMDL so
  every measure traces to exactly
  one APPROVED contract") and T044 (OD-5, human PBIR authoring) both sit BEHIND this seam --
  the task briefing named OD-4 and OD-5 as the two approval stops, and this is a third that
  the spec's task list does not separately number or name.
- **classification**: `authority_leak` -- this is exactly the class of gap L9 already
  generalized about: the kit correctly REQUIRES a named human approval here (the gate fires,
  fail-closed), but nothing in the SPEC's OWN approval inventory (OD-1..OD-5) named this
  specific seam in advance. A reader following only the spec's "Open owner decisions" section
  would not know to look for it until the gate found it.
- **existing_rule_or_surface**: the metric-contract template's `readiness.status` field and
  the `metric_owner` approval convention it documents; `semantic-check` L3 (mechanically
  enforces it); no rule was added or changed to discover this
- **minimal_resolution**: none attempted -- naming a `metric_owner` is a human decision this
  agent cannot make (Principle V, `never_self_grant_approval`); the contracts stay `blocked`.
  A future refinement to spec-authoring practice (not this feature, and not a kit change)
  could enumerate the "one approval per governance gate" set explicitly in a spec's Open Owner
  Decisions section, the way OD-4 (mapping gate) and OD-5 (PBIR authoring) already are, so a
  metric-contract-owner seam is visible before implementation reaches it rather than found by
  running the gate.
- **core_change_required**: false
- **evidence**: with the contracts now committed, `python -m seshat.cli semantic-check` (no
  flag needed) exit 1, 7 findings, one per contract, each reading `"metric contract is not
  owner-approved pass"`; earlier, while the same files were untracked, the identical command
  returned exit 0 with `"no drift (0 findings)"` (see L16) -- proving that earlier zero-findings
  state was non-discovery, not compliance

## L15 -- no_leak (positive): AL1 and AL2 fired for the first time in this repository's history, on this feature's contracts, and both were correct

- **location**: `src/seshat/rules/assumptions.py` (AL1); `src/seshat/rules/assumption_coherence.py`
  (AL2); observed against `mappings/finance_gl_actuals/metrics/*.yaml` and
  `mappings/finance_gl_budget/metrics/*.yaml`
- **observed_problem**: once the seven metric contracts were committed (`git add`), `python -m
  seshat.cli check` returned `exit 1` with 11 errors: AL2 fired four times (OD-1 on
  `fct_gl_actuals_fgl`; OD-1, OD-2, OD-3 on `fct_gl_budget_fgl`) because this session had
  worded the SAME decided ruling slightly differently across sibling contracts (e.g.
  "PRESENTED" vs "presented", "polarity via direction_of_good" vs "whether higher is better is
  carried by direction_of_good") -- a genuine authoring defect AL2 exists to catch, not a false
  positive. AL1 fired seven times (once per contract) because every contract was
  simultaneously `readiness.status: blocked` (correctly -- no metric_owner) AND carried a
  SETTLED, real `binds_to.gold_table` (`gold.fct_gl_actuals_fgl` / `gold.fct_gl_budget_fgl`,
  both genuinely built by `0008_create_gold_finance_gl_star.sql`) -- which AL1 correctly reads
  as a contradiction: a binding that claims to be wired while the contract's own readiness
  block says a human approval is still open.
- **classification**: `no_leak` -- BOTH rules behaved exactly as designed, fail-closed, on
  their FIRST-EVER exercise in this repository (`src/seshat/rules/assumption_coherence.py`'s
  own docstring: "no committed contract carries a decided `ambiguities[]` entry today"; every
  committed contract before this feature was `status: pass`, so AL1 had nothing to trigger on
  either). This is the same category of finding as L1's correction and HR1 in L1: a
  domain-neutral governance rule, never previously exercised because no prior worked example
  produced the SHAPE of artifact that trips it, worked correctly the first time a non-retail
  domain produced that shape.
- **existing_rule_or_surface**: AL1, AL2 (both unmodified)
- **minimal_resolution**: this feature's own authoring defect, not a kit gap -- fixed by (1)
  canonicalizing the `ruling` text for OD-1/OD-2/OD-3 to one exact string per code, transcribed
  from `spec.md`, byte-identical across every contract that cites it (per-contract commentary
  moved to YAML comments, outside the `ruling` field AL2 compares); (2) replacing
  `binds_to.gold_table`/`columns` with the template's own placeholder shape
  (`gold.<fact_or_dim>` / `<gold_column_a>`) on every `blocked` contract, with a YAML comment
  naming the REAL intended binding and the migration that builds it, per AL1's own named
  remedy ("resolve the assumption or revert binding to a placeholder"). `blocking_reasons[]`
  and `status: blocked` were NOT touched -- the metric_owner seam (L14) stays fully visible.
- **core_change_required**: false
- **evidence**: `python -m seshat.cli check` before the fix: exit 1, 11 errors (4 AL2 + 7 AL1);
  after the fix: exit 0, only the pre-existing RS1 warning. `python -m seshat.cli
  semantic-check` after the fix: exit 1, 7 findings, every one the EXPECTED
  "not owner-approved pass" (L3) with zero AL1/AL2 contamination.

## L16 -- documentation_leak / near-miss: `semantic-check`'s default tracked-files-only discovery silently reported a false-clean result on the untracked contracts, before they were committed

- **location**: `src/seshat/cli/commands/semantic.py` `_semantic_files` (git `ls-files`
  default, `--include-untracked` opt-in)
- **observed_problem**: the seven metric contracts in this feature were authored but not yet
  `git add`ed when `python -m seshat.cli semantic-check` was first run. It printed `"seshat
  semantic-check: no drift (0 findings)"` and exited 0 -- a CLEAN result -- because its
  default discovery reads `git ls-files` (tracked files only) and every new contract was
  untracked. The command's own code comment states the correct principle exactly ("zero
  findings" and "zero inputs" are different states and collapsing them is a fail-open) and
  implements it for the TOTAL-zero-input case (printing `[not_started]` to stderr) -- but that
  safeguard does not fire when SOME inputs are tracked (the pre-existing TMDL/contracts) and
  the NEW ones are merely untracked: the total input count is non-zero, so the zero-input
  branch never triggers, and the untracked new files are silently absent from the count with
  no distinct signal from "everything was checked and passed."
- **classification**: `semantic_leak` (conservative choice per this ledger's own tie-breaking
  rule -- arguably `documentation_leak` since the SAFEGUARD the code already has is sound and
  well-commented, and `--include-untracked` is a genuine, working escape hatch; but the
  DEFAULT behaviour silently under-covers a normal authoring-session state -- new files not
  yet staged -- which is exactly the shape of gap this ledger is built to catch)
- **existing_rule_or_surface**: `_semantic_files` in `src/seshat/cli/commands/semantic.py`;
  the `--include-untracked` flag (already exists; this is a discoverability/default finding,
  not a missing-capability one)
- **minimal_resolution**: none attempted here (FR-031 forbids changing kit code in this
  feature). The agent's own practice going forward in this session was to always pass
  `--include-untracked` when the contracts are not yet committed, and to note in this ledger
  that the plain `semantic-check` exit-0 seen earlier was NOT evidence of compliance. A future
  refinement could print a stderr note whenever untracked candidate files exist under a
  `metrics/` path but were excluded by the default discovery, similar to the existing
  zero-input safeguard's spirit.
- **core_change_required**: false to walk (the escape hatch already exists and was used once
  discovered); a discoverability improvement would still be a genuine, separately-scoped fix
- **evidence**: `python -m seshat.cli semantic-check` (no flag) on the tree WHILE all seven
  contracts were still untracked: `exit 0`, `"no drift (0 findings)"`; `python -m seshat.cli
  semantic-check --include-untracked` on the IDENTICAL, still-untracked tree: `exit 1`, 7
  findings. Same filesystem state, two different verdicts, distinguished only by a flag this
  feature's own task briefing did not mention.
- **status of this specific window**: CLOSED for this feature. The seven contracts are now
  committed (tracked), so the default (no-flag) `semantic-check` reaches them correctly (see
  L14's evidence) and the false-clean window described above no longer applies to THIS tree.
  The underlying default-discovery behaviour itself is unchanged and would recur for any
  future author's untracked, not-yet-staged contract files -- that generic exposure is the
  finding this row records, not a currently-live defect on this branch.

## L17 -- process_note: the seven metric contracts were SPLIT OUT of the landing PR

- **location**: PR #596 (`137-finance-gl-genericity-proof`); the contracts are held on
  branch `137-metric-contracts-held` at commit `b61ec38`.
- **observed_problem**: the seven contracts authored in T035-T041 are correct, but every
  one is `readiness.status: blocked` for want of a named `metric_owner` (L14). CI's
  required `check` job runs `retail semantic-check --require-inputs` as a step, so those
  seven L3 findings make the whole PR unmergeable -- not merely "red by design" as first
  framed. The finding is CORRECT; the contracts genuinely are not owner-approved.
- **classification**: `process_note` -- not a genericity obstruction. The kit behaved
  exactly as designed: an unapproved contract must not pass a gate.
- **minimal_resolution**: land the SQL, ledger and census-guard fixture (all of which pass
  every gate today) and defer the contracts to a follow-up PR opened once a named
  `metric_owner` exists. T035-T041 are un-checked on the landing branch because their
  deliverables are not in it; the authored work is preserved on the held branch, not lost.
  Nothing was silenced, no gate was weakened, and no approval was self-granted.
- **consequence**: L14's `authority_leak` finding stands unchanged -- the `metric_owner`
  seam is a third approval gate that neither the spec's "Open owner decisions" section nor
  the implementation brief named, discovered only because a non-retail domain reached it.

## L18 -- process_note: two reviewer findings on the split commit, both valid

- **location**: PR #596 review (`chatgpt-codex-connector`);
  `mappings/finance_gl_{actuals,budget}/readiness-status.yaml` and
  `specs/137-finance-gl-genericity-proof/tasks.md`.
- **observed_problem (P1)**: `next_action` on both tables named a `metric_owner`
  approval -- Stage 5 work -- while `silver_ready` and `gold_ready` were both
  `not_started`. It routed the next agent past two whole stages. It also cited
  `metrics/*.yaml` paths the split had removed. Compounding this, each
  `silver_ready` block still carried a comment asserting "no silver.* SQL before the
  mapping gate is CLEARED" -- stale, since the gate IS cleared and the SQL is
  authored.
- **observed_problem (P2)**: un-checking T035-T041 was not sufficient. Their notes
  still read `**DONE**: mappings/.../metrics/ActualAmount.yaml`, naming seven files
  no longer in the tree. An unchecked box carrying a DONE claim for a missing
  artifact is worse than either alone: a reviewer cannot reproduce the recorded
  experiment.
- **classification**: `process_note` -- neither is a genericity obstruction. P2 was a
  defect introduced by the split itself, not by the finance domain.
- **minimal_resolution**: `next_action` on both tables now advances the EARLIEST
  incomplete stage (`silver_ready`) and states explicitly that metric-contract work
  is Stage 5 and must not be treated as next while Stages 3-4 are incomplete; the
  stale gate comments now say the hard stop is satisfied but that authoring is not
  entering the stage. T035-T041 notes now state the artifacts were split out, name
  the holding branch, and record that semantic-check finds zero finance contracts in
  this commit.
- **consequence**: a reader of either file can now reproduce exactly what this commit
  does and does not contain. Nothing about L14's `metric_owner` seam changes.

## L19 -- BLOCKING, needs an owner ruling: the two facts share no conformed TIME dimension

- **location**: `warehouse/migrations/0008_create_gold_finance_gl_star.sql`;
  `docs/quality/conformed-dimension-map.yaml`.
- **found by**: PR #596 review (`chatgpt-codex-connector`, P1). Verified against the
  committed SQL and the owner ruling before being recorded.
- **observed_problem**: `fct_gl_actuals_fgl` is keyed to `dim_date_fgl` (daily
  `date_sk`). `fct_gl_budget_fgl` is keyed to `dim_fiscal_period_fgl`
  (`fiscal_period_sk`). **Neither time dimension filters both facts.** Slice the
  required Actual-vs-Budget trend by quarter and one series repeats its unfiltered
  total for every period -- the spec's central deliverable does not work.
- **verification**: `docs/quality/conformed-dimension-map.yaml` carries an owner
  ruling (Ahmed Shaaban, 2026-07-30) for exactly two names: `dim_account_fgl` and
  `dim_department_fgl`. **No time dimension was ever ruled.** FR-009 names
  `dim_date` among the dimensions that MUST be conformed, so this is a real gap, not
  a reviewer misreading.
- **classification**: `genericity_obstruction` -- and a substantive one. The retail
  worked example has a single fact at a single daily grain, so the question "what
  happens when two facts live at different time grains?" never arose. Finance is the
  first domain where it does.
- **minimal_resolution**: **NOT ATTEMPTED -- this is a Principle-V human modelling
  judgment and an agent must not decide it.** `conformed-dimension-map.yaml` says so
  in its own header: a cross-star dimension ruling "is a Principle-V human modelling
  judgment; HR1 never decides it."
  The options, stated without a recommendation being acted on:
  - **(a)** add `fiscal_period_sk` to `fct_gl_actuals_fgl` alongside its daily
    `date_sk`. FR-010 permits aggregating actuals UPWARD to the budget comparison
    grain, so this direction is allowed.
  - **(b)** introduce a shared period bridge between `dim_date_fgl` and
    `dim_fiscal_period_fgl`.
  - **(c)** rule the two time dimensions `distinct` and accept that no cross-fact time
    slice exists -- which would contradict the spec's own required trend visual.
  Option (a) is what the reviewer suggested. Whichever is chosen, it needs a
  `conformed-dimension-map.yaml` entry naming a human and a date, and it may change
  the authored gold SQL.
  **What is NOT an option**: adding a daily `date_sk` to the budget fact. That is
  downward disaggregation of budget, which FR-010 forbids without a named human
  approval.
- **consequence**: this blocks the T042 semantic model and the T044 dashboard page
  independently of the `metric_owner` seam (L14). Two distinct human decisions now
  gate Stage 5+, not one.

### L19b -- the SAME root cause also blocks live validation of the budget table

A second reviewer finding (PR #596, P1, `mappings/finance_gl_budget/readiness-status.yaml`)
turns out to be this same obstruction seen from the validator side, not a separate issue:

`validate_targets.load_targets()` unconditionally requires `gold_star.date_dimension`
(`src/seshat/validate_targets.py:183`). The budget source-map deliberately omits it,
because budget lives at fiscal-period grain and has no date dimension. Verified
empirically -- loading the budget map raises
`ValueError: source-map.yaml: missing required 'date_dimension' in gold_star`.

So with the DB extra and a DSN configured, `retail validate` on `finance_gl_budget`
exits before running a single check, and the table cannot advance through Gold Ready.

The reviewer offered two remedies: record it as a concrete blocker, or add validator
support for a declared fiscal-period target. **The second is out of bounds here** -- it
edits `src/seshat/validate_targets.py`, a kit module, which T025 forbids outright and
which this spec's scope does not cover. So it is recorded as a blocker, folded into
L19 rather than opened as a third decision: whichever way the time-conformance
question is ruled determines whether budget gains a date dimension, gets a shared
period bridge, or needs validator support. One ruling settles both.

## L20 -- FIXED: a derived measure was listed as a silver->gold reconciliation target

- **location**: `mappings/finance_gl_actuals/source-map.yaml`
  (`gold_star.fact.measures`, `additive_money_measures`).
- **found by**: PR #596 review (`chatgpt-codex-connector`, P1). Verified empirically.
- **observed_problem**: `amount` was listed in `gold_star.fact.measures`, so
  `validate_targets.load_targets()` included it in the silver->gold reconciliation and
  `check_reconciliation()` would execute `sum(amount)` against BOTH silver and gold.
  But `amount` is derived -- `(s.debit_amount + s.credit_amount)`, computed only in
  0008's gold insert -- and `0006_create_silver_finance_gl_actuals.sql` has no such
  column. Live validation would have died with an undefined-column error instead of
  completing.
- **classification**: `authoring_defect` -- mine, not a genericity obstruction. The
  retail example has no derived money measure, so the question never arose, but the
  fix required no kit change.
- **minimal_resolution**: removed `amount` from both `measures` and
  `additive_money_measures`, with the reason stated inline. A derived column is not a
  silver->gold reconciliation target; its correctness is proven by the arithmetic, not
  by a sum comparison. The landed `debit_amount` / `credit_amount` remain reconciled.
- **verification**: `load_targets()` on the actuals map now loads and no longer
  targets `amount`.

## L21 -- BLOCKING, needs an owner ruling: the -1 unknown member hides the D1/D2 refusal

- **location**: `warehouse/migrations/0008_create_gold_finance_gl_star.sql` lines
  192-194 and 243-245; `docs/worked-examples/finance-gl-defect-matrix.md` D1/D2.
- **found by**: PR #596 review (`chatgpt-codex-connector`, P1). Verified against both
  the migration and the retail precedent.
- **observed_problem**: the defect matrix requires D1 (row references an absent
  account) and D2 (unknown department) to **`refuse`**, detected by
  `check_orphan_fks` (RC16). But `COALESCE(da.account_sk, -1)` rewrites a FAILED
  natural-key lookup into the valid `-1` member the migration itself inserts. The
  validator then compares gold surrogate FKs against dimension surrogate PKs and
  finds **zero orphans**. The required refusal never fires: the defect matrix would
  report a pass while the defect is undetected.
- **why this is NOT simply my bug**: `COALESCE(..., -1)` is the kit-wide convention,
  used identically in `0004_create_gold_retail_store_sales_star.sql` (lines 132-135)
  and cited in this table's own RC14 rationale. It is declared, not improvised.
- **classification**: `genericity_obstruction`. The convention conflates two
  different failures. Retail's `-1` exists for a legitimately NULL source value (the
  9.65% NULL item, Q4) where collapsing IS correct. Finance D1/D2 is an
  unknown-but-PRESENT natural key -- a reference to an account that does not exist --
  which must refuse. The convention cannot distinguish "no value" from "value that
  resolves to nothing", and neither can the orphan check. Retail never had a case
  where an unresolvable reference had to refuse, so the gap never surfaced.
- **minimal_resolution**: **NOT ATTEMPTED.** Every available fix leaves this spec's
  scope:
  - **(a)** validate the natural-key lookup before coalescing (e.g. refuse when the
    source key is non-null but unmatched) -- changes the kit-wide gold-star
    convention, affecting the retail star too;
  - **(b)** preserve evidence of the unresolved reference in a separate column or
    reject-table so `check_orphan_fks` can see it -- a new convention;
  - **(c)** extend the validator to distinguish sentinel-assigned FKs from genuine
    matches -- edits a kit module, which T025 forbids.
  All three are Principle-V/kit-convention decisions an agent must not make alone.
- **consequence**: D1 and D2 in the defect matrix cannot be honestly marked as
  proven-refusing until this is ruled. They currently read `[PENDING LIVE PROFILE]`,
  so no false claim is committed -- but a live run would report a pass for the wrong
  reason, which is worse than a failure.
