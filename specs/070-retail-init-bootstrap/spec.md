# Feature Specification: `retail init` Bootstrap-to-First-Result (Compass-Driven Kit, Phase-1 Step 1-2)

**Feature Branch**: `070-retail-init-bootstrap`

**Created**: 2026-07-02

**Status**: Ratified (Ahmed Shaaban, 2026-07-02)

> Ratified by owner directive dated 2026-07-02 ("ratify it and authorize
> implementation"), accepting DEC-1/2/3 as specified (Phase-1-only scope; live-DB
> profile with `[PENDING LIVE PROFILE]` degrade, no CSV/Excel profiler; fence-body
> human review until the Phase-2 drift linter). The advisor transcribes the owner's
> recorded decision (approval-console pattern) -- it does not originate it. analyze:
> 0 CRITICAL / 0 HIGH; plan-review round 2: PASS-WITH-NOTES. Build authorized.

**Input**: User description: "Phase-1 Step 1-2 of the Compass-Driven Agent Kit
(`docs/roadmap/distribution-ideas.md`): an agent-invokable `retail init` that
bootstraps the orienting files, offers a worked example (c086-pharmacy or
retail-store-sales) to steer by, then routes into the existing
`retail-orchestrate` / `source-mapping` verbs to profile the user's own table and
show a visible first result (grain candidates, column types). Backstage substrate
(`compass.yaml`, fenced `AGENTS.md` / `CLAUDE.md` projections, manifests) is
written during init but not shown as steps. The three pre-spec questions are
already resolved in the doc."

> **Provenance.** This slice is the doc's own recommended first pick (Phase-1 Step
> 1-2). The idea is deliberately NOT in `docs/roadmap/idea-backlog.md` (the
> idea-engine regenerates that from scratch; a hand-dropped idea would corrupt its
> provenance) and carries no roadmap F-number, so it was spec'd DIRECTLY via the
> speckit chain rather than through `idea-to-spec`'s backlog-locate front stage.
> The three pre-spec questions (F024 category, the fence, the Codex premise) are
> RESOLVED in `distribution-ideas.md` and inherited here, not reopened.

## Overview

Today there is no bootstrap. A new user who `pip install`s the kit lands in a repo
with no orienting files, no pointer to the two committed worked examples, and no
first-run path to a visible result on their own table. The orientation *spine*
exists in prose (`COMPASS.md` already says "answer *what stage am I serving?*
first, then route"), and the verbs exist (`retail-orchestrate` ->
`source-mapping`), but nothing connects install to a first "aha". Spec `001`
excluded ALL install runtime from its docs-and-templates-only slice; `init` is new
scope for this later slice, not something 001 "was really about".

This feature is primarily an **agent Workflow Skill** (`.claude/skills/retail-init/`)
that the AGENT performs -- NOT a terminal wizard. It leads with visible analyst
value and pulls the backstage substrate in silently behind it. Its thin mechanical
surface (a small `retail init` CLI + stdlib-ish modules) does ONLY substrate-writing;
all delegate / route / profile behavior is the agent executing the skill, consistent
with Principle I ("agent-first, not terminal-first"). Concretely:

- **The SKILL bootstraps + DELEGATES the worked-example offer** -- the agent, on
  first run, hands the worked-example choice to the EXISTING `first-hour-compass`
  skill, which already presents the two committed worked examples (`c086-pharmacy`,
  `retail-store-sales`) and lets the user pick the closer domain analog to steer by
  (shape reference, not a file copy). `init` MUST NOT reimplement that offer -- it
  routes into it, so there is one source for the first-arrival pattern.
- **The SKILL routes into the existing verbs to profile MY table** -- the agent
  hands off to the EXISTING `first-hour-compass` -> `retail-onboard-table` front
  door (the onboarding verb that owns the Stage-1 read-only profile), so profiling
  the user's actual source shows a first RESULT (grain candidates, column types).
  This result is produced by the agent executing the existing verbs OVER A LIVE DB
  (`db` extra + DSN). With no DB configured, the honest outcome is the source-map /
  orientation structure plus `[PENDING LIVE PROFILE]` -- still more than "the
  machine describing the machine", never a fabricated profile. The Python `init`
  module MUST NOT reimplement profiling and MUST NOT open a DB connection.
- **The SKILL sets expectations honestly** -- the agent states up front that it
  handles sequence and plumbing, but the user still owns the human judgment seams;
  the exact seam wording is DELEGATED to `first-hour-compass` (single source), not
  restated here. Those seams are surfaced and STOPPED on, never auto-resolved
  (Principle V).
- **The mechanical surface writes the backstage substrate silently** -- the compass
  router (`.seshat/compass.yaml`), the fenced `AGENTS.md` / `CLAUDE.md` generated
  regions, and the kit manifests are WRITTEN during `init` but are NOT shown as
  user-facing steps; they orient the agent underneath the profile step. A `retail
  init` CLI, if present, writes ONLY the substrate and PRINTS the next agent step --
  it never prompts, shows a menu, or emits a profile (the `scaffold.py` write/print
  precedent).

`init` is an **Official Workflow Skill** (F024): an agent procedure invoked to
drive a step (scaffold-and-orient), writing files but self-granting nothing -- the
same category as `retail-orchestrate` and `retail-onboard-table`. It defines and
orients; it never approves a readiness gate, never advances a stage, never fetches
from a remote, and never fabricates a confidence score.

## Clarifications

### Session 2026-07-02

- Q: Does `init` STORE a readiness stage anywhere (a repo-level `current_stage`)?
  -> A: NO. Work-state is per-table and already lives in `readiness-status.yaml`;
  AGENTS.md is explicit that "there is no separate run-state engine". `init` and
  `compass.yaml` DECLARE the orientation protocol and POINT AT per-table state;
  they store none. A singleton repo-level stage is both forbidden and incoherent
  (a repo has many tables at different stages).
- Q: Does `init` regenerate the whole `AGENTS.md` / `CLAUDE.md`? -> A: NO. It writes
  ONLY inside a delimited generated fence (`<!-- SESHAT-KIT START -->...<!-- SESHAT-KIT END -->`),
  reusing the proven speckit fence pattern already shipped in `CLAUDE.md`.
  Everything outside the fence is hand-authored / constitution-owned and is NEVER
  touched -- regenerating those files can never bypass the constitution amendment
  procedure.
- Q: Is `init` idempotent -- what happens on a second run over an already-bootstrapped
  repo? -> A: `init` is safe to re-run. On a repo that already has the fenced regions
  and `.seshat/` substrate, it re-projects ONLY the fenced regions and reports
  "already bootstrapped"; it never duplicates a fence, never clobbers the
  hand-authored region, and never re-asks the worked-example pick if state already
  records one. (The full self-update / three-way-merge path is Phase-3 `sync`, out
  of scope here.)
- Q: Does `init` PROFILE the table itself, or route to the profiling verb? -> A: The
  AGENT (executing the skill) ROUTES; the Python `init` module never profiles. `init`
  owns bootstrap + the substrate write + the orientation framing; the actual profile
  is the EXISTING `first-hour-compass` -> `retail-onboard-table` verb chain, which
  the agent performs (those are prose skills, not importable functions). The Stage-1
  read-only profile that yields grain candidates + column types is DB-backed
  (`profile.py` runs over a `QueryRunner`); the `init` module MUST NOT reimplement it
  and MUST NOT open a DB connection.
- Q: Is the "grain candidates + column types" result GUARANTEED on first run? -> A:
  No -- it is guaranteed only when a live DB is reachable (`db` extra + DSN). The
  kit's only profiler (`profile.py`) is DB/SQL-backed; there is no CSV/Excel
  profiler and building one is out of scope (YAGNI, `CLAUDE.md`). With no DB, the
  honest first-run outcome is the source-map / orientation structure + `[PENDING
  LIVE PROFILE]`. "Lead with visible value" holds in the DB case and degrades
  honestly without one; it NEVER fabricates a profile.
- Q: Which verb is the profiling front door -- `retail-orchestrate`,
  `source-mapping`, or `retail-onboard-table`? -> A: `retail-onboard-table` (reached
  via `first-hour-compass`). It is the Source -> Mapping front door that OWNS the
  Stage-1 read-only profile; `source-mapping` is the downstream Stage-2 gate (too
  late for grain candidates) and `retail-orchestrate` is the whole-pipeline
  conductor (broader than a first profile). `retail-onboard-table` is therefore the
  one route and MUST appear in the compass `verbs[]`.
- Q: What if there is no table yet / the user names nothing? -> A: `init` still
  delivers value: it bootstraps and DELEGATES to `first-hour-compass` (which
  presents the two worked examples as reference patterns), then routes to
  `retail-onboard-table` for the user's own table when they name one. Absent is the
  honest not-started state, never a fabricated table or stage.
- Q: Doesn't `first-hour-compass` ALREADY offer the worked examples -- is `init`
  duplicating it? -> A: YES it does, and `init` MUST NOT fork it. `first-hour-compass`
  owns the first-arrival worked-example offer and the single-table orientation card;
  `init` owns ONLY what has no existing home: writing the backstage substrate
  (`compass.yaml` + fenced projections + manifests), the honest install-time
  expectation-setting, and wiring bootstrap -> the EXISTING
  `first-hour-compass` -> `retail-onboard-table` front door (with
  `retail-orchestrate` / `source-mapping` as the later medallion stages). The
  distinction is INSTALL-TIME bootstrap vs. per-table orientation; `init` delegates
  the overlap rather than restating it (no second source of truth for the
  first-arrival pattern).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - First run ends on a visible result from MY table (Priority: P1)

A new analyst who has just installed the kit invokes the `init` skill and, within
the same short agent-driven flow, sees a concrete result computed against THEIR own
source -- grain candidates and column types (when a live DB is reachable) -- rather
than a green gate over an empty repo. With no DB, the same flow ends honestly on the
source-map / orientation structure + `[PENDING LIVE PROFILE]`.

**Why this priority**: This is the entire "aha". The analyst-lens review was blunt:
a first run that ends on "the machine tells the agent about the machine" over an
empty repo is backwards. Leading with a visible result on the user's own table (or,
without a DB, the honest orientation structure) is what makes the kit feel
agent-driven and worth adopting. Everything else (the substrate) is plumbing that
earns its place only by serving this.

**Independent Test**: Have the agent invoke the `init` skill; it delegates the
worked-example offer to `first-hour-compass`, routes into `retail-onboard-table`,
and -- with a live DB -- ends on a profile result (grain candidates + column types)
for the named table; without a DB it ends on the orientation structure + `[PENDING
LIVE PROFILE]`. The substrate is written but not shown as a step. (No terminal
wizard: the flow is the agent performing prose skills, not a `retail init` menu.)

**Acceptance Scenarios**:

1. **Given** a freshly installed kit in a repo with no `.seshat/`, a real source
   table, AND a reachable DB, **When** the agent invokes the `init` skill and the
   user names their table, **Then** the flow DELEGATES the worked-example offer to
   `first-hour-compass`, the user picks one, and it ends on a first profile result
   (grain candidates + column types) produced by the agent executing
   `retail-onboard-table`'s Stage-1 read-only profile.
2. **Given** the same flow, **When** the profile result (or the `[PENDING LIVE
   PROFILE]` structure) is shown, **Then** the compass router, fenced `AGENTS.md` /
   `CLAUDE.md` regions, and manifests have been written to disk but were NOT
   presented as user-facing steps.
3. **Given** the live boundary is unavailable (no `db` extra / no DSN), **When**
   the agent routes into profiling, **Then** the flow reports the boundary and the
   enable steps, marks profile numbers `[PENDING LIVE PROFILE]`, and STAYS USEFUL
   (authors the artifact structure) -- it never tracebacks and never fakes a pass.

---

### User Story 2 - Bootstrap orients the agent (backstage substrate) (Priority: P2)

An agent (Claude Code or Codex) picking up the repo after `init` can read a single
harness-neutral router to learn what verbs exist, what hard-stops it must respect,
and that per-table state is recomputed from `readiness-status.yaml` -- without a
human walking it through the plumbing.

**Why this priority**: The substrate is real and load-bearing (it is what buys
harness-neutral / Codex parity), but it is backstage. It must be BUILT and CORRECT,
yet it must never surface as ceremony in the user-facing flow. P2 because the P1
aha can be demonstrated on top of it, but the substrate is what makes the kit
durable and multi-harness.

**Independent Test**: After `init`, confirm `.seshat/compass.yaml` exists and
declares the verbs + hard-stops + the "recompute stage from readiness-status.yaml"
protocol, stores NO `current_stage`, and that the `AGENTS.md` / `CLAUDE.md` fenced
regions match the canonical source (drift check), with the hand-authored regions
untouched.

**Acceptance Scenarios**:

1. **Given** `init` has run, **When** an agent reads `.seshat/compass.yaml`, **Then**
   it finds the verb list, the hard-stops (never self-grant approval; no silver
   before mapping cleared; no dashboard before metric contracts; never fabricate a
   confidence score), and an orientation protocol that POINTS AT per-table
   `readiness-status.yaml` and stores no repo-level stage.
2. **Given** `init` writes the fenced `AGENTS.md` / `CLAUDE.md` regions, **When** the
   files are inspected, **Then** ONLY the `<!-- SESHAT-KIT START -->...<!-- SESHAT-KIT END -->`
   region is generated content and every line outside the fence is byte-identical to
   before `init` ran.
3. **Given** a repo already bootstrapped, **When** `init` runs again, **Then** it
   re-projects only the fenced regions, reports "already bootstrapped", and does not
   duplicate a fence or re-ask a recorded worked-example pick.

---

### User Story 3 - Honest expectation-setting on the human seams (Priority: P3)

Before the analyst invests in the flow, `init` states plainly which relief the
agent provides (sequence, plumbing, ordering, ceremony) and that the human still
owns the judgment seams -- surfacing the seam list from its single source
(`first-hour-compass`), not a re-typed copy.

**Why this priority**: Trust. The kit's value proposition must not over-promise
autonomy the constitution forbids. Setting the seam expectation up front is cheap
and prevents the analyst from believing a `pass` or a profile relieved them of a
judgment call it never touched. P3 because it is a message, not a mechanism, but it
is a required part of the honest first-run.

**Independent Test**: Confirm the `init` flow surfaces, up front, the statement that
the agent handles sequence + plumbing while the user owns the human judgment seams,
and that the seam wording is the one `first-hour-compass` states (not a divergent
list re-typed inside `init`).

**Acceptance Scenarios**:

1. **Given** the `init` flow, **When** it sets expectations, **Then** it surfaces the
   human-owned judgment seams AS STATED BY `first-hour-compass` (its single-source
   list) as things the agent surfaces and STOPS on, never self-grants (Principle V) --
   `init` does not maintain its own divergent seam list.
2. **Given** the worked-example offer, **When** a user picks one, **Then** the flow
   is explicit that the example is a narrative pattern to steer by (copy the shape),
   NOT a file template copied into the user's table dir.

### Edge Cases

- **No source table named**: `init` bootstraps, presents the worked examples as
  reference, and routes to `retail-onboard-table`; it never fabricates a table or a
  stage. Absent = honest not-started.
- **Partial / prior bootstrap** (fence present but `.seshat/` missing, or vice
  versa): `init` completes the missing pieces and reports what it reconciled; it
  never double-inserts a fence and never clobbers the hand-authored region.
- **Live boundary absent** (`db` extra / DSN missing): report boundary + enable
  steps, mark `[PENDING LIVE PROFILE]`, stay useful, never traceback, never fake a
  pass (mirrors the existing `retail validate` deferred-mode contract).
- **Constitution-owned file conflict**: if the fence markers are missing from a
  hand-edited `AGENTS.md` / `CLAUDE.md`, `init` inserts a fresh fenced region at a
  safe location and does NOT rewrite surrounding law; if it cannot do so safely, it
  reports and STOPS rather than risk clobbering constitutional text.
- **Second harness** (Codex): the same `compass.yaml` + `AGENTS.md` projection must
  orient Codex; nothing in `init` may be Claude-Code-only in a way that leaves Codex
  without a machine-readable router.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The kit MUST expose an agent-invokable `init` workflow SKILL that
  bootstraps a repo for the Compass-Driven kit and ends the first-run flow on a
  visible result from the user's own table when a live DB is reachable, or on the
  orientation structure + `[PENDING LIVE PROFILE]` otherwise. The Python/CLI surface
  of `init` MUST be substrate-writing only (it never prompts, shows a menu, or emits
  a profile); the delegate/route/profile behavior is the agent performing the skill.
- **FR-002**: `init` MUST DELEGATE the first-arrival worked-example offer to the
  existing `first-hour-compass` skill (which presents `c086-pharmacy` /
  `retail-store-sales` and takes the user's pick); `init` MUST NOT reimplement the
  offer, so there is exactly one source for the first-arrival pattern.
- **FR-003**: The `init` SKILL MUST route (agent-performed) into the EXISTING
  `first-hour-compass` -> `retail-onboard-table` verb chain to profile the user's
  table (the onboarding verb owns the Stage-1 read-only, DB-backed profile). The
  Python `init` module MUST NOT reimplement profiling and MUST NOT open a DB
  connection itself. `retail-onboard-table` MUST be listed in the compass `verbs[]`
  so an agent reading only `compass.yaml` can discover the profiling front door.
- **FR-004**: `init` MUST write the backstage substrate (`.seshat/compass.yaml`,
  the fenced `AGENTS.md` / `CLAUDE.md` generated regions, the kit manifests) but
  MUST NOT present that substrate as user-facing steps.
- **FR-005**: `compass.yaml` MUST declare the verbs, the hard-stops, and an
  orientation protocol that POINTS AT per-table `readiness-status.yaml`; it MUST NOT
  store a repo-level `current_stage` or any run-state.
- **FR-006**: `init` MUST write generated content ONLY inside a delimited fence
  (`<!-- SESHAT-KIT START -->...<!-- SESHAT-KIT END -->`) in `AGENTS.md` /
  `CLAUDE.md`; every line outside the fence MUST remain byte-identical.
- **FR-007**: `init` MUST NOT regenerate, relocate, or delete any hand-authored /
  constitution-owned content, and MUST NOT route a constitutional change around the
  amendment procedure.
- **FR-008**: `init` MUST be idempotent: a re-run over an already-bootstrapped repo
  re-projects only the fenced regions, reports "already bootstrapped", never
  duplicates a fence, and never re-asks a recorded worked-example pick.
- **FR-009**: `init` MUST set expectations up front that the agent handles sequence
  + plumbing while the user owns the human judgment seams, which the agent surfaces
  and STOPS on, never self-grants (Principle V). `init` MUST surface the seam list
  from its single source (`first-hour-compass`) rather than maintaining its own
  divergent copy.
- **FR-010**: `init` MUST NOT approve or advance any readiness stage, MUST NOT write
  an `approvals[]` entry, and MUST NOT emit any numeric health / confidence /
  percent-ready score (hard rule #9).
- **FR-011**: `init` MUST NOT fetch from any remote channel or auto-execute pulled
  content; kit updates are the Phase-3 `sync` / Phase-4 channel-driven scope, gated
  and out of this feature.
- **FR-012**: When the live boundary is unavailable, `init` MUST report the boundary
  and enable steps, mark profile numbers `[PENDING LIVE PROFILE]`, stay useful, and
  never traceback or fake a pass.
- **FR-013**: The worked example MUST be presented as a narrative pattern to steer
  by, NOT copied as a file template into the user's table directory (starting
  artifacts still come from `templates/`, seeded by `retail-onboard-table`).
- **FR-014**: All files `init` authors MUST be UTF-8 without BOM, `\n` line endings,
  ASCII-safe (Principle IX), and respect the Windows 260-char path limit.
- **FR-015**: The `compass.yaml` (and any manifest `init` writes) MUST be a
  PROJECTION of a single canonical kit source, so a later drift linter can verify
  projection-matches-source; `init` MUST NOT introduce a second source of truth for
  the verb list or hard-stops.

### Key Entities *(include if feature involves data)*

- **`compass.yaml` (kit router)**: harness-neutral declaration of what verbs exist,
  what each is for, the hard-stops the agent must respect, and which harness
  integrations are wired. Stores NO stage. Buys Codex/Claude parity.
- **Fenced generated region**: the delimited `<!-- SESHAT-KIT START -->...END -->`
  block in `AGENTS.md` / `CLAUDE.md` that `init` owns; everything outside is
  hand-authored / constitution-owned and exempt.
- **Worked example (reference pattern)**: `c086-pharmacy` (build-to-Gold) or
  `retail-store-sales` (full seven-stage spine) -- a narrative shape to steer by,
  presented at first arrival BY `first-hour-compass` (which `init` delegates to),
  never copied as files.
- **`first-hour-compass` (delegated first-arrival)**: the EXISTING skill that owns
  the worked-example offer + the single-source human-seam list + single-table
  orientation card; `init` routes into it rather than restating it (anti-fork).
- **`retail-onboard-table` (delegated profiling front door)**: the EXISTING Source
  -> Mapping onboarding verb that owns the Stage-1 read-only DB-backed profile
  (grain candidates + column types via `profile.py`); the agent routes into it for
  the first result. Listed in the compass `verbs[]` so it is discoverable. `init`
  never reimplements it and never opens a DB.
- **Per-table readiness state**: `readiness-status.yaml` -- the EXISTING per-table
  work-state the compass points at; `init` reads/points, never stores a duplicate.
- **Canonical kit source**: the single committed source the compass + manifests are
  projected from; downstream of the constitution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who invokes the `init` skill on a repo with a real source table
  AND a reachable DB reaches a first profile result (grain candidates + column types)
  for THEIR table, produced by the agent executing `retail-onboard-table`, with zero
  user-facing "substrate" steps. Without a reachable DB, the flow instead reaches the
  source-map / orientation structure + `[PENDING LIVE PROFILE]` (SC-005) -- never a
  fabricated profile. (No CSV/Excel profiler is in scope; the only profiler is
  DB-backed.)
- **SC-002**: After `init`, 100% of lines outside the `SESHAT-KIT` fence in
  `AGENTS.md` / `CLAUDE.md` are byte-identical to before the run (a diff limited to
  the fenced region).
- **SC-003**: A re-run of `init` on an already-bootstrapped repo produces zero
  duplicated fences, zero clobbered hand-authored lines, and reports "already
  bootstrapped".
- **SC-004**: `compass.yaml` contains no `current_stage` / run-state field (a
  structural check), and its verb list + hard-stops match the canonical source (a
  projection-drift check passes).
- **SC-005**: When the live boundary is absent, `init` completes with profile numbers
  marked `[PENDING LIVE PROFILE]` and a non-error exit -- never a traceback, never a
  fabricated pass.
- **SC-006**: The `init` flow surfaces the human-owned judgment seams (as stated by
  `first-hour-compass`, its single source -- not a divergent list) and the
  agent-handles-plumbing / user-owns-judgment statement before the profile step, on
  every first run.
- **SC-007**: An agent reading only `.seshat/compass.yaml` (no other file) can
  enumerate the verbs and the hard-stops it must respect -- demonstrating
  harness-neutral orientation (Codex parity premise).
- **SC-008**: The first-arrival worked-example offer exists in exactly ONE place
  (`first-hour-compass`); `init` contains no restated copy of the offer table or the
  pick logic (an anti-fork check -- no second source of truth).

## Assumptions

- The two worked examples (`docs/worked-examples/c086-pharmacy.md`,
  `retail-store-sales.md`) remain committed and are the reference patterns `init`
  offers.
- The `first-hour-compass` -> `retail-onboard-table` verb chain remains the
  first-arrival + profiling front door the agent routes into; `init` does not own
  profiling logic. `profile.py` (DB-backed) remains the only profiler; no CSV/Excel
  profiler is built (YAGNI).
- The speckit fence pattern already shipped in `CLAUDE.md`
  (`<!-- SPECKIT START -->...END -->`) is the proven precedent for the
  `SESHAT-KIT` fence; no new fence design is needed.
- The Codex parity premise (Codex drives via the `AGENTS.md` convention) holds as
  stated in `distribution-ideas.md`; the harness-neutral router is useful regardless
  of whether Codex later gains a skill layer.
- Kit self-update (`sync`, three-way merge, release notes) and channel-driven fetch
  are LATER, gated slices (Phase-3 / Phase-4) and are explicitly out of scope here.
- This feature advances NO readiness stage and takes NO roadmap F-row by itself
  (YAGNI; it is kit-bootstrap infrastructure, not a per-table readiness step),
  matching how `manifest.py` / `severity_posture.py` / `scaffold.py` sit outside the
  stage sequence.
