# Design: Build the eligible OPEN + RECOMMENDED idea-bank ideas

**Date**: 2026-07-03
**Author**: Ahmed Shaaban (with Claude)
**Status**: Draft — for review
**Scope decision**: "Everything eligible" + "go as recommended across sessions"
**Supersedes/relates**: `docs/roadmap/idea-backlog.md` (generated, stale), reconciled
against `docs/roadmap/shipped-ideas.yaml` + `docs/roadmap/design-ideas-decisions.md`.

---

## 1. Purpose & scope

The idea bank lists 45 ideas; 17 shipped and 5 are settled. Of the remaining 24,
the owner selected the **eligible OPEN + RECOMMENDED** subset to build. After
verifying each against the committed tree (not the generated backlog), the buildable
scope is **8 ideas**:

| ID | Idea | Build type | Owner ruling applied |
|----|------|-----------|----------------------|
| I1 | Seed-Layer Route Honesty Rule | new `@register` rule | — (spec 067 Draft exists) |
| F1 | Navigation Regression Harness | test + scenarios YAML | — |
| I2 | Land bi-python planned cleaning artifacts | content (markdown) | — |
| D1 | Confusable-skill / path foot-gun guard | new `@register` rule | **path + stale-phrase only** (defer boundary.yaml) |
| H4 | Contract-Sufficiency Card | content (template) | **separate `templates/kpi-sufficiency-card.md`** |
| E2 | Wiring-Truth snapshot | test + verify-only generator | **keep guard model, add snapshot test** |
| E5 | Design-Lint severity (reshaped) | test assertion (no rule) | **branch-level only, no declared table** |
| E7 | `retail doctor` drift digest | CLI helper (no rule) | **repo-wide read-only aggregator** |

**Dropped (not in scope), for the record:**
- **H5** — ineligible: smuggles threshold semantics into the settled F5/F6 stats-engine
  rejection zone. Drop unless reframed as strict presence/absence.
- **A10** — no first step, V4/F5; defer.
- **I4** — namespace lint; spec 002 is Draft, low value; defer.

## 2. Non-negotiable eligibility spine (the review gate every item faces)

Every item below is checked against the constitution's nine principles. The four that
bite this work:

1. **No numeric confidence/health score** (roadmap hard rule #9 / Principle re
   readiness). H4 emits `present|absent` + `status` + `blocking_reasons[]`, never a %.
   E7 emits a findings *digest*, never a score.
2. **No self-granting a gate** (Principle V). E7, F1 **report**; they never write
   `approvals[]` or move a stage to `pass`.
3. **No resolving a human judgment call** (Principle V). I1, D1 **flag drift**; they
   never decide grain / PII / product identity / business rollup.
4. **Static-first, never-execute** (Principle VIII + B1/B3 boundary). The three new
   rules are stdlib-only in the `retail check` core and read `ctx.tracked_files`,
   never the live filesystem or a DB. Any non-stdlib import (none expected here) is
   lazy.

Additionally honored:
- **Observed-not-declared severity** (ratified spec 044). E5 is reshaped to assert
  severity **at the branch level** and let `severity_posture` observe it — it adds
  **no** declared per-rule severity table (which would conflict with 044).
- **C086 is an example, not the schema** (Principle VII). H4 **cites** a worked
  example, never inlines client data; the c086 corpus is gone (#144) so H4 references
  the surviving `retail_store_sales` example.

## 3. Shared mechanism (all already shipped — we reuse, not rebuild)

- **`retail scaffold <ID>`** (idea E6, `src/seshat/scaffold.py`) does the **5-place
  wiring** for a new rule: module stub, `EXPECTED_RULE_IDS` membership in the wiring
  test, glossary rules-table row, `rules-manifest.json` entry, severity-posture entry.
  It prints the two golden-record regen commands. Used by I1, D1.
- **Rule contract**: `@register(RULE_ID, title)` on a `check(ctx: RuleContext) ->
  Iterable[Finding]` in `src/seshat/rules/<name>.py`. `RuleContext(repo_root,
  tracked_files)` and `Finding(rule_id, severity, message, locator)` live in
  `src/seshat/core.py`.
- **Test pattern**: adversarial **good/bad fixture corpus** + a **fail-closed
  locator/severity/count** assertion, mirroring `tests/unit/test_design_*.py`.
- **Drift manifests**: SC1 status-claims (`docs/quality/status-claims.yaml`) and SC2
  rule-count (`docs/quality/rule-count-claims.yaml`). Content ideas register their
  prose claims here; each new rule bumps the count 51→N and updates the SC2 anchor in
  `docs/glossary.md` + the manifest (scaffold regen handles manifest+severity; the
  glossary prose anchor is a manual edit that MUST move in lockstep).

## 4. Per-idea design (logic + eligibility boundary)

Each rule's *value* is its detection logic and boundary — scaffold handles the wiring.

### I1 — Seed-Layer Route Honesty Rule  `[new rule, ~ID "SR1"]`
**Logic**: parse each seed `skills/**/SKILL.md` (and `INDEX.md`) route table; for each
route resolve its terminal-artifact target against `ctx.tracked_files`. If the target
does **not** resolve, the route MUST carry a `planned` marker. ERROR on a **LIVE**
route whose terminal artifact is unresolved (a dangling live route). Honest `planned`
routes pass.
**Boundary**: pure resolution + presence check; decides nothing. Extends A1
(`routes.py`, routing-manifest targets) and AQ1 (answerability) to the *seed-skill
route tables* they don't cover. Build from **spec 067** (Draft).
**Test**: fixtures — live-resolves (pass), live-dangling (ERROR), planned-dangling
(pass), moved-marker (ERROR).

### F1 — Navigation Regression Harness  `[test, no rule]`
**Logic**: `tests/unit/test_navigation_regression.py`, parametrized over a committed
`tests/fixtures/nav-scenarios.yaml` + a COMPASS-table extractor. Assert each expected
navigation target (a) resolves on disk (in `tracked_files`) and (b) is present in
`docs/routing/routes.yaml`. Fail-closed on a rename/miss.
**Boundary**: new surface is the **COMPASS table** — A1/A3 only guard `routes.yaml`.
Test-only; no rule id, no score.
**Test**: mutation-verified (rename a target → test fails).

### I2 — Land bi-python planned cleaning artifacts  `[content]`
**Logic**: `skills/bi-python-knowledge/INDEX.md` has a **Planned routes** table naming
6 not-yet-written files. Author the **terminal checklist + 1–2 highest-value pattern/
knowledge files** (start with `knowledge/groupby-aggregation-and-grain.md` — it's
referenced live twice as "planned"), then flip those INDEX route rows `planned → live`.
Keep the `aggregation-grain-checklist` fork boundary intact (Principle: depend, never
fork).
**Boundary**: content only; KPI *meaning* stays upstream (INDEX boundary note). No code.
**Test**: links resolve; register the "now-live" status in SC1 so the claim can't drift.

### D1 — Confusable-skill / path foot-gun guard  `[new rule, ~ID "DR1"]` (scoped)
**Logic**: `src/seshat/rules/design_routes.py` with **two** checks (boundary.yaml
deferred per ruling): (1) **bad-prefix path check** — flag design-skill route targets
using a known foot-gun path prefix; (2) **curated stale-phrase manifest** (doc + line
anchored, like SC1's anchor discipline) — flag a committed doc line asserting a stale
verb/status. Fail-loud.
**Boundary**: static text scan; the stale-phrase list is hand-curated (no inference).
Decides nothing. Defer `design-system-boundary.yaml` until a real two-system collision
exists (YAGNI).
**Test**: fixtures — clean, bad-prefix (ERROR), stale-phrase-present (ERROR),
anchor-moved (ERROR).

### H4 — Contract-Sufficiency Card  `[content, template]`
**Logic**: `templates/kpi-sufficiency-card.md` — per KPI: `kpi_id`, `required_fields[]`
each `present|absent`, resulting `status` + `blocking_reasons[]`. Reference it from
`docs/metrics/retail-kpi-catalog.md` + `skills/retail-kpi-knowledge/INDEX.md`. Cite a
filled contract under `skills/retail-kpi-knowledge/contracts/` (e.g. `net-sales.md`) as
the worked example, never inline client data.
**Boundary**: **NO numeric score** (rule #9) — `present/absent` + `status` only, exactly
the readiness `status + evidence + blockers` shape. Template only; filling it per KPI is
later analyst work.
**Test**: template well-formed; SC1 registers the "template shipped" claim.

### E2 — Wiring-Truth snapshot  `[test + verify-only generator]` (guard model)
**Logic**: keep the shipped **guard** architecture (E1 meta-gate + scaffold). Add (1) a
**live == committed snapshot test** for `EXPECTED_RULE_IDS` (fails if the registry and
the committed snapshot diverge), and (2) a glossary-rule-table generator that runs in
**verify-only** mode (fails if the committed glossary table drifted from the registry;
it does not rewrite). **Do NOT** add a severity field to `@register` (044).
**Boundary**: verify-only; no generate-and-overwrite, no severity model change. Closes
the drift E1 doesn't (registry↔snapshot, registry↔glossary-table).
**Test**: mutation — add a rule without updating snapshot → test fails.

### E5 — Design-lint severity (reshaped)  `[test assertion, no rule]`
**Logic**: assert **at the branch level** that each design (D/DL/CT) rule emits
`warning` for readability findings and `error` for purity/fidelity findings, then let
`severity_posture` observe it. **No declared per-rule severity table.**
**Boundary**: honors the ratified observed-not-declared model (044). Low value — kept
only because "everything eligible" was chosen; if it fights the severity_posture
tests, drop it (noted for the plan).
**Test**: assertion over the design rules' emitted severities.

### E7 — `retail doctor` drift digest  `[CLI helper, no rule]`
**Logic**: `src/seshat/doctor.py` + a `retail doctor` subcommand that **aggregates
existing read-only checks** (rule-manifest snapshot, `routes_coverage`, `status_claims`)
+ lightweight file-existence probes, and prints a **Findings digest**. No new
`@register` rule; imported lazily like scaffold.
**Boundary**: **read, never fix**; **no score**; never self-grants. Broader than the
shipped `scaffold --doctor` (which only checks rule-wiring lockstep) — it's a repo-wide
diagnostician, not a duplicate.
**Test**: digest lists a seeded drift; exits 0 (advisory, not a gate) — or non-zero
only if the owner wants it gating (default: advisory).

## 5. Build sequencing (waves)

Ordered by dependency + risk, designed for **multi-session, per-idea execution** (one
spec→plan→PR cycle each; "go as recommended across sessions"):

- **Wave 1 — content, zero-risk, no rule-count change**: I2, H4. (Author files; register
  SC1 claims. No registry churn.)
- **Wave 2 — the three new rules, each independent**: I1, D1. (Each: `retail scaffold
  <ID>` → write `check()` → fixtures → bump count 51→52→53 + SC2 anchor.) Serialize to
  keep the rule count monotonic and avoid `EXPECTED_RULE_IDS` merge clashes.
- **Wave 3 — tests/tooling, no rule id**: F1, E2, E5, E7. (Independent; can parallelize
  across sessions since none touch the registry count.)

Rationale: content first (no registry risk), then rules one at a time (registry count
is a serialization point — two in flight collide on `EXPECTED_RULE_IDS`/manifest), then
tooling (touches no count). Each idea is its own PR with `retail check` green.

## 6. Testing & verification (all waves)

- Every new rule: adversarial good/bad fixtures + fail-closed locator/severity/count,
  per `tests/unit/test_design_*.py`.
- `ruff format --check`, `ruff check`, `pytest -m unit`, then `retail check` +
  `retail kit-lint` green before each PR (the repo's mandatory local gate).
- Rule-count lockstep: after each new rule, manifest+severity via scaffold regen; SC2
  glossary anchor + `rule-count-claims.yaml` edited in the same commit.

## 7. Risks & mitigations

- **Rule-count merge clashes** (I1, D1 in parallel) → serialize Wave 2.
- **E5 fighting severity_posture** → if the branch-level assertion is redundant with
  existing posture tests, drop E5 (it's the weakest item).
- **E7 scope creep** → cap at aggregating *existing* checks + file-existence; no new
  detection logic in the doctor.
- **Stale-phrase manifest rot** (D1) → anchor each entry doc+line (SC1 discipline) so a
  moved line is itself flagged.

## 8. Out of scope

No Power BI execution (F016 deferred), no DB, no numeric scores, no gate self-granting,
no `design-system-boundary.yaml` (deferred), no H5/A10/I4.
