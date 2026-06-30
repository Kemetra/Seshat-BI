# Implementation Plan: Idea-Bank Memory Seam (IL1)

**Branch**: `052-idea-bank-memory-seam` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/052-idea-bank-memory-seam/spec.md`

## Summary

Add a curated, structured shipped/settled ledger `docs/roadmap/shipped-ideas.yaml`
(idea-id -> `{ status, pr_sha, f_row|none }`) and one read step in the idea-engine Memory
stage that consumes it as known-history. The ledger is evidence-OF-shipped only; no code
path writes a roadmap F-row from it. Scope is the CORE seam (doc artifact + workflow read
step); the optional static IL1 reconciler rule is explicitly OUT OF SCOPE (FR-010).

Technical approach: the Memory stage today (`phase('Memory')` in
`.claude/workflows/idea-engine.js`) builds a `prior_ideas[]` list from two prose sources
(idea headings + the "## SHIPPED / SETTLED" appendix) plus Ground's in-session ship-status.
This feature adds the ledger as a THIRD, structured, authoritative-on-conflict input to that
same list. The change is: (1) author the yaml doc, (2) extend the Memory reader's prompt /
input with the ledger contents and a precedence rule, (3) seed the ledger from the existing
prose appendix. No new module, no executor, no DB.

## Technical Context

**Language/Version**: JavaScript (the `.claude/workflows/idea-engine.js` workflow, run by the
Workflow loader -- a stricter-than-node JS parser; see repo memory note) + a YAML data file.
No Python source changes in the core seam (the optional rule that would touch Python is out
of scope).

**Primary Dependencies**: None new. YAML is read as text by the workflow's existing agent
read step (the Memory reader already reads `idea-backlog.md` from disk via the agent). No new
runtime library is added to the JS workflow; if a future optional rule parses the yaml in
Python it would use the existing lazy `import yaml` discipline (out of scope here).

**Storage**: One new tracked text file, `docs/roadmap/shipped-ideas.yaml`. No database.

**Testing**: A unit-level fixture/assertion that (a) the ledger is valid YAML with the
required keys, and (b) the generic-identifiers-only invariant holds (no sample data /
domain specifics). Workflow-prompt behavior (labeling) is validated by the spec's
acceptance scenarios as a manual/quickstart check, since the Memory stage is an LLM agent
step not a deterministic function.

**Target Platform**: Repo tooling / CI (Windows + CI Linux). No deployment target.

**Project Type**: Governance/CLI plumbing for the idea-bank workflow. Docs + workflow edit.

**Performance Goals**: N/A (a small hand-curated ledger, single read per run).

**Constraints**: ASCII + UTF-8 no BOM (rule IX: `--` and `->`, no glyphs). Generic-only
(rule 7: no C086/pharmacy specifics). Fail-loud on malformed yaml (rule 9). No executor,
no live DB, no auto-promotion to roadmap. Must not violate the single-owner-of-ship-status
invariant (Ground owns git-derived ship-status; the ledger is a curated human record).
Windows 260-char path limit (names already short).

**Scale/Scope**: Seed ledger is the handful of already-shipped/settled ideas in the prose
appendix today (A1, B1, B2, F7, F8 shipped; F5, F6 settled). Grows by one hand-edited row
per future shipped idea.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Idea bank, not a roadmap / human rules promotion (Principle V)**: PASS by construction.
  The ledger records an F-row only when a human already placed one; FR-003 forbids any code
  path from writing/assigning a roadmap F-row. No self-grant of a promotion or a readiness
  pass.
- **Single owner of ship-status**: PASS with a recorded open question. The CORE seam keeps
  the ledger a human-curated record distinct from Ground's git read; the Memory reader still
  does NOT re-read git. Whether the engine may APPEND to the ledger (vs strictly human-curated)
  is a Principle-V judgment call left open for the human (spec ## Clarifications).
- **Add the seam, not the implementation (hard rule #8 / YAGNI)**: PASS. Doc + read step only;
  optional rule deferred (FR-010).
- **Fail-closed / no fabricated confidence (rule 9)**: PASS. Malformed yaml fails loud
  (FR-006); absent/empty yaml degrades gracefully to today's behavior (FR-005); no numeric
  score or readiness claim is produced.
- **Generic-only (rule 7) / no C086 leak**: PASS. Ledger holds idea-ids, PR/SHA, F-row labels
  only (FR-007); a test asserts the generic-identifiers-only invariant.
- **No deferred capability assumed**: PASS. Does not assume F016 Power BI Execution Adapter
  or F031-F033 spec-only runtimes; touches none of them.
- **Stdlib-only / lazy-yaml invariant**: N/A to the core seam (no Python rule added). Recorded
  as a constraint for the deferred optional rule only.

Result: PASS (two items carry recorded-open human judgment calls that do not block the core
seam design).

## Project Structure

### Documentation (this feature)

```text
specs/052-idea-bank-memory-seam/
|-- plan.md              # this file
|-- spec.md              # feature spec (stage 2-3 output)
|-- data-model.md        # Phase 1 output (ledger schema)
|-- quickstart.md        # Phase 1 output (how to verify the seam)
|-- contracts/
|   `-- shipped-ideas.schema.md   # the ledger's field contract (doc, not executable)
|-- checklists/
|   `-- requirements.md   # spec quality checklist (stage 2 output)
|-- analysis.md          # stage 5 output (/speckit-analyze)
|-- plan-review.md       # stage 6 output (adversarial review)
`-- tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source / repo files touched

```text
docs/roadmap/shipped-ideas.yaml        # NEW -- the structured ledger (the seam artifact)
.claude/workflows/idea-engine.js       # EDIT -- Memory stage: read ledger as 3rd input,
                                        #         authoritative-on-conflict, fail-loud on
                                        #         malformed, graceful on absent/empty
tests/                                  # NEW test -- ledger validity + generic-only invariant
                                        #   (exact location chosen in tasks; mirrors how
                                        #    existing manifest files are guarded)
docs/roadmap/idea-backlog.md           # (only if the human later rules "replace" -- OUT of
                                        #  this plan's scope; the prose appendix is left in
                                        #  place and the yaml sits alongside as authoritative
                                        #  for the machine read -- the YAGNI-minimal default)
```

## Phase 0 -- Research (decisions)

1. **Where the ledger plugs in**: confirmed -- the Memory reader's step 2b already folds the
   prose "## SHIPPED / SETTLED" appendix into `prior_ideas[]` with `current_state` of
   `shipped`/`rejected-settled` and a `state_citation`. The ledger becomes a structured input
   to that same list; `status: shipped -> current_state: shipped`, `status: settled ->
   rejected-settled`, `state_citation` = the `pr_sha` (+ `f_row` when present). No new
   downstream shape is needed -- `renderMemoryLine` already consumes `prior_ideas[]`.

2. **Precedence on conflict**: the yaml is authoritative for the machine read (spec FR-009 /
   Clarifications). The reader uses the yaml value and surfaces (in `notes`) any disagreement
   with the prose appendix; it never rewrites either file.

3. **Read mechanism**: keep it a disk read inside the existing Memory agent step (the step
   already reads `idea-backlog.md` from `<repo-root>` resolved via `git rev-parse
   --show-toplevel`). The ledger read uses the same repo-root resolution; no machine path is
   assumed. No new JS dependency, no executor.

4. **Fail-loud vs graceful**: absent OR empty file -> treat as "no structured history",
   continue on prose + ship-status (FR-005). Present-but-malformed (invalid YAML / missing
   required keys) -> fail loud with a clear error (FR-006). These are distinct branches.

5. **Single-owner boundary**: the ledger does NOT carry git-derived live status; it is a
   curated human record. Ground stays the only git reader. The CORE seam is human-curated
   authorship (mirrors `status-claims.yaml` / `parked-on.yaml`); engine-append is left as an
   open human call and is NOT designed in here.

6. **Optional rule**: explicitly deferred (FR-010). No `EXPECTED_RULE_IDS` change, no
   `src/retail/rules/` file in this feature. Authoritative current count is the live
   `EXPECTED_RULE_IDS` frozenset length (38 today); no N+1 claim is made.

## Phase 1 -- Design artifacts

- **data-model.md**: the ledger schema -- top-level mapping `idea-id -> { status, pr_sha,
  f_row }`, value domains, the generic-only invariant, and the prose-appendix relationship.
- **contracts/shipped-ideas.schema.md**: the field contract (required keys, allowed `status`
  enum, `f_row` = label-or-`none`) as a DOC contract (not an executable schema) plus a small
  valid example using generic placeholder ids.
- **quickstart.md**: how to verify the seam without a live run -- inspect the seeded ledger,
  run the validity/generic-only test, and the manual labeling check (seed one id, confirm the
  Memory reader treats it as known-history).

## Complexity Tracking

No constitution deviations requiring justification. The feature is intentionally one doc
artifact + one workflow read step + one guard test; no new module, no executor, no library.
