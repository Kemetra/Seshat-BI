# Implementation Plan: Public Extension-Pack Catalog

**Branch**: `128-pack-catalog` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/128-pack-catalog/spec.md`

## Summary

Add a community DISCOVERY and RETRIEVAL layer over the extension-pack system
already shipped in spec 120 (US5): a reviewed static git registry of pack
metadata, and three new subcommands on the existing `pack` verb group --
`search` (keyword + category over registry metadata), `inspect` (one full
record), and `add` (fetch -> verify hash -> verify content schema -> run the
EXISTING pack validation -> explicit, reviewable workspace addition). The
catalog introduces exactly one new schema (the registry INDEX, metadata ABOUT
packs) and reuses the shipped pack content model, manifest schema, single-pack
and selection validation, path-containment guard, disclosure scan, and
JSON-contract validator unchanged. It fails closed on invalid, incompatible,
missing, or tampered packs, preserves contributor attribution, and -- by design,
consistent with the shipped pack system -- creates no activation state and
advances no readiness stage.

## Technical Context

**Language/Version**: Python 3.13, matching the current package contract. Static
core stays stdlib-only; `pyyaml` is already an existing dependency and is
imported lazily as the shipped pack loader does.

**Primary Dependencies**: No new runtime dependency. The catalog reuses
`seshat.packs` (model, loader, validator, scaffold), `seshat.ecosystem_contracts`
(`validate_json_contract`), `seshat.artifact_identity` (containment + canonical
paths), and `seshat.disclosure` (`scan_disclosure`). Content hashing uses
`hashlib` (stdlib).

**Storage**: Local files only. The registry is tracked repository text (a static
git artifact); there is no service database, hosted marketplace, or dynamic
index endpoint. A successful `add`'s only write is declarative pack content into
the workspace as a reviewable change. No gitignored derived state and no hidden
"installed packs" file (there is no activation lifecycle).

**Testing**: pytest unit + contract + integration. Contract test for the new
registry-index schema. Fixture-driven fail-closed tests for each refusal class
(unknown id, tamper/hash-mismatch, schema-invalid record, schema-invalid
content, incompatible core, missing/dangling source, containment escape,
disclosure hit, existing-validation finding, duplicate record, workspace
collision). Existing `retail check`, `retail semantic-check`, and `retail
kit-lint` stay green. All tests run offline with no network and no database.

**Target Platform**: Windows release gate; macOS/Linux best effort. Fully
offline: exercised against a checked-out static registry.

**Project Type**: Single Python CLI/agent toolkit. The catalog is a
transport-neutral pure core (`seshat.packs.catalog`) plus a thin extension of
the existing `pack` CLI handler/parser.

**Performance Goals**: `search` and `inspect` over a 500-record registry return
within one second. `add` (including hashing the fetched content and running the
existing validation) completes within two seconds for a typical pack. These are
comfort bounds, not gates.

**Constraints**: Offline-first; local workspace boundary (all source/content
paths pass the shipped containment guard); deterministic same-input output; no
score (verification state is a categorical status + evidence); no self-approval
(verification state is human-authored in the registry, never set at runtime); no
second pack validator; no second pack format; no activation/enablement
lifecycle; no readiness-stage promotion; no database, Power BI execution, or
publish; no secret/PII/DSN/absolute-path disclosure; Windows-safe relative
paths.

**Scale/Scope**: One static registry, targeting on the order of hundreds of pack
records. v1 is NOT a hosted marketplace, a dynamic index API, a signing/trust
web, a rating/leaderboard system, or an activation manager.

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.7.0 before research
and re-checked after design.*

| Principle | Verdict | Basis |
|-----------|---------|-------|
| I. Agent-First, Gate-Enforced | PASS / reinforced | Catalog verbs are helpers the agent calls; the add gate is fail-closed (refuse on any finding), not advisory. The existing `retail check` gate is untouched. |
| II. Depend, Never Fork | PASS | Reuses the shipped pack model/schema/validation/guards unchanged; introduces no fork of them and no rival format. Git is the transport, not a vendored engine. |
| III. Medallion, Postgres-First, Gold-Only | PASS / untouched | No warehouse authoring, no source-of-truth change, no Power BI read-path change. |
| IV. Source Mapping Before Silver | PASS / untouched | The catalog neither writes silver nor touches the mapping gate; adding a pack advances no stage. |
| V. Agent Stops at Judgment Calls | PASS / reinforced | Verification `reviewed` state is human-authored in the registry; the tool never self-grants it and never promotes readiness (hard-stops `never_self_grant_approval`, `never_fabricate_a_confidence_score`). |
| VI. Defaults Then Deviations | PASS | Added packs are declarative suggestions; they cannot silently override cleaning defaults or grant authority (enforced by the reused pack validation). |
| VII. C086 Is an Example | PASS | Registry records and reference packs are synthetic/generic; C086 is not a schema. |
| VIII. Static-First, Live Deferred | PASS / reinforced | The whole catalog is static: a reviewed git registry, no hosted service, exercisable offline. This is the deferred registry spec 120 US5 named, now bounded static-first. |
| IX. Secrets and Reproducibility | PASS / reinforced | Disclosure-safe findings reuse the shipped scan; content hashing gives reproducible identity; canonical relative paths; no committed secrets. |

**Result: PASS. No constitutional violation requires Complexity Tracking.**

## Project Structure

### Documentation (this feature)

```text
specs/128-pack-catalog/
├── plan.md
├── spec.md
├── tasks.md
├── analysis.md              # /speckit-analyze cross-artifact findings
├── research.md              # Phase 0 decisions (below)
├── data-model.md            # registry record + catalog finding + fetched-content entities
├── quickstart.md            # acceptance walkthrough (search -> inspect -> add + refusals)
├── contracts/
│   └── seshat-pack-registry.schema.json   # the NEW registry-INDEX schema
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/seshat/
├── packs/
│   ├── model.py             # UNCHANGED (pack content model)
│   ├── loader.py            # UNCHANGED (local manifest read)
│   ├── validator.py         # UNCHANGED (single-pack + selection validation)
│   ├── scaffold.py          # UNCHANGED
│   ├── registry.py          # NEW: parse + schema-validate the static registry index; search/inspect metadata
│   └── catalog.py           # NEW: fetch -> hash-verify -> schema-verify -> existing validation -> add (fail-closed)
├── ecosystem_contracts.py   # REUSED (validate_json_contract for the index schema)
├── artifact_identity.py     # REUSED (containment, canonical relative paths)
└── disclosure.py            # REUSED (scan_disclosure)

src/seshat/cli/
├── commands/pack.py         # EXTEND: add search/inspect/add handlers alongside scaffold/validate
└── parser_ecosystem.py      # EXTEND: add search/inspect/add subparsers to the pack verb group

schemas/
├── seshat-extension-pack.schema.json   # UNCHANGED (pack CONTENT schema)
└── seshat-pack-registry.schema.json    # NEW (registry INDEX schema)

packs/
└── registry/
    ├── index.yaml           # the reviewed static registry (generic reference records)
    └── reference/           # generic declarative reference packs a record can source

tests/
├── contract/                # registry-index schema conformance
├── integration/             # end-to-end search -> inspect -> add + each refusal class
└── unit/                    # registry parse/search/inspect, hashing, fail-closed catalog
```

**Structure Decision**: Keep one canonical Python project. The catalog is a
pure core under `seshat.packs` (a `registry` module for metadata and a `catalog`
module for the fetch-verify-add flow), with a thin CLI adapter added to the
EXISTING `pack` verb group. The pack content model, manifest schema, and
validation are imported, never re-implemented. The registry is tracked text; a
successful add writes only reviewable workspace content.

## Phase 0 - Research

See [research.md](./research.md). Key decisions (each an auto-decision recorded
against a repo default or a hard-stop):

1. **Transport = static git registry, not a service.** v1 indexes a reviewed,
   version-controlled `index.yaml` from the checked-out repository. No hosted
   marketplace, dynamic endpoint, or network service (Principle VIII; spec 120
   US5's registry-deferral clarification). Keeps the core offline-testable and
   stdlib-only.
2. **`add` = reviewable fetch, not activation.** `add` copies verified
   declarative content into the workspace as an inspectable change and hands it
   to the existing validation. It writes no activation state and promotes no
   readiness stage -- reconciling with the shipped pack system's "no
   install/activate verb by design" and "constructing a selection installs
   nothing and persists nothing."
3. **One NEW schema (the index), zero new pack formats/validators.** The
   registry-index schema is validated with the shipped `validate_json_contract`;
   pack CONTENT continues to use `seshat-extension-pack.schema.json` and
   `validate_pack` / `validate_selection` unchanged.
4. **Fail-closed chain maps every gate to a reused component.** unknown id
   (registry lookup) -> tamper/hash mismatch (`hashlib` compare) -> record
   schema-invalid (`validate_json_contract` on the index) -> content
   schema-invalid + declarative/authority/stage checks (`validate_pack`) ->
   incompatible core (`validate_pack`'s core-compatibility check) ->
   missing/dangling source + containment (`artifact_identity.resolve_within`) ->
   disclosure (`disclosure.scan_disclosure`) -> selection findings
   (`validate_selection`) -> refuse. The catalog computes/compares the hash and
   resolves the source; everything downstream is handoff.
5. **Verification state = categorical status + evidence, human-authored.** A
   fixed vocabulary (`reviewed` / `unreviewed` / `deprecated`) with evidence,
   mirroring the readiness spine's status+evidence shape; never a number
   (`never_fabricate_a_confidence_score`); set only by a committed human edit to
   the registry (`never_self_grant_approval`). Absence = NOT reviewed.
6. **Attribution is preserved and distinct from content owner.** The registry
   record's `author` is carried through all outputs and is never conflated with
   the pack manifest's content `owner`.
7. **Hash algorithm** is SHA-256 over the declarative content (implementation
   detail, not a semantic decision).

No `NEEDS CLARIFICATION` remains (all clarifications auto-answered to the
recommended default; see spec Clarifications).

## Phase 1 - Design and Contracts

- [data-model.md](./data-model.md) defines the Registry, Registry Record,
  Verification State, Fetched Pack Content, and Catalog Finding entities and
  their state/validation rules, and the exact reuse boundary to the shipped
  `PackManifest` / `PackSelection` model.
- `contracts/seshat-pack-registry.schema.json` is the observable boundary for the
  registry INDEX (the one new schema); the pack CONTENT contract remains
  `schemas/seshat-extension-pack.schema.json`, unchanged.
- [quickstart.md](./quickstart.md) is the acceptance walkthrough: a clean search
  -> inspect -> add, plus a tampered-pack refusal and an incompatible-pack
  refusal.
- The SPECKIT pointer in `CLAUDE.md` continues to reference the current plan; no
  edit to shipped pack surfaces is planned.

## Delivery Phases

| Phase | Story | Independently releasable result |
|------:|-------|---------------------------------|
| 1 | US1 | `pack search` over a reviewed static registry returns matches with identity, version, category, author, compatibility, and verification state; fetches nothing. |
| 2 | US2 | `pack inspect <id>` shows one full record (all required fields, declared dependencies + conflicts); fetches nothing. |
| 3 | US3 | `pack add <id>` fetches, hash- and schema-verifies, runs the existing validation, and adds a verified declarative pack as a reviewable change; fails closed on every refusal class; advances no readiness and writes no activation state. |

Phases are ordered by the user-story priority in the spec (US1 MVP). Each is
independently releasable: search ships without inspect; inspect ships without
add; add reuses the validation already shipped.

## Post-Design Constitution Re-check

**PASS unchanged.** The data model carries verification state as status +
evidence with no score; `reviewed` is a human-authored committed registry edit
the tool cannot self-grant; the add is explicit and its only write is reviewable
workspace content; the reused pack validation supplies every content verdict; no
second pack format or validator is introduced; no activation lifecycle, no
readiness promotion, no database, no Power BI execution, and no publish enter
scope.

## Complexity Tracking

No violations to justify. The one new schema (registry index) is required by the
spec's Requirement 2 fields (source, hash, verification state, author) that do
not exist on the pack content model; it is metadata ABOUT packs and does not
duplicate or compete with the pack content schema.
