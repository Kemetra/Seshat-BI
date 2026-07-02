# Adversarial Plan-Review: Rule-Count Claim Reconciler (SC2)

**Stage**: 6 (single default-adverse skeptic). READ-ONLY over spec.md, plan.md,
tasks.md (+ research.md, data-model.md, contracts/, quickstart.md). Reports fixes;
edits no artifact.

**Date**: 2026-07-02

**Draft completeness precheck**: spec.md, plan.md, tasks.md, analysis.md, and this
review are all present on the branch; analyze ran (verdict CLEAN, 0 critical / 0
high). Not an automatic BLOCKED.

## Axis 1 -- Hidden principle violation

- **Principle VIII (static-first / stdlib-only core)**: The count source is
  `docs/rules/rules-manifest.json` read with stdlib `json`; the rule takes NO
  module-scope import of the rules package and only a lazy `import yaml` inside the
  handler (contract INV-3, FR-014). This is the SC1 discipline preserved. No
  violation.
- **Hard rule 9 (no fabricated confidence)**: strictly categorical equality; the
  only integers in a finding are the claimed and authoritative counts, explicitly
  distinguished from a confidence measure (FR-013). No violation.
- **Principle V (agent stops at judgment calls)**: no grain/PII/rollup/identity
  question arises; the two genuinely human-owned items (roadmap readiness STAGE and
  the F-number/spec-number) are recorded for the human and NOT self-assigned (spec
  Clarifications deferral note; tasks T022; research D6). No violation.
- **Circularity probe**: SC2 reads the same JSON that the golden snapshot test pins
  to `all_rules()`. Could a corrupted manifest make SC2 vacuously agree with a wrong
  prose count? No -- the manifest-snapshot test independently fails closed on any
  manifest/registry drift, so the two guards are independent; and SC2's
  count-source guard (contract step 3) fails loud on an unreadable/unparseable
  source. No hidden hole.
- **Verdict**: PASS.

## Axis 2 -- Assumes a deferred capability

- No task or requirement invokes the Power BI execution adapter (F016), the
  spec-only runtimes (F031-F033), a database, or ingestion. SC2 is a pure static
  read of committed text + one committed JSON + the tracked-files set. Out of Scope
  explicitly excludes all live capability.
- **Verdict**: PASS.

## Axis 3 -- C086 / pharmacy leak

- The rule, the manifest schema, and the single seed entry are generic governance
  infrastructure (the glossary + the committed rule-count manifest). Test fixtures
  are synthetic. T024 is a dedicated final generic-leak sweep over the module, its
  test, and the manifest. c086_risk in grounding was "none".
- **Verdict**: PASS.

## Axis 4 -- Fabricated confidence / self-granted readiness

- No numeric score, percentage, or readiness value anywhere. The spec Status stays
  Draft; no artifact writes "Ratified". SC2 grants no readiness and advances no
  stage. FR-013 + SC-004 + contract INV-2 lock the categorical output.
- **Verdict**: PASS.

## Axis 5 -- Over-scope (beyond the idea's first step)

- Family-count reconciliation is explicitly deferred (Out of Scope, Q3).
- Manifest completeness/coverage is explicitly deferred (Out of Scope, Q4),
  mirroring how SC1 shipped without a coverage sibling.
- In-prose number extraction is explicitly excluded (the anchor is presence-only;
  the integer comes from the declared claimed-count). This keeps SC2 at exactly the
  first-step scope named in the idea backlog.
- **Verdict**: PASS.

## Notes (non-blocking)

- **N-1 (low)**: Task ordering dependency -- SC2's count source
  (`rules-manifest.json`) is regenerated in T020, and the live-guard test (T021)
  and the seed `claimed-count: N+1` both depend on that regen having run (so the
  source length is N+1). The tasks already pin this order and analysis A-2 calls it
  out; the implementer must not reorder T020 after T021. Advisory only.
- **N-2 (low)**: The seed target count is N+1 (post-SC2), not N. This is correct and
  well-justified across artifacts, but it is a subtle point an implementer could get
  wrong by correcting the glossary to the pre-SC2 count. T017-T019 and research D3
  make it explicit; flagged so a reviewer double-checks the final integer equals the
  registered count after SC2 lands.
- **N-3 (low)**: The exact glossary anchor sentence is chosen at implement time
  (T018 -> T019 dependency). Intentional -- the manifest anchor must be
  byte-identical to the corrected wording. No action needed beyond honoring the task
  order.

## Verdict

**PASS-WITH-NOTES** -- 0 critical, 0 high, 3 low advisory notes (task-ordering and
count-arithmetic care for the implementer). Analyze is CLEAN; all workflow stages
ran; spec Status remains Draft. The spec is ratifiable pending the human's two
reserved decisions (roadmap readiness stage + F-number/spec-number) and the human
ratification edit itself, which this workflow is structurally forbidden to make.
