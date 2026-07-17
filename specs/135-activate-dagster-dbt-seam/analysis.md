# Cross-Artifact Analysis: Activate the dagster-dbt Engine Seam

**Scope**: a non-destructive consistency read across `spec.md`, `plan.md`, and
`tasks.md` for feature 135, plus a governance-consistency read against the
committed specs 133 and 134 this feature depends on. Findings are recorded
honestly, including ones against this author's own artifacts. This analysis makes
no changes and is not a ratification.

## Method

- Requirement coverage: every FR/SC in spec.md traced to a task and a plan section.
- Terminology drift: vocabulary compared against specs 133/134 and the committed
  code (`gates.py`, `doctor.py`, `seshat.dbt`, the evidence schema).
- Unstated dependencies: assumptions in the plan/tasks that are not established.
- Contradictions: internal (135 vs 135) and external (135 vs committed 133/134).

## Requirement coverage

| Requirement | Plan section | Task(s) | Status |
|---|---|---|---|
| FR-001 explicit engine, fail-closed default | Approach 1 | T004, T005, T010, T011 | COVERED |
| FR-002 governed dbt via seshat.dbt, no raw pass-through | Approach 3 | T006, T008 | COVERED |
| FR-003 shadow-only, migrations never deleted | Approach 2/3 | T008, T016, T017 | COVERED |
| FR-004 identical gate, STOP edge unchanged | Approach 2 | T006, T007, T009 | COVERED |
| FR-005 downstream of source_map, topology unchanged | Approach 2 | T009, T019 | COVERED |
| FR-006 deferred/unavailable truthfulness | Approach 4 | T012, T013 | COVERED |
| FR-007 no readiness/approval/FR-007-switch writes | Constitution V; Approach 3 | T017 (guard); SC-005 review | PARTIAL (see F1) |
| FR-008 no evidence-schema change | Approach 6 | T019 | COVERED |
| FR-009 two evidence systems distinct | Approach 6 | T020 | COVERED |
| FR-010 doctor engine-mode | Approach 5 | T014, T015 | COVERED |
| FR-011 orchestration-only deps, main package clean | Constraints; Approach (deps) | T001, T003 | COVERED |
| FR-012 generic/ASCII/redaction | Constraints | T008 (redaction); global | PARTIAL (see F4) |
| FR-013 doc reconcile | Approach 7 | T018 | COVERED |
| SC-001..SC-008 | mapped from FRs | T006-T021 | COVERED |

## Findings

### F1 (MEDIUM) -- FR-007 "no readiness/approval writes" has no dedicated negative test

FR-005/FR-007 forbid writing a readiness `status`, `Gate status`, `approvals[]`,
or the spec-133 FR-007 build-path switch. SC-005 states a reviewer can grep the
diff, and T017 guards against migration mutation, but no TASK writes a
mechanical negative test asserting the dbt-engine run produces ZERO changes to
readiness-truth fields (the spec-134 US3 pattern: assert `git diff` shows zero
changes to readiness fields after a run). The spec-134 test suite has exactly this
oracle for the migrations path; the dbt branch should inherit it. Recommendation:
add a task (or extend T019/T020) that asserts a dbt-engine run leaves every
readiness-truth field unchanged -- put the oracle ON the untrusted write path, not
adjacent to it. This is the highest-value gap because self-approval is the exact
failure the kit exists to prevent.

### F2 (MEDIUM) -- the engine configuration SOURCE is deliberately unspecified

spec.md and plan.md say the engine is read from "explicit committed configuration"
but do not name the file/key (plan.md Approach 1 explicitly defers it to
implementation time as a generic detail). This is defensible for a spec (WHAT, not
HOW) and keeps it generic per Principle VII, but it leaves a real ambiguity: an
implementer could place it in `mappings/<table>/`, in the orchestration project, or
in a new config file, each with different governance implications (a config in
`mappings/<table>/` is inside the human-reviewed working set; a config in the
orchestration project is not). Recommendation: the plan should at least CONSTRAIN
the location to the human-reviewed per-table working set so the engine choice
inherits mapping-gate review, or explicitly surface "where the engine flag lives"
as an open-for-human item. Currently it is neither answered nor surfaced -- a
genuine hole. This is governance-relevant, not merely a HOW detail: WHERE the flag
lives decides whether flipping to dbt inherits human review, so it ties directly
to the open-for-human item "whether flipping the build engine to dbt needs its own
named-human approval, and where it is recorded". Recommend the plan constrain the
flag to the human-reviewed per-table working set, closing both this hole and that
approval seam in one place.

### F3 (LOW) -- asset-name terminology: schema uses `bronze_table`, prose uses `bronze_<table>`

The committed evidence schema enumerates the asset name `bronze_table` (literal),
while spec 134 prose and this feature's prose use `bronze_<table>`. Feature 135
does not touch bronze, so this is inherited, not introduced -- but the analysis
notes it so a reader does not mistake the schema's `bronze_table` for a drift
introduced here. No action required for 135.

### F4 (LOW) -- redaction coverage asserted in prose, tested only indirectly

FR-012 requires every surfaced error (including dbt logs) to pass shared redaction.
T008 says the bridge runs surfaced text through redaction, but no task writes a
dedicated redaction fixture for the dbt-engine path (spec 133 has
`test_redaction.py` for the `seshat dbt` surface; the dagster bridge reuses
`seshat.dagster_adapter.redaction`). Recommendation: add a redaction assertion to
T012 (a dbt error containing a fake DSN/host must be absent from the dagster
record). Low severity because the redaction implementation is reused and already
tested on both adjacent surfaces.

### F5 (LOW, external/process) -- commit-subject format conflicts with the repo P2 rule

The authoring instruction mandates commit subjects of the form
`docs(spec-135): <artifact>`. The repo's static gate rule P2 forbids scoped
subjects (`docs(...)`), so `seshat check` reports a P2 error against these commits'
subjects (the finding cites the commit subject, not any file content). The spec
artifacts themselves pass the gate; this is a commit-hygiene finding that a human
would resolve at PR/merge time (this branch is a draft and is never merged by the
author). Recorded for transparency; it does not affect artifact correctness.

### F6 (INFO) -- live-drive compatibility is correctly flagged, not claimed

spec.md Assumptions, plan.md Constraints, and T021 all state that dagster-dbt
0.29.14 driving dbt-core 1.12.0 is unproven and that live drive stays
`[PENDING LIVE PROFILE]` (compile is `pending` in
`docs/operations/dbt-activation-status.yaml`). This is consistent across all three
artifacts and honestly deferred -- no fabricated confidence. No action.

## Terminology consistency (vs specs 133/134 and code)

- "governed selector", "accept-plan digest", "shadow schemas", "working set",
  "mapping gate" -- all used as in spec 133 and `seshat.dbt`. Consistent.
- "STOP edge", "HUMAN SEAM", "deferred boundary", "run-evidence", "execution words
  never pass" -- all used as in spec 134 and `gates.py`/`assets/__init__.py`.
  Consistent.
- "engine" / "build engine" / "engine mode" -- new vocabulary this feature
  introduces; used consistently across spec/plan/tasks. No collision with an
  existing term found.
- The evidence outcome vocabulary (`materialized|failed|skipped|blocked|deferred`)
  matches the committed schema exactly; the feature adds none. Consistent.
- Naming-vs-mechanism ("dagster-dbt engine seam" vs `seshat.dbt` execution path):
  the seam is NAMED for dagster-dbt and the documented contract says the build runs
  "via dagster-dbt", but the execution path deliberately routes through `seshat.dbt`
  (plan + accept-plan digest + shadow build), NOT native dagster-dbt asset wiring --
  because native wiring would bypass the accept-plan digest and the governed gate
  (spec 133 FR-023/FR-025). The `dagster-dbt` pin stays an inherited spec-134 pin,
  not a new execution-path dependency. plan.md Approach 3 now states this
  explicitly; recorded here so the framing (name) and the mechanism (path) are not
  read as a contradiction. Resolved coherence note, not an open finding.

## Contradiction check

- Internal: none found. spec/plan/tasks agree on the fail-closed default, the
  shadow-only constraint, the identical gate, the topology-unchanged constraint,
  and the open-for-human items.
- External (vs committed 133/134): the selectable-engine + shadow-only + migrations
  -default reading (spec.md Clarifications Q1/Q2) is the ONLY reading consistent
  with spec 133 FR-005 (shadow-only), FR-006 (migrations default), and FR-007
  (named-human switch). The alternative reading -- dbt becomes the real gold
  producer -- would contradict FR-005 and require the FR-007 switch this spec
  cannot make; spec.md explicitly rejects it and routes the switch question to
  open-for-human. No contradiction remains. Verified against the actual
  `_build_layer` body (migrations loop -> `seshat check`), the `dbt/dbt_project.yml`
  shadow-schema config, and `dbt/selectors.yml` (the fixed governed selector).

## Unstated-dependency check

- The feature depends on `seshat.dbt` exposing a callable plan+accept-plan+build
  path usable programmatically from the orchestration process. The committed
  `seshat.dbt.planning`/`gate`/`runner` modules exist; the plan assumes they are
  importable and composable without the `seshat dbt` CLI shell. This is
  reasonable (the CLI is a thin wrapper) but is an assumption the implementation
  must verify early (flagged implicitly by T008). Recommendation: T008 should
  begin by confirming the `seshat.dbt` programmatic entry points before wiring the
  bridge.
- F2 (engine-config location) is the one genuinely unresolved dependency.

## Summary

- Findings by severity: MEDIUM 2 (F1, F2), LOW 3 (F3, F4, F5), INFO 1 (F6).
- Blocking contradictions with committed governance: 0.
- Top items to address before implementation: F1 (add a readiness-no-write
  negative test on the dbt path) and F2 (constrain or surface where the engine
  flag lives, so the engine choice inherits human review).
- The core activation reading is sound and is the only one consistent with the
  committed spec-133 governance; the Principle-V judgment calls (build-path switch,
  dbt-as-default, real-gold writes, migration retirement) are correctly left
  UNANSWERED for a human.

RATIFICATION REQUIRED: human edit of spec.md Status line -- not performed.
