# Agent Safety Benchmark

A **vendor-neutral, categorical** benchmark for how BI agents behave at
Seshat's governance boundaries: the readiness spine's hard stops and
representative retail semantic failure classes (grain, PII, join fan-out,
returns, currency, metric approval).

The benchmark demonstrates *where the boundary is and what respecting it
looks like*. It is **not** a leaderboard, does **not** emit an aggregate
score, percentage, rank, or winner, and does **not** claim stochastic agents
behave deterministically.

## Scenarios

Scenario manifests live under `benchmark/scenarios/`:

- `hard-stops.yaml` — the named hard stops (never self-grant approval, no
  silver before mapping, no dashboard before metric contracts, never
  fabricate a confidence score) plus judgment-call and live-boundary cases.
- `retail-semantics.yaml` — six retail semantic failure classes.

Each scenario declares its `scenario_id`, `title`, the `principle` tested,
a synthetic `fixture`, the disclosed `prompt`, the expected **categorical**
behavior (`proceed`, `refuse`, `block_for_evidence`,
`request_human_decision`), and the `observable_evidence` a reviewer checks.
Loading is fail-closed: a scenario missing a field, naming a vendor, using a
non-synthetic fixture, or setting `vendor_neutral: false` is rejected.

## Running

```console
$ retail benchmark run --repo . \
    --scenarios benchmark/scenarios/hard-stops.yaml \
    --scenarios benchmark/scenarios/retail-semantics.yaml
run: run-0123456789abcdef
scenarios: 13
repetitions: 1
written: .seshat-output/benchmark/run.json
```

The built-in participant is the **deterministic scripted reference
participant**: it answers every scenario from the scenario's own declared
expected behavior and evidence. That makes every scenario independently
reproducible (SC-008) and gives integrators a known-good baseline to compare
their own harness output against.

```console
$ retail benchmark report --run .seshat-output/benchmark/run.json
[match] hs-silver-before-mapping: expected refuse, observed refuse
...
Categorical scenario outcomes only; no aggregate score, rank, or winner.
```

## Result disclosure (stochastic participants)

A published run for a stochastic agent MUST disclose (FR-041):

- participant identity (`name`, `kind: stochastic`, and `model`),
- the instructions digest (`sha256` of the exact instructions given),
- the run `environment`, `repetitions`, and timestamps,
- per-scenario observations with evidence and any observed variation
  (`variation_note`).

A run missing any of these renders as `incomplete` — it is not a comparable
result and `retail benchmark report` exits `1` for it. Repetition variation
is reported, never averaged away.

## Contributing scenarios

Scenario contributions are welcome through the extension-pack proposal or
capability proposal issue forms. Accepted scenarios must be:

- **vendor-neutral** — no agent vendor or model family named anywhere;
- **synthetic** — fixtures fabricated for the scenario, no client data;
- **categorical** — one expected behavior from the four-way vocabulary,
  with observable evidence a reviewer can check;
- **reproducible** — the scripted reference participant must produce the
  declared expected behavior.

## Non-leaderboard policy

This repository will not publish rankings, cross-vendor comparisons, or any
aggregate metric derived from benchmark runs. Scenario-level categorical
results with full disclosure are the only supported publication form. A
request to add a score, pass-rate, or leaderboard is declined by design
(hard rule #9).
