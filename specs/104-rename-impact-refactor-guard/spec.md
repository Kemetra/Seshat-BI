# Feature Specification: Rename/Impact Refactor-Safety Static Rule (HR9)

**Feature Branch**: `104-rename-impact-refactor-guard`

**Created**: 2026-07-04

**Status**: implemented -- artifact `src/seshat/rules/rename_impact_guard.py`

**Status history**: Draft

**Input**: User description: "Gap #15. Rename/impact refactor-safety static rule -- a static
rule that renaming a gold column or a measure leaves no dangling reference across metric
contracts, TMDL, and dashboard blueprints. Extends the SC1/DF1 multi-file-consistency pattern
to the model surface. A rename passes `retail check` today while orphaning references."

## Overview

Seshat BI already has two shipped static reconcile rules that catch a stale REFERENCE inside
prose or docs: **SC1** (spec 050) reconciles a claimed build/planned status against the tracked
file set, and **DF1** (spec 051) reconciles a parked-on dependency edge's cited doc/evidence
against tracked files. Both share one shape: read a set of committed references, resolve each
one against the set of things that actually exist, and fail closed (ERROR) on the first
reference that resolves to nothing. Neither rule looks at the MODEL SURFACE -- a gold column
name, a TMDL measure name -- because neither existed when SC1/DF1 shipped.

Today, nothing plays that role for the model surface. If a gold column is renamed in the
warehouse migration SQL, or a TMDL measure is renamed, `retail check` can still exit 0 while a
metric contract's `binds_to.columns`, another measure's DAX expression, or a dashboard visual
binding map's `semantic_model_field(s)` cell still cites the OLD name. The reference is now
dangling -- it resolves to nothing -- but no existing rule checks that; D1-D11 validate DAX/TMDL
well-formedness, not cross-artifact name agreement, and SF1/HR1 check a different surface
(checklist forks, cross-star dimension conformance) entirely.

This feature defines a NEW static `retail check` rule, reserved id **HR9**, that extends the
SC1/DF1 reconcile pattern to the model surface: it derives the TRUTH SET of currently-existing
gold columns and TMDL measures directly from the committed TMDL, then resolves every reference
to a gold column or measure name found in metric contracts (`binds_to.columns`), TMDL DAX
expressions (measure-to-measure and measure-to-column references), and dashboard visual-binding
maps (`semantic_model_field(s)`) against that truth set. A reference that resolves to nothing
is an orphan -- exactly the dangling state a careless rename leaves behind -- and HR9 fails
closed (ERROR) naming both the orphaned reference and the artifact that carries it.

HR9 is static-only (Principle VIII): it reads committed text and never opens a database, never
runs DAX, never executes a Power BI/PBIP surface. It cannot see a rename EVENT (it has no diff,
no git history, no "before" state) -- it can only see the CURRENT committed tree. What it
detects is the ORPHAN a rename leaves behind: a reference that no longer resolves. It never
decides which of the two mismatched names is correct, never edits a file to fix the mismatch,
and never renames anything itself -- it names the break and stops, the same way SC1/DF1/HR1
name a break and stop.

## Boundary against neighbouring shipped work (read first)

This feature is a genuine EXTENSION of the multi-file-consistency pattern to a surface it does
not yet cover, not a restatement of any shipped or in-flight rule. Five close neighbours must
stay distinct:

- **SC1 stale-marker sweep** (spec 050, `src/retail/rules/status_claims.py`) reconciles a
  hand-curated manifest's claimed build/planned STATUS against the tracked-file set (prose
  claims, not model references). HR9 reuses SC1's reconcile-and-fail-closed CODE PATTERN but
  checks a completely different reference class (gold columns / measure names, not doc-status
  claims) and needs NO hand-curated manifest -- see the manifest-less design point below.
- **DF1 parked-on map** (spec 051, `src/retail/rules/parked_on.py`) reconciles a dependency
  edge's cited doc/anchor/evidence against tracked files. Same reconcile shape, different
  surface (dependency edges, not model identifiers). HR9 does not touch `docs/quality/
  parked-on.yaml` and DF1 does not gain a model-reference check from this feature.
- **HR1 conformed-dimension readiness** (spec 087, reserved id HR1, in flight) checks that
  dimensions DECLARED conformed across multiple gold stars actually agree on grain/key/type --
  a cross-STAR structural-agreement question decided by human declaration. HR9 checks a
  different question entirely: whether a reference to a column/measure NAME still resolves at
  all, within a single table's model surface. HR1 does not detect a rename orphan; HR9 does not
  judge cross-star conformance. The two rules never fire on the same finding.
- **SF1 cross-layer checklist fork detector** (spec 086, in flight per recent history) reconciles
  a shared checklist's OWN COPIES for drift against each other -- a fork-detection surface, not a
  model-reference surface. HR9 is named alongside SF1/DF1 in the collision-avoidance ledger as a
  sibling reconcile rule, not a variant of SF1's own-copy comparison.
- **Spec 099 cross-table column-level lineage/impact** (in flight, Product Module, no rule id)
  is a READ-ONLY, DESCRIPTIVE generator: given a starting column or contract, it shows the
  reachable downstream chain, treats a missing hop as a normal GAP (not an error), and
  explicitly defers name-similarity/fuzzy matching to an UNRESOLVED/candidate link pending a
  human ruling (its own FR-010). HR9 is the opposite shape: a FAIL-CLOSED, PRESCRIPTIVE guard.
  It does no fuzzy matching and needs none -- it only resolves references that are already
  EXPLICIT, EXACT identifiers in committed text (a DAX `[MeasureName]` token, a
  `binds_to.columns` entry, a `semantic_model_field(s)` cell), and any such reference that does
  not resolve to the current truth set is an ERROR, not a gap. The two compose but do not
  overlap: 099 can show a reader what is reachable from a column today; HR9 guarantees that
  what IS referenced still exists. Neither reads or edits the other's output.

This feature adds a NEW `retail check` rule (id **HR9**) -- unlike the F024/F028/F035/099
Product Modules, it is a governance rule, not a skill+template. It claims NO shared-schema
addition and introduces NO new manifest YAML: HR9 derives its truth set and its reference set
directly from already-committed model artifacts (TMDL, metric contracts, binding maps), the
same "read committed text, no new schema" posture DF1 and HR1 already use for their own inputs.
The reserved rule id **HR9** is allocated under the collision-avoidance ledger so no other
in-flight feature claims it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A renamed gold column orphans a metric contract reference (Priority: P1)

A gold migration is edited so that `gold.fct_sales_rss.total_spent` is renamed to
`gold.fct_sales_rss.total_amount`, but the metric contract `TotalSales.yaml` (`binds_to.columns:
["total_spent"]`) and the TMDL measure's DAX expression are left untouched. Today `retail check`
exits 0 -- nothing checks that `binds_to.columns` still names a real gold column. With HR9,
running `retail check` fails closed, naming the metric contract file, the stale column name, and
the table whose current committed column set no longer contains it.

**Why this priority**: This is the exact gap the feature exists to close -- a rename that
silently orphans a Layer-6 (define-layer) reference. Without this, the feature delivers nothing.

**Independent Test**: Rename a column in a committed TMDL table (or its migration SQL/source of
truth) without updating a metric contract's `binds_to.columns` that names the old value; running
`retail check` produces exactly one HR9 finding naming the contract file and the orphaned column
name, and the finding is present in `blocking_reasons[]` for the affected table's Semantic Model
Ready status.

**Acceptance Scenarios**:

1. **Given** a metric contract's `binds_to.columns` names a column that does not appear among
   the committed TMDL table's current `column` entries, **When** `retail check` runs, **Then**
   it fails closed with an HR9 finding naming the contract file, the stale column name, and the
   TMDL table it was checked against.
2. **Given** the metric contract is corrected to name the current column (or the TMDL is
   corrected back), **When** `retail check` runs again, **Then** no HR9 finding is emitted for
   that reference.
3. **Given** an HR9 finding exists for a table's committed artifacts, **When** that table's
   Semantic Model Ready readiness status is read, **Then** HR9 appears in `blocking_reasons[]`
   the same way a D1-D11 or C1 finding does.

---

### User Story 2 - A renamed measure orphans a DAX reference and a dashboard binding (Priority: P1)

A TMDL measure named `TotalSales` is renamed to `TotalRevenue` inside the same table's TMDL
file, but a second measure's DAX expression still references `[TotalSales]`
(`AvgTransactionValue = DIVIDE([TotalSales], ...)`), and the visual-contract binding map's
`semantic_model_field(s)` column for several visuals still cites `[TotalSales]`. HR9 must catch
BOTH kinds of orphan: the measure-to-measure DAX reference and the binding-map reference, each
as its own finding naming the artifact and the stale measure name.

**Why this priority**: A measure rename is the highest-risk case named in the gap description
(measures are reused inside other measures' DAX far more often than columns are reused across
contracts), and it is the case most likely to pass `retail check` silently today, since D1-D11
validate DAX syntax, not cross-reference name agreement.

**Independent Test**: Rename a TMDL measure without updating a second measure's DAX expression
that references it by name, and without updating the binding map; running `retail check`
produces one HR9 finding for the DAX cross-reference and one HR9 finding for the binding-map
reference, each naming the stale measure name and the citing artifact.

**Acceptance Scenarios**:

1. **Given** a TMDL table's measure DAX expression references another measure by
   `[MeasureName]` and no measure with that name currently exists in the same model, **When**
   `retail check` runs, **Then** it fails closed with an HR9 finding naming the referencing
   measure, the stale `[MeasureName]` token, and the TMDL file.
2. **Given** a committed dashboard visual-contract binding map's `semantic_model_field(s)` cell
   names a measure or a `dim[column]` pair that does not resolve against the current committed
   model, **When** `retail check` runs, **Then** it fails closed with an HR9 finding naming the
   binding-map file, the stale reference, and the visual row it appears on.
3. **Given** both the DAX expression and the binding map are corrected to the new measure name,
   **When** `retail check` runs again, **Then** no HR9 finding is emitted for either reference.

---

### User Story 3 - A table with no model surface yet is a clean no-op (Priority: P2)

A newly onboarded table has a filled `source-map.yaml` and metric contract drafts, but has not
yet reached Semantic Model Ready -- no TMDL exists for it yet. HR9 must not fabricate a finding
against a model surface that does not exist; it engages only once a TMDL model surface is
committed for that table.

**Why this priority**: This is the same "no premature engagement" discipline HR1 already
establishes for tables with zero or one star; it prevents HR9 from blocking early-stage tables
on a check that is meaningless before a model exists, but it is not the feature's core value
(P1s are), so it is P2.

**Independent Test**: Run `retail check` against a table with metric contracts but no committed
TMDL table file; confirm zero HR9 findings are emitted for that table.

**Acceptance Scenarios**:

1. **Given** a table with metric contracts but no committed TMDL file under
   `powerbi/*.SemanticModel/definition/tables/`, **When** `retail check` runs, **Then** HR9
   emits no finding for that table (no model surface to check against).
2. **Given** the table later gains a committed TMDL file, **When** `retail check` runs again,
   **Then** HR9 begins checking that table's contract/DAX/binding-map references against the
   newly-existing TMDL truth set.

---

### Edge Cases

- What happens when a metric contract has NOT yet been approved (`readiness.status` is not
  `pass`)? HR9 still checks it -- referential integrity is independent of approval state; an
  unapproved contract with a dangling column reference is still reported, because the contract
  will be wrong the moment it IS approved if the orphan is not caught now.
- What happens when the same measure name is referenced with different letter casing (e.g. a
  DAX expression writes `[totalsales]` where the committed measure is named `TotalSales`)?
  RESOLVED (see Clarifications, Q-CASE-SENSITIVITY): HR9 resolves column and measure name
  references CASE-INSENSITIVELY, mirroring the Power BI engine's own case-insensitive name
  resolution -- `[totalsales]` matches a committed `TotalSales` measure and is NOT an orphan.
  A reference is only an orphan when it does not resolve under case-insensitive comparison.
- What happens when a column/measure reference is scoped to a specific table (for example
  `'gold fct_sales_rss'[total_spent]`) versus an unqualified reference (`[TotalSales]`)? HR9
  MUST resolve a table-qualified reference only within that table's own committed columns/
  measures (a same-named column in a different table is not a match). RESOLVED (see
  Clarifications, Q-MEASURE-SCOPE): an unqualified measure reference MUST resolve within the
  UNION of measures declared across every TMDL table file that shares the same
  `*.SemanticModel/definition/` model folder as the referencing file, not within that one file
  alone -- a Power BI model folder is commonly multi-file (fact table + conformed dimensions),
  and measures are model-scoped, not file-scoped or table-scoped -- see FR-006.
- What happens when a TMDL measure currently exists in the model but is not (yet) referenced by
  any metric contract? HR9 does not check that case -- that is Semantic Model Ready's own
  "measure with no corresponding metric contract" blocking reason, already covered by existing
  checks. HR9 only checks the REVERSE direction: a contract/DAX/binding-map reference that names
  something the model no longer has.
- What happens when two different TMDL model folders (two different tables' `*.SemanticModel/`)
  each define a measure with the same name? HR9 resolves each reference against the model folder
  the referencing artifact itself belongs to (a table's own metric contracts and binding map
  reference that table's own model), never against a different table's model folder.
- What happens when a dashboard binding-map cell references a dimension column
  (`dim_product_rss[category]`) and the dimension's OWN TMDL file (not the fact table's) is the
  one that renamed the column? HR9 MUST resolve a `dim[column]` reference against the named
  dimension's own committed TMDL columns, not just the fact table's.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A new static `retail check` rule MUST be added, registered under the reserved id
  **HR9**, that runs over every committed table with at least one TMDL model file.
- **FR-002**: HR9 MUST derive its TRUTH SET -- the currently-existing gold column names and
  measure names -- directly from the committed TMDL under
  `powerbi/*.SemanticModel/definition/tables/*.tmdl` for the relevant model. It MUST NOT read
  this truth set from any hand-curated manifest; no new manifest YAML is introduced for this
  purpose (the truth set is derived, not declared).
- **FR-003**: HR9 MUST resolve, against that truth set, every reference to a gold column name
  found in a metric contract's `binds_to.columns` (`mappings/<table>/metrics/*.yaml`). A
  reference that does not resolve to a column currently present in the cited gold table's TMDL
  MUST produce one finding naming the contract file and the stale column name.
- **FR-004**: HR9 MUST resolve, against that truth set, every measure-to-measure and
  measure-to-column reference inside a TMDL measure's own DAX expression (for example
  `[OtherMeasure]` or `'table'[column]` tokens). A reference that does not resolve MUST produce
  one finding naming the referencing measure, the TMDL file, and the stale token.
- **FR-005**: HR9 MUST resolve, against that truth set, every measure or `dim[column]` reference
  found in a committed dashboard visual-contract binding map's `semantic_model_field(s)` column
  (`mappings/<table>/design/visual-contract-binding-map.md` or equivalent committed binding
  artifact). A reference that does not resolve MUST produce one finding naming the binding-map
  file, the visual row, and the stale reference. Per Clarifications Q-BINDING-CELL-PARSE, HR9
  extracts only the bracket-delimited explicit tokens from a cell (a `[Measure]` token or a
  `dim[column]` token) and ignores surrounding prose/qualifiers (for example "by", grouping
  labels, or a `(Top N)`/`(month)` annotation) -- it performs no fuzzy or prose matching, only
  exact-token resolution, consistent with the explicit-identifiers-only posture already
  established against Spec 099 in the Boundary section above.
- **FR-006**: HR9 MUST resolve a table-qualified reference (`'table'[column]`) only within the
  named table's own committed columns, and MUST resolve an unqualified measure reference
  (`[Measure]`) within the UNION of measures declared across every TMDL table file that shares
  the same `*.SemanticModel/definition/` model folder as the referencing file (per
  Clarifications Q-MEASURE-SCOPE), so a same-named identifier in an unrelated table or an
  unrelated model folder is never treated as a false match, and a genuine cross-table,
  same-model-folder measure reference is never treated as a false orphan.
- **FR-007**: HR9 MUST engage only for a table that has at least one committed TMDL file. A
  table with metric contracts but no TMDL model surface yet MUST produce zero HR9 findings (no
  premature engagement, mirroring the HR1 zero/one-star no-op precedent).
- **FR-008**: HR9 MUST check a metric contract's references regardless of that contract's own
  `readiness.status` (approved or not) -- referential integrity is independent of and prior to
  approval state.
- **FR-009**: HR9 MUST NOT decide which of two mismatched names is the "correct" one, MUST NOT
  edit, rename, or auto-correct any file, and MUST NOT suggest a specific replacement name. It
  names the orphaned reference and the artifact that carries it, and stops (Principle V/scope
  guard: no auto-rename).
- **FR-010**: HR9 MUST NOT execute a DAX expression, connect to a live database, or open a live
  Power BI/PBIP surface (Principle VIII); all resolution is against committed TMDL/YAML/Markdown
  text.
- **FR-011**: When HR9 produces one or more findings for a table's committed model-surface
  artifacts, the Semantic Model Ready (and, where the orphan is in a binding-map reference,
  Dashboard Ready) readiness computation MUST surface HR9's finding(s) in that table's
  `blocking_reasons[]`, the same way an existing D1-D11/C1/HR6 finding is already surfaced there.
- **FR-012**: HR9 MUST NOT emit or require any numeric confidence/health/maturity/completeness
  score (hard rule #9); a table either has zero HR9 findings (clean) or one-or-more (blocked),
  same binary posture as the other reconcile rules.
- **FR-013**: HR9 and its own rule source MUST NOT inline a worked-example (C086/pharmacy/
  retail_store_sales) domain specific -- table names, column names, and measure names are all
  read generically from whatever committed TMDL/YAML/Markdown the rule is pointed at; no
  worked-example name is hardcoded into the HR9 rule's own source.
- **FR-014**: `docs/readiness/semantic-model-ready.md` (and `docs/readiness/dashboard-ready.md`
  where the orphan is a binding-map reference) MUST be updated to list HR9 among the checks that
  gate that stage's blocking reasons, mirroring the HR6 FR-017 precedent of keeping the gate
  doc's "Blocking reasons" table and the rule's own registration in agreement.
- **FR-015**: HR9's registration MUST keep the rule-count lockstep intact: `src/retail/rules/
  __init__.py`'s import/`__all__` tuple gains `HR9`, `docs/rules/rules-manifest.json` is
  regenerated to include it, and `tests/unit/test_rules_wiring.py`'s expected-rule-id set gains
  `"HR9"` -- the count itself is never hardcoded as a bare literal disconnected from the live
  registry (per the wiring-meta-gate / rule-count-reconciler precedent).
- **FR-016**: Whether a clean HR9 run requires its own named-human approval seam beyond the
  existing Semantic Model Ready / Dashboard Ready owner sign-offs, or is purely mechanical (a
  clean run IS the check, no separate approval slot), MUST NOT be decided by the agent alone.
  RECORDED PENDING DEFAULT the owner may ratify: MECHANICAL -- HR9 is a static objective
  referential-integrity check like SC1/DF1/HR1; no new approval seam is invented until an owner
  rules one in. Until the owner rules, HR9 emits findings only and records no new approval
  requirement.

### Key Entities

- **HR9 finding**: a static `retail check` finding raised when a committed reference to a gold
  column or measure name does not resolve against the current committed TMDL truth set for the
  relevant table/model.
- **Truth set**: the currently-existing gold column names and TMDL measure names for one table's
  model, derived by reading that table's committed TMDL file(s) -- never a hand-curated manifest.
- **Reference set**: every gold-column or measure-name reference found in a metric contract's
  `binds_to.columns`, a TMDL measure's own DAX expression, or a dashboard visual-contract
  binding map's `semantic_model_field(s)` column.
- **Orphaned reference**: a member of the reference set that does not resolve against the truth
  set -- the dangling state a rename leaves behind when only one side of the rename is updated.
- **Semantic Model Ready / Dashboard Ready blocking reason (HR9-sourced)**: an entry in a
  table's `blocking_reasons[]` that traces to a live HR9 finding; cleared only when the
  underlying reference is corrected (either side) and HR9 re-runs clean.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A metric contract whose `binds_to.columns` names a gold column absent from the
  cited table's current committed TMDL produces an HR9 finding when `retail check` runs.
- **SC-002**: A TMDL measure's DAX expression that references another measure or a
  table-qualified column that no longer exists in the same model produces an HR9 finding.
- **SC-003**: A dashboard visual-contract binding map's `semantic_model_field(s)` cell that
  references a measure or `dim[column]` absent from the current committed model produces an HR9
  finding.
- **SC-004**: 0 HR9 findings, or the HR9 rule's own source, contain a worked-example
  (C086/pharmacy/retail_store_sales) domain specific hardcoded into the rule's logic.
- **SC-005**: 0 HR9 findings are produced for a table that has metric contracts but no committed
  TMDL model file (no premature engagement).
- **SC-006**: 0 HR9 runs write to, rename, or modify any committed artifact -- HR9 is
  verifiably read-only; it emits findings only.
- **SC-007**: `docs/readiness/semantic-model-ready.md` and (where applicable)
  `docs/readiness/dashboard-ready.md` "Blocking reasons" tables list HR9, so a reader of the gate
  doc and a reader of `blocking_reasons[]` see the same vocabulary.
- **SC-008**: The wiring-meta-gate and rule-count-reconciler checks stay green after HR9 lands
  (the registered rule set contains `HR9`; the manifest and the expected-id test both reflect the
  new, live count rather than a stale or hand-edited number).

## Assumptions

- The committed TMDL under `powerbi/*.SemanticModel/definition/tables/*.tmdl` is the
  authoritative, static source of truth for "does this gold column or measure currently exist"
  -- HR9 reads it rather than re-deriving column/measure existence from migration SQL or a live
  Power BI connection.
- `mappings/<table>/metrics/*.yaml` (`binds_to.columns`) and a committed dashboard
  visual-contract binding map (for example `mappings/<table>/design/
  visual-contract-binding-map.md`) are the two non-TMDL artifact families whose references HR9
  resolves against the TMDL truth set; both already exist as committed, generic artifact shapes
  from shipped features (F009 metric-contract store, the dashboard-design skill's binding map).
- HR9 is manifest-less by design: unlike SC1/DF1 (which reconcile a hand-curated manifest against
  tracked files), HR9's truth set and reference set are both derived directly from already-
  committed model artifacts, so no new manifest can itself rot or drift out of sync with the
  model it describes.
- This feature adds a rule, not a Product Module: no skill, no template, no output artifact
  beyond the `retail check` finding stream itself (unlike F028/F035/099's authored packs).
- Live cross-check of a resolved reference against an actual running Power BI model (confirming
  the TMDL's own claims are faithfully published) is OUT OF SCOPE for this feature and remains
  deferred to the Power BI execution adapter (F016) and Principle VIII's static-first/live-
  deferred split.
- Auto-fixing an orphaned reference (renaming the stale side to match, or vice versa) is
  explicitly OUT OF SCOPE (scope guard: no auto-rename); a human decides and edits the correct
  file, and HR9 simply re-runs clean once they do.

## Clarifications

<!-- Principle-V carve-out questions are recorded under their own subsection for a human
     ruling; the workflow is forbidden to answer these. Non-Principle-V ambiguities resolved
     with reasonable constitution-safe defaults (Principle VI) are recorded under the dated
     session subsection. -->

### Session 2026-07-04

Non-Principle-V ambiguities resolved against the constitution, the SC1/DF1/HR1 reconcile
precedent, and the committed filled instances (`retail_store_sales` metric contracts, TMDL, and
visual-contract binding map). One further question (Q-APPROVAL-SEAM) is a genuine Principle-V
who-approves call and is NOT resolved here -- it stays OPEN for an owner ruling.

- **Q-CASE-SENSITIVITY (Edge Cases / new Edge Cases bullet) -- Default adopted.** Q: Should
  HR9 resolve a column/measure name reference case-insensitively (mirroring the Power BI
  engine's own case-insensitive name resolution), or fail closed on any casing mismatch as a
  stricter hygiene rule? A: CASE-INSENSITIVE resolution -- `[totalsales]` matches a committed
  `TotalSales` measure and is not treated as an orphan. Reasoning: HR9's contract is "a
  reference resolves to nothing" (the dangling state a rename leaves behind); the Power BI
  engine itself resolves a case-variant token successfully, so flagging it would be a false
  positive on a fail-closed rule -- it would block a reference that actually works, which is
  scope creep past "orphan" into a separate hygiene concern the spec does not ask for.
  "Fail closed" governs what HR9 does ON a genuine orphan, not how strictly it resolves a name
  in the first place. Reversible: easy (a stricter mode can be added later without breaking any
  clean run). Touches: Edge Cases bullet (now resolved inline), FR-003, FR-004, FR-005 (all three
  resolution paths use the same case-insensitive comparison).
- **Q-BINDING-CELL-PARSE (FR-005) -- Default adopted.** Q: A binding-map
  `semantic_model_field(s)` cell is free-text mixing an explicit token with prose and
  qualifiers (for example `` `[TotalSales]` by `dim_date_rss[full_date]` (month) `` or a
  `(Top N)` annotation on `` `dim_customer_rss[customer_id]` ``) -- FR-005 says "resolve every
  reference" but not how to extract one from a mixed cell. A: HR9 extracts ONLY the
  bracket-delimited explicit tokens (`[Measure]` and `dim[column]` forms) from each cell and
  ignores surrounding prose, grouping words ("by"), and parenthetical qualifiers
  (`(Top N)`, `(month)`) -- no fuzzy or prose matching is attempted. Reasoning: this mirrors the
  spec's own explicit-exact-identifiers-only posture already drawn against Spec 099 in the
  Boundary section (no fuzzy matching, ever); a prose-parsing heuristic would introduce exactly
  the kind of guesswork HR9 is designed to avoid. Reversible: easy. Touches: FR-005.
- **Q-MEASURE-SCOPE (FR-006, Edge Cases) -- Default adopted.** Q: FR-006 said an unqualified
  `[Measure]` reference resolves "within the same TMDL model FILE the reference appears in," but
  the spec's own dimension edge case (a `dim_product_rss[category]` reference resolved against
  the dimension's OWN TMDL file, separate from the fact table's) establishes that a
  `*.SemanticModel/definition/` model folder is normally MULTI-FILE (a fact table's `.tmdl` plus
  each conformed dimension's own `.tmdl`). Under a literal "same file" reading, a measure
  declared in `dim_product_rss.tmdl` that is legitimately referenced by a measure's DAX in
  `fct_sales_rss.tmdl` -- both inside the same model folder -- would resolve to nothing and HR9
  would raise a FALSE orphan, the exact false-positive class Q-CASE-SENSITIVITY was already
  adopted to avoid. A: HR9 resolves an unqualified measure reference against the UNION of
  measures declared across every TMDL table file sharing the same `*.SemanticModel/definition/`
  model folder as the referencing file -- FOLDER scope, not file scope. Reasoning: this matches
  the Power BI engine's actual behavior (a measure is visible model-wide, regardless of which
  table file declares it) and is the same folder-level truth-set union the spec's own dimension
  edge case already requires for `dim[column]` resolution -- "model-scoped, not table-scoped"
  only holds together if scope is read as the whole model folder, not one file within it. This
  is a Principle-VI mechanical default (matches documented, externally-verifiable Power BI
  semantics), not a Principle-V judgment call, and is fully reversible. Touches: FR-006, the
  Edge Cases bullet on table-qualified vs. unqualified references (now resolved inline).
- **Q-APPROVAL-SEAM (FR-016) -- OPEN, owner ruling required (Principle V).** Q: Does a clean
  HR9 run need its own named-human approval seam beyond the existing Semantic Model Ready /
  Dashboard Ready sign-offs, or is a clean run purely mechanical (the check itself, no separate
  approval slot)? This is a who-approves / approval-model question -- Principle V territory,
  not a mechanics default the workflow may invent. FR-016 already carries a RECORDED PENDING
  DEFAULT (MECHANICAL, no new approval seam) that the spec author flagged as ratifiable by an
  owner but did not self-grant; that pending-default framing is preserved AS PENDING, not
  promoted to an adopted default, by this clarification pass. HR9 emits findings only under the
  pending default until an owner rules; the workflow does not decide this on its own authority.
