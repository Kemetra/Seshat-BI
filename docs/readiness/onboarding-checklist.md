# Table Onboarding Checklist

Planning (docs/templates; no runtime code).

The text-first, reviewable definition-of-done for the **Source Ready -> Mapping
Ready** onboarding walk that the `retail-onboard-table` skill performs (roadmap F006,
Layers 1-2). It mirrors the two stage docs it spans -- `source-ready.md` and
`mapping-ready.md` -- and calls out the four Principle-V human seams as explicit STOP
rows. The wizard ENDS at Mapping Ready; Silver Ready is out of scope.

## Stage 1 -- Source Ready (profile + PROPOSE semantics)

Definition-of-done mirrors `source-ready.md`'s `pass` criteria.

- [ ] No prior `mappings/<table>/` exists (fresh onboarding), OR resume from the first
      incomplete artifact without clobbering a committed one.
- [ ] `mappings/<table>/source-profile.md` records the MECHANICAL numbers over a
      READ-ONLY connection:
  - [ ] row count + column count;
  - [ ] per-column missingness as `'' OR NULL` (never `IS NULL` alone -- RC5);
  - [ ] candidate-key uniqueness proof (does the proposed PK hold on the data?);
  - [ ] returns-column population.
- [ ] Semantic rows are PROPOSED for human confirmation, never invented.
- [ ] `source_ready` recorded: `pass` (numbers measured, profile as evidence),
      `warning` (deferred-boundary mode -- numbers `[PENDING LIVE PROFILE]`), or
      `blocked` (a required number unmeasurable -> do NOT enter Stage 2).

**Stage gate:** Stage 2 is entered ONLY when `source_ready` is `pass` (or `warning`
in deferred mode); never on a `blocked` source.

## Stage 2 -- Mapping Ready (delegate to source-mapping)

Definition-of-done mirrors `mapping-ready.md`'s artifact set. The wizard DELEGATES
authoring to the `source-mapping` skill; it does not re-implement mapping.

- [ ] `source-map.yaml` -- grain statement, PK column(s), every column's `pii:` flag,
      gold placement (fact vs dim, conformed dims).
- [ ] `assumptions.md` -- RC1-RC16 each marked adopted/deviated; every deviation cites
      a concrete data fact.
- [ ] `unresolved-questions.md` -- the open judgment calls; `Gate status: OPEN` until
      a human clears it (the wizard never writes `CLEARED`).
- [ ] `reconciliation-report.md` blank emitted (the live-acceptance run, filled later).
- [ ] `mapping_ready` recorded `blocked` (review pending) with a blocking reason --
      NOT `pass`, and NOT `Gate status: CLEARED` (that is the human's act).

## Human seams -- HARD-STOP (Principle V; propose, never answer)

Each row is a STOP: PROPOSE with the supporting data fact, raise an
`unresolved-questions.md` row with a NAMED owner, set the matching
`blocking_reasons[]`, and STOP. Never satisfiable by a silent default.

- [ ] **Grain** -- candidate PK not unique on the rows -> report the duplicate count;
      propose the finer grain / composite PK; never collapse or pick silently. Owner:
      analyst.
- [ ] **PII publish-safety** -- a `pii:true` candidate -> propose the default (drop
      before the BI layer, RC4); raise the publish-safety question. Owner: governance.
- [ ] **Business rollup / segment** -- a categorical needing a value->group mapping ->
      never invent it; raise it for the analyst-supplied table; unmapped -> `UNMAPPED`.
      Owner: analyst.
- [ ] **Product identity** -- which column authoritatively identifies the entity (or
      two disagree) -> report the conflict; never assert identity. Owner: analyst /
      data owner.
- [ ] **Conflicting answer** -- an analyst answer contradicts a profiled data fact ->
      surface the conflict and STOP to reconcile; do not proceed.

## Resume + deferred mode

- [ ] **Resume** -- re-running recomputes the stage from disk (`mappings/<table>/`
      presence, the five artifacts, `Gate status`); it resumes, never restarts, and
      never overwrites a committed artifact. No separate run-state file is created.
- [ ] **Mapping Ready reached** -- when `Gate status: CLEARED` + an `approvals[]` entry
      exist, promote `mapping_ready: pass` (evidence = artifacts + approval), state
      Silver Ready is the next (out-of-scope) stage, and STOP. Never author silver.
- [ ] **Deferred-boundary mode** -- no DSN / no `db` extra: no traceback, no fabricated
      numbers; mechanical rows `[PENDING LIVE PROFILE]`; `source_ready: warning`; print
      the enable steps (`pipx inject seshat-bi psycopg2-binary` or `pip install
      "seshat-bi[db]"`; set `DATABASE_URL` in the git-ignored `.env`; never commit a
      real DSN).

## Terminal definition-of-done

- [ ] The readiness-status at `mappings/<table>/readiness-status.yaml` is seeded
      (`source_ready` + `mapping_ready` + `current_stage` + `next_action`), with
      evidence for any `pass` and blockers for any `blocked`; NO numeric score.
- [ ] The wizard wrote NO `silver.*` SQL and self-granted NO approval.
- [ ] The final message states the SINGLE next allowed action and which surface owns
      it (human review; then Silver Ready / `retail-build-warehouse`, out of scope).

## See also

- The stages: `source-ready.md`, `mapping-ready.md`.
- The skill that performs this walk: `../../.claude/skills/retail-onboard-table/SKILL.md`.
- The delegated mapping leg: `../../.claude/skills/source-mapping/SKILL.md`.
- The spine: `readiness-model.md`, `readiness-pipeline.md`;
  `../../templates/readiness-status.yaml`.
- The roadmap row: `../roadmap/roadmap.md` (F006). A filled worked example under
  `../worked-examples/` is the first real instance, not the schema.
