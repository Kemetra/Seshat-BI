# Phase 0 Research: Agent Ecosystem Growth

## R1 - First-Success Boundary

**Decision**: Build on spec 119's package and clean-install journey. US1 adds a static
HTML proof to `demo report`; it does not introduce another installer or workspace state.

**Rationale**: Package identity, Windows smoke testing, and `status`/`next` already exist.
The missing adoption surface is visible proof, not another bootstrap mechanism.

**Alternatives rejected**:

- Hosted playground: introduces operations, privacy, and a second runtime before demand.
- New demo state engine: would conflict with the committed readiness authority.
- Fake all-seven-stage pass: violates the live-validation boundary.

## R2 - Agent Protocol and Transport

**Decision**: Use the official stable Python MCP SDK v1 line with an optional dependency
constraint `mcp>=1.28,<2`. Support stdio only in v1. Expose structured results validated
by output schemas and mark every tool read-only; enforce read-only behavior in code rather
than trusting annotations.

**Rationale**: The official SDK identifies v1 as the stable production line and warns
that v2 is pre-release. MCP defines stdio as a standard transport clients should support.
The tool specification requires input validation and output sanitization and treats tool
annotations as untrusted metadata.

**Alternatives rejected**:

- MCP SDK v2 pre-release: breaking-change risk during this feature.
- Hand-rolled JSON-RPC: forks protocol behavior and increases security risk.
- Streamable HTTP: contradicts the clarified local-only boundary and adds authorization,
  origin validation, service lifecycle, and remote exfiltration risk.

## R3 - Change-Review Distribution and SARIF

**Decision**: Keep the canonical composite action under `integrations/github-action/`.
It installs a released Seshat version, runs existing gates, emits a stable JSON artifact
and job summary, and optionally emits SARIF 2.1.0. A separate Marketplace repository is
deferred; if approved, it must be a generated one-way wrapper.

**Rationale**: GitHub accepts SARIF 2.1.0 for third-party findings, but upload availability
depends on repository visibility and code-security configuration. Therefore SARIF cannot
be the only result channel. GitHub recommends a dedicated action repository for
Marketplace publication, which conflicts with single-source authority unless generated.

**Alternatives rejected**:

- PR-comment bot with write token: unnecessary permissions and duplicate-noise risk.
- SARIF-only output: excludes consumers without code-scanning upload.
- Independently maintained action repository: creates a second product authority.

## R4 - Duplicate-Noise Control

**Decision**: Compute a deterministic review digest from normalized finding identifiers,
locators, severity, stage, and blocker text. The action always updates its job summary but
does not create or update PR comments in v1.

**Rationale**: Job summaries and check annotations are native to the run. Avoiding comment
writes satisfies the no-duplicate requirement with lower permissions.

## R5 - Passport Identity and Verification

**Decision**: Identify evidence with repository-relative POSIX paths, SHA-256 content
hashes, declared artifact kind, and optional source revision. Verification is local and
categorical: `verified`, `changed`, `missing`, `incompatible`, or `unavailable`.

**Rationale**: Content identity detects staleness without signing authority, network
access, or a new source of truth. Relative paths avoid machine disclosure.

**Alternatives rejected**:

- Digital signatures in v1: requires unresolved key ownership and trust policy.
- Modification times: machine-dependent and weak evidence.
- Embedded artifact contents: increases disclosure and package-size risk.

## R6 - Extension Pack Mechanism

**Decision**: Packs are declarative local directories validated against a versioned
manifest. Load only explicitly selected paths. Pack content may include supported YAML,
JSON, Markdown, fixtures, and static assets; it cannot include executable hooks. Use no
automatic Python entry-point discovery in v1.

**Rationale**: PyPA entry points are appropriate for installed executable plugins, but
loading third-party code is unnecessary for the requested knowledge-pack categories and
would violate the smallest trust boundary. A future executable adapter SDK requires its
own security decision.

**Alternatives rejected**:

- Public registry: explicitly deferred by clarification.
- Naming-convention discovery: silently broadens installed-code trust.
- Arbitrary scripts in packs: makes validation incapable of proving read-only behavior.

## R7 - Pack Conflicts

**Decision**: Every exported identifier is namespaced by pack ID. Packs declare
`provides`, `requires`, and `conflicts`. Validation builds a selection graph, rejects
cycles, duplicate fully qualified IDs, incompatible core ranges, and authority claims.

**Rationale**: Conflict detection before projection keeps packs additive and prevents
load-order behavior from becoming hidden policy.

## R8 - Benchmark Semantics

**Decision**: Benchmark scenarios define an expected categorical behavior from
`proceed`, `refuse`, `block_for_evidence`, or `request_human_decision`. Results show a
scenario matrix and evidence. No aggregate score or ranking is produced. Stochastic runs
record participant, model, instructions digest, environment, repetitions, and every
observed outcome.

**Rationale**: This evaluates boundary behavior without presenting a stochastic LLM as a
deterministic CI oracle or confusing benchmark points with readiness confidence.

**Alternatives rejected**:

- Single numeric leaderboard: conflicts with the product's no-score semantics and hides
  over-refusal.
- Live-agent CI gate: flaky and unable to prove emergent behavior deterministically.

## R9 - Static Explorer Architecture

**Decision**: Build a disclosure-filtered JSON projection, then render self-contained
static HTML/CSS/JS. Generation and browser interaction are read-only. Default output is
local and gitignored; publication is a separate explicit user action after disclosure
validation. Reuse the existing brand assets.

**Rationale**: A static site is inspectable, host-agnostic, offline-capable, and needs no
authentication or runtime service. A shared projection lets the demo and explorer reuse
the same truth without sharing UI concerns.

**Alternatives rejected**:

- Hosted API/dashboard: creates availability, authentication, and secret-management work.
- Client-side parsing of arbitrary repository files: expands disclosure surface.
- Power BI report as the explorer: requires the gated execution environment.

## R10 - Schema Compatibility

**Decision**: All new JSON contracts use `schema_version` as `MAJOR.MINOR`. Minor versions
are additive; consumers ignore unknown optional fields. Removed/renamed fields or changed
semantics require a major version. Unknown major versions fail closed.

**Rationale**: Matches the shipped review-pack compatibility discipline and supports
independent release phases without silent reinterpretation.

## R11 - Contributor Surfaces

**Decision**: Add structured issue forms for defects, capabilities, pack proposals,
compatibility reports, and starter tasks plus one PR template. Starter work must declare
write scope, forbidden scope, verification, acceptance evidence, and response expectation.

**Rationale**: Structured forms make external reports actionable. They complement rather
than duplicate `CONTRIBUTING.md`.

## R12 - Privacy and Telemetry

**Decision**: Collect no hidden telemetry. The 90-day adoption criterion uses public
repository activity plus explicitly volunteered install confirmations. All generated
artifacts pass a shared disclosure scanner before any explicit publication step.

**Rationale**: This aligns with local-first use and avoids creating a privacy policy and
service solely to count adoption.
