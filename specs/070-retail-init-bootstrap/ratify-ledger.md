# Ratify Ledger — 070 retail init (Compass-Driven Phase-1 Step 1-2)

**This is the STOP point.** The `idea-to-spec` / speckit chain DEFINES and CHECKS; it
never APPROVES. Ratification is a named-human edit this workflow is structurally
forbidden to make. Below is everything the human needs to decide; the approval slot at
the bottom is intentionally EMPTY.

## What is being ratified

A ratifiable spec for **`retail init`** — an agent-invokable Workflow Skill that
bootstraps a repo for the Compass-Driven kit and leads with a visible first result on
the user's own table (over a live DB) or an honest `[PENDING LIVE PROFILE]` structure
without one. It writes the backstage substrate (`.seshat/compass.yaml` router, the
fenced `SESHAT-KIT` regions of `AGENTS.md`/`CLAUDE.md`, manifests) silently, delegates
the worked-example offer + seam list to `first-hour-compass`, and routes into
`retail-onboard-table` for the profile. Substrate-only Python/CLI; no wizard; no
run-state; no remote fetch; no self-granted approval; no fabricated score.

Provenance: the doc's own recommended first pick (`docs/roadmap/distribution-ideas.md`,
Phase-1 Step 1-2). Spec'd DIRECTLY via speckit (not `idea-to-spec`'s backlog-locate
front stage) because the idea is deliberately outside `idea-backlog.md` and carries no
roadmap F-number.

## Artifacts produced (branch `070-retail-init-bootstrap`, worktree, NOT merged)

| Artifact | State |
|----------|-------|
| `spec.md` | Draft — awaiting ratification |
| `plan.md` | Complete (Constitution Check: no violations) |
| `research.md` | Complete (R1–R6 resolved) |
| `data-model.md` | Complete (E1–E5) |
| `contracts/compass-yaml.contract.md`, `contracts/fence.contract.md` | Complete |
| `tasks.md` | Complete (25 tasks: T001–T024 + T021b, story-organized) |
| `plan-review.md` | Complete (2 rounds: BLOCK → PASS-WITH-NOTES) |

## Gate evidence

- **`retail check`**: exit 0 on the worktree (pre-commit gate passed on every commit).
- **`speckit-analyze`**: 0 CRITICAL, 0 HIGH; coverage 21/23 full + 2 partial resolved
  (FR-011 guard added as T021b; SC-008 review-verified).
- **Adversarial plan-review**: Round 1 BLOCK (1 BLOCKER + 4 MAJOR + 3 MINOR); all
  BLOCKER/MAJOR closed with cross-propagated edits; Round 2 **PASS-WITH-NOTES**;
  MINOR-8/MINOR-9 fixed after Round 2; one optional NOTE remains (quickstart seam list
  is attributed + passes T020).

## Constitution posture (from plan.md)

No violations. Notable stances the human should confirm they accept:
- `init` is agent-first (Principle I): the Python/CLI is substrate-only; the agent
  performs delegate/route/profile. NOT a terminal wizard.
- Amendment-safety (MINOR-5 caveat): `AGENTS.md` has no fence today, so first-run
  insertion of generated prose there is the normal path; the fence BODY is
  human-reviewed at ratify until the Phase-2 source-vs-constitution drift check lands.
  Outside-fence invariance is guaranteed (SC-002).
- Advances NO readiness stage; takes NO roadmap F-row (kit-bootstrap infra, like
  `scaffold.py` / `manifest.py`).

## Open items the human owns (not blockers — recorded decisions the spec adopts)

1. **DEC-1 — Phase boundary.** This spec is Phase-1 only. `sync` (Phase-3 self-update)
   and channel-driven fetch (Phase-4) are explicitly OUT of scope and gated.
2. **DEC-2 — No CSV/Excel profiler.** The guaranteed visible result requires a live DB;
   without one the flow degrades to `[PENDING LIVE PROFILE]`. Building a file profiler
   is YAGNI-deferred. Confirm this is the accepted first-run experience.
3. **DEC-3 — Fence-body review until Phase-2.** Until the source-vs-constitution drift
   linter exists, the human reviews the `SESHAT-KIT` fenced body content at ratify.

## Approval slot — TO BE FILLED BY A NAMED HUMAN

> The workflow STOPS here. It does not set the status, name the owner, or supply the
> rationale. To ratify: set `spec.md` `**Status**:` to
> `Ratified (<name>, <date>)`, record the rationale, and (if desired) authorize the
> build of the tasks in `tasks.md`.

- **Decision** (ratify / revise / reject): **ratify**
- **Named owner**: **Ahmed Shaaban**
- **Date**: **2026-07-02**
- **Rationale / conditions**: **Owner directive "ratify it and authorize
  implementation." DEC-1/2/3 accepted as specified (Phase-1-only scope; live-DB
  profile with `[PENDING LIVE PROFILE]` degrade and no CSV/Excel profiler;
  fence-body human review until the Phase-2 drift linter). No conditions beyond the
  spec as written.** (Transcribed by the advisor from the owner's recorded decision
  -- approval-console pattern; not self-originated.)
- **Build authorization** (may `speckit-implement` proceed?): **Yes.** The 25 tasks
  in `tasks.md` are authorized to build, TDD, on a feature branch off `main`. Merge
  of the resulting PR to `main` remains a separate act requiring explicit owner
  approval (two-party review).

`spec.md` is now `Ratified (Ahmed Shaaban, 2026-07-02)`. Build proceeds on branch
`070-retail-init-impl`; nothing merges to `main` without a separate owner approval.
