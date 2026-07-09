# Ratify Ledger -- Personal-Data-Touch Notice (spec 114)

**Status: AWAITING HUMAN RATIFICATION.** This is the stop point of the
idea-to-spec chain. The chain DEFINED and CHECKED the feature; it did NOT
approve, implement, or merge. Ratification is a named-human action the agent is
structurally forbidden to self-grant (Principle V). No `silver.*`/runtime code
was written; this branch carries spec + plan + tasks only.

## What was produced

Branch `114-pii-touch-notice`, spec dir `specs/114-pii-touch-notice/`:

- `spec.md` -- feature spec, 2 clarifications resolved, 14 FR + 6 SC, 3 user
  stories, scope wall.
- `plan.md` -- Constitution Check PASS (9/9 + hard rule #9); Python-composer
  structure decision.
- `research.md` -- 5 decisions (D1 vehicle, D2 enforcement, D3 source, D4
  undecided-definition, D5 idioms).
- `data-model.md`, `contracts/composer.md`, `contracts/verifier.md`,
  `quickstart.md`.
- `tasks.md` -- 17 TDD-ordered tasks, 6 phases; MVP = US1.
- `checklists/requirements.md` -- specify-phase quality checklist (all pass).

## Provenance

Idea #3 from the 2026-07-08 idea bank ("Personal-Data-Touch Notice"), CONSIDER,
V5/F8. Adversarially verified net-new + principle-eligible against `main`
@ 84d05c8 on 2026-07-09 (12-agent workflow, all 6 skeptic verdicts
refuted=false). Fills F040 consumer-data-dictionary's own declared PII exclusion
(its FR-010) rather than competing with it. Grounded on the committed fixture:
`retail_store_sales/source-map.yaml` L69 `customer_id` `pii:true, decision:keep`
+ RC4 disposition, rendered by no shipped surface.

## Key decisions the ratifier is signing off on

1. **Vehicle: Python composer** (`src/retail/pii_notice.py` + CLI verb), NOT
   skill-only. Chosen because FR-011 needs a MECHANICAL guarantee a prose skill
   cannot give. (Alternative on record: skill + external verifier.)
2. **Enforcement: a decoupled unit-test verifier**, NOT a `@register` retail
   check rule -- adding a gate would violate the feature's own FR-007. The
   mechanical guarantee lives in the test suite.
3. **Disposition source: `source-map.yaml` only** (Clarification Q1);
   `unresolved-questions.md` not parsed. FR-010 is an intra-file check.
4. **Output: `mappings/<table>/pii-touch-notice.md`** (Clarification Q2),
   mirroring F040's co-located output.

## Open items flagged for the ratifier (from the plan/advisor)

### OPEN-1 -- Vehicle (Python vs skill-only)

- If the ratifier prefers to KEEP the feature skill-only (F040 posture), that
  consciously downgrades FR-011 from a mechanical guarantee to prose enforcement.
  The spec as written assumes the mechanical (Python) path. Confirm the Python
  vehicle, or direct the skill-only downgrade here.

### OPEN-2 -- The column->disposition JOIN (SAFETY-CRITICAL; needs a ruling before implement)

The kept-PII disposition string lives in the table-level `defaults.deviations[]`
block, keyed by RC-id (`RC4`, `RC8`, ...), NOT by column. In the committed
`retail_store_sales` fixture there is NO structured field linking `customer_id`
to RC4 -- the only linkage is FREE TEXT: the string "customer_id" appears inside
`RC4.reason`, and "RC4" appears inside `customer_id.reason`. Two consequences the
ratifier must rule on:

1. **How does a column claim its deviation?** Options:
   - (a) **Explicit link** -- add a structured field (e.g. `deviation_ref: RC4`
     on the column, or `applies_to: [customer_id]` on the deviation) to the
     source-map schema + template. Deterministic, but TOUCHES the source-map
     schema and Principle VII genericity (new generic field, back-fill the
     fixture). Recommended for safety.
   - (b) **Text heuristic** -- match the column name inside a deviation `reason`
     (and/or the RC-id inside the column `reason`). No schema change, but carries
     a real FALSE-POSITIVE risk: a wrong join makes an UNGOVERNED PII column read
     as CLEARED -- the exact Principle-V hazard this feature exists to prevent.
   The undecided->GAP trigger (US2, the safety half) IS "no disposition
   reachable", so the join rule directly decides what renders as a safe GAP vs a
   false clearance.

2. **Which field is the disposition -- the column's `reason` or the deviation's
   `reason`?** They differ: the promised verbatim quote "...(data owner): keep,
   no raw PII" lives ONLY in `RC4.reason` (quickstart.md assumes this). "disposition
   = column.reason" makes that promise unproducible; "disposition = deviation.reason"
   requires resolving OPEN-2.1. Pin one.

**Why this matters and why it's here, not resolved:** V1 (verbatim-substring)
does NOT catch a mis-join -- a wrongly-attributed disposition is still a verbatim
substring of *some* committed field. The chosen Python/verifier guarantee sits
OUTSIDE the attribution logic. So the plan MUST, once OPEN-2 is ruled:
(i) define the join rule in data-model.md/research D3, and (ii) add a join-
CORRECTNESS assertion to the verifier (contracts/verifier.md V7 below), since
V1 alone is insufficient. This is a Principle-V / schema question -- a named
human's ruling, not an agent default.

## Analyze outcome

0 CRITICAL, 0 HIGH. 100% semantic requirement coverage. 0 constitution
violations. 4 LOW nits (optional id-tag traceability; denylist enumerated in
verifier.md not spec.md) -- none blocking.

## Ratification

- [x] **RATIFIED** by: Ahmed Shaaban (repo owner) on 2026-07-09.
- Ratifying means: the spec/plan/tasks are approved to proceed to
  `/speckit-implement` (or the equivalent build) on this branch.
- Until this box is checked by a named human, no implementation begins.

### Owner rulings (2026-07-09)

- **OPEN-1 (vehicle): Python composer + unit-test verifier.** As specced;
  FR-011 stays a mechanical guarantee. Skill-only rejected.
- **OPEN-2 (join, safety-critical): EXPLICIT `deviation_ref` field.** A kept-PII
  column claims its governance disposition via a NEW structured
  `deviation_ref: <id>` field on the column, joined by EXACT id-match to
  `defaults.deviations[].id`. No text heuristic. Disposition text = the matched
  deviation's `reason` (authoritative). A `pii: true` column with no
  `deviation_ref` (or a `deviation_ref` matching no deviation) is `undecided`
  (GAP), never a guess.
  - **Scope consequence (owner-accepted):** implementation ADDS the
    `deviation_ref` field to `templates/source-map.yaml` (generic, Principle VII)
    and back-fills the `retail_store_sales` fixture
    (`mappings/retail_store_sales/source-map.yaml`: `customer_id` gains
    `deviation_ref: RC4`). So #114 now edits two committed source-map artifacts,
    not only new files. V7 becomes: assert the rendered disposition's deviation
    id == the column's `deviation_ref` (exact match).
