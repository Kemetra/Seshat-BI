---
name: cross-table-lineage
description: >-
  Generate ONE column-level or metric-level lineage/impact artifact from
  already-committed artifacts in the Seshat BI repo: source-map entry ->
  silver/gold migration SQL -> metric contract -> TMDL measure -> dashboard
  visual binding. Use when someone asks to "trace this column's downstream
  reach", "show what depends on this column/KPI", "generate the lineage/
  impact artifact for <schema.table.column>", or "turn the Net-Sales trace
  into a generated artifact for <Metric>". This is a Product Module,
  artifact-writing: it READS committed source-map/migration-SQL/metric-
  contract/TMDL/binding-map text only, cites every hop it asserts to its exact
  committed path, tiers each hop `proven` / `unresolved` / `gap`, and writes
  ONE derived lineage file -- then STOPS. It NEVER connects to a database,
  executes SQL, runs DAX, opens a live Power BI/PBIP surface, invents a
  lineage edge no committed artifact records, moves a readiness stage, grants
  an approval, or emits a blast-radius score, completeness count, or
  confidence/health/maturity value. Generic across any table/column/metric
  (no C086/retail_store_sales specifics baked in).
---

# cross-table-lineage

- **Roadmap feature:** F039 (PROPOSED at plan time; not yet a
  `docs/roadmap/roadmap.md` ledger row -- see "See also" below).
  **On-disk spec:** `specs/099-cross-table-lineage-impact/`.
- **Authority category:** Product Module / `artifact-writing`
  (the F024 enumerated declaration -- see `docs/architecture/product-modules.md`).

Seshat BI can already answer "does this ONE source drift from its own
profile" (F014) and "what does this ONE KPI derive from, conceptually,
inside the contract layer" (spec 044). Neither answers the question a table
owner actually asks the moment a column changes: if this column changes shape
or disappears, which migrations, metric contracts, TMDL measures, and
dashboard visuals sit downstream of it, and how far does the chain reach
before it runs out of committed evidence? Today that question is answered by
hand -- `docs/demo/net-sales-end-to-end-readiness-trace.md` proves it can be
done for exactly one KPI, on paper, by a human reading five artifact families
in sequence. This skill GENERALIZES that trace's shape (evidence tiers,
hop-by-hop citation) into a regeneratable artifact for any column or metric
contract. It derives evidence only; it never fabricates a link, never scores
impact, and never decides what must be re-reviewed.

## Boundary against neighbouring shipped work (read first)

- **Spec 044 KPI Derivation-Lineage Contract** (`specs/044-kpi-derivation-
  lineage/`, ratified, no runtime code) authors a `Derives from` PROSE section
  inside a metric contract describing METRIC-TO-METRIC conceptual derivation
  (e.g. Net Sales derives from Gross Sales and Discount Amount) in the
  DEFINE/reasoning layer. This skill does not touch contract prose and does
  not declare or transcribe a metric-to-metric edge; it derives a PHYSICAL,
  cross-ARTIFACT chain (column -> SQL -> contract -> measure -> visual) from
  structural references already present in committed YAML/SQL/TMDL/binding
  files, generated as an artifact, never authored as prose. A 044 `Derives
  from` edge is a citable input at the metric-contract hop when a chain
  happens to pass through a derived KPI; this skill never edits, re-derives,
  or second-guesses it.
- **F014 Source Drift Detector** (spec 015, shipped) DETECTS that one
  source's shape or semantics drifted from its own recorded profile. This
  skill does not detect drift and runs no comparison against a baseline
  profile; it is the DOWNSTREAM-SCOPING half of the same idea -- given a
  column, it shows what sits downstream so a reviewer knows what to re-check
  after F014 (or a human) flags something. It enables F014's aftermath; it
  does not re-implement F014's comparison logic.
- **F012 Data Quality Control Room** (spec 013, shipped) is also a
  cross-table, read-only aggregator, but it rolls up DATA-QUALITY findings
  across tables. This skill aggregates LINEAGE EDGES, a different evidence
  category; it does not read Control Room's findings and Control Room gains
  no lineage view from this skill.
- **The Net-Sales end-to-end readiness trace**
  (`docs/demo/net-sales-end-to-end-readiness-trace.md`, shipped) is the
  single hand-authored proof for exactly one KPI. This skill generalizes that
  trace's SHAPE into a regeneratable template for any column or metric
  contract; it supersedes nothing and never retro-edits that file.
- **OpenLineage** was evaluated and DEFERRED (`docs/decisions/0013-bi-tool-
  adapter-shortlist.md`: "emitter, not a gated reader; external-service
  boundary; duplicates F014"). This skill is not a revival: it is a static
  reader over already-committed repository text (Principle VIII), never a
  running emitter, never a client of an external lineage backend.

This module adds NO new readiness stage and NO new `retail check` rule -- it
composes evidence other tools already recorded (the F024 Product Module
boundary).

## Authority declaration (F024) -- the filled module contract

This module declares EXACTLY ONE of the five F024 authority categories.
Quoted verbatim from `docs/architecture/product-modules.md`: a **Product
Module** is "a focused tool that consumes Core Authority and presents,
summarizes, or derives from it. A module MUST declare exactly one capability
level: `read-only` | `artifact-writing` | `execution-capable`. It never
creates truth." This module's capability level is **`artifact-writing`**: it
derives one committed lineage artifact per run from committed evidence, and
-- per the matrix -- MAY write derived evidence but MUST NOT execute.

The filled `templates/module-contract.md` declaration follows.

---

### Module Contract -- Cross-Table Lineage

- **Authority category:** Product Module
- **Capability level:** `artifact-writing`  *(exactly one)*
- **Product layer:** `6`  *(the functional axis -- see docs/roadmap/roadmap.md; spans Mapping through Dashboard, the same cross-cutting axis F028's evidence pack and F035's approval pack occupy)*
- **Roadmap feature:** `F039` (proposed)  **On-disk spec:** `specs/099-cross-table-lineage-impact/`
- **Owner:** the reader who requests the trace (analyst / metric owner / reviewer); no approval seam of its own
- **Status:** Authored (docs/skill/template; no runtime code -- the agent is the runtime)

#### What it does (one line)

> Composes the committed forward chain (source-map -> migration SQL -> metric
> contract -> TMDL measure -> dashboard visual binding) for ONE starting
> column or metric contract into one ordered, cited lineage artifact, tiering
> each hop proven/unresolved/gap, inventing nothing.

#### Core Authority it READS

It reads; it never writes these.

- `mappings/<table>/source-map.yaml` -- the committed column entries a
  column-rooted run resolves its starting point against (hop 1).
- `warehouse/migrations/*.sql` -- the silver/gold migration SQL a resolved
  column is traced into (hop 2).
- `mappings/<table>/metrics/*.yaml` -- the metric contracts that consume a
  gold column, or that anchor a metric-rooted run (hop 3).
- `powerbi/*.SemanticModel/definition/tables/*.tmdl` -- the committed TMDL
  measures that reference a metric contract (hop 4).
- `templates/visual-contract-binding-map.md` (+ any filled per-subject-area
  copy the dashboard-design skill has produced) -- the dashboard visual-to-
  contract binding, when one exists (hop 5).

#### Derived evidence it WRITES

Composed FROM committed evidence; never a new approval, metric definition, or
stage change.

- `mappings/<table>/lineage-column-<column>.md` (column-rooted starting
  point) OR `mappings/<table>/lineage-metric-<Metric>.md` (metric-rooted
  starting point) -- one filled copy of `templates/lineage-trace.md` per run.
  This is the ONLY file the module writes.

#### Approved step it EXECUTES

- none (capability is `artifact-writing`, not `execution-capable`; it
  composes and STOPS, touching no DB and publishing nothing).

#### Forbidden operations (the matrix says NO)

These hold for EVERY Product Module regardless of capability level:

- MUST NOT create truth: no defining/approving business meaning (metric,
  mapping, rollup, segment, grain, PII ruling).
- MUST NOT grant approval or move a readiness stage to `pass` (named-human /
  Core Authority only).
- MUST NOT connect to a DB or external service, read a live Power BI/PBIP
  surface, or invoke a deferred execution adapter (F016) or spec-only runtime
  (F031-F033).
- MUST NOT write back to any artifact this module reads (source-map,
  migration SQL, metric contract, TMDL, binding map).
- MUST NOT emit a numeric / maturity / confidence score (hard rule #9) or any
  completeness / "N artifacts affected" count.
- MUST NOT apply a verb of obligation ("must", "should", "needs to",
  "requires re-review") to any downstream item.

#### How it handles a missing input

When a required Core Authority input is absent, unfilled, a blank template,
or unreadable, the module SURFACES it as a GAP (or, for the starting point
itself, a top-level BLOCKER) naming the missing/unreadable path and stops
treating that source as content -- it never fabricates the input or proceeds
past the missing hop (Principle V; stop-and-ask).

---

## The input contract (committed-only)

The trace composes EXACTLY these committed sources -- no live DB, no PBIP
model, no Power BI execution adapter (F016), no spec-only runtime
(F031-F033), no network. "Committed" means the current on-disk working-tree
content of these tracked files, not a specific git ref -- whatever a reviewer
would see by opening the file right now, matching how `retail check` and the
other read-only skills in this repo already read state.

1. `mappings/<table>/source-map.yaml` -- hop 1.
2. `warehouse/migrations/*.sql` -- hop 2.
3. `mappings/<table>/metrics/*.yaml` -- hop 3.
4. `powerbi/*.SemanticModel/definition/tables/*.tmdl` -- hop 4.
5. `templates/visual-contract-binding-map.md` + any filled per-table copy --
   hop 5.

## Starting-point input contract

Accepts exactly one of two starting-point shapes (FR-001):

- **`column`** -- a `schema.table.column` identifier (e.g. a bronze/source
  column name qualified by its table).
- **`metric`** -- a `mappings/<table>/metrics/<Metric>.yaml` repo-relative
  path.

The module reads only already-committed artifacts (FR-002). It MUST NOT
connect to a database, execute SQL, run DAX, open a live Power BI/PBIP
surface, or invoke a deferred execution adapter (F016) or spec-only runtime
(F031-F033) to answer any part of the trace.

## Compose steps (numbered; do not reorder)

### 1. Resolve the starting point

- **Column-rooted**: search `mappings/<table>/source-map.yaml` for a
  `columns[].source_name` (or `rename_to`) entry matching the requested
  column. If found, `resolved: true` and the natural entry hop is hop 1. If
  NOT found in any committed source-map, record a top-level blocker naming
  the missing source-map row (Entity 1's `resolution_blocker`) and produce NO
  downstream chain (FR-015) -- STOP here.
- **Metric-rooted**: confirm `mappings/<table>/metrics/<Metric>.yaml` exists
  and is readable. If found, `resolved: true` and the natural entry hop is
  hop 3 (metric contract) -- a metric-rooted run does not run a full
  reverse-lineage query (out of scope), but traces backward only far enough
  to cite the contract's own required-field origin against the source-map/
  migration-SQL side as proven/unresolved/gap. If the contract file is
  missing or unreadable, record a top-level blocker and STOP.

### 2. Hop 1 -- source_map

Cite the exact `mappings/<table>/source-map.yaml` column entry (path +
`source_name` anchor + the quoted entry) as `proven`. For a metric-rooted
run, this hop is populated only if the contract's required field can be
traced back to a specific source-map row; if it cannot be resolved, record
the hop as a GAP naming what is missing (the specific source-map row or the
resolution path), never silently omitted (FR-008).

### 3. Hop 2 -- migration_sql

Search `warehouse/migrations/*.sql` for the silver/gold column the resolved
source-map row feeds. If a migration file selects or creates that column by
name, cite it as `proven` (path + the SQL column identifier as anchor + the
matched SQL fragment). If no committed migration SQL references it yet,
record a GAP naming the missing reference.

### 4. Hop 3 -- metric_contract

Search `mappings/<table>/metrics/*.yaml` for any contract whose required
fields consume the gold column from hop 2.

- If a contract's required-field name or `binds_to.columns` entry
  explicitly, textually names the gold column, cite it as `proven`.
- If a contract exists but its field reference does not explicitly and
  unambiguously name the gold column (for example a business-friendly name
  with no explicit cross-reference), record the hop as `unresolved` /
  candidate: `citation` MAY point at both sides, but `note` MUST say why the
  link was not promoted to `proven` (FR-005/FR-010's fail-safe -- see the
  Principle-V carve-out below; name-similarity alone is never sufficient).
- If no committed contract references the column at all, record a GAP.
- Two or more contracts may reference the same gold column: surface each as
  its own hop entry; never pick one arbitrarily.

### 5. Hop 4 -- tmdl_measure

Search `powerbi/*.SemanticModel/definition/tables/*.tmdl` for a measure whose
DAX expression sums, references, or otherwise explicitly consumes the gold
column, or whose measure-level comment explicitly names the contract from hop
3.

- An explicit reference (the DAX literally sums the named gold column, or a
  measure comment explicitly names the contract) is `proven`.
- A measure whose name merely resembles the contract's name, with no explicit
  DAX or comment cross-reference, is `unresolved` -- `note` MUST say the link
  is name-similarity only and was not promoted (same FR-010 fail-safe).
- No committed measure references the contract or column at all -> a GAP.
- Two different TMDL measures in different `*.SemanticModel/` folders both
  referencing the same gold column are BOTH surfaced as separate hops; the
  module does not pick one.

### 6. Hop 5 -- dashboard_visual

Look for a filled `visual-contract-binding-map.md` copy for this table (the
dashboard-design skill's committed per-subject-area output; the generic shape
is `templates/visual-contract-binding-map.md`). If a filled copy exists and a
row's `bound_contract` explicitly names the contract from hop 3, cite it as
`proven` (path + `visual_id` anchor + the matched row). If a table has not
yet reached Dashboard Ready and no filled copy exists, record the hop as a
GAP naming the missing binding map -- never fabricate a visual reference.

### 7. Evidence-state vocabulary (exact, non-overlapping; FR-016)

- **`proven`** -- a committed artifact contains an EXPLICIT, machine-readable
  reference connecting this hop to the previous one.
- **`unresolved`** (candidate) -- committed artifacts exist on BOTH sides of
  the hop, but the link between them is not an explicit machine-readable
  reference, and FR-010 has not authorized any promotion method. `note` MUST
  say why it was not promoted.
- **`gap`** -- no committed artifact exists yet at this hop. `note` names the
  missing artifact family.

The module MUST NOT create, infer-and-assert, or silently invent a lineage
edge that no committed artifact already records. Every hop reported as part
of the chain MUST cite the exact committed repo-relative path (and, where the
format supports it, a YAML key / SQL identifier / TMDL object name as an
anchor) it was read from (FR-004); the module MUST NOT assert a hop for which
no committed artifact is cited.

### 8. Net-Sales consistency note (optional; only when applicable)

If the starting point resolves to a Net-Sales-equivalent metric contract,
populate `net_sales_consistency_note` stating the generated hops do not
CONTRADICT `docs/demo/net-sales-end-to-end-readiness-trace.md`'s cited
evidence -- never restating or replacing that trace, and never claiming a
different gold table or TMDL measure than the trace already cites. When the
starting point does NOT resolve to a Net-Sales-equivalent contract, omit this
field/section entirely (leave it null); do not force a comparison that does
not apply.

### 9. Downstream set (User Story 3)

Compose `downstream_set` as a plain restatement of which `hops` entries are
`proven`/`unresolved` downstream of the starting point, using only "is
downstream of" / "cites" language. It MUST NOT contain a verb of obligation
("must", "should", "needs to", "requires re-review") applied to any
downstream item (FR-007). Deciding what to re-review is a human/reviewer
action -- or a separate F014 drift-detector run -- taken OUTSIDE the
artifact; this module supplies the candidate set only and never states an
item "must be re-reviewed," "is broken," or "is at risk" (FR-007, FR-009).

### 10. Write the artifact and STOP

Write exactly one file, populated from `templates/lineage-trace.md`:

- Column-rooted: `mappings/<table>/lineage-column-<column>.md`.
- Metric-rooted: `mappings/<table>/lineage-metric-<Metric>.md`.

The `column`/`metric` root-type token in the filename is load-bearing
collision-avoidance (FR-014): it prevents a column and a same-named metric
contract from writing to the same path. Edit no other artifact. Write no
approval, move no readiness stage. Any judgment call surfaced in the trace --
whether a name-similarity link should ever be promoted (FR-010), or any
grain/PII/business-rollup ambiguity a cited contract carries -- is a
stop-and-ask for the named human (Principle V); this module never resolves
it.

## Honest-state rules (never invent, never silently reconcile)

| Situation | What the module does |
|-----------|------------------------|
| Starting column/metric not found in any committed source-map or contract | top-level BLOCKER naming the missing path; NO downstream chain produced (FR-015) |
| A required upstream/downstream artifact is missing, unreadable, or a blank template | record it as an explicit GAP naming the missing/unreadable path; never fabricate content (FR-008) |
| A contract field or measure name merely resembles its neighbor with no explicit cross-reference | `unresolved` / candidate only; `note` says why; NEVER silently promoted to `proven` (FR-005/FR-010) |
| Two TMDL measures reference the same gold column | both surfaced as separate hops; never pick one arbitrarily |
| A table has not reached Dashboard Ready (no filled binding map) | hop 5 recorded as a GAP, not an error |
| The same trace is regenerated after a cited artifact changes (e.g. a TMDL measure renamed) | the regenerated artifact reflects only the CURRENT committed state; it carries no memory of the prior run and makes no "this changed" claim (that is F014 drift detection's job) |
| A numeric blast-radius score, completeness count, or confidence/health/maturity value is requested | refuse; the artifact expresses impact only as the named set of hops with citations and gaps (hard rule #9, FR-006) |
| A downstream item's re-review priority is requested | refuse to state obligation; report reachability and evidence only (FR-007) |

## Principle-V carve-out -- FR-010 stays OPEN (do not resolve it here)

FR-010 (what resolution method, if any, is authorized for the
contract<->gold-column and TMDL-measure<->contract hops when no explicit
machine-readable cross-reference exists) is a genuine OPEN owner ruling --
the same Principle-V line spec 044 drew for metric-to-metric derivation.
Authorizing any name-similarity method to promote a candidate link toward
"proven" would let this module assert an edge no human declared. This skill
does not authorize, implement, or even sketch such a heuristic. The fail-safe
default that ships regardless of the eventual ruling: every such link is
recorded `unresolved` / candidate, never `proven`, never silently
auto-accepted. If a future ruling authorizes a promotion method, that is a
separate, later change to this skill -- not something an agent running this
skill decides on its own.

## No score, no obligation verb (hard rule #9, FR-006, FR-007)

The artifact emits NO numeric blast-radius score, "N artifacts affected"
completeness count, or confidence/health/maturity value anywhere. Impact is
expressed only as the named SET of hops plus their evidence citations and
gaps. It also carries NO verb of obligation ("must", "should", "needs to",
"requires re-review") applied to any downstream item -- reachability and
evidence only; a human (or a separate F014 drift run) decides what to
re-review.

## Generic only (Principle VII)

The template (`templates/lineage-trace.md`) and this skill's fixed section
labels carry NO worked-example (C086 / retail_store_sales / pharmacy) domain
specific outside a clearly cited illustrative-instance paragraph. The module
resolves a generic `schema.table.column` or `mappings/<table>/metrics/
<Metric>.yaml` starting point (FR-011). ASCII only, UTF-8 no BOM (use `--`
and `->`, no glyphs); short repo-relative paths (Windows 260-char budget).

## Illustrative cited instance (example only -- never inlined into the template)

Using `retail_store_sales`'s currently-committed artifacts as a real, cited
example (Principle VII): a column-rooted run for the `total_spent` column
would trace:

1. `source_map` -- `proven`, citing `mappings/retail_store_sales/source-
   map.yaml` (`columns[].source_name: "total_spent"`).
2. `migration_sql` -- `proven`, citing `warehouse/migrations/0004_create_
   gold_retail_store_sales_star.sql` (the `total_spent` column carried into
   `gold.fct_sales_rss`).
3. `metric_contract` -- `proven`, citing `mappings/retail_store_sales/
   metrics/TotalSales.yaml`'s `binds_to.columns: ["total_spent"]`: an
   explicit, machine-readable reference to the gold column, matching this
   skill's own hop-3 rule (step 4 above) for what counts as `proven`.
4. `tmdl_measure` -- `proven`, citing `powerbi/RetailStoreSales.
   SemanticModel/definition/tables/gold fct_sales_rss.tmdl`'s `TotalSales`
   measure: the DAX (`SUM('gold fct_sales_rss'[total_spent])`) literally sums
   the gold column from hop 2, AND its comment explicitly names the contract
   ("Binds to approved metric contract: TotalSales.yaml") -- both conditions
   this skill's hop-4 rule (step 5 above) treats as `proven` are met.
5. `dashboard_visual` -- `proven`, citing `mappings/retail_store_sales/
   design/visual-contract-binding-map.md` (`v01`/`v05`/`v06`/`v08` rows all
   bind `TotalSales`) -- this table has reached Dashboard Ready with an
   approved binding map, so this hop is NOT a gap for this instance (earlier
   in this feature's own design notes it was expected to be a gap; the
   binding map was filled and approved after that note was written -- a
   concrete illustration of FR-002's "committed means current working-tree
   state," not a fixed git snapshot).

This chain happens to be `proven` end-to-end because `TotalSales.yaml`'s
`binds_to.columns` and the TMDL measure's comment both name their neighbor
explicitly -- not every chain will be this complete. A HYPOTHETICAL contrast
(not a real contract in this repo): if a contract instead named a
business-friendly field (e.g. "net revenue") with no `binds_to` entry and no
textual match to any gold column name, hop 3 would be `unresolved` /
candidate, with a `note` explaining that no explicit cross-reference exists
and that FR-010 has not authorized promoting a name-similarity guess to
`proven`.

This paragraph is the ONLY place in this skill where `retail_store_sales`
specifics appear as content; the template and this skill's fixed section
labels use only `<schema.table.column>` / `<Metric>` placeholders (SC-007).
This example resolves to `TotalSales`, which is NOT a Net-Sales-equivalent
contract (it sums `total_spent`, "total money taken," with no returns/tax/
discount netting distinct from Gross Sales); its `net_sales_consistency_note`
would be omitted (null), not fabricated as consistent or inconsistent with
`docs/demo/net-sales-end-to-end-readiness-trace.md`.

## Composes-only proof

After a run, `git status` shows the only new/untracked file is the one
derived trace at `mappings/<table>/lineage-column-<column>.md` or
`mappings/<table>/lineage-metric-<Metric>.md`. No source artifact (source-
map, migration SQL, metric contract, TMDL, binding map, readiness-
status.yaml) is modified. The skill triggered no `retail check` / `retail
validate` run of its own and opened no DB connection.

## What the agent must NOT do

- Do NOT connect to a database, execute SQL, run DAX, or open a live Power
  BI/PBIP surface; do NOT invoke F016 or any spec-only runtime (F031-F033).
- Do NOT create, infer-and-assert, or silently invent a lineage edge no
  committed artifact already records.
- Do NOT promote a name-similarity-only match to `proven` (FR-010 stays
  OPEN; the fail-safe is candidate-only, always).
- Do NOT fabricate content to fill a missing, unreadable, or blank-template
  artifact -- record a GAP naming the path instead.
- Do NOT emit a numeric blast-radius score, completeness count, or
  confidence/health/maturity value anywhere.
- Do NOT apply a verb of obligation ("must", "should", "needs to", "requires
  re-review") to any downstream item.
- Do NOT move a readiness stage, grant an approval, define or approve any
  business meaning, or write back to any artifact this module reads.
- Do NOT run a reverse (upstream-only) lineage query beyond what step 1's
  metric-rooted backward trace requires, and do NOT render a graphical/visual
  lineage diagram -- output is this one markdown artifact only.
- Do NOT inline C086 / retail_store_sales / pharmacy specifics into the
  template body or a fixed section label -- illustrative examples only, in a
  clearly cited paragraph.

## See also

- The output shape: `../../../templates/lineage-trace.md` (the generic
  copy-me trace).
- The trace this skill generalizes: `../../../docs/demo/net-sales-end-to-
  end-readiness-trace.md` (the hand-authored, single-KPI proof-of-concept;
  never retro-edited).
- The neighbour it does not restate: `../../../specs/044-kpi-derivation-
  lineage/` (metric-to-metric `Derives from` prose, a different layer).
- The authority contract: `../../../docs/architecture/product-modules.md`
  (the five categories + the matrix), `../../../templates/module-
  contract.md` (the copy-me declaration filled above).
- The dashboard-design skill's binding map:
  `../../../templates/visual-contract-binding-map.md` (generic shape; hop 5's
  source).
- The spec: `../../../specs/099-cross-table-lineage-impact/spec.md`.

## Orchestration

When a table owner or reviewer needs to know what sits downstream of a column
or metric contract before changing it -- including immediately after an F014
drift finding -- this skill may be invoked on demand to compose the trace.
This skill stays single-purpose: it composes the chain for one starting
point, tiers each hop honestly, ends with the candidate downstream set, and
STOPS. Deciding what to re-review, resolving FR-010's open name-resolution
question, and re-running drift detection all remain outside this skill.
