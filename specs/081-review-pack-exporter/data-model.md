# Phase 1 Data Model: Review Pack Exporter -- the stable schemas

This is the authoritative shape definition for this feature. `contracts/` gives one worked
example per output format against this shape; `quickstart.md` shows how a caller builds and
renders it. Generic only (Principle VII) -- no worked-example (C086) values appear below.

## 1. The recognized status-token union

The exporter recognizes and passes through, verbatim, every token in this table. It does not
invent a canonical union that replaces these; it documents which producers use which tokens so
a consumer can reason about what it might see.

| Token | Source vocabulary | Meaning |
|---|---|---|
| `not_started` | readiness-model (four-status) | the stage/section has not begun |
| `blocked` | readiness-model; feature-request vocabulary; LVR (`status` field) | a required artifact/check/approval is missing |
| `warning` | readiness-model; feature-request vocabulary; LVR (`status` field) | advanced, non-fatal issue recorded |
| `pass` | readiness-model; feature-request vocabulary | all required artifacts/checks/approvals present |
| `pending` | feature-request vocabulary | a producer-specific "not yet decided" state distinct from `not_started` (e.g. a section whose upstream producer has not yet run) |
| `not_applicable` | feature-request vocabulary; F028/J1 Form C prose ("no stage-approval slot applies") | the section's status concept does not apply to this pack instance (e.g. a mechanical gate with no approval slot) |
| `deferred` (as a `run_mode`, not a `status`) | LVR (`run_mode` field, spec 057) | NOT a section status; documented here only so an exporter that receives an LVR-shaped block understands `run_mode: deferred` maps to that block's own `status: blocked` (LVR already performs this derivation itself -- see `readiness_evidence.py`; the exporter does not re-derive it) |
| *(any other string)* | unrecognized | pass through verbatim; mark `"recognized": false` in JSON, visibly flag in Markdown/compact (FR-017) |

**Rule (FR-003/FR-004)**: the exporter NEVER maps one row of this table to another (e.g. it
never turns `not_started` into `pending` for "consistency"). Each token is rendered exactly as
received.

## 2. The `Pack` shape

The top-level object a producer constructs and passes to each render function.

```text
Pack:
  schema_version: str            # e.g. "1.0" -- JSON output only (see section 4)
  title: str                     # opaque to the exporter; producer-supplied label
  generated_at: str | None       # ISO-8601 or producer's own format; OPTIONAL.
                                  #   If absent, Markdown/compact rendering omits any
                                  #   generated-at line entirely (never fabricates a
                                  #   wall-clock timestamp -- FR-013 determinism).
  sections: list[Section]        # ordered; rendered in this exact order in every format
  source_note: str | None        # OPTIONAL free-text citing what produced this pack
                                  #   (e.g. "composed by approval-evidence-pack skill,
                                  #   2026-07-03") -- rendered verbatim if present, never
                                  #   originated by the exporter
```

## 3. The `Section` shape

```text
Section:
  name: str                          # section heading, producer-supplied
  status: str                        # one token from section 1's union, verbatim
  evidence: list[str]                # each a producer-supplied, already-true evidence line
  blocking_reasons: list[str]        # each a producer-supplied blocking reason
  findings: list[FindingRecord] | None   # OPTIONAL; see section 3.1
  note: str | None                   # OPTIONAL free-text (e.g. a business-rule LINK-AND-CITE
                                      #   pointer per J1's FR-013 discipline); rendered verbatim
```

Empty `evidence`/`blocking_reasons` lists are valid and MUST be rendered as "no evidence
recorded" / "no blocking reasons recorded" rather than an empty, ambiguous space (spec.md Edge
Cases).

### 3.1 `FindingRecord` (embedded, B2-compatible)

Identical field names and value shapes to `core.Finding.to_dict()` (verified in research.md
section 1.1) -- this feature does not redefine this shape, only documents the contract:

```text
FindingRecord:
  rule_id: str
  severity: str        # the Finding.severity enum's serialized value, e.g. "ERROR" | "WARNING"
  message: str
  locator: str
```

A caller MAY pass `Finding.to_dict()` output (or any dict with these exact four keys) directly
into `Section.findings`.

## 4. `schema_version` and the backwards-compatibility rule

- `schema_version` is a string of the form `"<MAJOR>.<MINOR>"` (e.g. `"1.0"`), carried at the
  top level of the JSON output only (see plan.md for why Markdown/compact omit it).
- **Additive-only rule (within one MAJOR)**: a MINOR bump MAY add a new OPTIONAL field to
  `Pack`, `Section`, or `FindingRecord`. It MUST NOT remove a field, rename a field, or change
  the meaning of an existing field's value (including reassigning a status token's meaning).
- **MAJOR bump required for**: removing a field, renaming a field, changing a field's type or
  the meaning of an existing value, or removing a status token from the recognized union
  (section 1) without a pass-through fallback.
- **Consumer contract (FR-008)**: a consumer written against `schema_version: "1.x"` MUST
  tolerate (ignore) any field it does not recognize in a `"1.y"` document where `y >= x`. It
  MUST NOT fail closed merely because an unknown field is present.
- See `contracts/backwards-compat-example.md` for a concrete worked MINOR-bump example.

## 5. The fixed worst-status severity ordering (for the compact CI/PR summary)

A mechanical, reversible convention (not a business-rule judgment) used ONLY to pick which
section's status the compact summary reports as the pack's overall result (FR-006):

```text
Severity rank (highest number = reported first / "worst"):
  4  blocked
  3  warning
  2  unrecognized token (section 1's fallback row) -- surfaced, never silently ranked below
     a known-safe token; treated as at least as severe as "warning" so it is never hidden
  1  pending
  1  not_started
  0  pass
  0  not_applicable
```

Rule: the compact summary reports the HIGHEST-ranked status present across all sections, plus
every `blocking_reasons` entry from every section carrying that highest-ranked status (not just
one section, if more than one section ties at the worst rank).

Rank-0 tie-break (the "nothing blocking" outcomes, `pass` and `not_applicable`) is decided by
what is actually PRESENT, so the label never overstates:
- A pack with **at least one `pass`** section (and otherwise only `not_applicable`) reports
  `pass` -- there is a real passing section behind the label.
- A pack with **zero `pass` sections** (every section `not_applicable`) reports `not_applicable`,
  NEVER `pass`. Reporting `pass` for a pack that contains no passing section would be a
  fabricated pass (FR-012 / hard rule #9) -- forbidden. For this all-`not_applicable` case the
  compact summary carries no "at least one evidence line" requirement (there may be no evidence
  to cite), and states plainly that nothing was applicable.
An empty pack (zero sections) is an input defect, not a `pass` -- see edge cases.

This ordering is documented here, in the open, specifically so it can be reviewed and changed
by ordinary spec amendment rather than being an undocumented implementation detail (spec.md
Assumptions).

## 6. What this schema explicitly excludes (fake-confidence guard)

- No field anywhere in `Pack`, `Section`, or `FindingRecord` is a numeric score, percentage, or
  ratio intended to be read as a confidence/health/maturity value.
- No field is a bare count (e.g. `sections_passed: int`, `total_sections: int`) intended to be
  read as a completeness verdict. A consumer that wants `len(pack.sections)` can compute it
  from the `sections` list itself for its OWN purposes; the exporter does not pre-compute or
  foreground such a count as part of any rendered verdict (hard rule #9; FR-005/FR-006).
