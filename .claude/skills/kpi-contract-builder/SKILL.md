---
name: kpi-contract-builder
description: >-
  Help a human turn a named-but-planned retail KPI into a governed, owner-ready
  project metric-contract by driving the shipped kpi_contracts engine (spec 124).
  On first contact, when no approved decisions exist yet, it assesses source
  answerability, lists the exact Decision Store decisions to get approved via
  business-knowledge-interview, and renders a preview with per-field provenance
  -- writing no YAML. Once the approved kpi_definition / policy_ruling decisions,
  a named eligible owner, and committed source evidence exist, it drives
  draft_project_metric_contract (a gold-blocked contract) and, after the gold
  binding is materialized, finalize_project_metric_contract. Use when someone
  asks to draft, author, or start a metric contract for a planned KPI in the
  Seshat BI repo. It never invents business meaning, DAX, SQL, gold columns,
  approvals, owners, a confidence score, or a registry entry; it never promotes
  a KPI to Seeded and never self-grants an approval.
---

# kpi-contract-builder

This skill is the agent-facing front door to the shipped `kpi_contracts` stage.
It does NOT reimplement contract authoring: the engine
(`src/seshat/kpi_contracts.py`) and the answerability scorecard
(`src/seshat/kpi_answerability.py`) already exist (spec 124). This skill DRIVES
them and adds the first-contact assessment the engine deliberately refuses to do.

## When to use

- Someone asks to draft / author / start a metric contract for a KPI that the
  registry marks `planned` (no seeded contract yet), or for a user-supplied
  custom KPI.
- You are at the `kpi_contracts` flow stage (downstream of
  `business-knowledge-interview`, upstream of silver/gold model planning).

Do NOT use it to define DAX (`retail generate`), to check a PBIP model
(`retail semantic-check`), or to run the interview itself
(`business-knowledge-interview`).

## The two-trip flow

The shipped `draft_project_metric_contract` REQUIRES an approved decision, a named
owner, and committed source evidence; without them it raises
`ContractDraftRefused`. So the flow has two trips.

### Trip 1 -- Assess & preview (the common first-contact case; writes nothing)

1. Identify the KPI. Registry-known -> resolve its `generic_kpi_ref: KPI-MC-NN`
   from `skills/retail-kpi-knowledge/registry.yaml` (`custom: false`).
   User-supplied -> `custom: true`, no ref, no suggested id.
2. Read the source-coverage signal (read-only). NOTE: for a `lifecycle: planned`
   registry entry -- the primary case for this skill -- `derive_answerability`
   short-circuits to `Planned` before it inspects source roles, mapped concepts,
   domain, or evidence, so its status alone CANNOT tell you which fields are
   present. For a planned KPI, take the coverage signal from the registry entry's
   own `blockers` and `source_roles` / `required_concepts` metadata (and a
   committed source profile / source-map, if present) -- that is what surfaces a
   `binds_to` gap. Use `derive_answerability` /
   `render_answerability_artifact` only for its designed purpose (a coverage
   scorecard for SEEDED KPIs); consume it read-only, never persist or re-decide it
   -- contract authoring is a separate concern.
3. Check the Decision Store for the required `kpi_definition` + applicable
   `policy_ruling` decisions. If any is missing/unapproved, do NOT call the
   engine (it will raise).
4. Render a PREVIEW: the contract's business body (clean; no provenance inside
   values) + a `field_provenance` block + the gap list.
5. Emit the decision-gap list: the exact `kpi_definition` / `policy_ruling`
   decisions to get approved (route to `business-knowledge-interview`) and the
   owner to name. STOP. Write no YAML.

### Trip 2 -- Draft & finalize (only when preconditions hold)

6. When an approved `kpi_definition` (+ every applicable approved `policy_ruling`)
   and a named eligible owner exist, build a `ContractDraftRequest` and call
   `draft_project_metric_contract`. The result is a contract with
   `readiness.status: blocked` and the reason `physical gold binding is not
   materialized` -- this is correct and expected until gold exists.
7. On explicit human confirmation, write the returned contract to
   `mappings/<table>/metrics/<Name>.yaml`.
8. After the gold binding is materialized and validated, call
   `finalize_project_metric_contract` with a `FinalizationContext`; it promotes
   to `readiness.status: pass` ONLY when every precondition (binding, decisions,
   fresh evidence, named-human approval) holds. The skill never sets `pass`
   itself.

## field_provenance (preview only; five-value origin vocabulary)

Rendered by this skill in the PREVIEW to show where each field came from. It is
NOT written into the persisted contract (which uses the engine's `decision_refs`
/ `source_evidence`). It is NEVER inserted inside a business value.

    field_provenance:
      formula_intent: { origin: knowledge,   ref: "KPI-MC-02/net-sales.md", resolved: true }
      binds_to:       { origin: profile,     ref: "source-profile.md#net_amount", resolved: false }
      grain:          { origin: human,       ref: "interview 2026-07-13", resolved: true }
      cost_method:    { origin: gap,         ref: "", resolved: false }

Origin is exactly one of: `knowledge` (transcribed from a generic
retail-kpi-knowledge contract), `profile` (proposed from the read-only source
profile -- never self-justifying), `human` (a recorded answer / approved
decision reference), `provisional` (a live unapproved answer shown in preview
only), `gap` (un-inferable). `provisional` and `gap` are never `resolved: true`;
either on a required field means the drafted contract stays `readiness.status:
blocked`.

## Hard stops

- Never self-grant an approval. The `owner` is REQUIRED at draft time
  (`draft_project_metric_contract` refuses an empty owner and persists the one you
  supply) -- so a named eligible owner must be identified before Trip 2; that is a
  human answer, not an agent invention. What the skill never fills is `approvals`
  and never sets `readiness.status: pass` -- promotion to `pass` is the named-human
  step performed by `finalize_project_metric_contract`.
- Never fabricate a confidence score or percentage.
- Never write DAX / SQL / a silver or bronze binding into any field.
- Never mutate `registry.yaml`; never suggest a `KPI-MC` id for a custom KPI;
  never promote a KPI from Planned to Seeded.
- For a `planned` KPI, contribute identity / concepts / roles / blockers only --
  never an invented `formula_intent`.
