# Khepri consumer boundary — proposal

- **Status:** **DRAFT — planning only.** Not authored, not ratified. Written 2026-08-05 against
  `Kemetra/Khepri@db98f4b` (its merged architecture package, PR #97) and this repository at
  `728de12`. Authorizes nothing.
- **Would become:** part of `[SESHAT-ADR-BOUNDARY]` and `[SESHAT-SPEC-CONSUMER]`. Neither
  identifier is allocated; both are derived at drafting time.
- **Read with:** `headless-analysis-engine.md`, `analysis-evidence-contracts.md`,
  `product-modules.md`.

---

## What Khepri is, in this repository's vocabulary

`Kemetra/Khepri` is a separate commercial product with its own constitution, its own YAML
governance registries, its own named-human approval authority, and its own approved
specifications. It is **not** a Seshat consumer in the sense that a skill or an adapter is. It
cannot be governed by this repository's ADRs, and this repository cannot be governed by its
decisions.

Two independent governance systems therefore need **two mirrored artifacts**, each approved
under its own rules, each citing the other by commit SHA. Neither may cite the other's approval
as evidence for its own.

## What Khepri already has, so this boundary does not need to supply it

Verified at `Khepri@db98f4b`. Listed because the natural instinct is to offer more than is
wanted, and each row is a thing Khepri would refuse.

| Khepri has | Where |
|---|---|
| CSV/XLSX intake, admissibility, deletion lifecycle | `src/khepri/rra/{intake,admissibility,deletion}.py` (spec RRA-002/003) |
| Retail column profiling and semantic mapping | `profiling.py`, `mapping.py` (RRA-003) |
| Twelve deterministic retail metrics in `Decimal`, formula-versioned and hashed | `facts.py`, `aggregates.py` (RRA-004) |
| Period comparison, concentration, growth decomposition, basket | `analysis/` (RRA-008) |
| Grounded bilingual narrative with uncited-number refusal | `narrative.py` (RRA-005) |
| HTML / PDF / Excel with reconcile-before-delivery | `rendering/`, `bundle.py` (RRA-006) |
| Job leases, bounded retry, dead-lettering, content-free telemetry | `jobs.py`, `worker.py`, `stage_telemetry.py` (RRA-007) |
| A provider-neutral AI interface with a deterministic fallback | `narrative.py:66` |

**Khepri needs statistical inference it does not have.** It does not need retail metrics,
profiling, mapping, rendering, or orchestration from this repository.

## The boundary, stated as three rules

### Rule 1 — Khepri reaches only the contracts, and this repository owns them

```text
Khepri  ──►  analysis contracts  ◄──  Seshat-BI (canonical)
```

Not `Khepri → Seshat-BI`. The contracts carry schemas, fixtures, and validators, and no
numerical library, no CLI, no workspace root, no adapter, and no readiness state machine.

This matters to *this* repository specifically. `Khepri/governance/decisions/KHEPRI-DEC-012`
records the co-installation evidence: this repository is on no package index, pins
`dbt-core==1.12.0` against Khepri's `jinja2>=3.1,<4`, and declares `requires-python >=3.13`
against Khepri's `>=3.13,<3.14`. Keeping the contracts separate from the `seshat-bi`
distribution sidesteps all three, because that distribution is never installed alongside Khepri.

**Direction reflected (not evidence): no package is published.** Contracts would be exchanged as
committed files, under five rules that replace what a package's version pin would have provided:

1. **This repository owns the canonical schemas.** Khepri does not author, extend, or locally
   amend one.
2. **Khepri holds a pinned copy or a generated projection**, never a hand-maintained parallel
   definition. A copy records the Seshat commit it came from.
3. **Schema version and content digest are recorded on both sides**, the version independent of
   any release version.
4. **Cross-repository compatibility tests detect drift**, failing closed on a digest mismatch.
5. **Fixtures demonstrate the contract; they do not define it.** A fixture disagreeing with the
   schema is a fixture defect.

Rule 4 is the enforcement; 1–3 are only an intention without it. Full statement in
`analysis-evidence-contracts.md` §6b, mirrored in the Khepri decision draft so both
repositories record the same contract.

### Rule 2 — Khepri never reaches these

```text
the seshat CLI                    (`seshat analyze` is not an API)
a Seshat repository checkout      (`workspace_root.py` is not a runtime input)
the readiness state machine
metric-contract authoring
dbt, Dagster, Power BI, PBIR
the seshat-bi distribution itself
```

Each has a reason, not just a prohibition. The CLI holds a repository-root filesystem lock. A
checkout implies a developer working set Khepri's wheel deliberately excludes. The readiness
spine is this kit's Core Authority and is meaningless to a Khepri customer session. The
adapters are refused by `KHEPRI-DEC-012` on its own evidence.

### Rule 3 — Seshat never reaches Khepri

No import, no reference, no test dependency, in any direction. The roadmap's §14 rule 8 and
this kit's independence both require that this engine be testable with no Khepri state.

**One live exception to check.** `src/seshat/report/` carries provenance headers reading
"PORTED from `Khepri/src/khepri/rra/rendering/…` at commit `7a1e3fd`" — a port approved by the
owner on 2026-08-03. A *port with a provenance header* is not a runtime dependency and does not
violate rule 3. But the cross-repository decision draft closes the practice: the port is
grandfathered, and **neither repository may port the other's renderer again in either
direction.**

## Where the two rendering stacks stand

This repository's `src/seshat/report/` and Khepri's `src/khepri/rra/rendering/` are two
renderers serving two products. Seshat's renders governed BI evidence for clients without a
Power BI licence; Khepri's renders a commercial customer report under its approved RRA-006.

The proposed cross-repository decision records the divergence as **intentional and closed**.
Neither is removed; neither imports the other; neither may be ported again.

**The constraint that makes this tolerable, and it applies to this repository directly:**
duplicated renderers are a maintenance cost; duplicated *calculators* are a correctness
failure. Both stacks already forbid themselves arithmetic in their own words — this
repository's design decision 1, "Numbers come from one upstream bundle; renderers only
transcribe"; Khepri's `pdf.py`, "It presents figures; it never produces one."

**Neither renderer may acquire arithmetic, and that must be tested on both sides.**
`src/seshat/report/model.py` is the specific watch point: it is a port of Khepri's `bundle.py`
`CitedFigure`, and a helpful subtotal is exactly the shape a well-meaning change would take.

## What this repository must expose

| Capability | Shape |
|---|---|
| Validate a request | Pure function over a contract object. No repo root, no filesystem. |
| Plan eligible analyses | Given available semantic roles and data shape, return which of the eight methods are eligible and why the rest are not. Names methods only — never proposes a business interpretation. |
| Execute an approved method | The headless facade in `headless-analysis-engine.md`. |
| Emit structured evidence | `AnalysisEvidence` serialized to the shared contract, with decimal strings for exact quantities. |
| Render deterministic technical evidence | Existing `statistical/render.py`, unchanged. |

Nothing here is a new capability. All five exist; three are reachable only through the CLI.

## What this repository must **not** expose

- **Any retail metric.** None exists, and none is added for Khepri. Khepri's are authoritative
  under its approved specifications.
- **Forecast evidence across the Khepri boundary.**
  `Khepri/governance/families/RRA.md` excludes forecasting. The `forecast` method stays for
  this kit's own consumers; the boundary does not carry it. If Khepri later wants it, its
  family amendment comes first.
- **Any surface that grants approval.** ADR-0008 reserves grant-approval to Core Authority, and
  a named-human action. A remote caller is neither.
- **Raw customer rows.** Already true — the local CSV provider "records a content digest
  instead of a local path or row payload", and the Gold provider "never exposes connection
  details or raw rows in evidence."

## Compatibility obligations

| Obligation | Owner | Note |
|---|---|---|
| Contract schema version, independent of package release version | This repository | Roadmap §7.1 |
| Compatibility manifest naming supported engine ↔ contract pairs | This repository | Roadmap §7 |
| Committed fixtures both sides validate independently | This repository produces | Roadmap §2 acceptance |
| Fail closed on an unknown contract version | **Khepri** | Roadmap §14 rule 7 |
| Deprecation path for a breaking schema change | This repository | Roadmap §14 rule 6 — new schema version plus migration plan |
| Producer contract lands before consumer implementation | Sequencing | Roadmap §14 rule 3 |

## The sequencing constraint this repository imposes

`CLAUDE.md`: spec 138 is RATIFIED and in implementation; spec 137 awaits ratification; **at
most one of the two may be in implementation at a time (spec 138 FR-026)**, and the SPECKIT
fence carries exactly one plan path by contract.

**Specifications for this boundary can be written and ratified now. Implementation waits for
138 to close.** The Khepri side has been told this; it appears as gate G3 in the
cross-repository PR sequence. It is a real constraint, not a preference, and planning that
ignores it will produce a schedule that cannot be executed.

## Direction this draft reflects — not evidence, not approval

**Direction given by the consuming product's owner in a working session on 2026-08-05.**
It is **not recorded in either repository** — no issue comment, approval package, registry
entry, or approval reference — so it is a planning input, not an approval, and nothing here
may be cited as evidence that a question is settled.


| Question | Decision | Effect on this repository |
|---|---|---|
| Is the integration wanted in Khepri's first release? | **Boundary now, integration deferred** past Khepri's first two milestones | Only `[SESHAT-ADR-BOUNDARY]` proceeds, and no spec number is allocated or reserved. **No implementation capacity is requested from this repository**, so the spec-138 constraint is not contended. |
| Distribution | **Committed fixtures; no package** | This repository publishes nothing. If contracts are ever authored, they are committed schema and example files cross-validated in each repository's own CI — which is what roadmap §14 rule 4 asks for anyway. |
| Renderer duplication | **Two renderers, two products, closed** | `src/seshat/report/` stays exactly as it is. Not removed, not extracted, not re-ported. One new constraint: **it may not acquire arithmetic** — see above. |
| `AGENTS.md` ambiguity in Khepri | **Qualified to Seshat-Platform** | Khepri's copy prohibition is being narrowed to its predecessor repository, so the 2026-08-03 port is not left readable as a violation. This repository need do nothing. |

**What "deferred" means here, precisely.** It does not mean the boundary is provisional. The
ADR should be authored and ratified on its own merits: it records what a non-Seshat consumer may
and may not reach, and that record is worth having whether or not a consumer ever arrives. What
is deferred is building anything.

## Metric authority — a precondition, not an open question

A Khepri customer's CSV has no Seshat metric contract behind it, and `evaluate_policy` requires
contract authority, grain authority, and PII evidence.

**Closed.** A consumer request must satisfy exactly one of two conditions:

1. it carries explicit **Khepri-approved metric authority through a versioned consumer-authority
   contract** — authority this engine *evaluates* rather than trusts — and the resulting evidence
   **identifies the origin of that authority on its face**, so it is distinguishable by
   inspection from evidence resting on an approved Seshat metric contract; or
2. it is **`refused`**, and stays refused until an approved Seshat metric contract exists.

**No relaxed or "uncontracted" policy profile.** An earlier draft recommended one; the
recommendation is withdrawn. A profile that computes without contract authority is an authority
bypass with a name, and stricter data floors do not repair it — floors bound how much data is
needed, not whether anyone approved what it means. `ADR-0008` gives create-truth to Core
Authority alone.

Option 1 is not a relaxed profile: it requires authority to exist, be versioned, be evaluated,
and be attributed. It permits that authority to have been granted by a named human in another
governed repository. **Delegated provenance, not absent provenance.**

The mechanism is parked to the integration specification (`analysis-evidence-contracts.md` §4).
The precondition is not parked — no integration work begins without it satisfied.

## Remaining open questions

Two, neither gating anything while the integration is deferred: whether `DataSnapshot` spans
file and database at v1 (file-only recommended), and whether `SemanticRole` publishes this kit's
seven roles as-is (yes). Both in `analysis-evidence-contracts.md` §8.
