# Quickstart: Business Knowledge Interview, Decision Store, and Knowledge Contracts

**Feature**: `specs/121-business-knowledge-interview` | **Date**: 2026-07-11

The end-to-end walk this feature enables, from a discovered database to an enforced
gate verdict. Paths follow research decisions R-3/R-4/R-5.

## 1. Start from discovery

A committed discovery profile exists (from `retail-onboard-table` Stage 1 or an
equivalent committed profile). Without it, the interview refuses to start.

## 2. Run the interview

Invoke the gated verb (`.claude/skills/business-knowledge-interview/`). The agent:

1. loads any existing Decision Store and presents prior decisions for confirmation;
2. proposes a **low-risk batch** (naming conventions, obvious display types) for one
   confirmation -- you may exclude any item, which becomes its own pending question;
3. asks **critical questions individually** (KPI meaning, PII, grain, keys,
   relationships, missing-value rules, ambiguous money/quantity/date columns), each
   grounded in profile summaries and masked samples;
4. records every outcome in the store -- nothing lives only in chat.

## 3. Inspect the Decision Store

```text
.seshat/semantic-decisions.yaml   # grain, PK, relationships, PII, exclusions, blueprint, publish
.seshat/kpi-contracts.yaml        # KPI meanings + VAT/returns/discount/cost policy rulings
.seshat/cleaning-rules.yaml       # missing-value + cleaning rulings (start from RC1-RC16)
```

Approved critical decisions carry full approval metadata (`approved_by` as
`"Name (authority_class)"`, `approved_at`, `source`, `evidence`,
`evidence_identity` captured at approval time, `reviewed_scope`).
High confidence is never approval. Approved records are immutable -- change happens
by supersession only.

## 4. Read the review artifact

`evidence/business-interview-review.md` -- regenerated deterministically from the
store: approved / pending / blocking / rejected / deferred decisions, PII handling,
KPI-impacting, grain and relationship, cleaning and missing-value decisions, the next
open questions, and the current gate verdict. Readable without opening YAML.

## 5. Ask for a gate verdict

Request readiness for a stage (e.g. Silver/Gold modeling). The verdict is
recomputed from the store + evidence:

- `pass` -- all required decisions approved and evidenced; proceed.
- `warn` -- proceed; listed non-fatal issues (e.g. stale evidence on a non-critical
  decision).
- `blocked` -- named unresolved decisions (e.g. `table_grain.fct-sales` pending) and
  what unblocks each.

`retail check` enforces the same truths statically (DS1-DS5): malformed records,
incomplete approvals, critical types in batches, in-place edits of approved records,
or a pass without evidence all fail the gate with a non-zero exit.

## 6. What comes later (not in this slice)

KPI contract production, Silver/Gold planning, semantic model + DAX, report intent,
dashboard blueprint, and the PBIP prototype (Blueprint -> Compiler -> Validation)
arrive in later slices -- each entered only when this slice's gates report pass.
