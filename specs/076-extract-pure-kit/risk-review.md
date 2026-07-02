# Risk / Adversarial Review — 076 extract pure kit

Adversarial pass over the extraction PLAN (not code — there is none). Each risk: the
failure, its likelihood/blast-radius, and the mitigation already in the plan (or added
here). Verdict at the end.

## R1 — BLAST RADIUS: history purge breaks 302 commits (HIGH severity, mitigated)

**Failure**: someone reads "extract pure kit / remove client data" and runs
`git filter-repo` immediately → all 302 commit hashes rewritten, every PR link dead,
every existing clone diverged, effectively irreversible.
**Mitigation (plan)**: the security section makes tip-redaction the DEFAULT and purge a
SEPARATE, explicitly owner-authorized, trigger-gated operation (public release / erasure)
— never bundled into the extraction PR (TB9 is conditional + isolated). The spec itself
rewrites no history (FR-005).
**Residual**: acceptable — the decision is surfaced, not taken.

## R2 — IRREVERSIBLE DELETE: data removed with no archive (HIGH severity, mitigated)

**Failure**: the future PR deletes `mappings/c086`/`sales_c086`/`warehouse` from the tree
with no recoverable copy → the proof-of-concept warehouse + the approved map are lost.
**Mitigation (plan)**: ARCHIVE precedes DELETE-from-tree (migration steps 4→5); the
archive ref is recorded in the PR; rollback = restore from the archive ref (step 9). And
because tip-redaction (not purge) is the default, the data ALSO remains in history as a
second recovery path.
**Residual**: low — two recovery paths (archive ref + history).

## R3 — BEHAVIOR REGRESSION: removing data breaks the tool (MED severity, mitigated)

**Failure**: a test or a runtime path secretly depends on a removed C086 instance → the
"pure" kit ships broken.
**Mitigation (plan/research)**: R2 proves data-independence (only path conventions);
migration step 2 migrates any data-coupled test to a fixture BEFORE removal; the
non-regression gate (step 7 / US2) — `retail check` + `kit-lint` + `pytest -m unit` +
live smoke — must be green post-extraction.
**Residual**: low — the one real vector (a stray data-coupled test) is explicitly hunted
first.

## R4 — COLLISION: extraction overlaps the in-flight c086 supersession work (MED, mitigated)

**Failure**: the future PR archives/removes `mappings/c086`+`sales_c086` while a human is
mid-reorganizing those exact files → their uncommitted work is lost or the PR conflicts.
**Mitigation (plan/research R5)**: the extraction is BLOCKED until that work
lands/discards; the ordering dependency is stated in the migration precondition and R5.
This spec touched none of it (SC-006).
**Residual**: low — sequenced, not overlapped.

## R5 — INCOMPLETE REDACTION: client markers survive in unscanned corners (MED, mitigated)

**Failure**: `ezaby`/`c086`/`insurance_no` linger in `docs/`, `specs/`, `reports/`,
`powerbi/`, `assets/`, or a workflow file after the "clean" PR → the kit isn't actually
data-free.
**Mitigation (plan Acceptance)**: the acceptance grep is broad (`git grep` across the
whole tree, excluding only the C2 regex + `*.example` + historical `specs/`), and is a
PASS/FAIL gate on the future PR. NOTE added here: the grep MUST be run tree-wide, not just
`mappings/` — the plan's acceptance command already does this.
**Residual**: low-med — depends on the marker list being complete; the plan lists the
known markers and the reviewer can extend. Flag: confirm `reports/`, `powerbi/`, `assets/`
are scanned (the acceptance grep is unscoped by dir, so they are).

## R6 — SCOPE MISCLASSIFY: a KEEP artifact is client-coupled, or a data artifact is generic (MED)

**Failure**: `retail_store_sales` / `warehouse/schema` / `pipelines` mis-sorted →
either client data ships (bad) or a generic asset is needlessly archived (waste).
**Mitigation (research R4)**: these three are explicitly ASSESS rows with per-file
decision rules, made migration step 1 (assess before removing). Nothing is removed on an
unverified classification.
**Residual**: low — the judgment is named, not assumed.

## R7 — STRATEGY REGRET: repo split chosen, then unwanted (LOW, surfaced)

**Failure**: a full repo split (Strategy A) is executed, then the two-repo maintenance
burden proves unwanted and is hard to undo.
**Mitigation (plan)**: the RECOMMENDATION is package+archive (B+C), NOT split; split is
documented as available-later only if the training repo must live on independently. The
strategy is a ratify decision, not auto-taken.
**Residual**: low — the heavy, hard-to-undo option is explicitly not the default.

## R8 — SYNTHETIC-EXAMPLE GAP: examples removed, nothing to steer by (LOW, mitigated)

**Failure**: worked examples removed → `first-hour-compass` has no offer → the onboarding
"aha" degrades.
**Mitigation (research R6)**: migration step 3 authors a narrative + tiny synthetic
example BEFORE/with removal; the acceptance flow confirms `retail init` offers the
synthetic, not the removed data.
**Residual**: low.

## Cross-cutting: this spec's OWN safety

- Writes only `specs/076-*` (SC-006) — no data touched, no history rewritten, c086 in-flight
  work untouched. Verified by `git status` post-task (TA6).
- Adds no gate rule, no runtime change (FR-012).

## Independent adversarial review (2nd perspective) — findings + closure

A separate skeptic reviewed the bundle against the tree and returned **BLOCK** on the
first draft. All findings verified against the tree and FIXED:

| # | Finding | Status |
|---|---------|--------|
| BLOCKER-1 | `powerbi/` was UNCLASSIFIED — ships a full client BI model (`c086 _sales.*` + generically-named `Retailgold.*` = same c086 star); the first-draft acceptance grep (markers `ezaby\|insurance_no\|personel_number\|sales_c086`) was blind to the bare-`c086` dir | **FIXED** — `powerbi/**` added to FR-002 + classification (ARCHIVE the c086 models; ASSESS the generic-named + RetailStoreSales); acceptance grep now includes bare `c086` + `powerbi/`. Verified: corrected grep catches `powerbi/c086 _sales.*`. |
| BLOCKER-2 | FR-001 "classify EVERY artifact" unmet — ~8 top-level dirs omitted (`reports/`, `assets/`, `themes/`, `design/`, `checklists/`, `tools/`, top-level `skills/`) | **FIXED** — complete top-level enumeration + a catch-all (default KEEP unless marker-match) added to FR-002 + plan; no dir unclassified. |
| MAJOR-1 | "No real host committed" was FALSE — cluster id `db-pgsql-fra1-29712` + `ezaby_demo` in 7 files, evading the C2 FQDN-only regex AND the grep | **FIXED** — finding corrected in spec/plan/research; cluster id + `ezaby_demo` added to redaction targets + acceptance markers; C2 FQDN-only gap noted. |
| MINOR-1 | Acceptance grep markers diverged from the prose set (dropped bare `c086`) | **FIXED** — runnable grep now equals the prose marker set (bare `c086`, cluster id, `ezaby_demo`, …). |

Corrected-scope check: the marker grep now matches **126 tracked files** tree-wide (the
true blast radius the future PR must clear) — vs the ~77 the first draft implied. The
first classification would have shipped client data AND reported "clean"; the corrected
one will not.

## VERDICT: PASS-WITH-NOTES (after fixes)

First draft was correctly BLOCKED (powerbi omission + false host finding). After the
fixes — complete top-level classification + catch-all, `powerbi/` archived, corrected
security finding + broadened acceptance grep verified to catch the previously-missed
data — the spec is a safe, complete analysis+plan that executes nothing. The surviving
notes are for the future PR: (1) the two `powerbi/` non-c086-named projects + the 3
original ASSESS rows need per-content decisions (never ship on a generic name); (2) keep
history-purge separate + trigger-gated. The strategy + security posture remain the
human's call at the ratify-ledger.

The plan's failure modes are the right ones and each is mitigated by an EXISTING plan
provision (archive-before-delete, tip-redaction-default, migrate-tests-first,
sequence-after-c086, broad acceptance grep, ASSESS-before-remove). Two notes for the
future PR, not blockers: (1) run the acceptance grep TREE-WIDE incl. `reports/`/`powerbi/`/
`assets/` (the command already is unscoped — just confirm); (2) keep the history purge
strictly separate and trigger-gated. No risk rises to BLOCK; the spec is safe to ratify
as an analysis+plan (it executes nothing). The one thing only a human can settle — the
strategy + security posture — is correctly routed to the ratify-ledger.
