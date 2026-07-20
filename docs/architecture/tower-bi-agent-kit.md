# Tower BI Agent Kit -- Architecture

- **Status:** Draft (Phase 0/1 foundation -- architecture + spec + templates only)
- **Date:** 2026-06-24
- **Repo:** `Seshat_BI` (renamed 2026-06-26 from `Retail_Tower_analytics`; this Phase-0 doc preserves the original name in its historical body below)
- **Scope of this document:** name the product, place the pieces that **already
  exist**, and add the one new load-bearing idea (a source-mapping gate). It defines
  **no new code, no new tables, no validators.** Those are later slices.

> **This is a map of what exists plus a thin new layer -- not a parallel design.**
> Every box below traces to a committed artifact or a settled decision. Where a box is
> new (the source-mapping gate, the agent surface), it is marked **[NEW]** or
> **[FORMALIZED]** and reconciled with the existing method explicitly, so nothing is
> silently re-decided or forked.

---

## 1. What this is (one line)

> The **Tower BI Agent Kit** is an **agent-first** way to turn a raw retail source
> table into a governed Power BI semantic model -- *source -> mapping -> silver -> gold ->
> Power BI* -- where an **AI agent drives** the workflow, **enforced checks gate** every
> step, and **`pbi-cli` is a later adapter** at the very bottom, not the core.

The kit is the product. The agent is the interface. The governance checker is the gate.
The medallion warehouse is the substrate. `pbi-cli` is one pluggable engine the agent
*may* call when it reaches the Power BI semantic-model step -- it is not the center of
gravity.

## 2. Design corrections (the North-Star constraints)

These are the explicit corrections this architecture honors. They are constraints, not
open questions:

| # | Correction | Where it lives in this architecture |
|---|------------|-------------------------------------|
| 1 | **Agent-first, not terminal-first.** | Layer **D** is the primary surface (Sec 4). The CLI (`seshat check`) is the gate the agent *calls*, not the product the user *operates*. |
| 2 | **C086 is the first worked example, not the universal schema.** | C086 appears only as a **cited filled instance** (Sec 6). The kit's pattern is general; pharmacy columns/codes are never baked into templates or the constitution. |
| 3 | **Source mapping happens before silver/gold.** | The **[NEW] source-mapping gate** (Sec 5) -- the one genuinely new idea here -- sits between *profile* and *build silver*. Reconciled with the playbook in Sec 5. |
| 4 | **`pbi-cli` is a later Power BI semantic-model adapter, not the core.** | Bottom of the stack (Sec 4, ENGINE row). Depend-not-fork, installed via `pipx`; consistent with the governance spec's decision #1. |
| 5 | **Postgres-first medallion storage.** | The substrate is the DigitalOcean Postgres medallion (`bronze`/`silver`/`gold`). **No DuckDB/Parquet-first ADR in the MVP** -- Power BI Import mode caches columnar at refresh (VertiPaq), so a gold-as-Parquet copy would be a redundant second source of truth. |
| 6 | **Validators are later -- categories only now.** | Sec 7 documents validator *categories* (reusing the static-vs-live taxonomy already written). **No validator logic is written.** |

## 3. The pieces that already exist (do not rebuild)

This kit is mostly **already built**. The job of this document is to *place* these, not
to re-describe or re-decide them:

| Existing artifact | What it is | Role in the kit |
|-------------------|------------|-----------------|
| **`seshat check`** (`src/seshat/`) | The shippable governance core -- stdlib-only, CI-able, parses committed TMDL/PBIR/SQL/git text. No `pbi-cli`, no Desktop, no network. | **The enforced gate (Layer A, static surface).** Already on `main`. |
| **`docs/medallion-playbook.md`** (7 phases) | The interactive cleaning method: connect & profile -> grain-first cleaning decisions -> ruleset -> review gate -> build silver -> build gold -> data dictionary. | **The process the agent runs.** The source-mapping gate (Sec 5) formalizes its early phases. |
| **`docs/decisions/0002-retail-cleaning-defaults.md`** (RC1-RC16) | The reusable cleaning/modeling defaults: grain, PII, types, returns, star schema, contiguous date dim, reconciliation. | **The default rulings** every new table starts from. The constitution ratifies their *spirit* as principles. |
| **A filled worked example** under `docs/worked-examples/` | The first validated medallion table: full ADR-default PASS after live DB validation. | **The first worked example** -- a *filled instance* of every template, cited, never the schema itself. |
| **`docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`** | The A->C->D governance design (depend-not-fork, gold-only, static-now/live-deferred). | **The design of Layer A.** This architecture sits one level up: it adds the agent framing and the source-mapping gate on top. |
| **`pbi-cli`** (PyPI, via `pipx`, unforked) | A maximally-capable but opinion-less Power BI semantic-model tool. | **The later ENGINE adapter** for the Power BI build step -- not the core. |

> **Naming note (disambiguated -- feature 002):** ADR 0002 numbers its cleaning defaults
> **RC1-RC16** ("retail cleaning"); the governance checker numbers its TMDL/DAX rules
> **D1-D8**. Distinct prefixes, distinct namespaces -- no collision. (Historically the ADR
> also used `D`; it was renamed to `RC*` because the checker ids live in code; see the
> owning ADR and constitution v1.2.0.)

## 4. The stack (D -> C -> A -> ENGINE -> substrate)

The kit reads top-down as *experience -> automation -> gate -> engine -> data*. Layer A
is the foundation that already ships; D is the new primary surface this kit is named for.

```
  D  AGENT EXPERIENCE        "Map and model the C091 sales table for Power BI."   <- PRIMARY SURFACE
     (agent-first)           An agent runs the playbook conversationally:            [DESIGNED -- orchestration
                             profiles the source, proposes a source map,              is a later slice]
                             fills the templates, writes silver/gold SQL,
                             builds the Power BI model, and self-heals
                             against the gate.
                                 | drives, and is gated by
                                 v
  C  AUTOMATION / CI         pre-commit hook + GitHub Action:                      <- UNATTENDED
     (the gate, unattended)  run the STATIC checks on commit/PR, block on            [SEAM -- wired for
                             violation. Exit non-zero is the contract.               seshat check]
                                 | runs
                                 v
  A  GOVERNANCE CORE         +-- STATIC surface --------+-- LIVE surface --------+  <- FOUNDATION
     (the enforced gate --   | seshat check             | retail validate        |    (already on main)
      THE SHIPPED UNIT)      | rules over committed     | wraps a live DB/Desktop |
                             | TMDL / PBIR / SQL / git   | for PK/coverage/recon  |
                             | stdlib-only, CI-able      | [BUILT; live run later] |
                             +-----------+--------------+------------------------+
                                 | the agent (D) authors against, the engine executes
                                 v
  ENGINE                     pbi-cli  (pipx, unforked, upgradeable)               <- LATER ADAPTER
     (pluggable, later)      the agent's Power BI semantic-model authoring engine   [ADAPTER -- not core]
                                 | executes against
                                 v
  SUBSTRATE                  Power BI (PBIP, plain text)  +  DigitalOcean Postgres <- DATA
                             bronze -> silver -> gold  (Power BI reads GOLD only)    (Postgres-first)
```

**Why this ordering is the powerful one** (carried from the governance spec): the gate
is *enforced, not advised* (a non-zero exit beats a paragraph); the layers *compound* (A
is the foundation, C is "run A unattended," D is "drive A conversationally"); and there
is *no fork tax* -- the opinion lives in this repo atop an upgradeable engine.

## 5. The source-mapping gate **[NEW]** -- and how it reconciles with the playbook

This is the **one new load-bearing idea** in this document. State it precisely so it is
*additive*, not a second methodology:

> **Before any `silver.*` SQL is written, the source must be profiled and mapped into
> committed artifacts, and that mapping must be reviewed.** Mapping is a *gate*, not a
> suggestion: silver is downstream of an approved map.

**This does not invent a new method -- it formalizes the playbook's existing early
phases into committed, reviewable artifacts.** The mapping:

| Mapping-gate artifact (template) | Formalizes which playbook phase | What it captures |
|----------------------------------|---------------------------------|------------------|
| `templates/source-profile.md` | **Phase 1** (Connect & profile) | The source's shape, quality, and semantics -- with numbers (row/col counts, missingness as `'' OR NULL`, candidate-key uniqueness, returns population). |
| `templates/source-map.yaml` | **Phase 2.0-2.5 + 2.7-2.8** (grain-first cleaning decisions) | Per-column keep/drop/rename/type, the **grain + PK decided first**, target silver column, and the gold star placement (fact measure / dim attribute / degenerate dim). The machine-readable spine. |
| `templates/assumptions.md` | **Phase 2 + 3** (which ADR defaults were adopted) | The ADR 0002 defaults taken as-is vs the **deviations** (with the triggering data fact), so review sees only what changed. |
| `templates/unresolved-questions.md` | **Phase 2 analyst decision points + Phase 4 review gate** | The open questions that block the build -- the things the agent cannot decide alone. |
| `templates/reconciliation-report.md` | **Phase 5/6 validation gates** (the live acceptance checks) | The blank that the live DB run fills: PK uniqueness, date-dim coverage, 0 orphan FKs, penny-exact cross-layer measure reconciliation. C086 Sec 5 is a filled instance. |

**Where filled copies live:** a table copies these five blanks into **`mappings/<table>/`**
(one folder per table) and fills them -- per [ADR 0003](../decisions/0003-mapping-artifact-location.md).
`templates/` holds the generic blanks; `mappings/<table>/` holds the table's filled set.

**Relationship to the playbook, stated to avoid a silent fork:** the playbook remains
*the method* (the interactive Q&A and the trap-checklists). The mapping gate is the
playbook's **Phase-1->Phase-4 output, elevated into mandatory committed artifacts** that
exist *before* silver SQL. Where they could appear to compete, the playbook is
authoritative on *how to decide*; the templates are authoritative on *what to record and
in what shape*. The playbook's Phase 4 ("Review gate -- before building") **is** the
mapping-gate review.

**Why mapping-before-silver matters (the failure it prevents):** writing silver SQL
first bakes ungoverned grain, type, and PII decisions into a table that gold's FKs then
depend on -- reversing them means rebuilding gold and re-publishing the BI model
(effectively irreversible once cached). The gate forces the load-bearing decisions
(grain, PK, PII, gold placement) to be *committed and reviewed as data* before any
schema is cut.

## 6. C086 as the first worked example (a filled instance, not the schema)

C086 (El Ezaby pharmacy sales) is **the first table to pass through this kit end to
end** -- and therefore the canonical *filled* instance of every artifact above:

- `templates/source-profile.md` -> filled by C086's bronze profile (249,106 raw rows).
- `templates/source-map.yaml` -> filled by C086's grain (`invoice_no + line_no`), column
  decisions, and gold star placement (1 fact + 6 dims).
- `templates/reconciliation-report.md` -> filled by C086 Sec 5: 246,916 silver rows, 0
  orphan FKs, penny-exact reconciliation across five measures.

**C086 is an example, never the universal schema.** Pharmacy-specific facts -- billing
codes `Z4/Z5/Z6/Z8/Z10`, the PHARMA/HVI/NON-PHARMA segment rollup, insurance PII --
belong to C086's own artifacts, **not** to the templates, the constitution, or this
architecture. The *questions and gates* generalize; the *answers* are per-table. See
a filled worked example under `docs/worked-examples/`.

## 7. Validator categories (documented only -- no validator logic)

Validators are a later slice. This kit only **names the categories**, reusing the
static-vs-live taxonomy already established in the worked example (Sec 7/Sec 8) and the
governance spec (Sec 4):

- **STATIC validators** -- checkable from committed text alone, CI-able, the powerful
  core that already exists as `seshat check`. The statically-checkable ADR
  defaults are now wired in (feature 003, after the namespace collision was resolved):
  **S5** enforces RC7 type discipline, **S6** enforces RC14 star-structure (`-1` member),
  **S7** enforces RC15 (`generate_series` date-dim). Each is a SQL-family rule that cites
  its RC default.
- **LIVE validators** -- provable only against a running database; the
  `retail validate` surface (feature 004, **built + fixture-tested**;
  `src/seshat/validate.py`). Checks: **PK uniqueness** on materialized rows (RC2),
  **date-dim coverage** (calendar spans every real date, RC15), **0 orphan FKs**
  (RC16), and **cross-layer measure reconciliation** (silver -> gold, to the penny,
  RC16). They run over a driver-free `QueryRunner` Protocol; the psycopg2 driver is
  an optional extra imported lazily, so the static core stays stdlib-only. Connection
  is host-agnostic (any Postgres via DSN).

The validator **surface is built**; the remaining deferred step is the **live run**
against a real DB (needs the optional `db` extra + credentials). Other engines and
local-file sources are explicitly out of scope (Postgres-first) -- future specs.

## 8. Out of scope for this slice (explicit boundaries)

This Phase 0/1 foundation deliberately stops at architecture + spec + templates:

- **No validator scripts** -- categories documented only (Sec 7).
- **No `pbi-cli` integration** -- placed as the later adapter (Sec 4), not wired.
- **No CLI installer**, no Spec-Kit preset or custom bundle.
  *(Aligned with constitution v1.1.0, 2026-06-24)* Spec-Kit IS now initialized
  (`specify init --here --integration claude --script ps`): `.specify/templates/`,
  `.specify/scripts/powershell/`, and the `speckit-*` skills back the spec -> plan ->
  tasks chain. Presets, custom bundles, and the bring-your-own extensions surface
  beyond the default init remain out of scope.
- **No new warehouse tables**, **no DB writes**, **no moving existing docs.**
- **No implementation beyond architecture/spec/templates.**

## 9. Open decisions (carried to `unresolved-questions`)

1. **D-namespace collision** -- **RESOLVED (feature 002).** ADR cleaning defaults renamed to
   `RC1-RC16`; the checker keeps `D1-D8`. Distinct prefixes, no collision; the prerequisite
   for wiring any ADR default into `seshat check` is now met.
2. **Where the mapping artifacts live per table** -- **RESOLVED (ADR 0003):**
   `mappings/<table>/`, a top-level dir with one folder per table holding the five filled
   artifacts. Keeps `warehouse/` SQL-only and `docs/` narrative-only.
3. **Agent orchestration shape** (Layer D) -- which agent/skill drives the playbook, and
   how it self-heals against the gate. (Designed as a seam; the runtime is a later slice.)
4. **`retail validate` live surface** -- **BUILT (feature 004).** The four checks +
   host-agnostic Postgres connection are implemented and fixture-tested; the **live run**
   against a real DB (+ per-table target sourcing from `source-map.yaml`) is the remaining
   deferred step. Other DB engines and local-file sources are deferred future specs.

## 10. See also

- **Constitution:** `.specify/memory/constitution.md` -- the non-negotiable principles
  this architecture is the engineering expression of.
- **Feature spec:** `specs/001-retail-bi-agent-kit/spec.md` -- the Phase-0/1 slice.
- **Governance design:** `docs/superpowers/specs/2026-06-23-pbi-governance-layer-design.md`.
- **Method:** `docs/medallion-playbook.md`. **Defaults:** `docs/decisions/0002-retail-cleaning-defaults.md`.
- **Worked example:** a filled instance under `docs/worked-examples/`.
- **Templates:** `templates/source-profile.md`, `source-map.yaml`, `assumptions.md`,
  `unresolved-questions.md`, `reconciliation-report.md`.
