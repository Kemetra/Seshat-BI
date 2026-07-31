---
name: dagster-workflows
description: >-
  Use when a user asks to preflight, run, schedule, troubleshoot, or review
  Seshat BI's governed Dagster orchestration of the medallion sequence and its
  committed run evidence.
---

# Governed Dagster workflows

Read `../../portable-operating-contract.md` before acting. Use only the
installed `seshat dagster` helpers; never invoke `dagster` directly against
the orchestration project and never bypass the gate readers, the closed-argv
runner, or the redaction layer. Dagster RUNS already-approved steps; the gate
exit code and the named human decide whether a stage passed.

## Fixed workflow

1. Preflight read-only, without a database query:

   `seshat dagster doctor --json`

   Report blockers verbatim with their remediation hints. Database
   credentials are reported present/absent only -- never echo a connection
   value. An absent DSN is a deferred boundary, not a failure to hide.

2. Execute one governed job as a shell-free child process in the
   orchestration project's own environment:

   `seshat dagster run --job <full_sequence_job|through_gold_job> [--table <table>] [--source-mode <csv|existing-bronze>] [--json]`

   `--source-mode` selects the Bronze origin (the gated tail is identical for
   both and is never bypassed):

   - `csv` (default): a raw `<table>.csv` lands and the loader OWNS and
     reloads `bronze.<table>` (drop-and-reload). Use it for a file-first
     workspace. This is the one destructive-by-design mode.
   - `existing-bronze`: NON-DESTRUCTIVE DB-first. An already-loaded
     `bronze.<table>` is verified READ-ONLY (existence, row count, and that its
     columns cover the approved source-map) and used as the satisfied
     upstream. It issues ZERO Bronze DDL/DML. Use it when Bronze already lives
     in the warehouse (BCP, COPY, an external ETL, a prior tool); never export
     Bronze to a CSV just to feed the default path. `raw_source_file` records a
     `deferred` boundary (no landing file by design), not a failure. A missing,
     empty, or source-map-mismatched relation fails closed with a named blocker.

   The chosen mode is explicit in the command result and in the run evidence
   (`bronze_table`'s measured facts). Any doctor blocker stops the run before
   anything executes. A failed or blocked gate halts every downstream asset
   fail-closed; report the recorded `blocking_reason` and its named owner, then
   stop.

3. List runs or render the committed derived record:

   `seshat dagster evidence [--run-id <id>] [--json]`

   The committed record is written by that verb as
   `orchestration/dagster/run-evidence/<run-id>.md`, rendered deterministically
   from the raw records. Never edit raw records or rendered evidence by hand.

## Hard boundaries

- A green asset means "the command ran and returned this exit code" -- NEVER
  "the stage is now pass". Readiness passes come only from the gate exit code
  and a named human; this adapter records, it does not decide.
- The shipped schedule and sensor are STOPPED by default; starting either is
  a named-human action, never an agent default.
- Publishing is walled off: the graph only TRIGGERS the publish feature and
  fails closed while it is absent. Never publish or simulate publishing.
- Without database credentials, DB-touching assets record a deferred boundary
  and block fail-closed. Report that truthfully; never fabricate a run,
  an asset result, or run evidence.
- Never write a readiness pass, an approval, a confidence score, raw adapter
  output, a credential, a DSN, or an absolute local path.

## Exit meanings

- exit 0: command completed; run evidence remains derived, not an approval.
- exit 1: usage error (unknown verb or flag).
- exit 2: preflight or gate refusal -- doctor blockers, a gate not CLEARED, a
  missing prerequisite, or evidence records refused schema validation
  (nothing executed).
- exit 3: the run failed or halted fail-closed on a gate (the CI signal);
  evidence is still rendered and must be reported.
- exit 4: unexpected internal error, already redacted; report it verbatim --
  it is not a fixable evidence-record problem.
