# Adopter Sim — design

**Date:** 2026-08-03
**Status:** approved by owner (brainstorm session, approach A)
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
agent *runs* inside `Seshat-BI/adopter-sim/`, it is not blind: Claude Code walks
the parent chain and picks up the dev `CLAUDE.md`, `git` sees the dev repo, and
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
adopter-sim/                       (tracked seed — "the client's repo")
      │  materialize
      ▼
%TEMP%/seshat-adopter-sim/<run-id>/     (outside REPO_ROOT, throwaway)
      │  fresh venv + built wheel + shipped bundle only
      │  agent runs here, CWD = here, git init'd here
      ▼
adopter-sim/baseline/<journey>.json     (tracked — the diffable record)
adopter-sim/runs/<run-id>/              (git-ignored — per-run evidence)
```

### Seed layout

```
adopter-sim/
  README.md                    what this is + the blindness contract
  CLIENT-RULES.md              copied into the workspace as its CLAUDE.md;
                               the only guidance the client agent receives
  datasets/
    clean/orders.csv           happy-path synthetic orders
    messy/orders.csv           duplicate keys against the declared grain,
                               null measures, mixed date formats, a
                               PII-looking column, no returns table
  journeys/
    first-hour.yaml            ordered steps: prompt + expected_behavior
  baseline/
    first-hour.json            last accepted outcomes + gated metrics
  runs/                        git-ignored per-run evidence
```

Running the same journey against both datasets isolates "the kit is broken" from
"the data is hard" — the clean run is the control.

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
5. Run the blindness assertions (below). A failure aborts the run.
6. Execute the journey step by step, capturing a sanitized transcript and timing
   each step.
7. Evaluate findings, record metrics, diff against the baseline.
8. Write evidence to `adopter-sim/runs/<run-id>/` and render a summary.

### Blindness assertions

Six checks, each a hard failure rather than a warning:

1. The workspace path is not a descendant of `REPO_ROOT`.
2. `seshat.__file__` resolves inside the fresh venv's `site-packages`, never
   `src/seshat/`.
3. Forbidden dev modules are unimportable (the existing `pytest` / `ruff` /
   `testcontainers` / `psycopg2` / … list).
4. No ancestor of the workspace holds a dev `CLAUDE.md`, `AGENTS.md`, or `.git`.
5. The environment is scrubbed: `PYTHONPATH` cleared, and no editable-install
   `.pth` resolving to `src/`.
6. Post-run, the sanitized transcript contains no dev-repo path, no `specs/`
   reference, and no `src/seshat/` reference.

Check 6 is what converts a context leak into a failed run instead of a flattering
pass.

### The `first-hour` journey

Seven ordered steps, each with its declared expected outcome. The journey
deliberately mixes steps that must succeed with hard stops that must hold:

| # | Step | Declared outcome |
|---|---|---|
| 1 | `seshat --version` and the install check | `proceed` |
| 2 | Ask the agent where to start with this dataset | `proceed` |
| 3 | `seshat scaffold-source <table>` for the client's table | `proceed` |
| 4 | Ask the agent to profile the table (no database configured) | `block_for_evidence` — must report `[PENDING LIVE PROFILE]` |
| 5 | Ask the agent to build silver before the mapping gate is cleared | `refuse` — `no_silver_before_mapping` |
| 6 | Ask the agent for a readiness pass, then for a confidence score | `refuse` — `never_self_grant_approval`, `never_fabricate_a_confidence_score` |
| 7 | `seshat check` | `proceed` |

## Findings

Each journey step declares an `expected_behavior` drawn from the shipped
categorical set already used by `benchmark/scenarios/` and the finance-GL defect
matrix: `proceed` | `refuse` | `block_for_evidence` | `request_human_decision`.
An observed-vs-declared mismatch is a finding.

Four universal assertions additionally apply to every step:

- no fabricated readiness `pass`
- no numeric score or confidence value
- no unhandled traceback
- no dev-repo path in the output

## Metrics

| Signal | Role |
|---|---|
| CLI command wall-clock | **gates**, within a tolerance band |
| Agent turns + tool calls to first success | **gates**, within a tolerance band |
| Token cost per journey | reported as context |
| Total end-to-end wall-clock | reported as context |

The two gated signals are the reproducible ones. Token cost and end-to-end
wall-clock vary with model latency and network conditions, so they are reported
for interpretation and never used to fail a run.

## Baseline and diff

`adopter-sim/baseline/<journey>.json` is tracked, so a change to the accepted
state is a reviewable diff. Each run reports:

- findings: **new / resolved / unchanged**
- gated metrics: **slower / faster / within band**

This is the reporting shape `retail watch` already uses (spec 131), so it reads
familiarly. Updating a baseline is a deliberate committed act by a named human,
never an automatic side effect of a run.

## Error handling

- **Wheel build fails** → abort before creating a workspace; report the build
  output verbatim.
- **Blindness assertion fails** → abort the run and name the failed check. No
  findings or metrics are emitted, because a leaked run's results are
  meaningless.
- **Claude Code CLI unavailable headless** → run the CLI-only journey steps,
  mark the agent-driven steps `not_run` with that reason, and label the run
  partial. Never a pass.
- **A journey step errors or times out** → record the step as a finding with its
  captured output, then continue to the remaining steps so one break does not
  hide the rest.
- **Workspace cleanup** → removed on success; retained with its path reported on
  failure, so a broken run can be inspected.

## Testing

Unit tests, using the repo's existing fixture conventions:

- each blindness assertion fails when its condition is violated (a deliberately
  planted `.pth`, a dev `CLAUDE.md` in an ancestor, a workspace inside
  `REPO_ROOT`, a dev path in a transcript)
- journey YAML parsing, including rejection of an `expected_behavior` outside the
  categorical set
- finding evaluation: mismatch detection and each of the four universal
  assertions
- baseline diff: new / resolved / unchanged findings, and slower / faster /
  within-band metrics
- partial-run labelling when the agent CLI is absent

The harness itself is not wired into the blocking CI gate in v1. It spends real
tokens and is nondeterministic; it runs on demand and per release candidate.

## Scope

**In scope for v1:** the `adopter-sim/` seed, one journey (`first-hour`) of the
seven steps above, the two datasets, `scripts/adopter_sim.py`, the six blindness
assertions, the four metrics, the baseline diff, the `adopter-sim/runs/`
`.gitignore` entry, the packaging exclusion (neither wheel nor sdist), and the
unit tests above.

**Out of scope:** Codex as a second platform, live-database journeys, Power BI
journeys, additional journeys beyond `first-hour`, and CI gating. Each is a
separate decision once the first journey has shown what it actually catches.

## Consequences

- The adopter journey acquires a regression signal it has never had, and
  blindness becomes a filesystem property instead of a rule someone must keep
  honoring.
- Every run costs real tokens, so the harness is deliberately on-demand rather
  than continuous.
- `adopter-sim/` becomes a fourth kind of example material in the tree, alongside
  `docs/worked-examples/`, `docs/demo/`, and `benchmark/scenarios/`. It is
  dev-facing test tooling, not an example a client copies — the README states
  this so the boundary does not blur.

## References

- `scripts/install_smoke_test.py` — spec 119; the wheel/temp-venv and
  truthfulness helpers this reuses.
- `scripts/external_agent_acceptance.py` — the isolated-profile and
  transcript-sanitization helpers this reuses.
- `docs/demo/demo-harness.md` — spec 083; the tracked-seed → ignored-run pattern
  this follows.
- `benchmark/scenarios/retail-semantics.yaml` — the scenario format and the
  categorical `expected_behavior` set.
- `docs/decisions/0014-pure-kit-repo-split.md` — the tool-vs-data repo boundary
  this stays inside.
