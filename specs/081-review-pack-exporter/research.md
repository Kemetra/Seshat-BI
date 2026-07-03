# Phase 0 Research: Review Pack Exporter

Purpose: confirm the seams this feature depends on (so the plan references real, verified
facts rather than assumed ones) and record the option analysis behind the decisions
Assumptions in spec.md commit to.

## 1. Confirmed seams (read, not modified)

### 1.1 B2 -- `retail check --format json` (shipped, PR #63)

- File: `src/retail/runner.py`, function `run_json(rules, ctx) -> int`.
- Verified shape (read directly): prints `json.dumps({"findings": [f.to_dict() for f in
  findings], "exit_code": exit_code}, ...)` to stdout and returns the same exit code as the
  text path.
- `Finding.to_dict()` is defined on the frozen `Finding` dataclass in `src/retail/core.py`;
  fields are `rule_id`, `severity` (an enum, serialized as its value), `message`, `locator`.
- Wiring: `src/retail/cli.py` exposes `--format {text,json}` on the `check` subcommand
  (`output_format`, default `"text"`); `json` calls `run_json`, unchanged exit code (verified
  at `cli.py` lines ~50-60 and ~282-284).
- **Consequence for this feature**: the exporter's JSON format, when a pack section embeds
  findings, MUST reuse these exact four field names and value shapes (FR-009, SC-007) so a
  consumer that already parses B2's `{"findings": [...]}` document recognizes the same finding
  shape nested inside an exported pack. This feature does not import `core.Finding` as a hard
  dependency (avoiding an unnecessary coupling for a stdlib-only formatter); it documents the
  field-name contract instead, so a caller can pass `Finding.to_dict()` output, or an
  equivalent plain dict, into a section.

### 1.2 J1 -- `approval-evidence-pack` (shipped, `specs/063-approval-evidence-pack/`)

- Deliverable shape: docs/skill/template only (`.claude/skills/approval-evidence-pack/SKILL.md`
  + `templates/approval-evidence-pack.md`), no runtime code, no `retail check` rule (spec 063
  FR-019, its Clarifications C2).
- It reads FOUR committed sources (readiness doc, `readiness-status.yaml`, metric-contract AL1
  signal, parked-on map) and renders ONE ordered Markdown document ending in an empty
  `approvals[]` slot.
- It already implements a "surface, never assert" discipline and a status-vocabulary of
  `not_started | blocked | warning | pass` (the readiness-model four values) verbatim from
  source, plus a Form A/B/C branch for the terminal approval slot.
- **Consequence for this feature**: J1 is proof that a Markdown pack-rendering need already
  exists and is solved today by hand-authored agent prose per producer. This feature does NOT
  replace J1's skill or its template; it offers an alternative, code-based Markdown (and JSON,
  and compact) renderer that ANY producer -- including a hypothetical future version of J1 --
  could call instead of writing its own Markdown by hand. Whether J1 itself is ever refactored
  to call this exporter is explicitly out of scope (that would be an edit to J1's shipped
  skill, forbidden by this task's boundaries).

### 1.3 LVR -- `readiness_evidence.py` (shipped, `specs/057-live-validation-evidence-recorder/`)

- `src/retail/readiness_evidence.py`, function `build_gold_ready_block(findings, table_identity,
  run_mode, timestamp, dsn) -> dict`. Pure, stdlib-only (only `urllib.parse` beyond builtins).
- Produces a plain dict: `{stage, table, run_mode, evidence: [...], warnings: [...],
  blocking_reasons: [...], status, recorded_at?}`. `status` is one of `blocked` / `warning`
  (never `pass` -- FR-012 of spec 057, a deliberate Principle-V deferral).
- Uses a `run_mode` of `"live"` / `"deferred"` -- a token OUTSIDE the four-status readiness
  vocabulary and outside the five-token feature-request vocabulary.
- **Consequence for this feature**: LVR is direct evidence that (a) a pure, stdlib, code-based
  producer of pack-shaped content already exists and ships successfully in this repo (the
  code-not-skill precedent cited in plan.md's Structure Decision), and (b) the status
  vocabulary problem is real today, not hypothetical -- LVR's own `run_mode` token does not fit
  either named vocabulary cleanly. This is the direct evidence behind the "status-vocabulary
  pass-through, not unification" Assumption in spec.md: any attempt to force LVR's block through
  a narrower canonical enum would either lose the `deferred` distinction or require this
  feature to invent a mapping LVR's own spec (057) never ratified.

### 1.4 K1 -- Gate Observability Rollup (idea, HORIZON, `docs/roadmap/idea-backlog.md`)

- Verified text (idea-backlog.md, entry "K1. Gate Observability Rollup"): `HORIZON` tier;
  "Strictly aggregates the structured Findings the gates ALREADY emit (B2/LVR/semantic-check)
  into one ledger -- no re-checking, no execution, no new verdict/score." First step (as
  written): "After the third gate's emission format is stable, add observability.py unioning
  each gate's JSON/SARIF into docs/quality/gate-run-ledger.json via a thin retail gate-ledger
  verb; no new @register rule."
- `docs/roadmap/design-ideas-decisions.md` confirms: "`K1` needs a third gate's emission format
  to stabilize" (dependency ledger, line ~102).
- **Consequence for this feature**: K1 is an AGGREGATOR (many gates' Findings -> one ledger).
  This feature is a FORMATTER (one pack -> many output shapes). They operate on orthogonal
  axes and neither builds nor unblocks the other: this feature does not add a "third gate," it
  adds a rendering layer for pack content that already-shipped gates (or J1's composed packs)
  produce. See spec.md's Assumptions and the analyze step (`analysis.md`) for the full
  distinctness argument.

## 2. Option analysis

### 2.1 JSON vs. YAML for the machine format

| Option | For | Against |
|---|---|---|
| JSON (chosen) | stdlib (`json` module); matches B2's existing machine format exactly; zero new dependency; this task's boundaries forbid new dependencies | less human-skimmable than YAML for a hand-edited config (not a concern here -- this is a generated, not hand-authored, artifact) |
| YAML | more human-friendly for hand editing | requires a third-party parser/dumper (`pyyaml` or similar) not currently a dependency of the stdlib-only static-governance core (Constitution Principle VIII); would violate this task's explicit "no new dependencies" boundary |

**Decision**: JSON now; YAML explicitly deferred (FR-016) as a possible future MINOR-compatible
addition, never a replacement.

### 2.2 Code module vs. skill+template (J1 precedent)

| Option | For | Against |
|---|---|---|
| skill + template (J1 shape) | matches the most recent Product Module precedent in this repo; no `src/` code | agent-authored Markdown rendering is not guaranteed byte-identical across runs (User Story 1's determinism requirement, SC-005); a "stable schema" claim (FR-007/FR-008, SC-004) is hard to test/prove without a deterministic function a golden-file test can pin down; three DIFFERENT output shapes (Markdown/JSON/compact) sharing one guaranteed-consistent source-of-truth is naturally a shared function, not three independently-drifting prose recipes |
| code module (chosen) | deterministic, testable via golden files (LVR precedent); one shared `Pack`/`Section` shape guarantees the three formats can never disagree about what a status token or an evidence line says; matches this feature's central claim (byte-stable, backwards-compatible schemas) | adds a `src/` module and a test file, which is a heavier deliverable than J1's docs-only shape |

**Decision**: code module (`src/retail/review_pack_export.py`, identified but not created in
this spec-work run), justified specifically because "stable, backwards-compatible schema" is a
byte-level determinism claim that a skill (an agent following prose instructions) cannot
guarantee run-to-run the way a pure function with golden-file tests can.

### 2.3 Status vocabulary: unify vs. pass-through

| Option | For | Against |
|---|---|---|
| Unify into one canonical enum | Simpler consumer-facing contract; only one status value type to document | Requires deciding how `not_started` relates to `pending`, how LVR's `deferred` relates to `blocked`, and how F028/J1's Form-C "not applicable" prose relates to a token -- each such mapping decision is exactly the kind of judgment call Principle V reserves for a human, and none of the shipped specs (057, 063) that emit these tokens have ratified a cross-vocabulary mapping |
| Pass-through (chosen) | No new judgment call; every existing producer's token survives unmodified; the exporter documents the UNION of known tokens rather than inventing a new one | Consumers see more than one token family in the wild (e.g. both `not_started` from readiness-model producers and, hypothetically, `pending` from a producer that speaks the feature-request's literal vocabulary) |

**Decision**: pass-through (FR-003, FR-004, FR-017), documented as a named Assumption in
spec.md, with unrecognized tokens surfaced (never silently coerced).

## 3. Open items carried to plan.md / tasks.md (not resolved here)

- The exact Python type for a pack (a `@dataclass(frozen=True)` per this kit's Python style
  rule, vs. a plain `TypedDict`) is an implementation-phase decision; plan.md's Structure
  Decision leans dataclass (consistent with `core.Finding`) but this is not load-bearing for
  the spec/plan chain and is left to the implementation PR.
- Whether a future `retail export-pack` CLI verb is ever added is explicitly out of scope
  (plan.md Forbidden scope) and not researched further here.
