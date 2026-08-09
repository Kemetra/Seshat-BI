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
> `powerbi-report-authoring` skill after Seshat's dashboard gate. Spec 148 adds
> catalog-backed, read-only Claude/Codex activation and discovery proof. F016 is
> only the separately parked live
> semantic-model connection/refresh/query/publish adapter.

> **Phase 9 -- generic development capability rationalization: ALREADY-SATISFIED
> (2026-08-09, verified against `main` at `d202d30`).** The §4 `INSPECT` rows
> below are now RULED, non-destructively: every one resolves to `KEEP` or
> `GENERATED`, and **no `MERGE`, `REPLACE`, or `REMOVE` is justified**. Three
> facts close the phase.
>
> 1. **The ownership axis is authored and complete.** `capabilities.yaml` carries
>    `ownership.capability_owner` on **110/110 entries** (51
>    `seshat-governance`, 17 `seshat-orchestrator`, 12 `seshat-authoring`, 9
>    `seshat-adapter`, 7 `seshat-domain-knowledge`, 6 `official-upstream`, 5
>    `specified-not-built`, 1 each `seshat-product-module` /
>    `vendored-upstream` / `human-deliverable`), gated by the ownership oracle in
>    `tests/unit/test_capability_inventory.py`
>    (`test_ownership_rejects_missing_capability_owner`) -- **not** by
>    `tests/contract/test_capability_ship_classification.py`, which gates only
>    `ships` / `ship_classification` and never reads
>    `ownership.capability_owner`. This discharges §5 finding 3 and **closes**
>    §5 finding 2 (see its own correction note).
> 2. **No official replacement is registered for generic development
>    competence.** `src/seshat/integrations/catalog.py` -- the repo's registry of
>    proven upstream owners -- contains only data/BI tooling (duckdb, polars,
>    pyarrow, pandera, connectorx, dbt x3, dagster x4, fabric/powerbi x2,
>    jinja2, xlsxwriter, playwright). There is **no GitHub / Claude Code / Codex
>    generic-development integration**, so no `REPLACE` can meet the
>    proven-replacement bar the dbt (Spec 146) and Dagster (Spec 147) rulings set.
> 3. **The candidate set is closed and unrouted.** A sweep of all **57**
>    repo-authored `SKILL.md` files -- the O2 scope as `capabilities.yaml:12-16`
>    declares it: `git ls-files` matches at the **repo top level**, i.e. the 51
>    canonical `.claude/skills/*/SKILL.md` plus the 6 Knowledge Bases under
>    `skills/*/SKILL.md` -- surfaces only the five
>    `development-only` entries already listed here; the 60 entries without a
>    `ship_classification` yield 21 keyword hits, all Seshat readiness/
>    governance/PBIR capabilities. None of the five appears in
>    `docs/routing/routes.yaml`, so no rerouting remedy applies either.
>    `zambahola` and any `code-review` skill are **not** repo-authored (zero
>    git-tracked files) -- user/plugin-level, outside O2 scope. The 57 excludes
>    the 42 generated Claude/Codex bundle projections, the 11 authored
>    `distribution/bundle-templates/` inputs, and 4 test fixtures; those are
>    projections or fixtures of the same canonical skills, so counting them would
>    sweep one skill up to three times and inflate the evidence without widening
>    it (an earlier draft of this note said 114 for exactly that reason). The
>    candidate set is identical under either count.
>
> Verdicts were taken from BEHAVIOR, not from each skill's self-declared
> boundary: `friendly-pr-reviewer` reads no source and finds no defects (it
> renders the `build_review_result` envelope via the 788-line
> `src/seshat/pr_summary.py`), and `pr-readiness-reviewer` names `gh` once in one
> line and teaches no `gh` usage -- so the Section 12 fork tax is minimal in both.
> Because all five are `ships: False` and the bundle allowlist is DERIVED from
> this manifest, no public bundle surface is affected. Internal consumers do
> exist and are unchanged: `retail-orchestrate` may invoke
> `pr-readiness-reviewer` as a pre-merge read, and the opt-in, off-by-default
> `.github/workflows/ci.yml` "Friendly PR summary" step
> (`scripts/post_friendly_pr_summary.py`) is the one networked write in the set.
>
> **No Phase 10 cleanup work is approved by this ruling** -- not for want of
> evidence, but because the rationalization was already performed incrementally
> by Specs 142/145/146/148/151. A future official development-capability
> integration entering the catalog would reopen the generic halves of
> `pr-readiness-reviewer` and `release-notes-generator` as genuine `WRAP`
> candidates, retaining the `merge_ready` derivation and the L0-L6 ladder above
> it. Nothing was deleted, merged, renamed, or rerouted to record this.

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
`knowledge-root` 6, `development-only` 5, `upstream-integration` 5, plus one
aggregate entry covering all 14 `speckit-*` skills.

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
| `dagster-agent-skills` | Dagster | `dagster-io/skills` | official `dagster-expert` payload; Spec 148 verifies declared Claude/Codex discovery paths |
| `fabric-skills` | Microsoft | `microsoft/skills-for-fabric` | `catalog.py:217-223` |
| `powerbi-modeling-mcp` | Microsoft | `@microsoft/powerbi-modeling-mcp` (npm) | **preview/pre-GA**, `mode="readonly"`, `catalog.py:224-235` |
| `seshat-dagster-adapter`, `seshat-dagster-workflows` | Seshat (bundled) | — | governed runtime adapter and public router; legacy `dagster-skills` is lookup-only compatibility |

`seshat integrations setup` is the official-first pattern already generalized
beyond Power BI: network-free plan by default, install only behind explicit
human approval, confined to gitignored `.seshat/integrations/`, never
pip-installing over the operator's interpreter, never writing a credential.

**Resolved for dbt by Spec 146:** the capability manifest now distinguishes
official `dbt-core`, `dbt-agent-skills`, and `dbt-mcp` ownership from the
Seshat `dbt-transformation-adapter` delta. Spec 148 keeps catalog membership
separate from skill activation and discovery and exposes a read-only proof for
supported Claude/Codex paths. MCP registration/liveness remains a separate fact.

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
| `dagster-orchestration-adapter` | Dagster (`dagster`, `dagster-io/skills`) | Readiness-aware sequencing, named-human stops, closed execution policy, fail-closed propagation, and derived run evidence. Generic Dagster competence routes upstream once discovery is proven (Spec 147). |
| `pbi-mcp-doctor` | Microsoft `@microsoft/powerbi-modeling-mcp` | read-only preflight; refuses `--skipconfirmation`/write-mode; fails closed before `semantic_model_ready` |
| `pbir-authoring-adapter` | PBIR format (Microsoft) | tight allow-list on committed JSON; no live publish |

### INSPECT — generic dev workflow, may overlap official surfaces

Not removal candidates on this evidence; each had a plausible Seshat delta that
was, at the snapshot, **undocumented**. **All rows RULED 2026-08-09 (Phase 9,
`main` at `d202d30`) -- see the resolution note at the top of this file.** Each
`capability_owner` below is the value authored in `capabilities.yaml`, and the
"Ruling" column replaces the snapshot's open "Question" column. Every ruling is
non-destructive; the Phase 9 audit approved no deletion, merge, or rename.

| Skill | Overlaps | `capability_owner` | Ruling (2026-08-09) |
| --- | --- | --- | --- |
| `friendly-pr-reviewer` | GitHub/Claude review surfaces | `seshat-governance` | **KEEP** (HIGH). The snapshot's question -- "is plain-language rendering of *governance* output a real delta?" -- is answered **yes**, and the overlap is a naming artifact rather than a behavioural one. It is **not a code reviewer**: it reads no source, finds no defects, and suggests no improvements. It renders the `build_review_result` envelope (`seshat check --format review`) plus SARIF `finding_fingerprint` NEW/RESOLVED diffing and the `readiness_classify` rank, via the 788-line deterministic `src/seshat/pr_summary.py` (30/30 tests pass). It emits no `merge_ready` boolean and declines verdict requests, so it is complementary to F025, not duplicative. |
| `pr-readiness-reviewer` | GitHub checks | `seshat-governance` | **KEEP** (HIGH) -- the snapshot's "likely KEEP" is confirmed on behaviour. Fork tax is minimal: `gh pr view` / `gh pr checks` are named once, in one line of step 2, with no `gh` usage taught. The novel surface (step 4) cross-checks PR-body CLAIMS against committed Seshat evidence -- readiness-stage consistency, `approvals[]` named-owner presence, `source-map.yaml` CLEARED metadata, declared-vs-run tests -- which GitHub cannot perform, having no concept of a readiness stage. |
| `release-notes-generator` | GitHub Releases | `seshat-governance` | **KEEP** (HIGH) -- "likely KEEP" confirmed. The capability splits as anticipated and the Seshat half is substantial: GitHub Releases owns generic note *authoring*, while the evidence-gated **L0-L6 binary maturity ladder** over the F028 evidence pack, the F032 compatibility matrix, and the roadmap ledger is Seshat-only. No upstream surface can assess kit maturity from governance evidence. |
| `showcase-build` | — | `seshat-governance` | **KEEP** (HIGH) -- "likely KEEP" confirmed. Reads the Explorer projection (`build_explorer_projection`), the Passport, and the fail-closed disclosure scanner; no upstream equivalent exists, and no overlap was ever alleged. |
| 14 × `speckit-*` | upstream Spec Kit | `vendored-upstream` | **RESOLVED 2026-08-07 -- not a finding.** They *are* vendored upstream content, but sanctioned: written by upstream's own installer (`specify init --here --integration claude --script ps`, spec-kit `0.8.10`) in commit `1eb0c98`, which in the same commit amended the constitution to v1.1.0 to permit exactly this (`.specify/memory/constitution.md:556-563`). Hash-verified against `.specify/integrations/claude.manifest.json`, zero local drift, no Seshat vocabulary in any body. Principle II is scoped to the **Power BI execution adapter**, not to all tooling, so it does not bind here. Residual risk is narrower: no recorded re-vendor/upgrade path (no lockfile, no `specify upgrade` record), which is the "fork tax" the Principle II *rationale* warns about -- unpaid so far. All `development-only`; no shipped surface affected. **Residual gap CLOSED by Spec 151 (verified 2026-08-09).** The re-vendor path is now recorded: `.specify/init-options.json` pins the reproducible invocation (`speckit_version: 0.8.10`, `integration: claude`, `script: ps`, `branch_numbering: sequential`) and `.specify/integrations/speckit.manifest.json` hash-pins all ten vendored `.specify/scripts/` + `.specify/templates/` files with an `installed_at` stamp. Phase 9 ruling: **GENERATED** (`capability_owner: vendored-upstream`, `upstream_project: github/spec-kit`, `upstream_reference: 0.8.10`, with an authored `update_policy`) -- a deterministic vendored projection, not architectural duplication. |

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

   **CLOSED 2026-08-09 (Phase 9).** The ownership field now exists and is
   populated: `ownership.capability_owner` is authored on **110/110** entries of
   `capabilities.yaml`. Two distinct tests gate the two halves, and they must not
   be conflated: `tests/unit/test_capability_inventory.py` is the ownership
   oracle (`test_ownership_rejects_missing_capability_owner`, plus the
   real-manifest check) and is what rejects a missing owner, while
   `tests/contract/test_capability_ship_classification.py` gates only `ships` /
   `ship_classification` and never reads `ownership.capability_owner` -- an entry
   with valid shipping fields but no owner passes the shipping test and fails the
   inventory one. The fail-open this finding named is no longer open, and no new
   `seshat check` rule was required to close it.
3. **§C is a build, not an audit.** Adding nine fields across 102 entries
   changes a manifest that `tests/contract/test_capability_ship_classification.py`
   reads. It warrants its own spec.

   **DISCHARGED 2026-08-09 (Phase 9).** That spec was written and shipped:
   **Spec 142 / PR #595** built the ownership axis, and the manifest's own status
   line records "all 31 tasks complete". The build this finding called for is
   done, so Phase 9 required no successor spec (`.specify/feature.json` remains
   `null`).
4. **Partial registry already exists** at `catalog.py:61-67`, covering
   installable deps. §C should extend the existing axis rather than introduce a
   parallel authority.

   **HONOURED 2026-08-09 (Phase 9).** Spec 142 extended the existing axis rather
   than forking a parallel authority: `catalog.py` still owns *installable
   upstream dependencies*, while `capabilities.yaml`'s `ownership:` map owns
   *capability-level* ownership and references the catalog by
   `upstream_project` / `upstream_surface` / `upstream_reference`. Phase 9 read
   both surfaces and found no competing authority.
5. **`speckit-*` was the one vendored-upstream question surfaced by this audit.
   It is now RESOLVED as not a finding** (2026-08-07, owner-directed
   investigation). The 14 skills are vendored, but by upstream's own installer
   and under an explicit constitution amendment (v1.1.0) made in the same commit
   -- not a silent fork. Principle II binds the Power BI execution adapter, not
   all tooling. What remains is a narrower, real gap: **no recorded re-vendor or
   upgrade path** for the vendored spec-kit content -- no lockfile, no
   `specify upgrade` record, no re-run instructions. That is the "fork tax" the
   Principle II rationale warns about. Worth its own decision, separate from
   this axis.

   **CLOSED 2026-08-09 (Phase 9).** Spec 151 recorded the re-vendor path:
   `.specify/init-options.json` pins the reproducible invocation
   (`speckit_version: 0.8.10`) and `.specify/integrations/speckit.manifest.json`
   hash-pins the ten vendored files with an `installed_at` stamp. The fork tax
   this finding named is paid; the decision it asked for was taken by Spec 151,
   which removed the one real local modification (the `spec-template.md` ADR-0019
   block) rather than institutionalizing it. See the `speckit-*` row in §4.

   **Correction, 2026-08-08 (spec 151).** This passage originally read that the
   fork tax "is unpaid today because the copy is provably unmodified." That was
   false at the time of writing: commit `f35612f` had already modified
   `.specify/templates/spec-template.md`, adding an 11-line ADR-0019 vocabulary
   block and changing the seeded status value. One tracked spec-kit file
   therefore carried a real local modification; the other five apparent hash
   drifts were CRLF checkout artifacts, not content changes. The claim in the
   row at the top of this section -- zero drift against
   `.specify/integrations/claude.manifest.json` -- was and remains true, as it
   covers the nine skill files rather than the templates. The architecture
   chosen is to REMOVE the modification rather than institutionalize it: Spec
   Kit owns Spec Kit, Seshat owns Seshat governance, and the status policy now
   lives in `src/seshat/spec_status_policy.py`. `specs/151-speckit-fork-removal`
   tracks that migration. The historical audit above is otherwise unchanged.

## 6. Not done here

- No field added to `capabilities.yaml` (that is §C, needs a spec).
- No new `seshat check` rule (that is §D, downstream of §C).
- Nothing deleted or merged; §4 rows are candidates for human review.
- No readiness or approval gate touched.
