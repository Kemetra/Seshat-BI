# Tasks: Extract the pure agent-driven BI kit

**Feature**: `076-extract-pure-kit` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

> **This is a SPEC task, not an implementation.** Two task groups:
> **A. Spec deliverables** (produced NOW — the five outputs the owner asked for).
> **B. Future implementation PR** (documented here, EXECUTED LATER, gated on ratify +
> on the in-flight c086 work resolving). Group B tasks are the runbook the future PR
> follows; NONE are executed in this task (FR-005).

---

## Group A — Spec deliverables (this task)

- [x] TA1 `spec.md` — scope, classification requirement, non-regression, security +
  acceptance requirements, the do-not (no delete / no history rewrite / no c086 touch)
- [x] TA2 `plan.md` — the artifact CLASSIFICATION table (KEEP/SYNTHETIC/ARCHIVE/DELETE),
  the 3-strategy comparison + RECOMMENDATION, the migration plan, the security decision,
  the acceptance criteria
- [x] TA3 `research.md` — package-clean finding, data-independence proof, security
  scoping, the ASSESS-row method, ordering dependency, synthetic-example approach
- [x] TA4 `risk-review.md` — the adversarial / risk review (FR-010): failure modes +
  mitigations, verdict
- [x] TA5 `ratify-ledger.md` — STOP for the human's two decisions (strategy: package+archive
  vs split; security: tip-redaction vs purge) + the synthetic-example approach
- [x] TA6 Run `speckit-analyze` + a `retail check` on the spec bundle; confirm SC-006
  (spec touched only `specs/076-*`, no data/history/c086 change)

---

## Group B — Future implementation PR runbook (DOCUMENTED, not executed)

> Precondition: the in-flight c086 supersession work has landed/been discarded (R5).
> Gated on ratify of THIS spec's strategy + security decisions.

- [ ] TB1 Assess the 3 ASSESS rows (`retail_store_sales`, `warehouse/schema|gold`,
  `pipelines/`) → finalize each as SYNTHETIC/ARCHIVE/KEEP (research R4 decision rules)
- [ ] TB2 Migrate data-coupled tests to tmp-fixtures / synthetic FIRST; suite green
  before any removal (US2 scenario 1)
- [ ] TB3 Author the synthetic/narrative worked example (R6 decision) so
  `first-hour-compass` still has an offer
- [ ] TB4 Archive `mappings/{c086,sales_c086}` + `warehouse/migrations` + ARCHIVE-classed
  items to the chosen archive ref; record the ref
- [ ] TB5 Remove the archived instances from the working tree (NOT history); leave
  `mappings/` as the empty/synthetic convention dir + README
- [ ] TB6 Genericize shipped-facing docs (worked examples + any shipped doc referencing
  the client) to placeholders/synthetic
- [ ] TB7 Non-regression gate: `retail check` + `retail kit-lint` + `pytest -m unit` +
  live `profile`/`validate` smoke → all green
- [ ] TB8 Acceptance grep (plan §Acceptance) → zero client-data hits; `unzip -l` on the
  wheel → zero data paths
- [ ] TB9 (CONDITIONAL, separately owner-authorized) history purge — ONLY if the repo goes
  public or an erasure obligation triggers; never bundled into TB1-TB8

---

## Dependencies

- Group A is this task (TA1-TA4 done; TA5-TA6 finish it).
- Group B is a FUTURE PR: blocked on (ratify of A) AND (in-flight c086 work resolved).
  Within B: TB1 → TB2 → TB3 → TB4 → TB5 → TB6 → TB7 → TB8; TB9 is a separate conditional.

## Notes

- No task in this file deletes data, moves a file out of `mappings/`/`warehouse/`, or
  rewrites history — Group B is a runbook the future PR executes after ratify (FR-005).
- The recommended strategy (plan §Recommendation) is **package + archive**, not a repo
  split; the ratify-ledger lets the owner override.
