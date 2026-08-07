# Feature Specification: Capability ownership fields -- declaring who owns each agent-facing capability

**Feature Branch**: `142-capability-ownership-fields`

**Created**: 2026-08-07

**Status**: implemented -- all 31 tasks complete, 102/102 manifest entries declared

**Status history**: Ratified (Ahmed Shaaban, 2026-08-07) -- implementation permitted

**Status history**: Draft -- 2026-08-07, revised the same day after two review
passes (12 + 8 findings) and six owner rulings; ratified after both CRITICAL
findings were resolved at the design level.

**Source**: issue #592 section C, as re-scoped by `docs/capabilities/ownership-audit.md`

---

## Why this exists

`docs/capabilities/capabilities.yaml` is the committed control plane for every
agent-facing capability in this kit -- 102 entries, each classified by lifecycle
`state`, `authority`, `surface`, `requirements`, and `provenance`.

It cannot currently answer one question issue #592 asks: **who owns this
capability -- an upstream project, or Seshat?**

That question has operational consequences. When an agent needs a capability it
must know whether to invoke an official upstream surface or a Seshat one, and a
reviewer must be able to tell a legitimate governance wrapper from a fork of
somebody else's tool. Today neither is recorded anywhere in the manifest.

Partial data already exists in code but not in the manifest:
`src/seshat/integrations/catalog.py` declares the allowlisted upstream *sources*
at `:61-67` (`ALLOWLISTED_SOURCES`, a name-to-URL map covering PyPI,
`microsoft/skills-for-fabric`, `dbt-labs/dbt-agent-skills`, the npm registry,
and `seshat-bundled`), and the per-component records carrying coordinates and
release channels from `:149` onward. Both cover *installable dependencies* only.
No record says that (for example) `dbt-workflows` is a Seshat adapter over dbt
Labs' upstream surface.

The nearest existing manifest axis, `provenance`, tracks release-verification
(`locally-verified` / `unrecorded` / `publicly-released`), **not** authorship
origin. Reusing it would conflate two independent facts.

## What this feature is

One new **ownership axis** on the existing manifest: a small set of optional,
declared fields per entry that record who owns a capability, what upstream
surface it wraps (if any), and what Seshat adds on top.

It is a metadata migration over an existing control plane. It ships no new
command, no new gate, and no new score.

## What this feature is NOT

- **Not a gate.** It adds no `seshat check` rule and no `semantic-check` finding.
  Its presence or absence blocks nothing. (Issue #592 section D -- the overlap
  gate -- is explicitly out of scope; see Non-goals.)
- **Not a score.** No numeric ownership/maturity/confidence/completeness/health
  value is introduced anywhere, at any nesting depth. This is enforced
  structurally by O6 (see FR-008).
- **Not a readiness surface.** It reads no `readiness-status.yaml`, moves no
  stage, and grants no approval.
- **Not a deletion instrument.** Classifying an entry as a duplicate candidate
  records an opinion for human review; it removes nothing.
- **Not a second source of truth.** Where `catalog.py` already owns a fact about
  an installable dependency, this axis references it rather than restating it.
- **Not a new registry file.** The fields extend the existing manifest. Issue
  #592 section C proposed "a machine-readable registry (or extend
  capabilities.yaml)"; this spec takes the extend branch, because a parallel
  authority would create exactly the drift the issue is trying to eliminate.

## User scenarios

### US1 -- An agent routes a task to the right surface (Priority: P1)

An agent needs to run a dbt transformation. It reads the manifest, sees the
capability is owned upstream by dbt Labs and that Seshat's contribution is
Mapping-Ready gating plus parity evidence, and therefore invokes the official
dbt surface *through* the Seshat adapter rather than reimplementing either.

**Acceptance**: for every entry whose `capability_owner` is `official-upstream`
or `seshat-adapter`, the manifest names the upstream project and the Seshat
delta. An agent can answer "who executes this, and what must run around it?"
from the manifest alone.

### US2 -- A reviewer distinguishes a wrapper from a fork (Priority: P1)

A reviewer sees a Seshat skill that resembles an upstream capability. The
manifest declares it a `seshat-adapter` with a stated delta, so the reviewer can
judge whether that delta is real instead of guessing.

**Acceptance**: every entry declaring `seshat-adapter` carries a non-empty
`seshat_delta`. An adapter with no stated delta is visible as incomplete.

### US3 -- A maintainer sees which capabilities overlap (Priority: P2)

A maintainer auditing for redundancy can list entries flagged as overlapping
another, with the relationship stated, without re-deriving the audit by hand.

**Acceptance**: `overlap_note` may name a related capability `id` and the nature
of the relationship. It is advisory and drives no automated action.

### US4 -- The vendored-upstream question stays visible (Priority: P2)

`docs/capabilities/ownership-audit.md` raised one question: whether the
`speckit-*` skills (**14** of them, not 12 as that doc first said) are
unmodified upstream Spec Kit content. They are -- see OD-1, resolved. The axis
must be able to record "this is vendored upstream content, sanctioned, with this
update policy" as a durable, reviewable statement rather than a paragraph in an
audit doc.

**Acceptance**: `capability_owner: vendored-upstream` exists as a declarable
value, and the `speckit-*` aggregate entry can carry it pending human ruling.

## Requirements

### FR-001 -- The ownership fields

Each manifest entry carries an `ownership:` mapping. `capability_owner` is
REQUIRED on every entry (FR-002a) -- an unclassified entry declares the
`unclassified` sentinel rather than omitting the field. The other eight
sub-fields are OPTIONAL.

| Field | Type | Meaning |
| --- | --- | --- |
| `capability_owner` | token (FR-002) | who owns the capability |
| `upstream_project` | string | human-readable owning project, e.g. `dbt Labs` |
| `upstream_surface` | token (FR-003) | the form the upstream capability takes |
| `upstream_reference` | string | a URL or coordinate, e.g. `dbt-labs/dbt-agent-skills` |
| `seshat_delta` | string | what Seshat adds; required when `capability_owner` is `seshat-adapter` (FR-006) |
| `canonical_source` | string | repo-relative path of the authored source |
| `overlap_note` | string | advisory relationship to another capability |
| `update_policy` | string | how the capability is kept current |

Naming note: the field is `capability_owner`, not `ownership_maturity` or any
similar construction, because of FR-008.

### FR-002 -- `capability_owner` is a closed token set

Exactly one of:

- `official-upstream` -- an upstream project is authoritative; Seshat references
  or configures it and adds nothing of its own.
- `seshat-adapter` -- Seshat coordinates, gates, or governs an upstream
  capability without reimplementing its core behavior. Requires `seshat_delta`.
- `seshat-governance` -- readiness gates, approvals, evidence, policy, drift and
  lint checks, status and rule registries. Judges or records; does not produce a
  deliverable artifact.
- `seshat-authoring` -- **added during implementation.** Generates or scaffolds a
  Seshat artifact: DAX from an approved contract, a theme JSON from design
  tokens, blank Stage-1 templates, compiled output. Distinguished from
  `seshat-governance` because it *produces* rather than *judges*, and from
  `seshat-domain-knowledge` because it executes rather than reasons. Added after
  a surface-based fallback was shown unsound: it would have labelled
  `retail-theme-gen` and `retail-generate` as governance, which is false -- they
  gate nothing.
- `seshat-orchestrator` -- Seshat sequences or coordinates other Seshat
  capabilities and stops at human seams. Distinguished from `seshat-adapter`:
  an orchestrator coordinates *Seshat's own* verbs, an adapter wraps an
  *upstream* surface. An orchestrator therefore has no `upstream_project` and
  needs no `seshat_delta`.
- `seshat-domain-knowledge` -- BI/SQL/DAX/Python/retail reasoning that no
  upstream tool owns.
- `vendored-upstream` -- upstream content committed into this repo. Neutral on
  whether that is acceptable: `seshat_delta` or `update_policy` carries the
  justification and the re-vendor path.
- `seshat-product-module` -- an executable Seshat engine that runs code rather
  than encoding reasoning. Covers `surface: product-module` entries such as
  `governed-statistical-core`, which fit neither `seshat-domain-knowledge` (it
  executes) nor `seshat-governance` (it gates nothing).
- `human-deliverable` -- an artifact a human produces outside any tool, e.g.
  `surface: human-artifact` entries such as `f034-built-dashboard-page`. Owned by
  a person, not by code.
- `specified-not-built` -- a ratified or drafted specification with no
  implementation, e.g. spec-only `surface: docs` entries such as
  `kpi-derivation-lineage`. Ownership follows once it ships.
- `unclassified` -- **required sentinel.** Explicitly not yet classified, with the
  reason in `overlap_note`. See FR-002a.

An unrecognized token is a spec violation, reportable by the oracle (FR-009),
never silently accepted as meaningful.

### FR-002a -- `capability_owner` is required, and absence is never meaningful

Every entry MUST carry `ownership.capability_owner`. An entry not yet classified
carries the `unclassified` sentinel with a reason -- it does not omit the field.

Rationale: without this, absence is overloaded three ways -- not yet classified,
deliberately unclassified, or "no upstream owner, so this is Seshat's". The third
reading is the dangerous one. Mid-migration, `pbi-mcp-doctor` carrying no
`ownership` would read as Seshat-owned when it in fact wraps a Microsoft preview
MCP. A required sentinel makes that misreading structurally impossible instead of
merely documented, and makes a half-landed migration honest rather than
misleading.

This supersedes FR-001's "an entry omitting the mapping entirely remains valid"
for `capability_owner` specifically. The other eight sub-fields stay optional.

### FR-003 -- `upstream_surface` is a closed token set

One of `plugin`, `mcp`, `skill`, `cli`, `library`, `format`. `format` covers a
file format owned upstream but with no executable surface (e.g. PBIR).

### FR-004 -- Fields are additive and independently landable

Adding the `ownership` mapping to any subset of entries MUST NOT change the
behavior or output of any existing consumer. Verified pre-conditions on
`main` at `edfab33`:

- `src/seshat/capability_inventory.py:172-186` projects a fixed key list via
  `.get()`; unknown keys are dropped, never raised on.
- `src/seshat/allowlist_derivation.py` reads only `ships`,
  `references.skill`, `ship_classification`, and `id`; the derived allowlist is
  therefore byte-identical regardless of this axis.
- Because the derived allowlist is unchanged, every bundle byte,
  `source_sha256`, `output_sha256`, and `manifest_digest` is unchanged, so the
  `Generated agent bundle drift` gate (`.github/workflows/ci.yml:68-69`) is
  unaffected.
- Three contract tests read the manifest, all asserting named keys only, none
  with a key-set closure assertion: `test_capability_ship_classification.py`,
  `test_dbt_documentation.py` (which asserts on `dbt-transformation-adapter` --
  the very entry the pilot phase edits first), and
  `test_statistical_documentation.py`. All three MUST be in the gate set so the
  FR-004 proof actually exercises them.

Consequence: **no lockstep schema bump is required.** The migration may land
entry-by-entry.

### FR-005 -- `canonical_source` names the authored path; targets are NOT restated

Where an entry ships into the generated bundles, `canonical_source` names the
authored path it is generated *from*. It records the direction the existing
generator already enforces -- `build_bundle`
(`scripts/export_agent_bundles.py:602`) drives it, with the actual checks in
`_validate_source` (`:319`), `_validate_entry_policy` (`:358`), and
`_record_destinations` (`:397`). It introduces no new enforcement.

**A `generated_targets` field was specified and then removed.** Destination paths
are already owned by `distribution/public-knowledge-allowlist.yaml` `targets`
(itself derived from this manifest) and validated by `_record_destinations`. A
hand-written third copy would be exactly the "second source of truth" the
Non-goals forbid -- and unlike `upstream_reference`, which FR-007 binds to
`catalog.py`, nothing would bind it. If a destination changed, those entries would
lie silently while every gate stayed green. An entry's targets are derivable from
the allowlist on demand; they are not restated here.

### FR-006 -- A declared adapter states its delta

When `capability_owner` is `seshat-adapter`, `seshat_delta` MUST be present and
non-empty. This is the "every wrapper documents its Seshat-specific delta"
acceptance criterion from issue #592, expressed as a manifest property.

Reportable by the oracle (FR-009). It is **not** a `seshat check` rule.

### FR-007 -- No second authority for installable dependencies

Where `src/seshat/integrations/catalog.py` already declares an upstream
component, `upstream_reference` MUST match the coordinate declared there rather
than restating it in a divergent form. The manifest points at the catalog; the
catalog stays authoritative for installable dependencies.

Two limits on this rule, both verified in the catalog:

- **Bundled components carry no coordinate.** `seshat-dagster-adapter` and
  `dagster-skills` are Seshat-bundled, so there is nothing to match.
  `upstream_reference` MUST be omitted for them, not invented.
- **Where a project ships several coordinates**, `upstream_reference` names the
  one the capability actually consumes, not the project's whole set. For the dbt
  adapter that is the skill bundle and/or `dbt-mcp` it drives -- not
  `dbt-core`/`dbt-postgres`, which are runtime dependencies of the operator's
  environment rather than the wrapped surface.

### FR-008 -- The axis must not trip the numeric-axis oracle (O6)

`tests/unit/_capability_oracle.py` enforces two constraints across **every key
and every scalar at every nesting depth** of every entry:

- `_axis_numeric_field_names` (`:451-456`) fails if any key name contains any of
  `NUMERIC_FIELD_HINTS = ("score", "maturity", "confidence", "completeness", "health")`
  (case-insensitive substring).
- `_axis_numeric_scalars` (`:441-448`) fails if any scalar value is `int` or
  `float` (bools excepted).

Therefore this spec REQUIRES:

1. No field name in the ownership axis may contain any of those five substrings.
   This is why the field is `capability_owner` and not `ownership_maturity`.
2. No ownership field value may be a bare numeric scalar. Any version, year, or
   count MUST be a quoted string.
3. No ownership field value may contain the literals `c086`, `C086`, or
   `retail_store_sales`, which `tests/unit/test_capability_inventory.py:513-526`
   bans from the manifest's raw text.

These are not stylistic preferences. They are the structural expression of the
kit's `never_fabricate_a_confidence_score` hard-stop, and this axis is exactly
the kind of field that would tempt a numeric ownership rating.

### FR-009 -- Validation belongs to the oracle, not a gate

Token-set validity (FR-002, FR-003) and the adapter-delta requirement (FR-006)
are checked by extending `tests/unit/_capability_oracle.py`, which already walks
raw manifest entries and is the manifest's existing truthfulness authority.

No `seshat check` rule is added. Rationale: a static rule is nine wiring
surfaces, and per the kit's own evidence-gate discipline a rule needs a filled
target before it is worth building. That target does not exist until entries
carry values -- which is what this spec produces. Gating is therefore downstream
of this work, not part of it.

### FR-011 -- The axis ships with a reader

Three ownership fields -- `capability_owner`, `upstream_project`, and
`seshat_delta` -- MUST be surfaced by the existing inventory renderer:

- add them to `_RECORD_FIELDS` / `InventoryRecord` and `_project_record` in
  `src/seshat/capability_inventory.py`;
- mirror them into `DECLARED_RECORD_FIELDS` in `tests/unit/_capability_oracle.py`,
  which is deliberately an independent restatement rather than an import, so both
  sides must be updated and the closed-schema assertion at
  `tests/unit/test_capability_inventory.py:40` keeps its teeth.

Rationale: without a reader this axis is **write-only**. Verified: the closed
record schema excludes `ownership`, `_project_record` drops unknown keys, FR-009
defers gating, and `docs/capabilities/capabilities.yaml` ships in **neither**
generated bundle. Absent this requirement, the only code reading these fields
after the migration would be the oracle validating them against its own
constants -- data with no consumer.

The remaining six fields stay unrendered; they are provenance detail, not routing
signal. Shipping the manifest itself inside the bundles is explicitly **not**
required here -- that would change every bundle digest and force a re-baseline of
the drift gate.

### FR-010 -- Existing dead constants are not silently promoted

`src/seshat/capability_inventory.py:35-43` defines `_LIFECYCLE_STATES`,
`_AUTHORITIES`, `_SURFACES`, `_REQUIREMENTS`, `_PROVENANCES`. These are
currently **dead** -- referenced nowhere else in the module, enforcing nothing.
Evidence: a live entry carries `surface: product-module`, which is absent from
`_SURFACES` and causes no failure anywhere.

This spec MUST NOT quietly begin enforcing them as a side effect. If the
ownership tokens are added as a constant in that module, the pre-existing
fail-open MUST be recorded as a known finding rather than incidentally fixed,
so that a behavior change to five other axes is not smuggled into a metadata
migration.

## Success criteria

- **SC-001**: Every entry carries `ownership.capability_owner` (FR-002a). No entry
  omits it. Since `unclassified` is an explicit token, this is mechanically
  checkable and cannot be satisfied by silence.
  **Floor**: every entry whose token is `unclassified` carries an entry-specific
  reason in `overlap_note`. A boilerplate reason repeated across entries does not
  satisfy this criterion.
  Note: the earlier floor -- "only OD-1/OD-2 entries may be unclassified" -- was
  **withdrawn as unsatisfiable**. The source audit names only 41 of the 102
  manifest `id`s, so 61 entries have no audit-derived classification; a floor of
  ~5 was impossible by construction. Phase 4 is therefore re-derived from the
  **manifest**, not the audit, and the honest measure is that every entry is
  *declared* -- classified or explicitly `unclassified` with a reason.
- **SC-002**: Every entry declaring `seshat-adapter` carries a non-empty
  `seshat_delta`.
- **SC-003**: The four wrappers named in `ownership-audit.md` are classified
  `seshat-adapter` with their upstream project named. Note that audit prose uses
  *skill names*, which are not always manifest `id`s -- e.g. the PBIR adapter's
  manifest entry is `pbir-authoring-adapter-skill`, while
  `pbir-authoring-adapter` appears in six other entries only as a
  `references.skill` value. Each task MUST resolve the manifest `id` before
  editing, never match on the skill name alone.
- **SC-004**: `python scripts/export_agent_bundles.py --check` returns PASS and
  the bundle trees are byte-unchanged, proving FR-004 empirically rather than by
  assertion.
- **SC-005**: `seshat check` reports no new finding, and the pre-existing RS1
  warning is unchanged.
- **SC-006**: The oracle rejects an unknown `capability_owner` token and an
  adapter missing its delta, demonstrated by tests that fail before the
  validation is added.
- **SC-007**: No key name anywhere in the manifest contains `score`,
  `maturity`, `confidence`, `completeness`, or `health`, and no ownership value
  is a bare numeric scalar. O6 stays green.

## Non-goals

- **Issue #592 section D, the overlap gate.** Out of scope, and not merely for
  cost. A rule needs a filled target; until entries carry ownership *values*
  there is nothing for a rule to assert against. Section D is downstream of this
  spec, and specifying it here would inherit a nine-surface rule-wiring job
  inside a metadata migration.
- **Deleting, merging, or consolidating any capability.** The audit's REMOVE and
  MERGE rows stay candidates for human review. Consistent with issue #592's own
  Non-goals.
- **Ruling on the `speckit-*` vendored-upstream question.** This spec makes the
  question *recordable* (US4). Answering it is a human judgment.
- **Changing `provenance` semantics** or any existing field's meaning.
- **Vendoring any official plugin or MCP implementation.**
- **Enabling any write or publish behavior.**
- **Granting this spec implementation permission.** The fence carries exactly one
  plan path by contract (`tests/contract/test_dbt_documentation.py:131`). As of
  2026-08-07 the fence and `.specify/feature.json` do point at this spec -- moved
  by owner ruling when spec 138 was closed out -- but the fence text states
  explicitly that implementation is **NOT permitted** while this spec is Draft.
  Being the fence target is not ratification; a named human must ratify `spec.md`
  before any task in `tasks.md` is started.

## Decisions (all resolved 2026-08-07 by owner ruling)

### OD-1 -- `speckit-*` -- RESOLVED: `vendored-upstream`, not a violation

Investigated on owner direction. **There are 14 such skills, not 12** as earlier
documents stated. Findings:

- All 14 were written by upstream's own installer
  (`specify init --here --integration claude --script ps`, spec-kit `0.8.10`) in
  a single commit `1eb0c98`, and none has been edited since.
- Hash-verified: every file matches `.specify/integrations/claude.manifest.json`
  byte-for-byte. The five `speckit-git-*` skills were additionally byte-diffed
  against the local upstream source under `.specify/extensions/git/commands/`;
  the only deltas are added frontmatter and one literalized placeholder.
- No Seshat vocabulary (`seshat`, `retail`, `medallion`, `gold`) appears in any of
  the 14 bodies.
- **Constitution amendment v1.1.0, made in the same commit**
  (`.specify/memory/constitution.md:556-563`), explicitly permits this exact
  state. It was a versioned, documented decision -- not a silent fork.
- **Principle II is scoped to the Power BI execution adapter**
  (`constitution.md:271-275`), not to all tooling. It does not bind here.

Classification: `capability_owner: vendored-upstream`, `upstream_project`
`github/spec-kit`, `upstream_reference` the pinned `0.8.10`, `update_policy`
recording the installer invocation.

**Residual gap, narrower than first framed**: no re-vendor or upgrade path is
recorded anywhere -- no lockfile, no `specify upgrade` record, no re-run
instructions. That is the "fork tax" the Principle II *rationale* warns about. It
is unpaid today because the copy is provably unmodified, but nothing preserves
that. Recorded here; it belongs to its own decision, not this axis.

### OD-2 -- dev-workflow skills -- RESOLVED: `seshat-governance` with stated deltas

The four INSPECT-flagged skills are `seshat-governance`, each REQUIRED to state
its delta. The deltas are real: each renders or adjudicates over *governance*
output, which no GitHub/Claude/Codex surface can produce -- those review code, not
readiness state.

| Skill | Required `seshat_delta` |
| --- | --- |
| `friendly-pr-reviewer` | plain-language rendering of the governance review, not a code review |
| `pr-readiness-reviewer` | `merge_ready` verdict from readiness evidence, not CI status |
| `release-notes-generator` | evidence-backed maturity ladder tied to roadmap F-numbers |
| `showcase-build` | disclosure-safe offline proof bundle from committed readiness truth |

### OD-3 -- dead constants -- RESOLVED: record, do not fix

The five constants at `capability_inventory.py:35-43` stay dead. The finding is
recorded (FR-010, task T005); reviving them is a behavior change across five
unrelated axes and would fail today on the live `surface: product-module` value.
It gets its own spec if ever wanted. **Not** in scope here.

Interaction with FR-011: that requirement edits `_RECORD_FIELDS` in the same
module. Implementers MUST leave the five constants untouched while doing so.

## Assumptions

- The manifest remains the single control plane; no parallel registry is
  introduced.
- `catalog.py` remains authoritative for installable-dependency coordinates.
- The 102-entry count is current as of `edfab33` and may drift; the migration
  targets "every entry", not a fixed number.
