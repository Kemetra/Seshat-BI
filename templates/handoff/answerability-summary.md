# Stage 7 Answerability Summary (executive-readable)

**Table**: `<schema>.<table>`
**Source family**: `<source system / domain>`
**Assembled on**: `<YYYY-MM-DD>`  **by**: `<analyst / agent>`
**Audience**: sponsor / finance reader (an executive companion to the engineer-facing
`bi-handoff-pack.md` -- it does NOT restate the pack).

> **Not a Stage 7 required artifact.** This summary is an optional executive companion. It is
> NOT listed in Publish Ready's Required artifacts / Required checks / Blocking reasons, and it
> changes no Stage 7 pass condition.

## What this is / is not

- **Is**: a presentation over the human publish-approval seam. For each business decision
  question, it states -- in plain language -- whether the table answers it today and, if not,
  the specific named blocker.
- **Is not**: an approval. It grants no readiness, moves no stage to `pass`, and self-grants
  nothing (Principle V -- the publish sign-off remains an un-delegatable human action).
- **Status + named blocker only.** Every row carries a status and, when blocked, a specific
  named blocker (a missing field or a specific undecided policy). **No percentage, no score,
  no count-as-score ever appears** (hard rule #9).
- **Answerability, not publish-safety (FR-014).** "Answerable today" is an *answerability*
  statement only. It asserts **no publish-safety judgment**: no field is implied safe to
  expose by appearing in any list. This summary inherits the caveats-note PII-exclusion
  posture; publish-safety remains a human judgment.
- **Generic.** This template is schema-agnostic -- generic `<placeholder>` tokens and generic
  KPI/domain names only. Any concrete instance is reached ONLY by reference to
  a filled worked example under `../../docs/worked-examples/`, never copied inline.

## Answerable today

One row per **decision question** (an F7 domain-file row) whose KPI is **Covered** in F8
(contract **Seeded** AND every required field present). Answerability is never inferred from
field presence alone -- both halves must hold.

| Decision question | KPI | Contract | Coverage status |
|-------------------|-----|----------|-----------------|
| `<business question from an F7 domain file>` | `<KPI name>` | `contracts/<file>.md` | Covered |

> If nothing is Covered yet: **"None answerable today."** (Do not fabricate an answerable row
> from field presence; an empty list is the honest state.)

## Blocked -- pending decision

One row per decision question kept out of "Answerable today". Each row names its **specific
missing field** OR its **specific undecided policy** (e.g. `A1`-`A11` from `kpi-ambiguities.md`)
as the blocker -- never a softened adjective. This template resolves no policy. The list is a
**flat observed list with no severity/priority/rank ordering** (FR-015): list order carries no
meaning -- which blocker matters most is a human priority judgment.

| Decision question | KPI | Named blocker |
|-------------------|-----|---------------|
| `<business question>` | `<KPI name>` | `Blocked -- missing field: <field>` \| `Blocked -- needs business definition: <A#>` |

## Out of scope

Decision questions this table cannot serve (e.g. an inventory-turns question against a
sales-only fact) -- keyed on the **decision question** like the other lists, not rolled up to
the domain, so a table that serves some questions in a domain but not others still names the
specific unanswerable question.

| Decision question | Domain | Why out of scope for this table |
|-------------------|--------|---------------------------------|
| `<business question from an F7 domain file>` | `<domain>` | `<the table does not carry this question's grain/facts>` |

## Planned / not yet contracted

KPIs marked **Planned** in F8 (no seeded contract yet) -- surfaced here as a distinct note so
they are neither dropped nor miscounted as answerable.

| KPI | Note |
|-----|------|
| `<KPI name>` | Planned -- no seeded contract yet; nothing to cover. |

## Paper-answerable, not live-validated

"Answerable today" means the contract is **Seeded** and the required fields are present per the
F8 scorecard -- it is **paper-answerable, not live-validated**. No live publish path is assumed;
the Power BI execution adapter (F016) remains parked.

## See also

- Stage authority (non-gating reference back): `../../docs/readiness/publish-ready.md`
- Answerable-today source (F7 KPI Decision-Question Index, 12 domain files):
  `../../skills/retail-kpi-knowledge/domains/`
- Coverage-status source + the no-percentage discipline (F8 KPI Coverage Scorecard):
  `../../skills/retail-kpi-knowledge/references/kpi-coverage-scorecard-template.md`
- Undecided-policy source (`A1`-`A11`):
  `../../skills/retail-kpi-knowledge/knowledge/kpi-ambiguities.md`
- The engineer-facing sibling this summary sits beside (referenced, not restated):
  `bi-handoff-pack.md`
- A filled concrete instance (a worked example):
  a filled worked example under `../../docs/worked-examples/`
