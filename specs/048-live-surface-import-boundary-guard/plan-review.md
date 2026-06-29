# Adversarial Plan-Review: Live-Surface Import Boundary Guard (B3)

Single default-adverse skeptic over spec.md, plan.md, tasks.md, analysis.md,
research.md, data-model.md, contracts/rule-contract.md. READ-ONLY -- findings
report fixes; no artifact was edited by this review. Stage completeness: specify,
clarify, plan, tasks, analyze all present; analyze verdict is clean (0 critical,
0 high). This is NOT an automatic BLOCKED.

## Verdict: PASS-WITH-NOTES

The draft is buildable, internally consistent, reuses the existing B1 AST helper
without forking, stays generic, assumes no deferred capability, fabricates no
confidence, and stays in first-step scope. One judgment-call note is recorded
below; it does not block.

## Axis findings

| ID | Axis | Severity | Finding | Fix / Disposition |
|----|------|----------|---------|-------------------|
| PR1 | hidden-principle-violation | medium | The grounder placed SEVERITY (ERROR vs WARN) in open_for_human ("surface, do not decide"); the clarify stage decided it = ERROR. Tension: was this the agent's call to make? | Defensible and recorded: severity posture is NOT in the Principle-V carve-out (grain/PII/rollup/identity), and Stage 3 authorizes the advisor to resolve non-Principle-V ambiguities with recorded reasoning. ERROR matches the direct sibling B1 (identical defect class) and is reversible-easy (one severity constant). A human may override at ratify. Surfaced here so the reviewer sees the grounder's preference differed; no fix required, but the ratifier should confirm ERROR. |
| PR2 | assumes-deferred-capability | none | Pure static AST rule over committed text; no dependency on F016 (Power BI execution adapter) or F031-F033 (spec-only runtimes) or any live DB. | None. |
| PR3 | c086-leak | none | Forbidden roots are libraries (psycopg2, requests, ...); the live-surface set is generic module paths; all fixtures are synthetic source strings (FR-007, C8, SC-005, T012). Verified: `validate.py`'s only `urllib`-family import is `urllib.parse` (allowed), so the rule is green today and carries no schema specifics. | None. |
| PR4 | fabricated-confidence | none | Emits Findings only; no readiness/confidence number; spec Status stays "Draft"; readiness stage is a [HUMAN RATIFY] item, not self-assigned. | None. |
| PR5 | over-scope | low | The candidate live-surface set excludes `metric_drift.py`, which the grounder noted ALSO has a lazy yaml/driver pattern -- a potential UNDER-scope (the rule could miss a real live surface). | Correctly handled, not a defect: final set membership is an explicit [HUMAN RATIFY] item (spec ## Clarifications; T014). The draft picks a defensible candidate set and leaves widening to ratification (one-line change). No silent over- OR under-broadening. |
| PR6 | over-scope | none | tasks.md adds exactly one rule + its tests + the wiring-id update + the regenerated manifest; it changes NO behavior of the four scanned modules and adds no new dependency, executor, or severity tier. | None. |

## Cross-checks that PASSED

- Reuse-not-fork (Principle II): the rule imports `module_scope_violations`,
  `_FORBIDDEN_ROOTS`, `_FORBIDDEN_DOTTED` from `never_execute` (research R1,
  FR-002, C9) -- no parallel parser.
- Disjointness: the live-surface set is verified disjoint from B1's
  `_GOVERNED_MODULES` + `_GOVERNED_PREFIX` (research R5, T011) -- no double-cover.
- Wiring-latent-gap (repo memory): closed by a direct firing test on a known-bad
  fixture (FR-009, SC-004, T010), not merely listing the id.
- No hard-coded baseline count: the wiring test keys off `len(EXPECTED_RULE_IDS)`
  (FR-008, research R3); the draft asserts no literal rule count anywhere.
- ASCII/Windows-safe (Principle IX): the only non-ASCII is box-drawing glyphs in
  fenced directory-tree blocks, matching shipped siblings 044/047; all prose uses
  `--` and `->`.
- Coverage: 100% of FR (11) and buildable SC (6) map to >=1 task.

## Open items left for the human (not defects)

- [HUMAN RATIFY] Final live-surface set membership (include `metric_drift.py`?).
- [HUMAN RATIFY] The official B-family registry id (the build uses a working id).
- [HUMAN RATIFY] Readiness stage (this rule occupies no roadmap F-row).
- Confirm the ERROR severity posture decided in clarify (PR1).

These are recorded in spec.md ## Clarifications and are structurally reserved for
a named human; the workflow does not self-grant them.
