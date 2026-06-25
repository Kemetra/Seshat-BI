# Implementation Plan: Readiness Viewer

**Branch**: `020-readiness-viewer`  **Roadmap feature**: F026 (spec-dir 020 = roadmap
F026; roadmap F-number is authoritative when they disagree)  **Date**: 2026-06-25
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/020-readiness-viewer/spec.md`

## Summary

Build the **stage-centric reading lens** over the kit's Core Authority readiness data
(Roadmap F026, Product Module, read-only). The viewer reads each item's
`readiness-status.yaml` and renders three things F012 does not: (1) a per-stage status
MATRIX across all seven readiness stages, (2) `evidence[]` as navigable REFERENCES (not
F012's counts), and (3) an `approvals[]` TIMELINE. It is a different VIEW over the SAME
inputs F012 already reads -- no new pipeline, no new measurement, no new truth. This
slice is **docs/templates/skill only** (roadmap rule #8; Principle VIII): no Python, no
CLI verb, no `retail check` rule, no DB read. The recommended shape is (a) a stage-view
mode reusing F012's aggregation, with (b) merge-into-F012 as the explicit fallback if the
delta proves thin (criterion: if the only durable difference is sort order + column
labels, merge). The viewer computes no truth, changes no state, infers no approval, and
shows missing evidence AS MISSING.

## Technical Context

**Language/Version**: None this slice -- docs/planning + agent-procedure text (Markdown)
+ one generic Markdown template. The agent is the runtime.

**Primary Dependencies**: None at runtime. Reuses F012's read-fan-out
(`.claude/skills/retail-control-room/`) as the aggregation layer; renders the readiness
schema from `templates/readiness-status.yaml` (ADR 0004). Authoring style borrows from
F012's SKILL.md and `templates/data-quality-control-room.md`.

**Storage**: Committed text in the repo: `.claude/skills/readiness-viewer/SKILL.md` (or a
documented mode of `retail-control-room/SKILL.md`) + `templates/readiness-view.md`. It
reads (never writes) `mappings/<table>/readiness-status.yaml` and the files those
`evidence[]` entries reference.

**Testing**: No code, so no unit tests. Verification is: (1) `retail check` exit 0 with
no new rule added, (2) the template is valid Markdown / parses as the intended shape,
(3) a manual generic render over two or more fixture items proves every matrix cell
equals the recorded per-stage `status`, evidence renders as references (missing flagged),
the approvals timeline renders verbatim, and `git status` shows zero modified per-item
files, (4) ASCII + UTF-8 no-BOM on every new file.

**Target Platform**: Repo text artifacts consumed by an agent + reviewed by a human.

**Project Type**: Product Module (read-only) -- a skill + one template; no `src/` change.

**Performance Goals**: N/A (static read-and-render at one-to-few item volume).

**Constraints**: ASCII + UTF-8 no BOM; generic (no C086 / retail_store_sales values);
Windows path budget (short names); NO numeric confidence/percent-ready score anywhere; NO
state mutation; NO recomputed status; NO inferred approval; NO fabricated evidence; NO
new validator / CLI / rule.

**Scale/Scope**: 1 skill (or 1 documented mode) + 1 template. Three future deliverables
enumerated (docs page, optional CLI) but NOT built this slice.

## Constitution Check

*GATE: must pass before and after design. Constitution at `.specify/memory/constitution.md`.*

| Principle | How this feature complies |
|-----------|---------------------------|
| I. Agent-First, Gate-Enforced | The viewer is agent-procedure text; the agent is the runtime. It adds no gate and grants no authority over pass/fail -- it RENDERS the gate states the Core Authority files record. `retail check` stays the gate, untouched. |
| II. Depend, Never Fork | No engine, no Power BI execution adapter, no fork. Reuses the shipped F012 aggregation rather than re-implementing a scan. Pure local rendering opinion in a skill + template. |
| III. Medallion, Gold-Only | Not triggered (no SQL, no DB, no Power BI read). The viewer renders readiness state; it touches no medallion layer. |
| IV. Source Mapping Before Silver | Not triggered (no silver SQL). The viewer renders the Mapping/Silver stage statuses; it never advances them. |
| V. Agent Stops at Judgment Calls | The viewer creates NO truth: it never approves a gate, never resolves a `current_stage`-vs-status conflict, never infers an approval. Conflicts and missing approvals/evidence are surfaced as flags for the named human, never auto-resolved. No-self-approval is an explicit Forbidden op. |
| VI. Defaults Then Deviations | Renders the recorded state as-is (the default); deviations (conflicts, missing evidence, missing approvals) are surfaced as flags, never silently smoothed. |
| VII. C086 Is An Example | The skill + template are generic; C086 / retail_store_sales are cited filled instances, never inlined. SC-001 verifies zero worked-example specifics. |
| VIII. Static-First, Live Deferred | NO Python, NO rule, NO CLI, NO DB read this slice; `retail check` exit 0 + no new rule added. Docs/templates/skill only (rule #8). |
| IX. Secrets & Reproducibility | No secrets, no DSNs, no paths-to-local-machine. ASCII + UTF-8 no BOM; short paths; the template is reproducible copy-me text. No numeric score that reads as confidence (rule #9). |

**Result**: PASS. No violations; Complexity Tracking left empty.

### Boundary gate (feature-specific, load-bearing)

The single biggest design risk is re-speccing F012. The plan holds the boundary:

- F026 reads the SAME inputs as F012 and adds NO new input, measurement, or pipeline.
- The ONLY differences are the three named deltas: the seven-stage matrix, evidence as
  references, the approvals timeline. `next_action` is shared with F012, not a delta.
- The recommended shape reuses F012's aggregation (shape (a)); the merge fallback (shape
  (b)) is explicit, with a stated thinness criterion. A viewer that duplicates F012 must
  merge, not ship.
- The second risk is creating truth in a viewer: no recomputed status, no inferred
  approval, no fabricated evidence -- all are Forbidden ops, mapped 1:1 in governance.md.

## Project Structure

### Documentation (this feature = the 5 spec-kit files)

```text
specs/020-readiness-viewer/
|-- spec.md                     # feature specification (done)
|-- plan.md                     # this file
|-- tasks.md                    # dependency-ordered task list
`-- checklists/
    |-- acceptance.md           # specification quality + acceptance checklist
    `-- governance.md           # Core-Authority / no-self-approval / no-fake-confidence gate
```

No `research.md` / `data-model.md` / `contracts/` dir is generated: there is no code to
research and no DB model to design. The only open decision (skill-vs-mode (a)/(b)) is
resolved in Phase 0 below with a recommended default, not deferred research.

### Repository artifacts this feature PLANS (not created this slice)

These are FUTURE outputs the spec enumerates. This planning slice writes ONLY the five
spec-kit files above; the artifacts below are authored in a later implementation slice.

```text
.claude/skills/readiness-viewer/SKILL.md   # PLANNED -- the read-only stage-view verb
                                           #   (or a documented stage-view MODE of
                                           #    .claude/skills/retail-control-room/SKILL.md)
docs/tools/readiness-viewer.md             # PLANNED -- the module's usage + boundary doc
templates/readiness-view.md                # PLANNED -- generic stage-view output template
                                           #   (7-stage matrix + evidence references +
                                           #    approvals timeline)
src/retail/tools/readiness_viewer.py       # PLANNED + OPTIONAL -- a deferred read-only
                                           #   CLI renderer (NO new validator); not built
                                           #   until item volume outgrows hand-rendering
```

**Structure Decision**: Product Module (read-only) -- no `src/` change this slice. The
viewer's home is a skill (or a mode of `retail-control-room`); the output template lives
in the existing `templates/` dir alongside F012's `data-quality-control-room.md`; the
usage doc lives under a `docs/tools/` home (parallel to `docs/readiness/`). The optional
CLI under `src/retail/tools/` is enumerated and deferred, mirroring F012's deferred-CLI
posture.

## Phase 0 -- Research (resolve the skill-vs-mode decision; no external research)

No external research needed -- both reference shapes are in-repo. The one decision to
settle:

- **Skill-vs-mode (a)/(b).** Evaluate the three deltas against F012's existing output. If
  each delta gives a reader something the control room cannot -- the stage matrix reveals
  WHERE in the seven-stage progression an item sits (not just its current stage),
  evidence-as-reference lets a reviewer open the backing file (not just see a count), and
  the approvals timeline answers "who let this advance, when" (which F012 does not read) --
  then ship as shape (a): a new `readiness-viewer` skill that REUSES F012's read-fan-out
  and adds the stage-lens rendering. If the deltas collapse to re-sorted columns (thinness
  criterion: the only durable difference is sort order + column labels), choose shape (b):
  fold the stage view into F012 as an optional section and DROP the separate module.
  Recommended default: shape (a).

## Phase 1 -- Design (the artifact shapes)

**`.claude/skills/readiness-viewer/SKILL.md`** (or the F012 mode). Frontmatter in the
F012 style (name + a description that triggers on "show readiness", "which stage is each
table at", "who approved this gate"). Body sections: a scope boundary (read-only;
computes no truth; infers no approval; missing evidence shown as missing; no fake
confidence; generic; ASCII no BOM); a "Relationship to F012" block (same inputs, three
deltas, `next_action` shared); a "Reads, never re-derives" evidence chain table mapping
each rendered element to its `readiness-status.yaml` field; the render procedure (1.
seven-stage matrix, 2. evidence references, 3. approvals timeline, 4. surface conflicts);
the no-fake-confidence guardrail; the honest-state rules (missing/malformed/conflict);
the read-only proof (`git status` clean after a run); See also; and an `## Orchestration`
pointer.

**`templates/readiness-view.md`** (generic). The stable output shape: a matrix block
(item rows x seven stage columns, each cell a `status` placeholder, `current_stage`
marked, `next_action` shown); an evidence-reference block per stage (placeholder path +
line/section, with explicit "evidence missing" / "referenced file not found" rows); an
approvals-timeline block (placeholder {stage, owner, date} rows in order, with an
"approval not recorded" flag row). Generic placeholders only; C086 cited, never inlined.

**`docs/tools/readiness-viewer.md`** (usage + boundary). What the viewer is, when to use
it vs. F012, the read-only contract (per F024's module category), and how the seven-stage
matrix / evidence references / approvals timeline are read from `readiness-status.yaml`.

**`src/retail/tools/readiness_viewer.py`** (OPTIONAL, DEFERRED): enumerated only; not
designed in detail this slice. A future read-only CLI renderer, still no new validator.

## Phase 1 -- Constitution re-check

Re-checked after design: still PASS. The design adds only a generic skill/mode + one
generic template (+ a usage doc and an optional deferred CLI, both future), reads no DB,
adds no rule, computes no status, infers no approval, and emits no score. Boundary gate
holds (same inputs as F012; the three deltas only; merge fallback explicit).

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
