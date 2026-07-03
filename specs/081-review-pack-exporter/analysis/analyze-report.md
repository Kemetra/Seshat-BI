# Specification Analysis Report: Review Pack Exporter (081)

**Feature dir**: `specs/081-review-pack-exporter/`
**Artifacts analyzed**: spec.md, plan.md, tasks.md, data-model.md, research.md, quickstart.md,
contracts/ (markdown, json-schema, compact-ci-summary, backwards-compat-example).
**Date**: 2026-07-03
**Mode note**: The `speckit-analyze` skill was invoked. Its PowerShell prerequisite check
(`.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks`)
initially failed on the branch-name heuristic (the worktree branch is `spec/review-pack-exporter`,
not the `NNN-slug` the script expects), then PASSED once run with `SPECIFY_FEATURE=081-review-pack-exporter`,
resolving `FEATURE_DIR` to this dir with `AVAILABLE_DOCS` = research.md, data-model.md,
contracts/, quickstart.md, tasks.md. The analysis below was then performed directly against the
three core artifacts (all held in full context). This file is written to
`specs/081-review-pack-exporter/analysis/analyze-report.md` per the assigning task's
manual-fallback instruction (kept inside the feature spec dir); it is a read-only report and
modifies no spec/plan/tasks file.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| O1 | Overlap (B2) | LOW (resolved) | spec.md L21-26; research.md 1.1; data-model.md 3.1 | Exporter's JSON format vs. B2's shipped `retail check --format json`. | Distinct: B2 emits `{"findings":[...], "exit_code"}` for ONE checker run; 081 wraps a multi-section PACK and EMBEDS the same `Finding` field shape rather than redefining it (FR-009). No competition; the embedding is a deliberate anti-duplication move. Keep as-is. |
| O2 | Overlap (J1) | LOW (resolved) | spec.md L27-36; research.md 1.2 | Exporter's Markdown vs. J1's shipped `approval-evidence-pack` Markdown. | Distinct: J1 COMPOSES (reads 4 scattered sources -> 1 doc); 081 SERIALIZES (takes 1 given pack -> N formats). FR-001 forbids 081 reading any source artifact. Opposite halves of one pipeline; J1 may optionally call 081 later (out of scope). Keep. |
| O3 | Overlap (K1) | MEDIUM (resolved, watch) | spec.md L84, L336-343; research.md 1.4; tasks.md "Out of scope" | Exporter vs. HORIZON idea K1 (gate-observability-rollup). | Distinct axes: 081 = one pack -> many formats (formatter); K1 = many gates' findings -> one ledger (aggregator). K1 is HORIZON-gated on "a third emission format stabilizing"; 081 is NOT that third format (it renders pack content, it is not a new gate emitting findings) and does not unblock K1. Correctly named in spec + tasks Out-of-scope. No action; flagged for a human reviewer to confirm the axes read as genuinely orthogonal. |
| O4 | Overlap (LVR) | LOW (resolved) | spec.md L37-41; research.md 1.3 | Exporter vs. LVR (`readiness_evidence.py`). | Distinct: LVR PRODUCES a `gold_ready` block dict (a pack-shaped input); 081 SERIALIZES such a block. 081 does not re-run or wrap LVR's derivation. Keep. |
| C1 | Fake-confidence risk | HIGH (mitigated, must-verify) | spec.md FR-005/FR-006/SC-003; data-model.md 6; contracts/compact-ci-summary.md; tasks.md T011/T016 | The compact CI/PR summary is the single place a numeric score or "N of M" tally could smuggle in as a verdict, violating hard rule #9. | Mitigation is present and concrete: FR-005/FR-006 forbid it in words; data-model.md 6 excludes scoring/count fields; the contract file shows FORBIDDEN negative examples; tasks.md T016 is an explicit negative test. This is the #1 thing the later implementation review must re-verify. Adequately specified; no spec change needed. |
| C2 | Ambiguity (compact "N of M") | RESOLVED (was MEDIUM) | spec.md US3 Independent Test; spec.md FR-006; contracts/compact-ci-summary.md; tasks.md T016 | An earlier draft's compact format carried a "(1 of 2 sections at this status)" parenthetical and an "and N more" marker -- both `\d+ of \d+`-shaped strings sitting on the hard-rule-#9 line. | RESOLVED by removing every numeric section count from the compact format: the REQUIRED shape's closing pointer is now the digit-free "See full pack for detail."; FR-006 now forbids a numeric section count "in ANY form ... anywhere"; the US3 Independent Test dropped the "and N more" marker; and T016 was widened to assert no `\d+ of \d+`, no `%`, no `\d+/\d+`, and no maturity adjective, anywhere in compact output, across every US3 fixture. Which sections triggered a status is now conveyed (if wanted) by NAMING sections, never by a count. No residual ambiguity. |
| U1 | Underspecification | LOW | spec.md FR-002; plan.md function names; data-model.md | Exact function signatures (`to_markdown`/`to_json`/`to_compact_ci_summary`) live in plan.md/tasks.md, not spec.md. | Correct by design -- spec.md is intentionally implementation-free (Content Quality checklist). The signatures appear in plan.md Structure and tasks.md T021-T023. No gap. |
| I1 | Inconsistency (status count) | LOW (explained) | spec.md FR-004; data-model.md 1 | "five status tokens" (request) vs. "four readiness-model tokens" vs. the 7-row union table. | Not a defect: the Assumptions + data-model.md 1 table reconcile the vocabularies explicitly as a UNION with pass-through, precisely because unifying them would be a Principle-V judgment call. Terminology is consistent across files. Keep. |
| I2 | Inconsistency (analyze filename) | LOW | plan.md ("analysis.md ... or analysis/analyze-report.md"); this file's actual path | Plan lists `analysis.md` as the stage-5 output but the report was written to `analysis/analyze-report.md`. | Cosmetic; plan.md already names both as acceptable. This report documents the chosen path. No action required. |
| CG1 | Coverage gap check | NONE | tasks.md T003-T034 vs. FR-001..FR-017 / SC-001..SC-007 | Every FR and buildable SC maps to at least one task (see Coverage table). | No uncovered requirement. |
| OG1 | Over-governance risk | LOW (avoided) | spec.md L43-46; plan.md Constitution Check; tasks.md T025/T033 | Risk that 081 adds a `retail check` rule or a new readiness stage (which the constitution would then have to carry). | Explicitly avoided: FR-043-46 and plan/tasks state NO new rule, NO new stage, rule count unchanged (T025/T033). This keeps the feature a library, not a gate. Good. |
| DEP1 | Dependency conflict | NONE | plan.md Technical Context; FR-016 | New dependency risk (YAML). | Avoided: JSON is stdlib; YAML explicitly deferred (FR-016). No new dependency. Consistent with the task's "no new dependencies" boundary. |
| LV1 | Live-validation-claim risk | NONE | spec.md SC-001; plan.md "Repo-only vs live-DB" | Risk of an unearned live-DB / live-pass claim. | None present: the feature is entirely repo-local, pure-function; no DSN, no `db` extra, no `[PENDING LIVE PROFILE]` boundary. No live claim anywhere. |
| HS1 | Hidden impl scope | NONE | tasks.md boundary block; STOP T035 | Risk that spec-work quietly did implementation. | None: no `src/` file created in this worktree (verified separately by `git status`); tasks.md is explicitly the LATER-PR task list, forbids `git add -A`, and STOPs before commit/push/PR. |

## Coverage Summary Table

| Requirement | Has Task? | Task IDs | Notes |
|---|---|---|---|
| FR-001 (no source reads) | Yes | T027 | static grep for source-path/DB/network imports |
| FR-002 (three formats) | Yes | T021, T022, T023 | one impl task per format |
| FR-003 (verbatim status) | Yes | T005, T012, T003/T008 | pass-through asserted per format |
| FR-004 (recognized union) | Yes | data-model.md 1; T007, T012 | union documented + unrecognized-token tests |
| FR-005 (no score) | Yes | T011, T016 | JSON key-pattern test + compact negative test |
| FR-006 (worst-status, no ratio) | Yes | T013, T017 | worst-rank + multi-section-tie tests |
| FR-007 (schema_version + additive rule) | Yes | T008, T018 | top-level field + compat pair |
| FR-008 (tolerate unknown fields) | Yes | T018; quickstart.md consumer section | documented + demonstrated |
| FR-009 (embed Finding shape) | Yes | T009 | round-trip vs. `Finding.to_dict()` |
| FR-010 (no business-rule authorship) | Yes | data-model.md 3 `note`; T026 | rendered verbatim; C086 grep |
| FR-011 (no DB/PBIP/adapter) | Yes | T027 | static grep |
| FR-012 (no approval/pass write) | Yes | T027, T028 | no write surface; frozen inputs |
| FR-013 (deterministic Markdown) | Yes | T006 | byte-identical double render |
| FR-014 (generic, no C086) | Yes | T026 | grep module+tests+contracts |
| FR-015 (ASCII/UTF-8/short paths) | Yes | authored artifacts; T029 ruff | ASCII throughout |
| FR-016 (YAML deferred) | Yes | tasks.md Out-of-scope | no YAML task; documented |
| FR-017 (unrecognized token visible) | Yes | T007, T012 | flagged per format |
| SC-001 (three formats, no source) | Yes | T003/T008/T013 + T027 | |
| SC-002 (100% verbatim tokens) | Yes | T005, T012 | |
| SC-003 (0 score/tally) | Yes | T011, T016 | |
| SC-004 (backwards compat) | Yes | T018 | worked pair |
| SC-005 (byte-identical Markdown) | Yes | T006 | |
| SC-006 (0 C086 specifics) | Yes | T026 | |
| SC-007 (Finding round-trip) | Yes | T009 | |

Coverage: 17/17 FR + 7/7 SC mapped to >=1 task = **100%**.

## Constitution Alignment Issues

None. Plan.md's Constitution Check maps Principles I, IV, V, VII, VIII, IX, hard rule #9, and
the B1/B3 import-boundary precedent, all PASS. The two constitution surfaces most relevant to
this feature -- Principle V (no self-grant / no judgment) and hard rule #9 (no fabricated
confidence) -- are enforced structurally (the exporter has no write surface for `approvals[]`
and no scoring field in its data model), not merely asserted.

## Unmapped Tasks

None. Every task T001-T035 maps to a requirement, a documented risk mitigation, a validation
step, or the explicit STOP boundary. T031/T032 (documentation) are correctly marked optional /
maintainer-choice and do not gate shipping.

## Why the exporter is a distinct FORMATTER layer (the required overlap argument)

The three named neighbours each occupy a different point in a produce-then-serialize pipeline;
081 is the serialize half only:

- **B2** answers "what did `retail check` find?" -> a findings+exit-code JSON for ONE run. 081
  does not run any check; it EMBEDS B2's finding field shape inside a pack so a B2 consumer
  recognizes it (reuse, not re-implementation).
- **J1** answers "what evidence does a human need to sign gate X for table Y?" -> reads four
  scattered committed sources and composes ONE Markdown doc. 081 reads NO source artifact
  (FR-001); it renders a pack it is HANDED. If anything, J1 is a potential CALLER of 081, never
  a thing 081 duplicates.
- **LVR** answers "what readiness block does a live validate run imply?" -> derives a
  `gold_ready` dict. 081 serializes such a dict; it does not derive it.
- **K1** answers "across all gates, what is the union of findings?" -> aggregates many gates
  into one ledger, and is HORIZON-gated on a third stable emission format. 081 does not
  aggregate across gates and is not a gate emitting findings; it is orthogonal (one pack ->
  many formats) and neither builds nor unblocks K1.

The distinctness is enforced, not just claimed: FR-001 (no source reads), FR-009 (embed, don't
redefine, B2's shape), and the "no new gate / no new rule / no new stage" posture (plan.md
Constitution Check; tasks.md T025/T033) are the concrete guardrails that keep 081 from drifting
into any neighbour's role.

## Metrics

- Total functional requirements: 17 (FR-001..FR-017)
- Total buildable success criteria: 7 (SC-001..SC-007)
- Total tasks: 35 (T001..T035)
- Coverage (requirements with >=1 task): 100%
- Ambiguity count: 0 (C2 was MEDIUM; RESOLVED by removing all numeric section counts from the
  compact format -- see C2 row)
- Duplication/overlap count: 4 neighbours analyzed (O1-O4), all resolved as distinct
- Critical issues count: 0
- Highest live risk: C1 (fake-confidence in the compact summary) -- mitigated in spec+data-model
  +contract+tests; must be re-verified at implementation review.

## Next Actions

- No CRITICAL, HIGH-unmitigated, or blocking issue, and no residual ambiguity (C2 resolved).
  The spec/plan/tasks chain is internally consistent, fully covered, and constitution-aligned.
- Recommend the later implementation PR treat tasks.md T016 (the widened fake-confidence
  negative test: no `\d+ of \d+`, no `%`, no `\d+/\d+`, no maturity adjective, anywhere) as a
  required, non-skippable gate -- it is the concrete enforcement of the C2 resolution.
- No `/speckit-specify`, `/speckit-plan`, or `/speckit-tasks` re-run is needed; the artifacts do
  not require remediation edits.

## Remediation applied

The single MEDIUM ambiguity (C2 -- a numeric section count in the compact format) was not left
as a preference call: it was REMOVED from the compact contract, FR-006, the US3 Independent
Test, and the T016 guard test (see the C2 row for exact edits) before finalizing this chain, so
the shipped artifacts are faithful to hard rule #9 rather than flirting with it. No other
remediation is needed (0 CRITICAL, 0 HIGH-unmitigated, 0 residual ambiguity). This analysis
itself modified no spec/plan/tasks logic beyond that C2 fidelity fix.
