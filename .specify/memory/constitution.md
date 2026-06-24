<!--
Sync Impact Report
==================
Version change: 1.0.0 -> 1.1.0 (amendment 2026-06-24)
Amendment rationale (1.1.0, MINOR -- scope expansion, no compliance-posture
                change to any principle): Spec-Kit was initialized into the
                repo via `specify init --here --integration claude --script ps`,
                adding `.specify/templates/`, `.specify/scripts/powershell/`,
                `.specify/{integration,extensions}.*`, and the `speckit-*`
                agent skills. This expands the Scope Boundaries clause that
                previously said "the rest of a Spec-Kit init is NOT scaffolded."
                The hand-authored constitution was preserved unchanged by the
                init (verified byte-identical to commit 7a691e0). No principle
                is added, removed, or redefined. Dependent artifacts updated:
                Scope Boundaries clause (this file), spec Assumptions
                (specs/001-retail-bi-agent-kit/spec.md). CLAUDE.md received an
                additive SPECKIT pointer block from the init (not a constitution
                edit).

Version change: none -> 1.0.0 (initial ratification)
Bump rationale: Initial ratification of the Tower BI Agent Kit Constitution.
                This document does NOT make new decisions. It RATIFIES,
                as non-negotiable principles, decisions already shipped on
                main: the 23-rule static governance core (src/retail/), the
                7-phase medallion playbook, the ADR 0002 cleaning/modeling
                defaults (D1-D16), the C086 worked example, and the A->C->D
                governance design (depend-not-fork, gold-only). Where a
                principle could read as a fresh ruling, it cites the
                already-committed artifact it is the expression of.

Added principles:
  I.    Agent-First, Gate-Enforced
  II.   Depend, Never Fork
  III.  Medallion, Postgres-First, Gold-Only
  IV.   Source Mapping Before Silver
  V.    Agent Stops at Judgment Calls
  VI.   Defaults Then Deviations
  VII.  C086 Is An Example, Not The Schema
  VIII. Static-First Governance, Live Deferred
  IX.   Secrets and Reproducibility

Added sections:
  - Identity statement (preamble)
  - Medallion and Source-of-Truth
  - Scope Boundaries (this Phase 0/1 slice)
  - Governance

Removed sections:
  - None (initial ratification).

Dependent kit artifacts (this set of 8 files; this is the keystone normative
doc the others are the expression of):
  done (this slice)      docs/architecture/tower-bi-agent-kit.md   (cross-links this file in its "See also")
  done (this slice)      specs/001-retail-bi-agent-kit/spec.md     (Phase 0/1 feature spec; references this Constitution)
  done (this slice)      templates/source-profile.md               (mapping-gate artifact; Principle IV)
  done (this slice)      templates/source-map.yaml                 (mapping-gate artifact; Principle IV)
  done (this slice)      templates/assumptions.md                  (mapping-gate artifact; Principles IV, VI)
  done (this slice)      templates/unresolved-questions.md         (mapping-gate artifact; Principles IV, V)
  done (this slice)      templates/reconciliation-report.md        (mapping-gate artifact; Principle VIII live category)
  deferred (future amend) CLAUDE.md (repo)                         (a constitution-at-a-glance pointer is OUT OF SCOPE for this docs/templates slice; add by amendment later)

Follow-up TODOs (recorded; not resolved in this ratification):
  - D-namespace collision: ADR 0002 numbers cleaning/modeling defaults
    D1-D16; the static checker numbers its TMDL/DAX rules D1-D8. Same D
    prefix, two namespaces. Flagged here and across the kit docs;
    deliberately NOT resolved and nothing renamed. Must be disambiguated
    before any ADR default is wired into retail check.
  - Where per-table mapping artifacts live (mappings/<table>/ vs alongside
    the migration vs docs/) is undecided (architecture doc, Open decision 2).
  - Layer D agent orchestration shape is a seam, not a runtime, in this slice
    (architecture doc, Open decision 3).
  - The retail validate live-validator surface needs its own spec before
    implementation (architecture doc, Open decision 4; Principle VIII).
-->

# Tower BI Agent Kit Constitution

The Tower BI Agent Kit is a standalone, agent-first way to turn a raw retail
source table into a governed Power BI semantic model along the path
source -> mapping -> silver -> gold -> Power BI. An AI agent drives the
workflow; enforced static checks gate every step; pbi-cli is a later adapter at
the bottom of the stack, not the core. This kit is a standalone analytics
service and is NOT bound by the Retail Tower OS orchestrator or its
contract-boundary rules (see the repo `CLAUDE.md`). Power BI is the primary
surface; the source substrate is a DigitalOcean Postgres medallion warehouse
(`bronze` -> `silver` -> `gold`), from which Power BI reads the `gold` schema
only.

This Constitution defines the non-negotiable principles for all specs, plans,
tasks, templates, and implementations in this repository. It uses
MUST / SHOULD / MUST NOT language. It contains no application code. It does not
re-decide settled work: it ratifies, as principles, decisions already committed
on main, and each principle cites the artifact it is the expression of.

## Core Principles

### I. Agent-First, Gate-Enforced
The agent is the interface; the enforced check is the contract.

- The primary surface is the agent (architecture Layer D): an agent runs the
  medallion playbook conversationally and self-heals against the gate. The
  terminal command (`retail check`) is the gate the agent CALLS, not the
  product a human operates. The kit is agent-first, not terminal-first
  (architecture North-Star correction #1).
- The governance contract is a NON-ZERO PROCESS EXIT from the static checker,
  not a paragraph of prose. A violation MUST fail closed (block commit/PR via
  the Layer C hook + Action), never merely advise. "Enforced, not advised"
  is the design's core claim (governance spec, A->C->D layering).
- Compliance MUST be demonstrable by running `retail check` over committed
  text. A claim of compliance unsupported by a passing checker run is not
  compliance.
- The agent MUST NOT be the authority on whether a rule passed; the checker
  exit code is. The agent proposes; the gate disposes.

**Rationale**: A prose convention drifts the moment it is inconvenient; a
non-zero exit does not. Making the gate (not the agent, not a reviewer's
attention) the contract is what lets an agent drive the workflow autonomously
without lowering the floor. This ratifies the governance spec's enforced-gate
posture and the architecture's Layer D / Layer A split.

### II. Depend, Never Fork
The opinion lives in this repo; the engine is borrowed and upgradeable.

- `pbi-cli` MUST be consumed as an external dependency installed via `pipx`,
  unforked and independently upgradeable. The kit MUST NOT vendor, fork, or
  re-implement it (governance spec, settled decision #1: depend-not-fork).
- `pbi-cli` is a LATER Power BI semantic-model adapter at the bottom of the
  stack (architecture ENGINE row), not the core and not the center of gravity
  (architecture North-Star correction #4). It is the engine the agent's
  authoring step executes against; it is not what the kit IS.
- All retail opinion -- the governance rules, the cleaning defaults, the
  templates, this Constitution -- MUST live in this repository, on top of the
  unopinionated engine. There MUST be no "fork tax": upgrading `pbi-cli` MUST
  NOT require re-applying local patches.

**Rationale**: Forking a maximally capable, opinion-less tool to add opinion
permanently strands the kit on a snapshot and turns every upstream improvement
into a merge conflict. Depending on it and layering opinion above keeps the
engine current and the opinion ours. This ratifies governance-spec decision #1.

### III. Medallion, Postgres-First, Gold-Only
One substrate, one read surface, one source of truth.

- The data substrate is the DigitalOcean Postgres medallion warehouse with
  schemas `bronze` -> `silver` -> `gold`. Data flows in that direction only.
- Power BI MUST read the `gold` schema only. Power BI MUST NOT read `silver`
  or `bronze` (governance spec, settled decision #3: gold-only).
- The MVP is Postgres-first. There MUST NOT be a DuckDB/Parquet-first ADR or a
  gold-as-Parquet materialization in the MVP: Power BI Import mode already
  caches columnar at refresh (VertiPaq), so a Parquet copy of `gold` would be a
  redundant second source of truth (architecture North-Star correction #5).
- `gold` MUST be a Kimball star (fact + conformed dimensions), the single
  shape the BI model binds to.

**Rationale**: A single downstream read surface (`gold`) keeps the BI model's
contract narrow and the lineage legible; reading `silver`/`bronze` from Power BI
would couple the report to ungoverned intermediate state. Refusing a
Parquet-first layer avoids maintaining two columnar copies of the same truth.
This ratifies governance-spec decision #3 and architecture North-Star #5.

### IV. Source Mapping Before Silver
The source-mapping gate: map before you build.

- Before any `silver.*` SQL is written, the source MUST be profiled and mapped
  into committed, reviewable artifacts, and that mapping MUST be reviewed and
  approved. Silver is downstream of an approved map. This is a GATE, not a
  suggestion (architecture North-Star correction #3, section 5).
- The load-bearing decisions -- grain, primary key, PII handling, and gold star
  placement (fact measure / dimension attribute / degenerate dim) -- MUST be
  committed AS DATA in the mapping artifacts before any schema is cut.
- The mapping gate FORMALIZES existing method; it does not invent a new one.
  It elevates the medallion playbook's Phase 1 (connect and profile),
  Phase 2.0-2.5 + 2.7-2.8 (grain-first cleaning decisions), Phase 2 + 3
  decision points, and the Phase 4 review gate into mandatory committed
  artifacts. The five templates ARE those artifacts:
  `source-profile.md` (Phase 1), `source-map.yaml` (Phase 2.0-2.5/2.7-2.8),
  `assumptions.md` (Phase 2 + 3), `unresolved-questions.md`
  (Phase 2 decision points + Phase 4), `reconciliation-report.md` (Phase 5/6).
- Where the playbook and the templates could appear to compete, the playbook is
  authoritative on HOW to decide; the templates are authoritative on WHAT to
  record and in what shape. The playbook's Phase 4 review IS the mapping-gate
  review. The agent MUST NOT silently fork a second method.

**Rationale**: Writing silver SQL first bakes ungoverned grain, type, and PII
decisions into a table that gold's foreign keys then depend on. Reversing them
means rebuilding gold and re-publishing the cached BI model -- effectively
irreversible. Forcing grain/PK/PII/placement to be committed and reviewed as
data first is the one new load-bearing idea this kit adds, and it is purely a
formalization of the playbook (medallion-playbook.md; architecture section 5).

### V. Agent Stops at Judgment Calls
The agent recommends; a human decides anything not provable from data.

- The agent MUST NOT decide alone, and MUST raise an entry in
  `unresolved-questions.md`, for: business-rollup / segment mappings (the
  playbook NEVER invents these -- an analyst MUST supply the full
  value->group table); PII publish-safety (governance MUST sign off; the
  default is drop); grain ambiguity (a row-vs-entity mismatch, or a candidate
  PK not unique on the data); sentinel-vs-null choice on a column; and any
  unresolved question that blocks the build.
- No `silver.*` SQL is written while any build-blocking question is unanswered.
  Accepting a proposed default is itself a decision and MUST be recorded by the
  named owner (analyst / governance / data-owner).
- The agent MUST surface conflicts, never bury them: if an answer contradicts an
  earlier decision or a profiled data fact, the agent MUST stop and reconcile
  rather than proceed (this is the Socratic Evidence-Cross-Check posture applied
  to the build).

**Rationale**: This kit is agent-first (Principle I); without an explicit
stop-and-ask floor, autonomy silently invents the very business / PII / grain
decisions the medallion playbook reserves for a human. The gate (Principle I)
disposes of rule-pass authority; this principle disposes of judgment authority.
This ratifies the playbook's interaction protocol ("recommend, then let the
analyst decide") and its Phase 2 decision points, and is realized by the
`unresolved-questions.md` template.

### VI. Defaults Then Deviations
Start from the rulings already made; record only what you change.

- Every new table MUST start from the ADR 0002 cleaning/modeling defaults
  (D1-D16): lowest grain, PK verified on transformed data, drop no-signal
  columns, PII removed early, `''` -> NULL, sentinels only on grouping dims,
  exact NUMERIC money/qty with leading-zero IDs kept TEXT, returns from the
  authoritative column, independent money measures, unified encodings, rollups
  only from analyst mapping, flat non-tree hierarchies, silver as an idempotent
  numbered migration, gold as a Kimball star with a `-1` unknown member and FK
  COALESCE and degenerate dims, a contiguous `generate_series` date dimension,
  and reconciled measure totals with zero orphan FKs.
- The `assumptions.md` artifact MUST record which defaults were ADOPTED as-is
  versus DEVIATED from, and every deviation MUST cite the triggering DATA FACT
  that justified it. Review then sees only what changed.
- A deviation without a recorded triggering data fact is a defect. Defaults
  MUST NOT be silently overridden.
- D-namespace collision (flagged, NOT resolved here): ADR 0002 numbers these
  cleaning/modeling defaults D1-D16, while the static checker (Principle VIII)
  numbers its TMDL/DAX rules D1-D8. Same D prefix, two distinct namespaces.
  This is flagged across the kit and MUST NOT be silently conflated; nothing is
  renamed in this ratification.

**Rationale**: Re-deriving grain, type, and star-schema decisions per table is
how an analytics codebase accumulates the unreviewed drift this kit exists to
prevent. Starting from a validated default set and recording only evidence-backed
deviations keeps review cheap and the reasoning auditable. This ratifies the
spirit of docs/decisions/0002-retail-cleaning-defaults.md.

### VII. C086 Is An Example, Not The Schema
The questions and gates generalize; the answers are per-table.

- C086 (the first worked example) is a FILLED INSTANCE of every template, cited
  as a reference, and MUST NOT be treated as the universal schema (architecture
  North-Star correction #2).
- The templates, this Constitution, and the architecture MUST stay generic.
  Worked-example-specific facts (billing codes, business segments, insurance or
  other PII columns, per-table grain keys) belong to that example's own
  artifacts and MUST NOT be baked into the kit's generic templates or principles.
- Templates MUST use placeholders and cite the worked example as the filled
  instance, never copy its answers inline. See
  `docs/worked-examples/c086-pharmacy.md` for what a fully filled set looks like
  (validated 16/16 against the ADR defaults on a live database).

**Rationale**: A kit whose templates carry one table's specifics is a kit that
only fits one table. Keeping the example cited-but-external is what makes the
pattern reusable across every future retail source. This ratifies architecture
North-Star #2.

### VIII. Static-First Governance, Live Deferred
Ship the static core; defer live validation to a named later surface.

- The shippable governance core is the STATIC checker: 23 rules over committed
  TMDL / PBIR / SQL / git text, stdlib-only and CI-able, with NO dependency on
  pbi-cli, Power BI Desktop, or the network. It is the enforced gate that
  ships now (src/retail/; governance spec, static surface).
- The 23 rules span the namespaces S1, S2, S3, S4a, S4b; D1-D8; R1; C1, C2;
  G1-G5; P1, P2. (The checker's D1-D8 is a DISTINCT namespace from ADR 0002's
  D1-D16; see Principle VI.)
- LIVE validators (PK uniqueness on materialized rows, date-dim coverage, zero
  orphan FKs, penny-exact cross-layer measure reconciliation) are DEFERRED to a
  later `retail validate` surface (architecture North-Star correction #6,
  section 7). This slice documents their CATEGORIES only and MUST NOT implement
  validator logic.
- `reconciliation-report.md` is the committed BLANK that a future live run fills;
  authoring it now does not constitute implementing a live validator.

**Rationale**: A static checker that needs nothing but committed text runs in CI
on every commit and never depends on a live database or a desktop being up;
that is what makes it the dependable floor. Live checks are valuable but require
a running database/model and belong to a surface with its own spec. This
ratifies the governance spec's static-now / live-deferred taxonomy.

### IX. Secrets and Reproducibility
Credentials stay out of git; artifacts are reproducible and Windows-safe.

- Secrets MUST live only in a git-ignored `.env`. Real credential values MUST
  NOT be written into any tracked file.
- Power BI MUST use parameters for connection details, never baked-in
  connection strings.
- Silver and gold builds MUST ship as numbered, idempotent migrations
  (re-running a migration MUST converge to the same state).
- PBIP and other tracked text MUST be UTF-8 without BOM; rely on
  `.gitattributes` and `core.autocrlf=true` for line endings.
- Repo-relative paths for PBIP projects, tables, and migrations MUST stay short
  (target `<= 200` characters repo-relative) to respect the Windows `MAX_PATH`
  limit.

**Rationale**: A leaked credential, a noisy line-ending diff, or a path that
exceeds Windows `MAX_PATH` are the cheap-to-prevent, expensive-to-recover
failures of a Power-BI-on-Windows analytics repo. Codifying the posture now keeps
it free. This ratifies the hard rules in the repo `CLAUDE.md`.

## Medallion and Source-of-Truth

- Pipeline direction is `bronze` -> `silver` -> `gold`, one way. Cross-layer
  back-writes are forbidden.
- `bronze` is the landed raw source; `silver` is cleaned at the lowest grain;
  `gold` is the Kimball star Power BI binds to.
- Power BI reads `gold` only (Principle III). The BI model MUST NOT reach into
  `silver` or `bronze`.
- The single source of truth for cleaning/modeling rulings is
  `docs/decisions/0002-retail-cleaning-defaults.md`; for method, it is
  `docs/medallion-playbook.md`; for the enforced static gate, it is
  `src/retail/` as designed in the governance spec. This Constitution is their
  expression, not a competing copy. A conflict between this file and a cited
  artifact is a defect in this file, to be reconciled by amendment.

## Scope Boundaries

This is the Phase 0/1 foundation. It deliberately stops at architecture, spec,
and templates (architecture doc, section 8). Out of scope for this slice:

- NO validator scripts. Live-validator CATEGORIES are documented only
  (Principle VIII).
- NO `pbi-cli` integration or wiring. It is placed as the later adapter,
  not connected (Principle II).
- NO CLI installer. NO Spec-Kit preset or custom bundle.
  **(Amended v1.1.0, 2026-06-24):** Spec-Kit IS now initialized into the repo
  (`specify init --here --integration claude --script ps`): the canonical
  `.specify/templates/`, `.specify/scripts/powershell/`, and the `speckit-*`
  agent skills now back the spec -> plan -> tasks chain. The hand-authored
  `.specify/memory/constitution.md` is preserved unchanged by the init and
  remains the source of truth. Still out of scope: presets, custom bundles, and
  the bring-your-own extensions surface beyond the default init.
- NO new warehouse tables, NO database writes, NO moving of existing docs.
- NO implementation beyond architecture, spec, and templates.

## Governance

This Constitution supersedes ad-hoc conventions for this repository. The
enforcement mechanism is the static checker's exit code (Principle I), not a
prose checklist: a change that introduces a governance violation is caught by a
non-zero `retail check` exit at the Layer C hook/Action, and MUST be brought
into compliance before merge.

**Amendment procedure**:
1. Edit `.specify/memory/constitution.md` and bump the version per the policy
   below.
2. Update the Sync Impact Report comment at the top of this file.
3. Propagate the change to the dependent kit artifacts listed in that report
   (the architecture doc, the feature spec, the five templates, repo CLAUDE.md),
   and to any cited authoritative artifact whose decision changed.
4. Because this Constitution ratifies decisions that live elsewhere, an
   amendment that changes a ratified decision MUST also amend the artifact that
   owns it (e.g. ADR 0002, the governance spec) -- this file MUST NOT become a
   second, divergent source of truth.

**Versioning policy** (semantic):
- MAJOR: backward-incompatible removal or redefinition of a principle/section,
  redefinition of the kit's identity, or addition of a new non-negotiable
  principle.
- MINOR: a new supporting section, or a materially expanded clause within an
  existing principle that does not change prior compliance posture.
- PATCH: clarifications, wording fixes, non-semantic edits.

**Compliance review**: a lightweight review of constitution adherence SHOULD
occur at the close of each slice (the next being the resolution of the
D-namespace collision and the `retail validate` live-surface spec). Findings
feed back into amendments.

**See also**: `docs/architecture/tower-bi-agent-kit.md` (the engineering
expression of these principles); `specs/001-retail-bi-agent-kit/spec.md` (the
Phase 0/1 feature spec); `docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`
(the A->C->D governance design); `docs/medallion-playbook.md` (the method);
`docs/decisions/0002-retail-cleaning-defaults.md` (the defaults, D1-D16);
`docs/worked-examples/c086-pharmacy.md` (the first filled instance).

---

**Version**: 1.1.0 | **Ratified**: 2026-06-24 | **Last Amended**: 2026-06-24
