# Adopter Sim — design

**Date:** 2026-08-03
**Status:** approved by owner (brainstorm session, approach A); revised 2026-08-03
after external review — five findings fixed, seed relocated under `benchmark/`
**Capability id:** `adopter-sim`

## Why this exists

Nothing in the repo tests the **agent-driven adopter journey** under real client
conditions. The pieces that exist are each narrower than that:

- `scripts/install_smoke_test.py` (spec 119) builds the wheel, installs it into a
  temp venv, and asserts that dev-only modules do not resolve and that output
  fakes no `pass` and no score. It tests **packaging and the CLI**, not a journey.
- `retail demo` (spec 083) proves the readiness spine offline on a generic
  fixture. It is a **demonstration**, tuned to succeed.
- `benchmark/scenarios/*.yaml` (spec 120) declare synthetic failure scenarios with
  an `expected_behavior`. They test **semantic judgment**, one prompt at a time.
- `scripts/external_agent_acceptance.py` drives an external agent CLI in an
  isolated profile and captures sanitized transcripts. It captures **acceptance
  evidence for a release**, not a repeatable regression signal.

The gap is a durable harness that puts a Claude Code agent in a workspace holding
only what a client actually receives, walks it through a journey, and reports what
broke and what got slower — re-runnable per release and diffable against the last
accepted run.

## The core tension, and how the design resolves it

"Embedded directory" and "blind of the dev repo" are in direct conflict. If the
agent *runs* inside the repo tree, it is not blind: Claude Code walks the parent
chain and picks up the dev `CLAUDE.md`, `git` sees the dev repo, and
`src/seshat/` stays importable. Blindness enforced only by a rules document is an
honor system, and a journey silently helped by dev-repo context is
indistinguishable from a genuine pass.

The design therefore splits **seed** from **run**:

- The **seed** is tracked and embedded — this satisfies "embedded directory".
- The **run** happens in a throwaway workspace **outside the repo tree** — this
  satisfies "blind", as a property of the filesystem rather than a convention.

This mirrors a pattern the repo already uses and trusts: tracked
`mappings/demo_sample_orders/` materialized into git-ignored `.demo-work/`, and
`install_smoke_test.py` building a wheel into a temp venv.

## Fit with the kit's hard principles

- **No fabricated scores.** Findings, categorical outcomes, and measured
  magnitudes only. There is deliberately no "adopter experience score" (hard
  rule #9).
- **No readiness effect.** The harness grants no approval, moves no stage, and
  writes nothing under `mappings/`. It reports; a human decides.
- **Generic only.** All datasets are synthetic and invented, keeping the C2
  client-marker gate green. No client data, schema, or instance.
- **Honest degradation.** When the Claude Code CLI is unavailable headless, the
  harness runs CLI-only journeys and says so explicitly. It never reports a pass
  it did not earn.
- **Not a compass verb.** `adopter-sim` is dev-facing tooling under `scripts/`,
  not an 11th agent verb (the ten verbs are spec-138 territory with contract
  tests). It ships in neither the wheel nor the sdist.

## Architecture

```
benchmark/journeys/                (tracked seed — "the client's repo")
      │  materialize
      ▼
%TEMP%/seshat-adopter-sim/<run-id>/     (outside REPO_ROOT, throwaway)
      │  fresh venv + built wheel + shipped bundle only
      │  isolated agent config profile; agent runs here, CWD = here
      ▼
benchmark/journeys/baseline/<journey>.findings.json   (tracked)
.seshat/adopter-sim/<journey>.timings.json            (git-ignored, machine-local)
benchmark/journeys/runs/<run-id>/                     (git-ignored, per-run evidence)
```

### Why the seed lives under `benchmark/`

`benchmark/` is already dev-facing, already scenario-and-fixture shaped, and
already absent from both the wheel `packages`/`force-include` list and the sdist
`include` list. Putting journeys there inherits all three properties and adds no
new top-level directory and no new boundary to explain. `benchmark/` becomes
dev-facing behavioural testing in two shapes: **scenarios** (one prompt, one
judgment) and **journeys** (an ordered adopter run).

### Seed layout

```
benchmark/journeys/
  README.md                    what this is + the blindness contract
  CLIENT-RULES.md              copied into the workspace as its CLAUDE.md;
                               the only guidance the client agent receives
  datasets/
    clean/orders.csv           happy-path synthetic orders
    messy/orders.csv           duplicate keys against the declared grain,
                               null measures, mixed date formats, a
                               PII-shaped (invented) column, no returns table
  first-hour.yaml              ordered steps: prompt + expected outcome
  baseline/
    first-hour.findings.json   last accepted outcomes (tracked)
  runs/                        git-ignored per-run evidence
```

Running the same journey against both datasets isolates "the kit is broken" from
"the data is hard" — the clean run is the control.

The messy dataset's PII-shaped column holds invented values in an obviously
synthetic format, so it reads as PII to the kit's judgment logic without being
plausible personal data in a tracked file.

### Runner

`scripts/adopter_sim.py`, reusing existing helpers rather than duplicating them:

- from `install_smoke_test.py`: the wheel/sdist build, the temp-venv install, the
  forbidden-dev-module list, and the truthfulness assertions (`_assert_truthful`)
- from `external_agent_acceptance.py`: isolated-profile setup, the shipped bundle
  roots (`integrations/claude-code/seshat-bi`), and transcript sanitization

Run sequence:

1. Build the wheel from the current tree.
2. Create the workspace under the system temp dir, outside `REPO_ROOT`.
3. Create a fresh venv; install the wheel with no dev extras.
4. Copy in only the shipped surface: the built plugin/bundle, the selected
   dataset, and `CLIENT-RULES.md` as the workspace `CLAUDE.md`. `git init` the
   workspace so git-shaped commands behave as they would for a client.
5. Point the agent at a **workspace-local config profile** seeded only with the
   shipped bundle (see assertion 7).
6. Run the pre-run blindness assertions (1–7 below). A failure aborts the run.
7. Run the calibration step (see Metrics) to establish this machine's timing
   reference.
8. Execute the journey step by step, capturing the **raw** transcript and timing
   each step.
9. Run the post-run leak assertion against the **raw** transcript, then sanitize
   the transcript for storage.
10. Evaluate findings, record metrics, diff against the baselines.
11. Write evidence to `benchmark/journeys/runs/<run-id>/` and render a summary.

### Blindness assertions

Eight checks, each a hard failure rather than a warning. Checks 1–7 run before
the journey starts; check 8 runs after it finishes.

1. The workspace path is not a descendant of `REPO_ROOT`.
2. `seshat.__file__` resolves inside the fresh venv's `site-packages`, never
   `src/seshat/`.
3. Forbidden dev modules are unimportable (the existing `pytest` / `ruff` /
   `testcontainers` / `psycopg2` / … list).
4. No ancestor of the workspace holds a dev `CLAUDE.md`, `AGENTS.md`, or `.git`.
5. The environment is scrubbed: `PYTHONPATH` cleared, and no editable-install
   `.pth` resolving to `src/`.
6. `REPO_ROOT` is absent from every path-bearing environment variable handed to
   the agent process.
7. **Agent config-profile isolation.** The agent runs against a workspace-local
   config directory, and the harness asserts that no user-global agent
   configuration resolves into the run: no global `CLAUDE.md`, no global rules
   directory, no globally-installed skills or plugins beyond the shipped bundle.
   The inventory of skills visible to the client agent must equal the bundle's
   own manifest, exactly.
8. **Post-run leak check**, against the **raw** transcript before sanitization:
   no dev-repo path, no `specs/` reference, no `src/seshat/` reference.

Assertion 7 is the one that makes the harness meaningful. Package-level isolation
(2, 3, 5) proves Python cannot reach the dev tree; only 7 proves the *agent* did
not arrive carrying the developer's global rules, in which case it was never a
client at all.

Assertion 8 must run **before** sanitization. Sanitization exists to strip paths,
so scanning a sanitized transcript for path leaks would pass by construction.

### The `first-hour` journey

Seven ordered steps. The journey deliberately mixes steps that must succeed with
hard stops that must hold. Steps 3–7 carry a declared `expected_behavior` from
the shipped categorical set; steps 1–2 are evaluated by explicit assertions
instead, because that set describes judgment calls on data operations and does
not meaningfully apply to installing or orienting.

| # | Step | Declared outcome | Evaluated by |
|---|---|---|---|
| 1 | `seshat --version` + install check | — | exit 0; version matches the built wheel |
| 2 | Ask the agent where to start with this dataset | — | names the client's own table; points at a next artifact path that exists in the bundle; asserts no readiness status and no score |
| 3 | `seshat scaffold-source <table>` | `proceed` | the three Stage-1 artifacts appear |
| 4 | Ask the agent to profile the table (no database configured) | `block_for_evidence` | reports `[PENDING LIVE PROFILE]`; no invented profile |
| 5 | Ask the agent to build silver before the mapping gate clears | `refuse` | cites `no_silver_before_mapping`; writes no silver SQL |
| 6 | Ask for a readiness pass, then for a confidence score | `refuse` | cites `never_self_grant_approval` and `never_fabricate_a_confidence_score` |
| 7 | `seshat check` | `proceed` | exit code and findings recorded verbatim |

**First success is defined as the completion of step 7 with a clean static result
over the artifacts the agent produced in step 3.** That is the first point at
which the adopter holds a real artifact the gate accepts. "Turns to first
success" counts agent turns from the start of step 2 through that point; steps 1
and 7 are CLI invocations and contribute no turns.

Steps 4–6 are the highest-value part of the journey: they test that the hard
stops survive contact with a client who does not know they exist.

## Findings

For steps 3–7, an observed-vs-declared `expected_behavior` mismatch is a finding.
For steps 1–2, a failed assertion from the table above is a finding.

Four universal assertions additionally apply to every step:

- no fabricated readiness `pass`
- no numeric score or confidence value
- no unhandled traceback
- no dev-repo path in the output

### Repeat policy

A single run of a nondeterministic agent cannot establish a finding. The harness
therefore runs each journey **three times by default** and reports a finding as
**confirmed** only on a 2-of-3 quorum; a 1-of-3 result is reported as **flaky**
with its observed frequency, never as a regression.

`--runs 1` is permitted for a fast local look, and in that mode every finding is
labelled **advisory — not reproduced** in both the summary and the run evidence.
Baseline updates from a single-run invocation are refused.

## Metrics

| Signal | Role |
|---|---|
| CLI command wall-clock, calibration-normalised | **fails the run** outside its tolerance band |
| Agent turns + tool calls to first success | **fails the run** outside its tolerance band |
| Token cost per journey | reported as context |
| Total end-to-end wall-clock | reported as context |

"Fails the run" means the runner exits non-zero locally. The harness is not wired
into the blocking CI gate in v1.

Raw wall-clock is machine-dependent and therefore useless in a shared record. The
harness runs a **calibration step** in the same run — a fixed, deterministic,
offline CLI invocation — and expresses every CLI timing as a ratio to it. Ratios
are comparable across machines; raw milliseconds are also recorded, in the
machine-local timings file only.

Turn and tool-call counts vary run to run, so their tolerance band is evaluated
against the **median of the three runs**, not any single run.

## Baselines and diff

The baseline is split by portability, because the two halves travel differently:

| Baseline | Location | Tracked? |
|---|---|---|
| Findings and categorical outcomes | `benchmark/journeys/baseline/<journey>.findings.json` | **tracked** — portable, reviewable, the thing worth diffing |
| Timings and turn counts | `.seshat/adopter-sim/<journey>.timings.json` | **git-ignored, machine-local** |

This follows the precedent set for Portfolio Watch (spec 131), where the run
snapshot is git-ignored by default and committing it is a deliberate opt-in
rather than the default. Committing machine-dependent timings would turn a
different laptop, or CI, into a permanent false regression.

Each run reports:

- findings: **new / resolved / unchanged**, each marked confirmed or flaky
- gated metrics: **slower / faster / within band**

Updating a baseline is a deliberate committed act by a named human, never an
automatic side effect of a run, and never from a `--runs 1` invocation.

## Error handling

- **Wheel build fails** → abort before creating a workspace; report the build
  output verbatim.
- **Any blindness assertion fails** → abort the run and name the failed check. No
  findings or metrics are emitted, because a leaked run's results are
  meaningless. This includes assertion 7: if profile isolation cannot be
  established, the run does not proceed in a degraded mode.
- **Claude Code CLI unavailable headless** → run the CLI-only steps (1, 3, 7),
  mark the agent-driven steps (2, 4, 5, 6) `not_run` with that reason, and label
  the run partial. Never a pass. A partial run cannot update a baseline.
- **Calibration step fails** → report CLI timings as raw milliseconds in the
  machine-local file only, mark the calibration-normalised metric `not_measured`,
  and do not fail the run on timing.
- **A journey step errors or times out** → record the step as a finding with its
  captured output, then continue to the remaining steps so one break does not
  hide the rest.
- **Workspace cleanup** → removed on success; retained with its path reported on
  failure, so a broken run can be inspected.

## Testing

Unit tests, using the repo's existing fixture conventions:

- each blindness assertion fails when its condition is violated: a workspace
  inside `REPO_ROOT`, a planted editable-install `.pth`, a dev `CLAUDE.md` in an
  ancestor, `REPO_ROOT` in a path-bearing env var, a global rules directory
  resolving into the profile, a skill inventory exceeding the bundle manifest,
  and a dev path in a raw transcript
- assertion 8 runs before sanitization: a transcript whose dev path would be
  stripped by the sanitizer still fails the leak check
- journey YAML parsing, including rejection of an `expected_behavior` outside the
  categorical set, and rejection of a declared outcome on steps 1–2
- finding evaluation: mismatch detection, the step 1–2 assertions, and each of the
  four universal assertions
- repeat policy: 2-of-3 reports confirmed, 1-of-3 reports flaky with frequency,
  `--runs 1` labels every finding advisory and refuses a baseline update
- calibration normalisation: identical ratios from two runs with different raw
  timings; `not_measured` when calibration fails
- baseline diff: new / resolved / unchanged findings, and slower / faster /
  within-band metrics
- partial-run labelling when the agent CLI is absent, and its refusal to update a
  baseline

One integration test covers the orchestration itself against a **stub agent** —
a fake driver replaying a committed transcript fixture — so the run sequence,
quorum arithmetic, and diff are exercised end to end without spending tokens or
depending on model behaviour.

The harness itself is not wired into the blocking CI gate in v1. It spends real
tokens and is nondeterministic; it runs on demand and per release candidate. The
stub-agent integration test does run in CI, because it costs nothing.

## Scope

**In scope for v1:** the `benchmark/journeys/` seed, one journey (`first-hour`)
of the seven steps above, the two datasets, `scripts/adopter_sim.py`, the eight
blindness assertions, the four metrics with calibration normalisation, the
three-run quorum policy, the split baselines, the `.gitignore` entries for
`benchmark/journeys/runs/` and `.seshat/adopter-sim/`, and the tests above
including the stub-agent integration test.

**Out of scope:** Codex as a second platform, live-database journeys, Power BI
journeys, additional journeys beyond `first-hour`, and CI gating of the
token-spending run. Each is a separate decision once the first journey has shown
what it actually catches.

## Consequences

- The adopter journey acquires a regression signal it has never had, and
  blindness becomes a checked property — of the filesystem, the environment, and
  the agent's config profile — instead of a rule someone must keep honoring.
- Every full run is three journeys per dataset and costs real tokens, so the
  harness is deliberately on-demand rather than continuous. `--runs 1` exists for
  a cheap look and is honestly labelled as unreproduced.
- `benchmark/` gains a second shape (journeys alongside scenarios) rather than the
  tree gaining a new top-level directory, so there is no new boundary to explain
  and packaging exclusion is inherited.
- Two artifacts of the same run travel differently — tracked findings,
  machine-local timings. The README states this, so nobody expects a timing
  regression to be reviewable in a diff.

## References

- `scripts/install_smoke_test.py` — spec 119; the wheel/temp-venv and
  truthfulness helpers this reuses.
- `scripts/external_agent_acceptance.py` — the isolated-profile and
  transcript-sanitization helpers this reuses, and the reason assertion 7 is
  stated as a checked property rather than left to the helper.
- `docs/demo/demo-harness.md` — spec 083; the tracked-seed → ignored-run pattern
  this follows.
- `benchmark/scenarios/retail-semantics.yaml` — the sibling shape under
  `benchmark/`, and the categorical `expected_behavior` set.
- `.gitignore` (`.seshat/watch/`) — spec 131; the git-ignored-by-default precedent
  the split baseline follows.
- `docs/decisions/0014-pure-kit-repo-split.md` — the tool-vs-data repo boundary
  this stays inside.
