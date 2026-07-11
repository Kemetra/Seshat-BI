# Contract: Business Knowledge Interview Protocol

**Feature**: `specs/121-business-knowledge-interview` | Anchors: FR-006 to FR-012, clarify Q4

The interview is agent-conducted conversation governed by this contract (R-8). Static
rules verify the recorded outcome in the Decision Store, not the conversation.

## Preconditions

- A committed discovery profile exists (Stage-1 read-only profile of
  `retail-onboard-table` or equivalent). No profile => the interview may not start;
  the verdict for it is `blocked` naming the missing profile.
- An existing Decision Store is loaded first; existing decisions are presented for
  confirmation or supersession, never overwritten (FR-012).

## Question construction (FR-006, FR-009)

- Every question cites discovery evidence: profile summary, candidate grain,
  column-type observation, or masked sample.
- Question effort concentrates on: KPI inputs, PII, table grain, keys,
  relationships/cardinality, missing-value rules, ambiguous financial/quantity/date
  columns. No column-by-column walk unless the owner requests it or unresolved
  ambiguity requires it.
- Bound (NFR-003): question rounds <= count of critical decisions + one batch round.

## Hybrid grouping (FR-007, FR-023, clarify Q4)

- **Batch**: obvious low-risk interpretations grouped into one reviewable set;
  critical decision types are NEVER batch members (DS3). The owner may exclude
  individual items; the remainder is approved in one confirmation, each excluded item
  becomes an individual `pending` question, exclusions are recorded with the batch.
- **Critical**: asked individually; explicit per-decision approval by a named human
  whose authority class is eligible for the decision type
  (`contracts/knowledge/approval-authority.yaml`).

## Masking (FR-008, R-9)

- Suspected-PII values display as shape-preserving masks by default; the suspicion
  source is cited.
- Unmasking requires an explicit owner instruction, itself recorded as a
  `pii_handling` decision scoped to the affected columns.
- Committed artifacts never contain raw suspected-PII values (FR-005).

## Recording obligations (FR-010, FR-011)

- Every outcome lands in the store: answered => `proposed`/`approved` per flow;
  refused => `rejected` or `deferred`; unanswered => `pending`/`needs_user_input`;
  sample required but unavailable => `needs_sample`.
- Pause/resume is safe: interruption approves nothing; unanswered questions persist
  as open statuses.
- Confidence (`low|medium|high`) is recorded on proposals and never presented to the
  owner as an approval or readiness signal (FR-016).

## Exit

The interview ends by regenerating `evidence/business-interview-review.md` from the
store and reporting the current gate verdict for the next requested stage. It never
self-grants approval, never advances a readiness stage, and never emits a numeric
confidence score.
