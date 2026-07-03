# Design-category idea decisions — 2026-07-03 autonomous wave

> Dispositions for the OPEN design-category ideas after the 2026-07-03 autonomous
> build wave (PRs #146–151, registry 47→51). Five ideas SHIPPED; the rest are
> ruled here. Each ruling is grounded in a committed fact (the discriminator is
> named) so the idea-engine's Memory stage and a human reviewer can trust it.
>
> Method: an idea is autonomously buildable only if (a) its contract is grounded
> in a COMMITTED declaration — not one the agent authors — AND (b) it has a live
> target today. `CONSIDER` is *defined* as "needs a decision or dependency", so
> most fail one test. Manufacturing a governance contract to drain the backlog
> would merge a contract no human agreed to; these are ruled instead.

## SHIPPED (this wave)

| Idea | Rule | PR | Note |
|------|------|----|------|
| A1 | `DL3` token→theme fidelity | #146 | theme dataColors reconciled to tokens (owner ruled tokens canonical); hardened #149 |
| A3 | `CT1` WCAG contrast pre-check | #146 | new `CT` family |
| C1 | `DL4` design-review evidence gate | #146 | verify-slot-only; hardened #149 |
| A7 | `DL5` grid arithmetic-closure | #147 | live 16x9 grid closes |
| D2 | (test) adopt `validate_cards.py` | #148 | test-only, no rule |
| — | severity-posture coverage for DL1–DL5 + CT1 | #151 | regression-lock |

## SETTLED — DECLINED (grounded on a committed fact)

### D3 — Cross-System Palette-Provenance Ledger — DECLINED
A `must_match`/`must_differ` provenance contract across the retail tokens, the
compiled theme, and the `claude-design-system` brand CSS would encode a
cross-system binding the repo **explicitly disclaims**: `design/claude-design-system/README.md`
says verbatim *"Do not blend the Power BI retail seed into the brand palette."*
The sentiment hexes being identical across the two systems is incidental, not a
declared invariant to lock. Within-system token→theme fidelity is already covered
by `DL3`. **Discriminator: the committed "do not blend" note.**

### F2 — COMPASS Fast-Routing Table Generated from routes.yaml — DECLINED
`docs/routing/routes.yaml` carries `id / task / targets / status`; the COMPASS
"Fast routing" table carries a **"Stop / End on"** column with no equivalent in
routes.yaml. Generating the table from routes.yaml would **delete** that
hand-authored semantic — it degrades the doc rather than drift-proofing it.
**Discriminator: the missing "Stop / End on" column.**

### F3 — Shipped-Ledger Reconciler (strict bijection) — DECLINED
The backlog appendix self-labels **"## SHIPPED / SETTLED (prior ideas, for the
record)"** — a frozen historical snapshot by design. The `shipped-ideas.yaml`
ledger has since grown 11 keys past it; strict backlog↔ledger bijection is the
wrong model (it would demand authoring 11 historical appendix entries).
**Discriminator: "for the record".** Optional no-rule follow-up: add a one-line
"not maintained in lockstep with shipped-ideas.yaml" note to the appendix so the
intent is explicit.

## LATENT BUG SURFACED (owner action — worth more than the rule)

### A6 — grid-fit: a real desktop-grid / blueprint inconsistency
The desktop `design/grids/16x9-grid.yaml` enumerates zones
`header / kpi_strip / main_insight / diagnostic / footer_status`, but three
committed blueprints (`branch-performance.yaml`, `data-quality-control-room.yaml`,
`product-mix.yaml`) place sections in `exception_detail` / `filter_rail` — which
exist only as **mobile-grid** bands. Either the desktop grid should enumerate
those zones, or the blueprints are mis-placing sections. **Owner ruling needed:
desktop-grid gap or blueprint error?** (Once ruled, a section-zone-resolution
rule + the exec-ceiling check — tokens declare exceeding 6 visuals = a
warning-with-reason — become grounded and buildable.)

## RECOMMENDED — owner decision (recorded, not auto-built)

- **B1** (anti-pattern parity): `visual-qa.md` (### headings) and
  `dashboard-qa.md` (pipe table) each list 13 anti-patterns with **divergent
  wording** ("on a page" vs "on one page"). *Recommendation: make the fuller
  pipe-table (`dashboard-qa.md`, which carries severities) canonical and align
  `visual-qa.md` to it.* Needs owner eyes (edits a human-authored doc) and the
  reviewer flagged the two-extractor approach as fragile.
- **E2** (wiring-truth single-source): guard-vs-generate architecture call that
  competes with the shipped `E1` meta-gate. Owner architecture decision.
- **E7** (retail doctor aggregator): overlaps the shipped `scaffold --doctor`;
  needs a distinctness ruling before it earns a build.
- **H4** (contract-sufficiency card): the open F8-packaging ruling (separate
  template vs fold into F8) — unchanged from the prior deferral.
- **D1 / I3** (two-system boundary guard / shared-spine): each needs an
  author-authored contract manifest — owner must author/authorize the contract.

## BLOCKED — inert until content lands (no live target)

`A4 / A5 / A9 / A11` need filled visual-specs or `visual.json` (the #144 pure-kit
extraction removed the c086 corpus). `H6 / H7 / H8 / H9 / H10 / H11` need KPI /
time-intelligence contracts to land first. `E3` needs `B1`/`B3` module-selection
made introspectable. `K1` needs a third gate's emission format to stabilize.
