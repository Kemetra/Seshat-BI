---
description: Preflight the Dagster orchestration adapter (read-only)
---

Load the `dagster-workflows` skill. Run the installed
`seshat dagster doctor` helper and interpret its findings as
orchestration preflight facts: is the orchestration project present, does its
environment resolve, is the pinned dagster consistent, which
tables have a cleared mapping gate, and are database credentials present
(reported as present/absent only -- never echo a connection value). Doctor
findings never grant a readiness pass or approval; report blockers verbatim
with their remediation hints. An absent DSN is a deferred boundary, not a
failure to hide. If `seshat` is unavailable, explain that the Python package
`seshat-bi` must be installed instead of inventing results.
