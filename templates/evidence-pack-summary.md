# Evidence Pack -- Summary -- `<schema>.<table>`

> **GENERIC template -- copy this file to `mappings/<table>/evidence-pack-summary.md`**,
> fill every `<placeholder>`, commit it.
> **Roadmap feature: F028  On-disk spec: `specs/022-evidence-pack-generator/`**
> (dir 022 == F028; the roadmap F-number is authoritative when the two disagree).
> **Authority category: Product Module / `artifact-writing`** (F024 --
> `../docs/architecture/product-modules.md`).
>
> The one-page readiness summary that accompanies the 10-section index
> (`evidence-pack-index.md`). It SURFACES the current readiness stage, the
> `publish_ready` state, the recorded approval (if any), and the rolled-up open
> blockers across all sections. It surfaces; it decides nothing.
>
> **Surfaces, never asserts.** The `publish_ready` status and the recorded approval
> are READ from `readiness-status.yaml` and DISPLAYED here. This summary records
> nothing back: it writes no approval, edits no `approvals[]`, and moves no stage to
> `pass`. The publish decision belongs to the named human via Core Authority; the pack
> reads-and-displays it. (F028 boundary: it does NOT transcribe a fresh decision and it
> does NOT make one.)
>
> **No publish-ready claim without the recorded pass + approval.** This summary prints
> a publish-ready CLAIM ONLY when `publish_ready: pass` with a named human approval is
> recorded in `readiness-status.yaml`. In every other case it shows the upstream
> blocking reasons -- never a claim.
>
> **No fake confidence, no count.** The four explicit statuses + evidence + blockers
> convey state and completeness. NO numeric confidence/health number and NO "N of 10
> sections present" tally anywhere (hard rule #9; Clarifications 2026-06-25).
>
> **Generic, not C086.** Placeholders only; the worked example is cited by reference
> (Principle VII). ASCII only, UTF-8 no BOM; keep paths short (Windows MAX_PATH).

---

## Header

| Field | Value |
|-------|-------|
| Table / report | `<schema>.<table>` |
| Source family | `<source_family>` |
| Composed on | `<YYYY-MM-DD>` |
| Composed by | `<analyst / agent>` |
| Source of state | `mappings/<table>/readiness-status.yaml` (read-only) |

## Current readiness stage (stated honestly)

- **Current stage:** `<current_stage from readiness-status.yaml>` (one of
  `source_ready` .. `publish_ready`).
- **In-progress?** `<yes -- composed before Publish Ready / no -- at Publish Ready>`.
  When in-progress, this summary states the CURRENT stage and the blocking reasons for
  the unreached stages; it claims NO stage the table has not reached.

The summary STATES the stage the Core Authority artifacts already record; it advances
no stage.

## Publish-ready state (surfaced, never asserted)

Read the `publish_ready` stage from `readiness-status.yaml`. Fill exactly one branch:

- **`publish_ready: pass` with a named approval recorded** -- surface the recorded
  approval and cite the source:
  - **Recorded approval:** owner `<data_owner | governance>`, at `<YYYY-MM-DD>`
    (from `readiness-status.yaml` `approvals[]`, stage `publish_ready`).
  - **Publish-ready:** stated as ready, traceable to the recorded `pass` + approval.

- **`publish_ready` is NOT `pass`** (`not_started` / `blocked` / `warning`) -- show the
  status and the upstream blocking reasons; print NO publish-ready claim:
  - **Publish-ready:** `<the non-pass status>`.
  - **Upstream blocking reasons:** `<reasons read from readiness-status.yaml -- one per line>`.

In both branches: this summary wrote NO approval, moved NO stage to `pass`, and edited
NO source artifact. It only rendered this derived summary + the index.

## Rolled-up open blockers (across all 10 sections)

List every open blocker carried from the section index, each traceable to a committed
source. While any blocker is open, the pack CANNOT read "complete".

| Section | Blocking reason | Source it traces to | Named owner |
|---------|-----------------|---------------------|-------------|
| `<NN-section>` | `<concrete reason, e.g. "section source missing or unfilled">` | `<repo-relative source path>` | `<owner / UNASSIGNED>` |
| `<...>` | `<...>` | `<...>` | `<...>` |

A blocker with no named owner is shown `UNASSIGNED` and flagged; the generator never
self-assigns an owner. If there are no open blockers AND `publish_ready: pass` with a
recorded approval, the pack is complete; otherwise it is in-progress or blocked.

## Source disagreements surfaced for human resolution (Principle V)

If two upstream sources disagree, both are surfaced here (and in the index) as a
`warning` for the named human to resolve. The summary records the discrepancy; it does
NOT pick a winner or reconcile silently.

- `<source A path + value> vs <source B path + value> -- warning; awaiting <named human>`
- `<... or: none>`

## Stop-and-ask items (the human's call, never the pack's)

These are surfaced, never resolved by the generator (Principle V):

- Publish authorization (only the named human via Core Authority -- this pack surfaces
  the recorded state, never grants it).
- A grain / PII / rollup ambiguity or a sentinel-vs-null question carried up from a
  section source.
- Any source disagreement listed above.

## See also

- The 10-section index this summarizes: `evidence-pack-index.md`.
- The skill that composes this: `../.claude/skills/evidence-pack-generator/SKILL.md`;
  the tool doc: `../docs/tools/evidence-pack-generator.md`.
- The Core Authority state it surfaces (read-only): `mappings/<table>/readiness-status.yaml`;
  the four-status / no-fake-confidence model: `../docs/readiness/readiness-model.md`; the
  publish stage authority: `../docs/readiness/publish-ready.md`.
- The authority contract: `../docs/architecture/product-modules.md`;
  `../templates/module-contract.md`. A filled worked example is cited by reference
  under `../docs/worked-examples/`.
