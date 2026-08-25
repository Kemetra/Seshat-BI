# Feature Specification: Answer Evidence Dates

**Feature**: 157
**Idea**: c35 -- Answer Freshness Header
**Status**: Ratified by owner Ahmed Shaaban on 2026-08-25

## Goal

Show readers the dates behind an answerability claim and the arithmetic distance
between them without emitting a freshness judgment, threshold, badge, or score.

## Functional Requirements

- **FR-157-001**: `templates/source-profile.md` MUST explicitly record the
  primary reporting-date column, observed coverage start, observed coverage end,
  and committed coverage evidence.
- **FR-157-002**: A non-temporal source or a source without defensible committed
  evidence MUST use a concrete `GAP`; the profile date MUST NOT substitute for
  data coverage end.
- **FR-157-003**: Existing filled source profiles MUST receive only facts already
  supported by their committed profile or fixture; no live query is authorized.
- **FR-157-004**: The answerability summary MUST show exactly three cited dates:
  data coverage end, `readiness-status.yaml:last_checked_at`, and the latest
  shape-valid `publish_ready` approval date.
- **FR-157-005**: The summary MAY state calendar-day differences, but MUST NOT
  label evidence fresh/stale/current/outdated/acceptable/unacceptable, define a
  threshold, render a traffic-light/badge/verdict, or emit a confidence score.
- **FR-157-006**: Missing or malformed dates MUST render a concrete `GAP` and
  MUST suppress arithmetic that depends on the missing fact.
- **FR-157-007**: The answerability summary remains optional and MUST NOT alter
  readiness state, publish approval, or any gate.
- **FR-157-008**: Generic templates MUST contain no C086, retail-specific schema,
  or concrete worked-example date.

## Acceptance Scenarios

1. A temporal source profile has explicit start/end dates and evidence; its
   answerability companion can cite data-through, audit, and approval dates.
2. A fiscal-period-only or unknown source records `GAP` instead of inventing a
   calendar coverage date.
3. A missing date produces a concrete sentence naming the unavailable arithmetic.
4. Documentation-contract tests reject judgment labels and concrete example data.

## Source Design

The approved architecture, exclusions, and lifecycle are defined in
`docs/superpowers/specs/2026-08-25-adopted-ideas-completion-design.md`.
