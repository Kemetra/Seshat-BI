# Post-Integration Stabilization Plan

## 1. Purpose

This plan defines the **next phase** after the completed Idea Bank feature
sequence (#62–#66) and the separate **Integration Smoke Test** for those five
features. Rather than opening new broad feature work, the project should now:

1. **Summarize current capability** (a stable snapshot),
2. **Prove one KPI end-to-end** (Net Sales), then
3. **Define scale boundaries** (Big Data strategy, then volume-assessment templates).

What this plan is and is not:

- This is **planning only**. It changes no runtime behaviour and builds none of
  the four items below.
- This is **not implementation**.
- This is **not a roadmap commitment**. The Idea Bank
  (`docs/roadmap/idea-backlog.md`) stays exploratory; the authoritative roadmap
  remains `docs/roadmap/roadmap.md`.
- Each future PR still needs an explicit **human decision** before execution, and
  each still goes through the repo's normal spec/feature discipline.
- The **Integration Smoke Test is a prerequisite** — it was prepared and is
  reviewed/merged as its **own** PR. This plan does **not** create or modify it.
- The purpose is **to avoid opening new broad feature work before proving the
  system is coherent on one KPI path**. A capability snapshot plus a single
  end-to-end proof is cheaper to verify and harder to drift from than a new
  feature tier.

A plan is a hypothesis about the safest order; it is not permission to build.

## 2. Prerequisite

**Before executing this plan, the separate Integration Smoke Test PR must be
merged.**

- **Expected prerequisite artifact:** `docs/quality/top-idea-bank-integration-smoke-test.md`
- **Expected prerequisite result:** the smoke test result is **PASS** — or any
  **BLOCKED** items it raises are resolved before continuing.

This plan does **not** create or modify that file. If the smoke test is not yet
merged (or is BLOCKED with unresolved items), **stop** — do not start NEXT PROMPT 1.

## 3. Current Baseline

| Capability | Source PR | Current role |
|------------|-----------|--------------|
| Route registry manifest | #62 | Route integrity / machine-checkable navigation (`routes.yaml` + static rule A1) |
| Structured findings output | #63 | Optional structured observability (`seshat check --format json`; default text unchanged) |
| Never-execute guard | #64 | Protects the no-execution invariant (rule B1; module-scope DB/network imports blocked) |
| KPI decision-question index | #65 | Business-question navigation into KPI domains |
| KPI coverage scorecard | #66 | Analytical coverage expressed as statuses/blockers (never a score) |
| Integration smoke test | #68 (separate follow-up PR) | Verifies #62–#66 work together and align with governance |

These are merged or prerequisite capabilities. The next phase should turn the
stabilized system into a clear **capability snapshot** and **one end-to-end
proof**, not a new feature tier.

## 4. Recommended Next-Phase Sequence

Order:

1. Post-Idea-Bank capability state report
2. Net Sales end-to-end readiness trace
3. Big Data Analytics capability report
4. Data volume / large-source assessment templates

| Order | Future PR title | Type | Why now | Must not do |
|-------|-----------------|------|---------|-------------|
| 1 | `docs: add post-idea-bank capability state report` | Docs (snapshot) | After the smoke test, capture a stable snapshot so the repo is navigable and future work does not drift | Claim runtime/live validation that does not exist; grant readiness; add features |
| 2 | `docs: add Net Sales end-to-end readiness trace` | Docs (demo/trace) | Prove the system on one KPI path before adding broader capabilities | Invent source data; claim live validation; write new SQL/DAX; grant readiness; bypass contracts |
| 3 | `docs: add big data analytics capability report` | Docs (strategy) | Define scale boundaries — only after the core proves coherence on one KPI | Create a Big Data skill; add runtime tooling/dependencies; create templates/checklists |
| 4 | `docs: add data volume assessment templates` | Docs (templates/checklists) | Make scale assessment repeatable — only after the report defines boundaries | Add runtime code/deps; add a Python performance slice; add distributed/lakehouse platform guidance beyond assessment language |

## 5. Phase Logic

### Step 1 — Capability State Report

**Goal:** Summarize what Seshat BI can do now, what remains planned, what is
explicitly forbidden, and what requires real data or a human ruling.

**Why first:** After the integration smoke test confirms #62–#66 cohere, a stable
snapshot makes the repo easier to navigate and keeps future work from drifting —
it is the cheapest way to establish "where we actually are" before any new proof.

**Expected artifact:** `docs/quality/post-idea-bank-capability-state.md`

### Step 2 — Net Sales End-to-End Readiness Trace

**Goal:** Prove the system on one KPI path, end to end:
business question → KPI contract → required fields → source/table coverage →
blockers → SQL/gold expectation → DAX/semantic readiness → dashboard usage →
readiness gates.

**Why second:** The project needs a single, honest end-to-end proof — that the
layers actually hand off to each other on one real KPI — **before** adding broader
scale capabilities. Net Sales is the right choice: it is the base contract most
other KPIs derive from, and it already has a seeded metric contract.

**Expected artifact:** `docs/demo/net-sales-end-to-end-readiness-trace.md`

### Step 3 — Big Data Analytics Capability Report

**Goal:** Add a **strategy-only** report for how Big Data / scale should fit
Seshat BI — what scale conditions would justify new capability, and what the
boundaries are.

**Why third:** Scale matters, but it must come **after** the core system proves
coherence on one KPI path. Defining the strategy before there is proven need
prevents premature tooling adoption.

**Expected artifact:** `docs/big-data/big-data-capability-report.md`

### Step 4 — Data Volume Assessment Templates

**Goal:** Add templates/checklists for assessing real source volume and
large-source risk, so scale decisions are evidence-based and repeatable.

**Why fourth:** Only **after** the Big Data capability report defines the
boundaries should templates exist — templates without a boundary definition would
encode assumptions the report has not yet justified.

**Expected artifacts:**

- `docs/big-data/data-volume-assessment.md`
- `templates/data-volume-profile.md`
- `templates/large-source-profile.md`
- `checklists/large-source-review-checklist.md`

## 6. PR Plan

Each subsection scopes a *future* PR. None is executed in this document.

### PR 1 — docs: add post-idea-bank capability state report

- **Allowed file:** `docs/quality/post-idea-bank-capability-state.md`
- **Must summarize:**
  - What works now
  - What is planned/deferred
  - What is explicitly forbidden
  - What requires human ruling
  - What requires real data
  - What each knowledge layer owns
  - What each knowledge layer must not own
  - What the next proof should focus on
- **Must include:**
  - A capability table by layer: Route/gate integrity · Structured findings ·
    Never-execute guard · SQL knowledge · DAX knowledge · Python knowledge ·
    Retail KPI knowledge · Readiness spine · Dashboard / Power BI boundary
  - Known limitations
  - Recommended next proof: the Net Sales end-to-end trace
- **Must not:**
  - Claim runtime execution exists if it does not
  - Claim readiness approval
  - Claim live validation unless actually verified
  - Add new features

### PR 2 — docs: add Net Sales end-to-end readiness trace

- **Allowed file:** `docs/demo/net-sales-end-to-end-readiness-trace.md`
- **Must trace:** Business question · Net Sales KPI contract · Required fields ·
  Source/table coverage · Blockers · SQL/gold expectation · DAX/semantic
  readiness · Dashboard usage · Readiness gates · What is proven · What is not
  proven · What needs human ruling · What needs real data
- **Must not:**
  - Invent source data
  - Claim live validation if not performed
  - Write SQL/DAX implementation unless already present and cited
  - Grant readiness
  - Bypass KPI contracts
  - Bypass semantic model readiness
  - Treat dashboard usage as publish approval

### PR 3 — docs: add big data analytics capability report

- **Allowed file:** `docs/big-data/big-data-capability-report.md`
- **Must state:**
  - Big Data is a **scale/latency condition, not a tool to install**.
  - Do not create a Big Data skill now.
  - Do not add runtime big data tooling now.
  - Extend Python **later** only for single-machine large-file analysis.
  - Create `analytics-scale-knowledge` **only later** if distributed / lakehouse /
    streaming needs are proven.
  - No Spark / Fabric / Databricks / Snowflake / BigQuery adoption before evidence.
  - Power BI remains an **adapter, not the product**.
  - Scale decisions must preserve Source → Mapping → Silver → Gold → Semantic
    Model → Dashboard → Publish.
- **Must not:**
  - Create templates/checklists in this PR
  - Add dependencies
  - Add code
  - Add execution adapters
  - Claim implementation

### PR 4 — docs: add data volume assessment templates

- **Allowed files:**
  - `docs/big-data/data-volume-assessment.md`
  - `templates/data-volume-profile.md`
  - `templates/large-source-profile.md`
  - `checklists/large-source-review-checklist.md`
- **Must produce:**
  - A repeatable source volume profile
  - A large-source profile
  - A large-source review checklist
  - A verdict vocabulary such as: `LOCAL_OK` · `WAREHOUSE_RECOMMENDED` ·
    `SCALE_REVIEW_REQUIRED` · `BLOCKED`
- **Must not:**
  - Add runtime code
  - Add dependencies
  - Add a Python performance slice yet
  - Add distributed/lakehouse platform guidance beyond assessment language
  - Create `analytics-scale-knowledge`
  - Claim Big Data support has been implemented

## 7. Cross-Phase Risks

| Risk | Affected phase | Why it matters | Mitigation |
|------|----------------|----------------|------------|
| Continuing before the integration smoke test is merged | all | The plan's premise (coherent #62–#66) is unproven until the smoke test passes | Treat the smoke test as a hard prerequisite (§2); do not start PR 1 until it is merged / unblocked |
| Opening new feature work before stabilization | all | New breadth before a snapshot + one proof invites drift and rework | Sequence is snapshot → one-KPI proof → scale strategy → templates; one PR per step |
| Turning the Idea Bank into a roadmap | all | Selection/planning could read as "approved to build" | Restate everywhere: planning only; human decision + spec process required per PR |
| Claiming readiness from coverage | 1, 2 | Coverage/snapshot signals could be mistaken for "ready to ship" | No PR advances a stage or grants a gate; readiness stays human-gated |
| Treating capability reports as implementation | 1, 3 | A report could be read as the capability itself | Reports describe state/strategy only; they add no runtime behaviour |
| Inventing evidence | 1, 2 | Fabricated facts corrupt the snapshot and the trace | If something can't be verified from the repo, mark it "not verified"; never invent |
| Jumping to Big Data tooling too early | 3, 4 | Premature Spark/Fabric/etc. adoption adds cost and lock-in with no proven need | Big Data stays report/template-only; no tooling/deps before evidence |
| Mixing KPI meaning with DAX/SQL/Python implementation | 2 | Recreates the multi-owner conflict the layers were designed to avoid | The trace cites `retail-kpi-knowledge` as the meaning owner; implementation layers consume a ready contract |
| Letting dashboard/publish bypass readiness | 2 | A trace that "shows a dashboard" could imply publish approval | The trace treats dashboard usage as a step gated on contracts + semantic-model readiness, never as approval |
| Adding templates before the report defines boundaries | 4 | Templates would encode unjustified assumptions | PR 4 is gated on PR 3 (the report defines the boundaries first) |
| Creating fake scores/confidence | 1, 4 | A made-up number contradicts "status + evidence + blockers" | Use statuses/blockers and an explicit verdict vocabulary; no numeric confidence |
| Treating the Net Sales trace as live validation | 2 | A trace is a paper proof, not a DB run | The trace explicitly states what is proven on paper vs what needs real data / a live run |

## 8. Validation Matrix

| Validation check | Applies to | Expected result |
|------------------|------------|-----------------|
| Exactly one file changed in this planning PR | this PR | Only `docs/planning/post-integration-stabilization-plan.md` |
| No implementation files changed | this PR | No `src/`, `tests/`, routes, KPI, readiness, CI changes |
| Each future PR is separately scoped | 1–4 | One artifact family per PR, explicit allowed/forbidden files |
| Integration smoke test is prerequisite, not duplicated | all | Referenced as a merged prerequisite; not created/edited here |
| Capability report comes before Net Sales trace | 1 → 2 | PR 2 gated on PR 1 merged |
| Net Sales trace comes before Big Data work | 2 → 3 | PR 3 gated on PR 2 merged |
| Big Data report comes before data volume templates | 3 → 4 | PR 4 gated on PR 3 merged |
| No runtime behavior is added | 1–4 | All four are docs/templates/checklists only |
| No readiness approval is granted | 1–4 | No stage advanced; no gate granted |
| No Power BI execution is added | 1–4 | F016 stays gated/deferred; Power BI remains an adapter |
| No fake score/confidence is introduced | 1, 4 | Statuses/blockers + verdict vocabulary only |
| Big Data remains report/template-only | 3, 4 | No tooling, dependencies, code, or execution adapters |

## 9. Implementation Prompt Pack

Four copy-ready prompts. **Text only — do not execute any of these in this PR.**
Each is gated on the prior step; run only after its gate condition is met and the
plan is approved.

### NEXT PROMPT 1 — Capability State Report — DO NOT RUN UNTIL INTEGRATION SMOKE TEST IS MERGED

- **Mission:** Produce a single capability-state snapshot of Seshat BI after the
  Idea Bank sequence + integration smoke test: what works now, what is planned/
  deferred, what is forbidden, what needs human ruling, what needs real data, and
  what each knowledge layer owns / must not own. Recommend the Net Sales trace as
  the next proof.
- **Branch name:** `docs/post-idea-bank-capability-state`
- **PR title:** `docs: add post-idea-bank capability state report`
- **Commit message:** `docs: add post-idea-bank capability state report`
- **Allowed files:** `docs/quality/post-idea-bank-capability-state.md` (one new file).
- **Forbidden files:** `src/`, `tests/`, `routes.yaml` / route registry, CLI,
  rules, KPI contracts/domains/templates, readiness templates, dependencies,
  GitHub Actions, the integration smoke test file, any other doc.
- **Implementation constraints:** Snapshot only — describe state, do not change it.
  Include a capability table by layer (route/gate integrity, structured findings,
  never-execute guard, SQL, DAX, Python, Retail KPI, readiness spine, dashboard/
  Power BI boundary). Verify each claim against the repo; if unverifiable, label it
  "not verified." Do not claim runtime execution, live validation, or readiness
  that does not exist.
- **Validation checks:** exactly one new file at the allowed path; no implementation
  files touched; every capability claim cites a real file or is marked unverified;
  no readiness/approval claimed.
- **Acceptance criteria:** the report lists works-now / planned / forbidden /
  needs-ruling / needs-data, the per-layer owns/must-not-own split, known
  limitations, and recommends the Net Sales end-to-end trace as the next proof.
- **Stop rules:** if a capability cannot be confirmed from the repo, mark it
  unverified — do not assert it. Do not add features. Do not edit the smoke test.
- **PR body template:** `## Summary` (what the snapshot captures) · `## Scope`
  (one capability-state doc) · `## Validation` (commands/inspection actually run;
  no unverified CI claim) · `## Boundaries preserved` (no code; no readiness
  granted; no live validation claimed).

### NEXT PROMPT 2 — Net Sales End-to-End Trace — DO NOT RUN UNTIL PROMPT 1 IS MERGED

- **Mission:** Produce a paper end-to-end readiness trace for the **Net Sales** KPI:
  business question → KPI contract → required fields → source/table coverage →
  blockers → SQL/gold expectation → DAX/semantic readiness → dashboard usage →
  readiness gates, with explicit "proven / not proven / needs human ruling / needs
  real data" sections.
- **Branch name:** `docs/net-sales-end-to-end-readiness-trace`
- **PR title:** `docs: add Net Sales end-to-end readiness trace`
- **Commit message:** `docs: add Net Sales end-to-end readiness trace`
- **Allowed files:** `docs/demo/net-sales-end-to-end-readiness-trace.md` (one new file).
- **Forbidden files:** `src/`, `tests/`, routes, CLI, rules, KPI contracts/domains/
  templates, readiness templates, dependencies, GitHub Actions, the smoke test, any
  other doc.
- **Implementation constraints:** Cite the existing `net-sales` metric contract and
  the existing readiness/SQL/DAX docs; do not invent source data; do not write new
  SQL/DAX (only cite implementation that already exists). Mark every step as proven
  on paper vs needing a live run / real data. KPI meaning stays owned by
  `retail-kpi-knowledge`; implementation layers consume the ready contract.
- **Validation checks:** exactly one new file at the allowed path; no
  implementation files touched; the trace cites real contract/required-field/
  readiness files; live validation is not claimed unless a real run is cited.
- **Acceptance criteria:** the trace walks the full path for Net Sales, names the
  blockers/open rulings, and clearly separates "proven on paper" from "needs real
  data / live validation"; it grants no readiness and treats dashboard usage as a
  gated step, not approval.
- **Stop rules:** if a step requires data or a run that has not happened, label it
  "not verified / needs real data" — do not fabricate a result. Do not grant
  readiness. Do not bypass the KPI contract or semantic-model readiness.
- **PR body template:** `## Summary` · `## Scope` (one Net Sales trace doc) ·
  `## Validation` (what was inspected; no unverified CI/live-run claim) ·
  `## Boundaries preserved` (no code; no live validation claimed; no readiness
  granted; contracts/semantic-model gates respected).

### NEXT PROMPT 3 — Big Data Capability Report — DO NOT RUN UNTIL PROMPT 2 IS MERGED

- **Mission:** Produce a strategy-only report on how Big Data / scale should fit
  Seshat BI: Big Data is a scale/latency condition (not a tool to install), what
  conditions would justify new capability later, and the boundaries that protect
  the medallion flow and the agent-first / no-execute principles.
- **Branch name:** `docs/big-data-capability-report`
- **PR title:** `docs: add big data analytics capability report`
- **Commit message:** `docs: add big data analytics capability report`
- **Allowed files:** `docs/big-data/big-data-capability-report.md` (one new file).
- **Forbidden files:** templates/checklists (those are PR 4), `src/`, `tests/`,
  routes, CLI, rules, KPI files, readiness templates, dependencies, GitHub Actions,
  the smoke test, any other doc.
- **Implementation constraints:** Strategy text only. State explicitly: do not
  create a Big Data skill now; do not add runtime tooling now; extend Python later
  only for single-machine large-file analysis; create `analytics-scale-knowledge`
  only later if distributed/lakehouse/streaming needs are proven; no Spark/Fabric/
  Databricks/Snowflake/BigQuery adoption before evidence; Power BI remains an
  adapter; preserve Source → … → Publish. Add no dependencies, code, or adapters.
- **Validation checks:** exactly one new file at the allowed path; no templates/
  checklists created; no code/deps/adapters; no implementation claimed.
- **Acceptance criteria:** the report frames Big Data as a condition, names the
  proof thresholds that would justify capability later, and states all the
  boundaries above; it creates no tooling and no templates.
- **Stop rules:** if tempted to add a template, a dependency, or a platform choice,
  stop — this PR is strategy text only. Defer templates to PR 4.
- **PR body template:** `## Summary` · `## Scope` (one strategy report) ·
  `## Validation` (what was inspected; no unverified CI claim) · `## Boundaries
  preserved` (no tooling/deps/code; report-only; Power BI stays an adapter;
  medallion flow preserved).

### NEXT PROMPT 4 — Data Volume Templates — DO NOT RUN UNTIL PROMPT 3 IS MERGED

- **Mission:** Add repeatable data-volume / large-source assessment artifacts that
  apply the boundaries the PR 3 report defined: a source volume profile, a
  large-source profile, a large-source review checklist, and an explicit verdict
  vocabulary — all assessment language only, no tooling.
- **Branch name:** `docs/data-volume-assessment-templates`
- **PR title:** `docs: add data volume assessment templates`
- **Commit message:** `docs: add data volume assessment templates`
- **Allowed files:** `docs/big-data/data-volume-assessment.md`,
  `templates/data-volume-profile.md`, `templates/large-source-profile.md`,
  `checklists/large-source-review-checklist.md`.
- **Forbidden files:** `src/`, `tests/`, routes, CLI, rules, KPI contracts/domains/
  templates, readiness templates, dependencies, GitHub Actions, the smoke test, a
  Python performance slice, `analytics-scale-knowledge`, any other doc.
- **Implementation constraints:** Templates/checklists only. Provide a repeatable
  volume profile, a large-source profile, and a review checklist with the verdict
  vocabulary `LOCAL_OK` / `WAREHOUSE_RECOMMENDED` / `SCALE_REVIEW_REQUIRED` /
  `BLOCKED`. No runtime code, no dependencies, no Python performance slice, no
  distributed/lakehouse platform guidance beyond assessment language, no
  `analytics-scale-knowledge`. Do not claim Big Data support is implemented.
- **Validation checks:** exactly the four allowed files; no code/deps; verdicts use
  the defined vocabulary (no numeric confidence); no implementation claimed.
- **Acceptance criteria:** the four artifacts exist, the checklist yields one of the
  four verdicts from explicit evidence/blockers, and nothing implies Big Data has
  been implemented or that scale tooling was adopted.
- **Stop rules:** if tempted to add a dependency, a platform choice, or a Python
  performance change, stop — assessment language only. Do not create
  `analytics-scale-knowledge`.
- **PR body template:** `## Summary` · `## Scope` (volume/large-source templates +
  checklist) · `## Validation` (what was inspected; no unverified CI claim) ·
  `## Boundaries preserved` (assessment-only; no tooling/deps; no Big Data
  implementation claimed; verdicts are statuses, not scores).

## 10. Final Recommended Sequence

| Order | Work | Purpose | Why before next |
|-------|------|---------|-----------------|
| 1 | Capability State Report | Summarize current system state | A stable snapshot grounds the proof and keeps later work from drifting |
| 2 | Net Sales End-to-End Trace | Prove one KPI path | One honest end-to-end proof must exist before adding scale breadth |
| 3 | Big Data Capability Report | Define scale boundaries | Strategy must be defined before any scale templates encode assumptions |
| 4 | Data Volume Templates | Make scale assessment repeatable | Templates apply boundaries the report defines; they cannot precede it |

## 11. Final Verdict

**Planning result: PASS**

This result is PASS because, for this PR:

- exactly one planning file is changed
  (`docs/planning/post-integration-stabilization-plan.md`);
- no implementation is included (none of the four items is built);
- all four future PRs are separately scoped with explicit allowed/forbidden files;
- the implementation prompts are gated (each waits for the prior to merge, and
  PR 1 waits for the integration smoke test);
- the integration smoke test is treated as a **prerequisite**, not duplicated or
  edited;
- hard project boundaries are preserved (agent-first; medallion stage order; KPI
  meaning vs implementation; no execution; no self-granted approval; readiness =
  status + evidence + blockers; coverage is status/blocker not score);
- Big Data work remains **report/template-only** (no tooling, dependencies, code,
  or execution adapters before proven need);
- the Net Sales trace does **not** claim live validation unless actually supported
  (it separates "proven on paper" from "needs real data / a live run").

It would be **BLOCKED** if any of these were true: more than one file changed;
implementation accidentally included; source/tests/KPI/readiness files edited;
prompts encouraged scope mixing; the plan suggested Big Data runtime/platform
adoption too early; the plan granted readiness or publish status; or the plan
duplicated the integration smoke test work.
