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
