# Implementation Plan: Review Pack Exporter (stable serialization formats)

**Branch**: `081-review-pack-exporter` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/081-review-pack-exporter/spec.md`

## Summary

Ship a small, pure, stdlib-only serialization module that turns an already-produced,
in-memory **pack** object (header + ordered sections, each carrying a status token +
evidence + blocking reasons + optional embedded `Finding`-shaped records) into three output
shapes: Markdown (for humans), JSON (for machines, `schema_version`-carrying), and a compact
CI/PR summary (worst-status + blocking reasons, never a score or a completeness tally). The
module is a **formatter over a stable pack shape**, not a producer: it does not read
`readiness-status.yaml`, metric contracts, or the parked-on map, and it does not decide any
status -- it renders whatever status the pack already carries, verbatim. This plan identifies
the likely module location, its function surface, and its golden-file test strategy WITHOUT
creating any of them (spec work only; no `src/` edits in this worktree).

## Technical Context

**Language/Version**: Python 3.13 (CI) / 3.12 (local dev); stdlib only (`json`, `dataclasses`,
`typing`) -- no new third-party dependency.

**Primary Dependencies**: None new. Reuses the existing `core.Finding` shape
(`src/retail/core.py`, `to_dict()` -- the B2 shape) for any embedded finding records, by field
name only (this feature does not import `core.py`'s `Finding` class itself as a hard
dependency; the pack shape documents the SAME field names so a caller can pass `Finding.to_dict()`
output directly, or an equivalent plain dict, into a section's `findings[]`). No YAML writer
enters the import path (FR-016; B3 import-boundary-guard precedent from `readiness_evidence.py`).

**Storage**: none. Pure in-memory transform; every output is a returned string (Markdown,
compact summary) or a `dict`/JSON string (machine format). No file write, no DB, no network.

**Testing**: pytest (`-m unit`). Golden-file / snapshot-style tests over synthetic pack
fixtures for each of the three formats, plus a schema-compatibility test asserting the
documented additive-only rule (e.g. a fixture pack rendered at a hypothetical later
`schema_version` still contains every field an earlier-version consumer would read). All
tests are pure (no DB, no driver, no network) -- same discipline as
`tests/unit/test_readiness_evidence.py` (spec 057).

**Target Platform**: repo-local Python library module, importable by any producer (J1's agent
workflow, a future `retail` CLI verb, LVR-adjacent code, or a test).

**Project Type**: Single project (library) -- matches the existing `src/retail/` layout.

**Performance Goals**: N/A (a pure in-memory transform over a small pack: a handful of
sections, each with a handful of evidence/blocking-reason/finding lines).

**Constraints**: stdlib-only; deterministic output (FR-013); no numeric confidence/health/
maturity score and no completeness tally in any format (FR-005, FR-006, hard rule #9); status
tokens preserved verbatim, never remapped (FR-003, FR-004); generic, no C086 specifics
(FR-014, Principle VII); ASCII / UTF-8 no BOM, short repo-relative paths (FR-015, Principle
IX); immutable (never mutates the input pack object).

**Scale/Scope**: one new small module (three render functions + the pack/section dataclasses)
+ its unit tests + golden fixtures. No new subsystem, no new `retail` CLI subcommand is
required by this feature (a future producer MAY wire one; out of scope here).

## Constitution Check

*GATE: Must pass before Phase 0. Re-checked after design.*

| Principle / rule | How this plan complies |
|---|---|
| I (Agent-First, Gate-Enforced) | Adds no gate and no `retail check` rule; the exporter is a pure library function a producer or a human calls. `retail check` exit code is unaffected (no new rule id). |
| IV (Source Mapping Before Silver) | Not applicable -- this feature touches no `silver.*`/`gold.*` SQL and no mapping artifact. |
| V (Agent Stops at Judgment Calls) | PASS by construction. The exporter never decides a status, never resolves an unrecognized token, never paraphrases a business-rule/PII ruling (FR-010), and has no write access to `approvals[]`. It renders; it never judges. |
| VII (C086 Is An Example) | PASS. Pack shape, schemas, and `contracts/` worked examples use a generic placeholder pack; no worked-example domain specifics (FR-014, SC-006). |
| VIII (Static-First Governance, Live Deferred) | PASS. No live DB/PBIP read (FR-011); purely static, stdlib, in-memory. |
| IX (Secrets and Reproducibility) | PASS. ASCII/UTF-8 no BOM, short paths (FR-015); no secrets are in scope (the pack is generic content, not a DSN). |
| Hard rule #9 (no fabricated confidence) | PASS. FR-005/FR-006 forbid a numeric score and a completeness tally in every format, most acutely the compact CI summary (User Story 3) -- the single highest-risk area this plan and the later analyze step must keep re-verifying. |
| B1/B3 (never-execute / import-boundary guard precedent) | PASS by design intent. The module is stdlib-only in its shared import path, same discipline as `readiness_evidence.py`; no DB driver or heavy import at module scope. (Actual guard-test wiring is an implementation-phase task, not performed here.) |
| Backwards-compatibility (this feature's own subject) | PASS. `data-model.md` defines `schema_version` + the additive-only rule; `contracts/` gives one worked compatibility example per format. This is not a bolt-on gate check -- it IS what FR-007/FR-008/SC-004 require this feature to prove. |

Result: PASS. No violation requires justification; Complexity Tracking omitted.

## Design overview

Five artifacts for this feature dir (this plan.md, research.md, data-model.md, quickstart.md,
contracts/) plus tasks.md (stage 4) and analysis.md (stage 5) -- no source-tree code is created
in this worktree (spec work only; implementation is a separate, later PR against `main`).

1. **research.md** -- confirms the seams this feature depends on (B2's `Finding.to_dict()`
   shape, J1's Markdown pack precedent, LVR's block shape, the readiness-model four-status
   vocabulary) and records the option analysis behind the JSON-not-YAML and code-not-skill
   decisions.
2. **data-model.md** -- the STABLE schemas: the `Pack` / `Section` / embedded-`Finding` shapes,
   the full recognized status-token union, the `schema_version` field and its additive-only
   compatibility rule, and the fixed worst-status severity ordering the compact summary uses.
3. **contracts/** -- one concrete worked example per output format (`markdown.md`,
   `json-schema.md` with an embedded example document, `compact-ci-summary.md`), each over a
   single GENERIC example pack (no C086 specifics), plus a `backwards-compat-example.md`
   showing a `schema_version` MINOR bump that stays additive.
4. **quickstart.md** -- how a producer (or a human, or a test) constructs a pack object and
   calls each of the three render functions; how a consumer is expected to tolerate unknown
   fields.
5. **tasks.md** -- stage 4 output: dependency-ordered tasks to actually build the module +
   tests + goldens, explicitly stopping before commit/push/PR (a later, separate execution
   step, out of scope for this spec-work run).

## Project Structure

### Documentation (this feature)

```text
specs/081-review-pack-exporter/
|-- spec.md
|-- plan.md              # this file
|-- research.md          # Phase 0: seam confirmation + option analysis
|-- data-model.md         # Phase 1: the stable Pack/Section/Finding schemas
|-- quickstart.md         # Phase 1: how a producer/consumer uses the exporter
|-- contracts/            # Phase 1: one worked example per output format
|   |-- markdown.md
|   |-- json-schema.md
|   |-- compact-ci-summary.md
|   `-- backwards-compat-example.md
|-- checklists/
|   `-- requirements.md
|-- analysis.md           # stage 5 output (or analysis/analyze-report.md if analyze
|                          # runs as a manual fallback -- see tasks.md note)
`-- tasks.md               # stage 4 output
```

### Source Code (repository root) -- IDENTIFIED, NOT CREATED in this worktree

```text
src/retail/
|-- review_pack_export.py   # LIKELY NEW (implementation phase, separate PR):
|                            #   dataclasses Pack, Section (+ a plain-dict-compatible
|                            #   constructor so callers need not import the dataclass);
|                            #   to_markdown(pack) -> str
|                            #   to_json(pack) -> dict   (caller does json.dumps)
|                            #   to_compact_ci_summary(pack) -> str
|                            #   STATUS_SEVERITY_ORDER: the fixed worst-status ordering
|-- core.py                  # UNCHANGED: Finding.to_dict() shape this feature embeds by
|                            #   field-name convention only (no new import edge required)
`-- cli.py                   # UNCHANGED by this feature; a future CLI wiring (e.g. a
                             #   `retail export-pack` verb) is explicitly OUT OF SCOPE here

tests/unit/
|-- test_review_pack_export_markdown.py    # LIKELY NEW: golden Markdown fixtures
|-- test_review_pack_export_json.py        # LIKELY NEW: JSON shape + schema_version tests
|-- test_review_pack_export_compact.py     # LIKELY NEW: compact-summary + no-score tests
`-- test_review_pack_export_compat.py      # LIKELY NEW: additive-only backwards-compat test
```

No `mappings/` change. No `templates/` change (this feature defines its schema in
`data-model.md` + `contracts/`, not a copy-me Markdown template like J1 -- see research.md for
why a template-only shape does not fit a byte-stable serializer). No `docs/readiness/` change.
No `retail check` rule (no `src/retail/rules/` entry).

**Structure Decision**: single-project Python library addition under `src/retail/`, diverging
from J1's docs/skill/template-only shape because this feature's job -- byte-stable,
backwards-compatible serialization -- is a deterministic pure-function contract, not a
judgment-driven composition (see research.md "Why code, not a skill" for the full argument).
This plan identifies the file but does not create it (spec-work boundary).

## Tests and validation this plan identifies (not run here)

- `pytest -m unit -k review_pack_export` -- once implemented, the golden-file suite for all
  three formats plus the compatibility test.
- `ruff format --check src/ tests/` / `ruff check src/ tests/` -- standard repo gate, once
  code exists.
- `retail check` -- MUST stay green with an UNCHANGED rule count (this feature adds no rule).
- Manual acceptance-scenario walkthroughs from spec.md (all four user stories) against a
  synthetic fixture pack, before any golden file is committed.

None of these are executed in this spec-work run (no `src/` edits, no golden-file regen, no CI
change, per this task's boundaries). They are recorded here so the later implementation PR has
a concrete validation checklist to run.

## Operational risks

- **Fake-confidence drift risk (highest)**: a future maintainer extending the compact summary
  could add a "N of M sections OK" line for readability, silently violating FR-005/FR-006/hard
  rule #9. Mitigation: `data-model.md` and `contracts/compact-ci-summary.md` show the forbidden
  shape explicitly as a negative example, and `tasks.md` includes an explicit test asserting no
  digit-ratio/percentage pattern appears in compact output.
- **Status-vocabulary silent unification risk**: a future maintainer, seeing five-ish
  near-synonymous tokens (`pending`/`not_started`, `not_applicable`/mechanical-gate Form C),
  could be tempted to normalize them "for consistency," which is exactly the Principle-V
  judgment call this feature must not make. Mitigation: FR-003/FR-004/FR-017 plus a dedicated
  pass-through unit test per token.
- **Schema-version discipline erosion**: without a concrete worked MINOR-bump example, a future
  contributor may not know what "additive-only" means in practice and could remove a field.
  Mitigation: `contracts/backwards-compat-example.md` is a concrete, copy-pasteable example of a
  compliant change (and, negatively, of a non-compliant one).
- **Scope creep into composition**: because J1 and LVR both produce pack-shaped content today,
  there is a natural temptation for a future change to have this module also fetch/assemble
  that content (for "convenience"). Mitigation: FR-001's explicit MUST NOT, plus the boundary
  section in spec.md naming the tripwire.

## Backwards-compatibility discipline (this feature's central subject)

- `schema_version` lives at the top level of the JSON output only (Markdown and the compact
  summary are human-facing prose formats with no consumer-parsed schema contract beyond "the
  status tokens are the ones documented"; a version marker in prose output is not required by
  any acceptance scenario and would add clutter without a consumer that needs it).
- Compatibility rule (documented in full in data-model.md): within one MAJOR `schema_version`,
  changes MUST be additive-only (new optional fields only; no field renamed or removed; no
  status token's meaning changed). A MAJOR bump is required for any removal/rename/repurposing.
- Verification approach for the later implementation phase: a golden-file EXPECTATION is
  described in `contracts/backwards-compat-example.md` (a `"1.0"` document and a hypothetical
  `"1.1"` document that only adds one field) -- this plan does NOT regenerate or commit an
  actual golden file (boundary: no golden-file regen in this spec-work run). The implementation
  phase's `tasks.md` items generate and commit the real fixtures.

## Repo-only vs live-DB scope

This entire feature is repo-only. No task, requirement, or test in this chain needs a DSN, the
`db` extra, or a live Postgres connection -- the exporter's only input is an in-memory pack
object a caller constructs from already-committed or already-computed content. There is no
`[PENDING LIVE PROFILE]` boundary for this feature to cross.

## Forbidden scope (explicit, for the later implementation PR)

- No reading of `readiness-status.yaml`, `metrics/*.yaml`, `parked-on.yaml`, or any other
  committed source artifact by the exporter module itself (FR-001).
- No new `retail check` rule, no new readiness stage, no change to any of the seven per-stage
  readiness docs.
- No YAML writer/dependency (FR-016; deferred).
- No numeric confidence/health/maturity score, no completeness ("N of M") tally, in any format,
  ever (FR-005, FR-006).
- No CLI subcommand wiring in this feature (a future feature may add `retail export-pack`; not
  built here).
- No live DB / PBIP / execution-adapter read.
- No modification to J1's, LVR's, or B2's existing shipped code or output shape -- this feature
  only reuses their field-name conventions by documentation, never by editing their source.
