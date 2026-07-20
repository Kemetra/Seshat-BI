---
name: business-knowledge-interview
description: >-
  After a database is discovered and profiled, interview the business owner to
  capture the meaning-critical decisions the rest of the Database-to-PBIP flow
  depends on -- KPI meaning, PII handling, table grain, primary keys,
  relationships, missing-value rules, and ambiguous financial/quantity/date
  columns -- and record every outcome in the project Decision Store. Use when
  someone asks to run the interview, capture business knowledge, or resolve the
  business questions behind a model in the Seshat BI repo. It asks obvious
  low-risk items as one batch and critical items individually with explicit
  named-human approval; it uses masked samples and never shows raw suspected PII
  by default; it records decisions and STOPS. It does NOT define metric contracts
  or DAX, does NOT self-grant any approval, and does NOT emit a confidence score.
---

# business-knowledge-interview

The interview is the front door of the Database-to-PBIP flow's decision layer
(spec 121). It converts a discovery profile into recorded, approvable business
decisions so that every downstream stage consumes governed answers instead of
unrecorded assumptions.

Behavior is governed by the contract
`contracts/interview/business-knowledge-interview.yaml`; the detailed protocol is
`specs/121-business-knowledge-interview/contracts/interview-protocol.md`. The
static rules DS1-DS5 (`seshat check`) verify the recorded outcome, not the
conversation.

## When to use

- After `retail-onboard-table` has produced a committed discovery profile (or an
  equivalent committed profile exists).
- Before KPI contracts, Silver/Gold planning, DAX, dashboard blueprint, or PBIP
  readiness -- those stages are blocked until their critical decisions are
  approved.

## Preconditions (stop if unmet)

- A committed discovery profile exists. **No profile => do not start**; report the
  gate as blocked naming the missing profile.
- Load the existing Decision Store first. Existing decisions are presented for
  confirmation or supersession -- **never overwritten**.

## How it runs

1. **Ground every question in the profile** (profile summaries, candidate grains,
   column types). Do not walk every column one-by-one unless the owner asks or an
   ambiguity requires it. Concentrate on: KPI inputs, PII, table grain, keys,
   relationships, missing-value rules, and ambiguous financial/quantity/date
   columns.
2. **Batch the obvious low-risk items** into one owner confirmation. Critical
   decision types are never in a batch. The owner may exclude any item; the
   remainder is approved in one action and each excluded item becomes an
   individual `pending` question.
3. **Ask critical decisions individually** with an explicit per-decision approval
   by a named human whose authority class is eligible for the decision type
   (`contracts/knowledge/approval-authority.yaml`). Route any KPI-*meaning*
   question to `retail-kpi-knowledge`; never invent meaning here.
4. **Mask suspected PII by default.** Show shape-preserving masks, cite the
   suspicion source. Unmasking requires an explicit owner instruction, recorded
   as a `pii_handling` decision scoped to the affected columns. Never write a raw
   suspected-PII value into a committed store file.
5. **Record every outcome in the Decision Store**
   (`.seshat/semantic-decisions.yaml`, `.seshat/kpi-contracts.yaml`,
   `.seshat/cleaning-rules.yaml`) -- answered => `proposed`/`approved`; refused =>
   `rejected`/`deferred`; unanswered => `pending`/`needs_user_input`; sample
   needed but unavailable => `needs_sample`. Confidence (`low`/`medium`/`high`) is
   the agent's proposal confidence only; it is never approval and never a
   readiness signal.

## Exit

Regenerate `evidence/business-interview-review.md` from the store and report the
current gate verdict for the next requested stage.

## Hard stops (never)

- Never self-grant an approval (Principle V; `never_self_grant_approval`).
- Never advance a readiness stage.
- Never emit a numeric confidence score (`never_fabricate_a_confidence_score`).
- Never display raw suspected-PII values by default, and never commit them.
- Never define a metric contract or DAX (that is the retail-kpi / DAX layers).
