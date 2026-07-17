# kpi-contract-builder — Design

**Date:** 2026-07-17
**Status:** Design (approved in brainstorming; not yet a ratified spec)
**Worktree/branch:** `worktree-kpis`
**Idea origin:** `docs/roadmap/idea-backlog.md` — "KPI Contract Elicitation Aid"
(2× ADOPT / 1 CONSIDER; renamed to `kpi-contract-builder`).

---

## 1. Purpose

Close the productive half of the KPI-contract gap. Spec 124
(`generic-kpi-contract-authoring`, shipped via PR #264) built the KPI **registry**
and **answerability** — *which* named KPIs a source can answer. Nothing yet helps a
human *produce* the governed project metric-contract for one. Across 12 domains
there are ~74 named-but-`[planned]` KPIs (e.g. the whole `inventory` domain) with no
contract; `F8`/`SL1` only *measure* that gap.

`kpi-contract-builder` is an agent-first capability that guides a human from a named
KPI to one **draft `metric-contract.yaml`**, transcribing generic meaning where it is
citable, proposing gold bindings from the read-only source profile, opening every
number-moving ambiguity as a blocking ledger entry, and **stopping** wherever a human
judgment or an approved decision is required. A named human remains solely responsible
for meaning, ownership, approval, registration, and lifecycle advancement.

## 2. Scope and locked decisions

Agent-first skill. **No** new CLI verb family, runtime engine, readiness stage, or
`retail check` rule. Produces **one** project metric-contract at a time. Reuses the
shipped template, registry, Decision Store + gate, answerability machinery, A1–A11
ambiguity ledger, and Business Knowledge Interview.

**Never** invents business meaning, DAX, SQL, gold columns, approvals, owners,
confidence scores, or registry entries.

- **Registry-known KPI:** resolve its existing `generic_kpi_ref: KPI-MC-NN`;
  `custom: false`.
- **Custom (user-supplied) KPI:** `custom: true`; no `generic_kpi_ref`; no registry
  mutation and no suggested `KPI-MC-NN` id; promotion into the product registry is a
  separate owner workflow (124 D5).
- A **persisted** contract requires the approved `kpi_definition`, all applicable
  approved `policy_ruling` / governance decisions, and a named eligible owner. Before
  those exist, the builder previews and lists the needed decisions only — it writes no
  YAML.
- Valid `readiness.status` is exactly `not_started | blocked | warning | pass`. There
  is **no `draft` status.** A pre-approval contract is `not_started`, or `blocked` if a
  required field is unresolved.
- Missing gold evidence ⇒ `readiness.status: blocked`. Source-profile evidence alone
  can propose but **cannot justify** `binds_to`.
- Planned KPIs may contribute identity, concepts, roles, and blockers — never an
  invented `formula_intent`.
- Provenance is structured **per field** in a separate additive block and **must not**
  be written into any business value.

## 3. Boundaries (does / never does)

| Does | Never does |
|------|-----------|
| Transcribes generic KPI *meaning* verbatim from `retail-kpi-knowledge` (registry-known KPI) | Invents `formula_intent`; writes DAX/SQL into it |
| Proposes `binds_to` gold columns from the read-only source profile | Binds to silver/bronze; fabricates a column absent from the profile; treats a profile-proposed binding as justified |
| Opens each applicable A1–A11 number-moving ambiguity as a `blocked` ledger entry | Auto-resolves a number-moving ambiguity |
| Emits `readiness.status: blocked` (materialization blocker), a required named `owner`, empty `approvals` | Sets `readiness: pass`; fills `approvals`; promotes Planned→Seeded |
| Reads `registry.yaml` to cite `generic_kpi_ref` (registry-known only) | Writes to `registry.yaml`; suggests an id for a custom KPI |
| Records per-field origin in a separate `field_provenance` block | Emits any numeric confidence score; inlines provenance into a business value |

All four kit `hard_stops` are honored: `never_self_grant_approval`,
`no_dashboard_before_metric_contracts`, `never_fabricate_a_confidence_score`, and the
gold-only/no-silver posture.

> **Correction (2026-07-17, post-grounding).** Spec 124 already shipped the runtime
> engine this design assumed was unbuilt: `src/seshat/kpi_contracts.py` provides
> `draft_project_metric_contract()` (Checkpoint A) and `finalize_project_metric_contract()`
> (Checkpoint B), plus `kpi_answerability.py` and a documented quickstart. Consequences
> for this design: (1) the shipped `draft_project_metric_contract` **already requires**
> approved decisions + a named owner + committed evidence and **raises
> `ContractDraftRefused`** without them — so it is the **Trip 2** engine call, NOT Trip 1;
> (2) **Trip 1** (the common first-contact case with no approved decisions) has no engine
> support by design and is the skill's genuine unbuilt job — assess, list the exact
> decisions to get approved, preview; (3) `finalize_project_metric_contract` is the
> gold-materialized promotion to `pass`. This capability therefore builds an **agent skill
> that drives the shipped engine**, not a new runtime module. `field_provenance` (§6) is
> **skill-composed in the preview only**; the persisted contract keeps 124's existing
> `decision_refs` / `source_evidence`, and the tested `kpi_contracts.py` runtime is not
> modified.

## 4. Workflow (two-trip) — driving the shipped engine

The builder runs the same **assess → compose-preview** sequence every time; whether it
can *write* depends solely on the shipped engine's precondition (approved decisions +
named owner + committed evidence), enforced by `draft_project_metric_contract` reusing
the Decision Store approval predicate (fail-closed: any `open`/missing decision ⇒
`ContractDraftRefused`).

**Trip 1 — Assess & Preview (the default; no write):**

1. **Identify the KPI.** Registry-known ⇒ resolve `generic_kpi_ref: KPI-MC-NN`,
   `custom: false`. User-supplied ⇒ `custom: true`, no ref, no suggested id.
2. **Consume answerability** (read-only precondition): invoke the existing
   `kpi_answerability` machinery for this (KPI, table); its coverage status is an
   *input signal only* (e.g. `Blocked — missing field` ⇒ a `binds_to` gap). Nothing is
   persisted or re-adjudicated — contract authoring is explicitly outside that module.
3. **Query the Decision Store gate** for the required `kpi_definition` + applicable
   `policy_ruling` decisions.
4. **Compose a preview** of the full contract: a clean business body + the
   `field_provenance` map + the escalation/gap list.
5. **Emit the decision-gap list** — the exact Decision Store records to get approved
   (routed to `business-knowledge-interview`) and the owner to name. **No YAML written.**
   Live conversational answers may appear in the preview clearly marked
   `provisional`/unapproved; they are never written until they are approved records.

**Trip 2 — Confirm & Write (only when the gate returns `ok` AND a named eligible owner
exists):**

6. Re-assess; re-render the now-writable contract.
7. Human confirms ⇒ write **one** `metric-contract.yaml` to
   `mappings/<table>/metrics/<Name>.yaml`.
8. The shipped `draft_project_metric_contract` returns `readiness.status: blocked`
   with the reason `physical gold binding is not materialized` (it never binds gold
   at draft time), so a freshly-drafted contract is always `blocked` until gold is
   materialized and `finalize_project_metric_contract` promotes it. The draft
   carries a REQUIRED named `owner` (the engine refuses an empty one and persists
   it) — that owner is a human answer identified before Trip 2, not an agent
   invention. What the builder never does is fill `approvals` or set
   `readiness.status: pass` itself; `pass` is the named-human promotion step in
   `finalize_project_metric_contract`. (An entirely pre-decision preview that is
   never drafted is conceptually `not_started`, but the engine never emits that
   status.)

## 5. Field-by-field composition

Each field is filled from exactly one origin, recorded in the separate
`field_provenance` map — never inline in the business value.

| Contract field | Registry-known KPI | Custom KPI |
|---|---|---|
| `name`, `grain`, required concepts | transcribed from the knowledge contract (`origin: knowledge`) | from a human answer (`origin: human`), else `gap` |
| `formula_intent` | transcribed **verbatim-or-gapped** from the knowledge contract's plain-language formula (`origin: knowledge`) | `gap` by default (no citable meaning); `provisional` only if the human supplies an unapproved answer in-session |
| `binds_to.gold_table` / `columns` | proposed from source profile (`origin: profile`, `resolved: false` until gold) | same |
| `generic_kpi_ref` | `KPI-MC-NN` | omitted (`custom: true`) |
| `ambiguities[]` (A1–A11) | each applicable number-moving item ⇒ `blocked` entry | same |
| `readiness.status` | `not_started`, or `blocked` if any required field unresolved | same |
| `owner` | REQUIRED named owner (human answer; engine refuses empty) | same |
| `approvals`, `readiness: pass` | never filled by the builder (named-human step via `finalize`) | same |

### The gap rule (unresolved field without invalid YAML)

An unresolved **required** field is omitted or placeholder in the body; its gap is
recorded as `field_provenance.<field> = {origin: gap, ref: "", resolved: false}` plus a
matching `readiness.blocking_reason`. A `[GAP]` string never appears inside a business
value — the gap is recorded structurally, so the YAML stays valid and the value stays
clean.

## 6. `field_provenance` — the new additive block

New, additive, top-level. Distinct from 124's **contract-level** provenance
(`generic_kpi_ref` / `custom` / `decision_refs` / `source_evidence`), which stays as-is;
this adds **per-field** origin. A contract without `field_provenance` remains valid
(additive posture).

```yaml
field_provenance:
  formula_intent: { origin: knowledge,   ref: "KPI-MC-02/net-sales.md", resolved: true }
  binds_to:       { origin: profile,     ref: "source-profile.md#net_amount", resolved: false }  # pending gold
  grain:          { origin: human,       ref: "interview 2026-07-17", resolved: true }
  cost_method:    { origin: gap,         ref: "", resolved: false }   # -> readiness blocking_reason
# origin vocabulary (fixed, five values):
#   knowledge   transcribed from a generic retail-kpi-knowledge contract
#   profile     proposed from the read-only source profile (never self-justifying)
#   human       a recorded human answer / approved decision reference
#   provisional a live unapproved answer shown in preview only
#   gap         un-inferable; forces resolved:false + a readiness blocking_reason
```

`resolved: false` on any required field forces `readiness.status: blocked` with a
matching `blocking_reason`. `provisional` and `gap` are never `resolved: true`.

## 7. Packaging (matches the sibling flow-skill convention)

> **Corrected 2026-07-17 (post-implementation).** The original §7 called for a
> `distribution/public-command-surface.yaml` entry. That was wrong and is removed: the
> public command surface is a curated list of umbrella/workflow commands (help, init,
> check, review, dbt/powerbi/dagster families), and the CI-enforced contract test
> `tests/contract/test_public_command_surface.py` rejects an individual medallion
> flow-stage skill there. The two sibling flow-skills this design modeled itself on —
> `business-knowledge-interview` and `source-mapping` — are NOT surface commands; they
> ship purely as repo `.claude/skills/` dirs surfaced through the kit-source verb router.

`kpi-contract-builder` ships exactly like its siblings:

- The skill body + walkthrough live under `.claude/skills/kpi-contract-builder/`
  (matching `business-knowledge-interview` and `source-mapping`).
- A `verbs[]` entry in `.seshat/kit-source.yaml` registers it; the projection
  (single fenced `SESHAT-KIT` region in `AGENTS.md`/`CLAUDE.md` + `.seshat/compass.yaml`)
  surfaces it to the agent. `kit-lint` fails loud on projection drift.
- The `seshat` **wheel** (`pyproject.toml` ships `src/seshat` + `src/retail`) carries the
  already-shipped `kpi_contracts.py` engine this skill drives — the Python "package
  upgrade." Individual flow-skills are not wheel or `.claude-plugin` marketplace-bundle
  members (neither are the siblings); there is no per-skill surface or bundle entry to add.

## 8. Reuse (rebuilds nothing)

| Reused | Role here |
|--------|-----------|
| `templates/metric-contract.yaml` | the authoring target |
| `src/seshat/kpi_answerability.py` | read-only coverage input (consumed, never generated) |
| `src/seshat/decision_gate.py` + `decision_store.py` | the write gate; `kpi_definition` / `policy_ruling` decision types |
| `skills/retail-kpi-knowledge/registry.yaml` | read-only; cite `generic_kpi_ref` |
| A1–A11 ambiguity catalogue (`kpi-ambiguities.md`) | the number-moving decisions opened as blockers |
| `src/seshat/source_profile_reader.py` + `profile.py` | the read-only source profile for `binds_to` candidates |
| `.claude/skills/business-knowledge-interview/` | upstream producer of the approved decisions this builder consumes |

## 9. Testing posture (docs-first — hard rule #8)

The MVP ships the skill prose, the `field_provenance` shape spec, and a worked
walkthrough with two cases: one registry-known KPI (e.g. an `inventory` KPI reaching
`blocked` on a missing gold snapshot) and one custom KPI (all meaning fields `gap`).
Any **static enforcement** of the `field_provenance` structure is a deferred later slice
— mirroring how 124 shipped the fixtures' specification rather than the fixture code.

## 10. Explicitly out of scope (MVP)

- Batch drafting across a whole domain (deferred until the single-KPI flow is proven).
- Any registry mutation or KPI-id suggestion for a custom KPI.
- A `retail check` rule enforcing `field_provenance` (deferred slice).
- Producing or re-adjudicating the answerability artifact.
- Writing DAX / the `definition` block (that is `retail generate`'s concern).
- Promoting a KPI from Planned to Seeded (a named-human lifecycle action).
