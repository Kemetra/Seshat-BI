# Adversarial Plan-Review: Rule Registry Snapshot Manifest (golden-file rule inventory)

**Date**: 2026-06-29 | **Branch**: `043-rule-registry-snapshot-manifest-golden`
**Reviewer stance**: single default-adverse skeptic, READ-ONLY (reports fixes, never edits).
**Scope**: spec.md, plan.md, tasks.md across five axes (hidden-principle-violation,
assumes-deferred-capability, c086-leak, fabricated-confidence, over-scope).

## Axis 1 -- hidden-principle-violation

### Finding R1 (HIGH): FR-009/T013 re-introduces the very drift defect the feature exists to kill

FR-009 / T013 say to "correct the stale '26 rules' on constitution lines 377+381 to MATCH the
live registry." Taken literally that means writing the literal "33" into the constitution prose.
That is a fresh HAND-TYPED count -- and NOTHING guards it: the golden snapshot test guards
manifest-vs-registry, NOT constitution-prose-vs-registry. The instant a 34th rule lands, the
constitution body is stale again -- the identical failure mode that already produced "26" -> the
header's own "27" note -> today's reality of 33. The feature would ship its own anti-thesis, and
it brushes hard rule #9's spirit (no restated count masquerading as truth).

EVIDENCE (repo-grounded fix already exists): `docs/glossary.md` line ~100 states the repo rule
verbatim -- "elsewhere refer to 'the static retail check gate' by name rather than restating a
count." The glossary is the ONE place that carries the number (kept in sync with the rule table);
every other location refers BY NAME. The constitution body is an "elsewhere."

FIX: Do NOT write "33" into the constitution body. Reword the two live-body lines (377+381) to
refer to the static `retail check` gate / the generated manifest as the authoritative inventory,
WITHOUT a bare literal count -- matching the glossary's own established rule. Update spec FR-009
and task T013 to say "remove the bare count and reference the manifest/gate by name," not "set it
to the live number."

### Finding R2 (HIGH): the constitution edit omits the required Sync-Impact / version-bump protocol

`.specify/memory/constitution.md` is governed by a versioned amendment protocol (its header is a
"Sync Impact Report" with explicit "Version change: X -> Y" entries). The header EVEN flags this
exact stale count as deferred: "pre-existing stale counts ... Not corrected here to avoid scope
creep ...; flagged for a follow-up patch." This feature IS that follow-up patch -- but FR-009/T013
prescribe editing the body with NO Sync-Impact Report entry and NO version bump. As written it
would land an un-versioned amendment, inconsistent with the file's own governance.

FIX: If any count-bearing constitution text changes, T013 MUST also add a Sync-Impact Report
entry (PATCH/MINOR -- a clarification/factual correction, no principle redefined) and bump the
version. Fold this into the same resolution as R1.

## Axis 2 -- assumes-deferred-capability

PASS. The spec, plan, and tasks all explicitly exclude F016 (Power BI Execution Adapter) and the
F031-F033 spec-only runtimes, and require stdlib-only with no DB/network/Power BI dependency
(FR-008, plan Constitution Check, tasks Out of Scope). Nothing assumes a deferred surface.

## Axis 3 -- c086-leak

PASS. The manifest carries exactly `id` + `title` from `RegisteredRule` (FR-002, Q3, T009). No
per-table grain keys, billing codes, segments, or pharmacy/PII specifics can flow in. The guard
is stated in three artifacts. Generic-only is preserved.

## Axis 4 -- fabricated-confidence

PASS. The manifest is an EXACT inventory (id+title equality), never a numeric confidence/health
score (FR-002, hard rule #9). Status stays "Draft" in the front-matter; no artifact writes
"Ratified" and none self-grants a readiness pass. No fabricated metric anywhere.

## Axis 5 -- over-scope

PASS (with one observation). The core is correctly minimal: a thin generator subcommand, one
golden JSON, one snapshot test, NO new `@register`, NO new `EXPECTED_RULE_ID` (FR-007, T008).
`retail manifest --check` mode is excluded as YAGNI. US3 (constitution/glossary/roadmap count
cleanup) does broaden the slice beyond pure manifest+test, but it is the motivating defect and is
bounded to count references; acceptable. NOTE: with the R1 fix (refer-by-name instead of writing
a literal), US3 actually SHRINKS -- it removes counts rather than restating them -- which is the
right direction.

## Minor note (does not affect verdict)

- M1 (LOW): Edge-case list promises "manifest missing -> fail closed with a message telling the
  developer to run the generator (not a silent skip)." Confirm T006 explicitly handles the
  pre-T011 missing-file case as an ACTIONABLE failure, not an uncaught `FileNotFoundError`. Add a
  half-line to T006 to make this explicit.

## Cross-artifact-pass observation

The Stage-5 analyze pass returned CLEAN, but it should have caught R1 (the spec contradicting its
own anti-drift thesis via FR-009). Coverage-mapping found every FR mapped to a task; it did not
interrogate whether FR-009's chosen METHOD undermines the feature's purpose. Recorded here.

## Verdict

Verdict: PASS-WITH-NOTES

**PASS-WITH-NOTES.** All artifacts present (spec, plan, tasks, analyze). No CRITICAL. Two HIGH
findings (R1, R2), both on the SAME constitution-edit step (FR-009/T013) and both fixable by
rewording -- they do not block ratify but MUST be resolved before implementation: the constitution
body should reference the manifest/gate BY NAME (no new literal count, per the glossary's own
rule) and, if count-bearing text changes, carry a Sync-Impact entry + version bump. The manifest
+ snapshot-test core (US1/US2) is sound, generic, static-first, and fabrication-free. The single
open Principle-V item (roadmap promotion / F-number) is correctly left for the human owner.
