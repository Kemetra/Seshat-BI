# Idea Wave 1 (Content) Implementation Plan — I2 + H4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land two content-only idea-bank items with zero rule-registry churn: I2 (a planned bi-python cleaning knowledge file + INDEX status flip) and H4 (a KPI contract-sufficiency card template).

**Architecture:** Both are markdown authoring, no Python. Each registers its "shipped" claim in the SC1 status-claims manifest so the claim cannot silently drift. No new `@register` rule, so the authoritative rule count stays 51.

**Tech Stack:** Markdown; YAML (SC1 manifest); `retail check` gate for verification.

## Global Constraints

- No numeric confidence/health score anywhere (roadmap hard rule #9). H4 uses `present | absent` + `status` + `blocking_reasons[]` only.
- No real client data in tracked files (Principle IX). H4 cites a filled contract by path; never inlines.
- C086 is an example, not the schema (Principle VII); the c086 corpus was removed in PR #144 — cite `retail_store_sales` / the shipped KPI contracts instead.
- Line endings: MD files are LF per `.gitattributes`; UTF-8 without BOM.
- Mandatory local gate before every commit: `ruff format --check src tests && ruff check src tests && pytest -m unit -x -q && retail check` (ruff/pytest are no-ops for pure-MD commits but run them anyway to stay honest).

---

### Task 1: I2 — land the groupby-aggregation-and-grain knowledge file + flip INDEX route

**Files:**
- Create: `skills/bi-python-knowledge/knowledge/groupby-aggregation-and-grain.md`
- Modify: `skills/bi-python-knowledge/INDEX.md` (move the two "planned" rows referencing this file from the Planned-routes table into the live task/symptom tables)
- Modify: `docs/quality/status-claims.yaml` (add an SC1 claim locking the new file as `built`)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: a live route target `knowledge/groupby-aggregation-and-grain.md` that I1 (Wave 2) and the SC1 gate will resolve against.

**Why this file first:** `INDEX.md` references it live TWICE as "*(groupby knowledge file is planned)*" (a task route and a symptom route) — it is the single highest-leverage planned file.

- [ ] **Step 1: Read the INDEX to find the exact rows to move**

Run: read `skills/bi-python-knowledge/INDEX.md`. Locate:
- Planned-routes row: `| Aggregate / groupby at a correct grain (knowledge file) | knowledge/groupby-aggregation-and-grain.md | planned / not yet implemented |`
- The two live rows whose middle cell says `*(groupby knowledge file is planned)*`.

- [ ] **Step 2: Write the knowledge file**

Create `skills/bi-python-knowledge/knowledge/groupby-aggregation-and-grain.md`. It must be a terminal knowledge artifact (not a fork of `checklists/aggregation-grain-checklist.md` — keep the fork boundary: the checklist is the *review* artifact, this is the *knowledge* artifact). Required sections:

```markdown
# Groupby, Aggregation, and Grain (Python / pandas for BI)

> Knowledge route. The *review* companion is `checklists/aggregation-grain-checklist.md`
> (a standalone checklist); this file is the conceptual knowledge it draws on. KPI
> *business meaning* lives upstream in `skills/retail-kpi-knowledge/` — this file covers
> the mechanical pandas grain/aggregation behavior only.

## What "grain" means before you group
[definition: one row = one what; grain is the set of keys that make a row unique]

## The double-counting trap (fan-out before aggregation)
[a join that fans out rows, then a sum that counts the fanned rows — worked pandas example]

## Additive vs non-additive measures under groupby
[sums are additive; ratios/rates/distinct-counts are NOT re-summable — link the
additivity concept to AD1's additivity classes]

## Choosing the groupby keys = declaring the output grain
[df.groupby(keys).agg(...); the keys ARE the new grain]

## Verifying grain after aggregation
[assert no duplicate keys; row-count sanity vs expected cardinality]

## Symptoms this file explains
- "Sums look too big after grouping" -> double-counting / wrong grain / non-additive summed
```

Content must be generic pandas knowledge (no client schema, Principle VII).

- [ ] **Step 3: Flip the INDEX routes live**

In `skills/bi-python-knowledge/INDEX.md`:
1. Remove the `groupby-aggregation-and-grain.md` row from the **Planned routes** table.
2. In the two live rows, replace `*(groupby knowledge file is planned)*` with `knowledge/groupby-aggregation-and-grain.md`.

- [ ] **Step 4: Register the SC1 status claim**

In `docs/quality/status-claims.yaml`, add under `claims:`:

```yaml
  - id: "bi-python-groupby-knowledge-built"
    doc: "skills/bi-python-knowledge/INDEX.md"
    anchor: "knowledge/groupby-aggregation-and-grain.md"
    claimed-artifact: "skills/bi-python-knowledge/knowledge/groupby-aggregation-and-grain.md"
    claimed-status: "built"
```

(The `anchor` must be a byte-exact substring present in `INDEX.md` after Step 3.)

- [ ] **Step 5: Verify the gate is green**

Run: `retail check`
Expected: exit 0. (SC1 confirms the anchor is present and the claimed artifact is tracked.)
Run: `git add -A && retail check` is enforced by the pre-commit hook too.

- [ ] **Step 6: Commit**

```bash
git add skills/bi-python-knowledge/knowledge/groupby-aggregation-and-grain.md \
        skills/bi-python-knowledge/INDEX.md \
        docs/quality/status-claims.yaml
git commit -m "docs: land bi-python groupby-aggregation-grain knowledge (I2)"
```

---

### Task 2: H4 — the KPI contract-sufficiency card template

**Files:**
- Create: `templates/kpi-sufficiency-card.md`
- Modify: `docs/metrics/retail-kpi-catalog.md` (add a reference to the new template)
- Modify: `skills/retail-kpi-knowledge/INDEX.md` (add a route to the new template)
- Modify: `docs/quality/status-claims.yaml` (SC1 claim locking the template as `built`)

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `templates/kpi-sufficiency-card.md` — a fillable card referenced from the catalog + KPI INDEX.

- [ ] **Step 1: Write the template**

Create `templates/kpi-sufficiency-card.md`. It records, per KPI, which required fields are present/absent and the resulting status — **NO numeric score** (hard rule #9):

```markdown
# KPI Contract-Sufficiency Card

> A per-KPI readiness card: does this KPI's contract carry every field needed to build
> it safely? Records `present | absent` per required field and a derived `status` +
> `blocking_reasons[]`. It emits NO numeric score (hard rule #9) — sufficiency is a
> categorical status, never a percentage. Fill one card per KPI; cite the KPI's filled
> contract, never inline data (Principle IX).

kpi_id: <kpi id, e.g. net_sales>
contract: <path, e.g. skills/retail-kpi-knowledge/contracts/net-sales.md>

required_fields:
  - name: grain            # the fact grain the KPI aggregates at
    state: present | absent
  - name: additivity       # additive | semi-additive | non-additive (links AD1)
    state: present | absent
  - name: filter_context   # the filter/rollup context it is valid under
    state: present | absent
  - name: source_binding   # the gold column(s) it binds to
    state: present | absent
  - name: ambiguities      # decided or open ambiguity rulings (links AL1/AL2)
    state: present | absent

status: ready | blocked          # ready = every required field present
blocking_reasons:                # one line per absent field; empty when ready
  - <field> unspecified — <what a human must supply>

worked_example: skills/retail-kpi-knowledge/contracts/net-sales.md
```

- [ ] **Step 2: Reference it from the catalog and KPI INDEX**

In `docs/metrics/retail-kpi-catalog.md`, add a short section pointing to `templates/kpi-sufficiency-card.md` as the per-KPI sufficiency artifact. In `skills/retail-kpi-knowledge/INDEX.md`, add a route row whose target is `templates/kpi-sufficiency-card.md`.

- [ ] **Step 3: Register the SC1 status claim**

In `docs/quality/status-claims.yaml` add:

```yaml
  - id: "kpi-sufficiency-card-template-built"
    doc: "docs/metrics/retail-kpi-catalog.md"
    anchor: "templates/kpi-sufficiency-card.md"
    claimed-artifact: "templates/kpi-sufficiency-card.md"
    claimed-status: "built"
```

(The `anchor` must be byte-exact in the catalog after Step 2.)

- [ ] **Step 4: Verify + commit**

```bash
retail check   # expect exit 0
git add templates/kpi-sufficiency-card.md docs/metrics/retail-kpi-catalog.md \
        skills/retail-kpi-knowledge/INDEX.md docs/quality/status-claims.yaml
git commit -m "docs: add KPI contract-sufficiency card template (H4)"
```

---

## Self-review notes
- Spec coverage: I2 + H4 fully covered; both are content, no rule-count change (stays 51).
- No numeric score in H4 (categorical status only) — honors hard rule #9.
- Both register SC1 claims so the "built" prose can't drift (the repo's own staleness gate).
- Fork boundary preserved (I2 knowledge file ≠ the checklist).
