# PR Readiness Report -- the structured "is this PR safe to merge" verdict

> Feature F025 (on-disk spec `019-pr-readiness-reviewer`). When the spec-dir number
> and the F-number disagree, the roadmap F-number wins.
>
> GENERIC template -- the stable OUTPUT SHAPE the `pr-readiness-reviewer` skill renders
> for ONE pull request. It carries `merge_ready` + the explicit finding lists, each line
> traceable to an observed PR fact or a committed source. See
> `docs/tools/pr-readiness-reviewer.md` (when to run, field meanings) and
> `.claude/skills/pr-readiness-reviewer/SKILL.md` (the procedure that fills it).
>
> **Authority category (F024): Product Module / `read-only`.** This verdict is a READING
> of evidence, never an authority. It does not merge, approve, resolve a thread, edit a
> PR, or move a readiness stage -- those stay named-human / Core Authority actions
> (Principle V). The module presents and summarizes; it creates no truth.
>
> **Rendered EPHEMERALLY, not persisted.** The skill renders this shape to the operator
> (chat / stdout). Emitting the verdict is "presents / summarizes Core Authority"
> (`read-only` permits this) -- it is NOT "writes derived evidence". Running the reviewer
> writes NO tracked verdict file and creates no committed evidence artifact. Saving or
> posting the verdict is a separate, opt-in, human-triggered action OUTSIDE this module.
>
> **The gating rule (verbatim).** `merge_ready` is `no` while ANY `blockers[]` entry OR
> ANY open `required_human_decisions[]` entry exists; `warnings[]` do NOT alone flip
> `merge_ready`; `required_human_decisions[]` is a SEPARATE gating class from `blockers[]`
> and BOTH gate `merge_ready: yes`.
>
> **No fake confidence.** `merge_ready` is a DERIVED BOOLEAN ("no blocker and no open
> required-human-decision found in evidence"), never a numeric merge / confidence / health
> score and never an approval (roadmap rule #9). This template has NO score field; a
> filled copy MUST NOT add one. If asked for a number, the skill declines and cites
> rule #9.
>
> **Evidence traceability.** EVERY entry in `blockers[]`, `warnings[]`,
> `required_human_decisions[]` MUST cite its source -- a PR fact (PR number, check-run
> conclusion, thread / comment id) or a committed source (path + field / line). A finding
> with no traceable source is a defect.
>
> **Generic, not an instance.** Placeholders only; `retail_store_sales` is a filled
> instance CITED as a reference (a filled worked example under
> `docs/worked-examples/`), never inlined
> (Principle VII). ASCII only, UTF-8 no BOM; use `--` and `->` (no Unicode symbols, no
> smart quotes).

---

## Subject

| Field | Value |
|-------|-------|
| PR | `<#PR / owner/repo#NNN>` |
| Head SHA | `<short-sha>` |
| Reviewed on | `<YYYY-MM-DD>` |
| Reviewed by | `<agent / person>` (read-only) |
| Promotion the PR claims | `<e.g. advances <table> to <stage>, or "no readiness claim">` |

## Verdict

The verdict is EXACTLY these six fields -- nothing more (no summary, no status, no score):

```
merge_ready              : <yes | no>     # derived boolean; NEVER a number, NEVER an approval
blockers                 : [ ... ]         # each makes merge_ready: no; each cites a source
warnings                 : [ ... ]         # surfaced for the reviewer; do NOT alone flip merge_ready
required_human_decisions : [ ... ]         # Principle-V judgment items; each to a NAMED owner; an open one gates merge_ready
evidence                 : [ ... ]         # one line per observed input; each names its source
next_action              : "<single highest-value next step>"
```

`merge_ready: yes` REQUIRES zero `blockers[]` AND zero open `required_human_decisions[]`,
each observed line traceable to its source. A `pending` or `unknown` line is NOT treated
as `pass`.

## blockers[] (each present -> merge_ready: no)

A finding that, while present, makes `merge_ready` `no`. Each carries a cited source.

| # | Blocker (concrete) | Cited source (PR fact or path + field/line) |
|---|--------------------|---------------------------------------------|
| 1 | `<e.g. required check <name> conclusion=failure>` | `<check-run on head SHA <short-sha>>` |
| 2 | `<e.g. PR is still a draft>` | `<PR <#> state=draft>` |
| 3 | `<e.g. claimed approval absent from approvals[]>` | `<mappings/<table>/readiness-status.yaml approvals[]>` |
| 4 | `<e.g. secret-shaped string in diff>` | `<path:line in the PR diff>` |

## warnings[] (surfaced; do NOT alone flip merge_ready)

A finding surfaced for the reviewer that does not, by itself, flip the verdict.

| # | Warning (concrete) | Cited source |
|---|--------------------|--------------|
| 1 | `<e.g. unresolved informational review thread (no change-request)>` | `<review thread id on PR <#>>` |
| 2 | `<e.g. benign PR-body imprecision unsupported by evidence>` | `<PR body line vs committed source>` |

## required_human_decisions[] (Principle V; an open one -> merge_ready: no)

A judgment item the module SURFACES and routes to a NAMED owner. A SEPARATE gating class
from blockers. The module recommends; the human decides. The module never rules, never
self-resolves, never self-assigns. An item whose owner is not named is shown
`UNASSIGNED` and flagged.

| # | Judgment call | Named owner who must decide | Evidence prompting it |
|---|---------------|-----------------------------|------------------------|
| 1 | `<e.g. publish approval requested before <prior stage> is pass>` | `<named owner>` | `<readiness-status.yaml field showing <prior stage> != pass>` |
| 2 | `<e.g. PII publish-safety question>` | `<governance owner>` | `<the PII-derived column / claim>` |
| 3 | `<e.g. grain ambiguity / sentinel-vs-null / business rollup call>` | `<analyst>` | `<the ambiguous evidence>` |

## evidence[] (one line per observed input; each names its source)

Every verdict input is interpreted from one of these observed / read lines. A missing
source is recorded `unknown` with the missing source NAMED -- never an assumed `pass`.

| Verdict input | Source observed / read | Observed value | Default severity |
|---------------|------------------------|----------------|------------------|
| PR state (open / draft / closed) | the PR's own state | `<value>` | draft -> blocker; closed -> blocker |
| mergeability / conflicts | the PR's mergeable state + base divergence | `<value>` | conflicts -> blocker |
| CI / workflow conclusions | recorded check-run / workflow conclusions on head SHA | `<value>` | failing required check -> blocker; pending -> blocker for `yes` |
| open review threads | unresolved review threads on the PR | `<value>` | unresolved -> warning (blocker if change-requested) |
| Codex / GitHub review comments | unresolved review comments / findings | `<value>` | unresolved -> warning; unaddressed change-request -> blocker |
| tests declared vs run | PR-body claimed test plan vs recorded CI test result | `<value>` | declared-not-run -> blocker |
| no raw data committed | the PR diff file list vs the raw-data ignore policy | `<value>` | raw data present -> blocker |
| no secrets / no local paths | the PR diff scanned for secret-shaped / machine-path strings | `<value>` | present -> blocker |
| readiness-stage consistency | PR-body claimed stage vs `mappings/<table>/readiness-status.yaml` `current_stage` + per-stage `status` | `<value>` | mismatch -> blocker |
| approvals consistency | PR-body claimed approval vs `readiness-status.yaml` `approvals[]` (named owner + date) | `<value>` | missing / absent -> blocker |
| source-map approval metadata | `source-map.yaml` approval / mapping-gate CLEARED metadata (when the PR touches a mapping) | `<value>` | absent when claimed -> blocker |
| PR-body drift vs readiness | any PR-body claim unsupported by committed evidence | `<value>` | unsupported claim -> warning (blocker if it asserts a stage `pass`) |
| publish approval requested too early | a publish / merge-to-publish request while the required prior stage is not `pass` | `<value>` | too-early -> required_human_decision, and a blocker until resolved |

> Severity defaults above are the starting rule (Principle VI). A classification that
> deviates from the default is recorded WITH ITS REASON (e.g. an unresolved thread
> promoted to blocker because a reviewer marked change-requested) -- never silently
> promoted or demoted.

## next_action (one line)

The single highest-value step a HUMAN should take next. It NEVER instructs the module to
merge / approve / resolve / move a stage on its own.

> `<e.g. "mark ready for review", or "named owner <X> must decide the too-early publish
> request", or "fix the failing <check> then re-review">`

## Conflicting / missing / pending evidence (surfaced, never resolved)

| Situation | What the verdict records |
|-----------|---------------------------|
| Two sources disagree (PR body says stage `pass`; `readiness-status.yaml` shows `blocked` with an open reason) | SURFACE the conflict as a finding; do NOT resolve it by choosing one (Principle V) |
| A referenced `readiness-status.yaml` / `source-map.yaml` is absent | record the line `unknown` naming the missing source; do NOT assume `pass` |
| A required CI check is queued / in-progress | report `pending` (a blocker for `merge_ready: yes`); do NOT re-trigger or wait on CI |
| The PR touches no readiness artifact | record the readiness lines `unknown` / "not applicable: PR touches no readiness artifact"; do NOT fabricate a stage |

## See also

- The skill that renders this: `../.claude/skills/pr-readiness-reviewer/SKILL.md`;
  the tool doc: `../docs/tools/pr-readiness-reviewer.md`.
- The authority category it declares: `../docs/architecture/product-modules.md`
  (Product Module / `read-only`), the copy-me declaration:
  `module-contract.md`; the seam: `../docs/architecture/core-vs-modules-and-adapters.md`.
- The committed evidence it reads (inputs, unchanged): `readiness-status.yaml`
  (`current_stage`, per-stage `status`, `approvals[]`, `blocking_reasons[]`),
  `source-map.yaml` approval metadata.
- The closest read-only sibling: the portfolio roll-up `data-quality-control-room.md`
  (F012) -- F012 answers "which table is broken across the portfolio"; this answers "is
  THIS pull request safe to merge".
- The model + no-fake-confidence rule: `../docs/readiness/readiness-model.md`. A filled
  worked example under `../docs/worked-examples/` is a cited filled instance.
