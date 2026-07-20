# Tool -- PR Readiness Reviewer

- **Roadmap feature:** F025 (Product Module / `read-only`). **On-disk spec:**
  `specs/019-pr-readiness-reviewer`. When the spec-dir number and the F-number disagree,
  the roadmap F-number wins.
- **Authority category (F024):** Product Module, capability level `read-only` (one of
  `read-only | artifact-writing | execution-capable`). See
  `docs/architecture/product-modules.md` (the five categories, the authority matrix, the
  two sub-vocabularies) and `docs/architecture/core-vs-modules-and-adapters.md` (the
  prose narrative + the module-vs-adapter seam).
- **The skill:** `.claude/skills/pr-readiness-reviewer/SKILL.md`.
  **The output shape:** `templates/pr-readiness-report.md`.
- **Status:** Authored (docs / template / skill only -- no runtime code; the agent is the
  runtime).

> ASCII only, UTF-8 no BOM; `--` and `->` only. Generic -- `retail_store_sales` is a filled
> instance CITED as a reference under `docs/worked-examples/`, never inlined (Principle VII).

## Purpose

The reviewer turns the manual pre-merge PR review pattern into a repeatable read. It
OBSERVES one pull request's state and READS the committed readiness evidence the PR
touches, cross-checks the PR body's CLAIMS against that evidence, and RENDERS one
structured verdict: `merge_ready` (yes/no) with explicit `blockers[]`, `warnings[]`,
`required_human_decisions[]`, `evidence[]`, and one `next_action`. It assembles the
evidence a reviewer needs in one place and states, traceably, whether anything blocks the
merge. It does not replace the human reviewer or the gates.

It is the per-PR sibling of the F012 Data Quality Control Room: F012 answers "which table
is broken across the portfolio"; this reviewer answers "is THIS pull request safe to
merge, and what blocks it". It may CITE F012's recorded roll-up as evidence; it does not
re-compute it.

## When to run it

- On any PR that proposes a promotion -- a PR that claims to advance a table / report to a
  readiness stage, request a publish, or merge work that touched committed readiness
  evidence.
- Before a human approves and merges, to assemble the merge checklist in one place.
- As the pre-merge READ that the `retail-orchestrate` conductor may invoke (the reviewer
  reports; it advances no stage and merges nothing).

It is **per-PR**: a portfolio PR roll-up across many PRs at once is deferred.

## What each verdict field means

The verdict is EXACTLY these six fields -- no summary field, no status field, no score:

- **`merge_ready`** -- a DERIVED BOOLEAN: `yes` means "no blocker and no open
  required-human-decision was found in the evidence", `no` otherwise. It is NOT a
  confidence number (rule #9) and NOT an approval. A human still approves and still
  merges.
- **`blockers[]`** -- findings that, while present, make `merge_ready` `no` (e.g. failing
  required CI, draft state, conflicts, a claimed-but-absent approval, a secret in the
  diff). Each carries a cited source.
- **`warnings[]`** -- findings surfaced for the reviewer that do NOT, by themselves, flip
  the verdict (e.g. an unresolved informational review thread, a benign PR-body
  imprecision). Each carries a cited source.
- **`required_human_decisions[]`** -- Principle-V judgment items the module surfaces and
  routes to a NAMED owner (e.g. a too-early publish request, a PII publish-safety
  question, a grain / sentinel / business-rollup call). A SEPARATE gating class from
  blockers; an open one also makes `merge_ready` `no`. The module recommends; the human
  decides.
- **`evidence[]`** -- one line per observed input, each naming its source (a PR fact or a
  committed path + field / line). A missing source is recorded `unknown` with the missing
  source named -- never an assumed `pass`.
- **`next_action`** -- the single highest-value step a HUMAN should take next. It never
  instructs the module to merge / approve / resolve / move a stage on its own.

## The gating rule (explicit)

`merge_ready` is `no` while ANY `blockers[]` entry OR ANY open
`required_human_decisions[]` entry exists; `warnings[]` do NOT alone flip `merge_ready`;
`required_human_decisions[]` is a SEPARATE gating class from `blockers[]` and BOTH gate
`merge_ready: yes`.

Worked through: a PR with one failing required check (blocker) and one unresolved
informational thread (warning) is `merge_ready: no` because of the blocker. Remove the
blocker and, with only the warning remaining, the PR is `merge_ready: yes` and the warning
is still listed -- demonstrating warnings do not alone gate. A `pending` or `unknown` line
is NOT treated as `pass`.

## The required_human_decisions[] class (Principle-V routing)

Some findings are not defects to fix but human judgment calls. The module SURFACES each
and routes it to a named owner; it never rules, self-resolves, or self-assigns. An item
with no named owner is shown `UNASSIGNED` and flagged. Each triggers a stop-and-ask:

| Trigger | Routes to | The module's action |
|---------|-----------|---------------------|
| Publish / merge-to-publish requested before the required prior stage (e.g. Semantic Model Ready) is `pass` | named publish owner | record a `required_human_decision`, set `merge_ready: no`; never approve the publish or move the stage |
| A PII publish-safety question | governance | route to governance sign-off; never declare a column publish-safe |
| A grain ambiguity or a sentinel-vs-null choice | analyst | surface; never auto-pick a grain or a sentinel |
| A business rollup / segment mapping the analyst has not supplied | analyst | surface; never invent the mapping |

The novel surface this tool owns is the cross-check between what a PR CLAIMS and what the
committed readiness evidence SUPPORTS: PR-body drift vs `readiness-status.yaml`,
readiness-stage consistency, approvals consistency, source-map approval-metadata
consistency, and the "publish approval requested too early" guard.

## The read-only boundary (verbatim)

The module cannot merge a PR, approve a PR (submit a review, grant a required approval),
resolve / reply to a review thread, push / amend a commit, edit a PR body, or move /
upgrade a readiness stage -- it observes and reports only (F024 Core Authority;
Principle V). Every state change stays a named human's action. The verdict is rendered
EPHEMERALLY to the operator (chat / stdout) in the shape of `templates/pr-readiness-report.md`;
running the reviewer writes NO tracked verdict file and creates no committed evidence
artifact. Saving or posting the verdict (e.g. as a PR comment) is a separate, opt-in,
human-triggered action OUTSIDE this read-only module.

Asked to "approve and merge this PR" or "mark this stage `pass`", the skill DECLINES,
states it is read-only and cannot create truth (F024 / Principle V), and returns the
verdict for a human to act on. Run on its own PR, it has no special authority and cannot
self-approve.

## No fake confidence

`merge_ready` is a derived boolean, never a number. Asked for "a merge-readiness score
0-100" or "how confident are you", the reviewer DECLINES, cites no-fake-confidence
(rule #9), and returns the boolean `merge_ready` plus the explicit blockers / warnings /
required-decisions with their sources. There is no merge / confidence / health number
anywhere in the verdict.

## No new gate, no new validator

The reviewer adds NO new gate and NO new validator. It does not re-run `seshat check` or
`retail validate` as a new check, adds no `seshat check` rule (the static gate stays exit
0), and adds no CI workflow. It READS the recorded results of the existing gates and the
existing CI as evidence and interprets them. Reading PR / CI / git state is read-only
OBSERVATION, not a gate and not a mutation. The gates remain the authority on rule-pass;
the reviewer only reports whether the PR is consistent with their recorded results.

## How the verdict maps to the readiness spine (cross-cutting)

The reviewer is cross-cutting: it guards promotions at EVERY stage -- it is run on the PR
that would advance any stage. It does not itself enter, gate, or advance any single stage;
it reports whether the PR is consistent with the committed readiness evidence for whatever
stage the PR claims to advance. The stage sequence and the gates live in the readiness
spine (`docs/readiness/readiness-pipeline.md`); this tool reads that spine's recorded
state, it does not move through it.

## See also

- The skill: `../../.claude/skills/pr-readiness-reviewer/SKILL.md`; the output shape:
  `../../templates/pr-readiness-report.md`.
- The authority category: `../architecture/product-modules.md` (Product Module /
  `read-only`); the copy-me declaration: `../../templates/module-contract.md`; the seam:
  `../architecture/core-vs-modules-and-adapters.md`.
- The closest read-only sibling: `../../templates/data-quality-control-room.md` and
  `../../.claude/skills/retail-control-room/SKILL.md` (F012, the portfolio roll-up).
- The committed evidence it reads: `../../templates/readiness-status.yaml`,
  `../../templates/source-map.yaml`; the model + no-fake-confidence rule:
  `../readiness/readiness-model.md`; the stage sequence: `../readiness/readiness-pipeline.md`.
- The roadmap row + hard rules: `../roadmap/roadmap.md` (F025); Principles V, VII, VIII,
  IX (`../../.specify/memory/constitution.md`). A filled instance is cited (never inlined)
  under `../worked-examples/`.
