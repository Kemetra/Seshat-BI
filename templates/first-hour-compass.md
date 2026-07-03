# First-Hour Compass -- single-table "you are here" orientation card

> On-disk spec: `specs/055-first-hour-compass-new-table/`  Roadmap feature: none (idea-bank
> item; the roadmap F-number is authoritative when one is later assigned).
>
> GENERIC template. The STATEFUL single-table sibling of `readiness-view.md` (F026, which is
> the multi-table stage matrix) and the stateful version of the STATIC F006
> `docs/readiness/onboarding-checklist.md`. Rendered by the `first-hour-compass` skill from
> state that ALREADY EXISTS at `mappings/<table>/readiness-status.yaml` (ADR 0004). It runs
> NO check and edits NO file (read-only).
>
> **Renders, never re-derives.** Every field is copied VERBATIM from the source
> `readiness-status.yaml`: `current_stage`, each stage `status`, `blocking_reasons[]`,
> `approvals[]`. Never an adjective, never an invented status, never a synthesized line.
>
> **No fake confidence.** There is NO health / confidence / percent-ready / maturity score,
> and a filled copy MUST NOT add one (hard rule #9). Orientation is the four explicit
> statuses + evidence + blockers + the next allowed step.
>
> **Surfaces the human seam, never crosses it (Principle V).** The card SURFACES a recorded
> STOP (a `blocking_reason`, an approval-required flag) so the author knows a human must act;
> it never populates an approval, clears a blocker, advances a stage, or resolves the four
> judgment seams (grain / PII publish-safety / business rollup-segment / product identity).
>
> **Respects pipeline ordering.** The "next stage" is the FIRST non-`pass` stage in pipeline
> order (Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish); a
> downstream stage is never presented as reachable while an upstream gate is not `pass`.
>
> **Generic, not C086.** Placeholder rows only; C086 / `retail_store_sales` is a cited filled
> instance, never inlined. ASCII only, UTF-8 no BOM; the stage spine uses `->`.

---

## Orientation card

**Table**: `<schema>.<table>`  **Rendered on**: `<YYYY-MM-DD>` (a fresh read of the file)

| Field | Value (copied verbatim from `mappings/<table>/readiness-status.yaml`) |
|-------|----------------------------------------------------------------------|
| You are here | `current_stage` = `<stage_key>` (status `<not_started \| blocked \| warning \| pass>`) |
| Next stage | `<first non-pass stage in pipeline order, or "all pass -- Publish reached">` |
| Next artifact to produce | `<the artifact that stage requires -- from its <stage>-ready.md>` |
| Authoring skill | `<the skill from the cross-walk below for the next stage>` |
| STOP rows (human seam) | `<blocking_reasons[] verbatim + "approval required: <owner from stage doc>" when the next stage needs a named sign-off>` |
| Conflict flags | `<e.g. a stage marked pass with empty evidence[]; a downstream stage entered while an upstream is not pass -- surfaced, never auto-corrected>` |

> If `readiness-status.yaml` is absent for this table: **"Not yet onboarded -- start at
> Source Ready with `retail-onboard-table`."** (An absent file is the honest not-started state,
> never a fabricated stage.)

## Stage -> authoring-skill cross-walk (generic kit capability)

Each row maps a readiness `<stage_key>` to the named authoring skill DIRECTORY that advances
it. This is a generic kit capability map -- it embeds no table-specific, rollup/segment, or
product-identity assumption (Principle V / VII).

| `<stage_key>` | Gate doc | Authoring skill (directory) |
|---------------|----------|-----------------------------|
| `source_ready` | `docs/readiness/source-ready.md` | `.claude/skills/retail-onboard-table` |
| `mapping_ready` | `docs/readiness/mapping-ready.md` | `.claude/skills/source-mapping` |
| `silver_ready` | `docs/readiness/silver-ready.md` | `.claude/skills/retail-build-warehouse` |
| `gold_ready` | `docs/readiness/gold-ready.md` | `.claude/skills/retail-build-warehouse` (build the gold star), then `.claude/skills/retail-validate` (live-validate it) |
| `semantic_model_ready` | `docs/readiness/semantic-model-ready.md` | `.claude/skills/retail-semantic-check` |
| `dashboard_ready` | `docs/readiness/dashboard-ready.md` | `.claude/skills/dashboard-design` |
| `publish_ready` | `docs/readiness/publish-ready.md` | `.claude/skills/evidence-pack-generator` (+ `approval-console` for the recorded sign-off) |

## See also

- The multi-table stage-lens parent (F026): `../docs/tools/readiness-viewer.md`, `readiness-view.md`, `.claude/skills/readiness-viewer/SKILL.md`
- The static definition-of-done parent (F006): `../docs/readiness/onboarding-checklist.md`
- The input this card reads: `readiness-status.yaml` (canonical per-table location: ADR 0004 `mappings/<table>/readiness-status.yaml`)
- Stage ordering + gates: `../docs/readiness/readiness-pipeline.md`, `../docs/readiness/<stage>-ready.md`
- A filled concrete instance: a worked example under `../docs/worked-examples/`
