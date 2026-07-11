# Feature Specification: Agent Ecosystem Growth

**Feature Branch**: `120-agent-ecosystem-growth`

**Created**: 2026-07-11

**Status**: Draft

**Input**: User description: "Specify the creative and professional feature and repository enhancements proposed to increase Seshat BI adoption, stars, contributions, and strength as an agent-driven tool: a read-only agent governor, reusable readiness check integration, a rapid interactive proof, extension packs, an agent-safety benchmark, portable readiness evidence, contributor onboarding, and a static readiness explorer."

## Clarifications

### Session 2026-07-11

- Q: Should the eight journeys ship as one release or as independently releasable phases? -> A: Independently releasable phases in priority order, with User Story 1 as the MVP.
- Q: What trust boundary should the initial agent governance interface use? -> A: Read only the explicitly selected local workspace; no remote retrieval or execution.
- Q: How should extension packs be acquired in the initial release? -> A: Explicit local installation only; a public registry is deferred until pack trust and compatibility are proven.
- Q: When may generated passports and explorer output be published? -> A: Generation is local by default; publication requires an explicit user action after disclosure checks pass.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reach a Truthful First Success (Priority: P1)

A prospective user can install or launch Seshat BI, run a bundled example, and see the seven readiness stages, supporting evidence, concrete blockers, next allowed action, and forbidden scope without providing credentials, a database, or Power BI Desktop.

**Why this priority**: The current system has deep capabilities, but adoption depends on a visitor seeing the product's distinctive value before reading the full governance corpus.

**Independent Test**: Start from a supported clean environment, follow only the public first-success instructions, and verify that a truthful readiness result is visible within five minutes without secrets or external services.

**Acceptance Scenarios**:

1. **Given** a new user with no configured data connection, **When** they run the bundled proof, **Then** they see each readiness stage with its status, evidence, blockers, next action, and stop point.
2. **Given** the bundled proof cannot perform live validation, **When** it reaches the live boundary, **Then** it reports the affected stage as blocked or pending with enablement instructions and does not imply a pass.
3. **Given** a visitor is evaluating the repository, **When** they review the primary project page, **Then** they can identify the problem solved, view the proof, install the product, and find the next contribution path without navigating the full documentation tree.

---

### User Story 2 - Add Readiness to Change Review (Priority: P2)

A team can add Seshat BI to its change-review workflow and receive a concise readiness verdict that identifies changed evidence, blocking findings, affected stages, and the next allowed action.

**Why this priority**: A reusable review integration lets teams adopt the governance value without first adopting the entire example repository or learning every internal command.

**Independent Test**: Evaluate one compliant change and one gate-violating change in a sample repository and verify that reviewers receive distinct, actionable outcomes.

**Acceptance Scenarios**:

1. **Given** a change that preserves all readiness gates, **When** the review integration runs, **Then** it reports the checks performed and their evidence without claiming semantic correctness beyond those checks.
2. **Given** a change that introduces silver work before Mapping Ready is cleared, **When** the integration runs, **Then** it fails the review and names the violated gate, evidence, and corrective next action.
3. **Given** the same finding is present on repeated runs, **When** no material readiness state changes, **Then** the integration avoids posting duplicate review noise.
4. **Given** machine-readable findings are requested, **When** the review finishes, **Then** consumers receive stable finding identifiers, locations where available, severity, and supporting evidence.

---

### User Story 3 - Govern Other Agent Tools (Priority: P3)

An AI agent or agent host can ask Seshat BI what is currently allowed, why an action is blocked, what evidence exists, and which human decision is required before invoking a separate execution tool.

**Why this priority**: Seshat BI is most differentiated as the evidence and approval control plane around powerful analytics executors, not as another unrestricted executor.

**Independent Test**: Submit requests representing an allowed action, a premature action, and a human-owned judgment call; verify that the interface returns the correct action boundary without changing tracked artifacts or external systems.

**Acceptance Scenarios**:

1. **Given** a table with committed readiness evidence, **When** an agent requests its status and next action, **Then** it receives the current stage, evidence, blockers, allowed action, forbidden scope, and stop point.
2. **Given** Mapping Ready is blocked, **When** an agent asks whether it may create silver transformations, **Then** the interface refuses and cites the concrete blocking reasons.
3. **Given** a grain, PII, business-rollup, sentinel-vs-null, or metric-policy decision is unresolved, **When** an agent requests approval, **Then** the interface prepares a decision request for a named human role and does not grant the approval.
4. **Given** an agent invokes any v1 governance operation, **When** the operation completes, **Then** no database write, analytics execution, Power BI modification, publish action, or readiness-stage promotion has occurred.

---

### User Story 4 - Carry Verifiable Readiness Evidence (Priority: P4)

A reviewer can export and inspect a portable readiness passport that records the evidence behind a table's current state and can detect when referenced artifacts have changed.

**Why this priority**: Portable evidence makes readiness useful across agent sessions, review systems, audit handoffs, and delivery teams without creating a second source of truth.

**Independent Test**: Export a passport, verify it against unchanged artifacts, modify a referenced artifact, and verify that the passport becomes stale without changing the authoritative readiness status.

**Acceptance Scenarios**:

1. **Given** a table with committed readiness artifacts, **When** a passport is exported, **Then** it records the stage statuses, evidence references, blockers, approval receipts, validation boundary, artifact identities, and generation time.
2. **Given** a referenced artifact changes after export, **When** the passport is verified, **Then** it reports the affected evidence as stale or mismatched.
3. **Given** a passport contains a recorded human approval, **When** it is inspected, **Then** the record identifies the declared owner and source artifact but is never interpreted as Seshat granting approval.
4. **Given** a consumer cannot access a referenced artifact, **When** verification runs, **Then** the result is unknown or blocked rather than pass.

---

### User Story 5 - Extend Seshat Through Governed Packs (Priority: P5)

A domain contributor can create, validate, document, and share a narrowly scoped extension pack containing reusable retail knowledge or compatibility material without modifying the readiness spine or core authority.

**Why this priority**: A pack ecosystem creates meaningful contribution surfaces for BI practitioners, consultants, and data engineers while preventing one worked example from becoming a universal schema.

**Independent Test**: Validate one conforming sample pack and several deliberately invalid packs, then use the valid pack in a fresh workspace without changing core readiness rules.

**Acceptance Scenarios**:

1. **Given** a contributor wants to add a KPI, source-system vocabulary, warehouse compatibility, regional policy, accessibility aid, or dashboard blueprint pack, **When** they scaffold a pack, **Then** they receive the minimum required metadata, artifact locations, fixtures, tests, ownership declarations, and scope boundaries.
2. **Given** a pack attempts to redefine stage order, self-grant approval, embed secrets, or claim a universal retail schema, **When** it is validated, **Then** validation fails with an actionable reason.
3. **Given** a valid pack is absent, **When** the core product runs, **Then** all core readiness behavior remains available.
4. **Given** two packs declare incompatible ownership or identifiers, **When** both are selected, **Then** the conflict is reported before either can influence an output.

---

### User Story 6 - Make a First Contribution Safely (Priority: P6)

A first-time contributor can select a small, well-bounded task, understand its readiness impact, run the necessary checks, and submit a reviewable change without reading the entire repository.

**Why this priority**: More documentation alone does not reduce contribution friction; newcomers need prepared work units with explicit scope, evidence, and verification.

**Independent Test**: Ask a contributor unfamiliar with the repository to complete a starter task using only the issue, contributor quick path, and referenced local files.

**Acceptance Scenarios**:

1. **Given** a newcomer opens the contribution entry point, **When** they choose a task type, **Then** they see its expected files, forbidden scope, acceptance criteria, verification commands, and maintainer contact path.
2. **Given** a person reports a defect, proposes a pack, requests compatibility, or offers a starter contribution, **When** they open an issue, **Then** the submission captures the structured information required for triage.
3. **Given** a pull request is opened, **When** the contributor prepares its description, **Then** they are prompted to declare the readiness stage served, evidence provided, tests run, human decisions needed, and whether secrets or real data are absent.
4. **Given** a starter issue is advertised, **When** a newcomer accepts it, **Then** its write scope is small, its outcome independently testable, and its expected maintainer response is stated.

---

### User Story 7 - Compare Agent Safety Behavior (Priority: P7)

An evaluator can run a public set of synthetic retail scenarios against an agent-driven workflow and inspect whether the workflow proceeds, refuses, blocks for evidence, or requests a human decision at the correct boundary.

**Why this priority**: A transparent benchmark can make Seshat's safety model discoverable beyond Power BI while producing useful fixtures and contribution opportunities.

**Independent Test**: Run the published scenarios against a scripted reference participant and verify the categorical outcomes against the expected decision matrix.

**Acceptance Scenarios**:

1. **Given** scenarios for ambiguous grain, hidden PII, fan-out joins, returns semantics, currency misuse, missing metric approval, and premature dashboard work, **When** a participant is evaluated, **Then** each scenario records the observed action and expected boundary.
2. **Given** a participant produces an incorrect or unverifiable answer, **When** results are rendered, **Then** the result shows the evidence and mismatch without converting readiness into a numeric confidence score.
3. **Given** an evaluator uses a stochastic agent, **When** results are published, **Then** the agent, model, instructions, run conditions, repetition count, and observed variation are disclosed.
4. **Given** a community member contributes a scenario, **When** it is reviewed, **Then** it must use synthetic data, declare the principle tested, define observable expected behavior, and avoid vendor-specific favoritism.

---

### User Story 8 - Explore Readiness Without Runtime Access (Priority: P8)

A stakeholder can browse a static, shareable view of committed readiness artifacts, including table stages, blockers, evidence, approvals, and metric lineage, without receiving write access or connecting to a live data source.

**Why this priority**: A visual explorer makes the product understandable to non-CLI users and provides a useful project showcase while remaining a projection of committed truth.

**Independent Test**: Generate the explorer from the worked example, browse every displayed table and evidence link offline, and confirm the source readiness artifacts remain unchanged.

**Acceptance Scenarios**:

1. **Given** one or more valid table readiness records, **When** the explorer is generated, **Then** users can navigate a table-by-stage view and inspect evidence, blockers, approvals, next actions, and metric lineage.
2. **Given** an artifact is missing or malformed, **When** the explorer is generated, **Then** the affected view reports the problem and never substitutes an inferred pass.
3. **Given** sensitive connection details or local secrets exist outside committed artifacts, **When** the explorer is generated, **Then** they are not included.
4. **Given** a user interacts with the explorer, **When** they filter or navigate its content, **Then** no source artifact, readiness status, database, or Power BI model is modified.

### Edge Cases

- A repository contains no onboarded tables; first-success and explorer surfaces must show the truthful Source Ready onboarding action rather than an empty success.
- A readiness artifact uses an unsupported schema version; consumers must identify the incompatible version and stop rather than reinterpret it.
- Evidence references point outside the repository, to ignored files, or to missing paths; exports and views must mark them unavailable and must not expose local absolute paths.
- A review run has static success but lacks a required live validation; the result must distinguish static cleanliness from semantic or live correctness.
- A human approval receipt is malformed, anonymous, expired by policy, or disconnected from its decision artifact; it must not satisfy the approval requirement.
- A pack is valid in isolation but conflicts with another selected pack; the combined selection must fail closed with both owners identified.
- A benchmark participant refuses every scenario; results must show over-refusal rather than treating refusal as universal success.
- Generated public artifacts contain high-cardinality source values or possible PII; generation must omit the values and report the disclosure boundary.
- The public proof is run without network access or optional dependencies; the offline path must remain usable and truthful.

## Requirements *(mandatory)*

### Functional Requirements

#### Shared Product Contract

- **FR-001**: Every capability in this initiative MUST preserve the seven readiness stages and their required order.
- **FR-002**: Every readiness outcome MUST use status, evidence, and blocking reasons; no capability may emit or imply a readiness confidence score.
- **FR-003**: No capability may grant a human-owned approval or infer approval from a successful automated check.
- **FR-004**: Every pass claim MUST cite inspectable evidence, and every blocked claim MUST state at least one concrete blocking reason.
- **FR-005**: Derived views and exports MUST remain projections of authoritative committed artifacts and MUST NOT become a second readiness state engine.
- **FR-006**: Static success MUST be distinguished from live validation and semantic correctness wherever the latter have not been proven.
- **FR-007**: Public and generated artifacts MUST exclude secrets, real connection strings, unapproved raw data, and local absolute paths.
- **FR-008**: Every capability MUST expose a clear stop point and MUST name any action that remains forbidden at the current stage.

#### First-Success Proof

- **FR-009**: The product MUST provide a public first-success path that requires no database, credentials, external service, or Power BI Desktop.
- **FR-010**: The first-success output MUST display all seven stages, current evidence, blockers, next allowed action, and the live-validation boundary.
- **FR-011**: The first-success path MUST complete from a clean supported environment in no more than five user actions after prerequisites are present.
- **FR-012**: Public project information MUST provide a concise product description, discoverable domain topics, installation status, proof entry point, contribution entry point, and current capability boundaries.

#### Change-Review Integration

- **FR-013**: Teams MUST be able to add a reusable Seshat readiness check to a change-review workflow without copying Seshat source code into their repository.
- **FR-014**: The review result MUST identify checks run, changed readiness state, blocking findings, affected stages, evidence, and next action.
- **FR-015**: The review integration MUST provide stable machine-readable findings suitable for review annotations and retained run evidence.
- **FR-016**: Repeated review runs MUST avoid duplicate human-facing messages when no material result changed.
- **FR-017**: The review integration MUST fail closed when its required readiness inputs are malformed or when a prohibited stage transition is detected.

#### Agent Governance Interface

- **FR-018**: An agent host MUST be able to request readiness status, next allowed action, blocker explanation, approval-request preparation, static governance results, and evidence-pack export through a stable tool contract.
- **FR-019**: The initial agent governance interface MUST be read-only with respect to tracked files, databases, analytics models, reports, external services, approvals, and readiness stages.
- **FR-020**: Every agent-facing response MUST distinguish observed facts, derived conclusions, unresolved human decisions, and unavailable evidence.
- **FR-021**: Requests that cross a hard stop MUST return a refusal containing the violated rule, evidence state, required owner where applicable, and allowed recovery action.
- **FR-022**: The agent interface MUST remain useful when an optional execution or data-access tool is unavailable.

#### Readiness Passport

- **FR-023**: Users MUST be able to export a portable readiness passport for one table or a declared set of tables.
- **FR-024**: A passport MUST include artifact identities, readiness statuses, evidence references, blocking reasons, approval receipts, validation boundaries, source revision, generation time, and compatibility version.
- **FR-025**: Users MUST be able to verify whether a passport still matches its referenced artifacts.
- **FR-026**: Passport verification MUST report missing, changed, incompatible, and unverifiable evidence distinctly from verified evidence.
- **FR-027**: A passport MUST explicitly state that it records approvals and evidence but does not grant approval or independently advance readiness.

#### Governed Extension Packs

- **FR-028**: Contributors MUST be able to scaffold and validate extension packs for declared supported categories without changing the core readiness spine.
- **FR-029**: Each pack MUST declare identity, version, category, owner, compatibility, included artifacts, required human decisions, fixtures, verification evidence, and explicit non-goals.
- **FR-030**: Pack validation MUST reject secret material, real client data, self-approval, universal-schema claims, stage reordering, identifier collisions, and undeclared authority.
- **FR-031**: The core product MUST operate when no extension pack is installed.
- **FR-032**: Pack conflicts and compatibility failures MUST be reported before pack content contributes to a readiness output.
- **FR-033**: At least one generic reference pack MUST demonstrate the full contributor path without relying on C086 or another client-specific schema.

#### Contributor Experience

- **FR-034**: The repository MUST provide structured entry paths for defect reports, capability proposals, pack proposals, compatibility reports, and starter contributions.
- **FR-035**: The repository MUST provide a pull-request evidence prompt covering readiness stage, scope, tests, evidence, human decisions, and secret/data safety.
- **FR-036**: Starter contributions MUST declare a narrow write scope, independent acceptance test, expected verification, forbidden scope, and expected maintainer response.
- **FR-037**: A newcomer MUST be able to identify and begin a suitable starter contribution without reading the constitution, roadmap, or complete specification archive.

#### Agent-Safety Benchmark

- **FR-038**: The benchmark MUST contain synthetic scenarios covering every hard stop and representative retail semantic failure classes.
- **FR-039**: Each scenario MUST declare its input, expected categorical behavior, principle tested, observable evidence, and acceptance conditions.
- **FR-040**: Benchmark results MUST show scenario-level outcomes and evidence without creating a numeric readiness score or presenting stochastic behavior as deterministic proof.
- **FR-041**: Published stochastic-agent results MUST disclose participant identity, instructions, run conditions, repetition count, and observed variation.
- **FR-042**: Community benchmark submissions MUST be vendor-neutral, reproducible where practical, free of real client data, and reviewable independently.

#### Static Readiness Explorer

- **FR-043**: Users MUST be able to generate a static readiness explorer solely from committed, permitted artifacts.
- **FR-044**: The explorer MUST show table-by-stage status, evidence, blockers, approval records, next actions, and available metric lineage.
- **FR-045**: The explorer MUST represent missing, invalid, stale, and pending-live evidence explicitly and MUST never infer a pass.
- **FR-046**: The explorer MUST remain read-only and usable without database, Power BI, or repository write access.
- **FR-047**: Public explorer output MUST pass a disclosure review that prevents secrets, connection details, raw source values, PII, and local paths from being included.

#### Clarified Release and Trust Boundaries

- **FR-048**: The eight user journeys MUST remain independently releasable in priority order, with User Story 1 constituting the minimum viable release.
- **FR-049**: The initial agent governance interface MUST read only an explicitly selected local workspace and MUST NOT retrieve remote content or invoke an execution surface.
- **FR-050**: The initial pack capability MUST accept only packs selected from an explicit local source; discovery or installation from a public registry is out of scope until a separate trust decision is approved.
- **FR-051**: Passports and explorer output MUST remain local by default; any publication MUST require an explicit user action after the applicable disclosure checks pass.

### Key Entities

- **Readiness Result**: A stage-bound outcome containing status, evidence, blocking reasons, next action, forbidden scope, and stop point.
- **Review Finding**: A stable, locatable governance observation with severity, evidence, affected readiness stage, and corrective action.
- **Agent Governance Request**: A read-only request for status, routing, explanation, approval preparation, checking, or evidence export, together with its declared scope.
- **Readiness Passport**: A portable snapshot of referenced readiness evidence and artifact identities that can be verified for staleness but cannot grant authority.
- **Extension Pack**: A versioned, owned bundle of domain or compatibility artifacts that extends supported content without changing core readiness law.
- **Pack Compatibility Declaration**: The supported product range, dependencies, conflicts, and authority boundaries for an extension pack.
- **Contribution Lane**: A bounded category of newcomer work with expected files, verification, acceptance criteria, and forbidden scope.
- **Benchmark Scenario**: Synthetic inputs, expected categorical behavior, governing principle, and observable evidence for evaluating an agent-driven workflow.
- **Benchmark Run**: The disclosed participant, conditions, repetitions, scenario observations, and variation for one evaluation session.
- **Explorer Projection**: A generated, read-only representation of committed readiness artifacts with disclosure-safe navigation metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 90% of first-time evaluators in a moderated test can reach and correctly explain the bundled readiness result within five minutes without external services.
- **SC-002**: The first-success path requires no more than five user actions after documented prerequisites are available and produces no false pass across the offline boundary test suite.
- **SC-003**: A team unfamiliar with the codebase can add the reusable review check to a sample repository in under ten minutes and correctly distinguish a compliant change from each seeded hard-stop violation.
- **SC-004**: All agent governance contract tests demonstrate zero tracked-file writes, database writes, model/report mutations, publish actions, self-granted approvals, and readiness-stage promotions.
- **SC-005**: Passport verification detects 100% of seeded missing, changed, incompatible, and unverifiable evidence cases while accepting all unchanged reference cases.
- **SC-006**: At least three independently authored reference packs from different supported categories pass the same conformance process without core-code modification.
- **SC-007**: At least 80% of first-time contributors in a usability test can identify a suitable starter task, locate its scoped files, and run its required verification without reading more than three linked documents.
- **SC-008**: The benchmark covers all named hard stops and at least six retail semantic failure classes, with every scenario independently reproducible against the scripted reference participant.
- **SC-009**: Benchmark result reviewers can identify the expected boundary, observed behavior, and supporting evidence for every scenario without interpreting a numeric readiness score.
- **SC-010**: The explorer renders all valid worked-example readiness artifacts and reports 100% of seeded missing, malformed, stale, and pending-live cases without altering source artifacts.
- **SC-011**: Automated disclosure tests and human review find zero secrets, real connection strings, raw client records, PII values, or local absolute paths in public proof, passport, benchmark, review, and explorer fixtures.
- **SC-012**: Within 90 days of public availability, the project records at least five external issue participants, three external pull requests, and three independent installations that complete the first-success path; these are adoption indicators, not readiness scores.

## Assumptions

- This specification defines one product-level growth initiative. Each prioritized user story is independently deliverable and may become its own implementation phase or follow-on feature during planning.
- The public beta installation work remains a dependency; this initiative does not claim a package or marketplace is available before publication is verified.
- The existing readiness status, static checks, next-action surface, evidence packs, demo harness, worked examples, and JSON findings are reused as authoritative inputs rather than reimplemented.
- The initial agent governance interface is a read-only companion. F016 remains the only execution/publish adapter and stays gated on the required readiness state and human approvals.
- Delivery follows the user-story priority order as independently releasable phases; User Story 1 is the minimum viable release.
- Pack acquisition is local and explicit in the initial release. A public registry, remote discovery, signing authority, and automatic pack updates are deferred.
- Passport and explorer generation is local by default. Hosting or publication occurs only through an explicit user-selected action after disclosure checks pass.
- Public demonstrations and benchmark data are synthetic and generic. C086 remains a worked example, never a schema.
- Product analytics needed for SC-012 will use public repository activity and explicitly volunteered installation confirmations; no hidden user telemetry is required.
- Numeric operational counts may measure adoption and test coverage, but no numeric value may be presented as readiness confidence or substitute for status, evidence, and blockers.
- Wider runtime compatibility may be assessed separately; this feature does not silently lower the currently declared runtime requirement.
