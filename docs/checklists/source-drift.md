# Source Drift -- re-profile / compare checklist

Planning (docs/templates; no runtime code) -- DESIGN ONLY (roadmap F014).

The ordered steps an operator (or a future drift runtime) follows to re-certify a source
against its recorded baseline and fill `templates/source-drift-report.md`. The "gate" is
the existing Source Ready review, now able to read a drift report as evidence -- this
adds NO new gate. See `docs/readiness/source-drift.md` for the taxonomy. ASCII only.

---

## 1. Pin the baseline

- [ ] The table has a committed `mappings/<table>/source-profile.md` that earned Source
      Ready `pass`. If NOT, STOP -- there is nothing to drift FROM; the table is
      `not_started` (stage 1), not "drifted".
- [ ] Record the baseline commit/date in the report header. The baseline is IMMUTABLE for
      the duration of the drift run.

## 2. Re-profile with the SAME measures (deferred-live)

- [ ] Re-profile the same `<schema>.<table>` over a READ-ONLY connection (secrets only in
      the git-ignored `.env`), using the SAME measures as the baseline -- do not invent
      new ones:
  - [ ] missingness as `'' OR NULL` (RC5), never `IS NULL` alone;
  - [ ] candidate-PK uniqueness `COUNT(*) = COUNT(DISTINCT pk)` with `0` NULL PK (RC2);
  - [ ] returns population from the AUTHORITATIVE billing column (RC8), never a measure sign.
- [ ] If the DSN / `db` extra is absent: STOP the live step; mark the report
      `[PENDING LIVE RE-PROFILE]` and record `warning` -- never fabricate a comparison
      (Principle VIII). The runtime, when built, reuses `src/seshat/profile.py`.

## 3. Classify each difference

- [ ] For each diff, assign exactly one taxonomy class (column added/removed/retyped,
      missingness shift, cardinality shift, grain/PK drift, returns-rule drift,
      semantic-pair drift, PII surface drift) with its before/after MEASURED cells.
- [ ] Apply the default severity; escalate `column retyped` / `semantic-pair drift` to
      `blocked` when it touches a key/measure or underpins identity.
- [ ] Tolerances not recorded on the baseline -> record any movement as an observation at
      `warning`; raise a follow-up to set tolerances (never treat as zero-drift).

## 4. Set the Source Ready status

- [ ] No material drift -> `pass` (evidence = the report). Only non-fatal classes ->
      `warning`. Any fatal class -> `blocked` with `blocking_reasons[]` enumerating them.
- [ ] Record NO drift "score" -- statuses + measured per-class magnitudes + blockers only
      (roadmap rule #9).
- [ ] Flag downstream `pass` stages (Mapping/Silver/Gold/...) as SUSPECT / re-confirm
      required; do NOT silently demote or auto-`pass` any downstream stage.

## 5. Hand Principle-V classes to a human (HARD-STOP)

- [ ] grain/PK drift, returns-rule drift, PII surface drift, and identity-bearing
      semantic-pair drift each: set `blocked`, raise an `unresolved-questions.md` row with
      the named owner (analyst / governance / data-owner), and propose NOTHING -- never
      re-decide grain, re-rule PII (default stays `drop`), or re-pick the returns column.

## 6. Wire into the readiness status

- [ ] Update `mappings/<table>/readiness-status.yaml` (ADR 0004): set
      `source_ready.status`, append the drift report to `evidence[]`, populate
      `blocking_reasons[]` from the fatal classes, record the downstream-suspect note +
      `last_checked_at`/`checked_by`. No status-schema change is required.

## See also

- The taxonomy + status mapping: `../readiness/source-drift.md`.
- The blank this fills: `../../templates/source-drift-report.md`; the baseline:
  `../../templates/source-profile.md`; the Principle-V handoff:
  `../../templates/unresolved-questions.md`.
- The measures reused: `../decisions/0002-retail-cleaning-defaults.md` (RC2/RC5/RC8); the
  deferred-live profiler: `../../src/seshat/profile.py`.
- The roadmap row: `../roadmap/roadmap.md` (F014). A filled worked example lives under
  `../worked-examples/`.
