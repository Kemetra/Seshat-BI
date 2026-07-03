# Contract: Compact CI/PR summary format

This is the highest fake-confidence-risk surface in the feature (spec.md Safety Constraints;
plan.md Operational risks). This contract shows both the REQUIRED shape and an explicitly
FORBIDDEN shape, so the distinction is unambiguous for implementation and for the analyze step.

## Example input (same pack as `markdown.md`: one `pass` section, one `blocked` section)

See `markdown.md` for the full input description. Worst status across sections = `blocked`
(data-model.md section 5: rank 4, the highest present).

## REQUIRED output shape

```text
[BLOCKED] <TABLE>: <STAGE> review pack

Blocking reasons:
- grain not confirmed unique on data
- PII ruling pending on column <col>

See full pack for detail.
```

Notes on the required shape:

- The bracketed leading token (`[BLOCKED]`) is the WORST recognized status token, verbatim from
  data-model.md's union -- never translated to a synonym like "FAILING" or "RED".
- Every `blocking_reasons` entry from every section tied at the worst rank is listed (FR-006) --
  so the reader loses no blocking detail by there being no count.
- The compact summary carries NO numeric section count in ANY form -- no `N of M`, no
  percentage, no fraction, no tally (FR-005, FR-006, hard rule #9). An earlier draft of this
  contract included a "(1 of 2 sections at this status)" parenthetical for "traceability"; it
  was REMOVED because a `\d+ of \d+` string sits exactly on the line this whole feature exists
  to hold, and the per-section detail is already fully recoverable from the pointer to the full
  pack (and from the Markdown/JSON formats). The closing pointer is a plain "See full pack for
  detail." with no digits. If a future maintainer wants to indicate WHICH sections triggered
  the status, they MUST do it by naming the section(s) (e.g. "in section: Readiness state"),
  never by a count.

## FORBIDDEN output shapes (negative examples -- MUST NOT appear)

```text
# FORBIDDEN: a health percentage
[50% HEALTHY] <TABLE>: <STAGE> review pack
```

```text
# FORBIDDEN: a bare completeness tally presented as the verdict
1 of 2 sections passed.
```

```text
# FORBIDDEN: a maturity/confidence label with no basis in an explicit status token
[MOSTLY READY] <TABLE>: <STAGE> review pack
```

Any of these forms violates FR-005/FR-006 and hard rule #9 and MUST fail a review of the
implementation.

## Second worked example: an all-clear pack

Input: a pack with sections `pass` and `not_applicable` only (no `blocked`/`warning`/
unrecognized token present).

```text
[PASS] <TABLE>: <STAGE> review pack

Evidence:
- <STAGE> gate requirement documented at docs/readiness/<stage>-ready.md
```

- Worst rank present is `pass`/`not_applicable` (rank 0); the reported label prefers `pass`
  (data-model.md section 5 tie-break).
- At least one evidence line is cited (SC-001-adjacent traceability), never a bare "all good"
  with no citation.

## Third worked example: an empty pack

Input: a pack with `sections: []`.

```text
[NO SECTIONS] <TABLE>: <STAGE> review pack

No sections in pack.
```

- Never rendered as `[PASS]` (spec.md Edge Cases: a zero-section pack must not read as a
  fabricated pass).
