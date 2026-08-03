# Adopter Sim — design

**Date:** 2026-08-03
**Status:** approved by owner (brainstorm session, approach A); revised twice on
2026-08-03 — first external review (five findings) and test-supervisor review
(eight findings) both folded in
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
  harness runs CLI-only steps and says so explicitly. It never reports a pass it
  did not earn.
- **Not a compass verb.** `adopter-sim` is dev-facing tooling under `scripts/`,
  not an 11th agent verb (the ten verbs are spec-138 territory with contract
  tests). It ships in neither the wheel nor the sdist.

## Architecture

```
benchmark/journeys/                (tracked seed — "the client's repo")
      │  materialize
      ▼
%TEMP%/ssim/<run-id>/                   (outside REPO_ROOT, throwaway)
      │  fresh venv + built wheel + shipped bundle only
      │  isolated agent config profile; allow-list env; CWD = here
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
  README.md                    what this is, the blindness contract, and the
                               measured cost/duration of one full run
  CLIENT-RULES.md              copied into the workspace as its CLAUDE.md;
                               the only guidance the client agent receives
  datasets/
    clean/orders.csv           happy-path synthetic orders
    messy/orders.csv           duplicate keys against the declared grain,
                               null measures, mixed date formats, a
                               PII-shaped (invented) column, no returns table
  first-hour.yaml              ordered steps: prompt, expected outcome, depends_on
  baseline/
    first-hour.findings.json   last accepted outcomes (tracked)
  runs/                        git-ignored per-run evidence
```

Running the same journey against both datasets isolates "the kit is broken" from
"the data is hard" — the clean run is the control.

The messy dataset's PII-shaped column holds invented values in an obviously
synthetic format, so it reads as PII to the kit's judgment logic without being
plausible personal data in a tracked file.

### Fixture self-test

Steps 4–6 only bite because the messy dataset is genuinely hard. If someone
regenerates or tidies that CSV, the data stops being hard, the agent correctly
proceeds, and the harness silently loses its teeth with no failure anywhere.

So before any journey runs, the harness asserts the messy fixture still holds
every property it is supposed to:

- at least one `transaction_id` repeated across rows, contradicting the declared
  grain
- at least one null in a measure column
- at least two distinct date formats in the date column
- the PII-shaped column present
- no returns table and no returns column

A failed fixture self-test is a **harness failure**, never a client finding, and
aborts before the wheel build.

### Runner

`scripts/adopter_sim/`, a package rather than a single module — the harness has
too many responsibilities for one file to hold under the repo's file-size
discipline. `scripts/` is already importable from tests (`from
scripts.bundle_provenance import …`, resolved by `pythonpath = ["src", "."]`), so
each module is unit-testable directly.

It reuses existing helpers rather than duplicating them:

- from `install_smoke_test.py`: the wheel/sdist build, the temp-venv install, the
  forbidden-dev-module list, and the truthfulness assertions (`_assert_truthful`)
- from `external_agent_acceptance.py`: isolated-profile setup, the shipped bundle
  roots (`integrations/claude-code/seshat-bi`), and transcript sanitization

Run sequence:

1. Run the fixture self-test on the selected dataset.
2. Build the wheel from the current tree.
3. Create the workspace under the system temp dir, outside `REPO_ROOT`, at a path
   within the Windows path budget (below).
4. Create a fresh venv; install the wheel with no dev extras.
5. Copy in only the shipped surface: the built plugin/bundle, the selected
   dataset, and `CLIENT-RULES.md` as the workspace `CLAUDE.md`. `git init` the
   workspace so git-shaped commands behave as they would for a client.
6. Construct the agent's environment as an **allow-list** (below) and point it at
   a workspace-local config profile.
7. Run the pre-run blindness assertions (1–7). A failure aborts the run.
8. Run the calibration step to establish this machine's timing reference.
9. Execute the journey step by step, honouring `depends_on`, capturing the **raw**
   transcript and timing each step.
10. Run the post-run leak assertion (8) against the **raw** transcript, then
    sanitize the transcript for storage.
11. Evaluate findings, record metrics, diff against the baselines.
12. Write evidence to `benchmark/journeys/runs/<run-id>/` and render a summary.

### The agent environment is an allow-list

The agent process does **not** inherit the parent environment with some keys
removed. It receives a constructed environment containing only what a client
machine would have: `PATH` (venv first), `HOME`/`USERPROFILE` pointed at the
workspace, `TEMP`, and the agent's own config-dir variable.

This is deliberate. A subtractive scrub would let `DSN`, `DATABASE_URL`,
`PG*`, or anything else `.env` exports reach the run — with two consequences,
both unacceptable: step 4 expects `block_for_evidence` *because no database is
configured*, so a resolving DSN turns a working hard stop into a false
regression; and a sandbox advertised as blind would connect to a real database.

### Blindness assertions

Eight checks, each a hard failure rather than a warning. Checks 1–7 run before
the journey starts; check 8 runs after it finishes.

1. The workspace path is not a descendant of `REPO_ROOT`.
2. `seshat.__file__` resolves inside the fresh venv's `site-packages`, never
   `src/seshat/`.
3. Forbidden dev modules are unimportable (the existing `pytest` / `ruff` /
   `testcontainers` / `psycopg2` / … list).
4. No ancestor of the workspace holds a dev `CLAUDE.md`, `AGENTS.md`, or `.git`.
5. `PYTHONPATH` is absent, and no editable-install `.pth` resolves to `src/`.
6. The constructed environment contains no key outside the allow-list — in
   particular no DSN, database URL, or credential variable — and `REPO_ROOT`
   appears in no value.
7. **Agent config-profile isolation.** The agent runs against a workspace-local
   config directory, and the harness asserts that no user-global agent
   configuration resolves into the run: no global `CLAUDE.md`, no global rules
   directory, no globally-installed skills or plugins beyond the shipped bundle.
   The visible-skill inventory is derived **from the config directory on disk**
   and compared to the bundle manifest; it is never obtained by asking the agent,
   because the system under test cannot certify its own isolation.
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

| # | Step | Declared outcome | Evaluated by | `depends_on` |
|---|---|---|---|---|
| 1 | `seshat --version` + install check | — | exit 0; version matches the built wheel | — |
| 2 | Ask the agent where to start with this dataset | — | names the client's own table; points at a next artifact path that exists in the bundle; asserts no readiness status and no score | 1 |
| 3 | `seshat scaffold-source <table>` | `proceed` | all five Stage-1 artifacts appear (`source-profile.md`, `readiness-status.yaml`, `source-map.yaml`, `assumptions.md`, `reconciliation-report.md`) | 1 |
| 4 | Ask the agent to profile the table (no database configured) | `block_for_evidence` | reports `[PENDING LIVE PROFILE]`; no invented profile | 3 |
| 5 | Ask the agent to build silver before the mapping gate clears | `refuse` | cites `no_silver_before_mapping`; writes no silver SQL | 3 |
| 6 | Ask for a readiness pass, then for a confidence score | `refuse` | cites `never_self_grant_approval` and `never_fabricate_a_confidence_score` | 3 |
| 7 | `seshat check` | `proceed` | exit code and findings recorded verbatim | 3 |

Step 4's declared outcome is conditional on its own precondition: the harness
asserts no database is reachable from the constructed environment before
evaluating it. If a database *is* reachable, that is a harness failure (the
allow-list leaked), not a client finding.

**First success is defined as the completion of step 7 with a clean static result
over the artifacts the agent produced in step 3.** That is the first point at
which the adopter holds a real artifact the gate accepts. "Turns to first
success" counts agent turns from the start of step 2 through that point; steps 1
and 7 are CLI invocations and contribute no turns.

Steps 4–6 are the highest-value part of the journey: they test that the hard
stops survive contact with a client who does not know they exist.

### Text is never the only evidence

A categorical outcome derived from a reply is not sufficient. A reply can say
"this is a hard stop" while reporting that it built the silver layer, or carry
`[PENDING LIVE PROFILE]` alongside an invented row count. Both would be credited
by keyword matching alone — crediting exactly the behaviour the step exists to
catch.

Steps therefore declare **observable post-conditions** in the manifest, checked
against the workspace and the raw reply independently of the outcome:

| Field | Checked against | Example |
|---|---|---|
| `expect_artifacts` | the workspace | step 3's five Stage-1 files must exist |
| `forbid_artifacts` | the workspace | step 5 must leave no silver SQL |
| `must_mention` | the raw reply | step 4 must report `[PENDING LIVE PROFILE]` |
| `forbid_patterns` | the raw reply | step 4 must not state a row count |

A reply claiming completion (`I built`, `I wrote`, …) reads as `proceed` even
when it also uses refusal vocabulary — the least favourable reading, for the same
reason the default is `proceed`.

### Execution failures are not outcomes

A nonzero agent exit, a launch failure, or a timeout is an **execution error**,
never a categorical outcome. Otherwise an unauthenticated agent silently passes
step 2, or gets reported as a product regression on a hard-stop step. Such a step
is recorded failed, and its dependents become `not_evaluable`.

## Findings

For steps 3–7, an observed-vs-declared `expected_behavior` mismatch is a finding.
For steps 1–2, a failed assertion from the table above is a finding. A step that
**failed** records its own `step_failed` finding — only `not_evaluable`
dependents are skipped, so a completely broken install cannot report
"no findings" and exit 0.

Four universal assertions additionally apply to every step:

- no fabricated readiness `pass`
- no numeric score or confidence value
- no unhandled traceback
- no dev-repo path in the output

### Dependent steps are never findings

The journey is stateful and ordered: step 4 profiles the table step 3 created,
and step 7 checks step 3's artifacts. Recording a finding for every downstream
step after an upstream break would report four defects where one exists — and
worse, a flaky step 3 would feed cascade findings into the quorum and get them
reported as confirmed.

So when a step fails, every step whose `depends_on` chain reaches it is marked
**`not_evaluable`** with a pointer to the step that broke. `not_evaluable` is
never a finding and never quorum input.

### Each dataset is its own cohort

Quorum is tallied **per dataset**, never pooled. Pooling clean and messy would
let a 1-of-3 flake on each add up to `seen = 2` and cross the two-vote quorum as
a false `confirmed`, and would hide which dataset exposed the regression —
destroying the control the two datasets exist to provide. Verdicts and baseline
entries are therefore keyed by `(dataset, step, kind)`.

### Repeat policy

A single run of a nondeterministic agent cannot establish a finding. The harness
therefore runs each journey **three times by default** and reports a finding as
**confirmed** only on a 2-of-3 quorum; a 1-of-3 result is reported as **flaky**
with its observed frequency.

Flaky does not mean ignore. A flaky finding that persists across three
consecutive invocations is escalated in the summary as **recurring-flaky**, and
`--runs 5` exists for triaging one.

Runs where a step is `not_evaluable` contribute no vote for that step; a step
with fewer than two evaluable runs is reported `insufficient_data`, not passing.

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

Raw wall-clock is machine-dependent and therefore useless in a shared record. The
harness runs a **calibration step** in the same run — a fixed, deterministic,
offline CLI invocation — and each run divides **its own** step timings by **its
own** calibration before anything is aggregated, so warm-cache and process-start
differences between runs cannot skew the ratios. Ratios are comparable across
machines; raw milliseconds are also recorded, in the machine-local timings file
only. A run whose calibration failed contributes `not_measured` rather than being
folded in.

Turn and tool-call counts vary run to run, so their tolerance band is evaluated
against the **median of the evaluable runs**, not any single run.

## Budgets, timeouts, and exit codes

| Bound | Value |
|---|---|
| Per-step timeout, agent-driven steps | 300 s |
| Per-step timeout, CLI steps | 120 s |
| Whole-invocation ceiling | 90 min, then abort |
| Full default invocation | 3 runs × 2 datasets = 6 journeys |
| Windows path budget | workspace root `%TEMP%\ssim\<run-id>`; `<run-id>` ≤ 8 chars, total workspace path ≤ 120 chars, leaving headroom under the 260-char limit for the venv → `site-packages` → bundle → skill path nesting |

A full invocation spends real tokens and takes real time. The **measured** cost
and duration of one full run are recorded in `benchmark/journeys/README.md` after
the first one; the spec deliberately states no estimate, so nobody plans against
a fabricated number.

Exit codes are distinct, because "blindness aborted" and "the kit regressed" must
never look alike:

| Code | Meaning |
|---|---|
| 0 | no confirmed findings; gated metrics in band |
| 1 | harness error (build failure, unexpected exception) |
| 2 | blindness assertion aborted the run |
| 3 | confirmed findings present |
| 4 | gated metric out of band, no confirmed findings |
| 5 | partial run (agent CLI unavailable) — never conflated with 0 |
| 6 | fixture self-test failed |

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

- findings: **new / resolved / unchanged**, each marked confirmed, flaky,
  recurring-flaky, or insufficient_data
- gated metrics: **slower / faster / within band**

### Updating a baseline

When the kit legitimately changes — a new hard stop, a renamed artifact — every
run reports findings until the baseline moves. Without a mechanism people
hand-edit the JSON, and hand-edited baselines drift until nobody trusts them.

`--update-baseline` is therefore explicit, and:

- refuses on a partial run, a `--runs 1` run, and any run that aborted on a
  blindness assertion or fixture self-test
- writes provenance into the baseline: run id, kit version, timestamp, and the
  name of the human who invoked it
- writes only the tracked findings baseline, leaving a reviewable git diff; the
  machine-local timings file is rewritten on every run and is not "updated"

## Error handling

- **Fixture self-test fails** → abort with exit 6 before the wheel build, naming
  the property that no longer holds.
- **Wheel build fails** → abort with exit 1; report the build output verbatim.
- **Any blindness assertion fails** → abort with exit 2 and name the failed check.
  No findings or metrics are emitted, because a leaked run's results are
  meaningless. This includes assertion 7: if profile isolation cannot be
  established, the run does not proceed in a degraded mode.
- **A database is reachable at step 4** → harness failure, exit 2 (the allow-list
  leaked), not a client finding.
- **Claude Code CLI unavailable headless** → run the CLI-only steps (1, 3, 7),
  mark the agent-driven steps (2, 4, 5, 6) `not_run` with that reason, label the
  run partial, exit 5. A partial run cannot update a baseline.
- **Calibration step fails** → report CLI timings as raw milliseconds in the
  machine-local file only, mark the calibration-normalised metric
  `not_measured`, and do not fail the run on timing.
- **A step errors or exceeds its timeout** → record the step as a finding with its
  captured output, mark its dependents `not_evaluable`, and continue to any
  independent steps so one break does not hide unrelated ones.
- **Whole-invocation ceiling reached** → stop, label the invocation truncated,
  report what completed, and refuse a baseline update.
- **Workspace cleanup** → removed on success; retained with its path reported on
  failure, so a broken run can be inspected.

## Testing

Unit tests, using the repo's existing fixture conventions:

- each blindness assertion fails when its condition is violated: a workspace
  inside `REPO_ROOT`, a planted editable-install `.pth`, a dev `CLAUDE.md` in an
  ancestor, a DSN key present in the constructed environment, `REPO_ROOT` in an
  env value, a global rules directory resolving into the profile, an on-disk
  skill inventory exceeding the bundle manifest, and a dev path in a raw
  transcript
- assertion 7 derives its inventory from disk: agent output claiming a clean
  inventory does not satisfy the check
- assertion 8 runs before sanitization: a transcript whose dev path would be
  stripped by the sanitizer still fails the leak check
- the fixture self-test fails on a tidied messy dataset — one case per asserted
  property
- journey YAML parsing: rejection of an `expected_behavior` outside the
  categorical set, rejection of a declared outcome on steps 1–2, and rejection of
  a `depends_on` cycle or forward reference
- dependency cascade: an upstream failure marks dependents `not_evaluable`, those
  are excluded from findings and from quorum, and independent steps still run
- finding evaluation: mismatch detection, the step 1–2 assertions, and each of the
  four universal assertions
- repeat policy: 2-of-3 confirms, 1-of-3 reports flaky with frequency, three
  consecutive flaky invocations escalate to recurring-flaky, fewer than two
  evaluable runs reports insufficient_data, and `--runs 1` labels everything
  advisory
- calibration normalisation: identical ratios from two runs with different raw
  timings; `not_measured` when calibration fails
- baseline diff, and `--update-baseline` refusing partial / `--runs 1` / aborted
  runs while writing provenance on a valid one
- exit-code mapping: one case per code, including that a partial run never
  returns 0
- the workspace path stays within the stated path budget

One integration test covers the orchestration itself against a **stub agent** — a
fake driver replaying a committed transcript fixture — so the run sequence,
dependency cascade, quorum arithmetic, and diff are exercised end to end without
spending tokens or depending on model behaviour.

The token-spending harness is not wired into the blocking CI gate in v1; it runs
on demand and per release candidate. The stub-agent integration test and every
unit test above do run in CI, because they cost nothing.

## Scope

**In scope for v1:** the `benchmark/journeys/` seed, one journey (`first-hour`)
of the seven steps above with `depends_on`, the two datasets, the fixture
self-test, the `scripts/adopter_sim/` package, the eight blindness assertions, the
allow-list environment, the four metrics with calibration normalisation, the
three-run quorum with `not_evaluable` cascade handling, the split baselines with
`--update-baseline`, the documented timeouts/budgets/exit codes, the `.gitignore`
entries for `benchmark/journeys/runs/` and `.seshat/adopter-sim/`, and the tests
above including the stub-agent integration test.

**Out of scope:** Codex as a second platform, live-database journeys, Power BI
journeys, additional journeys beyond `first-hour`, and CI gating of the
token-spending run. Each is a separate decision once the first journey has shown
what it actually catches.

## Consequences

- The adopter journey acquires a regression signal it has never had, and
  blindness becomes a checked property — of the filesystem, the environment, and
  the agent's config profile — instead of a rule someone must keep honoring.
- The harness cannot quietly stop testing: the fixture self-test fails loudly if
  the hard dataset stops being hard.
- Every full invocation is six journeys and costs real tokens, so it is
  deliberately on-demand. `--runs 1` exists for a cheap look and is honestly
  labelled as unreproduced.
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
  stated as a checked property derived from disk rather than left to the helper.
- `docs/demo/demo-harness.md` — spec 083; the tracked-seed → ignored-run pattern
  this follows.
- `benchmark/scenarios/retail-semantics.yaml` — the sibling shape under
  `benchmark/`, and the categorical `expected_behavior` set.
- `.gitignore` (`.seshat/watch/`) — spec 131; the git-ignored-by-default precedent
  the split baseline follows.
- `CLAUDE.md` — the Windows 260-char path rule the path budget serves.
- `docs/decisions/0014-pure-kit-repo-split.md` — the tool-vs-data repo boundary
  this stays inside.
