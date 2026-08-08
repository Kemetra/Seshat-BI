# Ratify ledger: Spec Kit template fork removal

**Spec**: `specs/151-speckit-fork-removal`
**Branch**: `151-speckit-fork-removal` (worktree; nothing on `main`)
**Prepared**: 2026-08-08
**Status**: AWAITING RATIFICATION -- not ratified, not implemented

## What is being asked for

Authorization to relocate Seshat's spec-status policy out of an
upstream-managed Spec Kit template and into a Seshat-owned authority, then
return the template to upstream.

**Spec Kit itself is not removed, reduced, or upgraded.** All 14 `speckit-*`
skills, all 5 PowerShell scripts, and 4 of 5 templates are untouched. The single
changed file, `.specify/templates/spec-template.md`, changes by having 11
Seshat-added lines deleted and upstream's content restored.

## Why this is not an eleven-line change

The deletion is trivial. What the deletion breaks is not:

| Finding | Measured |
| --- | --- |
| The vocabulary has no home in shipped code | zero hits for `ratified`/`superseded` under `src/seshat/` |
| Its only code declaration is inside the test that checks it | `test_spec_status_vocabulary.py:27` |
| That test reads the template to learn the policy it then validates | lines 24, 66-72 -- circular |
| ADR-0019 is ~86% unenforced across the corpus | 110 of 139 specs outside the vocabulary |
| Two ratification grammars already disagree | `implement.js` H3 REFUSES the merged `specs/150-dbt-evidence-consumer` |
| A third grammar instructs the wrong form | `idea-to-spec.js` |
| The restored template seeds an invalid status | `**Status**: Draft`, copied verbatim by the scaffold |

## Decision record

| # | Decision | Made by | Basis |
| --- | --- | --- | --- |
| 1 | Reject patch-preservation machinery | **owner**, 2026-08-08 | Spec Kit owns Spec Kit; Seshat owns Seshat governance |
| 2 | Remove the fork rather than relocate it | **owner**, 2026-08-08 | stated architecture |
| 3 | Verdict is REQUIRED | agent, from repo evidence | fork present; no Seshat-owned authority exists |
| 4 | Authority is a library, not a rule or state machine | agent | ADR-0019 §3 says no new `seshat check` rule; a state machine would duplicate the readiness spine |
| 5 | Do NOT enforce corpus-wide in this feature | agent, from adversarial round 1 | 110 of 139 specs would fail; that is a separate decision |
| 6 | Reconcile all three grammars, not two | agent, from adversarial round 1 | `idea-to-spec.js` is the producer of the instruction |

## What changed during review

One independent adversarial pass found five confirmed problems, each verified
directly before acceptance. Full record in `plan-review.md`:

1. The proof gate was **vacuous** -- the old test inspects ~10 of 139 specs, so
   "still rejects everything it rejected" proved nothing.
2. US2 as drafted would have **reddened CI on 110 committed specs** with no
   migration task.
3. The restored template **seeds an invalid status**, so every new spec would
   start life broken.
4. A **third grammar** (`idea-to-spec.js`) was missing from the dependency table.
5. The obvious H3 widening makes `**Status history**: draft` match the draft
   regex, **wrongly refusing correctly ratified specs**.

None was found by self-review.

## Pre-ratification verification

| Command | Exit | Result | Classification |
| --- | --- | --- | --- |
| `git status --short` | 0 | one untracked spec dir | PASS |
| `git diff --stat HEAD` | 0 | empty -- no tracked file modified | PASS |
| `python -m seshat.cli check` | 0 | 1 pre-existing RS1 warning in `mappings/` | PRE-EXISTING -- branch touches no `mappings/` file |
| `python scripts/export_agent_bundles.py --check` | 0 | bundles match reviewed inputs | PASS |
| corpus census script | 0 | 139 specs / 20 canonical / 110 outside / 9 no line / 10 `_IMPLEMENTED` | PASS (measurement) |
| H3 regex executed against spec 150 | 0 | `H3_RATIFIED=false`, `H3_DRAFT=false` -> REFUSE | PASS (defect reproduced) |
| naive-widening regression probe | 0 | `**Status history**: draft` matches widened draft regex | PASS (defect reproduced) |

No test suite was run for implementation behavior, because no implementation
exists. Reporting green implementation gates here would be false.

## What ratification authorizes

Tasks T001-T015 in `tasks.md`, touching: a new authority module under
`src/seshat/`, `tests/unit/`, `.claude/workflows/{implement,idea-to-spec}.js`,
`.specify/templates/spec-template.md` (restoration only),
`.specify/integrations/speckit.manifest.json` (one entry),
`docs/capabilities/ownership-audit.md` (lines 217-218 only), and a pointer in
ADR-0019.

## What ratification does NOT authorize

Removing, reducing, or upgrading Spec Kit. Corpus-wide status enforcement or
migration of the 110 non-conforming specs. Re-vendor automation. A provenance
registry. The five `speckit-git-*` skills. A broad drift checker. Line-ending
normalization. Git or CI configuration changes. Dependency changes. Phase 9+.
Upstreaming to GitHub Spec Kit. Rewriting the historical audit beyond lines
217-218. Push, PR, merge, or publication.

## Decisions taken under delegation (2026-08-08)

The owner delegated the recommended choices. Both former open questions are now
DECIDED in the spec; the owner may overrule either at ratification.

| Question | Decision | Reason |
| --- | --- | --- |
| FR-025 -- the seeded upstream `Draft` | **Normalize post-scaffold** | Accepting it as a synonym would contradict FR-006, turning one testable rule into a rule plus a permanent exception. Normalization keeps FR-006 unqualified. |
| H3 reconciliation | **Widen additively** | Cannot invalidate an already-ratified spec; the alternative pulls ~40-spec corpus migration into a feature FR-023 keeps it out of. |

A contradiction introduced while fixing the scaffold trap was also resolved:
FR-006 ("values outside the vocabulary MUST be rejected") conflicted with the
former FR-025 option to accept capital `Draft`, which IS outside the vocabulary.
FR-006 now states it carries no exception list, and FR-025 resolves the case by
normalization instead.

"Is this worth doing now?" is not a separate question: doing it now and
deferring produce the same immediate state, since the package awaits
ratification either way.

## The one thing the agent cannot do

**Ratify this spec.** `implement.js` verifies by git blame that a human authored
the Ratified line, and `idea-to-spec.js` is structurally forbidden from emitting
it. A delegation instruction cannot clear that seam -- it is defined as a named
human other than the agent. This is the gate working as designed, not caution.

## To ratify

Replace, in `specs/151-speckit-fork-removal/spec.md`:

```
**Status**: draft
```

with:

```
**Status**: ratified -- <Your Name>, <YYYY-MM-DD>
**Status history**: draft
```

To decline or defer, say so; nothing is committed and `main` is untouched.
