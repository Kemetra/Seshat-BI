# Glossary — Seshat BI

A one-stop reference for the terms, abbreviations, and rule ids used across this repo.
Each entry is one line; follow the linked source for the authoritative detail. Entries
are grouped, then alphabetical within a group.

> **Authoritative sources** (this page summarizes, it does not replace them): the spine
> — `docs/readiness/readiness-model.md`; the cleaning defaults —
> `docs/decisions/0002-retail-cleaning-defaults.md`; the static rules — `src/retail/rules/` (live
> registry) and the `retail-govern` skill (id → fix); the method —
> `docs/medallion-playbook.md`.

---

## Readiness spine

| Term | Meaning |
|------|---------|
| **Readiness spine** | the operating state model that organizes the existing gates into a tracked seven-stage sequence; a state model, not a new gate (`docs/readiness/readiness-model.md`). |
| **Stage 1 — Source Ready** | a profiled, understood source exists; semantics + any PII ruling confirmed by the data owner. |
| **Stage 2 — Mapping Ready** | grain / PK / PII mapped and reviewed; the source-mapping gate is CLEARED with a recorded human approval. |
| **Stage 3 — Silver Ready** | a typed/cleaned silver table built and statically clean (`retail check` exit 0). |
| **Stage 4 — Gold Ready** | a Kimball star built and live-validated (PK uniqueness, date coverage, 0 orphan FKs, penny-exact reconcile). |
| **Stage 5 — Semantic Model Ready** | owner-approved metric contracts + a governed PBIP model whose every measure binds 1:1 to a contract. |
| **Stage 6 — Dashboard Ready** | a report design where every measure-bearing visual binds to an approved contract; design review signed off. |
| **Stage 7 — Publish Ready** | the handoff pack is complete and a publish approval is recorded by the data owner/governance. |
| **Status: `not_started`** | the stage has not begun; the prior stage may not be `pass` yet. |
| **Status: `blocked`** | a required artifact, check, or approval is missing — see `blocking_reasons`. **Blocks the next stage.** |
| **Status: `warning`** | advanced, with a non-fatal issue recorded (a static WARN, an accepted deviation). **Does not block the next stage.** |
| **Status: `pass`** | all required artifacts exist, all required checks pass, approvals are recorded. |
| **Evidence / blockers** | the explicit `evidence[]` (committed files/check-runs) and `blocking_reasons[]` that justify a status — never a fabricated confidence score (hard rule #9). |
| **Approval seam** | a stage that needs a named-human sign-off in `approvals[]`: Mapping, Semantic Model, Dashboard, Publish. The agent never self-grants one (Principle V). |

## Medallion layers

| Term | Meaning |
|------|---------|
| **Medallion** | the bronze → silver → gold layering method (raw landing → typed/cleaned → analytics star). |
| **bronze / raw** | a faithful all-TEXT landing of the source, retained as-is (missingness measured as `'' OR NULL`). |
| **silver** | the typed/cleaned flat table at the declared grain; `''` → NULL, exact `NUMERIC`, ids kept TEXT. |
| **gold / marts** | the Kimball star Power BI reads (one fact + conformed dimensions + a date dim). |

## Modeling & Power BI

| Term | Meaning |
|------|---------|
| **Grain** | what one row represents (e.g. "one retail transaction"); decided first (RC1). |
| **PK (primary key)** | the column(s) unique at the grain; proven on the *transformed* rows, not just landed (RC2). |
| **Star schema (Kimball)** | a central fact table joined to denormalized dimension tables. |
| **Fact** | the table holding measures at the grain (e.g. `gold.fct_sales`). |
| **Dimension** | a table of descriptive attributes joined to the fact (e.g. `dim_product`). |
| **Conformed dimension** | a dimension shared/consistent across more than one fact or subject area. |
| **SK (surrogate key)** | a system-generated integer key for a dimension row (`_sk`, IDENTITY). |
| **FK (foreign key)** | the fact column referencing a dimension's surrogate key. |
| **Degenerate dimension** | a transaction identifier kept on the fact itself, with no separate dim table (e.g. `transaction_id`). |
| **Unknown member (`-1`)** | the `_sk = -1` row in every entity dim that absorbs missing/unmatched keys via `COALESCE(..., -1)` (RC14). |
| **Marked date table** | a date dimension tagged for time-intelligence; it is contiguous and carries **no** `-1`/NULL member (rule S8). |
| **PBIP** | Power BI Project — the plain-text, git-friendly save format (preview feature). |
| **PBIR** | the report-definition half of a PBIP (the visuals/pages). |
| **TMDL** | Tabular Model Definition Language — the plain-text semantic-model definition in a PBIP. |
| **DAX** | the formula language for Power BI measures/columns. |
| **Semantic model** | the governed data model (tables, relationships, measures) Power BI reports sit on. |
| **Measure** | a DAX aggregation (PascalCase, in a display folder); should bind to a metric contract. |
| **Display folder** | the folder a measure is organized under in the model (required by rule D2). |

## Metrics, governance & delivery

| Term | Meaning |
|------|---------|
| **Metric contract** | a stored definition of a measure (name, grain, formula intent, owner) the model's DAX must bind to (`templates/metric-contract.yaml`; F009). |
| **KPI pack** | a generic set of retail metric definitions a table can adopt (`docs/metrics/metric-contract-store.md`; F009). |
| **Handoff pack** | the documentation/evidence bundle handed to a BI consumer at Publish Ready (F013). |
| **Source-mapping gate** | the rule that no `silver.*` SQL is written until the map is reviewed + approved (hard rules #2/#3; Stage 2). |
| **Companion module / adapter** | an optional tool that READS/SUMMARIZES/EXECUTES an approved step but never creates truth (F024 tier; e.g. dbt, Dagster). |
| **`retail check`** | the static governance gate (the rule families below); runs on committed text, no DB. |
| **`retail validate`** | the live data surface; reconciles a materialized table against a running Postgres (read-only). |
| **`retail value-check`** | the L4 value proxy that asserts a contract's live value still matches its approved `expected_value`. |
| **`retail generate`** | the DAX generator that emits a verified measure from an approved metric contract. |
| **`retail scaffold`** | the rule-authoring helper: author mode writes a new rule's stub module + failing test + EXPECTED_RULE_IDS insertion and prints the golden-regen commands + a glossary row (write/print split); `--doctor` reads the five wiring places and reports drift (062). |

## Cleaning defaults — RC1–RC16

The **ADR-0002 retail cleaning defaults** (`docs/decisions/0002-retail-cleaning-defaults.md`):
the starting-point answers for a silver/gold build. A table *adopts* each default or
records a *deviation* with its triggering data fact (in `mappings/<table>/assumptions.md`).
Highlights: **RC1** grain first · **RC2** PK proven on the transform · **RC4** PII handling
· **RC5** `''` → NULL · **RC7** type discipline (money/qty → `NUMERIC`, ids stay TEXT) ·
**RC8** returns from an authoritative column · **RC9** keep independent measures · **RC13**
idempotent migration · **RC14** Kimball star + `-1` member · **RC15** contiguous date dim ·
**RC16** reconcile totals + 0 orphan FKs.

> **Namespace note:** `RC<n>` are *cleaning defaults*; the static checker uses a separate
> letter-prefixed namespace (below). They no longer collide (feature 002).

## Static check rules (`retail check`)

This catalog is the **single source of truth for `retail check`'s rule count.**
The **live registry in `src/retail/rules/` is authoritative**; the table below
mirrors it and the `retail-govern` skill maps each id to its fix.

> **Currently 53 rules in 19 families** (S, D, C, R, RS, G, P, A, B, PP, SC, DF, SL, AL, AD, AQ, DL, CT, DR).
> When a rule is added or removed, update the table and this line **together** — and
> elsewhere refer to "the static `retail check` gate" by name rather than restating a
> number. Restated counts are exactly what drifted before (see
> `docs/quality/drift-consistency-audit-2026-06-28.md`). (`S4` is split into
> `S4a`/`S4b`.)

| Family | Layer it guards | Rules |
|--------|-----------------|-------|
| **S** | SQL / migrations | `S1` snake_case identifiers · `S2` medallion schema names · `S3` `vw_` prefix on views · `S4a` migration filename + numbering · `S4b` migration guard form (layer-aware) · `S5` type discipline (RC7) · `S6` gold dim `-1` unknown member (RC14) · `S7` contiguous date dim (RC15) · `S8` marked date table has no `-1`/NULL member |
| **D** | DAX / TMDL semantic model | `D1` PascalCase measure names · `D2` displayFolder required · `D3` no duplicated measure logic · `D4` use `DIVIDE()` not `/` · `D5` prefer explicit measures (WARN) · `D6` no bidirectional relationships · `D7` time-intelligence needs a date-table marker · `D8` partitions source from `gold` only · `D9` no hardcoded date literals in measures · `D10` no `FILTER(ALL/ALLSELECTED/ALLEXCEPT(...))` full-table-scan anti-pattern · `D11` each measure needs a `///` doc comment |
| **C** | connection / secrets | `C1` connection uses parameter identifiers, not string literals · `C2` no committed secrets |
| **R** | PBIR report | `R1` PBIR model reference must be relative |
| **RS** | readiness-status integrity | `RS1` readiness status files are internally consistent (status, evidence, blockers, approvals, and current stage agree) |
| **G** | git / project hygiene | `G1` `.gitignore` correctness · `G2` definition artifacts committed · `G3` UTF-8 without BOM · `G4` `.gitattributes` EOL policy · `G5` Windows MAX_PATH discipline · `G6` no real host/value in committed PBIP parameters |
| **P** | project layout / process | `P1` Approach-A PBIP layout · `P2` commit-message convention |
| **A** | route registry / architecture | `A1` route-registry targets resolve or are honestly marked planned · `A3` knowledge-map route ids ↔ `routes.yaml` ids are in bijection |
| **B** | never-execute boundary | `B1` no module-scope DB/network import in the static core (the static surface never executes on import) · `B3` live-surface modules keep DB/network imports lazy (no module-scope connection import) |
| **PP** | publish-pack completeness | `PP1` every required handoff-pack section is filled (checks the publish-approval slot is present, never grants it) |
| **SC** | status-claim integrity | `SC1` a prose status claim reconciles with tracked-file evidence (no stale planned/built marker) · `SC2` a prose "N rules" count claim reconciles with the authoritative rule count (manifest-anchored, never a free repo scan) |
| **DF** | dependency-edge integrity | `DF1` parked-on dependency edges reconcile with tracked-file evidence |
| **SL** | KPI coverage scorecard | `SL1` a committed coverage scorecard is structurally well-formed (status-enum, named blocker, resolving contract, no percentage) |
| **AL** | assumption ledger | `AL1` a metric contract with an unresolved assumption (blocked + reasons) must not also carry a settled gold binding · `AL2` contracts on one gold table record no contradictory decided ambiguity rulings |
| **AD** | additivity consistency | `AD1` a metric's additivity classification is not composed illegally with its lineage parents (no direct sum of a non-additive/semi-additive metric); absent/ambiguous class is ERRORed, never inferred |
| **AQ** | answerability | `AQ1` every domain decision-question route resolves to an existing contract (Seeded) or is honestly marked Planned with the placeholder glyph; dangling Seeded routes and stale Planned markers ERROR, ambiguous rows WARN |
| **DL** | design-lint (Power BI visual surfaces) | `DL1` theme JSON purity -- a theme file carries styling DEFAULTS only (surface 3, `docs/powerbi/theme-json.md`) · `DL2` background-spec purity -- a page background carries STATIC STRUCTURE ONLY, no dynamic/data-bound content (surface 2) · `DL3` token->theme fidelity -- a theme's declared styling values (dataColors, background) match the design tokens they compile from (surface 3) · `DL4` design-review evidence well-formedness -- a filled design-review-evidence record carries every required field (page_id, anti_patterns_checked, contrast_pairs, reviewer, date); verify-slot-only, never grants the pass · `DL5` grid arithmetic-closure -- a layout grid's column/row math closes (usable width/height == columns*column_width + gutters), and a declared arithmetic_check is not stale · `DL6` visual-spec self-check consistency -- a filled visual-spec that self-attests an anti-pattern (any `anti_pattern_checks` true) records at least one real `readiness.blocking_reasons` entry (single-spec existence pairing; the cross-file key-set reconcile stays with B1) |
| **CT** | contrast / accessibility | `CT1` token text/background color pairs meet the token-declared WCAG contrast floor (deterministic sRGB luminance ratio, pass/fail against `accessibility.min_text_contrast_ratio`, never a score) |
| **DR** | design-layer route honesty | `DR1` path foot-gun + stale-phrase guard -- no tracked file lives under a `.claude/worktrees/` scratch prefix, and no doc still contains a curated known-stale phrase (`docs/quality/design-stale-phrases.yaml`; the inverse of SC1's anchor-presence check) |

## Project shorthand

| Term | Meaning |
|------|---------|
| **Seshat BI** | the product (package alias `Seshat_BI`; previously the internal *Tower BI Agent Kit*). |
| **F-number** | a roadmap feature id (e.g. F016); the authoritative sequence id (`docs/roadmap/roadmap.md`). |
| **Hard rules** | the nine non-negotiable ordering constraints in the roadmap (e.g. #2 no source straight to silver; #6 no Power BI execution before semantic-model readiness; #9 no fake confidence). |
| **Principle V** | the constitution rule that the agent **stops at judgment calls** (grain, PII, business rollups, approvals) for a named human. |
| **F016** | the deferred, gated, execution-only Power BI adapter — materializes/publishes an approved model; deliberately last. |
| **C086** | the first worked example (El Ezaby pharmacy); the *first* example, not the universal schema (hard rule #7). |

## See also

- The spine: `docs/readiness/readiness-model.md` and the seven `docs/readiness/<stage>-ready.md` docs.
- The worked examples: `docs/worked-examples/README.md`.
- The cleaning defaults: `docs/decisions/0002-retail-cleaning-defaults.md`.
- The rules: `src/retail/rules/` + the `retail-govern` skill.
- The roadmap + hard rules: `docs/roadmap/roadmap.md`.
