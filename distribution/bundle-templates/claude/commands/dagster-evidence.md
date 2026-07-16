---
description: List Dagster runs or render a run's committed evidence
---

Run `seshat dagster evidence` to list recorded orchestration runs, or
`seshat dagster evidence --run-id <id>` to validate and render one run's
committed evidence markdown. The record is DERIVED evidence about an execution
(per-asset gate command, exit code, measured numbers, blocked/skipped reasons
with named owners) -- outcomes are execution words, never the readiness token
`pass`, and no numeric score exists anywhere in it. If rendering is refused
because the raw records fail schema validation, report the validation errors
verbatim; never hand-edit records to make them render.
