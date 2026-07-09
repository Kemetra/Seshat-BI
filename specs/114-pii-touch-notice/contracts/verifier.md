# Contract: the FR-011 verifier (test-only, non-gating)

The mechanical guarantee that separates this notice from a free-composed summary.
It lives in the test suite, NOT in `retail check` (FR-007 forbids a gating rule).

## `assert_notice_is_faithful(notice_text: str, source_map: dict) -> None`

Given a rendered notice and the parsed source-map it was composed from, raises
`AssertionError` unless ALL hold:

- **V1 verbatim substring**: for every disclosure line that quotes a disposition,
  the quoted string is a character-for-character substring of some committed
  source-map field (a `columns[].reason` or a `defaults.deviations[].reason`).
  No paraphrase can pass (SC-002).
- **V2 completeness / never-omit**: the set of columns named in the notice's
  PII-flagged section plus its GAP section equals the set of `columns[]` with
  `pii is True`. No `pii:true` column is missing (FR-004, SC-003).
- **V3 never-clear**: no line for an `undecided` column contains a clearance
  token from a closed denylist (`safe`, `cleared`, `no pii risk`, `approved`,
  `ok to publish`), and every GAP line carries the "NOT cleared" framing
  (FR-005, SC-004). (A DECIDED line may contain such a token ONLY inside the
  verbatim-quoted disposition -- V1 already binds that text to a committed
  source, so it is an attributed echo, not an authored claim.)
- **V4 no-score**: the notice contains no numeric score / risk-level / "N of M"
  count token (FR-006, SC-004).
- **V7 join-correctness (SAFETY; ratify OPEN-2 RULED -- explicit `deviation_ref`)**:
  for a kept-PII column whose disposition is drawn from a `defaults.deviations[]`
  entry, assert the disposition's deviation id EQUALS the column's `deviation_ref`
  field (exact match). V1 (verbatim-substring) is INSUFFICIENT alone: a mis-joined
  disposition is still a verbatim substring of a committed field and would pass
  V1-V4 while presenting an ungoverned column as cleared. Concretely: (a) assert
  the rendered disposition text == the `reason` of the deviation whose `id` ==
  `deviation_ref`; (b) add a fixture where a kept-PII column's `deviation_ref`
  points at a deviation that is NOT the one whose prose mentions the column
  (e.g. two deviations RC4/RC8) -- proving the composer joins by `deviation_ref`,
  NOT by text; (c) add a fixture where a kept-PII column has NO `deviation_ref` ->
  assert it renders as a GAP, never a guessed match. This assertion MUST exist
  before US1/US2 implementation lands.

## Fixtures the verifier runs against

| Fixture | Shape | Expected |
|---------|-------|----------|
| decided-kept | `pii:true, decision:keep` + RC4 disposition (the `customer_id` shape) | one decided_kept line, verbatim disposition |
| decided-dropped | `pii:true, decision:drop` + drop `reason` | one decided_dropped line, verbatim reason |
| undecided (SAFETY) | `pii:true` with NO reachable disposition | one GAP line, "NOT cleared", column present |
| no-pii | all `pii:false` | "No column ... flagged" statement, no findings |
| missing-source-map | no `source-map.yaml` | one document-level GAP |
| inconsistent | `pii:true`+`keep` but also in drop signals | GAP naming both loci (FR-010) |

## Read-only proof (V5, SC-005)

A test invokes `--write` in a temp copy of a table dir and asserts `git status`
(or a filesystem diff) shows ONLY `pii-touch-notice.md` changed and no upstream
artifact touched; and that `build_pii_notice` performs no DB/network import.

## Generic proof (V6, SC-006)

The verifier runs against at least two distinct tables (e.g. `retail_store_sales`
and a second fixture table) with the SAME composer code and no per-table branch,
proving Principle-VII genericity.
