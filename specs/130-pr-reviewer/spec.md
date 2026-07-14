# Feature Specification: Friendly PR Reviewer (Plain-Language PR Summary)

**Feature Branch**: `130-pr-reviewer`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Friendly PR Reviewer. Add an OPT-IN PLAIN-LANGUAGE PR
SUMMARY over EXISTING authoritative review results. A presentation layer over
shipped truth, NOT a second analysis engine."

## Overview

A retail-BI PR carries governance truth in machine shapes: the `retail check`
review envelope (`build_review_result`), the SARIF projection (`sarif.py`), the
review pack (`review_pack_export.py`), the readiness state
(`readiness-status.yaml`, `readiness_classify.py` / `readiness_evidence.py`), and
lineage (`cross-table-lineage`, kpi-derivation-lineage). A reviewer or a
non-technical owner reading a PR today must open several JSON/YAML artifacts and
reconstruct, by hand, what actually changed and what it means.

This feature adds ONE **plain-language presentation layer** over those already
shipped, already authoritative results. It answers, in words a non-technical
owner can read: which tables / metric contracts / measures / dashboards /
evidence changed; which readiness stages remain `pass` / `warning` / `blocked`;
which blockers are NEW versus which were RESOLVED; who must review or approve;
and EXACTLY ONE recommended next action. It is rendered predictably as a single
sticky comment that updates in place, never a stream of new comments.

It is a NARRATIVE, not a VERDICT. It creates no truth: it re-states, in plain
language, what the shipped engines already decided. It runs no new analysis,
adds no `retail check` rule, opens no database, and takes no action on the PR.

## Boundary against the shipped PR reviewer (F025) *(read first)*

The kit already ships `pr-readiness-reviewer` (F025, `.claude/skills/
pr-readiness-reviewer/`): a per-PR read-only **merge-safety VERDICT** --
`merge_ready` (yes/no) + `blockers[]` + `required_human_decisions[]`. That skill
answers "is this PR safe to merge?" -- a judgment reading of PR + evidence state.

This feature (Friendly PR Reviewer) is DISTINCT and complementary: it answers
"in plain language, what CHANGED in this PR and what does it mean?" -- a
**presentation NARRATIVE** over the governance review envelope. It renders no
`merge_ready` boolean, adopts no verdict authority, and does not replace or
re-derive F025. Where both could run on the same PR, F025 owns the merge
gate/verdict; this feature owns the plain-language change story. This feature
MUST reference F025 and MUST NOT duplicate its merge-verdict surface.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plain-language change summary over the review envelope (Priority: P1)

A reviewer (or a non-technical owner) wants to understand a PR without opening
JSON/YAML. They run the friendly summary over the PR's existing `retail check`
review envelope (the `build_review_result` output) plus the committed readiness
state. They get one short, plain-language document: what kinds of artifacts
changed (tables, metric contracts, measures, dashboards, evidence), which
readiness stages are `pass` / `warning` / `blocked`, who must review or approve,
and exactly one recommended next action.

**Why this priority**: This is the MVP and the core value. It is fully
deterministic and needs no network, no GitHub API, and no base run -- it renders
plain language over a single already-produced review envelope. Everything else
(the changed-vs-pre-existing diff, the sticky comment) builds on this renderer.

**Independent Test**: Given a fixture review envelope (the JSON shape
`build_review_result` emits) plus a readiness-status fixture, calling the
renderer returns a plain-language summary that names the affected stages, states
each stage status verbatim from the envelope, names the required approval
authority, and states exactly one next action -- byte-identical across repeated
calls, with no numeric score and no leaked secret/PII. No CI and no PR involved.

**Acceptance Scenarios**:

1. **Given** a review envelope whose `outcome` is `blocked` with two blocking
   findings and `affected_stages` = [`mapping_ready`, `gold_ready`], **When** the
   renderer runs, **Then** the summary states in plain language that the change
   touches the mapping and gold stages, that the change is currently blocked,
   lists the two blockers in words, and states exactly one next action drawn from
   the envelope's `next_actions[]`.
2. **Given** a review envelope whose `outcome` is `ok` with only warnings,
   **When** the renderer runs, **Then** the summary states the change is not
   blocked, surfaces the warnings as "worth a look" (not as blockers), and states
   the single next action -- and emits NO merge-ready boolean and NO score.
3. **Given** a finding message that embeds a shape the reused `_mask` contract
   detects (email, SSN/national-ID number, long digit run, or `key: value` secret
   assignment), **When** the renderer runs, **Then** that value is masked in the
   summary and a redaction is noted, never rendered verbatim. (A bare
   DSN/connection-URL in a finding message is a documented v1 non-coverage, not a
   masking guarantee -- see FR-009.)
4. **Given** an envelope with `next_actions[]` holding several candidates,
   **When** the renderer runs, **Then** it selects EXACTLY ONE next action using
   the shipped refutation-first category rank, and states no second "or also".

---

### User Story 2 - Distinguish NEW blockers from pre-existing ones (Priority: P2)

The same reviewer wants to know which problems this PR INTRODUCED versus which
were already present on the base branch, and which the PR RESOLVED. They supply
the base branch's finding identity set (a base review/SARIF run, or a supplied
base fingerprint list). The summary then clearly separates: NEW blockers (present
at head, absent at base), RESOLVED blockers (present at base, absent at head),
and CARRIED-OVER / pre-existing findings (present in both).

**Why this priority**: Distinguishing changed from pre-existing findings is an
explicit hard rule of the feature and the single most useful thing the summary
adds over reading raw findings -- but it depends on US1's renderer and on a base
identity set, so it is P2, not the MVP floor.

**Independent Test**: Given a head finding set and a base finding set (each keyed
by the shipped `finding_fingerprint`), the differ returns three disjoint groups
(new / resolved / carried-over) and the renderer labels each group in plain
language. When no base set is supplied, the summary states honestly that
new-vs-pre-existing could not be determined and treats all findings as
"present" without fabricating a base -- tested with fixtures, no network.

**Acceptance Scenarios**:

1. **Given** a base fingerprint set and a head finding set that share one
   fingerprint and each carry one unique fingerprint, **When** the differ runs,
   **Then** the shared finding is labeled "pre-existing / carried over", the
   head-only finding is labeled "NEW in this PR", and the base-only finding is
   labeled "RESOLVED by this PR".
2. **Given** no base fingerprint set is available, **When** the differ runs,
   **Then** the summary states explicitly that it could not distinguish new from
   pre-existing (naming the missing base input) and lists findings as "present",
   never silently presenting all findings as new.
3. **Given** a head finding whose fingerprint matches a base finding but whose
   message text differs only in a masked-secret position, **Then** identity is
   decided by the shipped fingerprint (rule id + severity + locator + message),
   and the pair's classification is reported honestly from that fingerprint.

---

### User Story 3 - One opt-in sticky PR comment via the existing Action (Priority: P3)

A maintainer wants the friendly summary to appear on the PR automatically, but
without comment spam. They opt in (an off-by-default step in the EXISTING
`ci.yml`). On each push to the PR, the summary is (re)posted as ONE sticky
comment that is UPDATED IN PLACE (found by a stable marker), never a new comment
per run. The step is opt-in, additive, and reuses the existing GitHub Action /
workflow -- it does not mint a new workflow file.

**Why this priority**: This is the only networked / GitHub-touching surface and
the only opt-in surface. It is deliberately last so the deterministic core (US1,
US2) ships and is fully tested first, and so a repository that does not opt in is
completely unaffected.

**Independent Test**: The rendered comment body carries a stable HTML-comment
marker; given a prior comment body with the same marker, the update logic targets
that comment (update-in-place) rather than creating a new one; given no prior
comment, it creates exactly one. The comment-composition (marker + body) is
tested as a pure function against fixtures; the actual GitHub post is a thin,
opt-in wrapper that is NOT part of the deterministic core and is documented, not
unit-tested against a live API.

**Acceptance Scenarios**:

1. **Given** the opt-in step is enabled and no prior friendly-summary comment
   exists on the PR, **When** the step runs, **Then** exactly one comment is
   posted carrying the stable marker.
2. **Given** the opt-in step is enabled and a prior friendly-summary comment
   exists (same marker), **When** the step runs again on a new push, **Then** the
   existing comment body is replaced in place and no second comment is created.
3. **Given** a repository that has NOT opted in, **When** CI runs, **Then** no
   friendly-summary comment is posted and no existing behavior changes.
4. **Given** the summary body, **When** it is composed for the comment, **Then**
   the `_mask`-detected shapes (email, SSN/national-ID, long digit run, secret
   assignment) are masked before egress (masking from US1 is applied), because the
   comment is a public surface. (A bare DSN/connection-URL in a finding message is
   a documented v1 non-coverage per FR-009, not a guarantee.)

---

### Edge Cases

- **Empty / no-findings envelope**: the summary states plainly that the change
  introduced no governance findings and gives the single next action from the
  status projection; it does not fabricate a blocker or a stage.
- **Review envelope could not be produced** (e.g. a bad commit range makes the
  review step fail before an envelope exists): the summary states that the review
  could not be produced (naming the defect) and stops; it does not invent a change
  story. NOTE: the authoritative input `build_review_result` only ever emits
  `outcome: ok` or `outcome: blocked` (never an `input_defect` outcome), so this
  is handled as an ABSENT/unreadable envelope -- the same honesty branch as
  "envelope absent" -- not as a distinct outcome value.
- **A next action list that is empty**: the summary states "no next action was
  produced by the review" honestly rather than inventing one.
- **A readiness status file the envelope references is absent**: the affected
  stage is reported `unknown` (source named), never assumed `pass`.
- **A finding locator that is not a file path** (e.g. a git-metadata rule): the
  summary describes it in words without pretending it points at a line.
- **Two sources disagree** (PR body claims a stage `pass`; readiness shows
  `blocked`): the summary SURFACES the conflict; it does not resolve it (that is a
  human judgment / F025 territory).
- **A very large finding set**: the summary groups by stage/kind and caps the
  per-group detail predictably (a stable, documented cap), never truncates
  silently in a way that hides a blocker.
- **Line-shift churn (fingerprint identity limitation)**: because
  `finding_fingerprint` includes the locator (`path:line:col`), a finding that
  merely SHIFTS LINES between base and head (unchanged rule/severity/message, moved
  by an edit above it) gets a new fingerprint and would be reported as one RESOLVED
  + one NEW rather than carried-over. v1 accepts this as a known limitation
  (see Assumptions) and MUST NOT claim the diff is line-shift-tolerant; the summary
  states the diff is keyed on the exact shipped fingerprint so a reader is not
  misled about its precision.

## Requirements *(mandatory)*

### Functional Requirements

**Presentation over shipped truth (reuse, never re-derive)**

- **FR-001**: The feature MUST consume the EXISTING authoritative review results
  as its inputs -- the `build_review_result` review envelope
  (`review_integration.py`), the `finding_fingerprint` / `sarif_document` identity
  (`sarif.py`), the readiness truth (`readiness-status.yaml`,
  `readiness_classify.py`, `readiness_evidence.py`), and where relevant the review
  pack shape (`review_pack_export.py`) and lineage (`cross-table-lineage`,
  kpi-derivation-lineage). It MUST NOT re-run rules, re-classify findings, open a
  database, or produce a second analysis.
- **FR-002**: The feature MUST NOT add a `retail check` rule, MUST NOT change any
  rule's behavior, and MUST NOT change the `build_review_result` / `sarif` /
  `review_pack_export` output shapes. It is additive and read-only over them.
- **FR-003**: Every line of the summary MUST trace to a field in a consumed input
  (an envelope field, a readiness field, a fingerprint). A summary line with no
  traceable source is a defect. The feature invents no fact.

**What the summary explains (the content contract)**

- **FR-004**: The summary MUST state, in plain language, which KINDS of governed
  artifacts changed -- tables, metric contracts, measures, dashboards, evidence --
  derived from the envelope's `affected_stages` / `changed_files` /
  `changed_readiness_state` and (where present) lineage, without re-deriving the
  change set itself.
- **FR-005**: The summary MUST state which readiness stages remain `pass`,
  `warning`, or `blocked`, taking each status VERBATIM from the readiness truth /
  envelope. It MUST NOT compute or upgrade a stage status.
- **FR-006**: The summary MUST clearly separate NEW blockers (introduced by this
  PR) from RESOLVED blockers and from PRE-EXISTING / carried-over findings, keyed
  on the shipped `finding_fingerprint`. When no base identity set is available, it
  MUST say so honestly and MUST NOT present all findings as new (FR-018).
- **FR-007**: The summary MUST name the required reviewer / approval AUTHORITY for
  any blocked stage (the named owner from `readiness-status.yaml` `approvals[]` /
  the classifier's routed surface), and MUST NOT self-grant, approve, or name
  itself as the authority.
- **FR-008**: The summary MUST state EXACTLY ONE recommended next action, selected
  from the envelope's existing `next_actions[]` using the shipped refutation-first
  category rank (`readiness_classify`: approval > grain > live_validation >
  artifact > readiness). It MUST NOT invent a next action absent from the inputs
  and MUST NOT list a second action.

**Safety, honesty, determinism (the guardrails)**

- **FR-009**: The summary MUST mask the PII/secret shapes the shipped
  `interview_review._mask` contract actually detects -- email addresses,
  national-ID / SSN-like numbers, long digit runs, and `key: value` secret
  assignments (e.g. `password:`, `token:`) -- BEFORE any finding message /
  evidence line enters the summary, reusing that contract verbatim (no new
  redaction engine, per hard rule #1). Default is mask-and-note; a detected value
  is never rendered verbatim to "be helpful". This applies with special force to
  the sticky comment (public egress).
  - **v1 out-of-scope, with the leak risk acknowledged**: a bare connection-string
    / DSN URL (a `scheme` + `credentials` + `@host/db` connection string, e.g. a
    Postgres/MySQL/Snowflake URI) that appears inside a finding
    *message* is NOT masked by the reused contract. `_mask` has no
    connection-URL shape, and `readiness_evidence._scrub` only redacts a DSN when
    the caller already holds the literal DSN string (which a DB-less PR summarizer
    does not). Adding a DSN/URL detector would be a NEW redaction primitive,
    contradicting the reuse-only rule and pre-empting an owner scope decision, so
    v1 deliberately does not do it. RESIDUAL RISK: a DSN URL embedded verbatim in
    a rule's finding message would pass through to the summary and the public
    sticky comment. This is bounded because the shipped review producers do not
    emit DSN URLs into finding messages today; a location-tolerant / DSN-URL-aware
    masker is deferred to a future spec. An implementer MUST NOT claim DSN-URL
    coverage in v1.
- **FR-010**: The summary MUST NOT approve, merge, dismiss a finding, mark a
  readiness stage `pass`, resolve a review thread, edit the PR body, or take any
  other action on the PR or on truth. It renders words only (Principle V; F024
  Product Module / read-only forbidden operations).
- **FR-011**: The summary MUST NOT emit a numeric merge / confidence / health /
  maturity / completeness score, percentage, or tally in any form (hard rule #9).
  Asked for one, it declines and cites the rule. Status is words + verbatim
  tokens, never a number.
- **FR-012**: The renderer and the differ MUST be deterministic: the same inputs
  produce byte-identical output, with NO wall-clock read (any timestamp is an
  explicit argument). Same envelope + same base set in -> same summary out.
- **FR-013**: The feature MUST NOT auto-fix code, edit any tracked file's content
  as a side effect of summarizing, or move any readiness state. Its only optional
  write is a PR comment via the opt-in step (FR-015), which is not a repo write.

**The sticky comment surface (opt-in, no spam)**

- **FR-014**: The friendly summary comment MUST be rendered as ONE sticky comment
  identified by a stable, documented marker, so that a re-run UPDATES the existing
  comment in place rather than posting a new one. The behavior MUST be
  predictable: at most one friendly-summary comment per PR.
- **FR-015**: Posting the comment MUST be OPT-IN and off by default, wired as an
  additive step in the EXISTING GitHub Action / `ci.yml`. The feature MUST NOT
  create a new workflow file for this, and a repository that does not opt in MUST
  see no behavior change and no comment.
- **FR-016**: The comment-body composition (marker + rendered summary) MUST be a
  pure function testable against fixtures; the actual GitHub API post is a thin,
  opt-in wrapper that is NOT part of the deterministic tested core and carries no
  new mandatory dependency in the static path.

**Honesty on missing / conflicting inputs**

- **FR-017**: When a required input is absent (no envelope, no readiness file, no
  base set), the summary MUST record the affected line as `unknown` / "could not
  determine" naming the missing source, and MUST STOP that line -- never assume
  `pass`, fabricate a blocker, or invent a base.
- **FR-018**: When base finding identity is unavailable, the new-vs-pre-existing
  section MUST state that distinction could not be made (naming the missing base
  input) rather than defaulting every finding to "new" or to "pre-existing".
- **FR-019**: When two consumed sources conflict, the summary MUST surface the
  conflict as a stated discrepancy and MUST NOT silently choose one side (that is
  a human judgment, F025 / Principle V).

**Generic and aligned**

- **FR-020**: The feature MUST stay generic: no worked-example specifics (billing
  codes, business segments, PII column names, per-table grain keys, pharmacy
  terms). C086 / `retail_store_sales` are cited as filled instances only
  (Principle VII). All artifacts MUST be ASCII, UTF-8 without BOM, using `--` and
  `->` only.
- **FR-021**: The feature MUST embed an F024 Module Contract declaration (Product
  Module; capability `read-only`; forbidden: create truth, approve/merge/dismiss,
  publish, connect to a DB, emit a score). It MUST NOT self-assign a roadmap
  F-number; it is described as a cross-cutting read-only companion module (sibling
  to F025/F036/F037) and a human assigns the F-number.

### Key Entities *(include if feature involves data)*

- **Review envelope (input, unchanged)**: the `build_review_result` dict --
  `outcome`, `checks_run`, `changed_files`, `changed_readiness_state`,
  `affected_stages`, `findings[]`, `blocking_findings[]`, `next_actions[]`,
  `run_boundary`, `result_digest`. Read verbatim; never mutated.
- **Finding identity (input, unchanged)**: the `finding_fingerprint` (sha256 of
  rule_id + severity + locator + message) and the SARIF `partialFingerprints` --
  the canonical new-vs-existing identity key.
- **Readiness truth (input, unchanged)**: per-table `readiness-status.yaml`
  (`current_stage`, per-stage `status`, `approvals[]`, `blocking_reasons[]`) and
  the `readiness_classify` category rank.
- **Friendly summary (output, new)**: a plain-language document -- affected-artifact
  narrative, per-stage status (verbatim tokens), NEW / RESOLVED / pre-existing
  blocker groups, required approval authority, exactly one next action. Carries
  no score. Rendered deterministically; masked before egress.
- **Change classification (derived)**: three disjoint fingerprint groups -- `new`,
  `resolved`, `carried_over` -- from (base fingerprint set, head finding set).
- **Sticky comment envelope (output, new, opt-in)**: the rendered summary wrapped
  with a stable marker for update-in-place; posted only when opted in.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can read the friendly summary for a PR and, without
  opening any JSON/YAML, correctly name the affected readiness stages, the
  blocked/warning/pass status of each, and the single next action -- verified by
  the summary containing each of those elements, sourced from the envelope.
- **SC-002**: For any PR with a base identity set, the summary correctly places
  every finding into exactly one of {new, resolved, carried-over}, with zero
  findings mis-grouped -- verified by the differ's three groups being disjoint and
  covering the union of base and head fingerprints.
- **SC-003**: The renderer and differ are byte-identical across repeated runs on
  the same inputs (determinism), with no wall-clock dependency -- verified by a
  repeat-invocation equality test.
- **SC-004**: No PII/secret shape that the reused `interview_review._mask`
  contract detects -- email, SSN/national-ID-like number, long digit run, or
  `key: value` secret assignment -- appears verbatim in any rendered summary or
  composed comment body; verified by a redaction test over adversarial finding
  messages carrying those shapes. The test MUST also assert the documented v1
  limitation (FR-009): a bare DSN/connection-URL in a finding message is NOT
  claimed to be masked, so the test does not assert its removal -- it records the
  known residual gap rather than a false guarantee.
- **SC-005**: On a repository that has not opted in, enabling the feature's code
  changes nothing about CI behavior and posts no comment; when opted in, at most
  ONE friendly-summary comment exists per PR at any time -- verified by the
  sticky-marker composition test and the opt-in default.
- **SC-006**: The feature adds zero `retail check` rules and leaves the
  `build_review_result` / `sarif` / `review_pack_export` output shapes unchanged --
  verified by the existing rule-registry snapshot test staying green and the
  existing SARIF/review tests staying green.
- **SC-007**: The summary emits no numeric score / percentage / tally in any
  format -- verified by a test asserting the absence of a score field and of a
  bare percentage in the rendered text.

## Assumptions

- **Altitude (auto-decided; reversible: easy)**: this ships as a docs-first
  Product Module -- a SKILL + ONE pure, stdlib, deterministic renderer/differ over
  the `build_review_result` envelope + a sticky-comment template, plus an opt-in
  additive step in the existing `ci.yml`. Rationale: matches the shipped F025
  precedent ("adds no new gate, no rule, no CLI verb, no new workflow -- the agent
  is the runtime"), hard rule #8 (docs/skill first), and Principle VIII (static
  core stays stdlib-only, no network; B1/B3 guards keep DB/network imports out of
  the tested core). The networked GitHub post is a thin opt-in wrapper, not part
  of the deterministic core.
- **New-vs-pre-existing is TEMPORAL (auto-decided; reversible: easy)**: "changed
  vs pre-existing" is read as base-branch vs head (temporal), keyed on the shipped
  `finding_fingerprint`, which is exactly the SARIF `partialFingerprints` identity
  GitHub uses for new-vs-existing. It requires a base identity set (a base run or a
  supplied base SARIF/fingerprint list); when that is absent, the distinction is
  reported as undeterminable (FR-018). A changed-files-spatial reading is the
  weaker fallback and is out of scope for v1.
- The `build_review_result` envelope and `finding_fingerprint` shapes are stable
  and additive-versioned (`schema_version`); this feature consumes them by field
  and tolerates unknown additive fields.
- Reuses the existing GitHub Action / `ci.yml`; no new workflow file. The sticky
  comment uses the platform's own comment API through the opt-in wrapper.
- Reuses the shipped masking contracts (`interview_review._mask`,
  `readiness_evidence._scrub`); no new redaction engine is authored.
- The feature is per-PR (a portfolio / multi-PR roll-up is out of scope for v1),
  matching the F025 per-PR scope.
- **Fingerprint diff is line-position-sensitive (known v1 limitation)**: the
  temporal diff keys on the shipped `finding_fingerprint`, which includes the
  locator line/column. A pure line SHIFT (an unrelated edit above a finding) can
  therefore surface a stable finding as one RESOLVED + one NEW (a false-new). v1
  accepts this rather than inventing a location-tolerant identity that would
  diverge from the shipped fingerprint (the reuse-not-rebuild rule, FR-001). A
  future spec may adopt a more location-tolerant identity (closer to GitHub's
  `partialFingerprints` semantics) if the false-new noise proves material; the
  summary is honest about the diff's precision in the meantime (see Edge Cases).
- The lineage surfaces (`cross-table-lineage`, kpi-derivation-lineage) are an
  OPTIONAL enrichment for the affected-artifact narrative in v1 (FR-004 works from
  the envelope alone); deeper lineage-driven "which measures/dashboards changed
  downstream" is not required for the MVP and is not claimed beyond what the design
  specifies.
- Depends on the already-shipped review/SARIF/readiness/lineage surfaces
  remaining on `main`; it adds the presentation seam, not the underlying truth.
