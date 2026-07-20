---
name: showcase-build
description: >-
  Compose a shareable, disclosure-safe, OFFLINE proof bundle of Seshat BI's
  committed readiness truth -- stages, evidence, blockers, approvals, next
  actions, metric lineage, a truthful badge/project card, and a four-category
  disclosure manifest -- for a maintainer or analyst to hand to a reviewer,
  stakeholder, or prospective contributor. Use when someone asks for a
  "shareable proof", a "showcase bundle", a "project card", or "something I
  can send to show what Seshat has governed here". This is a Product Module,
  artifact-writing: it READS the shipped Explorer projection
  (`build_explorer_projection`), the Passport (`seshat.passport`), and the
  disclosure scanner (`seshat.disclosure.scan_disclosure`), composes ONE
  offline HTML bundle, and STOPS. It recomputes NO readiness, defines NO new
  evidence schema, invents NO meaning, and grants NO approval. It is
  fail-closed: a disclosure finding over the FULL composed body blocks
  generation and writes nothing. Generation is local-only
  (`.seshat-output/`); publishing the bundle anywhere is a separate, explicit
  human action this skill never performs.
---

# showcase-build

- **Roadmap feature / spec:** `specs/127-showcase-build/` (Shareable Seshat
  Proof / Showcase Bundle).
- **Authority category:** Product Module / `artifact-writing`
  (`docs/architecture/product-modules.md`).
- **Delivery shape:** a read-only skill over a reusable library function
  (`src/seshat/showcase/build.py`), per the ratified Option B decision
  (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`, 2026-07-07). **No
  new top-level CLI verb is added** -- `seshat.cli._DISPATCH` has no
  `showcase` key, and importing `seshat.showcase` adds no network/driver
  import (mirrors the B1/B3 lazy-import guard).

A "shareable proof" is a single offline folder that answers "what has Seshat
governed here, and can I trust it?" -- the readiness spine, the evidence, the
blockers, the approvals, and the metric lineage together, a truthful badge
(never a fabricated score), and a disclosure manifest stating exactly what is
included, redacted, omitted, and unavailable. This skill is the COMPOSER: it
fills the bundle from surfaces that already ship (the Explorer projection,
the Passport, the disclosure scanner); it originates no readiness truth of
its own.

## Module contract (the filled F024 declaration)

- **Authority category:** Product Module
- **Capability level:** `artifact-writing` *(exactly one)*
- **Product layer:** `6` *(delivery/handoff rendering, sibling of the F013
  handoff pack and the F026/F028 read-only lenses)*
- **Owner:** the analyst or maintainer requesting the proof
- **Status:** Authored

### What it does (one line)

> Composes the already-committed readiness projection, an evidence-derived
> badge, and a four-category disclosure manifest into one offline HTML
> bundle, running the fail-closed disclosure scan over the FULL composed
> body before ever writing a file.

### Core Authority it READS

- `seshat.explorer.build.build_explorer_projection` -- stages, evidence
  states (`available` / `missing` / `deferred`), blockers, approvals,
  next actions, metric lineage, and input-defect entries.
- `seshat.passport` (`verify_passport`) -- ONLY when two snapshot paths are
  supplied, to compute the optional before/after section.
- `seshat.disclosure.scan_disclosure` -- the shared fail-closed scanner, run
  over the full composed bundle body (not merely the base projection).
- `seshat.cli.guards.resolve_local_output` -- the contained-output guard.

### Derived evidence it WRITES

- One offline HTML file (default `showcase/index.html`) under the contained
  `.seshat-output/` root, plus any inlined/embedded sidecar content (nothing
  external is ever referenced).

### Approved step it EXECUTES

- none. It composes and writes ONE local file, then STOPS. It runs no
  `seshat check` / `retail validate` of its own, opens no database, and
  calls no Power BI execution adapter.

### Forbidden operations

- MUST NOT recompute readiness, define a new evidence schema, or invent a
  new Explorer/Passport (FR-001/FR-002) -- it renders the existing ones.
- MUST NOT show any stage as `pass` without inspectable evidence (FR-003).
- MUST NOT write outside the contained `.seshat-output/` root (FR-006).
- MUST NOT publish, upload, track users, or call any external network/API
  (FR-007/FR-008) -- every asset is inlined or a data URI.
- MUST NOT grant or imply any approval or publish sign-off (FR-011).
- MUST NOT express a percentage, grade, or any other fabricated confidence
  number anywhere in the badge, card, or manifest (FR-013, FR-026; hard
  rule #9).
- MUST NOT modify `src/seshat/explorer/assets/explorer.css` /
  `explorer.js`, or any source readiness artifact (FR-025).
- MUST NOT add a new top-level CLI verb (FR-005; ratified Option B).

### How it handles a missing or unsafe input

- A missing artifact renders as missing; a malformed readiness file renders
  as an input defect; a deferred live check renders as unavailable -- never
  as a pass (FR-003; Principle V, stop-and-ask, never invent).
- A live disclosure finding (secret, DSN, PII value, or a residual absolute
  path that survives portability normalization) in the FULL composed body
  BLOCKS generation fail-closed: no partial or redacted file is written; the
  findings are printed (FR-009/FR-010).
- Two Passport snapshots that are not comparable (different `scope`,
  different `schema_version`, or fewer than two supplied) omit the
  before/after section gracefully with a truthful note -- never a
  fabricated delta (FR-020/FR-021).

## Scope boundary (read first)

- **Composes, never invents.** Every fact in the bundle traces to the
  reused Explorer projection or a supplied Passport snapshot. A missing
  artifact is missing; a deferred live check is unavailable; a malformed
  file is an input defect. Nothing is inferred into a pass.
- **Read-only over every source.** Generating or browsing the bundle never
  modifies a readiness status file, a database, or a Power BI model. After a
  run, `git status` shows only new files under `.seshat-output/` (typically
  git-ignored).
- **Fail-closed disclosure, full body.** The scan runs over tables, enriched
  lineage, approval receipts, the badge, the manifest, and any before/after
  content -- INCLUDING user-supplied snapshot content the base projection
  never saw. A blocking finding writes nothing.
- **No fake confidence, ever.** The badge states the highest CONTIGUOUS
  `pass` stage and the passed-stage count (e.g. "3/7 stages ready --
  Gold: blocked"). It never states a percentage, a grade, or an invented
  score (hard rule #9). When no stage has passed, it states the truthful
  onboarding status, never an empty or celebratory claim.
- **Four-category manifest, no silent drops.** Every composed item lands
  under exactly one of included / unavailable / omitted / redacted, each
  with a locator. "Redacted" names ONLY the composer's own by-design
  portability normalizations (an absolute path reduced to repo-relative, a
  private/internal URL stripped) -- never the suppression of a disclosure
  finding (those block, they are not redacted).
- **Own shell, untouched Explorer.** The bundle renders `showcase.css` /
  `showcase.js` (its own assets); it never reads or edits
  `explorer.css` / `explorer.js`.
- **Generation is not publication.** Producing the bundle never grants a
  publish approval or PII sign-off. Sharing the file anywhere is a separate,
  explicit human action outside this skill.
- **Generic.** No worked-example specifics baked in; `retail_store_sales`
  (`docs/worked-examples/retail-store-sales.md`) is a cited filled instance,
  never hard-coded (Principle VII). ASCII + UTF-8 no BOM for any text this
  skill's caller writes back into the repo (the skill itself only writes
  under `.seshat-output/`, which is not tracked).

## Procedure (numbered; do not reorder)

1. **Resolve inputs.** Workspace root (default `.`); optional output path
   (must resolve inside `.seshat-output/`); optional `rtl` render mode;
   optional two Passport snapshot file paths for the before/after section.
2. **Compose.** Call
   `seshat.showcase.build.build_showcase_bundle(root, snapshots=...)`. This
   reads the Explorer projection, derives the badge and manifest, applies
   portability normalization (absolute path -> repo-relative; private URL
   stripped -- each listed under the manifest's `redacted` category), and
   computes the optional comparison if two snapshots were supplied.
3. **Disclosure gate.** If `bundle["disclosure"]["status"] != "pass"`: STOP
   fail-closed. Print every finding (`rule`, `locator`, `message`). Write
   NOTHING. This is not a partial-write case -- no file appears.
4. **Resolve the output path.** Call
   `seshat.cli.guards.resolve_local_output(root, output)`. If the path
   escapes `.seshat-output/`, refuse and write nothing (FR-006).
5. **Render and write.** Call
   `seshat.showcase.build.render_showcase_html(bundle, repo=root, rtl=...)`
   and write the result to the resolved path.
6. **Report and STOP.** Print the written path and this reminder verbatim:
   "This is a local offline snapshot generated from committed evidence only.
   Publishing it anywhere is a separate, explicit human action." Do not
   publish, upload, or record any approval. Any judgment call surfaced in
   the bundle (an unresolved assumption, a blocked gate, a retracted
   approval) is a stop-and-ask for the named human (Principle V) -- this
   skill only renders it.

## Refusals

- **Uncontained output path** -- refuse before writing; nothing is written
  outside `.seshat-output/`.
- **Blocking disclosure finding** -- refuse fail-closed; print the findings;
  write nothing (no partial/redacted bundle).
- **A request to publish, upload, or otherwise distribute the bundle** --
  out of scope. This skill only writes a local file; publishing is the
  named human's separate, explicit action.
- **A request for a numeric confidence/health/percent-ready score** --
  refuse; the badge/manifest already state the truthful stage-and-count
  summary (hard rule #9).

## Honest-state rules (never invent, never silently resolve)

| Situation | What the skill does |
|-----------|----------------------|
| No table has reached any stage (or the workspace has no onboarded table) | badge states the truthful onboarding status; never an empty or celebratory claim |
| A readiness file is malformed | rendered as an input defect in the table panel AND listed under the manifest's `omitted` category |
| A secret / DSN / PII value / residual absolute path is present anywhere in the composed body | generation blocks fail-closed; findings printed; nothing written |
| A metric contract is unreadable | rendered as an input-defect lineage node, never a valid metric |
| Two snapshots share scope but one is malformed or a different schema | treated as not comparable; the before/after section is omitted with a note |
| Only one snapshot (or none) is supplied | no before/after section; no fabricated delta |

## See also

- The spec: `specs/127-showcase-build/spec.md`, `plan.md`, `data-model.md`,
  `contracts/showcase-contract.md`, `quickstart.md`, `research.md`.
- The library it composes: `src/seshat/showcase/build.py`,
  `src/seshat/showcase/badge.py`, `src/seshat/showcase/manifest.py`,
  `src/seshat/showcase/compare.py`.
- The reused shipped surfaces: `src/seshat/explorer/build.py`,
  `src/seshat/passport.py`, `src/seshat/disclosure.py`,
  `src/seshat/cli/guards.py`.
- The nearest sibling read-only lenses: `.claude/skills/readiness-viewer/`
  (stage matrix), `.claude/skills/evidence-pack-generator/` (late-stage
  pack) -- this skill's delta is that it renders an OFFLINE, SHAREABLE,
  disclosure-scanned bundle with a badge and a manifest, not an in-repo
  markdown artifact.
- The Option B ratification this delivery shape applies:
  `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.
- A cited filled worked example: `docs/worked-examples/retail-store-sales.md`.
