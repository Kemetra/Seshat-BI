# Feature Specification: Seshat BI Public Beta — Install to First Success

**Feature Branch**: `119-public-beta-install-first-success`

**Created**: 2026-07-11

**Status**: **RATIFIED by Ahmed Shaaban (owner), 2026-07-11.** Chain complete
(specify + clarify + plan + tasks + analyze; 0 critical/high, all 23 FRs + 8 SCs
task-covered). The owner cleared the Principle-V ratify seam by name; the agent records
this owner-directed decision, it did not self-ratify. **Approved to merge and implement.**
Implementation of the 31 tasks in `tasks.md` is a separate, deliberately-kicked-off piece
of work (MVP = User Story 1, first success on the distribution name; the `retail`→`seshat`
module rename is post-MVP Phase 5). Not yet implemented.

**Input**: User description: "Seshat BI Public Beta — Install to First Success. A completely new external user should be able to discover Seshat BI on GitHub, install it, create a fresh BI workspace, verify that the installation works, and start the Seshat-guided Claude Code workflow without understanding the internal source repository."

---

## Product goal

A completely new external user — someone who has never seen the Seshat BI source
repository — can discover Seshat BI, install it, create a fresh BI workspace, prove
the install works, and start the Seshat-guided Claude Code workflow. The first
successful experience requires **no database and no Power BI Desktop**; database
connectivity is an explicit, optional second step.

The intended shape of the experience:

```
install Seshat
  -> install or activate the Claude Code plugin
  -> create a BI workspace
  -> open Claude Code in that workspace
  -> ask Claude to use Seshat
  -> receive the truthful next allowed action
```

This spec **defines** that experience and the packaging transition beneath it. It
does not publish anything, does not implement, and stops at the ratify seam (see
"Boundary" and Non-goals).

---

## Clarifications

### Session 2026-07-11

- Q: FR-010 — how should the `retail` → `seshat` import-module rename avoid breaking the
  plugin's `python -m retail.cli` fallback? → A: **Option B** — retain a `retail`
  compatibility shim module so `python -m retail.cli` keeps resolving for one deprecation
  cycle (lower risk; preserves the original module; plugin fallback keeps working without
  lockstep mirror regeneration).
- Q: What is the required test scope for the macOS/Linux first-success path? → A: **Windows
  is the only gate-required smoke target**; macOS/Linux install steps are documented and
  covered by a **best-effort, non-blocking** CI job ("tested where practical").
- Q: FR-022 — what is the rollback mechanism when the *plugin* (not the package) is broken
  after release? → A: **Revert the generated one-way mirror** to the prior released
  tag/commit and re-issue a corrected version; if withdrawn, the truthful-status label
  **drops back to draft/beta** (symmetric with the package yank+revert).

---

## Boundary (what this spec is and is not)

- This is a **packaging + documentation + first-run experience** spec, delivered
  **under the ratified Option B (skill-driven packaging) decision**
  (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`, ratified by the owner
  2026-07-07). The agent + skills remain the product interface; the CLI stays the
  narrow gate it is today. **No broad replacement CLI verbs are added.**
- It is scoped to roadmap **M2 (Installable User Experience)** and completes M2's
  partially-shipped doc deliverables into a *tested* first-success experience. It
  **reuses** the release readiness built in spec 108 (versioning policy, changelog,
  install smoke test, CI smoke job) rather than rebuilding it.
- It **records an owner-directed naming decision** (2026-07-11): the tool's real name
  is Seshat, so the Python **distribution** publishes as `seshat-bi` (a safe,
  already-advertised, publish-time-verifiable name) and the **import module** migrates
  `retail` → `seshat` (a clean top-level brand import), while **both** `seshat` and
  `retail` console-script aliases are preserved. This is the "reviewed migration" the
  packaging rule's "preserve the existing Python module *unless a reviewed migration
  requires otherwise*" clause allows for.
- It makes **no claim** that PyPI or a public Claude Code marketplace is available.
  Publication is a separate, still-unmade owner act. Every user-facing status label
  is truthful (Alpha/Beta/Draft as applicable).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — New user reaches first success without a database (Priority: P1)

A new Windows user discovers Seshat BI, follows a short copy-pasteable quickstart,
installs the tool through a normal user-facing path (preferably `pipx`), confirms the
`seshat` command is available, creates a clean project with `seshat init-project`,
enters it, and runs a no-database verification (`seshat status --format json`,
`seshat next --format agent`, `seshat check`) — all succeeding without a database or
Power BI Desktop. The macOS/Linux path is documented and tested where practical.

**Why this priority**: This is the whole point — the shortest honest path from
"discovered it" to "it works." It is independent of the plugin and of the import-module
rename: it works through the `seshat` console script regardless of the internal package
name. It is the reviewable MVP; everything else builds on it.

**Independent Test**: In a clean environment (no repo clone, no dev deps, no DB driver),
install the published-style artifact, run `seshat --help`, `seshat init-project demo`,
`cd demo`, `git init`, `seshat status --format json`, `seshat next --format agent`,
`seshat check` — and confirm each exits as documented, in under 10 minutes on Windows.

**Acceptance Scenarios**:

1. **Given** a clean machine with Python and Git and no Seshat install, **When** the
   user follows the three-step quickstart, **Then** `seshat --help` succeeds and the
   user reaches a working command in under 10 minutes.
2. **Given** the tool is installed and no database is configured, **When** the user runs
   `seshat init-project <name>`, enters it, and runs `status --format json`,
   `next --format agent`, and `check`, **Then** each runs successfully, no step requires
   a database or Power BI Desktop, and `next` reports a truthful **Source Ready**
   onboarding action with **no fabricated readiness**.
3. **Given** the freshly created workspace, **When** the user runs `seshat check`,
   **Then** the workspace is governance-clean (exit 0) and no credentials are written to
   any tracked file.
4. **Given** Python, Git, the plugin, or the package install is missing or broken,
   **When** the user runs the first-run commands, **Then** the tool (or the quickstart's
   documented checks) returns an **actionable error** naming the missing prerequisite
   and how to resolve it — never a silent failure or a misleading success.

---

### User Story 2 — New user starts the Seshat-guided Claude Code workflow (Priority: P2)

After first success, the user installs or activates the public Seshat BI Claude Code
plugin using the simplest currently supported marketplace mechanism, opens Claude Code
in the workspace, and issues one instruction:

> Use Seshat BI for this project and perform only the next allowed action.

Claude Code loads the Seshat skill and commands, reads the recorded readiness state, and
returns the truthful next allowed action (a **Source Ready** onboarding action), with no
fabricated readiness and no database requirement.

**Why this priority**: This is the agent-first payoff and the product's actual
interface, but it depends on P1 having produced a working CLI and workspace first.

**Independent Test**: With P1 satisfied, install/activate the plugin per the documented
public flow, open Claude Code in the workspace, issue the one instruction, and confirm
the Seshat skill + `/seshat-*` commands load and the returned action is the truthful
Source Ready onboarding action.

**Acceptance Scenarios**:

1. **Given** first success is reached, **When** the user installs/activates the public
   plugin, **Then** the Seshat skill and the existing `/seshat-*` commands are exposed
   in Claude Code.
2. **Given** the plugin is active in the workspace, **When** the user asks Claude to use
   Seshat and perform only the next allowed action, **Then** Claude returns the truthful
   Source Ready onboarding action — not a fabricated pass, not a database prompt.
3. **Given** the user reads only the quickstart, **When** they reach first success and
   start the workflow, **Then** they did **not** need to read `AGENTS.md`, the
   constitution, the roadmap, or any internal spec first.

---

### User Story 3 — User connects a database as an explicit optional second step (Priority: P3)

Having reached first success, a user who wants live validation follows a clearly
separated "Connect your database" path: they install the appropriate optional extra
(`db` for PostgreSQL, or `mssql`/`mysql`/`snowflake`), provide a DSN via `.env`
(git-ignored, never a tracked file), and run the live checks. Normal first use never
installed these extras.

**Why this priority**: Valuable but deliberately downstream — the product's promise is
that the database is optional and later, so this must be discoverable but never on the
critical first-success path.

**Independent Test**: From a first-success install, confirm no DB driver was installed;
then follow the "Connect your database" path to install one extra and run a live check,
confirming credentials live only in `.env`.

**Acceptance Scenarios**:

1. **Given** a normal (non-dev) first install, **When** the user inspects what was
   installed, **Then** no database driver, no `dev`, and no `livetest` dependency is
   present.
2. **Given** the user follows "Connect your database," **When** they install exactly one
   engine extra and set a DSN in `.env`, **Then** live validation runs and no credential
   appears in any tracked file.

---

### Edge Cases

- **Python missing or wrong version** → the quickstart's prerequisite check (or the
  installer error) names the required Python version and points to how to install it.
- **Git missing** → `seshat check` / `next` are git-aware; the quickstart states `git init`
  is required for a fresh workspace and the error names Git when absent.
- **`seshat` not on PATH after install** → documented fallback and PATH remediation
  (e.g. `pipx ensurepath`), plus the module-invocation fallback for advanced users.
- **Plugin marketplace syntax has changed** → the public plugin install command is
  **verified against the current Claude Code version at plan/implementation time** before
  being published in docs; the local-only `marketplace add ./…` command is never
  presented as the public command.
- **User on macOS/Linux** → equivalent path is documented and tested where practical;
  quickstart separates Windows and macOS/Linux instructions.
- **A published artifact does not yet exist** → docs use a truthful status label and do
  **not** claim `pipx install seshat-bi` works until a real artifact is published.
- **Broken public release** → a documented rollback path lets the owner withdraw/yank the
  package or plugin and revert users to the prior good state.

---

## Requirements *(mandatory)*

### Functional Requirements — First-success experience (P1)

- **FR-001**: The system MUST provide a **user-facing installation path** (preferably
  `pipx`) that installs Seshat BI **without** requiring a source clone, an editable
  install, or development dependencies.
- **FR-002**: After install, the `seshat` console command MUST be available, and the
  existing `retail` alias MUST remain available; both MUST dispatch the same entry point.
- **FR-003**: `seshat init-project <name>` MUST create a clean, governance-clean project
  workspace (as spec 107 already implements), and the first-run sequence
  (`status --format json`, `next --format agent`, `check`) MUST succeed with **no
  database and no Power BI Desktop**.
- **FR-004**: The first run MUST NOT create any fabricated readiness pass; `next` MUST
  report the truthful conservative first action (**Source Ready** onboarding) with
  evidence and blocking reasons, never a numeric confidence score.
- **FR-005**: The first run MUST keep credentials out of tracked files (`.env` only,
  git-ignored) and leave the generated workspace governance-clean (`seshat check` exit 0).
- **FR-006**: When Python, Git, the plugin, or the package install is missing or broken,
  the user MUST receive an **actionable error** identifying the missing prerequisite and
  the remediation, never a silent or misleading result.
- **FR-007**: A new Windows user MUST be able to reach first success in **under 10
  minutes** using a short, copy-pasteable quickstart. **Windows is the only gate-required
  smoke target**; the macOS/Linux path MUST be documented and covered by a **best-effort,
  non-blocking** CI verification *(clarified 2026-07-11: "tested where practical" =
  best-effort/non-blocking, not a release gate)*.

### Functional Requirements — Packaging transition (P1/P2)

- **FR-008**: The specification MUST define the transition from the current editable
  GitHub install to a real user-facing Python distribution, including versioning, wheel +
  source-distribution build, clean-environment installation, and uninstall/upgrade
  behavior — **reusing** spec 108's versioning policy, changelog, and install smoke test
  rather than duplicating them.
- **FR-009**: The **distribution** MUST be published under the name **`seshat-bi`** (the
  name that enables `pipx install seshat-bi` and unblocks first-success), per the
  owner-directed naming decision (2026-07-11). Both `seshat` and `retail` console-script
  aliases MUST be preserved. This distribution rename is separable from — and independently
  shippable ahead of — the import-module rename in FR-009a.
- **FR-009a**: The **import module** MUST migrate `retail` → `seshat` (a clean top-level
  brand import: `import seshat`, `python -m seshat.cli`) as a **reviewed,
  backward-compatible migration** (whole tree + tests + plugin references). This is the
  internal follow-on to FR-009 and is NOT on the first-success critical path (P1 works via
  the `seshat` console script regardless of the import-module name).
- **FR-010**: The rename MUST NOT break the existing Claude Code plugin. Because the
  plugin's documented **fallback** invocation is `python -m retail.cli <verb>` (its
  primary path uses the `seshat` console script, which is unaffected), the migration MUST
  retain a **`retail` compatibility shim module** so `python -m retail.cli` still resolves
  for at least one deprecation cycle *(clarified 2026-07-11: shim chosen over rewriting the
  references — lower risk, preserves the original module, and the plugin fallback keeps
  working without regenerating the mirror in lockstep)*. The shim's presence and the
  `python -m retail.cli` fallback still resolving MUST be an acceptance criterion.
- **FR-011**: Optional extras MUST be documented and installable independently: `db`
  (PostgreSQL / DB validation), `mssql`, `mysql`, `snowflake`, and `files` (file
  profiling). These already exist in `pyproject.toml`; the spec documents them, it does
  not redesign them.
- **FR-012**: A **normal first install MUST NOT** install development (`dev`) or
  live-test (`livetest`) dependencies, nor any database driver.
- **FR-013**: No secret, credential, registry token, or machine-specific path may appear
  in any built artifact or tracked file.

### Functional Requirements — Claude Code plugin (P2)

- **FR-014**: The specification MUST preserve the ratified skill-driven product model and
  add **no** broad replacement CLI verbs for existing skills.
- **FR-015**: The specification MUST provide a **public installation and update story**
  for the existing Seshat BI Claude Code plugin. The exact public marketplace install
  syntax MUST be **verified against the current Claude Code version at plan/implementation
  time**; the existing local-only `claude plugin marketplace add ./…` command MUST NOT be
  presented as the public command without that verification.
- **FR-016**: `Seshat_BI` MUST remain the canonical product and contribution repository.
  If Claude Code distribution requires a separate repository, it MUST be specified as a
  **generated distribution mirror with a one-way release process** from `Seshat_BI` — not
  a second source of truth. Plugin references (including the `python -m …` fallback) MUST
  be regenerated from source, never hand-forked.
- **FR-017**: Plugin installation MUST expose the existing Seshat skill and the existing
  `/seshat-*` commands.
- **FR-018**: The plugin MUST accurately declare whether it is **draft, beta, or publicly
  released**; no badge, link, or wording may imply public availability before publication.

### Functional Requirements — Documentation (all priorities)

- **FR-019**: The README MUST provide a concise entry path with: a one-sentence product
  value statement; a three-step quickstart near the top; clearly separated Windows and
  macOS/Linux instructions (tabs or headed sections); "Try without a database"; "Connect
  your database"; "Use with Claude Code"; a truthful current-status label
  (Alpha/Beta/Stable); expected output so the user knows install succeeded; and
  troubleshooting limited to the most likely first-run failures.
- **FR-020**: The user-facing quickstart MUST NOT require reading `AGENTS.md`, the
  constitution, the roadmap, or any internal spec before first success. Those remain
  contributor and agent references. The M2 doc set (`user-install.md` present;
  `developer-install.md` and `agent-install.md` to be completed) MUST be reconciled, not
  duplicated.

### Functional Requirements — Release quality & rollback (P1)

- **FR-021**: Release acceptance MUST cover: building wheel and source-distribution
  artifacts; installing from those artifacts in clean environments; verifying
  `seshat --help`; generating a fresh project; running `status`, `next`, and `check`
  successfully; validating the public Claude plugin package and install flow; a Windows
  smoke verification; confirming no secrets or machine-specific paths in artifacts; and
  documented upgrade and uninstall behavior.
- **FR-022**: A **release rollback** procedure MUST be defined for both artifacts:
  (a) **package** — withdraw/yank the broken version and revert users to the prior good
  release; (b) **plugin** — revert the generated one-way mirror to the prior released
  tag/commit and re-issue a corrected version, and if the plugin is withdrawn, its
  truthful-status label **drops back to draft/beta** *(clarified 2026-07-11)*. The
  truthful-status discipline MUST be preserved throughout both paths.

### Key Entities

- **Python distribution (`seshat-bi`)**: the user-facing installable artifact (wheel +
  sdist); import module `seshat`; console scripts `seshat` + `retail`; optional extras
  `db`/`mssql`/`mysql`/`snowflake`/`files` (and dev-only `dev`/`livetest`).
- **Fresh project workspace**: the governance-clean tree produced by `seshat init-project`
  (spec 107) — the object of the first-success verification.
- **Claude Code plugin (`seshat-bi`)**: the marketplace-installable plugin exposing the
  Seshat skill + `/seshat-*` commands; a generated one-way mirror if a separate repo is
  required; carries a truthful draft/beta/released status.
- **Readiness answer**: the truthful `next` output (current stage, next allowed action,
  evidence, blocking reasons, forbidden scope, stop point) — never a fabricated pass or
  numeric score.
- **Quickstart entry path**: the README + `docs/install/*` surface a new user reads to
  reach first success without touching internal references.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new Windows user reaches first success (from "discovered on GitHub" to a
  working `seshat check` on a fresh workspace) in **under 10 minutes** following only the
  quickstart.
- **SC-002**: In a clean environment, installing the artifact and running
  `seshat --help`, `seshat init-project`, `status --format json`, `next --format agent`,
  and `check` succeeds **100%** of the time with **no database and no Power BI Desktop**.
  This is **gate-verified on Windows**; the macOS/Linux equivalent runs as a best-effort,
  non-blocking check.
- **SC-003**: A normal first install pulls **zero** development, live-test, and database
  driver dependencies (verifiable by inspecting the installed environment).
- **SC-004**: The `next` first-run answer is truthful in **100%** of fresh-workspace runs:
  it reports the Source Ready onboarding action, with **zero** fabricated readiness passes
  and **zero** numeric confidence scores.
- **SC-005**: A user can start the Seshat-guided Claude Code workflow (plugin installed,
  one instruction issued, truthful next action returned) **without** having read
  `AGENTS.md`, the constitution, the roadmap, or any internal spec.
- **SC-006**: The `retail` → `seshat` migration lands with **both** console scripts
  and the plugin's documented invocations still working (no regression in the existing
  test suite or the plugin's install-and-load flow).
- **SC-007**: **Zero** secrets, credentials, tokens, or machine-specific paths appear in
  any built artifact or tracked file (verifiable by artifact inspection).
- **SC-008**: Every user-facing status label and availability claim is truthful at all
  times — no doc claims PyPI or a public marketplace works before a real published
  artifact exists.

---

## Collision & Reuse *(concise; verified against the repo, 2026-07-11)*

This spec was reconciled against every named collision target. It **reuses and completes**
existing systems; it introduces **no** duplicate installation system and **no** second
product architecture.

| Target | State found | How this spec relates |
|--------|-------------|-----------------------|
| **Roadmap M2 — Installable User Experience** | Marked "built"; goal, desired `pipx install seshat-bi` UX, extras list, and "no premature publish claim" already stated. Doc deliverables only **partially** shipped. | **Completes** M2's first-success experience and tests it; inherits M2's naming-before-publish and truthful-claim rules. |
| **`specs/108-release-distribution-maturity/`** | **BUILT**: versioning policy, changelog, install smoke test, additive CI smoke job. Actual publishing explicitly out of scope (unmade owner call). | **Reuses** 108's release readiness (smoke test / versioning / changelog) as the substrate; does not rebuild it. Publishing remains a separate owner act. |
| **`docs/install/user-install.md`** | **Exists**; truthful — states `pipx install seshat-bi` does *not* work today, plugin is a verified draft. | **Extends/reconciles** into the README quickstart + status labels; keeps the truthful discipline. |
| **`docs/install/developer-install.md`** | **Absent** (M2 deliverable not yet created). | Spec calls for it to be created/reconciled, cleanly separated from the user quickstart. |
| **`docs/install/agent-install.md`** | **Absent** (M2 deliverable not yet created). | Same — created/reconciled; remains an agent/contributor reference, not on the first-success path. |
| **`integrations/claude-code/`** | Verified **draft** marketplace + plugin (`seshat-bi`, skill + four `/seshat-*` commands); local install flow verified (Claude Code CLI v2.1.206); **not** published. Plugin fallback is `python -m retail.cli`. | Provides the public install/update story + truthful status; treats the plugin as a **one-way mirror** if a separate repo is needed; verifies public syntax at plan time. |
| **Ratified CLI-vs-skill decision** (`docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`) | **RATIFIED Option B** (skill-driven) 2026-07-07; the one sanctioned CLI addition is `status --format json`. | **Honored**: no new broad verbs; packaging/docs only. |
| **`init-project`, `status`, `next`, `check`, `doctor`** | All **exist** and behave as the journey claims (specs 107/109/080; verified in `src/retail/cli/parser.py`). | **Consumed as-is**; the spec adds no new verb and changes no existing behavior. |
| **`pyproject.toml`** | Distribution `name = "retail"`; module `src/retail/`; both `seshat`/`retail` scripts; extras `db`/`mssql`/`mysql`/`snowflake`/`files`/`livetest` already present and CI installs none. | The **rename** (FR-009 dist `seshat-bi` / FR-009a module `retail`→`seshat` / FR-010 plugin fallback) and extras **documentation** (FR-011/012) act here; extras are documented, not redesigned. |
| **Specs 110–113 (Option-B packaging)** | **BUILT** (docs-only) — source-onboarding / mapping-review / evidence-pack / BI-delivery packaging over shipped skills. | Adjacent and **reused** as the discovery layer the plugin exposes; this spec does not re-document their capabilities. |

**No-duplication guarantee**: no new installer, no second CLI surface, no second product
architecture, and no second authoritative repository are created by this spec.

---

## Proposed First-Success Journey Diagram

```
                        ┌──────────────────────────────────────────────┐
                        │  NEW EXTERNAL USER (no source-repo knowledge)  │
                        └───────────────────────┬──────────────────────┘
                                                │  reads README quickstart only
                                                ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │  P1 — FIRST SUCCESS  (no database, no Power BI Desktop, < 10 min on Windows)│
   ├───────────────────────────────────────────────────────────────────────────┤
   │  1. install Seshat  ──►  pipx install seshat-bi     (target — NOT yet       │
   │                                                      published; no clone)   │
   │  2. confirm command ──►  seshat --help              (actionable error if    │
   │                                                      Python/PATH missing)   │
   │  3. create workspace ─►  seshat init-project <name> (spec 107; clean tree)  │
   │  4. enter it        ──►  cd <name>  +  git init     (git-aware; named error │
   │                                                      if Git missing)        │
   │  5. verify (no DB)  ──►  seshat status --format json   → {"tables": []}     │
   │                          seshat next   --format agent  → SOURCE READY action│
   │                          seshat check                  → exit 0 (clean)     │
   └───────────────────────────────────┬───────────────────────────────────────┘
                                        │  first success proven
                                        ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │  P2 — START THE SESHAT-GUIDED CLAUDE CODE WORKFLOW                          │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  6. install/activate public plugin  (syntax verified at plan time;          │
   │                                       NOT the local marketplace-add command)│
   │  7. open Claude Code in the workspace                                       │
   │  8. "Use Seshat BI for this project and perform only the next allowed       │
   │      action."                                                               │
   │  9. ◄── truthful SOURCE READY onboarding action  (no fabricated readiness,  │
   │         no numeric score, no database prompt)                               │
   └───────────────────────────────────┬───────────────────────────────────────┘
                                        │  (optional, explicitly later)
                                        ▼
   ┌───────────────────────────────────────────────────────────────────────────┐
   │  P3 — CONNECT YOUR DATABASE  (optional second step, never on the P1 path)  │
   ├───────────────────────────────────────────────────────────────────────────┤
   │  pipx inject seshat-bi <one engine extra: db|mssql|mysql|snowflake>         │
   │  set DSN in .env  (git-ignored; NEVER a tracked file)                       │
   │  seshat validate ...   → live checks                                        │
   └───────────────────────────────────────────────────────────────────────────┘

   Truthfulness invariants across all phases:
     • no fabricated readiness pass        • no numeric confidence score
     • credentials only in .env            • no "published" claim before a real artifact
     • actionable errors on missing deps   • quickstart needs no internal docs
```

---

## Assumptions

*(Informed defaults chosen where the input did not fully specify; recorded here instead of
firing the interactive clarification loop, per the spec-only boundary.)*

- **Naming decision is settled, not open.** The owner directed (2026-07-11) the
  distribution name `seshat-bi` and the import-module rename `retail` → `seshat`
  (a clean top-level brand import), with both `seshat` and `retail` console scripts
  preserved. `seshat-bi` was chosen for the *distribution* (over a bare `seshat`) because
  a generic single-word PyPI name is high-risk/unverifiable at spec time, whereas the
  *import module* `seshat` carries the clean brand internally. The spec records this as an
  owner-directed decision (same pattern as the ratified Option-B doc), not a to-be-verified
  item.
- **Backward-compatible rename via a `retail` compat shim** is now the **decided**
  mechanism (FR-010, clarified 2026-07-11): lower risk, honors the original "preserve the
  module" intent, and keeps the plugin's `python -m retail.cli` fallback resolving for one
  deprecation cycle.
- **`pipx` is the preferred user-facing installer**; `pip install seshat-bi` is documented
  as the alternative. `uv tool install` is a nice-to-have, not required for first success.
- **Target Python is 3.13** (matches the current `requires-python`).
- **Public marketplace syntax is unverified at spec time and treated as a plan-phase
  gate**; the spec does not assert a specific public command (per the input's explicit
  warning and the truthful-status discipline).
- **Windows is the only gate-required tested first-success target** (per the input and the
  2026-07-11 clarification); macOS/Linux is documented and covered by a best-effort,
  non-blocking CI check.
- **No artifact is published during this feature.** Publishing to PyPI and to a public
  Claude Code marketplace remain separate, still-unmade owner acts.

---

## Out of scope / Non-goals

- No new BI rules; no changes to the seven readiness stages.
- No Power BI publishing adapter; no automatic dashboard generation; no database
  provisioning; no web application.
- No broad CLI redesign and no new replacement CLI verbs for existing skills.
- No implementation in this phase; no GitHub release or PyPI/plugin publication during
  specification.
- No creation of a second authoritative source repository (a generated one-way mirror is
  the only permitted separate-repo shape, and only if Claude Code distribution requires
  it).
