# Idea Bank -- ADOPT Shortlist (2026-08-22 run)

## 1. Purpose

This document RECORDS the eight candidates the idea-engine's reviewer panel ranked
ADOPT in the `wf_97a589cd-7d2` run of 2026-08-22, so the shortlist survives the next
regeneration of the bank. It is the same kind of artifact as
`top-idea-bank-execution-plan.md`: a bridge between exploratory ideas and real feature
work, and nothing more.

- This document is **recording only**. It changes no runtime behavior.
- This is **not implementation**. No idea below is built here.
- This is **not a roadmap commitment**. The Idea Bank
  (`docs/roadmap/idea-backlog.md`) remains exploratory; the authoritative roadmap
  stays `docs/roadmap/roadmap.md`. No idea below has an F-row, and this document
  assigns none -- a human places F-rows (Principle V).
- **ADOPT is the reviewer panel's triage opinion, not an approval.** Each idea still
  needs an explicit human decision and the repo's normal spec/feature process.
- The V/F numbers are the panel's carried-forward triage opinion, never a readiness
  or confidence score (hard rule #9).

**Status**: Recorded, not ratified as a batch -- but SUPERSEDED IN PART by delivery.
Verified against `origin/main` on 2026-08-23: **c22** (PR #706, `5451baf1`), **c27** and
**c29** (PRs #707/#708, `9bbfcbde`) and **c41** (PR #704, `1e1ea518`) have shipped, and
**c2** was already live as a knowledge route (`skills/bi-sql-knowledge/INDEX.md`, commit
`e6c421a4`) when this shortlist was written -- its ADOPT verdict rested on a
code-consumer check that a routed knowledge corpus does not need. **c10** is built and
under review on PR #709, not yet merged. Only **c19** (widen `dax_gen` past `base|ratio`)
and **c35** (answer freshness header) remain open, and neither has been ratified.

This section is a dated record; it is not rewritten as ideas ship. Read the per-idea
rows below as the panel's 2026-08-22 opinion, not as current ship status.

## 2. Why these eight, and why the count is not comparable to prior runs

The 2026-07-10 run produced **0 ADOPT**; this run produced **8** from a comparable
panel and identical thresholds. The difference is a fixed defect, not a loosened gate:
candidate identity used to be inferred from free-text titles, so one idea split into
two or three reviewer rows with divergent scores and could never reach the 2-of-4
majority ADOPT requires. Identity is now a JS-stamped id (`c1..cN`), so the panel's
real consensus is visible. No clamp, rank or threshold was changed.

ADOPT requires 2+ of 4 reviewers independently choosing it AND a unanimous full-panel
eligibility pass. All eight rows below passed the gate cleanly (`gate=pass`) and
survived the adversarial skeptic (`survived`), which is why they are the shortlist.

## 3. The shortlist

Ordered by V+F. `id` is the run-local candidate id, useful for finding the full
rationale and panel dissent in the bank; it is NOT a stable cross-run key.

| # | id | Idea | V/F | Serves | Layer |
|---|---|---|---|---|---|
| 1 | `c41` | Make ONBOARDING.md actually onboard someone to Seshat BI | 8/9 | operator | docs-spine |
| 2 | `c22` | Fix-at-the-point-of-failure: annotate check findings with the rule's own means/fix line | 8/8 | operator | none |
| 3 | `c27` | Token Ref-Pointer Resolution Guard (dangling `*_ref` and `grid_ref` paths) | 7/8 | operator | design-system |
| 4 | `c29` | Section-Vocabulary Parity Across Grid, Mobile Grid and Blueprints | 7/8 | operator | design-system |
| 5 | `c2` | EXPLAIN-Plan Review Surface over the shipped PostgreSQL plan knowledge | 7/7 | end_user | bi-sql |
| 6 | `c10` | Domain Pack Interview Cards -- turn a KPI domain into owner questions | 7/7 | operator | retail-kpi |
| 7 | `c19` | Widen dax_gen beyond base\|ratio: the variance/two-table contract shape | 8/6 | end_user | bi-dax |
| 8 | `c35` | Answer Freshness Header -- how old is the proof behind this number | 7/7 | end_user | docs-spine |

## 4. Per-idea record

Each entry carries the panel's own first step verbatim. A first step is a suggested
entry point, not an instruction to proceed.

### 1. Make ONBOARDING.md actually onboard someone to Seshat BI

- **Candidate id (run-local)**: `c41`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 8 / 9 (panel median)
- **Horizon**: NOW | **Serves**: operator | **Strengthens**: docs-spine
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Move the existing usage-stats content to a differently-named file, then write the four-part routing page pointing at each stage doc's own self-label.

### 2. Fix-at-the-point-of-failure: annotate check findings with the rule's own means/fix line

- **Candidate id (run-local)**: `c22`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 8 / 8 (panel median)
- **Horizon**: NOW | **Serves**: operator | **Strengthens**: none
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Ship the additive text --explain footer against the documented [severity] id message (locator) shape, with a test asserting exit code and severity are byte-identical with and without the flag.

### 3. Token Ref-Pointer Resolution Guard (dangling `*_ref` and `grid_ref` paths)

- **Candidate id (run-local)**: `c27`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 7 / 8 (panel median)
- **Horizon**: NOW | **Serves**: operator | **Strengthens**: design-system
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Enumerate every pointer-shaped key in the tokens and blueprint corpora by hand first, so the suffix convention is validated against the real key set rather than assumed.

### 4. Section-Vocabulary Parity Across Grid, Mobile Grid and Blueprints

- **Candidate id (run-local)**: `c29`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 7 / 8 (panel median)
- **Horizon**: NOW | **Serves**: operator | **Strengthens**: design-system
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Confirm 16x9-grid.yaml is the sole declarer of `zones` across the four files, then assert each filled blueprint's section values are a subset of it.

### 5. EXPLAIN-Plan Review Surface over the shipped PostgreSQL plan knowledge

- **Candidate id (run-local)**: `c2`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 7 / 7 (panel median)
- **Horizon**: NOW | **Serves**: end_user | **Strengthens**: bi-sql
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Fix the input contract for a pasted plan (what a minimal acceptable EXPLAIN ANALYZE dump must contain) and confirm the plan-review checklist is the terminating artifact.

### 6. Domain Pack Interview Cards -- turn a KPI domain into owner questions

- **Candidate id (run-local)**: `c10`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 7 / 7 (panel median)
- **Horizon**: NOW | **Serves**: operator | **Strengthens**: retail-kpi
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Take one domain (sales-performance) and draft its owner question cards from kpi-ambiguities.md plus kpi-sufficiency-and-policy-decisions.md, each naming its Decision Store key.

### 7. Widen dax_gen beyond base|ratio: the variance/two-table contract shape

- **Candidate id (run-local)**: `c19`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 8 / 6 (panel median)
- **Horizon**: NOW | **Serves**: end_user | **Strengthens**: bi-dax
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Write the failing round-trip test first: a filled variance contract that check_measure_drift must accept, so the checker is the oracle before any emitter code exists.

### 8. Answer Freshness Header -- how old is the proof behind this number

- **Candidate id (run-local)**: `c35`
- **Panel verdict**: ADOPT -- triage opinion only, not an approval
- **Value / Feasibility**: 7 / 7 (panel median)
- **Horizon**: NOW | **Serves**: end_user | **Strengthens**: docs-spine
- **Eligibility gate**: pass | **Adversarial skeptic**: survived
- **Suggested first step (panel's words)**: Add the three-date block to the answerability summary using readiness-status evidence dates plus the source-profile coverage end date, with the gap stated as a sentence and no label.

## 5. What happens next

Nothing, until a human decides. For any row the owner wants to pursue:

1. The owner names the idea and authorizes spec work on it.
2. `idea-to-spec` drives it through the Spec-Kit chain in an isolated worktree and
   STOPS at a ratify seam -- the workflow cannot ratify its own spec.
3. The owner ratifies, then `implement` builds it TDD-gated to a PR-ready branch.
4. An F-row is placed on `roadmap.md` by a human, if and when it ships.

No step above is started by recording this document.

## 6. Provenance

- **Run**: `wf_97a589cd-7d2` (`idea-engine-fast`), 2026-08-22 -- 21/21 agents, 0 errors.
- **Bank**: `docs/roadmap/idea-backlog.md` (regenerated by that run).
- **Funnel**: 47 raw -> 46 scored (ADOPT 8, CONSIDER 9, PARK 20, REJECT 8, SHIPPED 1).
- **Known limitation of that run**: it ran DEGRADED -- the skeptic left one candidate
  (`c23`) unchallenged, which was clamped to killed and demoted out of ADOPT for
  unproven coverage. No row in this shortlist is that candidate.
- **Precedent for this artifact**: `docs/planning/top-idea-bank-execution-plan.md`.
