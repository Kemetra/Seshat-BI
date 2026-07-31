# kpi-contract-builder -- worked walkthrough

Two end-to-end cases. Both are illustrative and generic (no C086/pharmacy
specifics). Neither writes YAML unless its stated preconditions hold.

## Case A -- registry-known planned KPI (Inventory Turnover)

Context: `skills/retail-kpi-knowledge/domains/inventory.md` marks Inventory
Turnover `Planned (needs COGS + average inventory cost)`; no seeded contract.

Trip 1 (first contact, no approved decisions):
1. Registry lookup: Inventory Turnover -> `generic_kpi_ref: KPI-MC-<NN>`,
   `custom: false`.
2. Source-coverage signal: `derive_answerability` returns `Planned` for this
   `lifecycle: planned` entry (it short-circuits before source checks), so read the
   real gap from the registry entry's `blockers` / `source_roles` instead -- the
   sales-only source has no inventory snapshot fact, so the required
   snapshot/COGS/average-inventory-cost roles are absent.
3. Decision Store: no approved `kpi_definition` for turnover -> engine would
   raise; do not call it.
4. Preview business body (clean):
   - `formula_intent`: transcribed intent from the knowledge layer if present,
     else omitted.
   - `binds_to`: gold snapshot columns are absent -> left unbound.
   - `readiness.status: blocked`.
5. field_provenance (preview only):

       field_provenance:
         formula_intent: { origin: knowledge, ref: "<knowledge-contract-ref>", resolved: true }
         binds_to:       { origin: gap,       ref: "", resolved: false }   # no gold snapshot
         cost_method:    { origin: gap,       ref: "", resolved: false }

6. Decision-gap list emitted: "Get approved via business-knowledge-interview: a
   `kpi_definition` for Inventory Turnover and a `policy_ruling` for the cost
   method (A6). Name the metric owner." STOP -- no YAML written.

Trip 2 (later, once the above are approved and a gold inventory snapshot exists):
- Build a `ContractDraftRequest` and call `draft_project_metric_contract`; write
  the returned contract (still `blocked` until the gold binding is materialized)
  to `mappings/<table>/metrics/InventoryTurnover.yaml` on confirmation.
- After the gold binding is validated, `finalize_project_metric_contract`
  promotes to `pass` only if every precondition holds.

## Case B -- custom (user-supplied) KPI

Context: a user names "Shrinkage Adjusted Margin", not in the registry.

Trip 1:
1. `custom: true`, no `generic_kpi_ref`, no suggested id.
2. There is NO citable generic meaning -> every meaning field is `gap`:

       field_provenance:
         formula_intent: { origin: gap, ref: "", resolved: false }
         grain:          { origin: gap, ref: "", resolved: false }

3. Decision-gap list: an approved `kpi_definition` for the custom KPI plus each
   applicable `policy_ruling`; a named eligible owner in `Name (authority_class)`
   form (the engine's `owner_shape_ok` requires it for custom KPIs). Note
   explicitly: promotion of this custom KPI into the product registry is a
   SEPARATE owner workflow -- this skill never does it.
4. STOP -- no YAML written until the decisions + owner + evidence exist.
