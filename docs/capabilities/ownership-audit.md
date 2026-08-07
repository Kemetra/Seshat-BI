# Capability ownership audit — official-first, Seshat-for-the-delta

Read-only audit for issue #592, Workstreams 1-2. Verified against `main` at
`f596f20`.

This document **records findings only**. It deletes nothing, changes no gate,
adds no field to `docs/capabilities/capabilities.yaml`, and grants no approval.
Per the issue's own Non-goals: *"Do not delete skills in the inventory phase."*
Every `REMOVE`/`MERGE` row below is a **candidate requiring explicit human
review**, not a decision.

> **Current Power BI resolution (Spec 145, 2026-08-07).** The snapshot's Power
> BI MERGE candidate is resolved without deletion: `powerbi-workflows` is the
> broad public front door, `powerbi-dashboard-design` is a nested design-only
> router, and `pbi-mcp-doctor` is the machine-checkable execution-owner selector.
> Native report mechanics delegate to Microsoft's official
> `powerbi-report-authoring` skill after Seshat's dashboard gate; activation and
> discovery proof remains Phase 6. F016 is only the separately parked live
> semantic-model connection/refresh/query/publish adapter.

## 1. What the surfaces actually are

The issue describes "four representation layers" that "can drift
independently". The verified structure is narrower: **two canonical sources
with two distinct shipping gates, plus generated output.**

| Tree | Role | Count | Shipping gate |
| --- | --- | --- | --- |
| `.claude/skills/` | canonical authored workflow/governance skills | 51 | `ship_classification` in `capabilities.yaml` (10 are `compass-verb`) |
| `skills/` | canonical authored knowledge roots | 6 | `canonical_roots` in `distribution/public-knowledge-allowlist.yaml` |
| `integrations/claude-code/seshat-bi/` | **generated** projection | 16 skills + 6 knowledge + 26 commands | output of `scripts/export_agent_bundles.py` |
| `integrations/codex/seshat-bi/` | **generated** projection | same, minus `commands/` (Codex has no slash-command surface) | same |

`distribution/bundle-templates/` is a fifth tree the issue does not name: it is
**authored template source** (e.g. the `bi-analyst-knowledge` router, which is
intentionally *not* a copy of `skills/bi-analyst-knowledge/SKILL.md`), not a
downstream copy. No drift check is owed to it beyond the allowlist pipeline.

Byte-diff of every canonical→generated overlapping pair on `main`: **identical**.

### Already-shipped drift enforcement

| Gate | Location |
| --- | --- |
| `Generated agent bundle drift` CI step | `.github/workflows/ci.yml:68-69` → `export_agent_bundles.py --check` |
| Bundle contract tests in CI | `.github/workflows/ci.yml:64` → `tests/contract/test_generated_agent_bundles.py` |
| Byte-level tree comparison | `compare_bundle_trees`, `scripts/export_agent_bundles.py:656-673` |
| Determinism | `test_two_exports_have_identical_paths_and_bytes` |
| Cross-target parity | `test_pbip_adoption_router_is_identical_in_claude_and_codex_regeneration` |
| Source/output hash divergence | `compare_shared_provenance()` |
| Ship-completeness | `test_capability_ship_classification.py` |
| Fail-closed inputs | `test_public_knowledge_allowlist.py` |
| Release-time | `release.yml:71`, `prepare-coordinated-release.yml:261,300` |

Consequence: **Workstream 4 is substantially complete.** Its remaining scope is
documenting why `distribution/bundle-templates/` is exempt.

## 2. Capability-to-surface matrix

`docs/capabilities/capabilities.yaml` — 102 entries:

| `surface` | Entries |
| --- | --- |
| `cli` | 53 |
| `skill` | 36 |
| `docs` | 6 |
| `execution-adapter` | 4 |
| `product-module` | 1 |
| `plugin` | 1 |
| `human-artifact` | 1 |

`ship_classification`: `consumer-capability` 23, `compass-verb` 10,
`knowledge-root` 6, `development-only` 5, plus one aggregate entry covering all
14 `speckit-*` skills.

### MCP surfaces

| File | Declares |
| --- | --- |
| `distribution/bundle-templates/shared/mcp-servers.json` | `seshat-governor` (`seshat mcp`) — template source |
| `integrations/{claude-code,codex}/seshat-bi/mcp-servers.json` | `seshat-governor` — generated |
| `.mcp.json.example` | `powerbi-modeling` — Microsoft's binary, `--readonly --compatibility=powerbi` |

The Seshat-authored server is the **only** one a bundle installs. Official
execution MCPs stay machine-local. This is the §2/§3 architecture, confirmed.

### Plugin/marketplace surfaces

`.claude-plugin/marketplace.json` (`seshat-bi-marketplace`) and
`.agents/plugins/marketplace.json` (`seshat-bi-repository`) each publish one
plugin sourced from the corresponding generated `integrations/` tree.

## 3. Upstream ownership already declared in code

`src/seshat/integrations/catalog.py:61-67` is **already an upstream ownership
registry** — just in code, and only for *installable* dependencies:

| Component | Upstream project | Coordinate | Notes |
| --- | --- | --- | --- |
| `dbt-core`, `dbt-postgres` | dbt Labs | PyPI | `catalog.py:151-167` |
| `dbt-agent-skills` | dbt Labs | `dbt-labs/dbt-agent-skills` | `catalog.py:168-175` |
| `dbt-mcp` | dbt Labs | PyPI via `uvx` | `mcp_server=True`, `catalog.py:176-186` |
| `dagster` | Dagster | PyPI | `catalog.py:191-198` |
| `fabric-skills` | Microsoft | `microsoft/skills-for-fabric` | `catalog.py:217-223` |
| `powerbi-modeling-mcp` | Microsoft | `@microsoft/powerbi-modeling-mcp` (npm) | **preview/pre-GA**, `mode="readonly"`, `catalog.py:224-235` |
| `seshat-dagster-adapter`, `dagster-skills` | Seshat (bundled) | — | `catalog.py:199-212` |

`seshat integrations setup` is the official-first pattern already generalized
beyond Power BI: network-free plan by default, install only behind explicit
human approval, confined to gitignored `.seshat/integrations/`, never
pip-installing over the operator's interpreter, never writing a credential.

**Resolved for dbt by Spec 146:** the capability manifest now distinguishes
official `dbt-core`, `dbt-agent-skills`, and `dbt-mcp` ownership from the
Seshat `dbt-transformation-adapter` delta. Catalog membership still does not
prove skill/MCP activation or discovery; that remains a Phase 6 integration gap.

## 4. Workstream 2 — ownership classification

Classes: `official-dependency` / `seshat-governance` /
`seshat-domain-knowledge` / `seshat-orchestrator`.

### KEEP — `seshat-domain-knowledge` (6)

All of `skills/`: `bi-analyst-knowledge`, `bi-bigdata-knowledge`,
`bi-dax-knowledge`, `bi-python-knowledge`, `bi-sql-knowledge`,
`retail-kpi-knowledge`. Seshat-reviewed reasoning layers, not upstream tooling
docs. No upstream owns "retail KPI additivity and grain policy".

### KEEP — `seshat-governance` (readiness, evidence, approvals)

`retail-govern`, `retail-semantic-check`, `retail-validate`,
`readiness-viewer`, `run-next-readiness`, `portfolio-watch`,
`retail-control-room`, `approval-console`, `approval-evidence-pack`,
`evidence-pack-generator`, `grain-confidence-reviewer`, `capabilities`,
`cross-table-lineage`, `consumer-data-dictionary`.

Encode readiness gates, evidence contracts, and approval seams. No upstream
equivalent exists — these are the product.

### KEEP — `seshat-orchestrator` (front doors and sequencers)

`retail-orchestrate`, `retail-onboard-table`, `source-mapping`,
`retail-discover-portfolio`, `business-knowledge-interview`,
`kpi-contract-builder`, `first-hour-compass`, `retail-build-warehouse`,
`retail-init`, `retail-scaffold`, `report-intent-interview`,
`dashboard-intelligence`.

Sequence governed steps and stop at human seams. Coordination logic, not
reimplementation.

### WRAP — `seshat-orchestrator` over `official-dependency`

Each needs a documented `seshat_delta`. All four already reference the official
surface rather than forking it — the gap is **declaration**, not behavior.

| Skill | Upstream | Seshat delta |
| --- | --- | --- |
| `dbt-transformation-adapter` | dbt Labs (`dbt-core`, `dbt-agent-skills`, `dbt-mcp`) | Mapping-Ready and accepted-plan gating; fixed selector/shadow policy; run/test/parity recorded as derived evidence. Generic dbt competence routes upstream once discovery is proven (Spec 146). |
| `dagster-orchestration-adapter` | Dagster | gate-aware asset graph; committed run evidence |
| `pbi-mcp-doctor` | Microsoft `@microsoft/powerbi-modeling-mcp` | read-only preflight; refuses `--skipconfirmation`/write-mode; fails closed before `semantic_model_ready` |
| `pbir-authoring-adapter` | PBIR format (Microsoft) | tight allow-list on committed JSON; no live publish |

### INSPECT — generic dev workflow, may overlap official surfaces

Not removal candidates on this evidence; each has a plausible Seshat delta that
is currently **undocumented**. Needs a ruling.

| Skill | Overlaps | Question |
| --- | --- | --- |
| `friendly-pr-reviewer` | GitHub/Claude review surfaces | is plain-language rendering of *governance* output a real delta? |
| `pr-readiness-reviewer` | GitHub checks | `merge_ready` verdict is Seshat-specific; likely KEEP |
| `release-notes-generator` | GitHub Releases | evidence-backed maturity ladder is Seshat-specific; likely KEEP |
| `showcase-build` | — | disclosure-safe offline proof bundle; likely KEEP |
| 14 × `speckit-*` | upstream Spec Kit | **RESOLVED 2026-08-07 -- not a finding.** They *are* vendored upstream content, but sanctioned: written by upstream's own installer (`specify init --here --integration claude --script ps`, spec-kit `0.8.10`) in commit `1eb0c98`, which in the same commit amended the constitution to v1.1.0 to permit exactly this (`.specify/memory/constitution.md:556-563`). Hash-verified against `.specify/integrations/claude.manifest.json`, zero local drift, no Seshat vocabulary in any body. Principle II is scoped to the **Power BI execution adapter**, not to all tooling, so it does not bind here. Residual risk is narrower: no recorded re-vendor/upgrade path (no lockfile, no `specify upgrade` record), which is the "fork tax" the Principle II *rationale* warns about -- unpaid so far. All `development-only`; no shipped surface affected. |

`pbip-workflow`, `pbip-xray`, `dashboard-design`, `powerbi-dashboard-design`,
`powerbi-workflows` — Power BI layer. At this audit snapshot,
`powerbi-dashboard-design` and `powerbi-workflows` appeared to be overlapping
routers. **Resolved by Spec 145** as the broad-router / nested-design-router
hierarchy recorded above; no merge or deletion was justified.

### GENERATE — already correct

All 16 skills + 6 knowledge roots + 26 commands under `integrations/*`. Already
generated and drift-gated. **No action.**

### REMOVE — none proposed

No capability on this evidence lacks unique value. Consistent with the
inventory-phase Non-goal.

## 5. Findings the issue should absorb

1. **Workstream 4 is shipped** (§1 above). Remaining: document the
   `bundle-templates/` exemption.
2. **§D is downstream of §C, not parallel.** The canonical/generated half is
   gated twice already. The ungated half — "a new skill ships without ownership
   classification" — cannot be gated until an ownership field exists.
3. **§C is a build, not an audit.** Adding nine fields across 102 entries
   changes a manifest that `tests/contract/test_capability_ship_classification.py`
   reads. It warrants its own spec.
4. **Partial registry already exists** at `catalog.py:61-67`, covering
   installable deps. §C should extend the existing axis rather than introduce a
   parallel authority.
5. **`speckit-*` was the one vendored-upstream question surfaced by this audit.
   It is now RESOLVED as not a finding** (2026-08-07, owner-directed
   investigation). The 14 skills are vendored, but by upstream's own installer
   and under an explicit constitution amendment (v1.1.0) made in the same commit
   -- not a silent fork. Principle II binds the Power BI execution adapter, not
   all tooling. What remains is a narrower, real gap: **no recorded re-vendor or
   upgrade path** for the vendored spec-kit content -- no lockfile, no
   `specify upgrade` record, no re-run instructions. That is the "fork tax" the
   Principle II rationale warns about; it is unpaid today because the copy is
   provably unmodified, but nothing keeps it that way. Worth its own decision,
   separate from this axis.

## 6. Not done here

- No field added to `capabilities.yaml` (that is §C, needs a spec).
- No new `seshat check` rule (that is §D, downstream of §C).
- Nothing deleted or merged; §4 rows are candidates for human review.
- No readiness or approval gate touched.
