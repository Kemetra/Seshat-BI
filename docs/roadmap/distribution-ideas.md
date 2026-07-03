# Seshat BI — Compass-Driven Agent Kit (distribution architecture note)

> **Hand-authored architecture note, NOT idea-engine output and NOT a roadmap
> commitment.** Kept deliberately SEPARATE from `idea-backlog.md` (the idea-engine
> regenerates that from scratch; hand ideas dropped there get wiped + corrupt its
> provenance). Nothing here is planned, scheduled, or approved. This note is the
> architecture the eventual build will SPEC FROM; it never promotes an idea onto the
> roadmap or assigns an F-number. The paved next step is human-picks-one →
> `idea-to-spec` (one idea per run).

_Authored 2026-07-02. Goal: ship Seshat BI the way speckit / impeccable ship — a
package you `pip install`, then an agent-invokable `init` that scaffolds files to
**orient the agent**, and thereafter **the agent drives the tool** by calling verbs,
not a human running a CLI. This note proposes a NEW model (not a copy of either) and
scopes it against the repo's constitution and the F024 taxonomy._

---

## The load-bearing "why": dual-harness parity

Claude Code drives Seshat via its **skill system** (`/retail-orchestrate`,
`/source-mapping`, …). **The premise:** Codex exposes no equivalent skill-invocation
layer, so the only way Codex can drive the tool the way Claude Code does is a
**harness-neutral, machine-readable orientation file both harnesses read**. That file is
`compass.yaml`. This is the whole reason the model exists — it IS the goal ("connect with
Claude Code AND Codex") restated as an artifact.

> **⚠️ This premise is EXTERNAL and unverified from the repo — verify at build time.**
> Nothing in the repo confirms Codex's capabilities: `.specify/integrations/` holds only
> `claude.manifest.json` + `speckit.manifest.json` (speckit ≠ Codex), no `codex.manifest.json`;
> the only repo mention of Codex is as an external PR reviewer (ADR 0006). If Codex *does*
> gain a skill layer, the compass is still useful (harness-neutral orientation) but its
> load-bearing justification weakens — so this fact must be checked, not assumed, before
> the model is spec'd.

> **Correction to an earlier framing:** speckit's router is NOT its manifest — it's its
> *skills*. Its manifest is just an integrity receipt. The novel thing here is a
> machine-readable **router** that is harness-neutral, which is what buys Codex parity.

---

## The model: one canonical source → projections (NOT a new subsystem)

This is a **simplification**, not new surface. There is ONE canonical kit source; the
compass, both convention files, and the integration manifests are all **generated
projections** of it, verified by a drift linter.

```text
canonical kit source  (single source of truth, committed — DOWNSTREAM of the constitution)
        │  generate
        ├──►  .seshat/compass.yaml        machine router (harness-neutral)  ← Codex parity
        ├──►  AGENTS.md   [FENCED region only]   prose projection (Codex convention)
        ├──►  CLAUDE.md   [FENCED region only]   prose projection (Claude Code convention)
        ├──►  .seshat/integrations/*.json per-harness file+checksum manifest (speckit's good part)
        └──►  .seshat/manifest.yaml       kit file inventory + checksums
                              ▲
              drift linter (B2) fails loud if any projection drifts from the source
```

The agent reads `compass.yaml` (or its `AGENTS.md`/`CLAUDE.md` projection) to know
**what verbs exist and what it must not do**, then drives the verbs.

### AGENTS.md / CLAUDE.md are only PARTIALLY generated — the fence (read before speccing)

**These two files are constitution-governed and must NOT be blanket-regenerated.**
`AGENTS.md` is a constitution dependent artifact (constitution.md:22); changes to repo
`CLAUDE.md` flow through the named-human amendment procedure (constitution.md:156, 512–522).
`CLAUDE.md` also carries repo law with **no upstream generator** — the secrets/`.env`
baseline, the exact PBIP `.gitignore` baseline (`**/.pbi/localSettings.json`,
`**/.pbi/cache.abf`), the Windows 260-char limit, line-endings. A `retail sync` that
regenerated the whole file would clobber that law or route a constitutional change around
the amendment procedure.

So generation is **fenced**: the tool writes ONLY a delimited generated region (CLAUDE.md
already demonstrates the pattern with its `<!-- SPECKIT START -->…<!-- SPECKIT END -->`
block); the hand-authored / constitution-owned region is **exempt** and never touched by
`sync`. The canonical kit source is itself **downstream of the constitution** — the drift
linter must eventually check the source *against* the constitution's hard-stops, not only
the projections against the source. Regenerating these two files can never bypass
constitution.md:512–522.

### What `compass.yaml` IS and IS NOT (the scope wall — read this before speccing)

- **IS:** the **kit router** — a static-ish, repo-level declaration of *what verbs
  exist*, *what each is for*, *the hard-stops the agent must respect*, and *which
  harness integrations are wired*.
- **IS NOT a state / run-state engine.** It **MUST NOT store a readiness stage.**
  Work-state ("what stage am I serving") already exists, is **per-table**
  (`readiness-status.yaml`), and AGENTS.md is explicit: *"there is no separate
  run-state engine."* A repo has MANY tables at different stages — a singleton
  repo-level stage is both forbidden and incoherent. The compass **points at**
  `readiness-status.yaml` for state and **declares the orientation protocol**; it never
  holds the state.
- **DECLARES, does not ENFORCE.** A hard-stop the agent *reads* in the compass is
  **orientation**. Enforcement stays where it already lives: the `@register` lint rules
  + the `G6`/`C2` gate guards. The **drift linter (B2) is the enforcement arm** for the
  compass itself (does the projection match the source?). The doc/spec must never claim
  the compass "enforces" what it only "declares."

### Sketch of `compass.yaml` (kit router only — no stage stored)

```yaml
kit: seshat-bi
version: 0.2.0

# Orientation PROTOCOL — declares HOW to orient; points at per-table state, stores none
orient:
  question_first: "What readiness stage am I serving?"
  state_lives_in: "templates/readiness-status.yaml shape (per TABLE, recomputed)"
  recompute_from: [committed artifacts, "Gate status", migration presence]
  # NOTE: no `current_stage` field here — that would be the forbidden run-state engine.

# The verbs the agent DRIVES (helpers it CALLS; each does its job and STOPS)
verbs:
  - id: retail-orchestrate   # conductor
  - id: source-mapping       # the gate → produces source-map.yaml
  - id: retail-build-warehouse
  - id: retail-validate      # live checks; needs db extra + DSN, else [PENDING LIVE PROFILE]
  - id: retail-govern        # static check

# Hard-stops the agent READS as orientation (enforcement is the lint rules + G6/C2, not this file)
hard_stops:
  - never_self_grant_approval          # Principle V — human owns approvals
  - no_silver_before_mapping_cleared   # Principle IV
  - no_dashboard_before_metric_contracts
  - never_fabricate_a_confidence_score

integrations: [claude, codex]   # which harness projections are generated
```

### The agent loop (what "agent-driven" means, concretely)

```text
1. Agent starts a task
2. Reads compass (or its AGENTS.md / CLAUDE.md projection)  ──►  verbs + hard-stops + "recompute stage from readiness-status.yaml"
3. Agent recomputes the per-table stage, picks the next verb
4. Agent invokes the verb (a helper it CALLS); the verb does its job and STOPS
5. Agent re-reads state; loops. The agent removes ORDERING and CEREMONY, not JUDGMENT:
   the human still owns every named approval the compass refuses to self-grant — and those
   (grain, PII placement, metric policy) ARE the hard retail-BI thinking, not a residual chore.
```

---

## What the repo ALREADY commits to (verified against specs — do NOT rebuild)

| Concern | Status | Where |
|---|---|---|
| Packaging substrate + install profiles | ✅ **Shipped** | `pyproject.toml`: `retail` entry point + `db` / `files` / `dev` extras. |
| Companion-tools **authority taxonomy** (5 categories) | ✅ **Spec'd** | F024 / spec `018` (docs-first; writes no code, adds no CLI verb). |
| Adapter/kit **update SAFETY policy** (3 lanes, PR-based, human-review gates) | ✅ **Spec'd** | F031 / spec `025`. **Principle II: Depend, Never Fork.** |
| Adapter/kit **version-truth record** | ✅ **Spec'd** | F032 / spec `026`. |
| **Release notes + evidence-gated maturity ladder** | 🟡 Spec'd, unbuilt | F033 / spec `027` (consume it; never reinvent). |
| The **speckit precedent** for exactly this pattern | ✅ **Present** | `.specify/` = manifest + per-integration checksummed manifests + templates scaffolded to orient the agent. Proof the pattern works here. |
| Orientation **spine** the compass makes machine-readable | ✅ **Present** | `COMPASS.md` already says "answer *what stage am I serving?* first, then route." The compass just makes that prose spine harness-neutral + init-scaffolded. |

## The genuine gap (confirmed — no spec defines it)

The **install / bootstrap RUNTIME** — an agent-invokable `init` that scaffolds the
orienting files, and a `sync` that re-projects them — **does not exist**. Spec `001`
excludes **all install runtime** from its docs-and-templates-only slice ("no validator
scripts, no `pbi-cli` integration, no CLI installer, no warehouse tables, no DB writes" —
spec.md:305). The text draws **no human-vs-agent distinction** — so the honest framing is:
`init` is **new scope for a later slice**, not something the 001 exclusion "was really
about." (An earlier draft of this note claimed the 001 exclusion targeted a *human* wizard
specifically; that was a misread — corrected here so the eventual spec survives a
`speckit-analyze` consistency pass.)

**Precedent — split honestly.** `.specify/` was created by `specify init --here` — a
**human-run CLI** (spec.md:310; init-options.json `"ai": "claude"`). So:

| | Does `.specify/` precedent it? |
|---|---|
| **Scaffold files, then let the agent drive** from them | ✅ **Yes** — agents read `.specify/` templates + constitution to orient. Strong precedent. |
| **An AGENT invokes the scaffolder** (`init` is agent-triggered) | ❌ **No** — `.specify/` was scaffolded by a human CLI. This half is unprecedented here; it is, by its own nature, the CLI-install pattern 001 declined. |

> **F024 classification — RESOLVED: use existing categories, NO amendment.** The wrong move
> is "Product Module" (that category *consumes Core Authority*, spec 018:131–133 — and
> `init`/`sync`/the generator consume the kit's own files, not a table's truth). But the fix
> is NOT a 6th category: FR-001 declares the five a **"normative, closed set"**, and adding
> one is a versioned constitution amendment — over-engineering when an existing category fits.
> Two do, cleanly, because neither restricts its INPUT to Core Authority:
> - **Projection generator + drift linter = `Maintenance Automation`** (FR-006): runs in CI
>   without a per-invocation human trigger, emits only derived evidence (the projections + a
>   pass/fail signal), creates no truth, self-approves nothing. Exact fit.
> - **`init` / `sync` = `Official Workflow Skill`**: an agent procedure invoked to drive a
>   step (scaffold-and-orient / re-project), writing files but self-granting nothing — the
>   same category as `retail-orchestrate` and the onboarding wizard.
>
> The "consumes Core Authority" restriction is specific to Product Module; Maintenance
> Automation and Workflow Skill carry no such input rule, so the meta-level tension dissolves
> without touching the closed set.

---

## The one load-bearing decision — the update seam (F024 module-vs-adapter)

Discriminator: **does the kit's own code make the network fetch, or does pip/git?**

- **Package-driven (Phase-1 model, ships now).** Update = `pip install -U seshat-bi`
  (pip/git fetches), then `retail sync` re-projects `.seshat/` + regenerates ONLY the fenced
  regions of `AGENTS.md`/`CLAUDE.md` from the installed package, three-way-merging user edits
  by checksum. Kit touches only the **local repo working set** → **Official Workflow Skill**
  (invoked to drive the re-projection step; the generator it calls is Maintenance Automation).
  Constitution-clean; runs **under** the F031 update-safety lanes.
- **Channel-driven (deferred, gated end-state).** The kit itself fetches from a remote
  channel → **crosses the external trust boundary** → **Execution Adapter /
  `external-service-connected`**, gated like F016; collides with "never auto-exec
  untrusted pulled content."

**Not rival winners — the "now" and "later" of one axis,** mirroring how the repo defers
F016 to last-and-gated. **Phase-1 = package-driven.**

---

## Build order — LEAD WITH ANALYST VALUE (revised after the analyst-lens review)

The analyst review was blunt and correct: the earlier "Phase-1 = canonical source +
generator + drift linter" was **four kinds of invisible plumbing**. Installing it and
running all four steps produces *nothing an analyst can show a stakeholder* — the
first-run experience was "the machine tells the agent about the machine," ending on a
green governance gate over an empty repo. That is backwards. The plumbing is real and
still gets built — but it moves **backstage** (the agent consumes it silently), and the
build **leads with a visible result on the user's own table**.

### Phase 1 — the "aha": `init` ends on a visible artifact from MY table

The very first shippable slice must end on something an analyst can see:

| Step | What the analyst experiences | Notes |
|---|---|---|
| **1. `init` bootstraps + offers a worked example** | "Pick a starting point: a filled worked example under `docs/worked-examples/` such as `retail-store-sales`" — then it clones that filled spine's *shape* against my table. | The worked examples already exist (`docs/worked-examples/`); the bootstrap must **connect me to them**, not walk past them. |
| **2. First run profiles MY table** | The next command profiles my actual source and shows me grain candidates / column types — a result, not a gate. | Uses the existing `retail-orchestrate` → `source-mapping` verbs; `init` just routes me into them. |
| **3. Honest expectation-setting** | Up front: *"the agent handles sequence and plumbing — you still own grain, PII, and metric policy."* | The hard-stops the agent won't self-grant ARE the judgment; don't imply more relief than an analyst gets. |

The compass, projections, and manifests are **written during `init` but not shown as
steps** — they orient the agent silently underneath step 2.

### Phase 2 — the backstage substrate (built, never user-facing)

| Component | What | F024 category (RESOLVED — existing, no amendment) |
|---|---|---|
| Canonical kit source | the single committed source projections generate from; **downstream of the constitution** | committed static artifact |
| Projection generator | one source → `compass.yaml` + fenced `AGENTS.md`/`CLAUDE.md` regions + manifests | **Maintenance Automation** (CI, emits derived evidence, no truth) |
| Drift linter | fail loud if a projection drifts from source **or the source drifts from the constitution** | **Maintenance Automation** (CI-only; **never a user step**) |

> The drift linter + checksummed manifests are **kit-author hygiene, not analyst value** —
> they can only ever say "the plumbing is consistent," never "your numbers are right." Keep
> them entirely in CI/maintenance; if they ever surface in the user-facing flow, that is
> ceremony to cut.

### Phase 3 — updatable, safely

`retail sync` (package-driven self-update: `pip install -U`, then re-project **only the
fenced regions**, three-way-merge user edits, surface F033 release notes), then
`retail doctor` (read-only health check).

### Phase 4 — deferred / gated

Channel-driven fetch + rollback + integrity — the kit itself fetches from a remote →
**Execution Adapter / `external-service-connected`**, gated like F016.

## Pre-spec questions — RESOLVED (grounded in repo law 2026-07-02)

1. **F024 category — RESOLVED: no new category.** FR-001 declares the five a closed set;
   adding a sixth is a versioned amendment (over-engineering). Existing categories fit because
   they don't restrict INPUT to Core Authority: generator + drift linter = **Maintenance
   Automation** (FR-006); `init`/`sync` = **Official Workflow Skill**. Only Product Module
   required Core-Authority input — so simply don't use it.
2. **Codex premise — RESOLVED: reframed & confirmed.** Codex IS a configured harness on this
   repo (ADR 0006 — a PR reviewer that found 9 real defects). The repo has no evidence about
   its skill-invocation capability, so the honest claim is *"Codex drives via the `AGENTS.md`
   convention"* (verified), NOT the absolute *"has no skill system"* (kept hedged). The
   harness-neutral router is how Codex reaches parity today regardless — foundation holds.
3. **Fence — RESOLVED: reuse the existing pattern.** No need to design one. `CLAUDE.md` already
   ships a working fence (`<!-- SPECKIT START -->…<!-- SPECKIT END -->`, lines 35–39) that
   leaves all surrounding repo law untouched. `sync` writes ONLY inside a
   `<!-- SESHAT-KIT START -->…<!-- SESHAT-KIT END -->` block; everything outside is
   hand-authored / constitution-owned and never touched. Proven-in-production safety property.

## The paved next step

A human **chooses one idea** — the natural first pick is **Phase-1 Step 1–2** (the
`init`-to-worked-example-to-first-profile path), because it delivers a visible result and
pulls the backstage substrate in behind it only as far as that path needs. Then run
`idea-to-spec` on that single idea (one idea per run) inside a worktree. The three questions
above are now **settled**, so `clarify` inherits answers, not open decisions.
