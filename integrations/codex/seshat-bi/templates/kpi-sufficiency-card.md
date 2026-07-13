# KPI Contract-Sufficiency Card

> **A per-KPI readiness card.** For **one** KPI: does its metric contract carry every
> field needed to build the KPI safely? Records `present | absent` per required field
> and a derived `status` + `blocking_reasons[]`.
>
> **No numeric score.** Sufficiency is a categorical status (`ready` / `blocked`), never
> a percentage or a count-based score (roadmap hard rule #9). A KPI is `ready` only when
> **every** required field is `present`; otherwise `blocked` with one reason per gap.
>
> **Distinct from the coverage scorecard.** The per-*table* coverage scorecard
> (`skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`) asks
> *"which KPIs can this source table support?"*. This card is narrower: *"is this one
> KPI's contract complete enough to build?"*. Use the scorecard to pick KPIs; use this
> card to gate an individual KPI's contract before DAX/SQL handoff.
>
> **Cites, never inlines.** Reference the KPI's filled contract by path; never copy
> client data into this card (Principle IX). Fill one card per KPI you adopt.

```yaml
kpi_id: <kpi id, e.g. net_sales>
contract: <path to the filled contract, e.g. mappings/<table>/metrics/NetSales.yaml>

# Each required field the KPI's contract must carry to be buildable.
# state: present  -> the contract answers it
#        absent   -> the contract leaves it unspecified (a human must supply it)
required_fields:
  - name: grain             # the fact grain the KPI aggregates at
    state: present | absent
  - name: additivity        # additive | semi-additive | non-additive (links AD1)
    state: present | absent
  - name: filter_context    # the filter/rollup context the KPI is valid under
    state: present | absent
  - name: source_binding    # the gold column(s) / expression it binds to
    state: present | absent
  - name: ambiguities       # decided or explicitly-open ambiguity rulings (links AL1/AL2)
    state: present | absent

status: ready | blocked     # ready = every required field present; else blocked
blocking_reasons:           # one line per absent field; empty list when ready
  - <field> unspecified -- <what a named human must supply>

worked_example: skills/retail-kpi-knowledge/contracts/net-sales.md
```

## How to fill it

1. Open the KPI's filled contract (`mappings/<table>/metrics/<Name>.yaml`).
2. For each `required_fields` entry, mark `present` only if the contract genuinely
   answers it — an empty/placeholder value is `absent`.
3. Set `status: ready` iff every field is `present`; otherwise `blocked` and record one
   `blocking_reasons` line per gap.
4. This card **grants no readiness** and **approves nothing** — it reports sufficiency so
   a named human can act. Semantic Model Ready is still decided at its own gate.
