# Dagster Run Evidence -- `<run-id>`

> **GENERIC TEMPLATE.** This is the blank that ONE unattended / CI Dagster run fills.
> A filled copy is written by the run to `orchestration/dagster/run-evidence/<run-id>.md`.
> Replace every `<placeholder>`, record real measured numbers, and commit it as DERIVED
> EVIDENCE about the execution. It belongs to feature **F030** (on-disk spec
> `024-dagster-orchestration-adapter`; when the spec-dir number and the F-number disagree, the
> roadmap F-number wins).
>
> **What this record IS:** a measured, timestamped, reproducible log of what each orchestrated
> asset DID -- the same category as a `reconciliation-report.md` being filled by a live run. It
> is evidence ABOUT a run.
>
> **What this record is NOT:** it is NEVER a ruling. It writes NO readiness `status`, NO
> `Gate status: CLEARED`, NO `approvals[]` entry, NO metric/mapping/grain/PII definition, and
> NO numeric health / confidence / maturity score. An asset's outcome is an EXECUTION word
> (exit 0 / non-zero; materialized / failed / skipped / blocked) -- never the readiness token
> `pass`. Whether a stage is `pass` is Core Authority's record, written by Core Authority's
> process from this evidence, never by Dagster's write (see the ADR + the integration doc).
>
> **How it relates to the readiness `evidence[]` channel:** the measured per-asset results and
> the `blocking_reason`s below are ALSO surfaced as `evidence[]` / `blocking_reasons[]` entries
> on the affected table's `mappings/<table>/readiness-status.yaml`. That surfacing is Core
> Authority's record of the evidence; it is never a `pass` write by Dagster. Run evidence is
> append / record-only and never overwrites a human-authored gate field.
>
> For a **filled instance**, a later live run would record one under
> `orchestration/dagster/run-evidence/`; a filled worked example under
> `docs/worked-examples/` is CITED there, never inlined here. Keep its specifics (grain
> keys, segments, PII columns, real metric names) out of this template (Principle VII).

---

## Run header

| Field | Value |
|-------|-------|
| Run id | `<run-id>` (the Dagster run identifier) |
| Commit sha | `<sha>` (the repo state the run executed against) |
| Started | `<YYYY-MM-DDThh:mm:ssZ>` (UTC) |
| Finished | `<YYYY-MM-DDThh:mm:ssZ>` (UTC) |
| Triggered by | `<schedule | sensor | manual-CI>` (the unattended / CI trigger -- never a per-run human ruling) |
| Table(s) in scope | `<table>` (generic; one row per orchestrated table) |
| Connection | **READ-ONLY for validation steps.** Credentials from the git-ignored `.env` only (e.g. `DATABASE_URL` or `ANALYTICS_DB_*`); never committed, never inlined here (Principle IX). |
| Run status | `<succeeded | failed>` (a halted / fail-closed run terminates `failed` -- the CI signal; this is derived evidence about the run, never a readiness write) |

> **Run status is the CI signal, not a readiness verdict.** A halted or fail-closed run MUST
> terminate `failed` so an unattended scheduler surfaces the blocker. `failed` here means "the
> run halted"; it flips no readiness stage.

---

## Per-asset results (the eleven planned assets, in graph order)

One row per asset that the run reached. Record the gate command it ran, its EXIT CODE, the
measured numbers it produced, and its EXECUTION outcome. Outcome is an execution word, NEVER the
readiness token `pass`:

- `materialized` -- the asset ran and its gate command returned exit 0.
- `failed` -- the asset's gate command returned non-zero (fail-closed; see STOP-edge note).
- `skipped` -- a STOP edge upstream halted; this asset did not run.
- `blocked` -- a HUMAN-SEAM asset whose committed approval was absent; it halted and ran nothing.

| # | Asset | Gate command (the SAME command CI runs) | Exit code | Measured numbers | Outcome |
|---|-------|------------------------------------------|-----------|------------------|---------|
| 1 | `raw_source_file` | `<n/a -- landing input>` | `<n/a>` | `<bytes / rows landed>` | `<materialized | failed | skipped>` |
| 2 | `bronze_<table>` | `<load command>` | `<0 | non-zero>` | `<rows loaded>` | `<materialized | failed | skipped>` |
| 3 | `source_profile` | `<profile command>` | `<0 | non-zero>` | `<rows profiled, null-rate, distinct PK>` | `<materialized | failed | skipped>` |
| 4 | `source_map` *(HUMAN SEAM)* | `<reads Gate status; runs nothing if OPEN>` | `<n/a>` | `<Gate status read: CLEARED | OPEN; open rows: N>` | `<materialized | blocked>` |
| 5 | `silver_tables` *(STOP + gated on source_map)* | `seshat check` | `<0 | non-zero>` | `<rule violations: N>` | `<materialized | failed | skipped | blocked>` |
| 6 | `gold_tables` *(STOP)* | `seshat check` | `<0 | non-zero>` | `<rule violations: N>` | `<materialized | failed | skipped>` |
| 7 | `metric_contracts` | `<reads approved contracts; authors none>` | `<n/a>` | `<contracts bound: N; unbound: N>` | `<materialized | skipped>` |
| 8 | `semantic_model` *(HUMAN SEAM)* | `seshat check` + contract-binding read | `<0 | non-zero>` | `<measures bound to approved contracts: N of M>` | `<materialized | blocked | skipped>` |
| 9 | `dashboard_blueprint` *(gated on semantic_model)* | `<design-evidence command>` | `<0 | non-zero>` | `<pages / visuals planned: N>` | `<materialized | skipped>` |
| 10 | `handoff_pack` | `<generate handoff command>` | `<0 | non-zero>` | `<handoff written at <path>>` | `<materialized | skipped>` |
| 11 | `publish_execution_evidence` *(HUMAN SEAM; gated on publish_ready = pass; TRIGGERS F016 only)* | `<reads publish_ready; triggers F016 if pass>` | `<n/a>` | `<publish_ready read: pass | not-pass; F016: triggered | unavailable>` | `<materialized | blocked>` |

> **The live validate row (acceptance).** Where the run includes the live `retail validate`
> step, record it explicitly:
>
> | Step | Gate command | Exit code | Measured numbers | Outcome |
> |------|--------------|-----------|------------------|---------|
> | `retail validate` | `retail validate --source-map mappings/<table>/source-map.yaml` | `<0 | non-zero | deferred-boundary>` | `<PK unique yes/no; orphan FKs: N; reconcile delta: <amount>>` | `<materialized | failed | deferred>` |
>
> If creds are absent / the DB is unreachable, record `deferred-boundary` with the timestamp --
> NEVER fabricate a pass and NEVER mark Gold Ready (Principle VIII; the live run is gated on
> creds).

> **STOP-edge note.** A `failed` asset HALTS all downstream assets, which are recorded
> `skipped` -- not run around. A `blocked` HUMAN-SEAM asset likewise halts its downstream build.

---

## Blocked / skipped assets (one block per halted asset)

For every asset recorded `failed`, `skipped`, or `blocked`, record the CONCRETE blocking reason
and the NAMED OWNER who can clear it. No adjective, no score -- a measured reason and a name.

| Asset | Why blocked / skipped (concrete `blocking_reason`) | Named owner who can clear it |
|-------|----------------------------------------------------|------------------------------|
| `<asset>` | `<e.g. retail validate exit non-zero: 3 orphan FKs in dim_<...>; reconcile delta 0.07>` | `<named role / person>` |
| `<asset>` | `<e.g. source_map Gate status OPEN: 2 unresolved rows>` | `<the mapping reviewer>` |
| `<asset>` | `<e.g. publish_ready not pass: handoff sign-off absent>` | `<the named publish approver>` |
| `<asset>` | `<e.g. F016 publish adapter not available>` | `<the F016 owner>` |

> A human-seam halt MUST record the committed approval it READ (or recorded as absent) with the
> file + field it was read from -- e.g. "read `Gate status` from
> `mappings/<table>/unresolved-questions.md`: OPEN" or "read `approvals[]` from
> `mappings/<table>/readiness-status.yaml`: none for stage `<stage>`".

---

## What this run did NOT write (the no-authored-truth attestation)

This block is part of the record so a reviewer can confirm the run authored no truth. A green
run and a blocked run BOTH leave these untouched:

- [ ] No `readiness-status.yaml` stage `status` was changed by this run.
- [ ] No `Gate status: CLEARED` was written by this run.
- [ ] No `approvals[]` entry was added by this run.
- [ ] No metric / mapping / grain / rollup / segment / PII disposition was defined by this run.
- [ ] No Power BI model was published and no Power BI connection was opened by this run (the
      terminal asset only TRIGGERS F016 when `publish_ready = pass`).
- [ ] No numeric health / confidence / maturity score appears anywhere in this record.

> `git diff` after the run should show changes ONLY to this run-evidence file and to the
> `evidence[]` / `blocking_reasons[]` channel that Core Authority's process records from it --
> never to any stage `status`, `Gate status`, or `approvals[]` field.

---

## See also

- **The decision:** `docs/decisions/0010-dagster-is-orchestration-adapter.md` -- Dagster runs
  approved steps, decides no stage; the derived-evidence vs authored-truth boundary.
- **The integration guide:** `docs/integrations/dagster-adapter.md` -- the asset graph, the
  human seams, the allowed / forbidden operations.
- **The agent-side companion skill:** `.claude/skills/dagster-orchestration-adapter/SKILL.md`.
- **The live-evidence sibling this mirrors:** `templates/reconciliation-report.md` (the live
  acceptance run filled by a real DB read; the same evidence-not-ruling category).
- **The readiness spine + the four-status / no-score vocabulary:**
  `docs/readiness/readiness-model.md`; the stage sequence `docs/readiness/readiness-pipeline.md`.
- **The conductor sibling whose gate-read posture this mirrors:**
  `.claude/skills/retail-orchestrate/SKILL.md`.
- **The filled worked-example instance (cited, never inlined):**
  a filled worked example under `docs/worked-examples/`.
- **The spec:** `specs/024-dagster-orchestration-adapter/spec.md` (FR-007, FR-013, US3).
