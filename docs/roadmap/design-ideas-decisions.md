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

### A6 — grid-fit: desktop-grid / blueprint inconsistency — RESOLVED (grid fixed)
The desktop `design/grids/16x9-grid.yaml` enumerated only 5 of the 7 committed
section-vocabulary zones (`docs/powerbi/dashboard-blueprints.md` §Section
vocabulary declares seven, incl. `exception-detail` and `filter rail`, and says a
control room "leans on exception-detail"). Three blueprints legitimately use
`exception_detail` / `filter_rail`; the **desktop grid was the incomplete side**
(the mobile grid already had all seven). Ruled a **desktop-grid gap**, not a
blueprint error — the authoritative vocabulary is the tiebreaker.

**Fixed:** both 16x9 profiles now enumerate all seven zones; all four blueprints
resolve. NOTE (needs a human eyeball): the two added zones' geometry is
**authored/illustrative, not vocabulary-derived** — `exception_detail` shares the
diagnostic rows (6-7); `filter_rail` is marked `placement: side` (rows
deliberately omitted, because this grid is a row-band model with no column/side
concept — a side rail is not a row span).

**Ready-to-build follow-up (HELD, not auto-built):** an A6 section-zone-resolution
rule (assert every blueprint `section:` resolves to a zone in its referenced
grid) is now grounded and green-on-main after the reconciliation. HELD pending
(1) a human eyeball on the authored grid-zone geometry above (esp. `filter_rail`),
and (2) a ruling on which grid a section resolves against when a blueprint's
`grid_ref` is absent (`branch-performance.yaml` has no `grid_ref`). Plus the
optional exec-ceiling check (tokens declare exceeding 6 visuals = warning-with-
reason). Not built now: nothing consumes it yet, and it would enforce a state
this session just created before any human review (circular).

## SHIPPED since this section was written (2026-07-04 git reconciliation)

> Four ideas listed below as "owner decision" had in fact **already shipped** in
> the 2026-07-02/03 build wave; this section (and `shipped-ideas.yaml`) lagged
> git. Corrected 2026-07-04 — ledger rows added, verified as ancestors of
> origin/main. **When this section disagrees with git, git wins.**

| Idea | Shipped as | PR | Note |
|------|-----------|----|------|
| **D1** | `DR1` design_routes.py | #158 | scoped: path + stale-phrase (boundary.yaml deferred per owner ruling); registry → 52 |
| **E2** | glossary↔registry bijection test (shrunk) | #161 | verify-only two-thirds; severity-into-`@register` third correctly dropped (ratified 044) |
| **E7** | `retail doctor` (doctor.py) | #160 | read-only repo-wide drift digest (A3 routes_coverage + SC1 status_claims); broader than `scaffold --doctor` |
| **H4** | `templates/kpi-sufficiency-card.md` | #157 | owner ruled *separate template*; present/absent + status, NO numeric score |

## RECOMMENDED — owner decision (recorded, not auto-built)

_Genuinely open after the 2026-07-04 git reconciliation — the only two of the
original six that have no shipping commit._

- **B1** (anti-pattern parity): `visual-qa.md` (### headings) and
  `dashboard-qa.md` (pipe table) each list 13 anti-patterns with **divergent
  wording** ("on a page" vs "on one page"). *Recommendation: make the fuller
  pipe-table (`dashboard-qa.md`, which carries severities) canonical and align
  `visual-qa.md` to it.* Needs owner eyes (edits a human-authored doc) and the
  reviewer flagged the two-extractor approach as fragile.
- **I3** (shared-checklist fork detector): needs an author-authored contract
  manifest (which checklists must stay in lockstep) — owner must author/authorize
  the contract before a rule can enforce it. The `specify` stage must NOT fabricate
  this contract (Principle V).

## BLOCKED — inert until content lands (no live target)

`A4 / A5 / A9 / A11` need filled visual-specs or `visual.json` (the #144 pure-kit
extraction removed the c086 corpus). `H6 / H7 / H8 / H9 / H10 / H11` need KPI /
time-intelligence contracts to land first. `E3` needs `B1`/`B3` module-selection
made introspectable. `K1` needs a third gate's emission format to stabilize.
