# Governance Checklist: Dagster Orchestration Adapter

**Purpose**: Verify the spec respects Core Authority -- the gate that asks "does this adapter
RUN steps without ever DECIDING a stage or authoring truth?"
**Created**: 2026-06-25
**Roadmap feature**: F030 (spec-dir 024)
**Feature**: [spec.md](../spec.md)

This is the feature's "does it respect Core Authority" gate. Every item maps to the spec's
Forbidden operations + Human approval boundary. Items are unchecked [ ] -- they are the review
to run against the authored spec.

## Core-vs-adapter authority (the load-bearing boundary)

- [ ] CHK-G1 The spec states Dagster is an ORCHESTRATION ADAPTER that RUNS approved steps and
      DECIDES no readiness stage (Core Authority owns truth; the adapter executes).
- [ ] CHK-G2 The derived-evidence vs authored-truth boundary has its OWN subsection AND is
      reflected in Allowed/Forbidden operations -- the reconciling sentence is stated (Dagster
      writes evidence ABOUT runs and READS committed approvals; it never writes a `pass`, a
      `Gate status: CLEARED`, an approval, or a metric/mapping/grain ruling).
- [ ] CHK-G3 For mechanical stages (Silver/Gold Ready) the spec says Dagster writes the CHECK
      evidence and Core Authority records the `pass` from that evidence -- Dagster does not write
      the `pass`.
- [ ] CHK-G4 The gate exit code remains the SOLE pass authority for mechanical stages
      (Principle I) -- an asset's success means "the command ran and returned this exit," not
      "the stage passed."

## Principle V -- stop-and-ask (judgment calls halt, never auto-resolve)

- [ ] CHK-G5 Every Principle-V judgment call (grain ambiguity, PII publish-safety, business
      rollup, segment mapping, sentinel-vs-null) HALTS the affected asset and escalates to the
      named owner; the orchestrator never resolves one to make a finding go away (US4 / FR-004).
- [ ] CHK-G6 The source-map gate (Principle IV) is held: the `silver_tables` asset cannot
      materialize until the mapping is CLEARED in the committed gate artifacts; Dagster READS
      that approval and never self-grants it (US2 / FR-006).
- [ ] CHK-G7 Conflicts are surfaced, not buried: a run-evidence write that conflicts with a
      human-authored gate field surfaces the conflict; the orchestrator does not resolve it.

## No self-approval (the adapter never grants approval)

- [ ] CHK-G8 The Forbidden operations enumerate: approve a mapping; write `Gate status:
      CLEARED`; invent a parallel approval marker; approve/define a metric contract; change a
      readiness stage to `pass` without evidence + named approval.
- [ ] CHK-G9 Every human-seam asset (`source_map`, `semantic_model`, `publish_execution_evidence`)
      is bound to a NAMED human approver in the Human approval boundary section; Dagster reads
      the approval as the GO signal and halts if absent.
- [ ] CHK-G10 The publish path is execution-trigger-only: with `publish_ready = pass` the publish
      asset TRIGGERS the parked F016 adapter; Dagster opens no Power BI connection and publishes
      nothing (Principle II + hard rule #6).

## No fake confidence (Principle IX / hard rule #9)

- [ ] CHK-G11 Run evidence carries explicit `status` + measured numbers + `blocking_reasons[]`,
      never a fabricated health/confidence score; a numeric score is explicitly OPTIONAL +
      DEFERRED.
- [ ] CHK-G12 Every evidence cell is a measured, traceable value (exit code, row count, 0 orphan
      FKs, penny-exact reconcile, timestamp, commit sha) -- not an adjective.

## Generic (no worked-example contamination -- Principle VII)

- [ ] CHK-G13 All five files use placeholders (`<table>`, `<source>`, `<MetricName>`); the
      C086 / retail_store_sales worked examples are CITED as references only, never inlined.
- [ ] CHK-G14 No worked-example specifics (billing codes, business segments, PII column names,
      per-table grain keys) appear in any of the five files.

## Secrets, paths, encoding (Principle IX)

- [ ] CHK-G15 No secrets, DSNs, tokens, Kaggle/Power BI credentials, or local machine paths
      appear in any file.
- [ ] CHK-G16 All five files are ASCII-only, UTF-8 without BOM (`->` arrows, `--` dashes, no
      box-drawing / smart quotes / em-dashes); repo-relative paths stay short (`<= 200` chars).

## Allowed-vs-forbidden operations (closed, non-overlapping)

- [ ] CHK-G17 The Allowed operations are a closed set: sequence the stages (decide none); RUN
      the named steps (load bronze, profile, dbt/SQL migrations, `retail check`, `retail
      validate`, semantic check, handoff pack); WRITE derived run-evidence; READ committed
      approvals; TRIGGER F016 only when `publish_ready = pass`; halt + propagate a failed gate;
      escalate judgment calls.
- [ ] CHK-G18 The Forbidden operations are a closed set with NO overlap with Allowed: approve
      mapping/metrics, write `pass`/`CLEARED`/status, define truth, resolve ambiguity, bypass
      the source-map gate, publish Power BI / publish without `publish_ready = pass`, emit a
      score, run around a STOP edge, create any Dagster file this slice.
- [ ] CHK-G19 A reviewer can classify any proposed Dagster action as Allowed or Forbidden with
      no ambiguity about which list it falls in.

## Evidence-required (every claim is backed)

- [ ] CHK-G20 The Evidence required section states what a green run, a blocked run, a human-seam
      halt, and a triggered publish must each record -- and that evidence is append/record-only,
      never overwriting a human gate field.
- [ ] CHK-G21 The readiness stage affected is stated as ALL stages, DECIDES none, with the gate
      exit code (mechanical) and the named human (judgment-call) as the authority for every
      stage's `pass`.

## Scope wall (planning-only; creates no Dagster file)

- [ ] CHK-G22 The spec creates ONLY the five planning files; every Dagster file, pyproject,
      module, doc, ADR, template, and skill is ENUMERATED as a FUTURE output and created by
      NONE of the five files (FR-001 / SC-001).
- [ ] CHK-G23 The F005 reconciliation is explicit and does not duplicate the sequence: Dagster
      is the unattended/CI sibling of the `retail-orchestrate` conductor -- same sequence, same
      gate-exit authority, same two human seams, neither self-approves.

## Notes

- The single governance risk is an orchestrator silently becoming Core Authority by conflating
  "my asset succeeded" with "the stage passed." CHK-G1..G4 and CHK-G8..G10 are the items that
  guard exactly that line.
- This checklist maps 1:1 to the spec's Forbidden operations and Human approval boundary; a
  failing item is a Core-Authority violation to fix in the spec before the planning slice is
  considered done.
