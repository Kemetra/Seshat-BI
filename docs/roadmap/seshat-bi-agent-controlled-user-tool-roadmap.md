## Seshat BI — Agent-Controlled User Tool Roadmap

**Status:** **Draft / Proposed — direction ratified, delivery in progress.** The core
product-direction fork (A-vs-B, see the ✅ callout below) was **ratified B by Ahmed
Shaaban (owner) 2026-07-07**. M1/M2 are built; M3/M11 and M4/M6/M7/M9/M10 are specced
(the latter under B). This remains a forward-looking roadmap, NOT part of the delivered
ledger: individual milestones still land through the normal spec → build → gate path,
and net-new runtime / CI pieces are spec-and-held for review rather than auto-built
(Principle V — `never_self_grant_approval`; the agent records owner-directed rulings,
never self-grants). The authoritative delivered ledger remains
`docs/roadmap/roadmap.md` (F-numbered rows + commit refs) and
`docs/roadmap/shipped-ideas.yaml`.
**Repository:** `Kemetra/Seshat-BI`
**Target direction:** Turn Seshat BI into an installable, agent-controlled Retail BI readiness tool for other BI users and teams.

> **Reconciliation note (2026-07-07 — git-wins-on-ship-status).** This draft's
> §2 "Current State" is accurate on the facts it checks but **under-scoped**: it
> stops at the original F005–F016 sequence and does not mention the shipped
> **Companion / adapter tier (F024–F039)** — readiness-viewer, pr-readiness-reviewer,
> approval-console, evidence-pack-generator, dbt/dagster adapters,
> approval-evidence-pack, cross-table-lineage, consumer-data-dictionary,
> a11y-rtl-readiness-checklist (all live under `.claude/skills/`) — nor the
> idea-bank waves that grew the static `seshat check` gate from 27 to **56
> registered rules** (67 manifest entries). Because several capabilities this
> draft frames as "new" (see M4/M5/M6/M7/M9) already ship **as agent skills**,
> read those milestones as *"add a CLI-verb wrapper / packaging story over an
> existing skill"*, NOT as net-new capability. Verify each milestone against
> `shipped-ideas.yaml` + `.claude/skills/` before speccing it.

> **✅ RATIFIED: Option B (skill-driven packaging) — Ahmed Shaaban (owner) 2026-07-07.**
> The product-direction fork below (does *"installable, agent-controlled tool"* mean
> **(A)** more CLI verbs, or **(B)** an install/packaging story over the existing skills
> while staying skill-driven?) is decided: **B**. Hard rule #1 holds — the agent+skills
> stay the interface; the CLI stays a narrow gate, with the one deliberate addition being
> a small machine-readable `status --format json` surface (M4's schema part), NOT a broad
> verb surface. So M4/M6/M7/M9/M10 below are delivered as packaging/discovery over shipped
> skills — read every "new CLI verb" in those milestones as "packaging over an existing
> skill." Full decision + rationale: `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.
> Specced under B in specs 109–113. (M1/M2/M3/M11 never depended on this ruling.)

---

## 1. Product North Star

Seshat BI should become:

> **An agent-controlled Retail BI readiness tool that helps users move from messy retail data to trusted Power BI delivery through evidence-based gates, source profiling, mapping governance, medallion warehouse validation, metric contracts, semantic checks, and PBIP-ready handoff.**

The final user experience should feel like this:

```text
User installs Seshat BI
→ starts a new BI workspace
→ connects or provides a retail source
→ the agent profiles the source
→ the agent drafts mapping evidence
→ the user approves business meaning / grain / PII decisions
→ Seshat gates silver/gold work
→ live validation proves the warehouse
→ metric contracts define KPIs
→ semantic checks protect Power BI meaning
→ dashboard design and PBIP handoff happen last
→ publish/execution stays gated until semantic readiness and human approval
```

This is consistent with the repo’s existing positioning: README already defines Seshat BI as an **agent-first Retail BI readiness system** that profiles the source, maps meaning, builds the medallion warehouse, validates it, defines metrics, prepares the semantic model, designs the dashboard, and only then publishes.

---

## 2. Current State — What Already Exists

This roadmap must not restart from zero. The repo has already shipped a serious foundation.

### 2.1 Product identity and philosophy

The product name is already **Seshat BI**, with `Seshat_BI` as the CLI/package alias in the README.

The core philosophy is already defined: readiness is not a fake confidence score; it is `status` + `evidence` + `blocking_reasons`.

### 2.2 Readiness spine already exists

The seven readiness stages already exist:

```text
Source Ready
→ Mapping Ready
→ Silver Ready
→ Gold Ready
→ Semantic Model Ready
→ Dashboard Ready
→ Publish Ready
```

The README states that each stage is a gate and must not be entered before the prior one passes.

### 2.3 CLI package already exists

The package currently ships as Python project name `retail`, version `0.1.0`, with the console script:

```toml
[project.scripts]
retail = "retail.cli:main"
```

### 2.4 Core command surfaces already exist

The current CLI already includes:

```text
seshat check
retail validate
retail semantic-check
retail value-check
retail generate
```

These are not theoretical; they are implemented in the `src/seshat/cli/` package (a dispatch table + per-command handlers under `src/seshat/cli/commands/`; the former single-file `cli.py` was split for maintainability). `check` supports `--format json`, `validate` supports DSN/source-map live checks, `semantic-check` checks contract↔DAX drift, `value-check` recomputes approved values live, and `generate` creates verified DAX from metric contracts. A read-only `status --format json` surface (spec 109) has since been added.

### 2.5 Power BI / PBIR helper surface already exists

The CLI already includes Power BI helper commands:

```text
retail theme-gen
retail theme-compile
retail pbir-apply-theme
retail pbir-format-visual
retail pbir-set-page-background
retail pbir-set-geometry
```

These commands are local PBIR/file writers, not live Power BI publishers.

The recent PBIR geometry work deliberately preserves data binding and refuses unsafe layout moves; it writes position only for an existing visual and does not change `visualType`, create/delete visuals, or move unbound visuals.

### 2.6 Agent-first substrate already exists

The CLI already includes:

```text
retail init
retail kit-lint
retail doctor
retail demo init/load/run/report
```

`retail init` bootstraps the Compass-driven kit substrate and writes `.seshat/` plus fenced `AGENTS.md` / `CLAUDE.md` regions. The `demo` verb group already exists for proving the readiness spine on a generic sample.

### 2.7 Agent operating contract already exists

`AGENTS.md` already states that Seshat BI is **agent-first**: the agent is the interface, while CLI gates like `seshat check` and `retail validate` are helpers the agent calls.

It also defines hard stops:

* no silver when mapping is blocked,
* no Power BI before validation,
* no dashboards before metric contracts,
* no Power BI execution adapter yet,
* no self-granted approvals.

### 2.8 Demo path already exists

There is already a `retail_store_sales` demo guide that walks a generic retail store-sales source through the readiness spine, including source profile, source map, metrics, reconciliation evidence, dashboard design, handoff pack, and readiness status.

The demo explicitly proves three core rules: source mapping before silver, metric contracts before dashboard, and validation before Power BI.

### 2.9 Roadmap says the original foundation is shipped

The roadmap says the original F005–F015 sequence, including F011A, is shipped to `main`; the only original parked feature is F016, the Power BI execution adapter, deliberately last and gated.

---

## 3. What We Must Not Repeat

The next roadmap must avoid rebuilding existing shipped surfaces.

| Already shipped / present          | Do not repeat                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------------- |
| Seven-stage readiness spine        | Do not create a second readiness model                                                |
| `seshat check`                     | Do not create a duplicate static gate                                                 |
| `retail validate`                  | Do not create a second validation CLI                                                 |
| `semantic-check` / `value-check`   | Do not create another metric drift/value checker                                      |
| DAX generator                      | Do not create another measure generator before improving contracts                    |
| PBIR theme/format/geometry helpers | Do not rebuild Power BI helpers from scratch                                          |
| `retail init` kit substrate        | Do not replace it; build a user-workspace layer around it                             |
| `retail demo` harness              | Do not create a separate demo system; productize it                                   |
| Agent rules in `AGENTS.md`         | Do not create conflicting agent rules elsewhere                                       |
| F016 Power BI execution adapter    | Do not start it until semantic-model readiness and human approval gates are satisfied |

---

## 4. Strategic Product Gap

The repo is strong as a governed BI kit, but the product gap is:

> **A new external user still needs a clear install → workspace → agent-run → evidence-output path.**

Today, the repo contains the foundation and many commands. The next product phase should make Seshat BI feel like a downloadable tool that another BI user can actually adopt.

The gap is not “more rules.”
The gap is **productization**:

1. installable command identity,
2. workspace creation,
3. agent control protocol,
4. first-hour onboarding,
5. demo-to-real-source path,
6. shareable BI evidence output,
7. clear Power BI delivery boundary.

---

## 5. Target End-State

A future user should be able to do something like:

```bash
pipx install seshat-bi
seshat init-project my-retail-bi
cd my-retail-bi
seshat doctor
seshat demo init
seshat demo run
seshat demo report --format json
```

Then, for real work:

```bash
seshat source profile --input sales.csv --table retail_sales
seshat check --format json
seshat validate --source-map mappings/retail_sales/source-map.yaml
seshat semantic-check
seshat value-check
seshat evidence-pack build --table retail_sales --stage dashboard_ready
```

The exact commands can change, but the product promise should not:

> **The user does not need to know the whole repo. The agent reads the readiness state and calls the next safe command.**

---

# 6. Roadmap Overview

## Milestone 0 — Product Direction Lock

**Goal:** Record the new product direction without changing runtime behavior.

**Why:** Before adding code, lock the goal: Seshat BI is no longer only a repo/kit; it is becoming an installable agent-controlled BI tool.

### Deliverables

* `docs/product/seshat-bi-product-direction.md`
* `docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md`
* `docs/product/user-journeys.md`

### Acceptance Criteria

* Defines the target external user:

  * BI developer,
  * data analyst,
  * retail ops analyst,
  * AI agent operator,
  * consultant delivering Power BI from messy retail sources.
* Defines non-goals:

  * not a one-click dashboard generator,
  * not a Fabric deployment platform,
  * not an ML/forecasting system,
  * not a universal ERP connector,
  * not a self-approval engine.
* Explicitly reuses existing shipped surfaces instead of replacing them.

### Scope Type

Docs-only.

### Do Not Touch

* `src/seshat/**`
* `pyproject.toml`
* tests
* Power BI files
* warehouse SQL

---

## Milestone 1 — Brand-Level CLI Surface

**Goal:** Make the installed command feel like Seshat BI, while preserving the existing `retail` command.

### Current Reality

The Python package currently exposes only:

```bash
retail
```

via `pyproject.toml`.

### Desired Direction

Add a brand alias:

```bash
seshat
```

while keeping:

```bash
retail
```

for backward compatibility.

### Proposed Behavior

```bash
seshat check
seshat validate
seshat semantic-check
seshat value-check
seshat generate
seshat init
seshat doctor
seshat demo report
```

Internally, `seshat` can point to the same `retail.cli:main` entrypoint.

### Deliverables

* Add `seshat = "retail.cli:main"` under `[project.scripts]`.
* Update README quickstart to prefer `seshat`, while documenting `retail` as a supported legacy/internal alias.
* Add tests or packaging smoke docs proving both commands resolve to the same CLI.

### Acceptance Criteria

* `retail --help` still works.
* `seshat --help` works.
* No command behavior changes.
* README uses Seshat as product-facing command.
* No breaking rename.

### Scope Type

Small packaging / docs slice.

### Risk

This touches `pyproject.toml`, so it should be an explicit approved slice.

---

## Milestone 2 — Installable User Experience

**Goal:** Make the repo usable as a tool by someone who is not developing the repo itself.

### Problem

The repo has installation instructions, but the experience is still developer-oriented:

```bash
git clone
pip install -e ".[dev]"
seshat check
```

The README currently documents editable dev install and `seshat check`.

### Desired Product Experience

Support a user-facing installation path:

```bash
pipx install seshat-bi
# or
pip install seshat-bi
```

The exact distribution name should be decided before publishing.

### Deliverables

* `docs/install/user-install.md`
* `docs/install/developer-install.md`
* `docs/install/agent-install.md`
* packaging smoke checklist
* optional `make`-free / shell-free install verification for Windows users

### Acceptance Criteria

* A user can understand:

  * how to install for normal use,
  * how to install for development,
  * how to install optional extras:

    * DB validation,
    * file profiling,
    * live tests.
* Docs explain extras already present:

  * `db`,
  * `mssql`,
  * `mysql`,
  * `snowflake`,
  * `files`,
  * `livetest`.
* No claim that the package is published until publication is actually done.

### Scope Type

Docs-first, then packaging.

---

## Milestone 3 — User Workspace Mode

**Goal:** Separate “the Seshat BI source repo” from “a BI project created by a user.”

### Current Reality

`retail init` already exists, but it is described as bootstrapping the kit substrate into a repo by writing `.seshat/` and fenced `AGENTS.md` / `CLAUDE.md` regions; it is not a full user project wizard.

### Desired Direction

Create a user workspace mode that can initialize a clean BI project folder.

Possible command:

```bash
seshat init-project my-retail-bi
```

or:

```bash
seshat workspace init my-retail-bi
```

### Generated Workspace Shape

```text
my-retail-bi/
  AGENTS.md
  CLAUDE.md
  .seshat/
    compass.yaml
    kit-source.yaml
  mappings/
  warehouse/
    bronze/
    silver/
    gold/
  powerbi/
  reports/
  evidence/
  templates/
  readiness-status.yaml
  README.md
```

### Important Boundary

This should reuse existing `retail init` substrate logic where possible. It should not create a parallel kit initializer.

### Deliverables

* Workspace template spec.
* Workspace initializer command.
* Golden fixture test for generated tree.
* Idempotency behavior:

  * first run creates,
  * second run reports already initialized,
  * no silent overwrite of user artifacts.

### Acceptance Criteria

* A clean folder can become a Seshat workspace.
* Existing project files are not overwritten silently.
* `.seshat` projection stays compatible with `kit-lint`.
* `seshat doctor` can run on the workspace.
* The generated `AGENTS.md` tells the agent to read readiness state and perform only the next allowed action.

### Scope Type

Runtime + tests.

---

## Milestone 4 — Agent Control Protocol

**Goal:** Give agents a stable contract for controlling Seshat safely.

### Current Reality

`AGENTS.md` already defines operating rules and lists agent-driven verbs.

The CLI already supports JSON output for `seshat check --format json`.

The demo report command also supports text/json output.

### Desired Direction

Create a formal **Agent Control Protocol** that standardizes:

* how an agent discovers current readiness,
* how it asks “what is the next allowed action?”,
* how it reports blockers,
* how it stops for approval,
* how it calls CLI gates,
* how it avoids self-granting readiness.

### Proposed New Commands

```bash
seshat status --format json
seshat next-action --format json
seshat blockers --format json
seshat doctor --format json
```

### Deliverables

* `docs/agent-control/protocol.md`
* `schemas/agent-status.schema.json`
* `schemas/next-action.schema.json`
* JSON output for `doctor`
* JSON output for readiness status rendering

### Acceptance Criteria

* Agent can parse status without scraping prose.
* Every output includes:

  * `current_stage`,
  * `status`,
  * `evidence`,
  * `blocking_reasons`,
  * `next_action`,
  * `requires_human_approval`.
* No output can mark a stage `pass` unless committed evidence already supports it.
* Human approval remains external and named.

### Scope Type

Small runtime + schemas + docs.

---

## Milestone 5 — First-Hour Experience

**Goal:** Make Seshat impressive and understandable in the first session.

### Current Reality

The repo already has a guided `retail_store_sales` demo path and a CLI `demo` group.

### Desired Direction

Turn the existing demo into a polished first-hour product experience.

### Proposed Flow

```bash
seshat demo init
seshat demo run
seshat demo report
seshat demo report --format json
```

Then show the user:

```text
What Seshat proved
What remains warning
What needs real data
What needs human approval
What the next allowed action is
```

### Deliverables

* `docs/demo/first-hour-demo.md`
* `docs/demo/demo-script-for-agent.md`
* `docs/demo/demo-script-for-human.md`
* Improved CLI messages for `demo report`
* Optional generated `evidence/demo-summary.md`

### Acceptance Criteria

* A user can understand Seshat without reading the whole repo.
* Demo does not claim live validation unless DSN exists.
* Demo preserves honest states like `warning`.
* Demo explains why this is not a fake green dashboard.

### Scope Type

Docs + small CLI polish.

---

## Milestone 6 — Source Onboarding v1

**Goal:** Let a user bring a real source into Seshat safely.

### Current Reality

Source Ready already supports DB tables and standalone files, including CSV/Excel, and the docs specify that file profiling uses `file_profile.py`; CSV uses stdlib and Excel uses the optional `files` extra.

The source stage requires a source profile before mapping and explicitly forbids writing source-map decisions or touching silver at this stage.

### Desired Direction

Productize source onboarding:

```bash
seshat source profile --table sales --dsn-env DATABASE_URL
seshat source profile-file --input sales.csv --table sales
seshat source profile-file --input sales.xlsx --sheet Sheet1 --table sales
```

### Deliverables

* Friendly CLI around existing profiling logic.
* Output path convention:

  * `mappings/<table>/source-profile.md`
* JSON summary option:

  * row count,
  * column count,
  * missingness,
  * candidate keys,
  * proposed semantics,
  * pending owner decisions.
* Agent instructions for what to do next.

### Acceptance Criteria

* No source-map is authored during Source Ready.
* File encoding/delimiter/header are marked `[PROPOSED]` until owner confirmation.
* No fabricated profile numbers when a DB/file reader is unavailable.
* If live boundary is unavailable, output is `warning` / `[PENDING LIVE PROFILE]`, not `pass`.

### Scope Type

Runtime + tests + docs.

---

## Milestone 7 — Mapping Review UX

**Goal:** Make the mapping gate easier for real users to approve.

### Current Problem

Mapping governance exists, but external users need a clear review artifact.

### Desired Direction

Create a user-friendly mapping review pack:

```bash
seshat mapping review --table sales
```

Outputs:

```text
mappings/sales/mapping-review.md
```

The review pack should summarize:

* grain,
* primary key candidates,
* date columns,
* PII columns,
* retail business meaning,
* unresolved questions,
* approval slots.

### Deliverables

* `templates/mapping-review.md`
* `seshat mapping review`
* mapping review JSON summary
* tests for no auto-approval

### Acceptance Criteria

* Agent can draft a review pack.
* Human must approve.
* Seshat cannot move Mapping Ready to `pass` by itself.
* Review pack cites source profile and source-map evidence.

### Scope Type

Artifact-writing Product Module.

---

## Milestone 8 — Workspace Doctor and Repair Guidance

**Goal:** Help new users understand what is missing without reading all docs.

### Current Reality

`doctor` already exists as a read-only repo-wide drift digest and can be strict or advisory.

### Desired Direction

Make `doctor` user-facing and agent-friendly.

### Proposed Command

```bash
seshat doctor
seshat doctor --format json
seshat doctor --strict
```

### Desired Output

```text
Workspace health:
- kit projection: ok
- readiness status: missing
- source profile: missing
- mapping gate: not started
- check gate: ok / failed
- live validation: deferred
- next allowed action: source profile
```

### Deliverables

* JSON output.
* More human-readable grouping.
* “repair hints” that do not modify files.
* Agent-safe stop instructions.

### Acceptance Criteria

* `doctor` remains read-only.
* `--strict` fails on real findings.
* Default mode remains advisory.
* Output includes next safe action.

### Scope Type

Runtime polish.

---

## Milestone 9 — Evidence Pack as Product Output

**Goal:** Make Seshat produce something a BI team/client can actually review.

### Current Reality

The roadmap says Evidence Pack Generator and Approval Evidence Pack are already shipped as companion/product modules, with artifact-writing behavior and no self-approval.

### Desired Direction

Make evidence output a first-class product experience.

### Proposed Commands

```bash
seshat evidence build --table sales --stage source_ready
seshat evidence build --table sales --stage dashboard_ready
seshat evidence export --table sales --format markdown
seshat evidence export --table sales --format zip
```

### Evidence Pack Should Include

* current readiness stage,
* evidence files,
* blocking reasons,
* owner decisions needed,
* metric contracts,
* validation results,
* dashboard design trace,
* publish warning if F016 is absent/gated.

### Acceptance Criteria

* Evidence pack never grants approval.
* Empty approval slots remain empty.
* Pack cites committed artifacts only.
* Pack is useful to a human approver.

### Scope Type

Product module runtime or skill-to-CLI bridge.

---

## Milestone 10 — BI Delivery Layer

**Goal:** Turn Power BI delivery into a controlled handoff flow, not uncontrolled publishing.

### Current Reality

Power BI policy says Power BI is the reporting target, not the source of truth; it reads from `gold` only, every measure traces to a metric contract, PBIP artifacts stay source-control friendly, and publishing automation is deferred until semantic-model readiness passes.

The roadmap says F016 remains the only original parked feature and is deliberately execution-only, gated, and last.

### Desired Direction

Create a user-facing BI delivery flow:

```bash
seshat pbi review
seshat pbi apply-theme
seshat pbi format-visual
seshat pbi set-geometry
seshat pbi handoff
```

But keep:

```bash
seshat pbi publish
```

out of scope until F016 gates are satisfied.

### Deliverables

* `docs/powerbi/delivery-boundary.md`
* `seshat pbi review`
* `seshat pbi handoff`
* clear message when user asks for publish too early

### Acceptance Criteria

* No Power BI publish before `semantic_model_ready: pass`.
* No dashboard design before metric contracts.
* No PBIP mutation outside allow-listed surfaces.
* No connection secrets committed.

### Scope Type

Runtime wrapper + docs.

---

## Milestone 11 — Distribution and Release Maturity

**Goal:** Prepare the tool to be downloadable by other users.

### Deliverables

* release checklist,
* changelog policy,
* versioning policy,
* install smoke test,
* package build workflow,
* signed release notes,
* docs site or GitHub Pages-ready documentation.

### Acceptance Criteria

* A release artifact can be built locally.
* User install docs match the actual package.
* `seshat --version` exists.
* `seshat doctor` runs after installation.
* No dev-only assumptions in user install path.

### Scope Type

Packaging + docs + CI.

### Approval Required

Any CI/release automation changes should be explicitly approved.

---

## Milestone 12 — Future: Power BI Execution Adapter

**Goal:** Add live Power BI execution only after the product can prove semantic readiness.

### Current Constraint

Roadmap hard rule #6 says there is no Power BI execution before semantic-model readiness; F016 is execution-only, last, and cannot define metrics, mappings, semantic logic, or dashboard design. 

### Future Direction

Only after the earlier milestones are stable:

```bash
seshat pbi publish
```

Possible backend:

* official Power BI MCP / connection,
* no `pbi-cli` preference unless re-approved,
* no publish without evidence pack,
* no publish without named approval,
* no publish with live validation missing.

### Acceptance Criteria

* F016 cannot create truth.
* F016 cannot define KPIs.
* F016 cannot approve semantic readiness.
* F016 only materializes an already-approved model/report.

### Scope Type

Gated execution adapter.

---

# 7. Recommended Execution Order

## Slice 1 — Product Direction Doc

**Branch**

```text
docs/seshat-product-direction
```

**Commit**

```text
docs: define Seshat BI user-tool direction
```

**Files**

```text
docs/product/seshat-bi-product-direction.md
docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md
```

**Why first**

Locks the direction without touching runtime.

---

## Slice 2 — CLI Brand Alias

**Branch**

```text
feat/seshat-cli-alias
```

**Commit**

```text
feat: add seshat CLI alias
```

**Files**

```text
pyproject.toml
README.md
tests/unit/...
```

**Why second**

Makes the product feel like Seshat BI, while preserving `retail`.

---

## Slice 3 — User Workspace Spec

**Branch**

```text
spec/user-workspace-init
```

**Commit**

```text
docs: specify user workspace initialization
```

**Files**

```text
specs/<next>-user-workspace-init/spec.md
specs/<next>-user-workspace-init/plan.md
specs/<next>-user-workspace-init/tasks.md
```

**Why third**

Prevents implementation drift before writing workspace code.

---

## Slice 4 — Workspace Init Runtime

**Branch**

```text
feat/user-workspace-init
```

**Commit**

```text
feat: initialize Seshat BI user workspaces
```

**Files**

```text
src/seshat/...
templates/workspace/...
tests/unit/...
```

**Why fourth**

This is the first real external-user feature.

---

## Slice 5 — Agent JSON Control Contract

**Branch**

```text
feat/agent-control-json
```

**Commit**

```text
feat: expose agent-readable readiness control output
```

**Files**

```text
docs/agent-control/protocol.md
schemas/...
src/seshat/...
tests/unit/...
```

**Why fifth**

Agents need stable JSON, not prose scraping.

---

## Slice 6 — First-Hour Demo Polish

**Branch**

```text
docs/first-hour-demo
```

**Commit**

```text
docs: add first-hour Seshat BI demo flow
```

**Files**

```text
docs/demo/first-hour-demo.md
docs/demo/demo-script-for-agent.md
docs/demo/demo-script-for-human.md
```

**Why sixth**

Makes the project presentable to other BI users immediately.

---

## Slice 7 — Source Onboarding Productization

**Branch**

```text
feat/source-onboarding-cli
```

**Commit**

```text
feat: add user-facing source onboarding commands
```

**Files**

```text
src/seshat/...
docs/readiness/source-ready.md
tests/unit/...
```

**Why seventh**

This turns the tool from demo-only into real project intake.

---

## Slice 8 — Evidence Pack Export

**Branch**

```text
feat/evidence-pack-export
```

**Commit**

```text
feat: export readiness evidence packs
```

**Files**

```text
src/seshat/...
templates/...
tests/unit/...
```

**Why eighth**

This creates the professional output users can send to managers/clients.

---

# 8. Product Rules Going Forward

These must stay non-negotiable:

1. **Agent-first, not CLI-first.** The CLI is what the agent calls; the product experience is the guided agent workflow. This is already a hard roadmap rule. 
2. **No source directly to silver.**
3. **No silver without profile + source map + grain + reviewed questions.**
4. **No gold to Power BI before validation.**
5. **No dashboard before metric contracts.**
6. **No Power BI execution before semantic-model readiness.**
7. **No self-granted approval.**
8. **No fake confidence score.**
9. **Docs/templates/checklists before automation.**
10. **Every new feature must improve one readiness stage or one user-adoption layer.**

Rules 2–9 are already consistent with the roadmap hard rules. 

---

# 9. Final Product Shape

When this roadmap is done, Seshat BI should look like this to users:

```text
Seshat BI
├── installable CLI
│   ├── seshat
│   └── retail legacy alias
├── agent control protocol
│   ├── status
│   ├── next-action
│   ├── blockers
│   └── doctor
├── workspace initializer
│   ├── mappings/
│   ├── warehouse/
│   ├── powerbi/
│   ├── reports/
│   └── evidence/
├── readiness engine
│   ├── check
│   ├── validate
│   ├── semantic-check
│   └── value-check
├── source onboarding
│   ├── DB source profile
│   ├── CSV profile
│   └── Excel profile
├── metric and DAX governance
│   ├── metric contracts
│   ├── DAX generation
│   └── semantic drift checks
├── Power BI handoff
│   ├── theme
│   ├── formatting
│   ├── geometry
│   ├── handoff pack
│   └── publish gated for later
└── demo and evidence outputs
    ├── first-hour demo
    ├── readiness report
    └── approval evidence pack
```

---

# 10. Immediate Next Action

The next best action is **not code**.

The next best action is to create the docs-only direction slice:

```text
docs: define Seshat BI user-tool direction
```

With this file:

```text
docs/roadmap/seshat-bi-agent-controlled-user-tool-roadmap.md
```

and optionally:

```text
docs/product/seshat-bi-product-direction.md
```

After that, the first implementation slice should be:

```text
feat: add seshat CLI alias
```

Then:

```text
spec: user workspace initialization
```

This keeps the work professional, reviewable, and aligned with the repo’s existing governance.

---
