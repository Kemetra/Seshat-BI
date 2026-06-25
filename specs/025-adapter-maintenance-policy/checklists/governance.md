# Governance Checklist: Adapter Maintenance and Auto-Update Policy

**Purpose**: Verify this feature respects Core Authority -- the rule that modules,
adapters, and automation may READ, SUMMARIZE, VISUALIZE, write DERIVED evidence, or
EXECUTE approved steps, but MUST NOT create truth. This is the "does an update policy
respect the readiness spine" gate.
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md) (F031, spec directory 025)

## Core-vs-Module Authority

- [ ] The policy reads/classifies updates and runs checks; it does NOT define business
      meaning, approve a metric/mapping, or define semantic logic (Core Authority owns
      truth)
- [ ] Lane A automerge is confined to the dependency/CI plane -- it writes no readiness
      evidence, sets no status, and touches no `mappings/<table>/` artifact
- [ ] No update PR (in any lane) can move a readiness stage to `pass`, clear a blocker,
      or write a `pass` into `readiness-status.yaml`
- [ ] The compatibility-review verdict is recorded by a named human and stored in
      F032's matrix; the policy routes the trigger and records evidence only
- [ ] The policy publishes nothing to Power BI and grants the Power BI execution
      adapter (F016) no new authority -- its updates are Lane C (never automerge)

## Principle V -- Stop at Judgment Calls

- [ ] A major-version / adapter compatibility verdict is a stop-and-ask: the policy
      recommends/routes, a NAMED human decides (FR-007)
- [ ] Lane B mandates a named human review before merge; green checks are necessary,
      not sufficient
- [ ] Lane C mandates a named human review AND forbids automerge under any check state
- [ ] The policy never self-assigns a reviewer and never self-approves a Lane B/C merge

## No Self-Approval / No Gate Bypass

- [ ] The no-bypass invariant is stated verbatim: no update in ANY lane may bypass a
      readiness gate or move a stage to `pass`; automerge lives below the readiness
      spine (FR-005, SC-004)
- [ ] An update that could regress a gate (`retail check`, `retail validate`,
      silver/gold build, semantic-model checks) MUST re-pass that gate before merge
- [ ] `--no-verify`, gate-skip, admin force-merge, and force-push to a protected
      branch are forbidden (FR-002)
- [ ] A red or absent required check blocks merge in EVERY lane, including Lane A
      automerge (FR-003, FR-004)
- [ ] The transitive-escalation rule prevents a Lane A label from shielding a Lane B/C
      effect (FR-008) -- highest blast radius wins

## No Fake Confidence

- [ ] The policy emits NO dependency/adapter health/maturity/confidence score (hard
      rule #9; FR-010)
- [ ] An update's status is explicit per-check pass/fail + lane + named reviewer (B/C)
      -- never an adjective and never a fabricated number
- [ ] A "dependency health score" request is DECLINED with the no-fake-confidence
      rationale (SC-005)
- [ ] An unavailable required check is marked "not applicable yet (<reason>)", never
      silently treated as passed (FR-009)

## Generic (No Worked-Example Leakage)

- [ ] The policy is stated with placeholders (`<adapter>`, `<dependency>`, `<lane>`);
      concrete package names appear only as lane-membership examples (FR-011)
- [ ] No C086 / `retail_store_sales` / pharmacy specifics (billing codes, segment
      rollups, PII columns, grain keys) appear in any of the five files (SC-005)

## Secrets / Paths (Principle IX)

- [ ] No update may introduce a secret, credential, DSN, token, or local machine path
      into a tracked file; the no-secrets / no-paths check is a hard merge blocker in
      every lane (FR-006)
- [ ] If such a leak is found, the policy says STOP, do not merge, and sweep for
      similar (security rule)
- [ ] The five planning files contain no secret, DSN, token, or local machine path and
      are ASCII + UTF-8 no BOM

## Depend, Never Fork (Principle II)

- [ ] The policy takes an update by UPGRADING the dependency, never by vendoring,
      forking, or re-implementing an adapter (no fork tax)
- [ ] The lanes keep the borrowed engines (dbt, Dagster, Power BI execution adapter,
      Postgres driver, toolchain) current and upgradeable without stranding the repo on
      a snapshot
- [ ] The policy adds no local patch that an upstream upgrade would force re-applying

## Allowed vs Forbidden Operations (mapped to the spec)

- [ ] Every item in the spec's "Allowed operations" is a read / classify / run-check /
      route-to-human / automerge-Lane-A-on-green / re-run-gate action -- none creates
      truth
- [ ] Every item in the spec's "Forbidden operations" is enforced by a checklist item
      above (automerge B/C, gate bypass, stage promotion, self-approval, secret/path
      leak, self-verdict, fabricated score, fork, force-merge)

## Evidence Required (verifiable)

- [ ] The spec's "Evidence required" list is concrete and checkable: lane label,
      required-checks results, no-secrets/no-paths result, dependency-invariants note,
      Lane B/C named reviewer, and (for a major-version/adapter update) the
      compatibility-review record referenced in F032's matrix
- [ ] Each piece of evidence traces to a named source (the PR, CI, the reviewer, or
      F032) -- no evidence is asserted without a source

## Boundary (this slice creates only the five files)

- [ ] This slice creates ONLY the five Spec-Kit files; no `docs/operations/`,
      `docs/decisions/`, or `.github/` file is created (SC-001, T020)
- [ ] The future deliverables are ENUMERATED in plan.md and tasks.md as planned
      outputs, never written here
