# Contract: the export and disclosure boundary (spec 141)

This is the security contract of spec 141. Where spec 140's core was a *write* boundary
(writing a decision is not granting one), 141's core is a **disclosure** boundary: every
surface here takes internal truth and shows it to someone with less context -- a client,
or a maintainer holding a support bundle.

Reviewers should read this file first.

## The claim this contract makes

**A view may narrow what is shown. It may never soften what it means, and it may never
widen who can see it.**

Three distinct failures follow from getting this wrong, and they need distinct guards:

| Failure | Example | Guard |
| --- | --- | --- |
| Softening | `pending commit` rendered as "approved" | O1 |
| Leaking | a DSN inside an exported narrative | O2, O3 |
| Acting | a "recovery action" button that repairs | O4 |

## Obligations

### O1 -- Pending stays pending

A decision in `pending commit` MUST render as pending in every Operations and Client
Review surface and export. A blocked fact MUST render as blocked.

*Rationale*: spec 140 made the false claim unrepresentable **on the write side** --
`RECEIPT_STATES` is a single-member tuple. That guard does not extend here: a
presentation layer can display whatever it likes without touching the receipt. This is
the render-side counterpart, and it needs its own test.

### O2 -- Allowlist, never denylist

Support bundles and client exports MUST be assembled from an explicit allowlist of safe
fields and files.

*Rationale*: a denylist fails open on the field nobody enumerated. Every new upstream
field is disclosed by default until someone notices. An allowlist fails closed: a new
field is absent until someone adds it deliberately.

### O3 -- Two redaction layers, applied to the assembled artifact

Every export MUST pass through `redaction.scrub_payload` **and** the secret-shaped scrub
before finalization, applied to the assembled content rather than at each construction
site.

*Rationale*: this repo's own lesson -- `redact()` alone is layer one, and a bare tenant
GUID passes through it. Applying at the assembly point means a field added upstream later
is covered without a second change.

### O4 -- Recommend, never repair

A diagnostic MAY name a recovery action. It MUST NOT execute one outside the existing
technical-approval and readiness policy.

*Rationale*: a support surface that can fix things is a mutation surface with a friendly
name. The approval boundary must not be reachable by a different door.

### O5 -- Atomic bundle, aborting scan

Bundle creation MUST be atomic, and a redaction-scan failure MUST abort it.

*Rationale*: a partially scrubbed archive is worse than none, because the recipient
assumes it was scrubbed.

### O6 -- No aggregate score

No surface, payload, or export may compute or display an aggregate health, maturity,
confidence, or readiness score. The model has no field for one.

### O7 -- Durable claims cite committed state

A record presented as durable MUST carry a committed source reference. An uncitable
record is `ephemeral`.

### O8 -- Acknowledgement is not approval

`ClientAcknowledgment` MUST NOT be capable of carrying a decision answer, and MUST NOT
route through the decision-recording path. A scoped business answer uses spec 140's
existing route.

## Verification -- how a reviewer proves each obligation

Each must be proven by a test that FAILS if the guard is removed. Absence-assertions on
field names do not count: they go green when the same value ships under a different key.

| Obligation | Proof |
| --- | --- |
| O1 | Record a decision, do not commit it, assert Client Review shows pending; then commit and assert it shows authoritative. **Both halves required** -- the first alone passes if the surface renders everything as pending. |
| O2 | Add an unexpected field upstream of the export and assert it is ABSENT from the artifact without any change to the export code. |
| O3 | Build an export from a workspace containing a DSN, an absolute path, and a bare GUID; scan the produced artifact for all three. |
| O4 | Invoke a recovery action without technical approval and assert refusal; then grant approval and assert it proceeds, so the refusal is not unconditional. |
| O5 | Make the scan fail and assert no artifact exists afterwards -- not a partial one. |
| O6 | Search every payload for a numeric roll-up rather than a named field; pair with a positive assertion that per-component states DO appear, so an empty payload cannot pass. |
| O7 | Present a record with no committed source and assert it reports `ephemeral`; pair with a citable record asserting `durable`. |
| O8 | Assert `ClientAcknowledgment` has no answer/approval field, and that posting an acknowledgement writes no decision entry. |

**O1 and O7 are the load-bearing pair.** Both are "the honest label survives the render",
and both are vacuous without their inverse. A test suite that only proves things show as
pending would pass on a surface that can never show anything else.

## Explicit non-goals

- No remote delivery of any artifact -- local export only.
- No cryptographic signing of exports; the manifest is provenance, not attestation.
- No second diagnostic engine, redaction path, or decision-recording route.
- No raw log or transcript download, at any privilege level.
