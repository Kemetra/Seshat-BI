# Implementation Plan: business meaning registry + Arabic<->English retail term dictionary

**Branch**: `008-business-meaning-registry` (roadmap F007) | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/008-business-meaning-registry/spec.md`

## Summary

Add two STRICTLY GENERIC docs/templates to Layer 2 (Source Intelligence) that give the
Source Ready stage a reusable shape for its semantic-proposal work: a **Business Meaning
Registry** (business term -> canonical meaning -> surface forms -> proposed/confirmed
status -> evidence) and an **Arabic<->English retail term Dictionary** (Arabic term ->
canonical English meaning -> synonyms/variants -> status -> evidence, with RC8 returns
discipline baked in). Both carry ZERO C086/El Ezaby/pharmacy values -- they cite the
filled C086 instance in `docs/data-dictionary.md`, never inline it. A short Layer-2
reference doc explains how the artifacts contribute Source Ready `evidence[]` and maps
them onto the EXISTING Source Ready statuses (no new stage, status, blocking reason, or
confidence number). `source-ready.md` is edited additively to mention them as OPTIONAL
strengthening artifacts. No code, no CLI, no new `retail check` rule, no new dependency.

Technical approach: pure template/doc authoring, mirroring the conventions of the five
existing mapping templates (`>`-blockquote header, ASCII-only, "cite numbers not
adjectives", "copy this file to ...", a "See also" block). Verification is a leakage
scan (no C086 specifics), an ASCII/no-BOM check, and `retail check` exit 0 + green suite.

## Technical Context

**Language/Version**: N/A -- Markdown templates + docs only. No application language.
(The repo's checker is Python 3, stdlib-only, `dependencies = []`; this feature adds none.)

**Primary Dependencies**: None added. Authoring conventions borrowed from
`templates/source-profile.md`, `templates/assumptions.md`, `templates/unresolved-questions.md`.

**Storage**: Tracked Markdown files under `templates/` and `docs/`. Filled instances (out
of scope) would live under `mappings/<table>/`.

**Testing**: No unit tests added (no code). Verification = `retail check` exit 0 (current rule count)
+ existing unit suite green + a leakage/ASCII/no-BOM scan over the new files. The "test"
of a template is the Independent Test in each user story (a reviewer fills placeholders).

**Target Platform**: Repo text consumed by the agent + human reviewers on Windows
(UTF-8 no BOM, ASCII content, `<=200` char repo-relative paths -- Principle IX).

**Project Type**: Docs/templates slice (single repo; no new source tree).

**Performance Goals**: N/A (static text).

**Constraints**: ASCII-only content; UTF-8 no BOM; no C086/ezaby/pharmacy values
(Principle VII; hard rule #7); no numeric confidence field (hard rule #9); additive-only
edit to `source-ready.md` (do not change its required-artifact set or its review gate);
short repo-relative paths (Principle IX).

**Scale/Scope**: 2 new templates + 1 new reference doc + 1 additive edit to an existing
readiness doc. No schema migration, no DB, no checker change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | This plan |
|-----------|------|-----------|
| I. Agent-First, Gate-Enforced | does not weaken the gate; `retail check` exit 0 stays the contract | PASS -- no rule added/removed; checker stays exit 0; the registry is read by the agent, the gate still disposes |
| II. Depend, Never Fork | no pbi-cli vendoring | PASS -- not touched |
| III. Medallion, Postgres-First, Gold-Only | no read-surface change | PASS -- not touched |
| IV. Source Mapping Before Silver | mapping gate intact | PASS -- this is Source Ready (stage 1), strictly BEFORE mapping; adds no silver path |
| V. Agent Stops at Judgment Calls | rollup/PII/grain meanings stay human | PASS -- templates force `proposed` + route to `unresolved-questions.md`; agent never self-confirms (FR-006) |
| VI. Defaults Then Deviations | RC defaults honored | PASS -- dictionary bakes RC8 (returns from authoritative column); cites RC-encoding for surface variants |
| VII. C086 Is An Example, Not The Schema | templates generic | PASS -- this is the load-bearing constraint; ZERO C086 values, cite-not-inline (FR-005, SC-002) |
| VIII. Static-First Governance, Live Deferred | no live dependency | PASS -- no validator, no network, no DB; review-gated per source-ready.md |
| IX. Secrets and Reproducibility | no secrets; ASCII/no-BOM; short paths | PASS -- no credentials; ASCII + UTF-8 no BOM; short filenames |
| Readiness spine | no new stage/gate/status/score | PASS -- reuses Source Ready stage + four-value vocabulary; `proposed`/`confirmed` is entry-level meaning status, not a new stage status; no numeric score (hard rule #9) |

**Result**: PASS, no violations. Complexity Tracking table left empty (nothing to justify).

The single highest-risk failure mode is C086 LEAKAGE into the generic templates
(Principle VII). The plan mitigates it with: placeholder-only authoring, an explicit
"cite the worked example, do not inline" instruction in each template, and a leakage scan
as an acceptance gate (SC-002).

## Project Structure

### Documentation (this feature)

```text
specs/008-business-meaning-registry/
  spec.md              # Feature specification (done -- /speckit-specify)
  plan.md              # This file (/speckit-plan)
  tasks.md             # Task list (/speckit-tasks)
  analysis.md          # Cross-artifact analysis findings (/speckit-analyze)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` are produced: there
is no unknown to research (the conventions and the Source Ready contract already exist),
no data model (the "model" IS the template schema, defined inline in the template), and
no API/contract surface (no code). This matches features 001-006, which are docs/templates
slices without those sub-artifacts.

### Source Code (repository root)

No source code. The deliverables are tracked text:

```text
templates/
  business-meaning-registry.md     # NEW -- generic registry schema/template
  retail-term-dictionary.md        # NEW -- generic Arabic<->English dictionary schema/template
  source-profile.md                # existing -- conventions to mirror (unchanged)
  assumptions.md                   # existing -- bilingual-decision sibling (unchanged)
  unresolved-questions.md          # existing -- where rollup/PII/grain meanings route (unchanged)

docs/
  source-intelligence.md           # NEW -- Layer-2 reference: how the two artifacts feed Source Ready evidence
  readiness/
    source-ready.md                # EDITED additively -- mention registry+dictionary as OPTIONAL strengthening artifacts
  data-dictionary.md               # existing -- the FILLED C086 instance the templates CITE (unchanged)
  roadmap/roadmap.md               # existing -- F007 row (unchanged; cited)
```

**Structure Decision**: Place the two templates in `templates/` alongside the five
mapping-gate templates (a filled copy is a per-table `mappings/<table>/` artifact, exactly
like `source-profile.md`). Place the Layer-2 explainer at `docs/source-intelligence.md`
(new top-level doc, parallel to `docs/data-dictionary.md` and `docs/conventions.md`) so it
reads as a Layer-2 reference and does not bloat the readiness stage doc. Keep the
`source-ready.md` change additive (a "See also" / optional-artifact note), preserving its
single required artifact and its review gate.

*Open structure choice deferred to tasks (low-stakes, reversible):* whether the explainer
lives at `docs/source-intelligence.md` or as a new section inside `docs/readiness/`.
Default chosen above is `docs/source-intelligence.md`; either is a one-file move if
reconsidered.

## Phasing

This is a single-pass docs/templates slice; "phases" here are authoring groups, not
medallion phases.

- **Phase A -- Registry template** (US1, P1): author `templates/business-meaning-registry.md`
  -- header convention, per-entry field table (FR-002), proposed-not-invented discipline
  (FR-006), no score field (hard rule #9), See-also (FR-010).
- **Phase B -- Dictionary template** (US2, P1): author `templates/retail-term-dictionary.md`
  -- bilingual per-entry fields (FR-004), synonyms/encoding-variant handling, RC8 returns
  discipline, generic placeholders only (FR-005), See-also.
- **Phase C -- Layer-2 explainer + spine linkage** (US3, P2): author
  `docs/source-intelligence.md` (FR-007) and edit `docs/readiness/source-ready.md`
  additively (FR-008) -- map artifacts onto existing Source Ready evidence/statuses, no new
  status/blocking-reason/score.
- **Phase D -- Verify**: leakage scan (SC-002), ASCII/no-BOM scan (SC-001),
  `retail check` exit 0 + suite green (SC-003), trace-the-example review (SC-004),
  discipline-present review (SC-005).

Phases A and B are independent (different files) and can be authored in parallel; C depends
on A+B existing (it references them); D is last.

## Complexity Tracking

> No Constitution Check violations. No entries.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | -- | -- |

## See also

- The spec: `specs/008-business-meaning-registry/spec.md`.
- The stage advanced: `docs/readiness/source-ready.md`; the spine:
  `docs/readiness/readiness-model.md`, `readiness-pipeline.md`.
- The roadmap + hard rules: `docs/roadmap/roadmap.md` (F007; #7/#8/#9).
- The constitution: `.specify/memory/constitution.md` (Principles V, VI/RC8, VII, IX).
- Conventions to mirror: `templates/source-profile.md`, `templates/assumptions.md`,
  `templates/unresolved-questions.md`.
- The filled instance the templates cite: `docs/data-dictionary.md`,
  `docs/worked-examples/c086-pharmacy.md`.
