# Tower BI Kit -- F024-F033 Audit + Spec Package (planning report)

- **Date:** 2026-06-25
- **Scope:** Audit the circulated roadmap extension; reconcile duplications; author the
  Spec Kit package for F024-F033 (companion modules + execution adapters + maintenance).
- **Posture:** Planning artifacts only. No runtime code, no dbt/Dagster/Power BI execution
  files, no readiness-gate changes, no commits unless instructed.

> Companion to the visual HTML report (Artifact). This markdown is the durable,
> git-tracked record; the HTML is the presentation layer.

---

## 1. Headline audit finding -- the prose roadmap is out of sync with `main`

The circulated roadmap extension (Phases 0-9, with F034/F035/F036 and a "Phase 0 -- close
PR #23") describes a different state than the committed `docs/roadmap/roadmap.md`:

| Roadmap-extension claim | Committed `roadmap.md` reality |
|-------------------------|--------------------------------|
| Phase 0: close PR #23, then F034 visual implementation is "next" | F005-F015 (incl F011A) are ALL SHIPPED; F016 is the ONLY parked feature |
| "F016 Power BI Execution Adapter" (Phase 4) | AGREES -- F016 is already the committed name. No conflict. |
| F034 / F035 / F036 (visual implementation, theme, screenshot QA) | These F-numbers DO NOT EXIST. The visual FOUNDATION shipped as F011A; the visual *implementation on a real page* is genuinely unspecced (a gap), but is NOT in the F024-F033 deliverable list. |

**Action taken:** authored F024-F033 only (the deliverable list). Flagged the
visual-implementation gap as a recommended future spec, did not author it.

## 2. Duplications reconciled (the "combine if duplication" ask)

Each overlapping spec CITES the shipped feature and scopes itself as the delta; the merge
recommendations live here and in the HTML report. No feature was dropped (the F024-F033
list is explicit) -- "combine" is satisfied by delta-scoping + merge recommendations.

| New feature | Overlaps shipped | Reconciliation |
|-------------|------------------|----------------|
| **F026 Readiness Viewer** | **F012 Data Quality Control Room** (`retail-control-room`) | STRONG. F012 = portfolio findings+blockers roll-up (worst-first). F026 = stage-centric 7-stage lens + evidence-link rendering + approvals timeline. **Recommend:** ship F026 as a stage-view MODE reusing F012's aggregation, or merge if the delta proves thin. |
| **F028 Evidence Pack Generator** | **F013 BI Handoff Pack** (`bi-handoff-pack.md`) | MODERATE. F013 = the Publish-Ready bundle template. F028 = the GENERATOR assembling a 10-section pack across all stages, INCLUDING the F013 pack as section 08. F028 consumes F013; keep both. |
| **F024 Companion Tools Architecture** | the roadmap's informal "Six product layers" | LIGHT. F024 formalizes the layer list into a normative 5-category contract. Cite, do not reinvent. |
| **F029 dbt adapter** | `warehouse/migrations/*.sql` (silver+gold already build) | NOT duplication -- a build-path question. dbt is an OPTIONAL alternative engine that must reconcile to the current gold; migrations stay default until dbt parity is proven. |
| **F030 Dagster** | F005 `retail-orchestrate` conductor | Sibling. retail-orchestrate = agent-conversational sequencer; Dagster = unattended/CI orchestration sibling. |

## 3. New ideas surfaced (recorded, not built)

1. **Visual Implementation MVP gap** -- the true next executable slice on the dashboard
   track (turn an approved blueprint into a real PBIP report page; manual Desktop first,
   git-diff review). Recommend a future spec.
2. **Unified decision ledger** -- F027 (approvals) + F015 (reconciliation ledger) could
   share one append-only audit trail.
3. **Machine-readable category declaration** -- F024's 5-category contract should be a
   declarable field (e.g. tool-manifest front-matter) so F025 can MECHANICALLY verify
   "every tool declares its category". Makes the contract enforceable, not just documentary.
4. **F031 + F032 pairing** -- policy + the version record it enforces; kept as separate
   specs per the explicit list, but noted as a tight pair.
5. **Secret-scan in required checks** -- add a pre-commit secret scan to F031's REQUIRED
   CHECKS, making the existing no-secrets rule a gate, not just a convention.

## 4. The binding architectural rule (every spec holds it)

Core Authority owns truth. Modules and adapters may READ, SUMMARIZE, VISUALIZE, write
DERIVED evidence, or EXECUTE approved steps -- they MUST NOT create truth: no self-granted
approval, no defining business meaning, no approving metrics/mappings, no publishing Power
BI, no moving a readiness stage to `pass` without the required evidence + named human
approval. Every one of the 10 specs declares its allowed/forbidden operations against this.

## 5. Specs created

`specs/018-027` (10 features x 5 files = 50 planning artifacts). Numbering: roadmap
F-number is authoritative; spec-dir is the next free on-disk slot; each header states both.

| F-no | Spec dir | Feature | Category (F024) | Readiness stage |
|------|----------|---------|-----------------|-----------------|
| F024 | 018 | Companion Tools Architecture | (defines the categories) | cross-cutting |
| F025 | 019 | PR Readiness Reviewer | Product Module (read-only) | cross-cutting (guards promotions) |
| F026 | 020 | Readiness Viewer | Product Module (read-only) | cross-cutting (overlaps F012) |
| F027 | 021 | Approval Console | Product Module (artifact-writing) | all (the approval mechanism) |
| F028 | 022 | Evidence Pack Generator | Product Module (artifact-writing) | Publish Ready (overlaps F013) |
| F029 | 023 | dbt Transformation Adapter | Execution Adapter (DB-connected) | Silver/Gold Ready |
| F030 | 024 | Dagster Orchestration Adapter | Execution Adapter (orchestrator) | all (sequences, decides none) |
| F031 | 025 | Adapter Maintenance & Auto-Update Policy | Maintenance Automation | none (protects all) |
| F032 | 026 | Adapter Compatibility Matrix | Maintenance Automation | none |
| F033 | 027 | Release & Maturity Management | Maintenance Automation / Skill | none |

## 6. Recommended first implementation slice

**F024 (Companion Tools Architecture) -> F025 (PR Readiness Reviewer).** F024 is the
foundation every other feature declares against; F025 is the highest-leverage read-only
module (it guards every future promotion) with zero new runtime dependencies. Both are pure
skill/docs -- lowest risk, immediate governance value.

## 7. What must NOT be implemented yet (guardrails)

No runtime code; no dbt files; no Dagster files; no Power BI MCP/execution code; no
publishing automation; no readiness pass/fail rule changes; no module self-grants approval;
dbt does not own mapping/metrics; Dagster does not own readiness pass/fail; no viewer/console
recomputes truth; no C086/retail_store_sales specifics in generic artifacts; no raw datasets;
no secrets/DSNs/tokens/credentials/local paths.

## 7a. Verification performed (this slice)

- 50/50 files present (~1,000-1,170 lines per feature); zero stray non-md files; no agent
  strayed outside its feature directory.
- Independent non-ASCII sweep across all 50 files: zero non-ASCII characters (Principle IX).
- Cross-feature vocabulary: all five F024 categories (Core Authority / Official Workflow
  Skill / Product Module / Execution Adapter / Maintenance Automation) are used consistently
  across the package; F024's own spec enumerates all five; F031 <-> F032 cross-reference.
- `retail check` exits 0 with the specs added. Its only findings are PRE-EXISTING
  warehouse-migration items (the S8 date-table rule on `0002_*`/`0004_*`) this slice did not
  touch; no finding is attributable to the specs and no runtime code was added. (The checker
  does not print a rule-count line, so "count unchanged" is not asserted; "exit 0, no new
  findings, no code added" is the verified claim.)
- The adversarial verify pass fixed 3 real defects in place (F027 task-numbering gap + an
  untagged FR; F029 cross-artifact enumeration mismatch).
- One full spec read end-to-end independently (F026, the strong-overlap case) -- confirmed
  house-standard incl. a substantive scope-delta section with an explicit merge-thinness
  criterion. Plus spot-reads of a plan.md, a tasks.md, and a governance.md.

## 7c. Genuine /speckit-analyze pass (all 10 features) + fixes applied

Ran the real `/speckit-analyze` cross-artifact consistency pass over every feature (F026
in the main thread; F024/F025/F027-F033 via a 9-agent read-only workflow). Result across
all 10: **0 CRITICAL, 0 HIGH**; coverage 100% (F031 94.1% with a now-recorded
satisfied-by-assumption note). The MEDIUM/LOW findings were then FIXED (user-authorized):

| Finding | Feature | Fix applied |
|---------|---------|-------------|
| Rule-count over-claim (`retail check` prints no count line) | 8 features, 45 spots | Reworded to "no new `retail check` rule added (verified by diff); checker stays exit 0". 0 occurrences remain. |
| `approvals[]` field drift: write-back said `date`, slot is `at` | F027 | spec US2 AC1 + FR-008 + tasks T011 now say `at` (= the decision date). |
| F008 mislabeled as the source-map producer | F028 | Reattributed: F008 = Grain Confidence + Mapping Diff Reviewer; it CONSUMES `source-map.yaml` (the Principle-IV mapping-gate artifact). |
| `dim_date_rss` "NO -1 member" contradicted migration 0004 (which inserts one; S8 flags it) | F029 | Restated the parity target AS COMMITTED + flagged the pre-existing S8/docs split-brain (16110d8); F029 reproduces gold as-is, does not resolve it. |
| ADR range `0001-0006` over-claimed (only 0001-0004 exist) | F031 | Corrected to `0001-0004` in plan + tasks. |
| FR-002 (PR-based / no gate-skip) untraceable | F031 | Added T023 recording it as satisfied-by-assumption (inherited global git rules + branch protection; enforced by governance.md). |
| SC-004 missing its task tag | F032 | Added `[SC-004]` to T014. |

Checker-provenance correction (important): during most of this session `retail check` was
importing the `retail` package from a SIBLING worktree
(`Retail_Tower_analytics-dax-fortify`, branch `feat/dax-fortify-d9`), which carries an
extra ERROR rule **S8** (date dims must NOT have a `-1` member) that this repo's `main`
does NOT have. That is why an `[error] S8 ...` appeared against `0002`/`0004`. A CLEAN-ROOM
re-run, with the import pinned to THIS repo's own `src` (verified `has S8: False`), shows
`retail check` **exit 0 with NO findings at all**, and **zero findings reference
`specs/018-027`** -- so the 50 spec files add no `retail check` finding under `main`'s own
S1-S7 gate. The S8/`dim_date` `-1`-member fix is already COMPLETE in the dax-fortify PR
(migrations 0002 + 0004 de-sentinel the date dim and de-COALESCE the fact date FK; S6 was
amended to exempt `dim_date*`; ADR 0006 governs; S8 is ERROR severity). No migration change
is needed in this worktree -- the fix belongs to that PR.

All fixes verified: 50/50 files intact, ASCII-clean, `retail check` exit 0 under main's own
checker with zero findings against the spec package, no new files.

## 7b. Note on the "Actors" required element

The task listed "actors" among the mandatory per-spec elements. The repo's established
house style (specs/010, specs/013) carries actor information inside **User Stories** ("A
human (or the agent) asks ...") rather than a standalone `## Actors` heading, and the task
also required matching house style. Conscious decision: the actor of every one of these 10
features is the same pair -- the **agent** (proposes/renders/composes) and a **named human
owner** (decides/approves) -- which each spec states explicitly in its User Stories and its
`## Human approval boundary` section. No separate `## Actors` heading was added, to avoid
diverging from house style; if a standalone Actors block is preferred, it is a one-line
addition per spec.

## 8. Open questions for the owner

1. **F026 vs F012:** ship F026 as a mode of F012, or merge them? (Recommendation:
   stage-view mode; revisit merge after F026's delta is sized in planning.)
2. **dbt build-path:** is dbt intended to REPLACE the migration build eventually, or remain
   an optional parallel engine? (Recommendation: optional until gold parity is proven.)
3. **Visual implementation gap:** author the F034-style "Visual Implementation MVP" spec
   next, or keep the dashboard track at foundation (F011A) until F016 lands?

## See also

- The HTML report (Artifact) -- the visual presentation of this audit.
- `docs/roadmap/roadmap.md` (the committed, authoritative sequence).
- `.specify/memory/constitution.md` (Principles I-IX).
- `docs/architecture/tower-bi-agent-kit.md`, `docs/readiness/readiness-model.md`.
- The 10 specs under `specs/018-027/`.
