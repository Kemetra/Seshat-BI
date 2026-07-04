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
| **B1** | `AP1` visual-qa↔dashboard-qa parity rule (`rule_ap1.py`) | #181 (+#183 fix) | ratified 085; two format-specific extractors, fail-closed on count/number→name/name divergence; registry → 54 |
| **I3** | `SF1` cross-layer checklist fork detector (`rule_sf1.py`) | #182 | ratified 086; reconciles `skills/**/checklists/*.md` against the owner-authored `docs/quality/shared-spine.yaml` fork contract; registry → 55 |

## RECOMMENDED — owner decision (recorded, not auto-built)

_Empty after the 2026-07-04 build wave. B1 and I3 — the last two genuinely-open
design ideas — were spec'd, ratified (owner: Ahmed Shaaban, 2026-07-04), and
shipped (#181/#183, #182); see the "SHIPPED since" table above. No design-category
idea remains in an owner-decision-pending state. **When this section disagrees
with git, git wins.**_

## BLOCKED — inert until content lands (no live target)

`A4 / A5 / A9 / A11` need filled visual-specs or `visual.json` (the #144 pure-kit
extraction removed the c086 corpus). `H6 / H7 / H8 / H9 / H10 / H11` need KPI /
time-intelligence contracts to land first. `E3` needs `B1`/`B3` module-selection
made introspectable. `K1` needs a third gate's emission format to stabilize.

## HELD — gap #6 (accessibility self-assertion) — TEMPLATE FIXED, rule held

_Design/business gap #6 from the 2026-07-04 gap analysis: a theme could
self-assert an accessibility pass (§8 "all confirmed") that nothing verified —
the same self-asserted-but-unchecked inconsistency the kit exists to prevent
(hard rule #9 spirit)._

**Done now (DEFINE-layer fix, has teeth immediately):** `templates/theme-json-spec.md`
§8 + Readiness rewritten so a bare checklist tick is **not** confirmation. Each
check names its evidence: **contrast → cite `CT1`'s computed verdict** (delegated,
not self-reported); **CVD / small-size legibility / saturated-background → a named
reviewer + date** (Principle-V human judgment / F016-rendered, not machine-ruled).
This closes the hole where it lives: `theme-json-spec.md` §8 is the only surface
carrying a bare "all confirmed" accessibility *checklist* (the shape that let a
tick stand in for evidence). Sibling surfaces like `screenshot-review.md` §5 are
findings-log tables, a different shape, out of scope here.

**Held (rule, owner decision to fire):** an evidence-gate rule — a filled theme
spec may not reach `pass` on a bare §8 tick (contrast must cite CT1; judgment
items must carry a named reviewer). **Shape: evidence-gate / anti-self-assertion
(DL4-like), NOT an accessibility computation** — CT1 is the only accessibility
dimension the kit computes *today* (WCAG text/background contrast on committed
token hexes). CVD-distinguishability and saturation are arithmetically computable
too (a future owner could add a CT2-style rule), but the kit does not compute them
now and this doc does not foreclose that choice; the small-size/adjacency check is
render-dependent (F016). Absent a computed check, all three route to a named
reviewer — the kit does not rule on them itself (Principle V). **Not auto-built:**
post-#144 there is **no filled theme-spec instance** in tracked files, so the rule
would fire on an empty set (BLOCKED — no live target). It ships when (a) a filled
theme spec lands to check, and (b) the owner fires the spec (per the
ask-before-firing rule). **Discriminator: no *filled* theme-spec instance (one
carrying real token hexes + a `Status:`/reviewer, not the template's placeholders)
exists outside `templates/` today.**

## HELD — gap #8 (i18n / RTL) — NO BUILD, layout is already direction-neutral

_Design/business gap #8 from the 2026-07-04 gap analysis: does the design layer
handle right-to-left (Arabic) presentation? Investigated 2026-07-04; the honest
answer is **no active hole, no live target — hold, do not build.**_

**What the investigation found (grounded):**
- **No hardcoded LTR commitment.** The discriminating grep for spatial direction
  (`placement: left|right`, horizontal `order:`, `align: left|right`) across
  `templates/`, `reports/`, `docs/powerbi/` returns **nothing**. The only
  `placement:` values are semantic (`fact_measure`, `dropped`, `degenerate_dim`),
  and the grid is a **row-band model with no column/side concept** — a
  `filter_rail` is `placement: side`, not `left`. Section "reading order" is
  **top-to-bottom (vertical)**, which is direction-neutral. The layout primitives
  are already largely RTL-safe by construction.
- **No active integrity hole** (unlike gap #6): nothing lets an author assert a
  false i18n claim. Absence of a `direction` field is a missing *feature*, not a
  self-assertion hole.
- **No live target + unverified scope.** Nothing in the tree exercises
  Arabic-*language* display. The kit's established model is **English display over
  Arabic *source* data** — `retail-term-dictionary` maps Arabic source → canonical
  English meaning, and the shipped worked example is deliberately English-only
  ("no Arabic↔English mapping needed"). RTL is a display concern for
  Arabic-language dashboards, which no committed artifact needs today.

**Held (owner-fired, only if RTL display ever comes into scope):** a single
additive **declared-intent** field `direction: ltr | rtl` (default `ltr`) on the
report/page composition — mirroring 088's drill/nav intent (F016 owns the rendered
mirroring/alignment; the kit declares intent only, never authors the mechanics).
**Not built now:** manufacturing a direction field for a use case no committed
artifact exercises is the "manufacture a contract to drain the backlog" move this
doc exists to refuse. **Discriminator: the spatial-direction grep above returns
nothing, and no Arabic-language display artifact exists in the tree.**

> Tier note: gap #6 was the last *governance-integrity* gap (a false-claim hole).
> #7 (delivery formats) and #8 (i18n/RTL) are *feature-coverage* gaps with no live
> target — 6 of 8 gaps addressed; the remaining two are nice-to-haves held for a
> real need, not manufactured now.
