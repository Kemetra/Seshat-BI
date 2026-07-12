# dashboard-semantic-audit (spec 123, US5)

Surface 1 (report visuals), a REPORT-LEVEL review aid layered on top of an
already-composed report. Open this workflow when someone asks to "audit the
report against its intent", "check the whole dashboard makes sense", or "does
this report actually answer what it was supposed to answer" -- AFTER a Report
Intent, page blueprints, visual specs, and a report composition are committed.
It is DISTINCT from `dashboard-qa.md` (which critiques ONE visual/page's
presentation defects against the thirteen-anti-pattern catalog): this workflow
asks whether the WHOLE report, taken together, answers its committed Report
Intent -- an intent question no page answers, a page mixing two purposes, a
diagnostic report with no visible driver, and so on (FR-018). This workflow
checks and cites; it does not redesign anything and it is not a `retail check`
gate (data-model.md D8) -- it is decision SUPPORT, not enforcement.

## Scope (read first)

This workflow reads ALREADY-committed artifacts -- the Report Intent
(`templates/report-intent.yaml` shape), the Report Composition
(`templates/report-composition.yaml` shape), the page blueprints
(`templates/dashboard-page-blueprint.yaml` shape) and their visual specs
(`templates/visual-spec.yaml` shape), the recorded `retail dashboard-planner`
verdict for each proposed page, and the filled
`a11y-rtl-readiness-checklist.md` -- and emits categorical findings. It does
NOT:

- author or edit the intent / blueprints / visual specs / composition (that is
  the report-intent-interview skill + the US2 coordinator + `page-blueprint.md`);
- redesign a visual or fix a presentation defect (that is `dashboard-qa.md`
  and the visual-design principles it cites);
- re-run `retail dashboard-planner`'s set-relation logic, or re-derive CT1
  contrast by reading `design/tokens/...` (FR-020: this workflow REUSES the
  shipped tools' RECORDED OUTPUTS -- it cites them, it never recomputes them);
- grant `dashboard_ready: pass`, `report_intent_approval`, or any other
  approval -- the audit is decision support, never a sign-off (Principle V);
- produce any numeric score, percentage, confidence value, or ranking anywhere
  (FR-020/FR-035) -- every finding's category is one of the seven closed values
  below, nothing else.

## The closed finding vocabulary (FR-017, verbatim -- never drift from this list)

Every finding's `category` is EXACTLY one of these seven values. Do not invent
an eighth, rename one, or substitute a synonym:

```
covered | incomplete | missing | conflicting | warning | blocked | not_applicable_with_reason
```

Each finding is the shape (data-model.md's Semantic Audit Finding entity):

```yaml
check: "<one of the FR-018 check ids, e.g. every_intent_question_covered>"
category: "<one of the seven values above>"
evidence:
  - "<committed artifact path(s), or a pointer into the in-memory shape checked>"
owner_or_correction: "<the named owner (from the intent's own `owner` field) or the correction to make>"
```

## The one load-bearing rule: cite recorded outputs, never recompute them

**Never re-run a shipped tool's own algorithm inside this workflow.** Two of
the FR-018 checks are structurally required to reuse another tool's OUTPUT,
not its logic:

- **"pages don't duplicate"** reads a RECORDED `retail dashboard-planner`
  verdict (a small committed YAML, e.g.
  `mappings/<subject-area>/design/dashboard-planner-verdicts.yaml`, one row per
  proposed page: `proposal_page` / `verdict` / `of_page`) and cites it. It
  never calls `dashboard_planner`'s set-relation logic itself -- if that
  verdict has not been recorded yet, this check is `blocked` (or
  `not_applicable_with_reason` if no path was ever supplied), never silently
  skipped and never re-derived on the spot.
- **"accessibility/mobile/RTL addressed"** reads the filled
  `a11y-rtl-readiness-checklist.md`'s recorded Roll-up `overall_status` and
  cites it verbatim. It never opens `design/tokens/...` or re-runs CT1
  (`design_contrast.py`) -- that computation already happened once, and its
  recorded disposition is what gets cited here.

Always call the pure library function -- never improvise the check logic by
hand:

```python
from pathlib import Path
from seshat.semantic_audit import run_semantic_audit

findings = run_semantic_audit(
    repo_root=Path("."),
    intent=intent_dict,            # parsed report-intent.yaml
    composition=composition_dict,  # parsed report-composition.yaml
    pages=[                        # one dict per composed page
        {
            "page_id": "overview",
            "business_question_ids": ["q1", "q2"],
            "visuals": [{"visual_id": "v1", "visual_type": "line_chart"}],
        },
        # ...
    ],
    planner_verdicts_path="mappings/<subject-area>/design/dashboard-planner-verdicts.yaml",
    a11y_checklist_path="mappings/<subject-area>/design/a11y-rtl-readiness-checklist.md",
)
```

`run_semantic_audit` (`src/seshat/semantic_audit.py`) is read-only: it opens
exactly the two paths given (if supplied) and returns an immutable tuple of
findings. It writes nothing, grants no approval, and moves no readiness stage.

**Mapping a real page blueprint's `pages[]` entry (do this before calling the
function).** A committed `dashboard-page-blueprint.yaml` carries a SINGULAR
free-text `business_question` field, not a list of intent question ids. Per
FR-002a, that field MUST trace to one (or more, if the page legitimately
answers a small composed set) of the intent's `business_questions[].question_id`
values -- resolve that trace explicitly (by matching the blueprint's
`business_question` text against the intent's `business_questions[].text`, or
by whatever explicit `question_id` reference the coordinator (US2) has already
recorded) BEFORE building each `pages[]` entry's `business_question_ids` list.
Do not guess the match, and do not pass every intent question id just to avoid
the mapping step -- an unresolved or ambiguous trace is itself a Step 3
finding (FR-002a), not something to silently paper over here. Likewise, a
page's `visuals[]` entries are read from its filled `visual-spec.yaml` files
(`visual_id` + `visual_type`), not invented.

## Step 1 -- Confirm the artifacts are the APPROVED / committed set

Audit the report the reviewer is actually about to sign off on, not a draft
mid-edit: the committed `report-intent.yaml`, `report-composition.yaml`, and
the page blueprints + visual specs it references. Name each path explicitly.

## Step 2 -- Run the checks (each an FR-018 item)

The library function above covers the mechanically-decidable subset (every
intent question covered; each page single coherent purpose; diagnostic
reports include drivers; pages don't duplicate; accessibility/mobile/RTL
addressed). The remaining FR-018 checks are cross-artifact JUDGMENT calls this
workflow performs by reading the artifacts directly (data-model.md's
check-to-artifact map) rather than a computed function -- they still emit only
the seven-value vocabulary, cite the artifact read, and name an owner:

| FR-018 check | Read this artifact, cite it |
|---|---|
| primary outcomes visible | visual specs in `kpi_strip`/`main_insight` vs intent `outcome_metrics` |
| guardrails/comparisons represented | visual `anti_pattern_checks.kpi_without_comparison` + intent `guardrail_metrics` |
| action/exception paths exist | blueprint `narrative.recommended_action`/`key_exception` + visual `drill_through` vs intent `expected_actions_and_exceptions` |
| composition matches declared purpose | `report-composition.yaml` audience/order/landing vs intent audience/purpose |
| navigation/drill coherent | `report-composition.yaml` `navigation` (an orphan `to:` naming no page) + visual `drill_through` |
| cross-page filters consistent | `report-composition.yaml` `cross_page_filters` vs each page's `slicers` |
| narrative claims supported | blueprint `narrative` text vs the page's `required_metric_contracts` + `visuals` |
| freshness addressed | blueprint `sections.footer_status.present` |
| orphan/unmapped hygiene | filled `visual-contract-binding-map.md` + (if PBIR exists) `visual-implementation-trace.md` |

An artifact that is missing for one of these judgment checks is `blocked` or
`missing` (naming the path checked), never silently skipped and never treated
as "nothing to report."

## Step 3 -- FR-002a: a blueprint `business_question` traces to a declared intent question

Every page blueprint's `business_question` field MUST trace to one of the
intent's `business_questions[].text` (by `question_id`, per FR-002a). A
blueprint `business_question` with no matching intent question is a coherence
finding here (`conflicting` or `missing`, naming the orphan text) -- it is
NEVER silently accepted as a second, independently-declared purpose (that
would violate the single-owner rule, FR-038).

## Step 4 -- Record findings; never self-grant approval

Present every finding with its `check` / `category` / `evidence` /
`owner_or_correction`. Do not fold the findings into a single number, a
percentage, or a ranked list -- there is no aggregate score (FR-020/FR-035).
This workflow does NOT set `dashboard_ready: pass`, `report_intent_approval`,
or any other Decision Store record -- it hands the finding set to the named
human review (US6) as evidence, exactly like `dashboard-qa.md` hands its
findings to the design-review sign-off.

## Stop-and-ask (Principle V)

STOP and surface to a human rather than self-answering when:

- whether a page's two questions are truly "one coherent purpose" is
  ambiguous (a judgment call, not a mechanical count);
- the recorded dashboard-planner verdict or the a11y checklist looks stale
  against the current composition (re-verify the path/date rather than
  guessing the current state);
- the audit implies a metric or field is wrong -- this workflow may flag that
  a blueprint's narrative or a visual seems uncontracted, but it does NOT
  redefine the metric (F009) or the field (F010); it records the finding and
  points upstream.

## See also

- The per-visual anti-pattern catalog this workflow is DISTINCT from:
  `docs/powerbi/visual-qa.md`, `dashboard-qa.md`.
- The FR-018 check-to-artifact map in full: `specs/123-governed-dashboard-intelligence/data-model.md`.
- The pure library function: `src/seshat/semantic_audit.py`.
- The recorded dashboard-planner verdict this workflow cites (never re-runs):
  `docs/tools/dashboard-planner.md`.
- The filled a11y/RTL checklist this workflow cites (never re-derives CT1):
  `templates/a11y-rtl-readiness-checklist.md`, `mappings/retail_store_sales/design/a11y-rtl-readiness-checklist.md`.
- The human review this audit's findings feed into: US6 (blueprint approval
  & versioning), the shipped Decision Store.
- Where the four statuses / this feature's seven-value vocabulary sit inside
  the wider readiness system: `docs/readiness/readiness-model.md`.
