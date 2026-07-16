# run-evidence/ -- committed Dagster run records

One `<run-id>.md` per unattended / CI run, rendered by `seshat dagster evidence`
from the raw records under the git-ignored `.seshat/dagster/runs/<run-id>/`,
strictly per `templates/dagster-run-evidence.md`.

These records are DERIVED EVIDENCE about an execution -- per-asset gate command,
exit code, measured numbers, timestamps, commit sha, and concrete
`blocking_reason` + named owner for every halted asset. They are NEVER a ruling:
no readiness `status`, no `Gate status`, no `approvals[]`, no numeric score.
Whether any evidence marks a stage `pass` is Core Authority's record, written by
Core Authority's process, never by a Dagster write.
