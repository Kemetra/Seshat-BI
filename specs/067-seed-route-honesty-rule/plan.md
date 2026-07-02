# Implementation Plan: Seed-Layer Route Honesty Rule

**Branch**: `067-seed-route-honesty-rule` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/067-seed-route-honesty-rule/spec.md`

## Summary

Extend the existing `A1` route-resolution rule (`src/retail/rules/routes.py`) to
accept a third `status` value, `seed`, and verify it against tracked-file evidence
exactly as it already verifies `built`: every target of a `seed` route MUST resolve
as a tracked file, else ERROR. Add the `seed` token to the `docs/routing/routes.yaml`
header-comment vocabulary so the manifest and the rule agree. The change adds NO new
rule id, triggers NO wiring seam, and requires NO manifest/golden regen. `A1` never
promotes a `seed` route to `built`; the seed -> built promotion criterion is a
Principle-V human call left open (FR-016).

## Technical Context

**Language/Version**: Python 3.13 (worktree + CI); 3.12 also present. Stdlib-only for
the `retail check` core chain; `yaml` imported LAZILY inside the `A1` handler (no new
dependency).

**Primary Dependencies**: none added. Reuses `@register`, `RuleContext`
(`tracked_files`, `repo_root`), `Finding`, `Severity` -- all already imported by
`src/retail/rules/routes.py`.

**Storage**: N/A -- static read over committed text (`docs/routing/routes.yaml`).

**Testing**: pytest, `-m unit`. New/extended fixtures under `tests/unit/` for the
`seed` status; existing `A1` `built`/`planned` tests must stay green (no regression).

**Target Platform**: CLI gate (`retail check`) on Linux/Windows dev + CI.

**Project Type**: Single project (library + CLI) -- the `retail` rule package.

**Performance Goals**: N/A -- a single YAML parse over ~29 routes; unchanged from
today's `A1` cost.

**Constraints**: static-first, stdlib-only core, read-only, fail-loud (never vacuous
green), categorical (no numeric score), ASCII/UTF-8-no-BOM, generic (no C086 literal).

**Scale/Scope**: one accepted-status value added to one `frozenset`; one branch of
the per-route loop extended; one manifest header-comment updated; fixtures + tests.
No new module, no new rule id.

## Constitution Check

*GATE: must pass before and after design. This feature is an in-place vocabulary
extension of an already-shipped static rule; the constitution gates apply as
non-regressions.*

- **Principle I (Agent-First, Gate-Enforced)**: PASS -- `seed` verification is an
  enforced non-zero exit in `retail check` via the existing `A1` Finding path; a
  broken `seed` route fails the gate, fail-closed. Not prose advice.
- **Principle V (Agent Stops at Judgment Calls)**: PASS -- `A1` VERIFIES a declared
  `seed` status against file existence; it NEVER auto-promotes seed -> built or
  self-grants a status. The promotion criterion (FR-016) is left as an open
  `[NEEDS CLARIFICATION]` for a human, not invented.
- **Principle VII (C086 Is An Example, Not The Schema)**: PASS -- the `seed` token,
  the rule logic, and the fixtures are generic routing machinery; no pharmacy/C086
  route target, KPI name, or dataset path is baked in. C086 cited only as an
  external instance if at all.
- **Principle VIII (Static-First Governance)**: PASS -- read-only over committed
  text; lazy `import yaml` preserved; missing/malformed manifest fails LOUD; never a
  vacuous green.
- **Rule IX (ASCII/UTF-8 no BOM)**: PASS -- all authored artifacts use `--`/`->`,
  no glyphs.
- **Hard rule #9 (no fabricated score/readiness)**: PASS -- categorical Finding
  only; no numeric confidence introduced; the drafting agent grants no readiness pass.
- **No deferred capability assumed**: PASS -- no F016 Power BI Execution Adapter, no
  F031-F033 runtime; static-check-only, ships no executor.

No violations -> Complexity Tracking table is empty (omitted).

## Project Structure

### Documentation (this feature)

```text
specs/067-seed-route-honesty-rule/
|-- spec.md               # feature specification (stages 2-3)
|-- plan.md               # this file (stage 4)
|-- tasks.md              # dependency-ordered tasks (stage 4)
|-- analysis.md           # cross-artifact consistency report (stage 5)
|-- plan-review.md        # adversarial plan-review (stage 6)
`-- checklists/
    `-- requirements.md   # spec quality checklist (stage 2)
```

No `research.md`, `data-model.md`, `contracts/`, or `quickstart.md` are produced:
there is no unknown to research (the seam is confirmed in the grounding), no data
model (a status enum widened by one value), and no external contract (a static rule).

### Source Code (repository root)

```text
src/retail/rules/
`-- routes.py                 # A1: extend _VALID_STATUS + the per-route status branch (EDIT)

docs/routing/
`-- routes.yaml               # add `seed` to the header-comment status vocabulary (EDIT)

tests/unit/
`-- test_rules_routes*.py     # add `seed` acceptance/rejection cases (EDIT or NEW fixture)
```

Untouched (verified non-regression, NOT edited):
`tests/unit/test_rules_wiring.py` (`EXPECTED_RULE_IDS`), `docs/rules/rules-manifest.json`,
the severity-posture golden fixture, `src/retail/rules/routes_coverage.py` (A3),
`src/retail/rules/status_claims.py` (SC1).

**Structure Decision**: Single-project `retail` rule package. The feature is a
minimal in-place edit to one existing rule module + one manifest header + tests. No
new module, directory, or rule id is introduced (FR-008); this is the crux of the
"extend A1 in place" scope decision (spec C4).

## Design notes (implementation-shaping, not implementation)

- **`_VALID_STATUS`**: widen `frozenset({"built", "planned"})` ->
  `frozenset({"built", "planned", "seed"})`. The existing unknown-status guard then
  accepts `seed` and continues to reject anything else, listing all three values.
- **Per-route existence branch**: the current loop treats `built` as "must resolve"
  and `planned` as "must NOT resolve". Add `seed` to the same "must resolve" arm as
  `built` (a `seed` target that does not resolve -> ERROR), and add `seed` to the
  same "no targets" guard as `built` (a `seed` route with no targets -> ERROR). Keep
  the `planned`-resolves-stale branch exactly as-is. Craft the `seed` ERROR messages
  to name the `seed` status (so a maintainer sees "seed" not "built" in the locator
  text), but reuse the same existence logic.
- **No promotion logic**: the rule adds NO code that compares a `seed` surface's
  content/count against a completeness threshold. Promotion is out of scope (FR-016);
  attempting it would be inventing the Principle-V criterion the rule must not decide.
- **Manifest vocabulary**: update the `status  -- built | planned` header comment in
  `docs/routing/routes.yaml` to `built | planned | seed` and add the one-line meaning
  ("seed -> target exists but is only an initial-seed surface; every target must
  resolve, same as built"). Do NOT flip any existing route to `seed` (FR: out-of-scope
  non-goal) -- the feature adds the capability, not a per-route reclassification.
- **A3 non-regression**: `routes_coverage.py` reconciles id SETS, not statuses; a
  `seed` route contributes its `id` identically to a `built` one. Verify with a
  fixture that includes a `seed` route -- do not merely assume.

## Phasing

- **Phase 0 (research)**: none needed -- seam confirmed by grounding
  (`_VALID_STATUS`, `check_routes_resolve()`, `routes.yaml` all opened).
- **Phase 1 (design)**: captured in Design notes above; no separate artifacts.
- **Phase 2 (tasks)**: see `tasks.md` -- TDD-ordered (failing `seed` tests first),
  then the two-line rule edit, then the manifest header, then the A3/wiring
  non-regression assertions.
