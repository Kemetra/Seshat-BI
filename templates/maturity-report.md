<!--
=============================================================================
 maturity-report.md  --  the copy-me point-in-time MATURITY LADDER snapshot
=============================================================================
 Seshat BI Agent Kit  -  feature F033 (Release & Maturity Management).
 On-disk spec: specs/027-release-maturity-management/  (dir 027 == roadmap F033;
 when the dir number and the F-number disagree, the roadmap F-number wins).
 See: .claude/skills/release-notes-generator/SKILL.md (the draft-and-assess verb),
      templates/release-notes.md (the SEPARATE per-release note -- a distinct artifact;
      never merge the two),
      docs/readiness/readiness-model.md (the seven numbered readiness STAGES this
      ladder is structurally modeled on -- legitimate milestones, NOT scores),
      docs/architecture/product-modules.md (F024: Maintenance Automation -- assesses
      derived evidence; creates no truth, grants no approval).

 THE LADDER IS A MILESTONE LADDER, *NOT* A SCORE  (FR-006 -- the crux; read first)
   The maturity ladder is an EVIDENCE-GATED MILESTONE ladder: each rung carries a BINARY
   "this evidence exists or it does not" test, and the kit's level is the HIGHEST rung
   whose required evidence ALL exists. This is structurally the SAME kind of artifact as
   the seven numbered readiness stages (docs/readiness/readiness-model.md) -- those are
   legitimate ordinal milestones, never scores, and so is this. The numbered rungs
   L0..L6 are milestone NAMES; the number is an ordinal milestone, never a quantity.

   A filled copy MUST NOT emit a percentage, a 0-100 health number, an average, or ANY
   number that reads as confidence (hard rule #9). A rung is reported "achieved
   (evidence: ...)" or "not achieved (missing: ...)" -- never "73% mature". If a numeric
   maturity score is requested, the generator DECLINES, cites hard rule #9, and returns
   the rung verdicts + cited evidence instead.

   A rung is BINARY -- achieved or not achieved -- NOT one of the four readiness statuses
   (not_started / blocked / warning / pass). Partial evidence (one worked example done,
   the second mid-build) is "not achieved" with the missing piece named; it is NEVER
   rounded up.

 CONSUME, NEVER RE-MEASURE; NEVER SELF-CONFIRM  (FR-009 / FR-010)
   The generator ASSESSES each rung from already-committed evidence + on-disk presence.
   It runs NO retail check / retail validate, profiles NO source, opens NO DB connection,
   reads NO powerbi/. It never self-confirms a level: a named RELEASE OWNER confirms the
   reported level (Core Authority / Principle V). A missing input -> "evidence not
   available", never fabricated.

 HOW TO USE
   Copy into docs/releases/<F-number>/maturity-report.md alongside the release note, fill
   every <ANGLE-BRACKET> field, delete this banner, keep it committed. GENERIC -- no
   per-table logic baked in (Principle VII); the worked tables may be CITED as the
   evidence the L1/L2/L3 tests check (allowed), never inlined as template logic. ASCII +
   UTF-8 no BOM; '--' and '->' only; short repo-relative paths (Windows MAX_PATH).
=============================================================================
-->

# Maturity Report -- the kit, as of <RELEASE F-NUMBER / date>

- **Roadmap feature (this snapshot's release):** `<Fxxx>`  **On-disk spec:** `<specs/0NN-...>`
- **Assessed by:** `release-notes-generator` (F033, Maintenance Automation -- assesses
  derived evidence; creates no truth, grants no approval, confirms no level)
- **Reported level:** `<L0..L6>`  *(the HIGHEST rung whose required evidence ALL exists -- not a score)*
- **Level confirmed by:** `<named release owner + YYYY-MM-DD, or: unconfirmed -- awaiting release owner>`

> The reported level is the highest all-evidence-present rung. The generator ASSESSES it;
> a named release owner CONFIRMS it (Core Authority). A level the evidence does not back
> is refused by the binary test regardless of who asks (Principle V). No production / GA /
> enterprise-grade claim is made unless an evidence rung backs it.

## The seven evidence-gated rungs (binary test per rung)

Each rung is achieved IFF its binary evidence test passes. The reported level is the
highest rung whose required evidence ALL exists; rungs above it are "not achieved" with
the exact missing artifact named. Rung order is a capability-evidence milestone narrative,
independent of the roadmap's F-sequence -- it does NOT imply F016 is the sequencing apex
(F016 remains the deliberately-last, bottom-of-stack execution-only adapter that no
readiness stage depends on).

| Rung | Capability | Binary evidence test (achieved iff this exists) | Verdict | Cited evidence (achieved) / missing artifact (not achieved) |
|------|------------|-------------------------------------------------|---------|-------------------------------------------------------------|
| L0 | docs only | the kit's docs/templates/spec-kit artifacts exist | `<achieved | not achieved>` | `<e.g. docs/medallion-playbook.md, docs/readiness/readiness-model.md / or: missing ...>` |
| L1 | one worked example | >= 1 worked-example table with mapping artifacts under `mappings/` | `<...>` | `<e.g. mappings/<table-a>/ / or: missing ...>` |
| L2 | two worked examples | >= 2 worked-example tables with mapping artifacts under `mappings/` | `<...>` | `<e.g. mappings/<table-a>/ + mappings/<table-b>/ / or: missing ...>` |
| L3 | repeatable silver / gold | silver + gold proven repeatable for the >= 2 worked tables (each has silver + gold) | `<...>` | `<cited silver+gold for the worked tables / or: missing ...>`  -- forward scope-note (if achieved): generic repeatability beyond the worked tables is the NEXT evidence (a scope-note on the achieved verdict, NOT an unmet gate) |
| L4 | dbt transformation adapter | a dbt transformation adapter (F029) exists in-repo | `<...>` | `<cited adapter path / or missing: a dbt transformation adapter (F029) in-repo>` |
| L5 | Dagster orchestration | a Dagster orchestration project (F030) exists in-repo | `<...>` | `<cited project path / or missing: a Dagster orchestration project (F030) in-repo>` |
| L6 | official Power BI execution adapter | an official Power BI execution adapter (F016) exists in-repo | `<...>` | `<cited adapter path / or missing: an official Power BI execution adapter (F016) in-repo>` |

## Reported level (the highest all-evidence-present rung)

> **Reported level: `<L0..L6>`** -- the highest rung whose binary evidence test ALL
> passes. Rungs above it: `<list each not-achieved rung + its named missing artifact>`.
> This is a milestone, NOT a score; no number is emitted.

## Standing notes (honest current state)

- The unbuilt rungs are reported NOT achieved with the missing artifact NAMED -- never
  rounded up, never implied. Today those are typically `<L4 dbt (F029), L5 Dagster (F030),
  L6 official Power BI execution adapter (F016)>` until each is built.
- L3 (repeatable silver/gold) is ACHIEVED when the binary test holds for the worked
  tables; its repeatability-beyond-the-worked-tables caveat is a FORWARD scope-note on the
  achieved verdict, NOT an unmet gate (this preserves the binary contract without rounding
  up).
- No rung is a percentage; no "N of 7 rungs" tally is emitted (the per-rung binary verdict
  conveys the state -- a count would read as a score, hard rule #9).

## Conflicts surfaced (if any)

When inputs disagree (e.g. the F032 compatibility matrix asserts an adapter version
interoperates but no such adapter exists in-repo), the conflict is RECORDED here as a
finding and left for the human to resolve -- the generator never resolves it by picking a
side (Principle V).

- `<conflicting inputs + the two sources>` -- *(unresolved; release owner decides)*
- `<... or: none>`

## See also

- The draft-and-assess verb: `../../.claude/skills/release-notes-generator/SKILL.md`.
- The SEPARATE per-release note: `release-notes.md` (a distinct artifact; never merged
  with this snapshot).
- The seven numbered readiness STAGES this ladder is structurally modeled on (milestones,
  not scores): `../../docs/readiness/readiness-model.md`; hard rule #9.
- The consumed inputs (by id + role): `../../docs/tools/evidence-pack-generator.md` (F028),
  the F032 compatibility matrix (`../../specs/026-adapter-compatibility-matrix/spec.md`).
- The authority contract (this skill is Maintenance Automation -- no sub-axis):
  `../../docs/architecture/product-modules.md`.
- The worked example that grounds the L1/L2/L3 tests: `../../docs/worked-examples/retail-store-sales.md`
  (its mapping artifacts live under `mappings/retail_store_sales/`; a FILLED snapshot cites
  these as evidence, plus any further worked tables added under `mappings/<table>/`).
- The spec: `../../specs/027-release-maturity-management/spec.md`.
