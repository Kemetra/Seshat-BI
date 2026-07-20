---
name: report-intent-interview
description: >-
  Given approved metric contracts and a ready semantic model, interview the
  report requester to capture what a dashboard report is FOR -- audience,
  purpose, supported decision, review cadence, primary business questions,
  outcome/driver/guardrail metrics (referenced by name only, never defined),
  comparisons, dimensions/filters, expected actions/exceptions, pages/drill
  paths, and mobile/accessibility/language/RTL needs -- and record the result
  as a committed Report Intent artifact plus a named-human
  `report_intent_approval` decision. Use when someone describes a report they
  need in plain language, before any page blueprint, visual spec, or report
  composition is authored. It asks obvious low-risk items as one batch and
  critical items individually with explicit named-human approval; it masks PII
  by default; it records the intent and STOPS. It does NOT define metric
  meaning, does NOT self-grant any approval, and does NOT emit a confidence
  score.
---

# report-intent-interview

The Report Intent Interview is the missing front end of the dashboard
intelligence journey (spec 123, US1). It converts a conversational report
request into a committed, reviewable `report-intent.yaml` so every downstream
artifact (blueprint, composition, preview, audit, PBIR) traces back to a clear,
approved report purpose instead of an unrecorded assumption.

This skill mirrors `.claude/skills/business-knowledge-interview/SKILL.md`
structurally (load-existing-first, batch/critical question grouping, PII
masking, record + STOP, never self-grant) but does NOT extend it: the
`required_inputs` and `focus` differ. Behavior is governed by the contract
`contracts/interview/report-intent-interview.yaml`; the shape of the produced
artifact is `templates/report-intent.yaml`. The static rule DL9
(`seshat check`) verifies the recorded artifact's SHAPE, not the conversation.

## When to use

- Someone describes a report they need in plain language ("I need a weekly
  report for branch managers to spot underperforming branches").
- Before `dashboard-design`, the dashboard coordinator, page blueprints, visual
  specs, or report composition -- those stages trace their `business_question`
  back to a question declared here (FR-002a) and are blocked until this
  intent's own `report_intent_approval` decision is approved.

## Preconditions (stop if unmet)

- Approved metric contracts exist for the subject area (`readiness.status:
  pass`). **No approved contract for a metric the request needs => record a
  gap, route upstream to metric-contract definition, and leave the intent
  blocked on that metric (FR-004)** -- never define the metric here.
- The semantic model is ready (`semantic_model_ready: pass`). Not ready => stop,
  name the missing readiness, and do not proceed to design.
- Load the existing Report Intent (if any) first. An existing intent is
  presented for confirmation or supersession -- **never silently overwritten**.

## How it runs

1. **Ground every question in the request and the approved contracts.** Focus
   on: audience, purpose, supported decision, review cadence, primary business
   questions, metric roles by name (outcome/driver/guardrail), comparisons,
   dimensions and filters, expected actions and exceptions, pages/drill paths,
   mobile/accessibility/language/RTL needs, and exclusions/non-goals.
2. **Refuse to commit a vague request.** "Build an executive dashboard" gets
   focused disambiguating questions; the intent is NOT committed until
   `audience`, `purpose`, and at least one primary `business_questions` entry
   are resolved (US1 AC#4).
3. **Batch the obvious low-risk items** into one owner confirmation (e.g.
   comparison phrasing, filter defaults). Critical decision types are never in
   a batch. The owner may exclude any item; the remainder is approved in one
   action and each excluded item becomes an individual pending question.
4. **Ask critical decisions individually.** The intent's own approval
   (`report_intent_approval`) is a critical decision type, authority class
   `report_owner` (`contracts/knowledge/approval-authority.yaml`); it requires
   an explicit, per-decision approval from a named human -- the agent never
   self-grants it (Principle V).
5. **Reference metrics by name only.** Every `outcome_metrics` /
   `driver_metrics` / `guardrail_metrics` entry names an approved metric
   contract (`name` + `store_ref` + `status_required: pass`) -- the same triple
   shape as `dashboard-page-blueprint.yaml`'s `required_metric_contracts`.
   There is no formula/DAX field. A metric with no approved contract is a gap:
   record it, route it upstream, and leave the intent `blocked` on that metric
   -- never invent the metric here.
6. **Mask suspected PII by default.** Any PII-adjacent dimension/filter follows
   the shipped masking behavior; unmasking requires an explicit owner
   instruction, recorded as a `pii_handling` decision.
7. **Record the artifact and the decision.** Write
   `mappings/<subject-area>/design/report-intent.yaml` per
   `templates/report-intent.yaml`, and record the `report_intent_approval`
   decision in the project Decision Store once a named human of authority
   class `report_owner` approves. Unanswered items stay `pending` /
   `needs_user_input`; a metric gap stays `blocked` with a matching
   `blocking_reasons` entry.

## Exit

Report the current gate verdict for the `report_intent` stage
(`contracts/report/report-intent.yaml`) and the next allowed stage
(`dashboard_blueprint`) -- which stays blocked until this intent's
`report_intent_approval` is valid (an unapproved intent yields `blocked`, never
a false `pass`).

## Hard stops (never)

- Never self-grant `report_intent_approval` (Principle V;
  `never_self_grant_approval`).
- Never advance a readiness stage.
- Never emit a numeric confidence score (`never_fabricate_a_confidence_score`).
- Never define metric meaning here (route to `retail-kpi-knowledge` /
  the metric-contract layer).
- Never display raw suspected-PII values by default, and never commit them.
- Never invent a metric contract to make a reference resolve; record the gap
  and leave the intent blocked instead (FR-003/FR-004).
