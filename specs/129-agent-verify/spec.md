# Feature Specification: Agent Compatibility Certification (`seshat agent verify`)

**Feature Branch**: `129-agent-verify`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Agent Compatibility Certification (`seshat agent verify --target claude|codex`). Produce CATEGORICAL EVIDENCE that an agent integration installs correctly and obeys Seshat governance. An evidence-producing extension of the existing benchmark + release-verification foundations, NOT a scoring system."

---

## Context and boundary

Seshat BI ships two agent integrations (a Claude Code plugin under
`integrations/claude-code/`, a Codex plugin under `integrations/codex/`), a
vendor-neutral agent-safety benchmark (`src/seshat/benchmark/` + the
`benchmark run|report` verb, spec 120), a read-only agent governor (spec 120),
and release-verification discipline (versioning policy, changelog, install
smoke test; spec 108). What is missing is a single command that a maintainer,
a contributor, or a catalog reviewer can run to answer one question per target:
*does this agent integration install correctly and does it carry the Seshat
governance contract intact?*

`seshat agent verify --target claude|codex` answers that question as
**categorical evidence**. It reuses the shipped foundations rather than
building parallel ones: release-verification for install/discovery/version/
update/uninstall integrity, the benchmark scenarios for the governance hard
stops and retail semantic classes, and the governor for readiness routing.

This feature advances **ecosystem / release-distribution maturity** (the
spec 120 growth family, roadmap M11 lineage). It does **not** advance a
per-table readiness stage, and it is a defect to force it into one.

### What this feature is NOT (the two load-bearing boundaries)

- **It does NOT drive a live stochastic agent.** Verify inspects the
  **installed bundle and its static governance contract** (the generated
  plugin files, the provenance manifest, the version/compatibility
  declarations, and the committed benchmark scenarios/contracts that encode
  each hard stop). It does not launch Claude or Codex, send prompts, or
  observe a model's live behavior. That is consistent with Principle VIII
  (static-first), the stdlib-only driver-free core, and the benchmark's only
  built participant being the deterministic scripted reference. Optionally,
  where an evaluator has already produced a **disclosed benchmark run** for a
  stochastic participant (via the existing `benchmark run|report` FR-041
  path), verify MAY reference that run as supplementary evidence, reported
  per-run with observed variation and never converted into a pass.

- **It produces EVIDENCE, not a CERTIFICATION.** Despite the working title,
  verify MUST NOT conclude "this agent obeys governance," emit a score, rank,
  pass-rate, leaderboard, or grant readiness/approval to any agent. It may
  only assert what static content and the reference baseline support: that the
  integration *ships* the governance contract encoding each hard stop, that
  each required check's inputs are present and evaluate categorically, and
  that the deterministic reference baseline matches. Any claim beyond that is
  forbidden (mirrors FR-002 / FR-040 of spec 120).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify one agent integration end to end (Priority: P1)

A maintainer or contributor runs `seshat agent verify --target claude` (or
`--target codex`) from a clean checkout and receives one categorical result
per required check, each with inspectable evidence, plus a clear per-check
verdict of PASS, BLOCKED, or UNAVAILABLE. No check is silently skipped, and no
check that could not actually run is reported as a pass.

**Why this priority**: This is the whole feature's value: a single, truthful,
reproducible statement of whether a target integration is installable and
carries the governance contract. It is the minimum viable release.

**Independent Test**: Run verify against the shipped `claude` and `codex`
targets from a clean environment and confirm each required check produces a
PASS/BLOCKED/UNAVAILABLE verdict with at least one evidence item, and that the
overall exit code distinguishes "all required checks PASS" from "one or more
BLOCKED" from "one or more UNAVAILABLE".

**Acceptance Scenarios**:

1. **Given** the shipped, drift-free `claude` integration, **When** verify runs
   for installation & discovery, **Then** it reports PASS citing the resolved
   plugin manifest, the marketplace entry, and a matching bundle provenance
   manifest as evidence.
2. **Given** a target whose declared compatibility version is outside the
   supported range, **When** the version-compatibility check runs, **Then** it
   reports BLOCKED naming the incompatible version and the supported range, and
   never reports PASS.
3. **Given** a required check whose surface is absent for that target (for
   example an IDE surface the target does not provide), **When** verify runs,
   **Then** that check reports UNAVAILABLE with the reason, distinct from
   BLOCKED, and is never coerced to PASS.
4. **Given** any required check that cannot be evaluated, **When** verify
   finishes, **Then** the overall result is not "all pass": at least one check
   is BLOCKED or UNAVAILABLE and the exit code reflects it.

---

### User Story 2 - Confirm the governance contract is intact per target (Priority: P2)

A reviewer wants to confirm that each of Seshat's hard stops is encoded in the
integration being shipped: PII refusal, no self-approval, no silver-before-
mapping, no invented metric meaning, and correct readiness routing. The
governance evidence has two distinct layers, and verify keeps them distinct:

- **Per-target contract presence**: the selected target's own bundle MUST ship
  the governance hard-stop contract (the `portable-operating-contract.md`
  exported into `integrations/<target>/`), and it MUST carry every hard-stop
  line. This is the layer that genuinely differs by `--target`: a target whose
  bundle drops or mutates a hard stop is BLOCKED, and the verdict is meaningful
  because it reads that target's exported artifact, not a shared repo file.
- **Shared reference baseline** (target-invariant): the committed benchmark
  scenarios + the deterministic scripted reference are repo-level and identical
  across targets. Verify confirms each hard stop resolves to a named committed
  scenario (or the governor contract) and that the reference baseline matches
  the declared expected categorical behavior. This layer is a shared baseline,
  and verify labels its evidence as such rather than implying it is per-target.

**Why this priority**: The governance contract is the product's distinctive
claim. Confirming it ships intact - the target's own bundle carries every hard
stop, and each hard stop maps to a committed scenario whose reference baseline
matches - is the second half of "installs correctly and obeys governance",
expressed as static contract presence + reference-baseline match, not live
behavior.

**Independent Test**: Run verify's governance checks against each target and
confirm (a) the target's exported operating contract is present and carries
every hard-stop line (per-target, and a target with a dropped hard stop is
BLOCKED), and (b) each of PII refusal, no self-approval, no silver-before-
mapping, no invented metric meaning, and readiness routing resolves to a named
committed scenario/governor contract whose reference baseline matches its
declared expected behavior (shared baseline).

**Acceptance Scenarios**:

1. **Given** the selected target's exported bundle, **When** the per-target
   governance-contract-presence check runs, **Then** it confirms the target's
   `portable-operating-contract.md` is present and carries every hard-stop line
   (PASS), and reports BLOCKED naming the missing/mutated hard stop for a target
   whose bundle drops one - so `--target claude` and `--target codex` can differ.
2. **Given** the shipped scenario manifests, **When** the PII-refusal check
   runs, **Then** it cites the `rs-pii-exposure` scenario, confirms its
   expected categorical behavior is a refusal, and confirms the scripted
   reference participant reproduces it (PASS, labeled a shared baseline).
3. **Given** the shipped scenario manifests, **When** the no-self-approval and
   no-silver-before-mapping checks run, **Then** they cite `hs-self-grant-
   approval` and `hs-silver-before-mapping` respectively and confirm the
   reference baseline matches each declared expected behavior.
4. **Given** the shipped scenario manifests, **When** the no-invented-metric-
   meaning check runs, **Then** it cites `rs-metric-without-approval` (metric
   used without an approved contract) and confirms the expected behavior blocks
   for evidence or requests a human decision, never proceeds.
5. **Given** the read-only governor, **When** the readiness-routing check runs,
   **Then** it confirms the governor returns the current stage, evidence,
   blockers, next allowed action, and forbidden scope for a fixture without
   any write, and reports UNAVAILABLE (not BLOCKED, not PASS) if the governor
   surface cannot be invoked in the environment.
6. **Given** any governance check whose cited scenario is missing, malformed,
   or whose reference baseline does not match, **When** verify runs, **Then**
   that check is BLOCKED with the concrete reason and verify never claims the
   agent obeys the rule.

---

### User Story 3 - Confirm update and uninstall integrity (Priority: P3)

A maintainer preparing a release wants assurance that the shipped bundle
matches its provenance manifest (so an update is a clean, reviewable diff) and
that the integration's footprint is fully declared (so an uninstall is
complete). Verify checks the bundle against `output_sha256` provenance and the
exporter drift check, and reports the declared install footprint.

**Why this priority**: Update and uninstall integrity protect the maintainer
and the downstream user; they are release-verification concerns and reuse the
already-shipped provenance manifest and exporter drift check.

**Independent Test**: Run verify against a drift-free target (PASS) and against
a deliberately mutated generated file (BLOCKED naming the drifted path), and
confirm the uninstall-footprint evidence lists the files the integration
installs.

**Acceptance Scenarios**:

1. **Given** a target whose generated files all match their recorded
   `output_sha256`, **When** the update-integrity check runs, **Then** it
   reports PASS citing the provenance manifest and the drift-check result.
2. **Given** a target with an edited generated file, **When** the update-
   integrity check runs, **Then** it reports BLOCKED naming the drifted path
   and the expected vs observed hash, and never PASS.
3. **Given** a target, **When** the uninstall-integrity check runs, **Then** it
   reports the declared set of installed paths as evidence so a reviewer can
   confirm removal is complete, and reports UNAVAILABLE if the footprint cannot
   be enumerated from committed inputs.

---

### User Story 4 - Produce a portable, disclosure-safe evidence record (Priority: P4)

An evaluator wants the verify result as a durable, machine-readable evidence
record they can attach to a release note or a catalog submission. Verify writes
a local evidence record under `.seshat-output/` by default; publication or
catalog submission is an explicit, owner-controlled action gated on a
disclosure check.

**Why this priority**: Portable evidence makes the result useful beyond one
terminal session, but publication must stay owner-controlled and disclosure-
safe, consistent with the spec 120 publication posture.

**Independent Test**: Run verify, confirm the evidence record is written under
`.seshat-output/` and contains per-check verdicts, evidence, target identity,
tool version, and generation time; then confirm that publication is refused
without an explicit publication intent and refused when disclosure findings
are present.

**Acceptance Scenarios**:

1. **Given** a completed verify run, **When** the evidence record is written,
   **Then** it records the target, tool version, per-check verdicts (PASS/
   BLOCKED/UNAVAILABLE), each check's evidence and blocking reasons, and the
   generation time, and it contains no aggregate score, rank, or pass-rate.
2. **Given** an evidence record and no explicit publication intent, **When**
   publication is attempted, **Then** it is refused and the record stays local.
3. **Given** an evidence record with unresolved disclosure findings (a secret,
   a real connection string, a local absolute path), **When** publication is
   attempted with intent, **Then** it is refused until disclosure passes.

### Edge Cases

- A target names an integration that does not exist (`--target foo`): verify
  refuses with a clear error listing supported targets; it does not emit an
  empty PASS.
- A target ships but its bundle provenance manifest is missing or unreadable:
  the affected checks are BLOCKED (fail-closed), never PASS.
- The environment lacks an optional surface a check depends on (no IDE surface,
  no governor invocation path, no prior stochastic benchmark run): those checks
  are UNAVAILABLE with the reason, distinct from BLOCKED.
- A benchmark scenario cited by a governance check has been removed or renamed:
  the check is BLOCKED naming the missing scenario id, so a contract regression
  cannot silently read as a pass.
- Every governance check would pass but one required install check is
  UNAVAILABLE: the overall result must not read as "verified"; the exit code
  and summary must surface the UNAVAILABLE check.
- A supplied prior stochastic benchmark run is `incomplete` (missing FR-041
  disclosure): it is not accepted as evidence; the referencing check stays
  UNAVAILABLE and never becomes a PASS.
- The evidence record would contain a high-cardinality source value or possible
  PII: generation omits the value and the disclosure boundary is reported;
  publication stays blocked.

## Requirements *(mandatory)*

### Functional Requirements

#### Shared verify contract (cross-cutting)

- **FR-001**: Verify MUST accept a `--target` naming exactly one shipped
  integration (initially `claude` or `codex`) and MUST refuse an unknown target
  with the list of supported targets.
- **FR-002**: Every required check MUST resolve to exactly one categorical
  verdict from the fixed vocabulary {PASS, BLOCKED, UNAVAILABLE}. No other
  verdict value is permitted.
  - **PASS**: the check ran, its evidence is present, and it matched the
    expected outcome.
  - **BLOCKED**: the check ran or sought to run but did not pass - a governance
    mismatch or over-refusal, missing/malformed evidence, drifted bundle, or an
    incompatible version. A BLOCKED verdict MUST carry at least one concrete
    blocking reason. Fail-closed.
  - **UNAVAILABLE**: the check could not run at all - an unsupported surface, an
    absent environment, or no live participant. UNAVAILABLE is distinct from
    BLOCKED and MUST NEVER be coerced to PASS.
- **FR-003**: Verify MUST NOT emit or imply any aggregate score, percentage,
  rank, pass-rate, grade, leaderboard, or winner, and MUST NOT roll the
  per-check verdicts up into a single "certified"/"verified" pass. The overall
  result is the set of per-check verdicts plus a truthful summary that names any
  BLOCKED or UNAVAILABLE check.
- **FR-004**: Verify MUST NOT grant readiness or approval to any agent, MUST NOT
  advance any readiness stage, and MUST NOT infer approval from a successful
  check (Principle V; hard rule #9).
- **FR-005**: Every PASS MUST cite at least one inspectable evidence item; every
  BLOCKED MUST state at least one concrete blocking reason; every UNAVAILABLE
  MUST state why the check could not run.
- **FR-006**: Verify MUST be read-only with respect to tracked files, databases,
  analytics models, reports, external services, approvals, and readiness stages;
  its only writes are the local evidence record under `.seshat-output/`.
- **FR-007**: Verify MUST distinguish static contract presence + reference-
  baseline match from any live or semantic conformance claim, and MUST NOT
  present static evidence as proof of a live agent's behavior.
- **FR-008**: Verify MUST NOT require a database, credentials, an external
  service, a running IDE, or Power BI Desktop for its required checks; checks
  that would need an absent surface report UNAVAILABLE rather than failing the
  run.

#### Installation & discovery (extends release-verification, spec 108)

- **FR-009**: Verify MUST confirm the selected target's integration is
  installable and discoverable by resolving its plugin manifest, its
  marketplace/discovery entry, and its presence in the generated integration
  tree; a missing or unresolvable manifest is BLOCKED.
- **FR-010**: Verify MUST reuse the existing install smoke-test discipline
  (spec 108) rather than reimplementing an install path, and cite its result as
  discovery evidence.

#### Version compatibility (extends release-verification, spec 108)

- **FR-011**: Verify MUST read the target's declared version and compatibility
  range and compare them against the supported range; an out-of-range or absent
  declaration is BLOCKED naming the incompatible/absent version and the
  supported range, and MUST NOT read as PASS (spec 120 unsupported-version
  edge case).

#### Governance contract checks (extend the benchmark scenarios + governor)

- **FR-012a**: Verify MUST confirm a **per-target governance-contract-presence**
  check by reading the selected target's own exported operating contract
  (`integrations/<target>/.../portable-operating-contract.md`) and confirming it
  is present and carries every governance hard-stop line (no self-approval, no
  silver before mapping, no Gold-to-Power-BI before live validation, no
  dashboard before metric contracts, no invented mappings / no exposed
  secrets-PII / no skipped gate / no numeric readiness score). A target whose
  exported contract is missing, or drops or mutates a hard-stop line, is
  BLOCKED naming the affected hard stop. This is the layer that genuinely
  differs by `--target`, so two targets can produce different governance
  verdicts. (Shared-baseline checks FR-012 through FR-016 read repo-level
  scenarios and are target-invariant; verify labels their evidence as a shared
  baseline, not per-target.)
- **FR-012**: Verify MUST confirm a **readiness-routing** check by exercising
  the read-only governor over a fixture and confirming it returns the current
  stage, evidence, blockers, next allowed action, and forbidden scope with no
  write; if the governor surface cannot be invoked, the check is UNAVAILABLE.
  (Shared baseline; target-invariant.)
- **FR-013**: Verify MUST confirm a **PII-refusal** check by citing the
  committed PII scenario (`rs-pii-exposure`), confirming its expected
  categorical behavior is a refusal, and confirming the scripted reference
  participant reproduces it.
- **FR-014**: Verify MUST confirm a **no-self-approval** check by citing
  `hs-self-grant-approval` and confirming the reference baseline matches its
  declared expected behavior (a request for a human decision, never a
  self-grant).
- **FR-015**: Verify MUST confirm a **no-silver-before-mapping** check by
  citing `hs-silver-before-mapping` and confirming the reference baseline
  matches its declared expected behavior (a refusal to build silver before
  Mapping Ready is cleared).
- **FR-016**: Verify MUST confirm a **no-invented-metric-meaning** check by
  citing `rs-metric-without-approval` and confirming the expected behavior does
  not proceed (it blocks for evidence or requests a human decision).
- **FR-017**: For every governance check (FR-012a and FR-012 through FR-016), a
  target contract or cited scenario that is missing, malformed, drops or mutates
  a hard stop, or whose reference baseline does not match its declared expected
  behavior MUST make the check BLOCKED with the concrete reason; verify MUST
  NEVER claim the agent obeys the rule on absent or mismatched contract
  evidence.

#### Update & uninstall integrity (extend release-verification provenance)

- **FR-018**: Verify MUST confirm **update integrity** by comparing the target's
  generated files against their recorded provenance (`output_sha256` in the
  bundle manifest) via the existing exporter drift check; a drifted or missing
  file is BLOCKED naming the path and the expected vs observed hash.
- **FR-019**: Verify MUST report **uninstall integrity** by enumerating the
  target's declared installed footprint (the set of generated paths) as evidence
  so a reviewer can confirm removal is complete; if the footprint cannot be
  enumerated from committed inputs, the check is UNAVAILABLE.

#### IDE verification where supported

- **FR-020**: Verify MUST perform an IDE-surface check only where the selected
  target declares an IDE surface; where the target does not provide one, the
  check reports UNAVAILABLE with that reason and is never treated as PASS or as
  a failure.

#### Evidence record & owner-controlled publication

- **FR-021**: Verify MUST write a machine-readable evidence record under
  `.seshat-output/` by default, recording the target identity, tool version,
  per-check verdicts, each check's evidence and blocking reasons, the
  static-vs-live boundary, and the generation time.
- **FR-022**: Publication of a verify evidence record, or its submission to an
  external agent catalog, MUST require an explicit user action and MUST be
  refused when a disclosure check finds a secret, a real connection string, a
  local absolute path, or possible PII (reuse the shipped publication-intent +
  disclosure guard).
- **FR-023**: The evidence record MUST exclude secrets, real connection strings,
  unapproved raw data, PII values, and local absolute paths (spec 120 FR-007).

#### Optional live/stochastic conformance (deferred path)

- **FR-024**: Where an evaluator supplies a previously produced, FR-041-complete
  disclosed benchmark run for a stochastic participant, verify MAY reference it
  as supplementary evidence for the governance checks, reported per-run with the
  disclosed variation and never converted into a PASS or a certification; an
  `incomplete` run MUST NOT be accepted and leaves the check UNAVAILABLE.

### Key Entities *(include if feature involves data)*

- **Verify Target**: A named, shipped agent integration (`claude`, `codex`) with
  a resolvable plugin manifest, a bundle provenance manifest, a declared
  version/compatibility range, and a declared installed footprint.
- **Required Check**: One of the fixed verification checks (installation &
  discovery, version compatibility, per-target governance-contract presence,
  readiness routing, PII refusal, no self-approval, no silver-before-mapping,
  no invented metric meaning, update integrity, uninstall integrity, IDE
  verification). Each declares the foundation it extends, the evidence source it
  reads, and whether its evidence is per-target or a shared baseline.
- **Per-Check Result**: The categorical outcome for one check on one target: a
  verdict {PASS, BLOCKED, UNAVAILABLE}, evidence items (for PASS), blocking
  reasons (for BLOCKED), and an unavailability reason (for UNAVAILABLE).
- **Verify Evidence Record**: The portable, disclosure-safe snapshot of one
  verify run: target identity, tool version, per-check results, the
  static-vs-live boundary, and generation time. It carries no aggregate score
  and grants no approval.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running verify against each shipped target (`claude`, `codex`)
  from a clean checkout produces a categorical verdict for every required check,
  and every PASS carries at least one evidence item while every non-PASS carries
  at least one reason.
- **SC-002**: Across the full check suite there is zero false pass: in a seeded
  suite of one drift, one incompatible version, one missing scenario, and one
  absent surface, the corresponding checks report BLOCKED (first three) and
  UNAVAILABLE (last) respectively, and never PASS.
- **SC-003**: Verify emits no aggregate score, percentage, rank, pass-rate,
  grade, leaderboard, winner, or single rolled-up "certified" verdict in any
  output form (text, machine-readable record, or summary), verified by an
  automated truthfulness check.
- **SC-004**: All verify contract tests demonstrate zero tracked-file writes,
  database writes, model/report mutations, publish actions, self-granted
  approvals, and readiness-stage promotions; the only write is the local
  evidence record under `.seshat-output/`.
- **SC-005**: The per-target governance-contract-presence check reads the
  selected target's own exported operating contract and reports BLOCKED (not
  PASS) for a target whose bundle drops or mutates a hard-stop line, so two
  targets can produce different governance verdicts; and each shared-baseline
  governance check resolves to a named committed benchmark scenario or the
  governor contract, with a removed or renamed cited scenario making the check
  BLOCKED rather than silently passing.
- **SC-006**: The evidence record passes an automated disclosure test finding
  zero secrets, real connection strings, raw client records, PII values, or
  local absolute paths, and publication is refused without explicit intent and
  when disclosure findings are present.
- **SC-007**: Verify runs without a database, credentials, external service,
  running IDE, or Power BI Desktop; checks depending on an absent surface report
  UNAVAILABLE and the run still completes truthfully.

## Assumptions

- **Static-first, not live-agent-driving**: verify inspects the installed bundle
  and its static governance contract (generated files, provenance manifest,
  version/compatibility declarations, committed benchmark scenarios, governor
  contract). It does not launch Claude or Codex or observe a live model's
  behavior. Live/stochastic conformance is the deferred, optional path that
  reuses the benchmark's existing FR-041 disclosed-run mechanism (FR-024).
- **Extends, does not reinvent**: each required check reuses a shipped
  foundation - release-verification (spec 108) for install/discovery/version/
  update/uninstall, the benchmark scenarios (spec 120) for the governance hard
  stops and retail semantic classes, and the governor (spec 120) for readiness
  routing. Verify adds no parallel install path, no new scoring scheme, and no
  new governance rule.
- **Ecosystem maturity, not a table stage**: this feature advances ecosystem /
  release-distribution maturity (the spec 120 growth family, roadmap M11
  lineage). It does not advance a per-table readiness stage and must not be
  forced into one.
- **CLI verb form**: the task explicitly names `seshat agent verify`, and the
  sibling `benchmark run|report` verb shipped in this same foundation, so verify
  ships as a CLI verb. The repo also holds an owner-ratified "Option B: no new
  CLI verbs" preference (specs 118/119); this is a reversible choice recorded as
  an auto-decision, and verify could later be re-homed as a skill without
  changing its evidence contract.
- **Publication is owner-controlled**: the evidence record is local under
  `.seshat-output/` by default; publication or catalog submission requires an
  explicit user action after a disclosure check passes (reuses the shipped
  publication-intent + disclosure guard).
- **Synthetic and generic**: all fixtures used by verify are synthetic and
  generic; C086 and any client specifics remain out of scope (Principle VII).
