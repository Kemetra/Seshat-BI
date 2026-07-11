# Top Idea Bank Execution Plan

## 1. Purpose

This document converts five selected **Idea Bank** candidates into a safe, ordered
execution *sequence*. It is the bridge between exploratory ideas and real feature work.

- This document is **planning only**. It changes no runtime behavior.
- This is **not implementation**. No idea below is built here.
- This is **not a roadmap commitment**. The Idea Bank
  (`docs/roadmap/idea-backlog.md`) remains exploratory; the authoritative roadmap stays
  `docs/roadmap/roadmap.md`.
- Each idea needs an explicit **human decision** before any execution begins.
- Each idea must still go through the repo's **normal spec/feature process** (a numbered
  feature, its spec, and review) — selection here does not skip that.

A plan is a hypothesis about the safest order; it is not permission to build.

## 2. Source Ideas

The five candidates, in recommended execution order. "First implementation PR" names the
later, separate PR each idea would get — none of which is opened here.

| Priority | Idea ID | Idea name | Category | Value | Feasibility | Why selected | First implementation PR |
|---|---|---|---|---|---|---|---|
| 1 | A1 | Machine-Checkable Route Registry + Planned/Built Status Manifest | Gate / routing integrity | 9/10 | 8/10 | Turns the two-hop routing contract into something *verifiable*; no `routes.yaml` exists today and planned routes only emit prose notes. Convergent top idea. | PR 1 — `feat: add route registry manifest` |
| 2 | B2 | Gate Observability Ledger / Structured Findings Output | Observability | 8/10 | 9/10 | Improves the *existing* findings output (a single `_format` chokepoint) before more checks are added; highest feasibility. | PR 2 — `feat: add structured findings output` |
| 3 | B1 | Never-Execute Invariant Guard | Invariant protection | 9/10 | 8/10 | Protects the core "knowledge/reasoning layers never execute" invariant with a deterministic, static guard. | PR 3 — `test: guard never-execute invariant` |
| 4 | F7 | KPI Decision-Question Index per Domain | KPI usability | 6/10 | 9/10 | Makes the KPI layer discoverable by the business questions each domain answers; pure docs, no runtime risk. | PR 4 — `docs: add KPI decision-question index` |
| 5 | F8 | Per-Table KPI Coverage Scorecard | Analytical coverage | 7/10 | 8/10 | Adds an explicit, status/blocker-based view of which KPIs a table can support, after the KPI layer is more navigable. | PR 5 — `docs: add KPI coverage scorecard` |

> Values/feasibility are the Idea Bank reviewer's triage opinion, carried forward for
> reference only. They are not commitments and not fabricated readiness scores.

## 3. Execution Philosophy

Every PR below obeys the same discipline:

- **Small PRs** — one feature family per PR, reviewable in isolation.
- **One feature family per PR** — no bundling A1 work into the B2 PR, etc.
- **Static / read-only first** — prefer checks that read tracked files over anything that runs.
- **Docs before automation where possible** — F7/F8 are docs; A1 adds a static check only
  after the manifest format is clear.
- **No runtime adapters** — nothing here touches the Power BI execution adapter (F016) or
  any execution path.
- **No auto-approval** — no feature self-grants a human approval (grain, PII, rollups,
  publish-safety remain human gates).
- **No fabricated confidence** — readiness and coverage are status + evidence + blockers,
  never a made-up number.
- **No execution during routing** — the route registry resolves references; it never runs anything.
- **Deterministic checks** — any added check is stdlib-only and reproducible, no network/DB.
- **No mixing KPI meaning with SQL/DAX/Python implementation** — `retail-kpi-knowledge`
  owns meaning; the implementation layers consume a ready contract. F7/F8 stay in the KPI layer.
- **No dashboard or publish readiness granted by these features** — none of A1/B2/B1/F7/F8
  advances a readiness stage or grants a gate.

## 4. Dependency Order

1. **A1 — Machine-Checkable Route Registry**
2. **B2 — Structured Findings Output**
3. **B1 — Never-Execute Guard**
4. **F7 — KPI Decision-Question Index**
5. **F8 — KPI Coverage Scorecard**

Why this order:

- **A1 first** creates route integrity (every route points to a real file or an honest
  planned/deferred marker) and the manifest that later route/eval work can build on.
- **B2 next** improves the *existing* findings output (a single, already-present chokepoint)
  before any new checks pile more findings onto it — better to standardize the output shape
  while the surface is small.
- **B1 then** protects the never-execute invariant; it benefits from B2's structured output
  to report a violation cleanly, and from A1's registry pattern as a model for a static rule.
- **F7 next** improves KPI discoverability (docs only) without any runtime risk, once the
  integrity/observability/invariant foundation is in place.
- **F8 last** adds analytical coverage on top of a KPI layer that F7 has made more navigable;
  coverage is most meaningful once questions/contracts are easy to find.

## 5. PR Execution Plan

Each subsection scopes a *future* PR. None is executed in this document.

### PR 1 — feat: add route registry manifest

- **Idea ID:** A1
- **Goal:** Make the routing contract machine-checkable — a manifest of routes where each
  entry points to an existing file or an explicit planned/deferred marker, plus (only if it
  fits the existing pattern) one static rule that fails on an unresolved route.
- **Proposed branch:** `feat/a1-route-registry`
- **Allowed files:** a new route manifest (`docs/routing/routes.yaml` or `routes.yaml`,
  whichever matches repo convention); at most one new rule module under `src/seshat/rules/`;
  the `EXPECTED_RULE_IDS` set in `tests/unit/test_rules_wiring.py`; a focused unit test for
  the new rule.
- **Forbidden files:** any B2/B1/F7/F8 surface; KPI contracts/domains/packs; readiness
  templates; GitHub Actions; unrelated `src/` modules.
- **Implementation notes:** inspect `COMPASS.md` and `docs/knowledge-map.md` for the routes
  to mirror; inspect the registry pattern in `src/seshat/registry.py` + `src/seshat/rules/*.py`
  (rules register via a decorator and are asserted by `EXPECTED_RULE_IDS`). Build the manifest
  first; add the rule *only* if the format is clear and it slots into the existing
  `@register` / `EXPECTED_RULE_IDS` pattern. Every route must resolve to a real file or carry
  a planned/deferred marker.
- **Validation commands (to run in that PR):** `python -m pytest tests/unit/test_rules_wiring.py`;
  the repo's static check (`retail check`) if it covers rules; a manifest-resolution check that
  every referenced path exists or is marked planned.
- **Acceptance criteria:** manifest exists and every entry resolves or is honestly marked
  planned; if a rule was added, it is registered AND present in `EXPECTED_RULE_IDS` and its
  test passes; no runtime/route execution introduced.
- **Stop rules:** if the manifest format is not clearly derivable from existing conventions,
  ship the manifest as docs only and defer the rule; do not invent a schema. Do not touch
  B2/B1/F7/F8.
- **Rollback notes:** delete the manifest file and the rule module; remove the rule's id from
  `EXPECTED_RULE_IDS`; the change is additive and isolated.
- **Risk level:** Medium (adds a rule into a wired registry; the wiring test is the guard).

### PR 2 — feat: add structured findings output

- **Idea ID:** B2
- **Goal:** Add an *optional* structured (JSON-first) output for findings while preserving
  the default human-readable text output exactly.
- **Proposed branch:** `feat/b2-structured-findings`
- **Allowed files:** the findings output chokepoint (`src/seshat/runner.py` — `_format` /
  `run`) and the CLI flag plumbing in `src/seshat/cli.py`; the `Finding` dataclass in
  `src/seshat/core.py` only if a serializer is needed; a focused test for the JSON output.
- **Forbidden files:** rule behavior (`src/seshat/rules/*`); A1 manifest; KPI/readiness files;
  GitHub Actions.
- **Implementation notes:** preserve the default text output (`runner._format` → `print`)
  byte-for-byte; add optional structured output behind a flag. Prefer **JSON first**; defer
  SARIF unless it is very small and clean. Reuse the existing `Finding` dataclass and the
  single output chokepoint — do not scatter formatting. No rule logic changes.
- **Validation commands:** `python -m pytest`; run the CLI with no flag and diff against
  current text output (must be identical); run with the JSON flag and validate the JSON parses
  and round-trips the findings.
- **Acceptance criteria:** default output unchanged; JSON output validates and contains the
  same findings; no rule behavior changed.
- **Stop rules:** if adding JSON would change default text output, stop and reconsider the
  flag design; do not alter findings semantics. Defer SARIF if it is not trivially clean.
- **Rollback notes:** remove the flag and the serializer; the chokepoint reverts to text-only.
- **Risk level:** Low (additive, behind a flag, single chokepoint).

### PR 3 — test: guard never-execute invariant

- **Idea ID:** B1
- **Goal:** Add a deterministic guard that the reasoning/CLI modules import no DB/network at
  module scope, protecting the never-execute invariant.
- **Proposed branch:** `test/b1-never-execute-guard`
- **Allowed files:** a new sentinel test under `tests/`; at most one static rule module under
  `src/seshat/rules/` (stdlib `ast` only) with its `EXPECTED_RULE_IDS` entry, *only if* it
  fits the existing pattern.
- **Forbidden files:** rule *behavior* of existing rules; A1/B2/F7/F8 surfaces; KPI/readiness
  files; dependencies; GitHub Actions.
- **Implementation notes:** add sentinel tests asserting no DB/network imports at **module
  scope** for the reasoning/CLI modules; if a static rule is added, use stdlib `ast` to scan
  for module-scope imports of DB/network libraries. **Do not** block legitimate **lazy**
  imports inside handlers (the repo deliberately imports `yaml`/db extras inside handlers). No
  runtime connection attempts; no dependency changes.
- **Validation commands:** `python -m pytest tests/` (the new sentinel test); if a rule was
  added, `python -m pytest tests/unit/test_rules_wiring.py`.
- **Acceptance criteria:** sentinel test passes and fails loudly if a module-scope DB/network
  import is introduced; lazy in-handler imports still pass; if a rule was added it is wired and
  in `EXPECTED_RULE_IDS`.
- **Stop rules:** if distinguishing module-scope from lazy imports reliably is not feasible
  with `ast`, ship the sentinel test only and defer the rule. Never attempt a real connection
  to "prove" the invariant.
- **Rollback notes:** delete the sentinel test and (if added) the rule + its `EXPECTED_RULE_IDS`
  entry.
- **Risk level:** Medium (must not flag legitimate lazy imports — that is the main failure mode).

### PR 4 — docs: add KPI decision-question index

- **Idea ID:** F7
- **Goal:** Make KPIs discoverable by the business questions each domain answers, routing each
  question to a real contract or an honest planned/deferred note.
- **Proposed branch:** `docs/f7-kpi-decision-questions`
- **Allowed files:** KPI **domain** docs under `skills/retail-kpi-knowledge/domains/`; the
  contract **template** under `skills/retail-kpi-knowledge/references/` *only* if adding an
  optional `answers_questions` field that the template conventions already allow.
- **Forbidden files:** SQL/DAX/Python implementation; `src/`; `tests/`; readiness templates;
  GitHub Actions; the meaning of any existing contract (no redefinition).
- **Implementation notes:** add a "business questions this domain answers" section to domain
  docs; route each question to an existing contract or a planned/deferred marker — never
  fabricate a contract. Optionally add an `answers_questions` field **only if** the metric
  contract template conventions allow it. No DAX/SQL/Python/big-data implementation; this
  stays inside the KPI meaning layer.
- **Validation commands:** a reference-resolution check that every question points to a real
  contract file or a planned/deferred marker; manual two-hop read of one domain.
- **Acceptance criteria:** each domain lists its decision questions; every question resolves to
  a real contract or an honest planned note; no contract meaning changed; no implementation added.
- **Stop rules:** if a question has no contract and none is planned, mark it planned/deferred —
  do not invent a contract. Do not let a question imply a DAX/SQL formula.
- **Rollback notes:** remove the added questions sections (and the optional field if added);
  pure-docs revert.
- **Risk level:** Low (docs within the KPI layer; main risk is phantom contract references).

### PR 5 — docs: add KPI coverage scorecard

- **Idea ID:** F8
- **Goal:** Add a per-table view of which KPIs the table can support, expressed as explicit
  statuses and blockers — never a numeric confidence score.
- **Proposed branch:** `docs/f8-kpi-coverage-scorecard`
- **Allowed files:** a KPI coverage scorecard section or template under
  `skills/retail-kpi-knowledge/` (e.g. `checklists/` or `references/`).
- **Forbidden files:** SQL/DAX/Python implementation; `src/`; `tests/`; readiness templates;
  dashboard/publish surfaces; GitHub Actions.
- **Implementation notes:** coverage must use **explicit statuses/blockers** (e.g.
  covered / needs-business-definition / blocked-on-missing-field), mirroring the readiness
  vocabulary. **No numeric confidence score.** Do not infer "covered" from a field merely
  existing — absence of a required field is a blocker, not silent coverage. Does not grant
  dashboard or publish readiness.
- **Validation commands:** review that every scorecard cell is a status/blocker, not a number;
  confirm no readiness stage is advanced by the scorecard.
- **Acceptance criteria:** scorecard expresses coverage as statuses + blockers only; no numeric
  score; no readiness/dashboard/publish gate granted; missing fields surface as blockers.
- **Stop rules:** if tempted to compute a coverage percentage, stop — express it as
  status/blocker. Do not claim coverage from missing fields.
- **Rollback notes:** delete the scorecard section/template; pure-docs revert.
- **Risk level:** Low (docs; main risk is drifting into a score or implying readiness).

## 6. Cross-Feature Risk Register

| Risk | Affected ideas | Why it matters | Mitigation |
|---|---|---|---|
| Idea Bank accidentally becoming roadmap | all | Selection here could read as "approved to build" | Restate everywhere: planning only; human decision + spec process required before any PR |
| Over-expanding scope | all | A small PR quietly grows into several feature families | One feature family per PR; explicit allowed/forbidden file lists per PR |
| Phantom routes | A1, F7 | A manifest/question pointing at a nonexistent file breaks the two-hop contract | A1 requires every route to resolve or be marked planned; F7 routes questions to real contracts or planned notes |
| Checks not registered in `EXPECTED_RULE_IDS` | A1, B1 | A rule that exists but isn't in the wiring set is silently un-validated | Any new rule must be added to `EXPECTED_RULE_IDS` in `tests/unit/test_rules_wiring.py` in the same PR |
| CLI breaking backward compatibility | B2 | Changing default output breaks existing consumers/scripts | B2 preserves default text output exactly; structured output is opt-in behind a flag |
| Runtime imports creeping into module scope | B1 | A module-scope DB/network import would violate never-execute | B1 sentinel guard; lazy in-handler imports stay allowed |
| Fake numeric scores | F8, all | A made-up confidence number contradicts "status + evidence + blockers" | F8 uses explicit statuses/blockers only; no numeric score anywhere |
| KPI meaning leaking into DAX/SQL/Python/Big-data | F7, F8 | Recreates the multi-owner conflict the layers were designed to avoid | F7/F8 stay in the KPI meaning layer; no implementation surfaces touched |
| Readiness approval being implied | all | A feature implying a gate passed bypasses human approval | No feature advances a stage or grants a gate; approvals remain human |
| F8 becoming score-based instead of blocker/status-based | F8 | A score hides the real blockers and fabricates confidence | F8 acceptance criteria forbid numeric scores; coverage = status + blockers |
| Dashboard/publish readiness granted indirectly | all | A coverage/observability signal mistaken for "ready to ship" | None of these features touches dashboard/publish readiness; stated in each PR's stop rules |

## 7. Validation Matrix

| Validation check | Applies to | Expected result | Notes |
|---|---|---|---|
| Route references resolve | A1 | Every manifest route points to an existing file | A planned/deferred marker is the only allowed exception |
| Planned/deferred routes marked honestly | A1, F7 | Unbuilt targets carry a planned marker, never a phantom | Matches the repo's existing `[planned]` honesty pattern |
| Rule registry updated when a rule is added | A1, B1 | New rule registered via the existing decorator | `src/seshat/registry.py` + `src/seshat/rules/*` pattern |
| `EXPECTED_RULE_IDS` includes new rules | A1, B1 | Wiring test passes with the new id present | `tests/unit/test_rules_wiring.py` |
| Default CLI text output preserved | B2 | Output with no flag is byte-identical to today | `src/seshat/runner.py` `_format`/`run` chokepoint |
| JSON output validates | B2 | Structured output parses and round-trips findings | JSON first; SARIF deferred unless trivial |
| No DB/network imports at module scope | B1 | Sentinel test passes; module scope clean | Lazy in-handler imports remain allowed |
| KPI questions route to real contracts or planned/deferred notes | F7 | Every question resolves honestly | No fabricated contracts |
| KPI coverage uses explicit statuses/blockers, not numeric confidence | F8 | Coverage cells are statuses/blockers | No score; missing field → blocker |
| No Power BI execution | all | No execution adapter touched | F016 stays gated/deferred |
| No dashboard readiness granted | all | No stage advanced by these features | Readiness remains human-gated |
| No human approval self-granted | all | No approval implied or auto-set | Grain/PII/rollup/publish stay human |

## 8. Implementation Prompt Pack

Five copy-ready prompts. **Text only — do not execute any of these in this PR.** Each is
gated on the prior step; run only after its gate condition is met and the plan is approved.

### NEXT PROMPT 1 — A1 — DO NOT RUN UNTIL THIS PLAN IS APPROVED

- **Mission:** Add a machine-checkable route registry manifest mirroring the COMPASS /
  knowledge-map routes; add at most one static route-resolution rule if it fits the existing
  pattern. Do not implement B2/B1/F7/F8.
- **Branch name:** `feat/a1-route-registry`
- **PR title:** `feat: add route registry manifest`
- **Commit message:** `feat: add route registry manifest`
- **Allowed files:** route manifest (`docs/routing/routes.yaml` or `routes.yaml` per repo
  convention); ≤1 new `src/seshat/rules/*.py`; `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py`; a focused unit test.
- **Forbidden files:** B2/B1/F7/F8 surfaces; KPI contracts/domains/packs; readiness templates;
  GitHub Actions; unrelated `src/`.
- **Implementation constraints:** inspect `COMPASS.md`, `docs/knowledge-map.md`, and
  `src/seshat/rules/` first; create the registry only if the format is clear; every route must
  point to an existing file or a planned/deferred marker; add the rule only if it fits the
  existing `@register` / `EXPECTED_RULE_IDS` pattern; stdlib-only; read-only (no execution).
- **Validation commands:** `python -m pytest tests/unit/test_rules_wiring.py`; manifest path
  resolution check; `retail check` if applicable.
- **Acceptance criteria:** manifest resolves end-to-end or marks planned; rule (if any) wired +
  in `EXPECTED_RULE_IDS`; no runtime/route execution.
- **Stop rules:** unclear format → ship docs-only manifest, defer the rule; never invent a
  schema; touch no other idea.
- **PR body template:**
  `## Summary` (what A1 adds) · `## Scope` (manifest [+ optional rule]) · `## Validation`
  (commands actually run; do not claim CI passed unless verified) · `## Boundaries preserved`
  (no execution; Idea Bank still exploratory; no readiness granted).

### NEXT PROMPT 2 — B2 — DO NOT RUN UNTIL A1 IS MERGED

- **Mission:** Add optional structured (JSON-first) findings output while preserving default
  text output exactly. No rule behavior changes.
- **Branch name:** `feat/b2-structured-findings`
- **PR title:** `feat: add structured findings output`
- **Commit message:** `feat: add structured findings output`
- **Allowed files:** `src/seshat/runner.py` (output chokepoint), `src/seshat/cli.py` (flag),
  `src/seshat/core.py` (`Finding` serializer if needed), a focused JSON-output test.
- **Forbidden files:** `src/seshat/rules/*` behavior; A1 manifest; KPI/readiness files;
  GitHub Actions.
- **Implementation constraints:** preserve default text output byte-for-byte; structured output
  behind a flag; JSON first, SARIF only if trivially clean; reuse the `Finding` dataclass and
  the single `runner._format` chokepoint; no rule semantics changes.
- **Validation commands:** `python -m pytest`; CLI with no flag diffed against current output
  (identical); CLI with JSON flag validated.
- **Acceptance criteria:** default unchanged; JSON validates and matches findings; rules unchanged.
- **Stop rules:** if JSON changes default output, stop; defer SARIF if not clean.
- **PR body template:** `## Summary` · `## Scope` (opt-in structured output) · `## Validation`
  (commands run; no unverified CI claim) · `## Boundaries preserved` (default output intact; no
  rule/readiness change).

### NEXT PROMPT 3 — B1 — DO NOT RUN UNTIL B2 IS MERGED

- **Mission:** Guard the never-execute invariant with sentinel tests (and optionally one
  stdlib-`ast` static rule) for no module-scope DB/network imports. Do not block lazy imports.
- **Branch name:** `test/b1-never-execute-guard`
- **PR title:** `test: guard never-execute invariant`
- **Commit message:** `test: guard never-execute invariant`
- **Allowed files:** new sentinel test under `tests/`; ≤1 `src/seshat/rules/*.py` (stdlib
  `ast`) + its `EXPECTED_RULE_IDS` entry, only if it fits the pattern.
- **Forbidden files:** existing rule behavior; A1/B2/F7/F8 surfaces; KPI/readiness files;
  dependencies; GitHub Actions.
- **Implementation constraints:** sentinel tests for no module-scope DB/network imports; stdlib
  `ast` only if adding a rule; do not block legitimate lazy in-handler imports; no runtime
  connection attempts; no dependency changes.
- **Validation commands:** `python -m pytest tests/`; `python -m pytest tests/unit/test_rules_wiring.py`
  if a rule was added.
- **Acceptance criteria:** sentinel fails on a new module-scope DB/network import, passes on
  lazy imports; rule (if any) wired + in `EXPECTED_RULE_IDS`.
- **Stop rules:** can't reliably separate module-scope from lazy → ship sentinel test only;
  never open a real connection.
- **PR body template:** `## Summary` · `## Scope` (sentinel [+ optional rule]) · `## Validation`
  (commands run; no unverified CI claim) · `## Boundaries preserved` (no deps; lazy imports
  allowed; reasoning stays non-executing).

### NEXT PROMPT 4 — F7 — DO NOT RUN UNTIL B1 IS MERGED

- **Mission:** Add business decision-questions to KPI domain docs, routing each to a real
  contract or an honest planned/deferred note. No DAX/SQL/Python implementation.
- **Branch name:** `docs/f7-kpi-decision-questions`
- **PR title:** `docs: add KPI decision-question index`
- **Commit message:** `docs: add KPI decision-question index`
- **Allowed files:** `skills/retail-kpi-knowledge/domains/*`; the contract template under
  `skills/retail-kpi-knowledge/references/` only if adding an `answers_questions` field the
  template conventions allow.
- **Forbidden files:** SQL/DAX/Python implementation; `src/`; `tests/`; readiness templates;
  GitHub Actions; existing contract meaning.
- **Implementation constraints:** add decision questions per domain; route each to an existing
  contract or a planned/deferred marker honestly; optional `answers_questions` only if template
  conventions allow; no implementation; stay inside the KPI meaning layer.
- **Validation commands:** reference-resolution check (every question → real contract or planned
  note); manual two-hop read of one domain.
- **Acceptance criteria:** each domain lists decision questions; all resolve honestly; no
  contract meaning changed.
- **Stop rules:** no contract + none planned → mark planned/deferred, do not invent; no question
  may imply a formula.
- **PR body template:** `## Summary` · `## Scope` (KPI domain docs) · `## Validation` (resolution
  check; no unverified CI claim) · `## Boundaries preserved` (KPI meaning only; no implementation;
  no readiness).

### NEXT PROMPT 5 — F8 — DO NOT RUN UNTIL F7 IS MERGED

- **Mission:** Add a per-table KPI coverage scorecard using explicit statuses/blockers (no
  numeric confidence). Grants no readiness.
- **Branch name:** `docs/f8-kpi-coverage-scorecard`
- **PR title:** `docs: add KPI coverage scorecard`
- **Commit message:** `docs: add KPI coverage scorecard`
- **Allowed files:** a scorecard section/template under `skills/retail-kpi-knowledge/`
  (`checklists/` or `references/`).
- **Forbidden files:** SQL/DAX/Python implementation; `src/`; `tests/`; readiness templates;
  dashboard/publish surfaces; GitHub Actions.
- **Implementation constraints:** coverage = explicit statuses/blockers (covered /
  needs-business-definition / blocked-on-missing-field); no numeric score; missing field is a
  blocker, never silent coverage; grants no dashboard/publish readiness.
- **Validation commands:** review every cell is a status/blocker not a number; confirm no stage
  advanced.
- **Acceptance criteria:** statuses/blockers only; no score; no gate granted; missing fields
  surface as blockers.
- **Stop rules:** tempted to compute a percentage → stop, use status/blocker; no coverage from
  missing fields.
- **PR body template:** `## Summary` · `## Scope` (KPI scorecard docs) · `## Validation` (cell
  review; no unverified CI claim) · `## Boundaries preserved` (status/blocker only; no score; no
  readiness granted).

## 9. Final Recommended Sequence

| Order | Idea | Type | Why now | Must wait for |
|---|---|---|---|---|
| 1 | A1 — Route Registry | Gate / routing integrity | Makes the routing contract verifiable; foundation for later route/eval work | Plan approval + human decision |
| 2 | B2 — Structured Findings Output | Output observability | Standardize the existing output surface before adding more checks | A1 merged |
| 3 | B1 — Never-Execute Guard | Invariant protection | Protects the core invariant; uses B2's output + A1's rule pattern | B2 merged |
| 4 | F7 — KPI Decision-Question Index | KPI usability | Pure-docs discoverability, no runtime risk, once the foundation is set | B1 merged |
| 5 | F8 — KPI Coverage Scorecard | Analytical coverage | Coverage is meaningful once F7 makes the KPI layer navigable | F7 merged |

## 10. Final Verdict

**Planning result: PASS**

This result is PASS because, for this PR:

- exactly one planning file is changed (`docs/planning/top-idea-bank-execution-plan.md`);
- no implementation is included (no idea is built);
- all five ideas are separated into later, individually gated PRs;
- hard project boundaries are preserved (agent-first; stage order; KPI meaning vs
  implementation; no execution; no self-granted approval; readiness = status + evidence +
  blockers; Idea Bank stays exploratory);
- the implementation prompts are scoped (explicit allowed/forbidden files) and gated (each
  waits for the prior to merge).

It would be **BLOCKED** if any of these were true: more than one file changed; implementation
accidentally included; source/tests/KPI/readiness files edited; prompts encouraged scope
mixing; or validation could not confirm planning-only scope.
