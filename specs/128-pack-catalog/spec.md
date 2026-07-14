# Feature Specification: Public Extension-Pack Catalog

**Feature Branch**: `128-pack-catalog`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Public Extension-Pack Catalog (seshat pack search / inspect / add). Add community discovery over the existing declarative pack system. Discovery + retrieval layer only; reuse the shipped pack scaffold and validation. Start from a reviewed static git registry, not a hosted marketplace. Registry records must carry pack id, version, category, author, source, compatibility, hash, dependencies, conflicts, and verification state. Flow: search -> inspect -> fetch -> verify hash/schema -> existing validation -> explicit project addition. Packs must be declarative only (no executable code); fetching must not auto-activate; packs cannot grant readiness or approval; fail closed on invalid, incompatible, missing, or tampered packs; preserve contributor attribution."

## Clarifications

### Session 2026-07-14

- Q: How is the catalog's registry made available in v1 -- a hosted service, a
  dynamic index endpoint, or a static reviewed git artifact? -> A: A reviewed,
  version-controlled static git registry that ships as tracked repository text;
  no hosted marketplace, no always-on network service, no dynamic index in v1
  (Principle VIII static-first; deferred surfaces listed under Out of Scope).
  Recorded as auto-decision (recommended default).
- Q: What does `pack add` actually change, given the shipped pack system states
  "no install/activate verb by design" and "constructing a selection installs
  nothing"? -> A: `add` fetches verified pack content into the workspace as a
  reviewable, committed change (a git diff the user can inspect), then hands it
  to the existing pack validation. It creates NO hidden global activation state,
  persists no runtime toggle, and promotes no readiness stage. A fetched pack is
  inert content until an operator explicitly selects it for a projection, exactly
  as today. Recorded as auto-decision (recommended default, reconciles with the
  shipped pack model).
- Q: What shape is a pack's `verification state`? -> A: A categorical status from
  a fixed vocabulary (for example `reviewed` / `unreviewed` / `deprecated`) with
  supporting evidence, mirroring the readiness spine's status+evidence shape --
  NEVER a numeric score, rank, or percentage, and never self-granted by the tool.
  A named human reviewer sets `reviewed` by committing it into the git registry.
  Recorded as auto-decision (hard-stop `never_fabricate_a_confidence_score` +
  `never_self_grant_approval`).
- Q: Who authorizes a pack's `reviewed` verification state? -> A: A named human
  registry reviewer, expressed as a committed edit to the tracked git registry.
  The catalog tool NEVER sets or upgrades a verification state at runtime and
  NEVER treats absence of review as `reviewed`. Recorded as auto-decision
  (hard-stop `never_self_grant_approval`; Principle V).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover a Relevant Pack (Priority: P1)

A user who wants to extend Seshat BI with community knowledge (a KPI template
family, a source vocabulary, a warehouse-dialect note set, a regional-policy
note set, an accessibility guidance set, or a dashboard blueprint) can search
the reviewed catalog by keyword and category and see, for each match, the pack
identity, version, category, author, compatibility, and verification state --
without fetching, executing, or adding anything.

**Why this priority**: Discovery is the entry point of the whole journey and the
smallest independently valuable slice. A user who cannot find a relevant pack
never reaches inspect, fetch, or add. Search reads only committed registry
metadata, so it ships first and requires no fetch or validation machinery.

**Independent Test**: Point the catalog at a reviewed static registry containing
several pack records across categories, run a keyword-and-category search, and
verify that the returned matches carry identity, version, category, author,
compatibility, and verification state, and that no pack content is fetched or
executed by the search.

**Acceptance Scenarios**:

1. **Given** a reviewed registry with several pack records, **When** a user
   searches by a keyword that matches one pack, **Then** they see that pack's id,
   version, category, author, compatibility, and verification state, and no
   content is fetched.
2. **Given** the same registry, **When** a user filters by a category, **Then**
   only packs in that category are returned.
3. **Given** a search term that matches nothing, **When** the search runs,
   **Then** it returns an empty result set with a clear "no matches" outcome and
   does not fail or fetch anything.
4. **Given** a registry that contains a pack marked `unreviewed` or `deprecated`,
   **When** it appears in results, **Then** its verification state is shown
   plainly so the user is not misled into treating it as reviewed.

---

### User Story 2 - Inspect Before Retrieving (Priority: P2)

Before fetching anything, a user can inspect a single catalog record and see its
full declared shape: id, version, category, author, source, compatibility, hash,
declared dependencies, declared conflicts, verification state, and the human
decisions the pack expects its adopter to make -- so the user can judge fit and
risk before any content crosses into the workspace.

**Why this priority**: Inspection is the informed-consent step between finding a
pack and pulling its content. It depends on US1 (a record must be discoverable
first) and gates US3 (a user should be able to read a pack's declared
dependencies, conflicts, and verification state before fetching). It still reads
only registry metadata, so it needs no fetch or hashing machinery.

**Independent Test**: Select one pack id from a reviewed registry, run inspect,
and verify the complete metadata record (all required fields) is shown, that
declared dependencies and conflicts are listed, and that no content is fetched.

**Acceptance Scenarios**:

1. **Given** a pack id present in the registry, **When** a user inspects it,
   **Then** they see id, version, category, author, source, compatibility, hash,
   dependencies, conflicts, and verification state.
2. **Given** a pack that declares dependencies, **When** a user inspects it,
   **Then** the declared dependency pack ids are listed so the user understands
   what an add would also require.
3. **Given** a pack that declares conflicts, **When** a user inspects it,
   **Then** the declared conflicting pack ids are listed.
4. **Given** a pack id that is not in the registry, **When** a user inspects it,
   **Then** the catalog reports "not found" and does not attempt any retrieval.

---

### User Story 3 - Fetch, Verify, and Explicitly Add (Priority: P3)

A user who has decided to adopt a pack can fetch its declared content from the
registry-recorded source, have the catalog verify the content hash and schema
and run the existing pack validation, and -- only if every check passes -- add
the verified declarative pack into the workspace as a reviewable, committed
change. The add never auto-activates the pack, never grants any readiness or
approval, and creates no hidden global state.

**Why this priority**: This is the payoff of the journey but the highest-risk
slice: it is the only step that brings external content into the workspace, so
it carries the full fail-closed chain. It depends on US1 and US2 and is scoped
so that the add is explicit and the retrieved pack is handed to the ALREADY
SHIPPED validation rather than a new one.

**Independent Test**: With a reviewed registry entry whose recorded hash matches
its declarative content, run the fetch-verify-add flow and confirm the pack
content lands in the workspace as a reviewable change, that the existing pack
validation ran and passed, that no activation state was written, and that no
readiness stage advanced. Then corrupt the content so the hash no longer matches
and confirm the add is refused.

**Acceptance Scenarios**:

1. **Given** a reviewed pack whose recorded hash matches its declarative content
   and whose compatibility matches this core, **When** the user runs add, **Then**
   the catalog fetches the content, confirms the hash, confirms the content is
   schema-valid, runs the existing pack validation, and adds the pack as a
   reviewable workspace change with a clear success outcome.
2. **Given** a pack whose fetched content does not match its recorded hash,
   **When** the user runs add, **Then** the catalog refuses, reports a tamper
   finding naming the pack, and adds nothing to the workspace.
3. **Given** a pack whose recorded compatibility does not match this core,
   **When** the user runs add, **Then** the catalog refuses, reports an
   incompatibility finding, and adds nothing.
4. **Given** a pack whose declared source or content cannot be located, **When**
   the user runs add, **Then** the catalog refuses, reports a missing-content
   finding, and adds nothing.
5. **Given** a pack whose content passes the hash check but fails the existing
   pack validation (for example, it declares executable wiring, a stage change,
   or an authority claim), **When** the user runs add, **Then** the catalog
   refuses on the validation findings and adds nothing.
6. **Given** a pack that adds cleanly, **When** the add completes, **Then** no
   pack has been activated, no readiness stage has advanced, no approval has been
   granted, and the added content is inert until an operator explicitly selects
   it for a projection.
7. **Given** a pack that declares a dependency, **When** the user adds it,
   **Then** the catalog surfaces the declared dependency (via the existing
   selection validation) so the user knows the dependency must also be present
   and does not silently pull it.

---

### Edge Cases

- **Duplicate ids across registry records**: two records claiming the same pack
  id at the same version MUST be treated as a registry defect and reported; the
  catalog MUST NOT silently pick one.
- **Registry file unreadable, non-UTF-8, or not a mapping**: fail closed with a
  disclosure-safe message; no partial results.
- **Registry record missing a required field** (id, version, category, author,
  source, compatibility, hash, dependencies, conflicts, verification state): the
  record is invalid; it MUST NOT appear as an addable pack.
- **Hash present but content absent** (dangling source): missing-content
  refusal.
- **Content present but no recorded hash**: MUST fail closed -- an unverifiable
  pack is not addable.
- **Verification state absent or unrecognized**: treated as NOT reviewed; the
  catalog MUST NOT assume `reviewed`.
- **Pack whose source path escapes the workspace or registry root**: containment
  refusal (reuse the existing path-containment guard).
- **Secret-bearing content** (a credential-shaped string in fetched content):
  disclosure refusal (reuse the existing disclosure scan).
- **Empty registry**: search returns no matches; inspect/add of any id returns
  "not found". The core operates normally with an empty catalog.
- **A pack already present in the workspace**: add MUST detect the existing
  content and MUST NOT silently overwrite it; it reports the collision.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The catalog MUST index packs from a reviewed, version-controlled
  static git registry expressed as tracked repository text. It MUST NOT require a
  hosted marketplace, a dynamic index endpoint, or an always-on network service
  in v1.
- **FR-002**: Each registry record MUST carry all of: pack id, version, category,
  author, source, compatibility, content hash, declared dependencies, declared
  conflicts, and verification state. A record missing any required field is
  invalid and MUST NOT be presented as an addable pack.
- **FR-003**: The registry index MUST be validated against a NEW registry-index
  schema using the EXISTING JSON-contract validation utility. This index schema
  describes metadata ABOUT packs; it MUST NOT replace, duplicate, or compete with
  the existing extension-pack manifest schema, which continues to govern pack
  CONTENT unchanged.
- **FR-004**: `search` MUST match registry records by keyword and MUST support
  filtering by category, reading only committed registry metadata. It MUST NOT
  fetch, execute, or add any pack content.
- **FR-005**: `search` results MUST display, per match, at least the pack id,
  version, category, author, compatibility, and verification state.
- **FR-006**: `inspect` MUST show the complete metadata record for one pack id --
  id, version, category, author, source, compatibility, hash, dependencies,
  conflicts, and verification state -- reading only committed registry metadata
  and fetching no content.
- **FR-007**: The retrieval flow MUST proceed strictly as search -> inspect ->
  fetch -> verify hash -> verify schema -> existing pack validation -> explicit
  project addition. No later step may run before every earlier gate passes.
- **FR-008**: `add` MUST verify that the fetched content's computed hash equals
  the registry-recorded hash before any content is added. On mismatch it MUST
  refuse, report a tamper finding naming the pack, and add nothing.
- **FR-009**: `add` MUST verify the fetched content is schema-valid against the
  EXISTING extension-pack manifest schema and MUST hand the content to the
  EXISTING pack validation (single-pack validation plus selection validation for
  dependencies and conflicts) before adding. It MUST NOT introduce a second pack
  validator or a second pack format.
- **FR-010**: `add` MUST fail closed on any of: unknown pack id, hash mismatch
  (tamper), schema-invalid registry record, schema-invalid pack content,
  incompatible core compatibility, missing/dangling source or content, a
  containment escape, a disclosure (secret) finding, or any existing-validation
  finding. On any such condition it MUST add nothing and report a
  disclosure-safe finding.
- **FR-011**: Fetching content MUST NOT automatically activate the pack. A
  fetched-and-added pack is inert declarative content; it becomes part of a
  projection only when an operator explicitly selects it, exactly as with the
  existing local pack selection.
- **FR-012**: `add` MUST NOT create hidden global activation state, MUST NOT
  persist a runtime toggle, and MUST NOT modify any readiness state. The only
  effect of a successful add is a reviewable change to workspace content that the
  user can inspect and commit.
- **FR-013**: No catalog operation MAY grant, advance, or imply any readiness
  stage or approval. Adding a pack MUST leave every readiness stage exactly as it
  was (Principle V; hard-stop `never_self_grant_approval`).
- **FR-014**: Retrieved and added pack content MUST be declarative only. The
  existing pack validation's rejection of executable wiring, stage changes, and
  authority claims MUST be enforced as part of the add gate; the catalog MUST NOT
  fetch or add any content that would bypass it.
- **FR-015**: `verification state` MUST be a categorical status drawn from a fixed
  vocabulary with supporting evidence. It MUST NOT be expressed as a numeric
  score, percentage, rank, or leaderboard position (hard-stop
  `never_fabricate_a_confidence_score`).
- **FR-016**: The catalog MUST NOT set, upgrade, or self-grant a pack's
  verification state at runtime. A `reviewed` state is authored by a named human
  reviewer as a committed edit to the tracked git registry; absence of an
  explicit review MUST be treated as NOT reviewed (hard-stop
  `never_self_grant_approval`; Principle V).
- **FR-017**: The catalog MUST preserve contributor attribution: the registry
  record's `author` MUST be carried through search, inspect, and add outputs and
  MUST NOT be stripped, overwritten, or conflated with the pack manifest's
  content `owner`. Both attributions are retained.
- **FR-018**: All catalog operations MUST be read-only with respect to external
  systems except for the explicit, user-initiated `add`, whose only write is
  local workspace content. No catalog operation MAY write to a database, execute
  analytics, modify a Power BI model, publish anything, or promote a readiness
  stage.
- **FR-019**: Every failure MUST be reported with a disclosure-safe message that
  never leaks a credential, absolute host path, or connection string, reusing the
  existing disclosure-safe finding shape.
- **FR-020**: Duplicate registry records for the same pack id and version MUST be
  reported as a registry defect; the catalog MUST NOT silently choose one.
- **FR-021**: The catalog MUST operate correctly with an empty or absent registry:
  search returns no matches; inspect and add of any id return "not found"; the
  core product functions with zero packs cataloged or added.
- **FR-022**: `add` MUST NOT silently overwrite pack content already present in
  the workspace; a collision MUST be reported and the add refused unless the user
  has taken an explicit action to replace it.

### Reused / Anti-Reinvent Requirements

- **RR-001**: Pack CONTENT validation MUST reuse the shipped extension-pack
  validation (single-pack and selection). No second pack validator is created.
- **RR-002**: Pack CONTENT schema MUST reuse the shipped extension-pack manifest
  schema. No second pack format is created.
- **RR-003**: Path containment MUST reuse the shipped workspace-containment guard;
  the catalog does not implement its own path-escape check.
- **RR-004**: Secret/disclosure scanning MUST reuse the shipped disclosure scan.
- **RR-005**: Registry-index schema validation MUST reuse the shipped
  JSON-contract validation utility (the same utility the pack content schema is
  checked with), applied to the NEW registry-index schema.
- **RR-006**: The catalog MUST extend the existing `pack` verb group with the new
  `search` / `inspect` / `add` subcommands rather than introducing a parallel
  command surface. The shipped `scaffold` and `validate` subcommands are
  unchanged.

### Key Entities

- **Registry**: A reviewed, version-controlled static collection of pack records,
  expressed as tracked repository text. Made available offline via the checked-out
  repository; no hosted service.
- **Registry Record**: One metadata entry describing an available pack -- pack id,
  version, category, author, source, compatibility, content hash, dependencies,
  conflicts, and verification state. Metadata ABOUT a pack, distinct from the
  pack's own manifest.
- **Verification State**: A categorical, human-authored status (for example
  `reviewed` / `unreviewed` / `deprecated`) with evidence. Never a score; never
  self-granted by the tool.
- **Fetched Pack Content**: The declarative pack manifest plus artifacts retrieved
  from a record's source, hash- and schema-verified before it is handed to the
  existing validation and added.
- **Catalog Finding**: A disclosure-safe, categorical finding (unknown id, tamper,
  incompatible, missing, containment, disclosure, validation) that causes a
  fail-closed refusal.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can search a reviewed registry and see identity, version,
  category, author, compatibility, and verification state for every match without
  any pack content being fetched or executed.
- **SC-002**: A user can inspect any registry pack id and see the complete
  required-field record before any content crosses into the workspace.
- **SC-003**: A tampered pack (content that does not match its recorded hash) is
  refused by add in 100% of cases, with nothing added to the workspace.
- **SC-004**: An incompatible, missing-source, schema-invalid, secret-bearing, or
  containment-escaping pack is refused by add in 100% of cases, with nothing
  added.
- **SC-005**: A pack whose content would fail the existing pack validation is
  refused by add via that existing validation -- no separate validator produces
  the verdict.
- **SC-006**: After any successful add, no readiness stage has advanced, no
  approval has been granted, and no activation state has been written; the added
  content is inert until explicitly selected.
- **SC-007**: Contributor attribution (`author`) is present and unaltered in every
  search, inspect, and add output and is never conflated with the pack's content
  `owner`.
- **SC-008**: No verification state anywhere in the catalog output is a number,
  percentage, or rank.
- **SC-009**: The catalog is fully exercisable offline against a checked-out
  static registry, with no network service required in v1.

## Assumptions

- The existing shipped extension-pack system (declarative pack model, manifest
  schema, single-pack and selection validation, and the `pack` verb group with
  `scaffold` + `validate`) is the substrate this feature builds on; it is not
  re-implemented, re-schematized, or re-validated.
- The reviewed static git registry is a repository artifact reviewers curate by
  committing records; establishing the human review process and appointing
  reviewers are organizational actions outside this software's control (the
  software enforces that only human-authored review state is trusted).
- "Compatibility" reuses the pack-to-core contract already expressed by the
  shipped validation's core-compatibility check; the catalog compares the
  record's recorded compatibility against the same supported core contract line.
- Content hashing uses a standard, collision-resistant digest computed over the
  declarative content; the digest algorithm is an implementation detail settled at
  plan time, not a semantic decision.

## Dependencies

- Shipped extension-pack model, manifest schema, and validation (single-pack and
  selection).
- Shipped `pack` CLI verb group (extended, not replaced).
- Shipped workspace path-containment guard, disclosure scan, and JSON-contract
  validation utility.
- The readiness spine's status+evidence convention (for the shape of
  verification state) and the constitution's Principle V and the hard-stops
  `never_self_grant_approval` and `never_fabricate_a_confidence_score`.

## Out of Scope

- A hosted marketplace, a public web UI, a dynamic index/search API endpoint, or
  any always-on network service. v1 is a static reviewed git registry only
  (Principle VIII static-first; deferred until pack trust and compatibility are
  proven, per spec 120 US5's registry-deferral clarification).
- Automatic dependency resolution that silently fetches transitive packs. The
  catalog surfaces declared dependencies via the existing selection validation;
  the user adds each explicitly.
- Any activation, enablement, or global "installed packs" lifecycle. There is no
  activation state, by design, consistent with the shipped pack system.
- Any change to the shipped pack manifest schema, pack validation, or the
  `scaffold` / `validate` subcommands.
- Signing, key management, or a trust-web beyond content hashing and
  human-authored, committed verification state.
- Publishing, rating, download counts, popularity ranking, or any leaderboard.
- Live database, Power BI execution, or readiness-stage promotion of any kind.
