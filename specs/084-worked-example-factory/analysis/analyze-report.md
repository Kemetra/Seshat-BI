# Cross-Artifact Analysis: Worked-Example Factory

**Feature**: `specs/084-worked-example-factory/` | **Step**: 4 (analyze)

**Method note (fallback declared upfront)**: `speckit-analyze` is implemented
as a conversational agent skill (`.claude/skills/speckit-analyze/SKILL.md`),
not a scriptable CLI command that returns a report deterministically. This
report was produced **manually** rather than by invoking that skill, to avoid
conversational-skill friction inside the isolated worktree (the plan's STEP 4
explicitly provides for a manual fallback: "try speckit-analyze; else MANUAL
`analysis/analyze-report.md`, note the fallback"). It is produced by direct
re-reading of spec.md, plan.md, tasks.md, research.md, data-model.md,
quickstart.md, and contracts/worked-example-completeness.md side by side. No
automated analyzer ran; every finding below was verified by opening the cited
file and section.

---

## 1. Cross-artifact consistency

| Check | Finding |
|-------|---------|
| Terminology consistency (tier names) | "repo-only" and "human/live-gated" are used identically across spec.md (FR-004), research.md (Sec 5), data-model.md (Completeness Tier entity), and contracts/worked-example-completeness.md (Tier 1 / Tier 2 headings). No drift found. |
| Terminology consistency (maturity rungs) | L0-L6 rung names and the binary-evidence framing match `templates/maturity-report.md` verbatim in research.md Sec 3 and are referenced consistently (not re-derived) in spec.md FR-005/SC-005 and plan.md's Constitution Check Readiness-System row. |
| Artifact inventory consistency | The 14-item artifact set in data-model.md matches the sequence in quickstart.md's 8-step process and the section letters (A-H) in contracts/worked-example-completeness.md. Cross-checked item-by-item; no artifact named in one document is missing from another. |
| FR -> task traceability | Every FR-00x in spec.md has at least one corresponding task in tasks.md (FR-001/002 -> T011/T012/T013; FR-003/004 -> T015/T016/T017/T018/T019; FR-005 -> T021/T022/T023; FR-006/007 -> checked throughout, see Sec 4 below; FR-008 -> T015; FR-009 -> T013/T014; FR-010 -> T008/spec.md itself; FR-011/012 -> enforced as boundaries, not a positive task). No orphan FR found. |
| SC -> validation traceability | SC-001 -> quickstart.md + T011-T014 (Phase 3 checkpoint). SC-002 -> contracts/worked-example-completeness.md's own Calibration section + T020. SC-003/SC-004 -> checked in Sec 4 below. SC-005 -> T022/T023 + this report's Sec 6. SC-006 -> contracts/worked-example-completeness.md Tier 2 section. All six have a concrete check, none is aspirational-only. |

**Approval-seam count consistency (re-trued after the Sec 3 fix)**: this pass
surfaced a count mismatch created by the Sec 3 correction below -- adding the
conditional `C-T2-0` (file-source `source_ready`) approval to the contract left
three "four seams" statements (spec.md SC-006, spec.md Human-Approval
Boundaries, data-model.md Completeness Tier) reading "four" while the contract
then listed five. **Resolved**: all three were updated to "four always-required
plus a fifth, conditional `source_ready` for file sources," matching the
contract and `templates/readiness-status.yaml`'s own conditional comment.
Re-checked after the edit: the count is now stated consistently across the
contract, spec.md (both places), and data-model.md.

**Verdict**: consistent. After the approval-seam reconciliation noted above, no
contradicting statement remains across the seven documents.

## 2. Missing acceptance criteria

Spec.md's Success Criteria (SC-001..SC-006) and the completeness contract's
Tier 1/Tier 2 checklists together cover: domain selection, artifact
completeness per readiness stage, the two-tier split, non-fabrication, non-C086,
and the maturity/capability distinction. Reviewed against the task briefing's
explicit ask ("this feature is largely ABOUT acceptance criteria... make that
section rich") -- the acceptance-criteria surface is the contract file itself
(29 checkable items across 10 subsections) plus spec.md's own Acceptance
Scenarios (7 Given/When/Then scenarios across 3 user stories). No gap found:
every stage of the readiness spine (Source through Publish Ready) has at least
one Tier-1 item and, where applicable, a Tier-2 item.

One deliberate near-gap, flagged rather than silently left: the contract does
not define a criterion for "the domain was a *good* choice" beyond the binary
C-A1/C-A2 checks (axis stressed + expressible with existing defaults) -- there
is no criterion for, e.g., "this domain is more valuable than that one." This
is intentional: spec.md's Non-Goals and FR-011 forbid this feature from
choosing or ranking domains; a value judgment between candidate domains is a
future human decision, not something this contract should pre-empt.

## 3. Ambiguous approval boundaries

Checked spec.md's Human-Approval Boundaries section against
contracts/worked-example-completeness.md's Tier 2 and quickstart.md's
approval callouts (steps 3, 5, 6, 7):

- All three name the same four stages (`mapping_ready`, `semantic_model_ready`,
  `dashboard_ready`, `publish_ready`) with the same authority classes (analyst/
  data_owner, metric_owner, report_owner, data_owner/governance) as
  `docs/readiness/readiness-model.md`'s own diagram. No mismatch found.
- `readiness-model.md` notes `source_ready` ALSO needs an approval when the
  source is a file (csv/excel), per `templates/readiness-status.yaml`'s own
  comment ("REQUIRED for a file source"). This feature's contract (Tier 2)
  originally did **not** list a `source_ready` approval item. **Finding
  (minor gap, since fixed): for a file-sourced candidate domain, a fifth
  approval seam applies that the contract's Tier 2 list did not enumerate.**
  **Resolution**: added item `C-T2-0` (file-source only, conditional) to
  `contracts/worked-example-completeness.md` Tier 2, mirroring
  `readiness-status.yaml`'s own conditional comment. This is a same-file,
  additive, non-scope-expanding correction (it documents an existing gate
  more completely; it adds no new gate) made during this analysis pass rather
  than deferred, since the fix was a single checklist item in the file this
  step was already reviewing. Not a blocker either way, since neither
  illustrative candidate domain (inventory, loyalty) was scoped to a file
  source in this spec.

No other ambiguity found: every approval boundary statement in every document
names the same four (or, per the finding above, potentially five) seams
consistently, and every one states the factory process leaves it empty.

## 4. FAKE-CONFIDENCE / FABRICATED-METRIC risk (flagged highest for this feature)

This is the risk the task briefing calls out explicitly as highest for this
feature. Checked exhaustively:

- **spec.md**: searched for any numeric claim beyond citations of already-
  published retail_store_sales figures (12,575 rows, etc., all attributed with
  "per doc Sec N"). No new number invented. FR-006 explicitly forbids fabricated
  metrics/approvals as a hard constraint on the *process*.
- **research.md**: all numeric content is either (a) citations of
  retail_store_sales' real, published figures, or (b) rung/stage names (L0-L6,
  the seven readiness stages), which are milestone labels, never magnitudes.
- **data-model.md**: no numeric field is populated; every table cell is a
  field name, a template path, or a stage name.
- **contracts/worked-example-completeness.md**: the Calibration Check section
  cites retail_store_sales' real recorded verdict (Dashboard Ready `pass`,
  Publish Ready `warning`) rather than computing a new number. The Verdict
  rule explicitly forbids a percentage/fraction as the reported outcome
  ("6/9 items' is itself a soft score and MUST NOT be reported as the
  verdict"). This is a **positive finding**: the contract pre-empts the exact
  failure mode (a soft numeric completeness score) the task warns about.
- **quickstart.md**: no numeric claim; procedural only.
- **plan.md / tasks.md**: no numeric claim beyond citing template rung names.

**Verdict**: no fabricated metric, KPI contract, or approval found anywhere in
the produced document set. Risk realized: **none**. Residual risk is entirely
in *future use* of this factory by an author who does not follow it (out of
this feature's control) -- mitigated as far as a documentation feature can by
FR-006, the Verdict rule's explicit anti-percentage clause, and Tier 2's
explicit "never simulate/pre-fill/infer" instruction.

## 5. Live-validation-claim risk

Checked every document for a claim that `retail check`, `retail validate`, or
a live DB run occurred against a real target as part of *this* feature's
production:

- plan.md's Tests section explicitly limits validation to "a read-only
  `retail check --repo .` run... reported with its exact exit code" -- a dry
  check over the repo's committed text, not a live-DB validate run.
- No document claims `retail validate` was run. Every reference to it is
  either (a) describing what a future example-builder would run, or (b)
  citing that retail_store_sales already ran it (attributed, past tense, with
  a citation).
- Tasks T028 explicitly instructs recording the *exact* exit code or the
  *exact* skip reason -- no "assume it passes" language.

**Verdict**: no live-validation-claim risk found in the produced documents.
The actual `retail check` dry-run result is reported in the final summary
(post-analysis, per T028) with its real exit code, not asserted here in
advance.

## 6. Over-governance risk

Checked whether this feature invents process weight beyond what the task
asked for:

- No new template file was added (data-model.md explicitly notes item 13 -- the
  narrative doc -- deliberately reuses retail-store-sales.md's own section
  structure "rather than proposing a new template file," citing this as a
  Complexity-Tracking-relevant choice).
- No new `retail check` rule proposed (FR-012 explicitly forbids it within
  this process; plan.md's Complexity Tracking table is empty, meaning no
  Constitution Check violation needed justifying).
- The completeness contract has 29 checkable items across 10 subsections -- reviewed for redundancy: each item maps to a distinct template's own stated
  exit criterion (source-profile.md's Exit Gate, assumptions.md's integrity
  invariant, unresolved-questions.md's Gate status) rather than inventing new
  criteria. This is composition of existing gates, not a new layer of
  governance on top of them.

**Verdict**: low over-governance risk. The feature is additive documentation
that cites and organizes existing gates; it does not introduce a new review
step beyond what a table already goes through today (the same five artifacts,
the same readiness spine, the same four approvals).

## 7. Dependency conflicts

- No conflict found with `076-extract-pure-kit` (the most recent prior spec):
  that feature is about repo/package extraction and does not touch worked
  examples or the maturity ladder.
- No conflict found with the 2026-07-03 design-governance wave (RELEASE_NOTES):
  that wave is design-lint/contrast rules, orthogonal to this feature.
- No conflict found with `027-release-maturity-management` (the spec owning
  `templates/maturity-report.md`): this feature only *cites* that template's
  rungs; it does not redefine them, add a rung, or change the binary-evidence
  rule.
- **`083-demo-harness`**: no spec directory exists yet on this branch (checked
  again at analysis time: `specs/` listing shows no `083-*` entry). No file
  conflict is possible since nothing exists to conflict with. The relationship
  is stated by role (FR-010, research.md Sec 6) rather than by reading a
  nonexistent spec.md, as instructed.

**Verdict**: no dependency conflicts found.

## 8. Overlap analysis (named per task briefing)

### vs. `083-demo-harness`

- **This feature (084)**: defines the *authoring* process -- how a worked
  example gets built and what "complete" means. Produces no runnable artifact.
- **083 (as briefed, not yet specced)**: *runs* an already-complete worked
  example (execution/demo surface).
- **Overlap**: none in scope (one authors, one runs). **Sequencing
  relationship**: a demo harness's natural first target (`retail_store_sales`)
  is already complete without this feature; this feature only becomes a
  prerequisite if `083-demo-harness` (or a later feature) wants to demo a
  *second* example, since that second example would need to satisfy this
  feature's completeness contract first. Recorded in research.md Sec 6.
  **Recommendation**: keep separate. No basis found for merging or narrowing
  either into the other -- they operate on different objects (the recipe vs. a
  finished dish) and have independent forbidden-scope lists (084 must not
  build an example; a demo harness must not redefine what "complete" means).

### vs. `docs/worked-examples/retail-store-sales.md` (the existing example)

- **Overlap risk**: this feature could have duplicated retail-store-sales.md's
  content instead of generalizing from it.
- **Finding**: no duplication found. This feature's documents *cite*
  retail-store-sales.md's real figures and structure as evidence/precedent
  (e.g. the genericity-axis table in research.md Sec 1, the calibration check in
  the contract) but do not restate its narrative, and explicitly forbid
  copying its answers (quickstart.md "Before you start" step 1: "not to copy
  its answers"). The existing doc remains the sole source of truth for
  retail_store_sales itself; this feature only extracts the *reusable pattern*
  from it, which is exactly what that doc's own "How to reuse this" section
  already invites (retail-store-sales.md, opening blockquote).

**Verdict**: both overlaps are the intentional, non-duplicative kind
(citation and generalization, not copy or re-implementation).

## 9. Unsafe claims

Scanned for any claim of CI status, live validation, or approval that was not
directly observed in this session:

- No GitHub Actions / CI claim made anywhere (task boundary honored).
- No "validated live" claim made (per Sec 5 above).
- No approval claimed on this feature's own behalf -- this spec chain requires
  none per spec.md's Human-Approval Boundaries, and none is asserted.

**Verdict**: no unsafe claim found.

## 10. Keep-separate-or-narrow recommendation

**Recommendation: keep as its own feature, as scoped.** This feature is
correctly narrow: it produces exactly one process document set and one
completeness contract, cites rather than restates every existing artifact it
depends on, and adds zero runtime surface. It should **not** be merged into
`083-demo-harness` (different objects, as above), **not** be merged into
`027-release-maturity-management` (that feature owns the maturity ladder
itself; this feature only consumes it), and **not** be expanded to actually
build a second worked example (that is explicitly out of scope and would be
its own, much larger, human/live-DB-dependent effort).

**Sequencing confirmation**: consistent with the task briefing's own note,
this feature has no forcing dependency and is reasonably last in
implementation priority among currently-drafted ideas -- it unlocks future
work (a second worked example) rather than being unlocked by anything else
still pending.

## 11. Validation-command note (what actually validated the new files)

Recorded here so no reader infers a pass that did not happen:

- `retail check --repo .` (from the worktree root) exits **1** with a single
  finding: `DR1 stale-phrase manifest 'docs/quality/design-stale-phrases.yaml'
  is missing or untracked`. This is a **pre-existing / environmental**
  condition, NOT a finding about this feature's files: the editable `retail`
  install resolves to the OTHER checkout (`C:\Users\user\Documents\GitHub\
  Seshat_BI`, verified via `retail.__file__`), where `design-stale-phrases.yaml`
  is an untracked in-progress file on a different branch; it is absent from this
  worktree (branch `spec/worked-example-factory`, base `main @ 760545d`). `DR1`
  aborts the run on that single error, so `retail check` **never reached or
  validated the new `specs/084-worked-example-factory/` files at all**. Its
  exit code says nothing, either way, about this feature.
- `retail semantic-check --repo .` exits **0** ("no drift (0 findings)") -- a
  real pass, expected since this feature adds no DAX/PBIP.
- The **actual** repo-hygiene validation of the new files was done directly: a
  BOM check (`od`), a non-ASCII scan (ripgrep `[^\x00-\x7F]` -> 0 matches after
  ASCII-normalizing em-dashes to ` -- `, the section sign to `Sec`, and the
  plan.md tree to ASCII box characters), and a secret-pattern scan (0 matches).
  These -- not `retail check` -- are what confirm the new files are ASCII /
  UTF-8-no-BOM and secret-free.

## Summary verdict

No blocking finding. One minor gap was found and corrected in place (Sec 3: a
conditional `source_ready` file-source approval seam, now `C-T2-0` in
`contracts/worked-example-completeness.md`) -- a same-file, additive checklist
addition, not a scope change; the resulting seam-count references were
reconciled across spec.md and data-model.md (see Sec 1). Recommend proceeding
to whatever comes after this analyze step (a human ratify/review action) with
this feature as-is.
