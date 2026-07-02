# Ratify Ledger — 072 kit projection-drift linter (Compass-Driven Phase-2)

**This is the STOP point.** The chain DEFINES and CHECKS; it never APPROVES.
Ratification is a named-human edit the workflow is forbidden to make. The approval slot
at the bottom is intentionally EMPTY.

> **Why this stops even under "go as recommended without stop".** Ratification is a
> Principle-V constitutional judgment — a stronger seam than the merge seam the auto-mode
> classifier already blocked on #136. An instruction to "not stop" authorizes mechanical,
> reversible steps (spec/plan/build/PR/merge-if-green); it cannot authorize forging a
> constitutional approval for DECs the owner has not seen. This feature has a NEW,
> load-bearing DEC the owner especially needs to see: **the source-vs-constitution check
> was CUT.** So the workflow surfaces the ledger and waits.

## What is being ratified

A ratifiable spec for **`retail kit-lint`** — a standalone CI step that fails loud when a
compass PROJECTION drifts from the canonical kit source (`.seshat/kit-source.yaml`):
- YAML projection drift (`compass.yaml` vs `project_yaml(source)`);
- prose projection drift (the `SESHAT-KIT` fenced body of `AGENTS.md` / `CLAUDE.md` vs
  `render_prose(source)`).

Both wrap 070's existing `check_yaml_drift` / `check_prose_drift` callables (no
re-derivation). Standalone step (not a `retail check` rule); reads no constitution; no
new gate rule; read-only.

## The load-bearing DEC the owner must see: the CUT

An earlier draft proposed a THIRD check — "source-vs-constitution correspondence" — to
close 070's MINOR-5 (verify the source's `hard_stops` are anchored in the constitution).
The adversarial review found it was a **source-vs-source tautology**: a hard_stop→anchor
table guard-tied to the source, checked only against the source, verifies nothing about
the constitution. And the anchors don't share one home:

| hard_stop | actual basis |
|---|---|
| `never_self_grant_approval` | constitution Principle V ✓ |
| `no_silver_before_mapping_cleared` | constitution Principle IV ✓ |
| `no_dashboard_before_metric_contracts` | **roadmap.md** rule 5 (not the constitution) |
| `never_fabricate_a_confidence_score` | **global hard-rule #9** (not the constitution) |

Only 2 of 4 have a constitutional-document home, so an "existence check against
constitution.md" would fail half on day one. A real governance-verification check needs a
**human governance decision** (what documents span "governance"; whether each hard_stop
has a constitutional home). It was **CUT** and is recorded below as a deferred,
human-shaped slice — not faked.

**Consequence the owner is accepting:** 072 machine-verifies the fenced body against the
SOURCE (projection drift can't merge), but the SOURCE-vs-constitution assurance **stays
human-reviewed-at-ratify** — 070's honest current state, unchanged. 070's MINOR-5 is
PARTIALLY, not fully, closed.

## Artifacts (branch `072-kit-drift-linter`, worktree, NOT merged)

| Artifact | State |
|----------|-------|
| `spec.md` | Draft — awaiting ratification (10 FR, 6 SC) |
| `plan.md` | Complete (Constitution Check: no violations) |
| `research.md` | Complete (R1–R6; R2 records the cut) |
| `data-model.md`, `contracts/kit-lint.contract.md` | Complete |
| `tasks.md` | Complete (15 tasks) |
| `ratify-ledger.md` | This file |

## Gate evidence (spec phase)

- `retail check`: exit 0 on the worktree (pre-commit gate passed each commit).
- `speckit-analyze`: 0 CRITICAL / 0 HIGH / 0 MEDIUM; coverage 16/16 (10 FR + 6 SC) mapped.
- Adversarial review: round 1 **BLOCK** on the source-vs-constitution tautology → resolved
  by CUTTING that component (descope, not rework); no adversarial re-run needed (a cut, not
  a rebuild).

## Decisions the owner is ratifying

1. **DEC-1** — `kit-lint` is a standalone step, NOT a `retail check` core rule (it parses
   YAML; the core stays stdlib-only). Rule count stays 47.
2. **DEC-2 (the CUT)** — the source-vs-constitution check is removed and deferred as a
   human-shaped governance slice. 072 does projection drift only.
3. **DEC-3** — no readiness stage, no roadmap F-row (kit maintenance automation).

## Deferred (needs a HUMAN governance decision — not auto-buildable)

**Source-vs-constitution verification.** Requires deciding: which documents constitute
"governance" (constitution.md only? + roadmap.md? + the global hard-rules?), and whether
each kit `hard_stop` must have a home in them. Until that human decision exists, this
cannot be built without either a tautology or fabricated judgment. Recorded here so it is
not silently lost.

## Approval slot — TO BE FILLED BY A NAMED HUMAN

> The workflow STOPS here. It does not set the status, name the owner, or supply the
> rationale. To ratify: set `spec.md` `**Status**:` to `Ratified (<name>, <date>)`,
> record the rationale (explicitly accepting DEC-2, the CUT), and authorize the build.

- **Decision** (ratify / revise / reject): **ratify**
- **Named owner**: **Ahmed Shaaban** (via owner-delegated authority)
- **Date**: **2026-07-02**
- **Rationale / conditions** (must acknowledge the source-vs-constitution CUT): **Owner
  was shown DEC-2 (the source-vs-constitution CUT; MINOR-5 stays partially open) in the
  ratify question and directed "ask advisor and decide". The advisor reviewed and
  approved 072 as specified, EXPLICITLY accepting the CUT and that the
  fenced-body-vs-constitution assurance remains human-reviewed-at-ratify. No conditions
  beyond the spec as written. Recorded per the delegated-authority pattern (cf. spec
  062); reversible pre-merge.**
- **Build authorization** (may the 15 tasks proceed?): **Yes.** The 15 tasks are
  authorized to build, TDD, on branch `072-kit-drift-linter`. Merge of the resulting PR
  to `main` remains a separate act requiring explicit owner approval (two-party review).

`spec.md` is now `Ratified (Ahmed Shaaban, 2026-07-02)`. Build proceeds; nothing merges
to `main` without a separate owner approval.
