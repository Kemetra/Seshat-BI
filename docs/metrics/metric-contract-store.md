# Metric Contract Store

Planning (docs/templates; no runtime code).

Layer 5 (Metrics & Semantic Model), feature F009. The metric-DEFINITION layer: a
committed, reviewable store of metric contracts (and the KPI packs that group them)
that the Semantic Model Ready stage reads. This guide defines where filled contracts
live, their lifecycle, and the rules a reviewer applies. It is the authoring home for
`templates/metric-contract.yaml` and `templates/kpi-pack.yaml`.

## Purpose

A **metric contract** is the atomic, reviewable DEFINITION of one metric: its stable
name, the grain it is valid at, its formula INTENT (plain language, not DAX), its
named owner, and the `gold` column(s) it binds to. It exists so a downstream Power BI
measure can TRUST a metric -- and trust requires an explicit, owner-approved
definition recorded as evidence, never a number a tool guessed.

This is the missing artifact the Semantic Model Ready stage
(`docs/readiness/semantic-model-ready.md`) waited on: "every measure traces to a
metric contract owned by the metric owner." Until a contract exists and is approved,
a measure has nothing to bind to. This feature ships the template, the pack template,
and these store rules -- so a contract can be DEFINED. It does not check a model.

## The define / check boundary (the load this feature respects)

This boundary is stated VERBATIM in `templates/metric-contract.yaml`,
`templates/kpi-pack.yaml`, and here -- it must not drift:

> This feature DEFINES contracts (and groups them into packs). It does NOT CHECK a
> model. Nothing here reads `powerbi/<Model>.SemanticModel/`, asserts a measure /
> relationship / marked date table, or adds a `retail check` rule. CHECKING a PBIP
> model against these contracts is the SEPARATE later feature F010 (on-disk feature
> 011, Semantic Model Readiness). A contract is INTENT + binding + an explicit
> readiness status; it is never the DAX, never a visual, never a check.

- **DEFINING is in-scope.** Authoring committed contract / pack TEXT is the same
  category as `source-mapping` authoring `mappings/` artifacts: no side effects, no
  PBIP read, no DB connection.
- **CHECKING a PBIP model is OUT of scope (F010 / on-disk 011).** Reading
  `powerbi/`, asserting a measure exists, asserting relationships or the marked date
  table, running `retail check`'s D1-D11 over TMDL -- all belong to the checking half.
- **No dashboard design (roadmap hard rule #5).** Contracts come BEFORE dashboards;
  designing visuals is F011, gated on approved contracts existing -- which is exactly
  what this store produces.

## Where filled contracts and packs live (O-1, recommended default)

Filled instances are NOT created by this feature; this guide only defines their
location. The default below follows ADR 0003's "cohesive per-table working set"
rationale and is cheaply reversible (a path move):

| Artifact | Location | Why here |
|----------|----------|----------|
| A filled metric contract | `mappings/<table>/metrics/<MetricName>.yaml` | co-located with that table's mapping + readiness artifacts -- one working set per table |
| A reusable KPI pack | `metrics/packs/<pack_name>.yaml` | packs span tables, so the store is top-level, not under one table |

`<MetricName>` is PascalCase (matches the DAX measure-naming convention in
`docs/conventions.md`), so a measure and its contract share a name. A contract name
MUST be unique within the store -- a duplicate is a defect the review catches. A KPI
pack references its member contracts by name; every referenced name MUST resolve to
an existing contract (a dangling reference is a defect).

This placement is recorded as open question O-1: it is the recommended default, not a
final decision; moving the store later is a path move, not a redesign.

## Lifecycle (draft -> reviewed -> approved), mapped to the four statuses

"draft / reviewed / approved" is lifecycle PROSE; the recorded `status` value is
always one of the four readiness words -- never the word "draft" and never a number:

| Lifecycle phase | Recorded `status` | What it means |
|-----------------|-------------------|---------------|
| draft (authored, not yet reviewed) | `not_started` | a filled contract exists but carries no owner approval yet (the default) |
| blocked on a judgment call | `blocked` | a `blocking_reason` holds (see the stop-and-ask list) -- not approvable until resolved |
| reviewed with a recorded caveat | `warning` | reviewable with a non-fatal recorded issue (e.g. an accepted grain note); never auto-promotes to `pass` |
| approved by the owner | `pass` | owner-approved; REQUIRES an `evidence[]` entry (owner name + approval date) |

## No fake confidence (roadmap rule #9 / readiness-model)

Readiness is recorded with EXACTLY the four explicit statuses
(`not_started` / `blocked` / `warning` / `pass`) plus `evidence[]` and
`blocking_reasons[]`. There is **no numeric score / confidence field** in any
contract, pack, or this store -- and a filled copy must not add one. A reviewer
determines `pass` vs `blocked` from the recorded status + evidence + blockers, never
from a number.

## Owner approval is the evidence for `pass`

A contract reaches `pass` **only** with owner approval recorded as evidence: the
named metric `owner` plus the approval date (`evidence: ["approved by <owner> on
<YYYY-MM-DD>"]`). The agent never self-approves -- it authors and recommends; the
named owner decides (Principle I). A `pass` with no evidence is a defect
(`readiness-model.md`). `blocking_reasons[]` is required whenever status is `blocked`.

A pack's readiness rolls up from its members: a pack is no more ready than its
least-ready contract, and a pack `pass` also needs its own owner approval as evidence.

## Per-contract ambiguity ledger

Each metric contract carries an `ambiguities[]` block recording the human ruling for every
`kpi-ambiguities.md` item that bears on it. **Purpose:** force each number-affecting ambiguity
to a *recorded* ruling so an undecided one cannot silently ride into a `pass`.

**Keying (A1..A11 -- the full range, not "A1..A10").** Each entry's `id` is one of A1 VAT,
A2 returns, A3 date, A4 gross/net, A5 discount line/header, A6 cost method, A7 cancelled/void,
A8 product key, A9 branch key, **A10 inventory snapshot, A11 same-store** -- the last two are
the range correction (the idea title's "A1-A10" would have dropped A11 same-store).

**Lifecycle:** applicable -> `decision_status: undecided` (a number-moving one forces the
contract `blocked` with a matching `blocking_reason`) -> the named owner rules ->
`decision_status: decided` with `ruling` + `evidence` (who + date). **Applicability by
omission:** an ambiguity that does not bear on a contract is simply absent from its
`ambiguities[]` -- omission means not-applicable, never "silently resolved".

**Non-pass blocker rule (FR-013 fail-safe):** an ambiguity with `number_moving: true` and
`decision_status: undecided` records a `blocking_reason` and forces `readiness.status:
blocked`. A named owner may record `number_moving: false` to make it non-blocking, but ONLY
with a non-empty `evidence[]` recording who downgraded it and when -- the downgrade is itself
a human ruling carrying the same attribution bar as a `decided` ruling, so the agent can never
silently clear a blocker by flipping the boolean. The agent never sets `number_moving: false`
and never invents a ruling to clear an entry. **No fake confidence (rule #9):**
`decision_status` is exactly `decided | undecided` -- no third word, no numeric
confidence/certainty field.

**Motivating example (generic):** the DiscountedTransactionRate denominator ruling
(all-transactions vs known-status-only) is a number-moving A7/A4 ambiguity -- undecided, it
blocks; ruled, it records the chosen denominator + owner + date. A real *filled* instance lives
in `../worked-examples/c086-pharmacy.md`; it is cited, never inlined here (Principle VII).

**Define/check boundary (verbatim, this feature respects it).** DEFINING a contract writes
INTENT + binding + this ambiguity ruling; it never authors DAX, never touches a `powerbi/`
model, and **adds no `retail check` rule**. The enforcing CHECK half (the AL1 static rule) is a
SEPARATE, deferred idea and is **not** implemented here -- until it ships, the non-pass blocker
is a docs convention the reviewer honors, not a gate exit code.

**Pack rollup (no new logic).** A contract blocked by an undecided number-moving ambiguity
propagates to its packs through the EXISTING rollup rule above ("a pack is no more ready than
its least-ready contract") -- this feature adds NO new rollup logic; it relies on what the store
already states.

## Principle-V stop-and-ask triggers

These are HUMAN judgment calls. The agent RECOMMENDS; the named owner DECIDES. When
any holds, record it as a `blocking_reason` and set `status: blocked` -- NEVER invent
the answer to fill the field (this list is stated verbatim in the contract template):

1. **Business rollup / segment mapping not analyst-supplied** (e.g. how raw
   categories roll into a reporting segment) -- record "rollup mapping not
   analyst-supplied" and STOP.
2. **Grain ambiguity**, or a metric defined at a grain FINER than the bound fact
   provides -- state the grain in the contract's `grain` field, record the conflict,
   and STOP for human review (do not auto-resolve).
3. **PII publish-safety** (a PII-derived bound column) -- set
   `binds_to.pii_sensitive: true`, record the deferral, and STOP for governance
   sign-off; never auto-approve a PII metric.

## Edge cases the review must catch

- **No clean `gold` column to bind to** -- the contract STOPS with a blocking reason
  ("no bound gold column"); it is not approvable until gold provides the column
  (Semantic Model Ready is downstream of Gold Ready).
- **A contract binding to `silver`/`bronze`** -- a defect; `binds_to` is gold-only
  (Principle III / FR-012).
- **A DAX expression, SQL, or a visual/page spec in any field** -- rejected; the
  contract is INTENT + binding, not implementation and not a check.
- **Duplicate contract name** within the store, or a **dangling pack reference** to a
  name that does not exist -- defects the review must catch.

## How the Semantic Model Ready stage reads contracts

Stage 5 (`docs/readiness/semantic-model-ready.md`) reads these contracts to confirm
that each governed PBIP measure traces to an APPROVED contract. That stage performs
the CHECK (it is F010 / on-disk 011); this store performs the DEFINE. A measure with
no corresponding `pass` contract is a Stage-5 blocker; an unapproved-but-present
contract is not yet a valid binding target. This guide changes none of Stage 5's
gates -- it only supplies the artifact Stage 5 was waiting for.

## What the agent must NOT do

- Do NOT self-approve a contract -- the highest the agent records is `warning`;
  `pass` needs the owner's approval as evidence (owner + date).
- Do NOT invent a business rollup, resolve a grain conflict, or auto-approve a PII
  metric -- each is a `blocking_reason` for the named owner (Principle V).
- Do NOT put DAX, SQL, a visual spec, or a `powerbi/` path in a contract -- it is
  INTENT + binding, not implementation.
- Do NOT emit a numeric confidence / score -- use the four statuses + evidence +
  blockers (rule #9).
- Do NOT read or check a PBIP model from this layer -- that is F010 / on-disk 011.
- Do NOT bind to `silver`/`bronze` -- `binds_to` is gold-only (Principle III).

## See also

- The atomic template: `../../templates/metric-contract.yaml`
- The pack template + example: `../../templates/kpi-pack.yaml`
- The generic KPI menu to copy from: `retail-kpi-catalog.md`
- The stage that reads contracts: `../readiness/semantic-model-ready.md`
- Status + evidence + blockers vocabulary: `../readiness/readiness-model.md`
- The four-status template idiom: `../../templates/readiness-status.yaml`
- Roadmap hard rules 5/7/8/9 + the F009/F010 split: `../roadmap/roadmap.md`
- C086 as the filled-instance reference (not the schema): `../worked-examples/c086-pharmacy.md`
