# T003 — dev-only reference enumeration (pre-change baseline)

**Captured**: 2026-07-31 | **HEAD**: `bf1285e` | **Scope**: the ten
`.seshat/kit-source.yaml` compass verbs (User Story 3)

## Count correction

The specification was authored citing **23** dev-only references. That figure
counted distinct dev-path *classes* per skill (a coarse prefix match). Enumerating
full paths gives **33 distinct (skill, path) pairs**. The specification, the
portability contract and T003 have been corrected to 33.

| Verdict | Count | Meaning |
|---|---:|---|
| `PASS-dev-scoped` | 1 | Already scoped by an explicit development-repository condition (FR-017) |
| `REVIEW` | 3 | Verdict depends on a scaffold decision; resolve before rewriting |
| `FAIL-read` | 17 | Instructs the agent to read or run a path a scaffolded workspace lacks |
| `FAIL-provenance` | 12 | A "see also" pointer at a development artifact — the claim is fine, the path is not |
| **Total** | **33** | |

## Findings

| # | Skill | Line | Path | Verdict | Resolution |
|---:|---|---:|---|---|---|
| 1 | retail-orchestrate | 23 | `specs/005-layer-d-orchestration` | FAIL-provenance | Drop the path, keep the claim |
| 2 | retail-orchestrate | 136 | `specs/006-warehouse-builder` | FAIL-provenance | Drop the path, keep the claim |
| 3 | retail-orchestrate | 165 | `.claude/skills/` (7 verbs) | FAIL-read | Name the skills, not their dev paths |
| 4 | retail-orchestrate | 169 | `docs/worked-examples/` | FAIL-read | Dev-scope, or point at the shipped example |
| 5 | first-hour-compass | 34 | `templates/first-hour-compass.md` | FAIL-read | Scaffold output, or inline the cross-walk |
| 6 | first-hour-compass | 57 | `docs/worked-examples/retail-store-sales.md` | FAIL-read | Dev-scope or ship it |
| 7 | first-hour-compass | 60 | `docs/worked-examples/README.md` | FAIL-read | Dev-scope or ship it |
| 8 | first-hour-compass | 66 | `templates/` | **REVIEW** | Describes where seeded artifacts come from — passes only if a scaffold verb is named |
| 9 | retail-onboard-table | 99 | `templates/readiness-status.yaml` | FAIL-read | Name the scaffold verb that writes it |
| 10 | retail-onboard-table | 154 | `docs/worked-examples/` | FAIL-read | Dev-scope or ship it |
| 11 | retail-onboard-table | 163 | `.claude/skills/source-mapping/SKILL.md` | FAIL-read | Name the skill |
| 12 | retail-onboard-table | 165 | `.claude/skills/retail-build-warehouse/SKILL.md` | FAIL-read | Name the skill |
| 13 | retail-onboard-table | 166 | `docs/roadmap/roadmap.md` | FAIL-provenance | Drop the path |
| 14 | retail-discover-portfolio | 24 | `templates/portfolio-survey.md` | FAIL-read | Name the scaffold verb |
| 15 | retail-discover-portfolio | 35 | `tests/fixtures/portfolio-survey/db-schema/survey.md` | FAIL-read | Dev-scope — a customer has no test fixtures |
| 16 | retail-discover-portfolio | 36 | `tests/fixtures/portfolio-survey/file-folder/survey.md` | FAIL-read | Dev-scope |
| 17 | retail-discover-portfolio | 54 | `templates/portfolio-survey.md` | FAIL-read | Name the scaffold verb |
| 18 | business-knowledge-interview | 26 | `specs/121-business-knowledge-interview` | FAIL-provenance | Drop the path |
| 19 | source-mapping | 35 | `templates/` | **PASS-dev-scoped** | None — already states it "exists only in the Seshat development repo" |
| 20 | source-mapping | 184 | `docs/worked-examples/` | FAIL-read | Dev-scope or ship it |
| 21 | kpi-contract-builder | 23 | `src/seshat/kpi_contracts.py` | FAIL-provenance | Name the CLI verb, not the module |
| 22 | kpi-contract-builder | 24 | `src/seshat/kpi_answerability.py` | FAIL-provenance | Name the CLI verb |
| 23 | retail-build-warehouse | 24 | `specs/006-warehouse-builder` | FAIL-provenance | Drop the path |
| 24 | retail-build-warehouse | 150 | `.claude/skills/retail-orchestrate/SKILL.md` | FAIL-read | Name the skill |
| 25 | retail-validate | 16 | `src/seshat/validate.py` | FAIL-provenance | Name the CLI verb |
| 26 | retail-validate | 85 | `src/seshat/validate_targets.py` | FAIL-provenance | Name the CLI verb |
| 27 | retail-validate | 88 | `templates/reconciliation-report.md` | FAIL-read | Name the scaffold verb that writes the blank |
| 28 | retail-govern | 18 | `src/seshat/rules/` | FAIL-provenance | Keep `docs/rules/rules-manifest.json`, drop the source path |
| 29 | retail-govern | 19 | `specs/2026-06-23-pbi-governance-layer-design` | FAIL-provenance | Drop the path |
| 30 | retail-govern | 41 | `src/seshat/severity_posture.py` | FAIL-provenance | Drop the source path |
| 31 | retail-govern | 59 | `scripts/export_rule_fix_table.py` | FAIL-read | Instructs running a script absent from a workspace — dev-scope it |
| 32 | retail-govern | 111 | `docs/quality/conformed-dimension-map.yaml` | **REVIEW** | A file the USER authors; `_EMPTY_DIRS` does not create `docs/quality/`. Either scaffold it or say "create" |
| 33 | retail-govern | 140 | `docs/quality/shared-spine.yaml` | **REVIEW** | Same as #32 |

## The three REVIEW items are one decision

Findings 8, 32 and 33 all ask the same question: **does a scaffolded workspace get
`templates/` and `docs/quality/`, or do the skills tell the user to create those
artifacts on demand?** `src/seshat/workspace_init.py::_EMPTY_DIRS` currently
creates only `mappings`, `warehouse/migrations`, `powerbi`, `reports` and
`evidence`.

This is a scaffold-scope decision, not a wording choice, and it changes the
resolution of three findings plus the shape of findings 5, 9, 14, 17 and 27.

### RULED — name the scaffold verb

- **decision**: shipped skills say "run *&lt;scaffold verb&gt;*, which writes this
  file" rather than "read `templates/x`". `workspace_init._EMPTY_DIRS` is **not**
  extended, and the references become FR-017 scaffold-outputs, which pass.
- **ruled_by**: Ahmed Shaaban (owner)
- **ruled_on**: 2026-07-31
- **recorded_by**: the agent transcribed an owner-directed ruling; it did not
  self-grant (Principle V).

**Rationale as ruled**: it resolves eight findings (8, 32, 33 plus 5, 9, 14, 17,
27) with one rule, changes no shipped CLI behaviour, and keeps `init-project`'s
surface exactly as specified — widening the scaffold would have been a change to
a shipped verb beyond this feature's scope.

**Consequence for findings 32 and 33**: `docs/quality/conformed-dimension-map.yaml`
and `docs/quality/shared-spine.yaml` are files the **user authors**. The rewrite
must therefore instruct creation ("declare it in …, creating the file if absent"),
not reading — a scaffold verb that does not write them cannot be named.

## Notable

- Finding 19 is the **working precedent** for the FR-017 dev-scoped exemption:
  `source-mapping` already states that `templates/` exists only in the
  development repository. The rewrites should follow its wording.
- Findings 3, 11, 12 and 24 are cross-skill references written as **file paths**.
  In a bundle these are skill *names* the agent routes to, so the rewrite makes
  them more correct in both contexts, not merely portable.
- Findings 21, 22, 25, 26, 28 and 30 point at `src/seshat/` modules. A customer
  running an installed `seshat` **has** that code, just not at a repo-relative
  path — so the rewrite names the CLI verb, which is what the agent can actually
  invoke.
