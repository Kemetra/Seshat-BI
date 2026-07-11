---
name: retail-semantic-check
description: >-
  Compute the Semantic Model Ready (Stage 5) readiness verdict for a committed
  Power BI PBIP model in the Seshat BI repo. Use after Gold Ready is
  `pass`, when someone asks whether the semantic model is ready, to check that every
  measure binds to an approved metric contract, or before any dashboard/PBIP work.
  READ-ONLY and invoke-and-interpret only: it runs the existing `retail check` gate,
  reads the committed TMDL and the filled metric-contract store (F009), and emits ONE
  status (not_started | blocked | warning | pass) with evidence + blockers, then
  STOPS. It NEVER edits TMDL, NEVER defines/approves a metric contract (that is F009),
  and NEVER calls the Power BI execution adapter (official Power BI MCP / connection;
  `pbi-cli` no longer preferred) -- that is F016.
---

# retail-semantic-check

`retail check` proves the model is mechanically clean (PascalCase measures, display
folders, DIVIDE, single-direction relationships, a marked date table, gold-only
partitions, parameterized connection, no real host). This skill answers the larger
question that clean text alone cannot: **is the semantic model GOVERNED** -- does
every measure trace to an APPROVED metric contract, with the gold star already
live-validated underneath it? It computes the Stage-5 verdict and STOPS -- the live
sibling of `retail-govern` / `retail-validate`, one layer up: it governs the SEMANTIC
MODEL, not the SQL. It implements the procedure that
`docs/readiness/semantic-model-ready.md` specifies; it redefines nothing.

## Scope boundary (read first)

Invoke-and-interpret only, and READ-ONLY.

- **CHECKS the model.** Reads the committed PBIP TMDL, reads the filled
  metric-contract store, runs `retail check`, evaluates the contract-binding
  criterion, and emits one readiness verdict. All side-effect-free reads over
  committed text -- the same category as `retail-govern` reading TMDL.
- **NEVER DEFINES contracts (F009).** The metric-contract store (name, grain, formula
  intent, owner, approval) is defined and owned by feature F009 (the `metric-contract`
  template + the `metric-contract-store` guide). This skill is the CONSUMER: it reads
  contracts to test the binding; it never creates, edits, or approves one.
- **NEVER AUTHORS or EXECUTES the model (F016, deferred + gated).** It writes no TMDL, adds/edits
  no measure / relationship / date marker, opens no DB connection, and calls no
  the Power BI execution adapter (official Power BI MCP / connection; `pbi-cli` no
  longer preferred) (constitution Principle II; roadmap hard rule #6 -- F016
  is last and gated on THIS stage being `pass`). It reads an EXISTING model and
  reports; a human edits Power BI Desktop and re-saves the PBIP to remediate.

## Prerequisites

- The prior stage **Gold Ready is `pass`** -- read it from the canonical
  `mappings/<table>/readiness-status.yaml` (ADR 0004; shaped to
  `templates/readiness-status.yaml`). This stage sits AFTER the live-validation hard
  gate (no gold to Power BI before validation, roadmap rule #4). If Gold Ready is not
  `pass`, the verdict is `not_started` and the skill STOPS.
- The committed PBIP model exists under `powerbi/<Model>.SemanticModel/definition/`.
- The metric-contract store (F009) -- the FILLED, per-table contracts -- may or may
  not exist. Its absence is not an error; it is the reason the verdict is `blocked`
  (see the central property below).

## The store is FILLED contracts, not the template (read this before binding)

F009 ships the TEMPLATE (`templates/metric-contract.yaml`) and the authoring guide
(`docs/metrics/metric-contract-store.md`). The TEMPLATE is the shape, NOT the store.
A binding target is a FILLED, owner-APPROVED contract at the canonical store location:

```
mappings/<table>/metrics/<MetricName>.yaml   # filled per-table contracts (the store)
metrics/packs/<pack_name>.yaml               # reusable KPI packs (group filled contracts)
```

NEVER treat the existence of `templates/metric-contract.yaml` (or `kpi-pack.yaml`) as
"the store is present". The template existing is the F009 deliverable; it binds to
nothing. If no filled contract exists for a measure, that measure is unbound -> a
`blocking_reason`.

## The central property: a green `retail check` is NECESSARY, not SUFFICIENT

A clean mechanical gate (`retail check` exit 0) does NOT make this stage `pass`.
`pass` ALSO requires the contract-binding criterion satisfied AND the metric owner's
approval recorded as evidence. Emitting `pass` on a green checker alone would be a
silent governance hole -- a perfectly-formed model whose measures bind to nothing.
When the gate is green but no filled, approved contract backs the measures, the
verdict is `blocked`, not `pass`, and the green run is cited as MECHANICAL-pass-only.

## Run it -- the fixed 5-step evaluation order (do not reorder)

### 1. Ordering gate
Read `mappings/<table>/readiness-status.yaml`. If that file is **absent or
unreadable**, or `gold_ready.status` is anything other than `pass`, emit
`not_started`, record the blocking reason "prior stage Gold Ready is not proven
`pass`" (an absent readiness file means gold has not been live-validated -- e.g. the
deferred DB boundary), and STOP. Never check a model whose source gold is unproven
(Principle VIII). Reaching the binding criterion (step 4) requires clearing this gate
first; `not_started` here takes precedence over a `blocked` the later steps would
produce.

### 2. Mechanical gate
Run the same command CI runs:

```
retail check
```

Any `D1`-`D8` (TMDL/DAX), `C1` (connection params), `R1` (relative reference), or
`G6` (no real host) finding is a distinct `blocking_reason` (cite the id + locator;
hand the fix to the `retail-govern` interpret table). Record the exit code as
evidence: **exit 0 is MECHANICAL-pass-only**, never a stage pass by itself.

### 3. Structural facts (interpret, do not re-implement)
The structural readiness the stage doc requires is already surfaced by step 2 --
interpret it, never re-code it:

| Fact | Surfaced by | Pass means |
|------|-------------|------------|
| Relationships present + single-direction | `D6` | star relationships exist; no bidirectional (or a justified, annotated exception) |
| A marked date table | `D7` | the `DATE_TABLE_MARKER` annotation OR table-level `dataCategory: Time` + a key column is present |
| Measures PascalCase, in display folders | `D1`, `D2` | every measure is PascalCase and carries a `displayFolder` |
| Gold-only partitions | `D8` | every partition reads `gold` only |

A finding here is a step-2 `blocking_reason`; a clean pass here is recorded as part of
MECHANICAL-pass-only, still not a stage pass.

### 4. Contract-binding (the criterion this stage adds)
Read the FILLED metric-contract store (see "The store is FILLED contracts" above).
For EACH PascalCase measure in the model:

- **Matched + approved** -> a measure that maps to a filled contract whose
  `readiness.status` is `pass` with owner-approval evidence (owner + date). Record the
  contract name + owner + date as `evidence[]`.
- **Unmatched** (no filled contract for the measure) -> a distinct `blocking_reason`
  naming the measure. NEVER auto-create the contract.
- **Matched but not approved** (a filled contract exists but its status is not `pass`
  / no owner approval recorded) -> `blocked` ("owner approval missing for <contract>").
  Approval is a human action the skill cannot self-grant (Principle V).
- **Store absent** (no `mappings/<table>/metrics/` filled contracts at all) ->
  `blocked` ("no filled, owner-approved metric contracts exist for this model's
  measures; the F009 template ships the shape but no per-table contract is authored").
- **Ambiguous mapping** (a measure name that does not map cleanly to a contract key)
  -> HARD-STOP and raise it for a human; never guess a match.

### 4b. Contract<->DAX drift (L3 -- the measure's LOGIC matches its contract)

Binding (step 4) proves a measure maps to an approved contract; it does NOT prove the
DAX LOGIC matches the contract's approved definition. A measure can bind to its
contract and still compute the WRONG number (the 50.37-vs-33.55 class: a denominator
over all transactions when the contract rules known-status only). `retail check` (D-rules)
sees only form; nothing else sees a wrong denominator. L3 closes that gap.

For each measure whose contract carries an optional machine-readable `definition`
block, invoke the drift checker (a lazy module -- it reads YAML, so it is NOT part of
the `retail check` core; mirrors `validate_targets`):

```python
from retail.metric_drift import load_definition, check_measure_drift
defn = load_definition("mappings/<table>/metrics/<Measure>.yaml")  # None if no block
verdict = check_measure_drift(<the measure's DAX body from the TMDL>, defn)
# verdict.status in {pass, drift, escalate, skip}
```

Map the per-measure status to this stage:

- **pass** -> the DAX denominator filter-set matches the contract; record as `evidence[]`.
- **drift** -> a recognized mismatch (wrong/missing/extra denominator filter, wrong
  column) -> `blocked` with the measure named ("DAX denominator drifts from the
  approved contract definition"). The fix is a human Desktop edit (re-save the PBIP) or
  a contract correction -- never self-applied here.
- **escalate** -> the DAX uses a predicate spelling the checker does not recognize, is
  not a DIVIDE ratio, or is unparseable -> HARD-STOP and raise it for a human; NEVER
  guess pass or drift (the contract -- not the DAX shape -- is the sole arbiter; an
  unrecognized form is a human judgment call, Principle V).
- **skip** -> the contract has no `definition` block yet -> no L3 finding (binding from
  step 4 still governs). Backward-compatible; contracts adopt the block incrementally.

The contract is the SOLE arbiter of the correct denominator direction. NEVER infer the
intended denominator from the DAX or the prose (an inference can be inverted -- it has
been). Only the structured `definition` decides; absent it, L3 stays silent (skip).

### 5. Verdict
Combine into EXACTLY ONE status, shaped to `templates/readiness-status.yaml`, with
`evidence[]` (committed files + the `retail check` run) and `blocking_reasons[]`:

| Verdict | When |
|---------|------|
| `not_started` | step 1 failed (Gold Ready not `pass`) |
| `blocked` | any step-2/3 finding, OR any unmatched/unapproved measure, OR store absent, OR an L3 `drift` (step 4b: DAX denominator contradicts the contract definition) |
| `warning` | `retail check` clean + binding satisfied, but a non-fatal recorded item (e.g. an accepted display-folder deviation), OR an L3 `escalate` left for human classification; never auto-promotes |
| `pass` | steps 2-4(+4b) ALL clear AND every measure binds to an approved contract AND owner approval is recorded as `evidence[]` (any measure with a `definition` block is L3 `pass` or `skip`; none `drift`/`escalate`) |

A `pass` MUST carry evidence; never fabricate a confidence number (roadmap rule #9 --
the four explicit statuses + evidence + blockers are the only vocabulary). Then STOP.

## Read-only / author-nothing contract

This skill writes no TMDL, edits no measure / relationship / date marker, opens no DB
connection, invokes no Power BI execution adapter (official Power BI MCP / connection;
`pbi-cli` no longer preferred), and modifies no file under
`powerbi/`. For every FIXABLE finding it REPORTS the human remediation step rather
than applying it:

| Fixable finding | Human remediation (the skill reports; never self-edits) |
|-----------------|---------------------------------------------------------|
| `D1` measure not PascalCase | rename the measure in Power BI Desktop, re-save the PBIP |
| `D2` measure missing `displayFolder` | set its display folder in Desktop, re-save the PBIP |
| `D4` `/` instead of `DIVIDE()` | rewrite the measure in Desktop, re-save the PBIP |
| `C1`/`R1`/`G6` connection / ref / host | repoint to parameters / a relative ref in Desktop, re-save |
| An unbound measure | author + owner-approve the metric contract under F009 (`mappings/<table>/metrics/`), not here |

Programmatic remediation (editing TMDL, marking a date table, adding a measure) is the
deferred, execution-only F016 Power BI adapter (official Power BI MCP / connection;
`pbi-cli` no longer preferred), gated on this stage being `pass` (Principle II;
hard rule #6).

## Fail-loud judgment-stop table (HARD-STOP, never a silent default)

Each of these STOPS and is raised for a human -- the skill never picks a default:

| Situation | Why it stops |
|-----------|--------------|
| Filled metric-contract store absent | nothing to bind to; `blocked`, never a guessed pass |
| A measure name not cleanly mappable to a contract key | guessing a match would mis-govern; raise the ambiguous mapping |
| `warning`-vs-`blocked` ambiguity | the analyst classifies the non-fatal item; do not auto-pick |
| Owner identity unclear for an approval | approval is a NAMED human action; the skill cannot self-grant it |

Grain semantics, PII publish-safety, business-rollup mappings, and product-identity
are NOT decided by this skill -- they belong to the metric owner / F009 (Principle V).

## What to do after interpreting

Report the one verdict, its `evidence[]`, and each `blocking_reason` with the measure
or finding id it names and the one place to fix it (Desktop edit + re-save PBIP for
mechanical findings; author + owner-approve a contract under F009 for unbound
measures). Then STOP -- re-running the check after a human remediates is the user's
next call, not a loop this skill performs.

## See also

- The stage authority (required artifacts, checks, statuses, approver):
  `docs/readiness/semantic-model-ready.md`.
- The spine: `docs/readiness/readiness-model.md`, `docs/readiness/readiness-pipeline.md`.
- The contracts it consumes (owned by F009): `templates/metric-contract.yaml`,
  `templates/kpi-pack.yaml`, `docs/metrics/metric-contract-store.md`.
- The mechanical gate it calls: `retail check` (`D1`-`D8` `src/seshat/rules/dax.py`,
  `C1`/`R1` `src/seshat/rules/pbir.py`, `G6` `src/seshat/rules/g6.py`); the
  `retail-govern` skill for the id -> fix mapping.
- The live sibling one layer down: the `retail-validate` skill.
- The model under check: `powerbi/Retailgold.SemanticModel/definition/`.
- The next stage (gated on this one passing): `docs/readiness/dashboard-ready.md`,
  the `dashboard-design` skill (F011).
- Roadmap hard rules #4 (gold validated first), #5 (no dashboard before contracts),
  #6 (no pbi-cli before this stage passes), #9 (no fake confidence):
  `docs/roadmap/roadmap.md`.

## Orchestration

When a table is driven end-to-end, the `retail-orchestrate` conductor parks at the
Phase-7 model seam and invokes this verb to compute the Semantic Model Ready verdict
BEFORE any Power BI authoring. A `pass` is the gate that lets the next phase
(dashboard design, then the deferred F016 PBIP adapter) proceed; anything else STOPS
the conductor with the blocking reasons. This skill stays single-purpose: it computes
one verdict and STOPS. The self-heal loop (run gate -> classify -> auto-fix mechanical
/ HARD-STOP judgment calls -> re-run) lives ONLY in `retail-orchestrate`, never here;
and contract approval is a human action no loop self-grants.
