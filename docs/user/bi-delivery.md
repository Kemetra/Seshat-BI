# BI delivery — user guide (roadmap M10)

> **Delivery under Option B (skill-driven).** A user-facing walkthrough of the
> *already-shipped* dashboard-design skills and PBIR authoring adapters — no new CLI
> verb, no new capability. The interface stays agent + skills (hard rule #1). Decision:
> `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md`.

## What BI delivery is

The last leg of the readiness spine: designing the Power BI report against approved metric
contracts, applying formatting to the PBIR, and preparing the handoff — with
publish/execution deliberately kept **out of scope and gated**.

## The skills and adapters (already shipped)

- **`dashboard-design` / `powerbi-dashboard-design`** — design the report against the
  approved metric contracts (blueprints, visual specs, layout). Design happens only after
  metric contracts exist (`no_dashboard_before_metric_contracts`).
- **`pbip-workflow`** — the PBIP project conventions (plain-text TMDL/PBIR, preview
  feature, short paths).
- **Existing PBIP adoption** — run `seshat adopt-pbip assess --project <path>` before
  treating an existing report as governed. It is read-only and returns one next action;
  the explicitly accepted scaffold writes only the adoption fingerprint baseline. See
  [PBIP adoption](../tools/pbip-adoption.md).
- **The PBIR authoring adapters (all shipped, run via `retail`/`seshat`):**
  `pbir-apply-theme`, `pbir-format-visual`, `pbir-set-page-background`,
  `pbir-set-geometry` — deterministic, local-file, reviewable writers that apply
  formatting/layout to committed PBIR JSON. They style and lay out **existing, bound**
  visuals; they never create/retype a visual or grant a stage pass.

## The flow

You drive this by talking to the agent:

1. **Design against contracts** — use `dashboard-design` once the metric contracts for the
   page are approved. The report references its model by a relative path (rule R1).
2. **Apply formatting** — use the `pbir-*` adapters to apply the generated theme, per-visual
   formatting, page background, and geometry to the committed PBIR. Every write is a
   reviewable git diff; re-runs are byte-identical.
3. **Prepare the handoff** — assemble the handoff/evidence pack (roadmap M9,
   `docs/user/evidence-pack.md`) for the owner's review.

## The honesty guard (carried from the F034 work)

These adapters write the **formatting mechanism**. They do NOT automatically produce
"great creative dashboards" — design quality is a human render + `screenshot-review`
judgment, explicitly not claimed by the tool. The guide never conflates the mechanism with
that outcome.

## Hard stops (the guide never suggests bypassing these)

- **`no_dashboard_before_metric_contracts`** — no report design before the metric
  contracts are approved.
- **Publish/execution stays gated** — F016 (the Power BI execution adapter) is parked;
  publishing requires Semantic Model Ready = `pass` and a named-human approval (hard rule
  #6, execution-only, last). This guide never suggests publishing early.
- **Principle V / no fabricated score** — the adapters record evidence of a formatting
  write; they never move a stage to `pass` or emit a health/maturity number.

## Next

An owner-approved, rendered-and-reviewed report proceeds toward Publish Ready — the final,
gated stage. See the [readiness model](../readiness/readiness-model.md) and the
[medallion playbook](../medallion-playbook.md).
