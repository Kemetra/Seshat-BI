# Feature Specification: Per-Contract Ambiguity Decision Ledger (force A1-A10 to a recorded ruling)

**Feature Branch**: `058-per-contract-ambiguity-decision-ledger`

**Created**: 2026-07-01

**Status**: Ratified (advisor-for-Ahmed-Shaaban, 2026-07-01)

**Ratification note**: Ratified by the advisor agent under the explicit, recorded per-session
delegated override granted by the repo owner (info@rahmaqanater.org) for the 2026-07-01
"release the kraken" batch of seven idea-to-spec specs. Provenance: this Ratified line is
AI-authored under recorded human authority; NOT a human-typed ratification -- the git author
identity does not by itself attest a human reviewer. Spec dir renumbered to
`058-per-contract-ambiguity-decision-ledger` to avoid the 053 collision across the parallel
kraken runs (roadmap F-number wins on disagreement). Rulings: FR-013 = fail-safe (a
number-moving ambiguity blocks until a named owner rules; owner may downgrade, agent never);
FR-014 = left exploratory, no F-number (extends the shipped F009 store template only). Premise
corrected: the ambiguity catalogue is **A1-A11** (A11 = same-store), not the title's "A1-A10" --
the ledger keys to the full A1-A11 range. This is the DEFINE half; the CHECK half (AL1) is a
separate spec. Docs/template only -- no runtime code, no new retail check rule (count stays
38). analyze=clean (0 critical/0 high); plan-review=PASS-WITH-NOTES. Override is
per-session/per-this-set only; it covers ratification, not merge (normal CI gate still applies).

**Input**: User description: "Per-Contract Ambiguity Decision Ledger (force A1-A10 to a recorded ruling)"

## Overview

The kit already catalogs eleven dangerous retail ambiguities -- ones that change a
reported number WITHOUT changing the underlying data (VAT included vs excluded,
returns as negative lines vs a separate fact, sale vs posting date, gross vs net,
discount line vs header, cost method, cancelled/void transactions, product key vs
name, branch key vs name, inventory snapshot date, same-store definition). That
catalog lives in the retail KPI knowledge reference. But a filled metric contract
today has nowhere STRUCTURED to record, per ambiguity, WHICH ruling the business
owner made and WHAT evidence supports it. The ambiguity is discussed in prose during
authoring and then lost; the contract's readiness status carries no trace of an
undecided-but-material ambiguity.

The most concrete stakes case is documented and generic: a discounted-transaction
rate over retail store sales swings from about 33.55 percent (counting every
transaction in the denominator) to about 50.37 percent (counting only
known-status transactions) purely on the unresolved cancelled/void/blank-status
ruling. Same data, same formula intent, a swing of roughly seventeen points -- driven
by an ambiguity no one recorded a ruling for.

This feature adds the DEFINE-side seam that closes that gap: a structured
**ambiguity ledger** on the metric contract. Each contract records, per applicable
catalogued ambiguity, a small entry -- which ambiguity it is, the ruling status, the
ruling text, and the supporting evidence. An undecided ambiguity that MOVES THE
NUMBER records a blocking reason and forces the contract's readiness to `blocked`.
The agent RECORDS the human owner's ruling; it never invents one and never
self-grants a decided status. This is the same discipline the contract's readiness
block already enforces, extended to name the specific ambiguity behind a block.

## What this is (and is NOT)

This is the **DEFINE half** of a DEFINE/CHECK pair, and it is **authoring only**:

- **IN scope** -- authoring committed template and documentation TEXT:
  1. Add an ambiguity-ledger block to the metric-contract template so a filled
     contract can record a per-ambiguity ruling keyed to the catalogued ambiguity
     identifiers.
  2. Document the ledger lifecycle, the non-pass blocker rule, and the
     define/check boundary in the metric contract store guide.
  3. CONFIRM (state, not invent) that the existing KPI pack rollup already
     propagates a blocked contract to its packs, so no new rollup logic is needed.

- **OUT of scope** (deferred; this spec neither builds nor assumes any of it):
  - The static CHECK rule that would machine-enforce the block (the enforcing half
    is a separate, unbuilt backlog idea). This spec adds NO automated check and NO
    new registered rule. The "blocker" is a documented authoring convention a human
    reviewer honors -- NOT a program exit code.
  - Reading or asserting anything about a Power BI model (that is the separate
    downstream checking feature).
  - Any Power BI execution adapter or other deferred runtime.
  - Any live database, ingestion, or real data.

This feature reads no model, connects to no database, and registers no check. It is
the same category of work as authoring a mapping or contract template: committed
text with no runtime side effects.

## Terminology correction (carried by this spec)

The idea title says "A1-A10". The live catalogue actually runs A1 THROUGH A11: A10 is
the inventory-snapshot-date ambiguity and A11 is the same-store-definition ambiguity.
The ledger MUST key to the real A1..A11 range. Keying only to a ten-item ceiling would
let the same-store ambiguity (A11) silently escape the ledger. Every artifact this
feature authors uses the A1..A11 range and none narrows it to A1..A10.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a decided ambiguity ruling on a contract (Priority: P1)

A metric owner has ruled on an ambiguity that affects one of their metrics (for
example: "cancelled and blank-status transactions are EXCLUDED from the
discounted-transaction-rate denominator"). The contract author records that ruling in
the contract's ambiguity ledger: the catalogued ambiguity identifier, a decided
status, the ruling text in plain language, and the evidence (who ruled and when). The
recorded ruling now travels WITH the contract and is reviewable.

**Why this priority**: This is the core value -- turning a lost hallway ruling into a
committed, reviewable part of the contract. Without it, nothing else in the feature
has a home to write to.

**Independent Test**: Copy the metric-contract template, fill one ambiguity-ledger
entry with a decided ruling plus owner-and-date evidence, and confirm a reviewer can
read exactly which ambiguity was ruled, the ruling, and its evidence -- with no
numeric confidence score anywhere.

**Acceptance Scenarios**:

1. **Given** a contract whose metric is affected by a catalogued ambiguity, **When**
   the owner has ruled and the author records the entry (identifier + decided status +
   ruling text + owner-and-date evidence), **Then** the ledger entry stands as the
   committed record of that ruling and the reviewer can trace it end to end.
2. **Given** a decided ledger entry, **When** a reviewer inspects it, **Then** the
   status is drawn only from the allowed vocabulary and there is no numeric
   confidence or score field.
3. **Given** a metric NOT affected by a given catalogued ambiguity, **When** the
   author fills the ledger, **Then** that ambiguity may be omitted or explicitly
   marked not-applicable, and its absence is not treated as an undecided block.

---

### User Story 2 - An undecided material ambiguity blocks the contract (Priority: P1)

A contract's metric is affected by an ambiguity that MOVES THE NUMBER, and the owner
has NOT yet ruled. The author records the ambiguity as undecided, which records a
blocking reason and forces the contract's readiness to `blocked`. The agent cannot
clear this by inventing a ruling; only a recorded owner decision resolves it.

**Why this priority**: This is the enforcement discipline that makes the ledger more
than documentation. An undecided material ambiguity is exactly the condition that
produced the seventeen-point rate swing in the motivating case.

**Independent Test**: Fill a contract whose metric has a material, undecided
ambiguity; confirm the ledger entry carries an undecided status, a blocking reason is
recorded, and the contract's readiness is `blocked` -- and that there is no path for
the author to reach `pass` without a recorded owner ruling.

**Acceptance Scenarios**:

1. **Given** a metric affected by a material ambiguity with no owner ruling, **When**
   the author fills the ledger, **Then** the entry is undecided, a blocking reason
   names the ambiguity, and readiness is `blocked`.
2. **Given** an undecided material ambiguity, **When** the agent attempts to author a
   ruling itself, **Then** the convention forbids it: the agent may recommend and
   record the OWNER's ruling as evidence, but never self-grant a decided status.
3. **Given** a previously blocked contract, **When** the owner rules and the author
   records the decision with evidence, **Then** the blocking reason for that ambiguity
   is cleared and readiness may advance per the existing readiness rules.

---

### User Story 3 - A blocked contract propagates to its packs (Priority: P2)

A KPI pack groups the blocked contract among its members. Because a pack is no more
ready than its least-ready contract, the pack's readiness reflects the block. This
feature CONFIRMS the existing rollup already carries this; it invents no new pack
logic.

**Why this priority**: It proves the seam composes with the existing store without new
machinery -- a correctness confirmation, not new behavior.

**Independent Test**: Point an example pack at a contract blocked by an undecided
ambiguity and confirm, by reading the existing rollup rule, that the pack cannot be
more ready than that blocked member -- with no rollup rule added or changed by this
feature.

**Acceptance Scenarios**:

1. **Given** a pack whose members include a contract blocked by an undecided
   ambiguity, **When** the pack readiness is read under the existing rollup rule,
   **Then** the pack is no more ready than that blocked member.
2. **Given** this feature's artifacts, **When** a reviewer looks for new rollup logic,
   **Then** none exists -- the propagation is the existing "least-ready member" rule,
   only confirmed.

---

### Edge Cases

- **A material ambiguity applies but the author leaves the ledger empty.** The store
  guide states that an omitted-but-applicable material ambiguity is itself a review
  defect: silence is not a decided status. The reviewer treats a missing material
  entry the same as undecided.
- **An ambiguity is cosmetic on this metric (recordable but not number-moving).**
  Whether a given ambiguity is number-moving (blocking) versus cosmetic
  (recordable-but-non-blocking) on a specific contract is a human judgment. See the
  Clarifications carve-out; the spec does not let the agent decide this by default.
- **An author tries to record certainty as a number** (for example a percentage of
  confidence in the ruling). Rejected: the ledger uses the allowed status vocabulary
  plus evidence and blocking reasons only. No numeric confidence field exists.
- **An author inlines a domain-specific ambiguity ruling into the generic template**
  (for example a pharmacy billing-code or insurance-grain ruling). Rejected: the
  template and store guide stay generic-retail; a real filled ruling lives in the
  cited worked example, never inline in the generic template.
- **A ledger entry references an identifier outside A1..A11.** Rejected as a defect:
  the ledger keys only to the catalogued A1..A11 identifiers.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The metric-contract template MUST gain an ambiguity-ledger block in
  which a filled contract records, per applicable ambiguity, an entry consisting of:
  the catalogued ambiguity identifier, a decision status, the ruling text in plain
  business language, and evidence.
- **FR-002**: The ledger MUST key to the catalogued ambiguity identifiers over the
  full A1..A11 range (A10 = inventory snapshot date, A11 = same-store definition). No
  authored artifact may narrow this to A1..A10.
- **FR-003**: An entry's ruling text MUST be plain-language business INTENT -- what
  the ruling means -- never a formula, query, visual spec, or model path. Such content
  is rejected in the ledger, consistent with the contract's existing define/check
  boundary.
- **FR-004**: An undecided ambiguity that MOVES THE NUMBER MUST record a blocking
  reason and force the contract's readiness to `blocked`. The agent MUST NOT clear
  this by inventing a ruling; only a recorded owner decision (owner plus date as
  evidence) resolves it.
- **FR-005**: The ledger MUST record certainty ONLY through the allowed status
  vocabulary plus evidence and blocking reasons. No numeric confidence or score field
  may be added anywhere (no fake confidence).
- **FR-006**: The decision-status vocabulary MUST reuse an existing recorded idiom --
  either the contract's four readiness statuses or the catalogue's
  needs-business-definition flag. Inventing a new fifth status word is forbidden. The
  exact choice is a human-confirmed decision (see Clarifications).
- **FR-007**: All authored artifacts MUST stay generic-retail. No domain-specific
  (for example pharmacy) ambiguity ruling may be inlined into the generic template or
  the store guide; a real filled ruling is CITED via the worked example only.
- **FR-008**: The store guide MUST document the ledger lifecycle, the non-pass blocker
  rule, and MUST restate the define/check boundary verbatim so it does not drift: this
  feature DEFINES; it reads no model, adds no check rule, and does not implement the
  deferred enforcing half.
- **FR-009**: The feature MUST CONFIRM, in the store guide, that the existing KPI pack
  rollup already propagates a blocked contract (a pack is no more ready than its
  least-ready contract). It MUST NOT add or change any rollup rule.
- **FR-010**: The feature MUST NOT add, register, or modify any automated check rule,
  and MUST NOT read any Power BI model or connect to any data source. The blocker is a
  documented authoring convention honored by a human reviewer, not a program exit code.
- **FR-011**: All authored text MUST be ASCII, UTF-8 without a byte-order mark, using
  short repo-relative paths (Windows path-length budget), consistent with existing kit
  artifacts.
- **FR-012**: The motivating example used in any authored artifact MUST be the generic
  retail-store-sales discounted-transaction-rate denominator case; no domain-specific
  case is inlined.
- **FR-015**: A contract MUST record a ledger entry only for each catalogued ambiguity
  that APPLIES to its metric; an ambiguity that does not apply may be omitted. Omission
  of an APPLICABLE material ambiguity is a review defect and is treated as undecided
  (Q1).
- **FR-016**: Not-applicable MUST be expressed by omitting the entry (optionally with a
  one-line note), NOT by a decided status; undecided MUST be an explicit status that
  carries a blocking reason. A reviewer distinguishes the two by presence-and-status,
  never by inference (Q2).
- **FR-017**: The ambiguity ledger MUST be authored as its own top-level block on the
  contract, a sibling of the readiness block, NOT nested inside readiness. An undecided
  material entry forces readiness to `blocked` and records a readiness blocking reason,
  but the readiness block's existing verbatim shape MUST NOT drift (Q3).

*The following requirements depend on human rulings and are recorded as open in
Clarifications rather than resolved here:*

- **FR-013** (human-ruled 2026-07-01, fail-safe default): An ambiguity is treated as
  **number-MOVING (blocking)** whenever its candidate rulings would change any reported
  number for that contract -- it records a `blocking_reason` and forces `status: blocked`
  until a named owner records the ruling. An ambiguity is non-blocking only when a named
  owner explicitly records it cosmetic. The default is conservative (unresolved
  number-affecting ambiguity blocks); the owner may downgrade, the agent never does. No
  numeric threshold is introduced (categorical: affects-a-number vs not).
- **FR-014** (human-ruled 2026-07-01): The ledger is **left exploratory -- NO roadmap
  F-number is assigned**. It extends the shipped F009 Metric Contract Store template
  (adding the `ambiguities[]` block) but is not itself a roadmap feature row (the idea bank
  is not the roadmap; Principle V / roadmap prose). A human may later fold it into F009 or
  assign an F-row; until then it stays an exploratory DEFINE-layer amendment.

### Key Entities *(include if feature involves data)*

- **Ambiguity ledger entry**: the per-ambiguity record on a contract. Attributes:
  the catalogued ambiguity identifier (A1..A11), a decision status drawn from an
  existing vocabulary, the ruling text (plain-language intent), and evidence (the
  owner who ruled plus the date, and any committed support). It carries no numeric
  confidence.
- **Ambiguity catalogue (read-only reference)**: the existing A1..A11 list of
  number-moving retail ambiguities the ledger keys to. This feature references it and
  never edits it.
- **Metric contract (host)**: the existing committed metric definition whose readiness
  block the ledger extends. An undecided material entry forces the host's readiness to
  `blocked`.
- **KPI pack (downstream reader)**: the existing grouping whose readiness rolls up
  from its least-ready member; it inherits a contract's ambiguity block through the
  existing rollup, unchanged by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer reading a filled contract can, for every applicable A1..A11
  ambiguity, see either a decided ruling (with owner-and-date evidence) or an
  explicit undecided entry with a blocking reason -- with zero material ambiguities
  left silently unaddressed.
- **SC-002**: 100 percent of undecided material ambiguities on a contract correspond
  to that contract's readiness being `blocked`; there is no authored path from an
  undecided material ambiguity to `pass`.
- **SC-003**: Zero numeric confidence or score fields appear in any authored artifact;
  certainty is recorded only via status, evidence, and blocking reasons.
- **SC-004**: Zero domain-specific (for example pharmacy) ambiguity rulings appear in
  the generic template or store guide; the only filled ruling is cited via the worked
  example.
- **SC-005**: The full A1..A11 identifier range is referenced in every authored
  artifact; no artifact narrows the range to A1..A10, so the same-store ambiguity
  (A11) is never dropped.
- **SC-006**: Zero new automated check rules, model reads, or rollup-rule changes are
  introduced; the pack-propagation behavior is the existing least-ready-member rule,
  only confirmed in prose.

## Assumptions

- The A1..A11 ambiguity catalogue is stable and authoritative; this feature keys to it
  and does not restate or redefine the ambiguities themselves.
- The contract's existing four-status readiness model and evidence/blocking-reasons
  structure remain the recording mechanism; the ledger extends, not replaces, them.
- The existing KPI pack rollup ("no more ready than its least-ready contract") is
  correct and sufficient to propagate a contract-level block; this feature only
  confirms it.
- Filled contracts and their real ambiguity rulings live per-table alongside their
  mappings (and, for a domain instance, in the cited worked example) -- never inline
  in the generic template.
- The enforcing static-check half is deferred to a separate future effort; nothing in
  this spec depends on it existing.

## Clarifications

Principle-V judgment calls reserved for a named human owner. These are recorded, not
answered, by this spec; the agent may recommend but must not decide them.

### Session 2026-07-01

**Advisor-resolved design decisions** (recorded design rulings, not business
judgment calls; integrated into the requirements below):

- **Q1 -- Applicability model: all 11 entries always, or only applicable ones?**
  Recommended answer: **only applicable ambiguities are recorded; each recorded
  entry is explicit.** A contract records an entry for each catalogued ambiguity that
  applies to its metric; an ambiguity that does not apply may be omitted. Silence on an
  APPLICABLE material ambiguity is a review defect (treated as undecided). Reasoning: a
  fixed 11-row block on every contract would force meaningless entries (for example a
  same-store ruling on a line-grain revenue metric), and padding the ledger with
  not-applicable rows dilutes the signal. Making omission-of-an-applicable-material-
  ambiguity a defect keeps the enforcement teeth without forcing noise. Reversible:
  easy (a schema-comment convention).
- **Q2 -- How is a not-applicable ambiguity distinguished from an undecided one?**
  Recommended answer: **omission means not-applicable; an explicit undecided status is
  required to mark a material ambiguity as unresolved.** Not-applicable is expressed by
  leaving the entry out (optionally with a one-line note), never by a decided status.
  Undecided is an explicit status that carries a blocking reason. Reasoning: this keeps
  the two states unambiguous to a reviewer -- absence is benign only for
  non-applicable ambiguities, and any material ambiguity must be present as an explicit
  undecided-or-decided entry. Reversible: easy.
- **Q3 -- Where does the ledger block sit in the contract structure?**
  Recommended answer: **a sibling top-level block on the contract (for example
  `ambiguities`), adjacent to the readiness block, NOT nested inside readiness.** An
  undecided material entry FORCES readiness to `blocked` and adds a readiness
  blocking_reason, but the ledger itself is its own block so the readiness block's
  existing shape does not drift. Reasoning: nesting the ledger inside readiness would
  alter the verbatim readiness structure that must not drift across F009 artifacts; a
  sibling block adds the seam without touching the readiness schema. Reversible: costly
  (moving the block after filled contracts exist is a migration), so pin it now.

*(carve-out) The following are reserved for a human owner and are NOT answered here:*

- **Headline-moving criterion**: What makes a given ambiguity number-MOVING (and thus
  a `blocked`-forcing entry) versus cosmetic (recordable but non-blocking) on a
  specific contract? This is a business judgment reserved for the named metric owner;
  the agent must not set a default rule that decides it.
- **Roadmap placement**: Which readiness stage or roadmap position does this ledger
  advance -- an amendment to the existing (shipped) metric contract store feature, a
  new roadmap row, or left exploratory? A human must place it; the feature extends a
  shipped store but is not itself roadmap-mapped.
- **Per-ruling correctness**: For each A1..A11 ambiguity on a given contract, whether
  the recorded ruling is CORRECT (for example, whether the discounted-transaction-rate
  denominator is known-status-only versus all transactions) is a named-owner decision
  the agent may only RECORD with evidence, never author.
- **Decision-status vocabulary choice**: Whether the ledger's decision status reuses
  the four readiness statuses or the catalogue's needs-business-definition flag. This
  touches the no-fake-confidence discipline and must be human-confirmed. Both candidate
  vocabularies already exist in the kit; the recommendation (see plan) is to reuse the
  four readiness statuses for consistency with the host readiness block, but the final
  pick is deferred to the owner.
