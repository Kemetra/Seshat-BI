# Implementation Plan: Agent Compatibility Certification (`seshat agent verify`)

**Branch**: `129-agent-verify` | **Date**: 2026-07-14 | **Spec**: `specs/129-agent-verify/spec.md`

**Input**: Feature specification from `specs/129-agent-verify/spec.md`

## Summary

Add a `seshat agent verify --target claude|codex` CLI verb that produces
**categorical evidence** (PASS / BLOCKED / UNAVAILABLE per required check) that
a shipped agent integration installs correctly and carries Seshat's governance
contract intact. It is an evidence producer, not a scorer: no aggregate score,
rank, pass-rate, or rolled-up "certified" verdict, and it grants no approval.

The technical approach is to add a thin, read-only orchestrator
(`src/seshat/agent_verify/`) that composes the already-shipped foundations
rather than reimplementing them:

- **release-verification (spec 108)** for installation & discovery, version
  compatibility, and update/uninstall integrity - via the plugin manifests,
  the bundle provenance manifest (`output_sha256`), the exporter drift check
  (`scripts/export_agent_bundles.py --check`), and the install smoke-test
  discipline.
- **the benchmark (spec 120, `src/seshat/benchmark/`)** for the governance hard
  stops and retail semantic classes - by loading the committed scenario
  manifests and confirming the deterministic scripted reference participant
  reproduces each cited scenario's declared expected behavior. This is a
  target-invariant **shared baseline** (the manifests are repo-level).
- **each target's own exported bundle** for the **per-target governance-contract
  presence** check (FR-012a) - by reading the target's
  `portable-operating-contract.md` (exported into `integrations/<target>/`) and
  confirming it carries every hard-stop line. This is the governance layer that
  genuinely differs by `--target`, so verify's governance evidence is not
  vacuously identical across targets.
- **the governor (spec 120, `src/seshat/governor/`)** for the readiness-routing
  check - by invoking its read-only service over a synthetic fixture.

Each check returns one categorical verdict with evidence/reasons; the
orchestrator writes a disclosure-safe evidence record under `.seshat-output/`.
Publication stays owner-controlled behind the existing publication-intent +
disclosure guard.

## Technical Context

**Language/Version**: Python 3.11+ (repo floor), stdlib-only core; `yaml` is
imported lazily where a manifest is read (matches `benchmark/runner.py`).

**Primary Dependencies**: None new. Reuses `seshat.benchmark` (scenario
loading, reference participant, run/compare model), `seshat.governor`
(read-only service), `seshat.cli.guards` (`resolve_local_output`,
`require_publication_intent`), `seshat.artifact_identity` (`resolve_within`),
and the bundle provenance manifests + exporter drift check.

**Storage**: Read-only over committed repo text and the generated integration
trees; the only write is the local evidence record JSON under `.seshat-output/`.

**Testing**: pytest, `-m unit`. All checks are monkeypatch/fixture testable with
no live agent, DB, network, or IDE (mirrors the benchmark and validate test
posture). New tests: `tests/unit/test_agent_verify_checks.py`,
`test_agent_verify_record.py`, `test_agent_verify_cli.py`.

**Target Platform**: Cross-platform CLI (Windows-first per repo); no OS-specific
surfaces required for the mandatory checks.

**Project Type**: Single project - a CLI verb group + a small read-only library
module, in the existing `src/seshat/` layout.

**Performance Goals**: N/A (a maintainer-run command over a bounded repo tree;
completes in seconds).

**Constraints**: Driver-free import path preserved (B1/B3): no module-scope
DB/network import in the new module; `yaml` imported lazily in-function.
Offline-capable and credential-free for all required checks (FR-008).

**Scale/Scope**: Two shipped targets (`claude`, `codex`); ten required checks;
one evidence-record schema. Target set is data-driven so a third target is an
allowlist/registry entry, not a code fork.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Agent-First, Gate-Enforced** - PASS. Verify is a helper the agent/
  maintainer calls; it is read-only and reports categorical evidence. It never
  becomes the authority on a rule pass - a governance check's verdict is
  "the committed scenario + reference baseline match", not "the agent is
  compliant". `retail check` remains the enforcement gate.
- **II. Depend, Never Fork** - PASS. No adapter is forked or vendored. Verify
  reads the benchmark/governor/release surfaces already in the repo.
- **III. Medallion / Postgres-First / Gold-Only** - N/A. No warehouse, no DB
  read.
- **IV. Source Mapping Before Silver** - N/A (no silver authored). The
  governance checks *confirm* the no-silver-before-mapping hard stop ships
  intact - both in the target's own operating contract (FR-012a, per-target) and
  as a committed scenario whose reference baseline matches (shared baseline);
  they author nothing.
- **V. Agent Stops at Judgment Calls** - PASS. Verify grants no approval,
  advances no stage, and infers no approval from a passing check (FR-004).
  Publication is an explicit owner action (FR-022).
- **VI. Defaults Then Deviations** - N/A (no cleaning decisions).
- **VII. C086 Is An Example** - PASS. All fixtures are synthetic and generic
  (Assumptions).
- **VIII. Static-First Governance, Live Deferred** - PASS. Verify is static:
  it inspects committed contract content and the deterministic reference
  baseline. Live/stochastic conformance is the deferred FR-024 path that reuses
  the benchmark's FR-041 disclosed-run mechanism; it never certifies.
- **IX. Secrets and Reproducibility** - PASS. No secret is read or written; the
  evidence record is disclosure-checked (FR-022/FR-023); output paths are
  contained under `.seshat-output/` and stay short.

Hard rules cross-check: #8 (docs/templates first) - this is a runtime verb, but
it composes shipped runtime (benchmark/governor) and adds no new governance
truth; #9 (no fake confidence) - FR-003 forbids any score/rank/rollup, enforced
by a truthfulness test (SC-003).

No violations. Complexity Tracking table intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/129-agent-verify/
|-- spec.md              # feature specification (done)
|-- plan.md              # this file
|-- data-model.md        # Phase 1: VerifyTarget, RequiredCheck, PerCheckResult, VerifyEvidenceRecord
|-- quickstart.md        # Phase 1: run verify against claude + codex; read the record
|-- contracts/           # Phase 1: check-to-foundation map + evidence-record schema
|     |-- verify-checks.md            # the 11 required checks, foundation, evidence source, per-target vs shared, verdict rules
|     `-- agent-verify-record.schema.json
|-- tasks.md             # Phase 2 (/speckit-tasks)
`-- analysis.md          # cross-artifact analysis record
```

### Source Code (repository root)

```text
src/seshat/
|-- agent_verify/
|     |-- __init__.py
|     |-- model.py          # PerCheckResult, VerifyTargetSpec, VerifyRecord (frozen dataclasses); VERDICTS = (PASS, BLOCKED, UNAVAILABLE); each result flags per_target vs shared_baseline
|     |-- targets.py        # data-driven target registry (claude, codex): manifest path, provenance manifest, version source, footprint source, operating_contract path, ide_surface flag
|     |-- checks.py         # the 11 pure check functions -> PerCheckResult; each reads one foundation, returns a verdict + evidence/reason
|     `-- record.py         # assemble VerifyRecord, disclosure scan, JSON serialization under .seshat-output/
|-- cli/
|     |-- commands/
|     |     `-- agent_verify.py   # agent_verify_main(args): dispatch verify; exit-code contract
|     |-- parser_ecosystem.py     # + _add_agent_parser: `agent` group with `verify` subcommand (--target, --output, --publish)
|     `-- __init__.py             # + lazy dispatch entry "agent": _lazy(".commands.agent_verify", "agent_verify_main")

tests/unit/
|-- test_agent_verify_checks.py    # each check: PASS / BLOCKED / UNAVAILABLE with fixtures + monkeypatch
|-- test_agent_verify_record.py    # record assembly, disclosure scan, no-score truthfulness, containment
`-- test_agent_verify_cli.py       # parser wiring, --target refusal, exit-code contract, read-only guarantee
```

**Structure Decision**: A dedicated read-only library package
`src/seshat/agent_verify/` plus one CLI verb group, matching the shipped
`benchmark`/`governor` layout (library module + `cli/commands/*` handler +
`parser_ecosystem.py` wiring + lazy dispatch in `cli/__init__.py`). The target
set lives in `targets.py` as data so adding a third integration is a registry
entry, not a code fork.

## Phase 0 - Research (research.md)

Resolve, with citations to shipped code, before authoring checks:

1. **Provenance/drift surface**: how `bundle-manifest.json` (`output_sha256`,
   `source_sha256`, `destination`) and `scripts/export_agent_bundles.py --check`
   expose drift and the enumerable installed footprint per target. (Update &
   uninstall checks read this; no re-hash logic is invented if the exporter
   already computes it.)
2. **Version/compat source**: where the target's version and supported range
   are declared (`plugin.json` `version`, `pyproject.toml`, the versioning
   policy from spec 108) and what "supported range" means for a governance kit.
3. **Governor invocation contract**: the read-only `governor/service.py` entry
   the routing check calls, its input fixture shape, and how "cannot invoke"
   maps to UNAVAILABLE (not BLOCKED).
4. **Scenario id stability**: confirm the cited scenario ids
   (`rs-pii-exposure`, `hs-self-grant-approval`, `hs-silver-before-mapping`,
   `rs-metric-without-approval`) and how `load_scenarios` + the reference
   participant + `Observation.comparison` give the reference-baseline match.
5. **Per-target operating-contract shape**: the exported
   `integrations/<target>/.../portable-operating-contract.md` and the exact
   hard-stop lines it must carry (confirmed: each of `claude` and `codex` ships
   its own copy, tracked in that bundle's provenance manifest). Define the
   hard-stop line set the presence check asserts, and how a dropped/mutated line
   maps to BLOCKED. This is the per-target governance evidence source.
6. **IDE-surface signal**: what in a target's declared metadata indicates an IDE
   surface exists; absence -> UNAVAILABLE.

## Phase 1 - Design

### data-model.md (entities from the spec, made concrete)

- **VerifyTargetSpec** (frozen): `name`, `manifest_path`, `provenance_manifest`,
  `version_source`, `footprint_source`, `operating_contract` (the exported
  `portable-operating-contract.md` path for this target), `ide_surface: bool`.
- **RequiredCheck** (enumerated, not a stored entity): a `check_id`, the
  `foundation` it extends, the `evidence_source` it reads, an
  `evidence_class` in {`per_target`, `shared_baseline`}, and the pure function
  that evaluates it. Only the install/version/update/uninstall/IDE checks and
  the governance-contract-presence check are `per_target`; the scenario- and
  governor-backed governance checks are `shared_baseline`.
- **PerCheckResult** (frozen): `check_id`, `verdict` in {PASS, BLOCKED,
  UNAVAILABLE}, `evidence_class` in {`per_target`, `shared_baseline`},
  `evidence: tuple[str, ...]`, `blocking_reasons: tuple[str, ...]`,
  `unavailable_reason: str | None`. Invariant (enforced + tested): PASS => non-
  empty `evidence` and empty reasons; BLOCKED => >=1 blocking reason;
  UNAVAILABLE => an `unavailable_reason`. The `evidence_class` label prevents a
  shared-baseline verdict from being read as per-target evidence.
- **VerifyEvidenceRecord** (frozen): `schema_version`, `target`, `tool_version`,
  `generated_at`, `static_vs_live_boundary` (a fixed disclosure string),
  `results: tuple[PerCheckResult, ...]`. `to_document()` emits JSON with **no**
  aggregate field.

### contracts/

- **verify-checks.md** - the authoritative table: for each of the 11 required
  checks, its `check_id`, the foundation it extends (spec 108 / benchmark /
  governor / target bundle), its `evidence_class` (per-target or shared
  baseline), the exact evidence source it reads, the PASS condition, the BLOCKED
  triggers, and when it is UNAVAILABLE. This is the contract US1/US2/US3 test
  against.
- **agent-verify-record.schema.json** - JSON Schema (draft 2020-12,
  `additionalProperties: false`) for the evidence record. Constrains `verdict`
  to the three-value enum, requires the per-verdict reason fields, and
  **forbids** any `score`/`rank`/`pass_rate`/`grade`/`overall` property by
  omission under a closed object (the truthfulness seam, mirroring
  `schemas/benchmark-run.schema.json`).

### quickstart.md

`seshat agent verify --target claude` then `--target codex` from a clean
checkout; read the written record path; interpret the three verdicts; show a
seeded BLOCKED (mutated generated file) and a seeded UNAVAILABLE (no IDE
surface); show that publication is refused without `--publish` and refused on a
disclosure finding.

### Exit-code contract (stable, mirrors the benchmark handler)

```text
0  all required checks PASS
1  at least one required check BLOCKED (fail-closed governance/integrity)
2  input defect: unknown --target, unreadable manifest, uncontained output path
3  at least one required check UNAVAILABLE and none BLOCKED (truthful "not fully
   verifiable" - distinct from 0 so a UNAVAILABLE run never reads as a pass)
```

(An UNAVAILABLE-only run MUST NOT exit 0; that is the FR-002/SC-002 no-false-
pass guarantee at the process boundary.)

## Testing strategy

- **Per-check unit tests**: each check gets a PASS fixture, a BLOCKED fixture
  (drift / incompatible version / missing scenario / mismatched baseline /
  dropped hard-stop line), and an UNAVAILABLE fixture (absent surface).
  Shared-baseline governance checks assert the cited scenario id and that a
  removed scenario -> BLOCKED. The per-target contract-presence check reads each
  target's own operating contract, asserts every hard-stop line is present, and
  asserts a target with a dropped/mutated hard stop -> BLOCKED while the other
  target stays PASS - proving the governance verdict is genuinely per-target
  (SC-005).
- **Truthfulness test** (SC-003): serialize a record for every verdict
  combination and assert the JSON contains no `score`/`rank`/`pass_rate`/
  `grade`/`overall`/`certified` key and no such token in text output; validate
  against the closed schema.
- **Read-only test** (SC-004): run the full suite under a temp repo and assert
  no tracked file, DB, model, or approval mutates; the only new path is under
  `.seshat-output/`.
- **Disclosure test** (SC-006): seed a record with a fake secret / absolute path
  and assert the disclosure scan flags it and publication is refused; assert
  `require_publication_intent` gates the publish path.
- **Offline test** (SC-007): run every required check with no DB/network/IDE and
  assert completion with UNAVAILABLE where a surface is absent.

## Complexity Tracking

> No Constitution Check violations; table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none)    | -          | -                                    |
