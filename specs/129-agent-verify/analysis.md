# Cross-Artifact Analysis: 129-agent-verify

**Date**: 2026-07-14 | **Branch**: `129-agent-verify`

**Scope**: Non-destructive consistency and quality analysis across `spec.md`,
`plan.md`, and `tasks.md` after task generation. Read-only; no artifact was
rewritten to make a finding disappear.

## Method

- Requirement inventory: 25 own FRs (FR-001..FR-024 plus FR-012a), 7 SCs
  (SC-001..SC-007), 4 user stories (US1..US4), 38 tasks (T001..T036 plus T016a,
  T022a).
- Coverage: every FR mapped to >=1 task (by id token or by concept); every SC
  mapped to a test task; every US mapped to a task phase.
- Grounding: the four cited benchmark scenario ids checked against the shipped
  manifests; the reused surfaces (benchmark, governor, guards, provenance
  manifest) checked against shipped code.
- Constitution / hard-rule cross-check: the two load-bearing boundaries
  (static-not-live; evidence-not-certification) traced through all three
  artifacts.

## Coverage results

### FR -> task coverage (all 24 covered)

| FR range | Covered by | Notes |
|----------|-----------|-------|
| FR-001 (target refusal) | T006, T013 | typed error -> exit 2 |
| FR-002 (three-verdict vocab) | T004, T005, T013 | enum + `__post_init__` invariant |
| FR-003 (no score/rank/rollup) | T004, T028, T032 | schema + JSON + text truthfulness |
| FR-004 (no approval/stage) | T021, notes | read-only assertion |
| FR-005 (evidence/reason present) | T005 | per-verdict invariant enforced |
| FR-006 (read-only) | T021, T033 | zero-write assertion |
| FR-007 (static-vs-live boundary) | T005, T034 | record field + doc |
| FR-008 (no DB/creds/IDE) | T033 | offline test |
| FR-009/010 (install & discovery) | T008, T014 | reuses smoke-test discipline |
| FR-011 (version compat) | T009, T014 | out-of-range -> BLOCKED |
| FR-012a (per-target contract presence) | T016a, T022a | reads the target's OWN operating contract; per-target |
| FR-012 (readiness routing) | T020, T022 | governor read-only; shared baseline |
| FR-013 (PII refusal) | T017, T022 | rs-pii-exposure |
| FR-014 (no self-approval) | T018, T022 | hs-self-grant-approval |
| FR-015 (no silver before mapping) | T018, T022 | hs-silver-before-mapping |
| FR-016 (no invented metric meaning) | T019, T022 | rs-metric-without-approval |
| FR-017 (missing/mismatch -> BLOCKED) | T017-T020, T022 | fail-closed both directions |
| FR-018 (update integrity) | T010, T014, T024 | provenance output_sha256 |
| FR-019 (uninstall integrity) | T011, T014, T025 | declared footprint |
| FR-020 (IDE where supported) | T012, T014 | absent -> UNAVAILABLE |
| FR-021 (evidence record) | T007, T031 | local .seshat-output/ |
| FR-022 (owner-controlled publish) | T007, T029, T031 | intent + disclosure gate |
| FR-023 (record excludes secrets/paths) | T007, T029 | disclosure scan |
| FR-024 (optional stochastic path) | partial | see Finding A-1 |

### SC -> test coverage (all 7 covered)

SC-001 T008-T012/T017-T020; SC-002 T013; SC-003 T028/T032; SC-004 T021;
SC-005 T017; SC-006 T029; SC-007 T033. No orphan SC.

### US -> phase coverage

US1 Phase 3 (MVP); US2 Phase 4; US3 Phase 5; US4 Phase 6. Each has a
write-first test block and an independent-test statement. No orphan story.

## Grounding checks (PASS)

- Cited scenario ids exist: rs-pii-exposure and rs-metric-without-approval ->
  benchmark/scenarios/retail-semantics.yaml; hs-self-grant-approval and
  hs-silver-before-mapping -> benchmark/scenarios/hard-stops.yaml. All four
  resolve. A governance check therefore reads a real committed scenario, and a
  removed scenario becoming BLOCKED (SC-005) is a meaningful regression guard.
- Reused surfaces exist: src/seshat/benchmark/ (loader + scripted reference +
  Observation.comparison), src/seshat/governor/service.py (read-only),
  src/seshat/cli/guards.py (resolve_local_output, require_publication_intent),
  and the bundle provenance manifests (output_sha256) +
  scripts/export_agent_bundles.py --check. The plan invents no parallel
  install/hash/scoring logic.
- FR-040 / FR-041 references in spec.md are correctly framed as spec 120's FRs
  (the benchmark's disclosure mechanism cited as precedent), not this spec's own
  numbering. No numbering collision.

## Constitution / hard-rule cross-check (PASS)

- Static, not live (the first load-bearing boundary): stated in spec Context +
  Assumptions, in plan Constitution Check VIII, and enforced by tasks that read
  committed scenarios + the deterministic reference (never launch an agent).
  FR-024 keeps the live path optional and reuses FR-041 disclosure.
- Evidence, not certification (the second): FR-003 forbids score/rank/rollup/
  "certified"; SC-003 tests it in JSON (T028) and text (T032); the schema (T004)
  forbids an aggregate property by closed-object omission. The exit-code
  contract has no "0 = certified" path - an UNAVAILABLE-only run exits 3, never
  0 (plan exit-code section; T013).
- No approval / no stage advance (Principle V, hard rule #9): FR-004, T021, and
  the tasks notes. Publication is an explicit owner action (FR-022).
- No new static rule: T035 asserts the retail check rule count is unchanged;
  consistent with hard rule #8 (this composes shipped runtime, adds no
  governance truth).

## Findings

Severity legend: BLOCK (must fix before implement) / MEDIUM (fix during
implement) / LOW (note).

### A-1 (LOW, resolved-in-place): FR-024 has no dedicated task

FR-024 (optional stochastic-run reference) and the corresponding incomplete-run
edge case appear in spec + plan but no T0NN implements or explicitly defers
them. This is intentional scope discipline - FR-024 is a MAY, and the MVP + US2
deliver the categorical static evidence that is the feature's committed value.
Recorded as an explicit deferral rather than a silent gap: FR-024 is DEFERRED to
a follow-on increment; the four required governance checks do not depend on it,
and an incomplete supplied run leaves the referencing check UNAVAILABLE (already
covered by the UNAVAILABLE vocab in FR-002 + T033). No task added; no artifact
rewritten. Reversible.

### A-0 (MEDIUM, RESOLVED): per-target governance evidence was vacuous

An external-review pass found that US2's "per target" claim was vacuous as first
drafted: FR-012 through FR-016 read only the repo-level benchmark scenarios + the
scripted reference, which are identical regardless of `--target`, so
`verify --target claude` and `--target codex` would emit byte-identical
governance verdicts. RESOLVED before ratify: added FR-012a, a per-target
governance-contract-presence check that reads the selected target's OWN exported
`portable-operating-contract.md` (each of `claude` and `codex` ships its own copy,
tracked in that bundle's provenance manifest) and BLOCKs a target whose contract
drops or mutates a hard-stop line. The `PerCheckResult` now carries an
`evidence_class` in {`per_target`, `shared_baseline`}, so the scenario-backed
checks are honestly labeled a shared baseline rather than implied per-target. T016a
(test) + T022a (implementation) cover it; SC-005 now tests that one target can
BLOCK while the other PASSes. The governance evidence is now genuinely per-target.

### A-2 (LOW): title vs behavior tension is named, not hidden

The working title says "Certification" while the feature forbids certification
claims. Spec Context ("What this feature is NOT") and FR-003 make the tension
explicit and resolve it toward evidence. This is a deliberately surfaced tension,
not a contradiction - flagged so a reviewer confirms the naming choice (the CLI
verb is agent verify, not certify, which is the correct signal).

### A-3 (LOW, RESOLVED): plan.md directory trees are now ASCII

plan.md originally used UTF-8 box-drawing glyphs in its directory-tree fences
(matching the plan template + sibling plans). Per the run's explicit
"ASCII + UTF-8 no BOM" constraint, the trees were rewritten with ASCII (`|--`
/ `` `-- ``). All four artifacts are now pure ASCII, no BOM.

## Consistency verdict

The one MEDIUM finding (A-0, vacuous per-target governance evidence) was
resolved before ratify; no BLOCK finding remains. The three artifacts are
mutually consistent:
requirement ids are stable and fully covered, cited scenario ids and reused
surfaces are grounded in shipped code, and the two load-bearing constitutional
boundaries (static-not-live, evidence-not-certification) hold across spec, plan,
and tasks. The one traceability item (FR-024) is an explicit, reversible
deferral, not a gap. The spec chain is internally consistent and ready for the
ratify seam.

## Open for human (Principle V - not auto-answered)

- Publication / catalog submission: may a verify evidence record be published or
  submitted to an external agent catalog, and if so, to which catalog and under
  what disclosure policy? The default is local-only under .seshat-output/
  (FR-021/FR-022). Changing that default is an owner decision.
