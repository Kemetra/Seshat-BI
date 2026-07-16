---
description: Execute one governed Dagster orchestration job (fail-closed)
---

Run `seshat dagster run --job <full_sequence_job|through_gold_job>` (add
`--table <table>` to scope one mapped table) and interpret the result. The run
executes ONLY already-approved steps behind every gate: a failed gate halts all
downstream assets and the command exits 3 -- report that as the honest
fail-closed signal with the recorded blocking reason and named owner, never as
something to bypass. The mapping gate, semantic-model approval, and
publish_ready are READ from committed artifacts; never edit them to make a run
green (approval is a named human's action). Run evidence is rendered to
`orchestration/dagster/run-evidence/<run-id>.md`; cite it. Without database
credentials the DB-touching assets record a deferred boundary -- say so
truthfully. A green run is evidence, never a readiness `pass`.
