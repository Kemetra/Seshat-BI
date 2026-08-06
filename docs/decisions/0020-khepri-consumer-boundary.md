# 0020 -- a non-Seshat consumer reaches the analysis contracts and nothing else

- **Date:** 2026-08-06
- **Status:** **Proposed -- NOT ratified.** This ADR takes effect ONLY when the
  owner replaces this line with an explicit ratification
  (`Accepted -- RATIFIED by <name> (owner) on <date>`). An agent must never
  edit this Status line (Principle V, never_self_grant_approval). Until
  ratification every boundary below is inert: it authorizes nothing, refuses
  nothing, and constrains no existing code.
- **Counterpart:** `Khepri/governance/decisions/KHEPRI-DEC-013`, which is
  `proposed` in Khepri's decisions registry and unapproved. **Neither side is
  ratified, and neither may be cited as settling the other.** The two are drafted
  to record the same boundary from each repository's own vocabulary and authority.
- **Context:** Khepri is a separately owned commercial product that renders a
  governed customer report from one uploaded CSV or XLSX per session. It has asked
  what, if anything, it may reach in this repository.

  `Khepri/governance/decisions/KHEPRI-DEC-012` already refuses the runtime
  direction on its own evidence: no dbt binary, no Dagster daemon, and no
  co-installation of the `seshat-bi` distribution. That decision explicitly
  declines to reach the different question of a **versioned analytical contract**,
  and states that the question belongs to a boundary decision. This is this
  repository's half of that boundary.

  The analysis was authored as three architecture documents in #579 (`3875aca`):
  `khepri-consumer-boundary.md`, `headless-analysis-engine.md`, and
  `analysis-evidence-contracts.md`. This ADR decides what those documents propose;
  it does not restate them.

## Decision

### 1. The consumer reaches the contracts, and this repository owns them

```text
consumer  ──►  analysis contracts  ◄──  Seshat-BI (canonical)
```

Not `consumer → Seshat-BI`. The contracts carry schemas, fixtures, and validators, and
no numerical library, no CLI, no workspace root, no adapter, and no readiness state
machine.

Five rules replace what a package version pin would otherwise have provided:

1. This repository owns the canonical schemas. A consumer does not author, extend, or
   locally amend one.
2. A consumer holds a pinned copy or a generated projection, never a hand-maintained
   parallel definition, and records the Seshat commit it came from.
3. Schema version and content digest are recorded on both sides, the version
   independent of any release version.
4. Cross-repository compatibility tests detect drift, failing closed on a digest
   mismatch.
5. Fixtures demonstrate the contract; they do not define it. A fixture disagreeing with
   the schema is a fixture defect.

**Rule 4 is the enforcement. Rules 1--3 are an intention without it**, and an
intention is not a boundary.

### 2. A consumer never reaches these

```text
the seshat CLI                    (`seshat analyze` is not an API)
a Seshat repository checkout      (`workspace_root.py` is not a runtime input)
the readiness state machine
metric-contract authoring
dbt, Dagster, Power BI, PBIR
the seshat-bi distribution itself
```

Each has a reason rather than only a prohibition. The CLI holds a repository-root
filesystem lock. A checkout implies a developer working set. The readiness spine is this
kit's Core Authority and is meaningless in a consumer's customer session. The adapters
are refused by `KHEPRI-DEC-012` on its own evidence.

### 3. This repository never reaches a consumer

No import, no reference, no test dependency, in any direction. This engine must stay
testable with no consumer state.

**One exception, grandfathered and closed.** `src/seshat/report/` carries provenance
headers recording a port from Khepri's renderer at commit `7a1e3fd`, approved by the
owner on 2026-08-03. A port carrying a provenance header is not a runtime dependency and
does not breach this rule. **Neither repository may port the other's renderer again, in
either direction.**

### 4. Two renderers, two products, intentionally closed

`src/seshat/report/` renders governed BI evidence for clients without a Power BI licence.
Khepri's renders a commercial customer report under its own approved specification.
Neither is removed, neither imports the other, neither is re-ported.

One new constraint on both: **neither renderer may acquire arithmetic.** A renderer that
computes is a second source of truth for a number, which is the failure both governance
regimes exist to prevent.

### 5. Metric authority is a precondition, not an open question

A consumer's uploaded CSV has no Seshat metric contract behind it, and `evaluate_policy`
requires contract authority, grain authority, and PII evidence. A consumer request
satisfies exactly one of:

1. it carries explicit **consumer-approved metric authority through a versioned
   consumer-authority contract** -- authority this engine *evaluates* rather than trusts
   -- and the resulting evidence **identifies the origin of that authority on its face**,
   so it is distinguishable by inspection from evidence resting on an approved Seshat
   metric contract; or
2. it is **`refused`**, and stays refused until an approved Seshat metric contract exists.

**There is no relaxed or "uncontracted" policy profile.** An earlier draft recommended
one and the recommendation is withdrawn. A profile that computes without contract
authority is an authority bypass with a name, and stricter data floors do not repair it
-- floors bound how much data is needed, not whether anyone approved what it means.
`ADR-0008` gives create-truth to Core Authority alone.

Option 1 is not a relaxed profile. It requires authority to exist, be versioned, be
evaluated, and be attributed, and permits that authority to have been granted by a named
human in another governed repository. **Delegated provenance, not absent provenance.**

### 6. Distribution is by committed files; nothing is published

This repository publishes no package for this purpose. If contracts are ever authored,
they are committed schema and example files, cross-validated in each repository's own CI.

## Consequences

- **Nothing is built.** The owner's direction is boundary now, integration deferred past
  the consuming product's first two milestones. No specification number is allocated or
  reserved by this ADR, and **no implementation capacity is requested from this
  repository** -- so the spec-138 constraint (at most one of specs 137 and 138 in
  implementation at a time, spec 138 FR-026) is not contended, and the SPECKIT fence is
  untouched.
- **Ratification is worth having anyway.** This ADR records what a non-Seshat consumer
  may and may not reach. That record is worth holding whether or not such a consumer ever
  arrives, and deferring the build does not make the boundary provisional.
- **The 2026-08-03 port stops being readable as a violation**, because §3 states the rule
  it is an exception to, and closes the practice going forward.
- **Two questions stay open, and neither gates anything** while integration is deferred:
  whether `DataSnapshot` spans file and database at v1 (file-only recommended), and
  whether `SemanticRole` publishes this kit's seven roles as-is (yes). Both are recorded
  in `analysis-evidence-contracts.md` §8.
- **The direction behind this ADR is a planning input, not evidence.** It was given by the
  consuming product's owner in a working session on 2026-08-05 and is recorded in neither
  repository as an approval -- no issue comment, approval package, registry entry, or
  approval reference. Nothing here may be cited as evidence that a question is settled;
  ratification of this ADR is what would settle this repository's half.
