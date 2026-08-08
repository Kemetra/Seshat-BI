# Data model: dbt evidence governance consumer

This spec adds NO new persisted artifact, NO new schema, and NO new field to any
existing artifact. It adds one state vocabulary and one derived caveat string.

## Unchanged (read-only inputs)

| Artifact | Owner | Change |
| --- | --- | --- |
| `RunEvidence` (`src/seshat/dbt/contracts.py:324`) | dbt adapter | none |
| `schemas/dbt-run-evidence.schema.json` | dbt adapter | none |
| `mappings/<table>/dbt-evidence/<invocation_id>.json` | `write_evidence()` | none; read only |
| `mappings/<table>/readiness-status.yaml` | readiness spine | none; not read by the classifier |
| evidence pack, its 10 sections, `_build_section`, `_section_blockers` | evidence pack | none (spec FR-016) |

Envelope fields consumed by the classifier, and only these:

- `invocation_id` -- identifies the run
- `outcome` -- execution result (`pass` / `blocked` / `failed`)
- `readiness_effect` -- the record's own statement of its governance weight
- `blocking_reasons` -- present when the run recorded blockers

Every other field in the record is deliberately not echoed. That restriction is
what makes read-time re-redaction unnecessary rather than merely assumed
(spec FR-013).

## New state vocabulary

Returned by the classifier, mirroring the shape of
`portfolio_watch.live_validation_state()`, which returns a bare string.

| State | Meaning | Caveat emitted |
| --- | --- | --- |
| `absent` | no `dbt-evidence/` directory, or no records in it | no |
| `built` | latest record parsed; execution outcome `pass` | no |
| `failed` | latest record parsed; execution outcome `failed` | yes |
| `blocked` | latest record parsed; outcome `blocked`, `unavailable`, or unrecognized | yes |
| `unreadable` | latest record is not valid JSON, or lacks required envelope fields | yes |

Reuse note: `portfolio_watch` already defines `STATE_UNREADABLE = "unreadable"`
(`src/seshat/portfolio_watch.py:107`). The classifier reuses that constant
rather than declaring a second spelling of the same state.

Vocabulary rule: none of these five values is a readiness four-status token.
`blocked` is the one collision, and it is the same word the execution vocabulary
already uses in `_DBT_OUTCOME_TO_EXECUTION`; it is returned as an execution
state by a function that never reads or writes readiness, and it is never placed
under a `status` key belonging to a stage.

## New shared constant

```
# src/seshat/dbt/  (public)
OUTCOME_TO_EXECUTION = {
    "pass": "built",
    "failed": "failed",
    "blocked": "blocked",
    "unavailable": "blocked",
}
```

Single definition. `orchestration/.../dbt_build.py` imports it and drops its
private `_DBT_OUTCOME_TO_EXECUTION`, inverting an existing backwards dependency
rather than adding a second copy.

An outcome absent from the mapping translates to `blocked`, matching the
orchestration package's existing `.get(result.outcome, "blocked")` default, so
an unknown upstream status fails closed.

Direction check: `orchestration/dagster/pyproject.toml` already declares a
runtime dependency on the root `seshat-bi[dbt]` package, and `dbt_build.py`
already imports `seshat.cli.commands.dbt` and `seshat.dagster_adapter.redaction`.
`src/seshat` imports nothing from `tower_bi_orchestration`. The move introduces
no cycle and no new package-boundary crossing.

## The caveat string

Composed in `agent_next`, mirroring `_live_validation_next_override()`.

Shape constraints, all load-bearing:

- It MUST NOT begin with `STOP` unless the dbt state genuinely closes the gate.
  `agent_next._is_stopped()` (`src/seshat/agent_next.py:812-816`) returns true
  when the emitted action string begins with `STOP`, which suppresses all
  downstream guidance. The existing live-validation override uses `CAUTION --`
  for its downgraded case for exactly this reason (spec FR-017).
- It MUST cite the record's relative path so the underlying artifact can be
  inspected.
- It MUST name the translated execution word, never dbt's raw `outcome`.
- It MUST NOT claim a stage, grant an approval, or restate a readiness status.

## Vocabulary separation

| Vocabulary | Values | Owner | Produced here |
| --- | --- | --- | --- |
| dbt execution outcome | `pass`, `failed`, `blocked`, `unavailable` | dbt adapter | no (translated first) |
| execution word | `built`, `failed`, `blocked` | `OUTCOME_TO_EXECUTION` | yes |
| classifier state | `absent`, `built`, `failed`, `blocked`, `unreadable` | this spec | yes |
| readiness four-status | `not_started`, `blocked`, `warning`, `pass` | readiness spine | never |

The readiness four-status vocabulary is never produced by this surface, and the
classifier never opens `readiness-status.yaml`. That is the structural guarantee
behind spec FR-004.
