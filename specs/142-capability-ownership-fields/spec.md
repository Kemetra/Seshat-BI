# Feature Specification: Capability ownership fields -- declaring who owns each agent-facing capability

**Feature Branch**: `142-capability-ownership-fields`

**Created**: 2026-08-07

**Status**: Draft

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
`src/seshat/integrations/catalog.py:61-67` names dbt Labs, Microsoft, and
Dagster with coordinates and channels -- for *installable dependencies* only. No
record says that (for example) `dbt-workflows` is a Seshat adapter over dbt
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

`docs/capabilities/ownership-audit.md` found one genuine open question: whether
the 12 `speckit-*` skills are unmodified upstream Spec Kit content. The axis
must be able to record "this is vendored upstream content" as a durable,
reviewable statement rather than a paragraph in an audit doc.

**Acceptance**: `capability_owner: vendored-upstream` exists as a declarable
value, and the `speckit-*` aggregate entry can carry it pending human ruling.

## Requirements

### FR-001 -- The ownership fields

Each manifest entry MAY carry an `ownership:` mapping. All sub-fields are
OPTIONAL; an entry omitting the mapping entirely remains valid.

| Field | Type | Meaning |
| --- | --- | --- |
| `capability_owner` | token (FR-002) | who owns the capability |
| `upstream_project` | string | human-readable owning project, e.g. `dbt Labs` |
| `upstream_surface` | token (FR-003) | the form the upstream capability takes |
| `upstream_reference` | string | a URL or coordinate, e.g. `dbt-labs/dbt-agent-skills` |
| `seshat_delta` | string | what Seshat adds; required when `capability_owner` is `seshat-adapter` (FR-006) |
| `canonical_source` | string | repo-relative path of the authored source |
| `generated_targets` | list of strings | repo-relative paths generated from `canonical_source` |
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
- `seshat-governance` -- readiness gates, approvals, evidence, policy. No
  upstream equivalent.
- `seshat-domain-knowledge` -- BI/SQL/DAX/Python/retail reasoning that no
  upstream tool owns.
- `vendored-upstream` -- upstream content copied into this repo. A declaration
  that a human ruling is owed, not an endorsement.

An unrecognized token is a spec violation, reportable by the oracle (FR-009),
never silently accepted as meaningful.

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
- `tests/contract/test_capability_ship_classification.py` asserts named-key
  invariants only; it contains no key-set closure assertion.

Consequence: **no lockstep schema bump is required.** The migration may land
entry-by-entry.

### FR-005 -- `canonical_source` and `generated_targets` state a direction

Where an entry ships into the generated bundles, `canonical_source` names the
authored path and `generated_targets` names what is produced from it. These
record the direction the existing generator already enforces
(`scripts/export_agent_bundles.py:602`); they introduce no new enforcement.

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

- **SC-001**: Every one of the 102 entries either carries an `ownership` mapping
  or is listed, with a reason, as deliberately unclassified.
- **SC-002**: Every entry declaring `seshat-adapter` carries a non-empty
  `seshat_delta`.
- **SC-003**: The four wrappers named in `ownership-audit.md`
  (`dbt-transformation-adapter`, `dagster-orchestration-adapter`,
  `pbi-mcp-doctor`, `pbir-authoring-adapter`) are classified `seshat-adapter`
  with their upstream project named.
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
- **Promoting this spec into the `<!-- SPECKIT -->` fence.** The fence carries
  exactly one plan path by contract
  (`tests/contract/test_dbt_documentation.py:131`), and `.specify/feature.json`
  currently points at `specs/138-agent-driven-bundle`. Promotion is a separate,
  human decision.

## Open decisions

- **OD-1**: Whether the `speckit-*` aggregate entry is classified
  `vendored-upstream`. Requires comparing the shipped skills against upstream
  Spec Kit. **Owner ruling required.**
- **OD-2**: Whether `friendly-pr-reviewer` and the other generic dev-workflow
  skills flagged INSPECT in the audit are `seshat-governance` or
  `official-upstream`. **Owner ruling required.**
- **OD-3**: Whether the five dead constants at `capability_inventory.py:35-43`
  should be made live in a separate spec. Recorded by FR-010, not resolved here.

## Assumptions

- The manifest remains the single control plane; no parallel registry is
  introduced.
- `catalog.py` remains authoritative for installable-dependency coordinates.
- The 102-entry count is current as of `edfab33` and may drift; the migration
  targets "every entry", not a fixed number.
