# INDEX -- route a DAX task to the right file(s)

> Read this before opening any DAX knowledge file. Find the row that matches the
> task, open only the files it names, then end on a metric contract, generated
> DAX shape, analyzer verdict, model-review checklist, or blocked verdict. Do not
> read the whole DAX base.
>
> **Boundary — metric meaning lives upstream.** The *business meaning* of a KPI
> (definition, additivity, grain, required fields, ambiguity, owner rulings) is
> owned by `skills/retail-kpi-knowledge/`, not here. This layer *implements* a
> ready business contract: it validates the contract's model prerequisites and
> generates/reviews the measure. If a "define a KPI" request arrives with no
> upstream business contract, **stop and route to `skills/retail-kpi-knowledge/`**;
> do not invent the KPI's meaning in DAX. Row 2 below assumes the business contract
> already exists and now needs DAX-side validation / a measure.

## Route by task

| I need to... | Open only these | End on |
|---|---|---|
| **1. Ground a model before DAX** | `references/retail-schema.md`, `knowledge/dax-core-concepts.md` | mapped model roles / known missing model metadata |
| **2. Validate a ready business contract for DAX (model features, filter behavior)** — *business meaning is defined upstream in `skills/retail-kpi-knowledge/`* | `patterns/metric-contract-patterns.json`, `knowledge/dax-core-concepts.md`, `checklists/metric-contract-checklist.md` | DAX-side contract validation (model features, filter behavior, validation notes) via `checklists/metric-contract-checklist.md`; if no upstream business contract exists, route back to `retail-kpi-knowledge` |
| **3. Write a basic measure** | `patterns/metric-contract-patterns.json`, `patterns/dax-patterns.json`, `knowledge/dax-best-practices.md` | generated measure + contract assumptions |
| **4. Write time intelligence** | `patterns/dax-patterns.json`, `knowledge/dax-core-concepts.md`, `knowledge/dax-retail-examples.md` | measure shape + date-table/model prerequisites |
| **5. Write ranking / segmentation / ABC** | `patterns/dax-patterns.json`, `knowledge/dax-retail-examples.md` | generated DAX shape + required model assumptions |
| **6. Review existing DAX** | `patterns/analyzer-rules.json`, `knowledge/dax-best-practices.md`, `knowledge/dax-anti-patterns.md`, `checklists/dax-measure-review-checklist.md` | analyzer-style verdict (issues, severity, fix direction) via `checklists/dax-measure-review-checklist.md` |
| **7. Fix context/filter problems** | `knowledge/dax-evaluation-context-deep-dive.md`, `knowledge/dax-calculate-deep-dive.md`, `knowledge/dax-core-concepts.md` | diagnosis of context issue + corrected DAX shape or blocked metadata request |
| **8. Check semantic model prerequisites** | `patterns/metric-contract-patterns.json`, `knowledge/dax-core-concepts.md`, `checklists/dax-model-review-checklist.md` | model-review verdict (`checklists/dax-model-review-checklist.md`) / missing prerequisites |
| **9. Tune DAX performance** | `knowledge/dax-engine-internals.md`, `knowledge/dax-performance-diagnostics.md`, `knowledge/dax-performance-notes.md` | performance diagnosis + safer rewrite direction |
| **10. Explain a DAX concept** | `knowledge/dax-core-concepts.md`, relevant deep dive if needed | concise explanation tied to user's model/problem |
| **11. Use analyzer rules** | `patterns/analyzer-rules.json`, `patterns/analyzer-rule-candidates.json` | rule-based review or staged candidate note |
| **12. Use retail examples** | `knowledge/dax-retail-examples.md`, `references/retail-schema.md` | adapted pattern mapped to the user's model, not copied blindly |

## Route by symptom

| Symptom | Likely route |
|---|---|
| Measure ignores slicers | Fix context/filter problems (row 7) |
| Total row looks wrong | Fix context/filter problems (row 7) |
| YOY/YTD wrong | Write time intelligence (row 4) |
| Ranking changes unexpectedly | Write ranking / segmentation / ABC (row 5) |
| DISTINCTCOUNT too high/low | Ground a model before DAX (row 1) + review existing DAX (row 6) |
| Measure slow | Tune DAX performance (row 9) |
| Visual KPI requested but no metric definition exists | Define the business meaning first in `skills/retail-kpi-knowledge/` (then return for row 2) |
| Date intelligence requested but no date table confirmed | Check semantic model prerequisites (row 8) |

## DAX stop rules

- Do not write a DAX measure before metric intent, grain, and filter behavior
  are known.
- Do not assume column names; map the user's model first.
- Do not design a dashboard KPI without a metric contract.
- Do not optimize before correctness.
- Do not fake semantic model prerequisites such as date table, relationships,
  uniqueness, or grain.
- If required model metadata is missing, stop and ask for it or return a blocked
  verdict.
- Generated DAX must be traceable to a metric contract or explicit user intent.

## File map

```
bi-dax-knowledge/
- SKILL.md                                       the interface (start here)
- INDEX.md                                       this router
- README.md                                      overview, scope, boundaries
- references/
  - retail-schema.md                             the fictional model all examples use
  - source-map.md                                attribution + how content was derived
- knowledge/
  - dax-core-concepts.md                         mental model + index to deep dives
  - dax-evaluation-context-deep-dive.md          row/filter context deep dive
  - dax-calculate-deep-dive.md                   CALCULATE / context transition deep dive
  - dax-function-semantics.md                    per-function return/blank/gotchas
  - dax-engine-internals.md                      SE vs FE, VertiPaq, cardinality
  - dax-performance-diagnostics.md               triage workflow + diagnostic playbooks
  - dax-best-practices.md                        BP-xxx rules
  - dax-anti-patterns.md                         AP-xxx mistakes
  - dax-performance-notes.md                     intro performance primer
  - dax-retail-examples.md                       worked original examples
- patterns/
  - dax-patterns.json                            pattern library
  - metric-contract-patterns.json                reusable metric specs
  - analyzer-rules.json                          enforceable AR-xxx rules
  - analyzer-rule-candidates.json                ARC-xxx candidates (some staged)
- references/agent-training-set.md               graded Q&A bank (teaching/eval)
- references/agent-training-set.json             machine-gradeable twin
- checklists/
  - metric-contract-checklist.md                 fill a metric contract before writing DAX
  - dax-measure-review-checklist.md              pre-merge review of a measure
  - dax-model-review-checklist.md                semantic-model DAX prerequisites
```
