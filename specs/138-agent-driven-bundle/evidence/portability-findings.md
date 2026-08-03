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

## T049 — the gate rejects, but its finding set is 2x the reviewed baseline

**Measured** 2026-07-31 with `seshat.portability_audit.audit_skill_text` over the
ten `.seshat/kit-source.yaml` verbs at HEAD `3e96af9`:

```text
findings                        87
distinct (skill, path) pairs    71
  of which under `.seshat/`      4   <- ambiguous, see below
  excluding `.seshat/`          67
classified read-instruction      8
classified provenance pointer   79
```

The transform **rejects before it permits**, which is what T049 requires. But the
T003 baseline above enumerates **33** distinct pairs, and the gate finds 71. Two
gate defects accounted for part of the gap and are fixed: a token of only
separators (`///`) was treated as a path, and a bare `warehouse/` reference was
flagged even though `_EMPTY_DIRS` carries `warehouse/migrations`, making
`warehouse/` an ancestor the scaffold demonstrably creates.

The remaining gap is **not** a gate defect. It is an unresolved question the
contract does not answer:

### Where the gap actually comes from — measured, and one hypothesis refuted

The obvious hypothesis was that "present" should include paths the **bundle**
ships: the bundle root carries `templates/`, `contracts/`, `design/`, `knowledge/`,
`commands/` and `skills/`, and the allowlist targets 7 entries under `templates/`,
so a skill reading `templates/readiness-status.yaml` might resolve it inside the
bundle it arrives in.

**Refuted by set difference.** Of the 46 gate pairs not covered by a baseline row,
only **8** fall under a bundle-shipped prefix. The other 38 do not:

| Extras not in the baseline | Count | Assessment |
|---|---:|---|
| `docs/…` (playbook, readiness, architecture, decisions) | 21 | almost certainly REAL findings the hand enumeration missed |
| `.specify/memory/constitution.md` | 4 | real -- a development-repository path |
| `.seshat/*.yaml` | 4 | ambiguous, see below |
| glob patterns (`**/.pbi/localSettings.json`) | 2 | **gate defect** -- a glob is not a read-instruction |
| PBIP internals (`definition/`, `.pbi/`) | 3 | **gate defect** -- relative to a `powerbi/` model folder, not repo-relative |
| `warehouse/<other>` sub-paths | 2 | real -- only `warehouse/migrations` is scaffolded |
| cross-skill relative refs (`../readiness-viewer/SKILL.md`) | 2 | real -- baseline findings 3/11/12/24 note this class |

So the bundle-presence reading explains 8 of 46, not the gap. The likelier
explanation is the opposite of a gate defect: **the T003 baseline of 33 is
incomplete.** It was enumerated by hand, and 21 `docs/` references plus the
`.specify/` constitution pointer were missed. A programmatic gate finding more than
a hand count is the expected direction.

**Two genuine gate defects remain** (5 pairs): glob patterns and PBIP-internal
relative paths are being read as repo-relative paths. Both are narrow and fixable
without touching the intent rules.

### RULED — adopt the agent's recommendation on both questions

- **ruled_by**: Ahmed Shaaban (owner)
- **ruled_on**: 2026-07-31
- **recorded_by**: the agent transcribed an owner-directed authorisation ("do all
  recommended, I authorize you") given after both questions and the agent's
  reasoning on each were presented in full. It did not self-grant (Principle V).

1. **The measured set supersedes the hand-enumerated 33.** The gate's output is
   authoritative; the T003 table stands as the reviewed subset it was, and the
   contract's "Known scope at authoring time: 33" is restated as a point-in-time
   count rather than a target. T050–T054 cover the `docs/` and `.specify/` classes
   too.
2. **`.seshat/*.yaml` references count as PRESENT.** `retail init` bootstraps that
   substrate, so a real consumer workspace has it; treating it as absent would
   force rewrites that make shipped skills *less* accurate. The gate derives this
   from the bootstrap verb rather than extending `_EMPTY_DIRS`, which stays exactly
   as `init-project` specifies it.

### The two questions as they were put

1. **Is the reviewed baseline of 33 superseded by the measured 66?** If yes, T050–T054
   grow to cover the `docs/` and `.specify/` classes, and the contract's "Known scope
   at authoring time: 33" line should be restated rather than quietly outgrown.
2. **Do `.seshat/*.yaml` references count as present?** Those files are bootstrapped
   by `retail init`, not by `init-project`, so a real consumer workspace has them
   while `_EMPTY_DIRS` does not list them. 4 pairs turn on it.

**Not resolved here.** The gate implements obligation 5 literally — presence is
`_EMPTY_DIRS`, nothing more — and the conflict is recorded rather than settled by
adopting whichever reading makes a number match
(`never_fabricate_a_confidence_score` / `never_self_grant_approval`).

Wiring the gate into the export (T047/T048) is deliberately NOT done: a wired gate
would block every export on a finding set nobody has reviewed. If a future change
does derive presence from what the bundle ships, note the direction — the audit
consumes the allowlist, never the reverse, or the derivation and the gate become
circular.

## T050-T056 — rewrite progress, measured after each file

Every count below is the gate's own output, re-run after each file.

| Gate run | Findings | Verbs clear |
|---|---:|---:|
| first measurement | 87 | 1 / 10 |
| after 2 gate defects fixed (`///`, `warehouse/` ancestor) | 74 | 1 / 10 |
| after `kpi-contract-builder`, `retail-validate`, `retail-build-warehouse` | 61 | 4 / 10 |
| after the `.seshat/` normalisation fix | 55 | 4 / 10 |
| after `business-knowledge-interview`, `source-mapping`, `retail-orchestrate` | **39** | **7 / 10** |

**Cleared**: `retail-discover-portfolio` (already clean), `kpi-contract-builder`,
`retail-validate`, `retail-build-warehouse`, `source-mapping`,
`retail-orchestrate`, `business-knowledge-interview`.

**Remaining**: `retail-govern` (16), `retail-onboard-table` (12),
`first-hour-compass` (11).

### A third gate defect, found by the ruling not taking effect

The `.seshat/` ruling appeared to do nothing. Cause: `_is_present` normalised with
`str.lstrip("./")`, which strips *every* leading dot and slash — turning
`.seshat/semantic-decisions.yaml` into `seshat/semantic-decisions.yaml` and
defeating the dotted-prefix comparison. Replaced with a regex that strips only
leading `./` and `../` segments. That alone cleared 6 findings, and it was only
visible because the ruling's effect was measured rather than assumed.

### Rewrite forms used (FR-017, by intent)

* **Name the CLI verb** — `src/seshat/validate.py` + `validate_targets.py` become
  "the checks and their target sourcing both run inside `retail validate`".
* **Name the module symbol, not its path** — `src/seshat/kpi_contracts.py` becomes
  the shipped `kpi_contracts` engine. The file already used this idiom.
* **Name the skill, not its file** — `.claude/skills/retail-orchestrate/SKILL.md`
  becomes "the `retail-orchestrate` skill", following the in-repo precedent at
  `retail-validate` line 87 ("the static sibling: the `retail-govern` skill").
* **Name the knowledge base, not its repo path** —
  `skills/retail-kpi-knowledge/registry.yaml` becomes "the `retail-kpi-knowledge`
  registry", which is also more correct in a bundle (where it lands under
  `knowledge/`).
* **Drop the path, keep the claim** — every `specs/…`, `docs/…` and
  `.specify/memory/constitution.md` provenance pointer.

### T056 — no hard stop weakened

Verified by diffing each rewritten file and filtering for hard-stop language
(`NEVER`, `MUST`, `STOP`, `HARD`, refusal, self-grant, approval). Across all six
rewritten files exactly one such line appears in a diff: `kpi-contract-builder`'s
"It does NOT reimplement contract authoring", whose clause is byte-identical on
both sides because only the trailing parenthetical changed. The approval-authority
constraint
at `business-knowledge-interview` line 55-57 ("an explicit per-decision approval by
a named human whose authority class is eligible for the decision type") was
preserved verbatim; only the repo path in its parenthetical was replaced.

### T047/T048 — the gate is WIRED, and the export passes again

`portability-audit-v1` is now enforced inside `scripts/export_agent_bundles.py`
(`_gate_portability`) and declared in both `ALLOWED_TRANSFORMS` and the derived
`policy.transforms`. It is applied to **every** shipping `SKILL.md` rather than
only to entries that declare it, so US4's additions are gated automatically
(obligation 6) without a transform becoming a content rewriter.

`python scripts/export_agent_bundles.py --repo .` now reports
**"PASS: generated Claude and Codex bundles match reviewed inputs"**, having first
rejected 5 genuine references in the currently-shipping skills, each fixed by a
reviewed rewrite:

| Skill | Reference | Rewrite |
|---|---|---|
| `bi-sql-knowledge` | `docs/readiness/` | named "the readiness spine" |
| `seshat-bi` | `docs/quality/conformed-dimension-map.yaml` | instruct creation |
| `seshat-bi` | `dbt/models/marts/<table>/` | named the adapter that generates it |
| `powerbi-workflows` | `templates/page-intent.example.yaml` | "the page-intent example the kit ships" |
| `powerbi-workflows` | `docs/tools/dashboard-gap-detector.md` | named the guide |
| `dagster-workflows` | `orchestration/dagster/run-evidence/<run-id>.md` | "written by that verb" |

### Seven gate defects, each found by measurement rather than by a passing test

The nine unit tests were green throughout. Every one of these was found by running
the gate against real content and comparing against a reviewed expectation:

1. `///` — a token of only separators treated as a path.
2. bare `warehouse/` — flagged although `_EMPTY_DIRS` carries
   `warehouse/migrations`, making it an ancestor the scaffold creates.
3. `str.lstrip("./")` — strips the leading dot from `.seshat/x`, so the owner's
   "`.seshat/` is present" ruling silently had no effect.
4. PBIP internals (`definition/`, `.pbi/`) — Power BI defines that structure inside
   the scaffolded `powerbi/`; they are not repo-relative.
5. Bundle-internal references — the knowledge wrappers point at
   `../../knowledge/<base>/INDEX.md`, correct in the delivered artifact. Presence is
   now taken from the allowlist's destination paths (audit consumes the allowlist,
   never the reverse).
6. A skill's own subdirectories — `references/foo.md` resolves against **where the
   file lands**, which differs between knowledge bases (`knowledge/<base>/`) and kit
   skills (`skills/<name>/`), so the destination is passed in rather than guessed.
7. Per-line exemption — markdown wraps, so "…is written by that verb as" and the
   path it scopes sat on different lines. Exemption is now judged over the wrapped
   sentence, stopping at sentence-final punctuation or a table pipe so one bullet
   cannot exempt its neighbours.

Also narrowed: a versioned contract identifier (`seshat.binding-map/v1`) is a
schema name, not a path.

**One deliberate broadening, with its boundary pinned.** Obligation 3's "names an
output a scaffold step produces" is matched by the production verbs (`writes`,
`generated`, `materialized`, `creating`) rather than a closed list of phrases —
this cleared 7 of the 12 export blockers. Taken alone it would be *looser*, not
more accurate: "read `docs/x.md`, generated last quarter" would be excused by an
incidental word. So **a read verb beats a production verb** — a sentence that
instructs a read is never exempted by naming a producer. Pinned by
`test_an_incidental_production_word_does_not_excuse_a_read_instruction`, because
this is the only change in the session that widened the gate rather than
correcting a false positive.

### The remaining cost of option 2, measured

With the gate correct, the 32 skills the inventory marks `ships: true` but the
bundle does not yet carry hold **347** findings across 28 skills:

| Prefix | Findings |
|---|---:|
| `docs/…` | 117 |
| `templates/…` | 74 |
| `specs/…` | 27 |
| `.claude/…` | 24 |
| `src/…` | 22 |
| everything else | ~83 |

Densest: `approval-evidence-pack` (36), `dagster-orchestration-adapter` (30),
`readiness-viewer` (23), `evidence-pack-generator` (22), `approval-console` (20),
`cross-table-lineage` (20), `powerbi-dashboard-design` (20).

**This is the number the option-2 ruling did not have.** The ruling was taken on
the understanding that US3+US4 payload would be folded in; the measured cost of
that fold is 347 reviewed rewrites across 28 governance-critical skill files, on
top of the 10 compass verbs already done. The owner may wish to revisit option 1
with this figure in hand — recorded here as a fact, not as a re-litigation.

### A third path, measured: ship US3 now, defer US4

With the gate corrected, the remaining cost splits cleanly along the story
boundary the specification already drew:

| Scope | Skills in bundle | Portability findings | Routing cost vs 6,000 |
|---|---:|---:|---|
| today (committed) | 11 | 0 | 579 |
| **US3 only** (knowledge roots + the ten compass verbs) | **21** | **0** | ~2,224 |
| US2+US3+US4 (option 2 as ruled) | 43 | **301** | ~5,698 after the trims |

The middle row was measured by deriving the allowlist with the 22
`consumer-capability` entries set to `ships: false` and auditing every resulting
skill: **21 skills, zero findings.** It is shippable immediately, and it fixes the
feature's headline defect — the compass named ten verbs the agent is told to drive
and both bundles carried none of them.

Option 2 as ruled remains 301 reviewed rewrites away from an export that runs at
all, spread over 21 skills (`approval-evidence-pack` 36,
`dagster-orchestration-adapter` 29, `readiness-viewer` 23,
`evidence-pack-generator` 21, `cross-table-lineage` 19, `approval-console` 18,
`retail-semantic-check` 17, `consumer-data-dictionary` 16, and 13 more).

### RULED — ship US3 now, defer US4

- **ruled_by**: Ahmed Shaaban (owner)
- **ruled_on**: 2026-07-31
- **recorded_by**: the agent transcribed an owner-directed ruling made after the
  301-rewrite measurement was presented against the original option-2 estimate. It
  did not self-grant, and it did not flip the flags before the ruling (Principle V).

The 22 `consumer-capability` entries are `ships: false`; the 6 knowledge roots and
10 compass verbs ship. **This supersedes the option-2 portion of correction 4** —
the option-2 ruling was taken on an estimate ("a large diff, 1,253 tokens over
ceiling") that measurement showed to be wrong by an order of magnitude.

**Delivered state:**

```text
bundle skills            11 -> 21   (both harnesses, identical sets)
allowlist entries        216 -> 227  (derived; 10 authored non-skill entries preserved)
portability findings     0
routing cost             2,224 / 6,000 ceiling   (T059 PASSES)
seshat check             exit 0, 0 errors, 1 pre-existing warning
kit-lint                 no projection drift
export                   PASS: bundles match reviewed inputs
test suite               4,914 passed, 27 skipped, 0 failed
```

The three tests that had been RED are green: the inventory and the artifact now
tell one truth, and `.seshat/kit-source.yaml`'s ten verbs are all present in both
bundles — the feature's headline defect is closed.

**Two derivation bugs the ship surfaced**, both fixed:

1. The derivation dropped the **10 authored non-skill entries** (fillable templates,
   the design grid, the interview handoff contract, the licence). The inventory
   classifies *skills*, so it cannot be their authority; they are now carried
   through from the committed allowlist and ordered by source, with `entry_id`
   reassigned across the whole list for determinism. Caught by
   `test_repository_allowlist_has_literal_reviewed_entries`.
2. `first-hour-compass`'s frontmatter `description` was an unparseable plain YAML
   scalar — it contains `: ` — so strict parsers rejected it. It had never mattered
   because the skill had never shipped. Converted to a folded block scalar; all ten
   compass frontmatters now parse.

A third, non-obvious one: `derive_allowlist` reads the committed allowlist for the
sections it preserves, so regenerating from an already-stripped file compounds a
drop. Verified fixed — `derive_allowlist` is now **idempotent against its own
output**, which is what obligation 6 requires in practice.

Also required by the ship, and done: the ten verbs are declared in
`distribution/public-command-surface.yaml` (their wrapper IS the canonical skill
body, vendored directly rather than via a bundle template, because FR-019 requires
every hard stop to still stop), the router skill routes to all ten in flow order,
and one markdown link escaping the bundle
(`[ADR 0003](../../../docs/decisions/…)`) was delinked — a class the portability
audit does not see, since it only inspects backticked paths, but the exporter's own
`_validate_links` does.

**US4 was open at this checkpoint** with its measured cost: 301 rewrites across
21 consumer skills.

### OWNER AMENDMENT — defer US4 into a separate future specification

- **ruled_by**: Ahmed Shaaban (owner)
- **ruled_on**: 2026-08-03
- **recorded_by**: the agent transcribed the owner's explicit authorization; it
  did not self-grant the decision.

T061–T064 and FR-020 are removed from spec 138's completion scope and remain
unimplemented. Their measured portability and routing-cost evidence is preserved
here as input to a separately designed and ratified future specification. The
current inventory remains truthful (`ships: false` for those capabilities), and
the committed bundles remain the identical 21-skill US3 artifacts. No future
specification identifier is reserved by this amendment.

### Known gate coverage gaps (not defects, but recorded)

1. **Brace expansions are invisible.** `retail-orchestrate` line 165 carried
   `` `.claude/skills/{a,b,c}/SKILL.md` `` — the candidate pattern has no `{` in its
   charset, so the gate never saw it. It was rewritten anyway, on inspection.
2. **A bare top-level directory is not a candidate**, by the two-segment rule that
   removes `definition/` and `.pbi/` false positives. "Read the files in
   `templates/`" would therefore pass. No reference in the reviewed set is affected.

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
