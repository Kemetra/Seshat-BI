# Tool -- Friendly PR Reviewer

- **Roadmap feature:** not yet assigned -- a human assigns the F-number at scheduling
  (this feature does not self-assign one). **On-disk spec:** `specs/130-pr-reviewer`.
- **Authority category (F024):** Product Module, capability level `read-only`. See
  `docs/architecture/product-modules.md` (the five categories, the authority matrix,
  the two sub-vocabularies) and `docs/architecture/core-vs-modules-and-adapters.md`.
- **The skill:** `.claude/skills/friendly-pr-reviewer/SKILL.md`. **The output shape:**
  `templates/friendly-pr-summary.md`. **The deterministic core:**
  `src/seshat/pr_summary.py` (+ `tests/unit/test_pr_summary.py`). **The opt-in CI
  wrapper:** `.github/workflows/ci.yml` (the "Friendly PR summary" step) +
  `scripts/post_friendly_pr_summary.py`.
- **Status:** Authored -- a pure, stdlib-only renderer/differ + docs-first skill/
  template, plus one additive, off-by-default CI step.

> ASCII only, UTF-8 no BOM; `--` and `->` only. Generic -- `retail_store_sales` is a
> filled instance CITED as a reference under `docs/worked-examples/`, never inlined
> (Principle VII).

## Purpose

A retail-BI PR carries governance truth in machine shapes: the `retail check` review
envelope (`build_review_result`), the SARIF projection, and the readiness truth
(`readiness-status.yaml`). A reviewer or non-technical owner reading a PR today must
open several JSON/YAML artifacts and reconstruct, by hand, what actually changed and
what it means.

This tool adds ONE plain-language PRESENTATION layer over those already shipped,
already authoritative results. It answers, in words: which tables / metric contracts /
measures / dashboards / evidence changed; which readiness stages remain `pass` /
`warning` / `blocked`; which blockers are NEW versus RESOLVED (when a base identity set
is supplied); who must review or approve; and EXACTLY ONE recommended next action. It
creates no truth -- it re-states, in plain language, what the shipped engines already
decided. It runs no new analysis, adds no `retail check` rule, opens no database, and
takes no action on the PR.

## The F025 boundary (read first)

The kit already ships `pr-readiness-reviewer` (F025): a per-PR read-only
**merge-safety VERDICT** -- `merge_ready` (yes/no) + `blockers[]` +
`required_human_decisions[]`. That skill answers "is this PR safe to merge?"

This tool is DISTINCT and complementary: it answers "in plain language, what CHANGED in
this PR and what does it mean?" -- a presentation NARRATIVE over the governance review
envelope. It renders no `merge_ready` boolean, adopts no verdict authority, and does not
replace or re-derive F025. Where both could run on the same PR, F025 owns the merge
gate/verdict; this tool owns the plain-language change story.

## When to run it

- On any PR, when a reviewer or a non-technical stakeholder wants to understand what
  changed and what it means without opening JSON/YAML.
- Alongside (never instead of) `pr-readiness-reviewer` when a merge-safety verdict is
  also needed -- the two are complementary, not substitutes.
- Automatically, on each push to a PR, if the repository has opted in to the additive
  CI step (see below).

## Inputs

- **The review envelope** (`review_integration.build_review_result`, exposed via
  `retail check --format review`): `outcome` (`ok` | `blocked` only -- there is no
  `input_defect` outcome value; an absent/unproducible envelope is a separate honesty
  branch, handled as `envelope is None`), `checks_run`, `changed_files`,
  `changed_readiness_state`, `affected_stages`, `findings[]`, `blocking_findings[]`,
  `next_actions[]`, `run_boundary`, `result_digest`.
- **The readiness truth** (`mappings/<table>/readiness-status.yaml`, already parsed
  into a mapping by the caller -- this module does no YAML I/O itself): `current_stage`,
  per-stage `status`, `approvals[]`, `blocking_reasons[]`.
- **(Optional, US2) a base fingerprint set**: a prior run's `sarif.finding_fingerprint`
  values, or a base SARIF run's `partialFingerprints`. Omitting this is honest and
  supported.
- **(Optional) a timestamp**: an explicit caller-supplied string. `render_summary` and
  `compose_comment` never read the wall clock -- this is required for byte-identical
  determinism.

## What the summary contains

`render_summary(envelope, readiness, base_fingerprints=None, *, timestamp=None)`
returns a `FriendlySummary` with:

- **`affected_artifacts`** -- the plain-language "what changed" narrative, derived from
  `affected_stages` / `changed_files` / `changed_readiness_state`.
- **`stage_statuses`** -- one entry per affected stage, `status` taken VERBATIM from
  readiness/envelope truth (never computed or upgraded), each `source`-tagged.
- **`blocker_groups`** -- either three groups (`new` / `resolved` / `carried_over`,
  when a base set is supplied) or one `present` group (when it is not), each a list of
  masked, plain-language finding lines.
- **`warnings`** -- non-blocking (WARNING-severity) findings, surfaced as "worth a
  look", never as blockers.
- **`required_authority`** -- for each `blocked` stage, the routed surface (via
  `readiness_classify`'s refutation-first category rank applied to that stage's
  `blocking_reasons[]`) and, for an `approval`-category blocker, the named
  `approvals[]` owner on record if any -- never self-granted, never self-named.
- **`next_action`** -- EXACTLY ONE action selected from `next_actions[]` by the same
  refutation-first rank (approval > grain > live_validation > artifact > readiness), or
  the literal sentinel "no next action was produced by the review".
- **`undetermined`** -- explicit "could not determine" lines for every missing required
  input (absent envelope, empty `next_actions[]`, absent readiness, absent base set),
  each naming the missing source.
- **`conflicts`** -- surfaced (never resolved) disagreements between consumed sources,
  e.g. readiness reports a stage `pass` while the envelope reports it `blocked`.
- **`text`** -- the full assembled plain-language document (deterministic, byte-
  identical across repeated calls on the same inputs).

No field is ever numeric; no field is ever a `merge_ready` boolean.

## The temporal fingerprint diff (US2) -- and its known limitation

`classify_changes(base_fingerprints, head_findings)` computes head fingerprints by
calling `sarif.finding_fingerprint` directly (no new hashing) and returns three
disjoint sets -- `new` (head-only), `resolved` (base-only), `carried_over` (in both) --
that together cover the union of base and head fingerprints.

**Known v1 limitation (line-shift churn):** `finding_fingerprint` includes the locator
(`path:line:col`). A finding that merely SHIFTS LINES between base and head (unchanged
rule/severity/message, moved by an edit above it) gets a new fingerprint and is reported
as one RESOLVED + one NEW rather than carried-over. This is accepted in v1 rather than
inventing a location-tolerant identity that would diverge from the shipped fingerprint
(the reuse-not-rebuild rule). The rendered summary is honest about this precision; it
never claims the diff is line-shift-tolerant.

When no base set is supplied, the summary states plainly that the new-vs-pre-existing
distinction could not be determined (naming the missing base input) and lists findings
as "present" -- it never defaults every finding to "new".

## Masking (FR-009) -- and its documented v1 gap

Before any finding message enters the summary, `mask()` redacts the four shapes the
shipped `interview_review._mask` contract detects: an email address, an SSN/national-
ID-like number, a long digit run, and a `key: value` secret assignment (`password:`,
`token:`, ...). The shapes are reproduced (cited, not imported) in `mask()`'s
docstring -- this is not a new redaction engine, it is the same shapes lifted into a
public, testable function. Masking is idempotent and applies with extra force to the
sticky-comment body (a public-egress surface).

**Documented v1 non-coverage**: a bare DSN/connection-string URL
(`scheme://user:pass@host/db`) embedded in a finding message is NOT masked.
`interview_review._mask` has no connection-URL shape, and `readiness_evidence._scrub`
only redacts a DSN when the caller already holds the literal DSN string -- which this
DB-less presentation layer never does. Adding a DSN/URL detector would be a NEW
redaction primitive, contradicting the reuse-only rule, so v1 deliberately does not add
one. This is a documented residual-risk gap, bounded because the shipped review
producers do not emit DSN URLs into finding messages today; a future spec may add a
location-tolerant / DSN-URL-aware masker if this proves material. No test in
`tests/unit/test_pr_summary.py` claims this gap is closed.

## The opt-in CI step (US3)

Posting the summary as a sticky PR comment is OPT IN and OFF BY DEFAULT. A repository
opts in by setting the Actions repository VARIABLE `POST_FRIENDLY_PR_SUMMARY` to
`"true"`. When set, the existing `.github/workflows/ci.yml` `check` job's "Friendly PR
summary" step:

1. Re-runs the already-produced review as `retail check --format review [--commit-range
   BASE..HEAD] > review.json` (no new analysis).
2. Calls `scripts/post_friendly_pr_summary.py`, a thin wrapper (not part of the tested
   core) that loads the envelope, best-effort loads a single changed
   `readiness-status.yaml`, calls `render_summary` + `compose_comment`, and posts/
   updates ONE sticky comment via the runner's own `gh` CLI + `GITHUB_TOKEN` --
   targeting an existing same-marker comment (`find_existing`) rather than creating a
   second one.

When the repo variable is unset (the default), the step's `if:` condition is false: the
step does not run, nothing is posted, and no existing behavior changes (FR-015,
SC-005). This adds NO new Python dependency: `pyyaml` is already installed via the
`[dev]` extra for the `retail semantic-check` / `retail kit-lint` steps in the same
job. The step does not create a new workflow file -- it is one additive step in the
existing `ci.yml`.

**Deferred**: the base-branch temporal fingerprint diff (US2) is not wired into this CI
step yet -- fetching a base run is explicitly the wrapper's job and stays out of the
thin CI step for now; the posted summary honestly states the new-vs-pre-existing
distinction could not be determined rather than defaulting every finding to "new".

## No fake confidence (the guardrail)

If asked for "a PR health score", "a confidence percentage", or "a merge-readiness
number", the tool declines: it cites no-fake-confidence (rule #9) and returns the
plain-language summary instead -- verbatim statuses, named blockers, one next action,
nothing numeric.

## See also

- `.claude/skills/friendly-pr-reviewer/SKILL.md` (the procedure, the embedded F024
  Module Contract, the honest-state rules table).
- `templates/friendly-pr-summary.md` (the generic rendered shape).
- `.claude/skills/pr-readiness-reviewer/SKILL.md` (F025, the merge-safety verdict
  sibling this tool is explicitly distinct from).
- `src/seshat/review_integration.py`, `src/seshat/sarif.py`,
  `src/seshat/readiness_classify.py` (reused, unchanged); `src/seshat/readiness_evidence.py`
  and `src/seshat/interview_review.py` (pattern/shape references, not imported).
- `src/seshat/pr_summary.py` + `tests/unit/test_pr_summary.py` (the deterministic core
  and its fixture-driven tests).
