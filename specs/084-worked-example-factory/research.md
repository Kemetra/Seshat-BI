# Research: Worked-Example Factory

**Feature**: `specs/084-worked-example-factory/` | **Phase**: 0 (research)

This is documentation research, not code research: what makes a good generic
example domain, how to keep it generic, and what "complete" means. Every claim
below cites the artifact it rests on.

## 1. What makes a good generic example domain

The single existing worked example, `retail_store_sales`
(`docs/worked-examples/retail-store-sales.md`), is explicit about *why it
matters as evidence*: "one example proving the build isn't enough to prove
genericity" (doc, "Why this evidence matters" callout). It lists the four axes
it deliberately varied relative to a hypothetical C086-shaped default:

| Axis | retail_store_sales' answer | What a *second* example should test |
|------|---------------------------|--------------------------------------|
| Returns | N/A -- no returns in source (RC8 deviation) | A domain **with** a real returns/exchange path, to prove RC8's authoritative-column rule on live returns data, not just its N/A branch |
| PII | Kept a pseudonymous surrogate key (RC4 deviation: keep, not drop) | A domain with **no PII at all**, or one where RC4's default (drop) is adopted as-is, to prove the *default* path, not just the deviation path |
| Language | English-only | A domain with non-English source labels, to prove the encoding/mojibake traps in `templates/source-profile.md` (File-source addendum, "Encoding corruption") on real data |
| Business rollups | None used | A domain with an analyst-supplied rollup (RC11), to prove the "never invent the mapping" rule against a real value->group table |
| Source shape | A single DB-shaped table | A file source (CSV/Excel) or a multi-table source, to exercise the File-source addendum / cross-file drift checks that retail_store_sales never touched |

**Selection rule (derived from the above, generalized):** a good second-example
domain should stress **at least one axis retail_store_sales did not stress**,
and ideally a different combination of axes than the first example, so that
completing it is evidence the *generic* mechanism works, not evidence that one
domain happens to fit. A domain that is structurally identical to
retail_store_sales on every axis (same grain shape, no PII, no returns, no
rollups, English, single DB table) fails selection -- it proves nothing new
(spec.md Edge Cases).

**Illustrative candidates** (named per the task's own examples; NOT drafted, NOT
scoped further, NOT assigned a spec number -- picking one is a future,
separate decision):

- **Inventory / stock levels**: naturally has a different grain (one row per
  stock-take or per movement, not per transaction), a returns-like "adjustment"
  concept, and often a location/warehouse dimension -- stresses grain-shape and
  possibly a business-rollup (product category -> department).
- **Customer loyalty / points ledger**: naturally has PII adjacent to
  retail_store_sales' pseudonymous key but potentially *real* identifiers
  (email, phone) -- stresses the RC4 *drop* default path, plus a
  point-accrual/redemption pair that is structurally like a returns pair
  (accrual vs. redemption, analogous to sale vs. return).

Neither is scoped, profiled, or committed to here -- this is domain-selection
*guidance*, not a domain *choice* (FR-011, Non-Goals).

## 2. How to keep an example generic

Three mechanisms already exist in the repo; the factory process reuses them
rather than inventing new ones:

1. **Constitution Principle VII** ("C086 Is An Example, Not The Schema"):
   worked-example-specific facts must live in that example's own artifacts
   under `mappings/<table>/`, never baked into `templates/` or the constitution
   itself. The factory process's only obligation here is: author guidance and
   templates stay untouched; only a new `mappings/<table>/` directory and a new
   `docs/worked-examples/<table>.md` doc are ever produced per example.
2. **The RC-defaults-then-deviations discipline** (Constitution Principle VI;
   `templates/assumptions.md`): every table starts from the same RC1-RC16
   defaults; only deviations are recorded, each with a triggering data fact.
   This is what makes "generic" checkable -- a reviewer can see exactly what
   varies per table instead of guessing.
3. **No cross-table template edits**: `templates/source-map.yaml` and its
   siblings carry "obvious placeholders, NOT C086" by design (file header
   comment). A worked-example factory run must never edit a file under
   `templates/` to special-case a domain; if a domain cannot be expressed with
   the existing placeholder shapes, that is a stop condition (spec.md Stop
   Conditions), not a template edit.

## 3. The maturity ladder -- which stages a "complete" example must reach

`templates/maturity-report.md` (feature F033, on-disk spec
`specs/027-release-maturity-management/`) is the **authoritative, already-
shipped** maturity ladder. It is explicitly a milestone ladder, not a score
(file banner, "THE LADDER IS A MILESTONE LADDER, NOT A SCORE"). This feature
does not invent a parallel ladder; it cites the existing seven rungs:

| Rung | Capability | Binary evidence test | Relevance to this factory |
|------|------------|----------------------|---------------------------|
| L0 | docs only | kit's docs/templates/spec-kit artifacts exist | Already achieved; not affected by this feature |
| L1 | one worked example | >= 1 worked-example table with mapping artifacts under `mappings/` | **Already achieved** -- `mappings/retail_store_sales/` |
| L2 | two worked examples | >= 2 worked-example tables with mapping artifacts under `mappings/` | **The rung a factory-produced second example would satisfy** |
| L3 | repeatable silver/gold | silver + gold proven repeatable for >= 2 worked tables | **The rung a factory-produced second example's build half would satisfy**, if it reaches Gold Ready |
| L4 | dbt transformation adapter | a dbt adapter (F029) exists in-repo | Not affected -- this feature adds no adapter |
| L5 | Dagster orchestration | a Dagster project (F030) exists in-repo | Not affected |
| L6 | official Power BI execution adapter | an adapter (F016) exists in-repo | Not affected |

**Load-bearing conclusion**: a completed second worked example is *evidence*
for the L2 (and possibly L3) rungs -- it does not itself grant the rung (a named
release owner confirms the reported level per the template's own rule,
"CONSUME, NEVER RE-MEASURE; NEVER SELF-CONFIRM"), and it has zero effect on
L4-L6. This is the concrete backing for spec.md FR-005 / User Story 3.

## 4. Which stages a "complete" worked example must traverse (the readiness spine)

`docs/readiness/readiness-model.md` defines the seven stages every table
passes through (Source Ready -> Mapping Ready -> Silver Ready -> Gold Ready ->
Semantic Model Ready -> Dashboard Ready -> Publish Ready), each entered only
when the prior is `pass`, with four of the seven requiring a **named-human
approval** the agent cannot self-grant (Mapping Ready, Semantic Model Ready,
Dashboard Ready, Publish Ready).

`retail_store_sales` is the only table that has traversed the full spine (to
Dashboard Ready `pass`, Publish Ready `warning` by design -- see its doc Sec 7).
The factory process's completeness contract (see `contracts/worked-example-
completeness.md`) uses exactly this spine, split into what a factory run can
achieve alone (artifacts + static checks) versus what requires a human/live DB
(the four approvals + `retail validate`).

## 5. Repo-only vs. live-DB completeness (research on the split)

Two existing repo postures directly answer "what if there's no database":

- AGENTS.md, "Live DB steps -- graceful deferred mode": absent the `db` extra
  and a DSN, the agent "report[s] the boundary + the enable steps... mark[s]
  numbers `[PENDING LIVE PROFILE]`, and STAY[S] USEFUL (author artifact
  structure). NEVER traceback, NEVER fake a pass."
- Constitution Principle VIII (Static-First Governance, Live Deferred): the
  static checker (`retail check`) is the shippable core; live validators
  (`retail validate`) are a separate, later-run surface that needs a real DB.

**Conclusion for this feature**: the completeness contract must have exactly
two tiers (spec.md FR-004):

1. **Repo-only tier** -- every artifact authored and internally consistent,
   `retail check` exit 0 over the new example's files, and every live-gated
   readiness stage explicitly `blocked` or carrying `[PENDING LIVE PROFILE]`
   evidence rather than a fabricated `pass`.
2. **Human/live-gated tier** -- the four always-required named-human approvals
   recorded in `approvals[]` (plus a fifth, conditional `source_ready` approval
   for a file source, per `templates/readiness-status.yaml`), plus a live
   `retail validate` run backing Gold Ready and beyond.

A factory-produced example can be *fully complete at tier 1* while sitting at
`not_started`/`blocked` on every stage that needs tier 2 -- that is not a defect
in the process, it is the honest, already-precedented state (mirrors
retail_store_sales' own Publish Ready `warning`, which is explicitly "not a
defect" in that doc's Sec 7).

## 6. Sibling feature relationship -- `083-demo-harness`

No `specs/083-demo-harness/` directory exists yet on this branch (checked:
`ls specs/` at the time of writing shows no `083-*` entry). Per this feature's
briefing, `083-demo-harness` **runs** an existing, already-complete worked
example (an execution/demo surface, analogous to
`docs/demo/retail-store-sales-demo.md` already in the repo). This factory
(`084`) **defines the process that produces** a worked example in the first
place (an authoring/definition surface). The two are complementary and
non-overlapping by construction:

- A demo harness has nothing to run until a worked example exists and is
  complete (per this feature's own completeness contract).
- This factory produces no demo, no CLI wiring, no runnable artifact -- only
  documentation and a checklist.

**Sequencing note**: because a demo harness's natural first target is the
*existing* `retail_store_sales` example (already complete), `083-demo-harness`
does not strictly depend on `084` shipping first. But if `083-demo-harness`
ever wants to demo a *second* worked example, that example would need to satisfy
this feature's completeness contract first. This feature is therefore a natural
prerequisite for demoing any example beyond the first, though not for
`083-demo-harness` itself to exist.

## 7. Why this feature comes last in the idea-bank / roadmap ordering

This feature is process/meta-documentation with no runtime consumer of its own
(no code, no rule, no CLI verb) and its output (a documented recipe) is only
useful once someone is ready to invest in an actual second worked example -- a
multi-stage, multi-approval effort in its own right. It has no forcing function
(unlike, e.g., a governance rule that closes a static gap). This matches the
task's own note ("this feature naturally comes LAST in implementation order")
and is recorded here as a plan-level sequencing fact, not a constraint this spec
enforces on anything else.

## Sources cited in this research

- `docs/worked-examples/retail-store-sales.md` (the four genericity axes, the
  "why this evidence matters" rationale, Sec 7's warning-by-design precedent)
- `templates/maturity-report.md` (the L0-L6 ladder, binary-evidence rule,
  consume-never-self-confirm rule)
- `docs/readiness/readiness-model.md` (the seven stages, the four
  human-approval seams)
- `.specify/memory/constitution.md` Principles V, VI, VII, VIII
- `AGENTS.md` ("Live DB steps -- graceful deferred mode")
- `docs/worked-examples/README.md` (the reuse recipe already sketched there -- this feature formalizes and extends it into a checkable contract)
