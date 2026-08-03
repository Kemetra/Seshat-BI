# Adopter journeys — the blind client sandbox

This directory is the **seed** for a client workspace. It is tracked so it is
reviewable; it is never the place a journey actually runs.

    benchmark/journeys/            <- this seed (tracked)
      -> <root>/ssim/<run-id>/     <- where the agent actually runs (throwaway)
      -> baseline/*.findings.json  <- accepted findings (tracked)
      -> .seshat/adopter-sim/      <- timings (machine-local, git-ignored)

## The blindness contract

A run is only meaningful if the agent could not reach this repo. Eight
assertions enforce that, and any failure aborts the run rather than degrading it:

1. the workspace is not under `REPO_ROOT`
2. `seshat` resolves from `site-packages`, never `src/`
3. no developer modules resolve in the client venv
4. no dev `CLAUDE.md` / `AGENTS.md` / `.git` above the workspace
5. no `PYTHONPATH`, no editable `.pth` into the repo
6. the environment is an allow-list — no DSN, no credentials, no `REPO_ROOT`
7. the agent's on-disk config profile equals the bundle manifest, exactly
8. the **raw** transcript (checked before sanitization) leaks no dev path

Assertion 7 is the one that matters most. Checks 2, 3 and 5 only prove *Python*
cannot reach the dev tree; without 7 the agent could still arrive carrying the
developer's global rules, in which case it was never a client. The inventory is
read from disk — never by asking the agent, since the system under test cannot
certify its own isolation.

## Where the workspace lives, and why not %TEMP%

On Windows `%TEMP%` sits under the user profile, which on a developer machine
holds a `CLAUDE.md` and `.claude/`. A workspace there inherits dev context
through the parent chain, so assertion 4 would abort every run. The harness
therefore *chooses* a root with a provably clean ancestor chain, preferring a
drive-root `ssim/` directory. If no candidate is clean it fails with an
instruction to set `ADOPTER_SIM_ROOT` — it never runs a compromised journey.

## Running it

    python -m scripts.adopter_sim                     # 3 runs x 2 datasets
    python -m scripts.adopter_sim --runs 1            # cheap look, advisory only
    python -m scripts.adopter_sim --datasets messy    # just the hard dataset

Exit codes: `0` clean, `1` harness error, `2` blindness abort, `3` confirmed
findings, `4` metric out of band, `5` partial run, `6` fixture self-test failed.

Timeouts: 300 s per agent step, 120 s per CLI step, 90 min per invocation.

## Cost and duration

**Not yet measured.** Record the measured tokens and wall-clock of the first
full invocation here. Do not write an estimate — an invented number becomes a
plan people trust.

## Findings, and why one run is not enough

A single run of a nondeterministic agent cannot establish a finding. Each journey
runs three times by default; a finding is **confirmed** on a 2-of-3 quorum,
**flaky** at 1-of-3 (reported with its frequency, not ignored), and
**insufficient_data** with fewer than two evaluable runs. `--runs 1` labels
everything **advisory** and cannot update a baseline.

The journey is ordered and stateful, so when a step fails its dependents are
marked `not_evaluable` — never findings, never quorum input. One defect reports
once.

## Why the datasets differ

`clean/` is the control: unique keys, no null measures. `messy/` is built to
hurt, and a fixture self-test asserts it still does — a repeated
`transaction_id`, null measures, two date formats, a PII-shaped column, and no
returns column. If the messy dataset is ever tidied, the harness fails loudly
rather than quietly passing everything.

## What this is not

Not an example a client copies — that is `docs/worked-examples/`. This is
dev-facing test tooling and ships in neither the wheel nor the sdist.

Design: `docs/superpowers/specs/2026-08-03-adopter-sim-design.md`.
