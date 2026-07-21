---
name: retail-orchestrate
description: >-
  Drive a retail table through the medallion sequence (profile -> map -> gate ->
  build -> validate -> Power BI) by composing the existing verb-skills, and
  self-heal against the governance gate's exit code. Use when someone asks to take
  a table end-to-end, "orchestrate", "run the whole pipeline", or drive the
  medallion playbook in the Seshat BI repo. The AGENT is the runtime:
  this skill sequences and instructs; it never spawns a loop runtime, never
  self-grants the mapping approval, and HARD-STOPS at human judgment calls.
---

# retail-orchestrate

The conductor for Layer D. The kit's architecture makes the agent the primary
surface: "an agent runs the playbook conversationally ... and self-heals against
the gate." This skill is how the agent does that -- it **sequences the four
existing verb-skills** across the medallion phases and runs the **self-heal loop**
whose only success signal is a literal gate exit 0.

You (the agent reading this) ARE the runtime. This skill is procedure, not an
engine: there is no daemon, no scheduler, no persisted counter, and no
fix-applying subagent. See `specs/005-layer-d-orchestration/spec.md`.

## Scope + non-negotiables (read first)

- **Agent is the orchestrator.** Do not build or invoke a loop runtime, a counter
  file, or a subagent whose job is "run gate, apply fix, repeat." That is the
  parked orchestration runtime (architecture open decision #3). The loop below is
  something YOU perform in-context.
- **The gate exit code is the SOLE pass authority** (constitution Principle I --
  agent proposes, gate disposes). A phase advances ONLY on a literal exit 0 from
  `seshat check` / `retail validate`. Never declare a rule "passed" from reading
  prose or your own edit; only the non-zero/zero exit decides.
- **Fail-closed.** A non-zero exit blocks. Never suppress, never promote warnings
  to pass, never merge around a failing gate.
- **Two hard human seams you MUST stop at:**
  1. **Mapping gate (Principle IV):** no `silver.*` until the map is reviewed and
     approved. Read approval from existing state (below) -- never self-grant it.
  2. **Judgment calls (Principle V):** grain, PII, business rollup, the
     authoritative returns column, sentinel-vs-null -- escalate to a human; do not
     decide them to make a finding go away.
- **ASCII only, UTF-8 no BOM** in everything you author (`->` arrows, `''OR NULL`).

## Run-state: read mappings/<table>/ FIRST (no new state file)

Compute the current phase from what is already on disk -- there is NO orchestration
state file to create:

| What you observe | Current phase / action |
|------------------|------------------------|
| No `mappings/<table>/` dir | Start at **Phase 1** (source-mapping). |
| `mappings/<table>/readiness-status.yaml` missing or `stages.mapping_ready.status` != `pass`; or artifacts present with `Gate status: OPEN` (any open row) in `mappings/<table>/unresolved-questions.md` | **STOPPED at the mapping gate.** Report the open questions; do not advance. |
| `stages.mapping_ready.status == pass` WITH a matching `approvals[]` entry, and the `Gate status: CLEARED` (zero open rows) mirror agrees | Map approved -> resume at the **silver [SEAM]**. |
| `warehouse/migrations/` has the table's silver+gold | Resume at the **validate** phase. |

The canonical GO signal is `mappings/<table>/readiness-status.yaml` ->
`stages.mapping_ready.status == pass` WITH a matching `approvals[]` entry (RS1).
Its human-readable mirror is the `Gate status: CLEARED` (zero open rows) field in
`mappings/<table>/unresolved-questions.md`; the two EXISTING artifacts MUST agree.
Do NOT add a THIRD marker (e.g. an "APPROVED-FOR-SILVER" flag) -- that forks the
signal into another source of truth; if the two disagree, STOP rather than advance.
You may READ both; you may not write `mapping_ready: pass`, an `approvals[]` entry,
or `Gate status: CLEARED` yourself (approval is the reviewer's action).

## Fixed sequence (delegate to the existing verbs)

| Phase | Verb skill | Gate command | Exit gate (from medallion-playbook.md) | Next |
|-------|-----------|--------------|----------------------------------------|------|
| 1-4 Profile -> map -> stop-and-ask | **retail-onboard-table** (the Source -> Mapping front door; seeds the readiness-status and DELEGATES the five artifacts to **source-mapping**) | (artifact review) | `mapping_ready == pass` (+ `approvals[]`), `Gate status: CLEARED` mirror agrees, zero open rows | gate |
| GATE Mapping approval | (read state; **grain-confidence-reviewer** surfaces the grain-confidence card + the source-map diff for the human) | -- | reviewer recorded `stages.mapping_ready.status == pass` (+ `approvals[]`), `Gate status: CLEARED` mirror agrees | silver |
| 5 Build silver | **retail-build-warehouse** (authors the silver `.sql`) -> then **[SEAM: a human APPLIES the SQL; execution is the deferred DB-write seam]** | `seshat check` | exit 0 | gold |
| 6 Build gold (star) | **retail-build-warehouse** (authors the gold star `.sql`) -> then **[SEAM: human applies]** | `seshat check` | exit 0 | validate |
| ACCEPT Live validate | **retail-validate** | `retail validate --source-map mappings/<table>/source-map.yaml` | exit 0 (or deferred-boundary report) | semantic |
| GATE Semantic Model Ready | **retail-semantic-check** (read-only; computes the Stage-5 verdict: `seshat check` clean AND every measure binds to an approved metric contract) | `seshat check` + contract-binding read | verdict `pass` (a green checker is necessary-NOT-sufficient) | PBIP |
| 7 Build Power BI model | **pbip-workflow** + `powerbi-analyst` agent | `seshat check` | exit 0 | done |
| PBIP execution engine | **[SEAM -- Power BI execution adapter (official Power BI MCP / connection; `pbi-cli` no longer preferred), deferred + execution-only, Principle II; gated on Semantic Model Ready = pass]** | -- | -- | -- |

At every gate node, run the SAME command CI runs (`seshat check`, and
`retail validate` once creds exist) so local behavior equals the unattended gate.

## The self-heal loop (a contract you follow; not a runtime)

When a gate command returns non-zero, perform this loop IN CONTEXT:

1. **RUN** the gate command for the current phase.
2. **READ the exit code** -- this is the only authority. Exit 0 -> go to step 7.
3. **For each finding**, classify it with the table below.
4. **AUTO-FIXABLE** -> apply the single id->fix at its locator via the matching
   interpret-skill (`retail-govern` for S/D/R/C/G/P ids, `retail-validate` for V-RC
   ids). One fix at a time. Never bundle.
5. **HARD-STOP class** -> STOP the loop; append an owner row to
   `mappings/<table>/unresolved-questions.md` and escalate to the human. Do not edit
   around it.
6. **RE-RUN** the same gate; go to step 2.
7. **Advance** to the next phase.

**Bounds (you count in-context, never in a file):**
- **Max iterations** ~5 per phase. On reaching the cap -> STOP + escalate.
- **No-progress detector (primary brake):** if the same `finding-id + locator`
  appears twice, STOP + escalate -- you are flip-flopping, not converging.

**Parsing note:** key pass/fail strictly off the EXIT CODE. The finding text is a
best-effort hint for the id->fix mapping; if you cannot confidently map an id,
escalate rather than guess.

## Per-rule classification: auto-fixable vs HARD-STOP

**AUTO-FIXABLE** (mechanical, single locator, no judgment):
- `D1` measure not PascalCase -> rename.
- `D2` measure missing `displayFolder` -> add the folder.
- `D4` `/` operator -> rewrite as `DIVIDE()` **only when** the denominator is
  unambiguous; if the intended denominator is unclear, escalate.
- `S1` non-snake_case identifier; `S3` view missing `vw_`; `R1` absolute/byConnection
  PBIR ref -> repoint relative.
- `C1` literal connection -> repoint to `Server`/`Database` parameters.
- `G3` BOM; `G4` `.gitattributes` EOL entry; `G5` path length -> mechanical.

**HARD-STOP / escalate (Principle V -- never auto-fix):**
- `V-RC2` PK not unique / NULL PK -> implies a **grain decision**. NEVER dedup to
  clear it. Escalate.
- `V-RC15` / `V-RC16` (coverage / orphan / reconciliation) when the fix implies a
  business or grain choice (which rows are in scope, which dim is authoritative).
- `D6` bidirectional relationship ("or justify") -> a modeling judgment.
- `D5` implicit aggregation ("or annotate exception") -> intent call.
- `D3` duplicated measure logic where inline-vs-shared intent is unclear.
- `C2` committed secret -> removing it from the file is mechanical, but **rotation is
  a human/ops action** -- never claim the secret was rotated.
- Business-rollup mapping, PII publish-safety, the authoritative returns column,
  sentinel-vs-null.
- **Any finding id you cannot confidently classify -> default to escalate.**

## Seams (deferred by design -- report and park, never fake)

- **Applying the silver/gold SQL to the DB** -- authoring the `warehouse/` `.sql` is
  NO LONGER deferred: it shipped as F006 (`specs/006-warehouse-builder/spec.md`), and
  this conductor invokes **retail-build-warehouse** at phases 5/6 to author the files
  (in-scope, no side effects). What remains a human seam is EXECUTING that SQL against
  the database -- the DB-write step -- not authoring it. The conductor stops at the
  apply step and says so.
- **Power BI execution adapter** -- the deferred, execution-only Power BI adapter
  (official Power BI MCP / connection; `pbi-cli` no longer preferred), Principle II;
  not wired. It executes an approved model; it never defines metrics/mappings/semantics.
- **Live `retail validate` run** -- needs the `db` extra + a user DSN (Principle
  VIII). Without them, report the boundary and the enable steps (`pipx inject
  seshat-bi psycopg2-binary` or `pip install "seshat-bi[db]"`, set `DATABASE_URL`
  or `ANALYTICS_DB_*` in the gitignored `.env`);
  mark profile/validate numbers `[PENDING LIVE PROFILE]`. Never traceback, never
  fake a pass.

At a seam: state plainly what is deferred, what would unblock it, and STOP. One
conductor invocation does NOT yet produce a finished Power BI deliverable -- that is
the named-seam design, not a bug.

## What "done for this slice" looks like

A demonstrable self-heal loop on the gate that fully exists today: route a table to
`source-mapping`, stop at the mapping gate, and (since c086's silver+gold already
exist in `warehouse/migrations/`) run `seshat check` after a change and watch the
loop converge to a literal exit 0 -- while a planted `V-RC2`/`D6`-class finding
HARD-STOPS instead of being auto-fixed.

## See also

- The verbs: `.claude/skills/{retail-onboard-table,source-mapping,grain-confidence-reviewer,retail-govern,retail-validate,retail-semantic-check,pbip-workflow}/SKILL.md`.
- The spec + posture: `specs/005-layer-d-orchestration/spec.md`;
  `.specify/memory/constitution.md` Principles I, IV, V, VIII.
- The method + exit gates: `docs/medallion-playbook.md`.
- The replay reference: a filled worked example under `docs/worked-examples/`.
