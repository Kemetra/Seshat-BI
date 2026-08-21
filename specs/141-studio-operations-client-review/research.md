# Research: Studio Operations and Client Review (spec 141)

**Date**: 2026-08-21

Every finding below was read from the shipped tree at `421c8f4d`, not inferred from the
outline. Each names its source so a reviewer can re-verify.

## R1 -- The prerequisite is genuinely met, and the distinction mattered

FR-141-020 requires specs 139 and 140 **accepted**, which is a stronger state than
ratified. The repo distinguishes them:

- 139: `implemented -- all 38 tasks complete; accepted by Ahmed Shaaban, 2026-08-16`
- 140: `implemented -- all 19 tasks delivered and merged (421c8f4d, PR #695); accepted by
  Ahmed Shaaban, 2026-08-21`

Before 2026-08-21 spec 140 read only `ratified`, and 141's own gate note said so
explicitly. That is why the owner's ratification request on 141 was answered with a
promotion rather than a status line: the gate names *acceptance*, and acceptance had not
happened yet.

**Consequence**: promotion is unblocked; implementation is not.

## R2 -- `doctor.py` already produces categorical findings

`seshat/doctor.py` ships the diagnostic engine US1 needs, including grouping and
non-mutating repair hints (delivered as M8, 2026-08-21). It emits machine-readable JSON
and names a next allowed action.

**Consequence**: FR-141-004 forbids a second diagnostic engine. Operations is a *view*
over `doctor.py` findings. A parallel probe set would drift from the one the CLI reports,
and then a technician reading Studio and a technician running `seshat doctor` would get
different answers about the same machine.

**Caution for implementers**: `doctor` is advisory and explicitly *not* a second gate.
Presenting its output as authority would breach Principle I.

## R3 -- Normalized events exist; raw transcripts must not be read

`studio/events.py` ships `StudioEvent`, `ThreadEvents`, `ThreadStore`, plus
`normalize_payload`. Foundation already draws the line between a normalized event and a
provider transcript.

**Consequence**: FR-141-007 is satisfiable by consuming `ThreadStore` rather than
inventing a history store. It also means the ephemeral/durable distinction (FR-141-009,
FR-141-010) is a property of *where* a record lives -- process memory versus a committed
receipt -- not a label the UI applies by preference.

## R4 -- The three-state decision model is the constraint Client Review inherits

Spec 140 shipped `draft` -> `pending commit` -> `authoritative`, with
`decision_write.RECEIPT_STATES` a single-member tuple so an uncommitted decision cannot
be represented as approved, and `decisions_at_head` reading committed state.

**Consequence**: FR-141-021. A client-facing surface is exactly where the temptation to
show a recorded-but-uncommitted decision as "done" is strongest, because the client asked
for an outcome and one exists on disk. The type-level guard from 140 stops the write side;
141 needs its own explicit rule for the *render* side, since a presentation layer can lie
without touching the receipt.

## R5 -- Two redaction layers exist, and one is not enough

`studio/redaction.py` provides `scrub_payload`, `redact_credentials`, `redact_paths`, and
`redact_for_boundary`, over the shared `seshat/redaction_core.py`.

**Consequence**: FR-141-008 consumes these rather than adding a third path. The repo's
own lesson applies: `redact()` alone is layer one, and a bare tenant GUID passes through
it -- every output surface must also apply the secret-shaped scrub. An export surface is
a new output surface, so it needs both.

## R6 -- Allowlist, not denylist, for the support bundle

The outline already specified this (FR-141-012) and it is worth keeping verbatim: a
denylist applied after assembly fails open on the field nobody enumerated. `evidence_pack.py`
is the shipped precedent for a self-contained export and should be read before designing
the bundle format.

**Consequence**: FR-141-014 requires the scan to run on *staged* content before
finalization, and a scan failure to abort. Shipping a partially scrubbed archive is worse
than shipping none, because the recipient assumes it was scrubbed.

## R7 -- `review_scope` already filters server-side

Spec 140 shipped `studio/review_scope.py`: an explicit scope is required (an absent scope
is refused rather than defaulted to everything), withheld fields are stripped from the
assembled payload rather than at each construction site, and decline plus
request-clarification are always offered.

**Consequence**: US4 and US3's scoping requirements consume this. The "strip from the
assembled payload" choice matters for 141 specifically: a field added upstream later is
withheld by default instead of leaking until someone notices.

## R8 -- No aggregate score, anywhere

The repo prohibits fabricated confidence and aggregate readiness scores as a standing
rule, and the outline restates it. `doctor.py` deliberately reports per-component
findings without a roll-up.

**Consequence**: FR-141-002 and SC-141-001. The test should search payloads for a numeric
roll-up rather than assert the absence of a specific field name -- an absence-assertion on
a field name goes green when the same value ships under a different key.

## Open questions

None blocking. Two items deferred to the plan rather than the spec:

1. Whether Operations is a new route set or an extension of the existing workbench
   registrar -- a structural choice constrained by the repo's single-file health gate,
   and worth deciding after reading how `workbench_routes.py` turned out.
2. The support bundle's archive format and manifest shape, which should follow
   `evidence_pack.py` rather than be designed fresh.
