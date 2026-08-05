# Analysis and evidence contracts — proposal

- **Status:** **DRAFT — planning only.** Not authored, not ratified, no schema is normative
  here. Written 2026-08-05 against `Kemetra/Khepri@db98f4b` (its merged architecture package, PR #97) and this repository at
  `728de12`.
- **Would become:** `[SESHAT-SPEC-CONTRACTS]` — **deferred** under the session direction of
  2026-08-05 (boundary now, integration later), which is a planning input and not an approval. **No spec number is allocated or reserved.** If
  any deferred work is ever pulled forward, **this is the piece to pull first**: committed
  schemas and fixtures need no package, no distribution decision, and no implementation
  capacity, and they satisfy the cross-repository roadmap's §2 acceptance criterion in full.
- **Read with:** `headless-analysis-engine.md`, `khepri-consumer-boundary.md`,
  `statistical-evidence-engine.md`.
- **Sequencing:** this must be authored **before** the headless engine spec —
  the cross-repository roadmap's §14 rule 3, "the producer contract lands before the consumer
  implementation." It is also the only piece of this program **not** blocked by spec 138.

---

## 1. What exists, and why it is not yet a cross-repository contract

`src/seshat/statistical/contracts.py` already defines `AnalysisSpec`, `AnalysisEvidence`,
`MethodSpec`, `ColumnBinding`, `Estimate`, `Interval`, `TestStatistic`, `Diagnostic`,
`Blocker`, and `Outcome`, exported from a package that keeps every numerical dependency
unloaded on import. `ENGINE_VERSION = "1.0"`.

Three properties stop it being a cross-repository contract as it stands:

1. **It is statistically shaped.** `MethodSpec` presumes one of the eight closed methods. A
   consumer sending a retail dataset has no method in mind yet — it has columns and a question.
2. **It is repo-root bound at the point of use.** Not in the dataclasses, but in
   `run_analysis(repo_root, …)` and `evaluate_policy(repo_root, …)`, which resolve cited
   governance paths against the working set.
3. **It has no version negotiation.** `ENGINE_VERSION` is a constant, not a manifest. There is
   no supported-range declaration and no consumer-side fail-closed path.

The gap is smaller than the roadmap's thirteen contract families imply. Most of what §7 names
already exists here under other names.

## 2. Mapping the roadmap's contract families onto reality

| Roadmap family | Nearest existing | Gap |
|---|---|---|
| `AnalysisSpecification` | `AnalysisSpec` | Generalize; decouple from `repo_root` resolution |
| `AnalysisResult` | `AnalysisEvidence` | Serialization format and version envelope |
| `AnalysisLimitation` | `Blocker` + `Diagnostic` | Already structured and machine-readable. Add the customer-unlock field? **No** — see §5 |
| `EvidenceReference` | evidence `governance` block, `_governance_reference` | Make repo-path-independent |
| `MetricContractReference` | metric contract authority in `policy.py:117` | Needs a form a non-Seshat caller can supply |
| `SemanticRole` | `ColumnBinding` roles (`response`, `group`, `predictor`, `numerator`, `denominator`, `time`, `pair`) | A closed, documented vocabulary already; needs publishing as a contract |
| `DatasetProfile` | `file_profile.py` | Not currently a contract; also duplicated by Khepri's `profiling.py` |
| `DataSnapshot` | provider inputs (`local_csv`, `gold`) | No normalized shape spanning both |
| `AnalysisRequest` | — | New. The envelope carrying spec + snapshot reference + governance context |
| `EvidenceBundle` | — | New. One or more `AnalysisEvidence` plus a manifest |
| `AuditManifest` | evidence `governance` + digests | Needs assembling into one artifact |
| `EngineCompatibilityManifest` | — | New |
| `SemanticMapping` | source-map workflow (specs 008, 010) | Warehouse-shaped; a file-upload caller has no source map |

**Four genuinely new artifacts: `AnalysisRequest`, `EvidenceBundle`, `AuditManifest`,
`EngineCompatibilityManifest`.** The rest are existing types needing generalization and
publication. That is a materially smaller job than "define thirteen contract families."

## 3. Rules the schemas must enforce, and how each is tested

From the cross-repository roadmap §7.1. Every one is testable; none should be asserted in prose
only.

| Rule | Test |
|---|---|
| Money and exact financial quantities serialize as **decimal strings** | Round-trip a value with more precision than IEEE 754 holds and assert byte equality. This repository already emits decimal-string intervals; Khepri already forbids binary floating point as an authoritative fact (`KHEPRI-DEC-008`). Both sides already believe it — the test makes it a contract. |
| Every published numerical result carries ≥1 evidence reference | Schema validation refuses a result with an empty reference list. |
| Every method and formula carries a version | Already true here (all methods `1.0`). Make it a required schema field. |
| Every bundle carries an input or snapshot digest | Already true — the local CSV provider records a content digest. Lift to the bundle. |
| Every limitation is structured and machine-readable | Already true — `Blocker` carries code, message, recovery. |
| Customer-facing wording is **not** part of the contract | Negative test: a bundle with no prose validates. |
| Contract schema version is independent of package release version | Two separate fields, and a test that they may differ. |
| An unknown contract version **fails closed** | Consumer-side. Khepri's obligation (roadmap §14 rule 7); this repository supplies the fixture that triggers it. |

## 4. Metric authority: a precondition for integration, not an open question

`evaluate_policy` requires metric contract authority (`policy.py:117`), grain authority
(`_grain_blocker`), and PII evidence (`_pii_evidence_exists`). Those exist because this kit
serves a governed medallion warehouse where a named human approved a source map and a metric
contract before any number was computed.

**A Khepri customer uploads a CSV.** There is no Seshat source map, no approved metric contract,
no readiness stage, and no named human who approved its business meaning under this kit's Core
Authority. Khepri has its own equivalent — a profiling and mapping confirmation flow under its
approved spec RRA-003 — but that is Khepri authority, not Seshat authority.

**This is closed, not open.** A consumer request must satisfy exactly one of two conditions:

1. **It carries explicit Khepri-approved metric authority through a versioned
   consumer-authority contract.** The authority is the consumer's own — an approved
   specification plus the mapping confirmation recorded against that dataset — expressed in a
   versioned contract this engine **evaluates** rather than trusts. The resulting evidence must
   **identify the origin of its authority on its face**, so that evidence resting on consumer
   authority is distinguishable by inspection from evidence resting on an approved Seshat metric
   contract.
2. **Otherwise the request is `refused`**, and stays refused until an approved Seshat metric
   contract exists for that data.

### There is no third option, and specifically no relaxed profile

An earlier draft of this document recommended a named "uncontracted consumer" policy profile
with stricter floors. **That recommendation is withdrawn, and the reasoning behind it was
wrong.**

A second profile that computes *without* contract authority is an authority bypass with a name.
Making its floors stricter does not fix it: the floors bound how much data is needed, not
whether anyone approved what the data means. The evidence it emits would look like governed
evidence and would rest on nothing this kit can point to. `ADR-0008` gives create-truth to Core
Authority alone, and a profile that computes over unapproved business meaning creates truth by
another route.

Option 1 is not a relaxed profile. It requires authority to exist, be versioned, be evaluated,
and be attributed — it simply permits that authority to have been granted by a named human in
another governed repository rather than in this one. The distinction is the whole point:
**delegated provenance, not absent provenance.**

Khepri Constitution II uses exactly this discipline for delegated approvals — "Human and
delegated approvals remain distinguishable by inspection" — and it is the right precedent.

### What is parked, and what is not

**Parked to the integration specification:** what a versioned consumer-authority contract
contains; how this engine validates it; how the origin marking is rendered in evidence; whether
a consumer-authority request may reach the Gold provider at all (**the presumption is no**).

**Not parked:** whether the precondition applies. It does. No integration work may begin without
it satisfied, and a slice that discovers this under schedule pressure must not resolve it by
relaxing the policy.

Because the integration is deferred, this constrains nothing today. It is recorded now precisely
so that it is not rediscovered later by someone with a deadline.

## 5. What the contract deliberately does not carry

- **Customer language.** Roadmap §7.1: "Customer-facing wording is not part of the analytical
  evidence contract." `Blocker.recovery` is a technical recovery instruction, not customer
  copy. Khepri owns the mapping from a code to a customer sentence, through its own approved
  presentation contract (`Khepri/docs/reporting/refusal-presentation.md`), and that mapping
  must not leak into this schema.
- **Arabic or English rendering.** Roadmap §7.1: rendering happens after evidence creation.
- **A customer-unlock field on limitations.** Tempting — the roadmap's §8.3 customer contract
  wants "how the customer can make the analysis available." But that is a product sentence
  about a product's data-collection options, and this engine knows nothing about them.
  `Blocker` says what evidence is missing; Khepri says how its customer can supply it.
- **A retail metric of any kind.** None exists here and none is added.
- **A confidence or maturity score.** Hard rule #9. Outcomes are categorical; `computed` is a
  numerical completion state, not acceptance.

## 6. Compatibility manifest

New artifact. Declares, for each engine release: supported contract schema versions, the
method catalog with method versions, required and optional dependency extras, and the provider
boundary (currently PostgreSQL-only for Gold acquisition).

Khepri pins an engine version and a contract version and refuses on mismatch — its own
precedent is `KHEPRI-DEC-005:187`, where the narrative provider is optional and fails closed
so that "report availability never depends on" it. The same shape applies here: on an
unsupported version Khepri delivers its deterministic report and records the refusal.

## 6b. Source of truth, with no package to supply one

**Direction reflected (not evidence): no package is published.** A package would otherwise have carried
the source of truth in its version pin. Without one it must be stated, or "committed fixtures"
degrades into two repositories editing lookalike files.

Five rules, mirroring the consumer-side decision draft so both repositories record the same
contract:

1. **This repository owns the canonical schemas.** They are authored and versioned here, per the
   cross-repository roadmap §5.2. A consumer does not author, extend, or locally amend a schema.
2. **A consumer holds a pinned copy or a generated projection** — never a hand-maintained
   parallel definition. A copy records the Seshat commit it came from; a projection records the
   generator and its input.
3. **Schema version and content digest are recorded on both sides.** The schema version is
   independent of any release version (roadmap §7.1). The digest is what makes a silent edit
   detectable.
4. **Cross-repository compatibility tests detect drift.** Each repository asserts its copy
   matches the recorded digest and fails closed when it does not. Without this, rules 1–3 are
   documentation rather than control.
5. **Fixtures demonstrate the contract; they do not define it.** A fixture is an example that
   must satisfy the schema. Adding a field to a fixture does not add it to the contract, and a
   fixture disagreeing with the schema is a fixture defect — which is why §7's set is a
   *minimum* and not a specification.

Rule 4 is the one that does work. Rules 1–3 describe an intention; rule 4 notices when the
intention lapses, which is what the absent version pin would otherwise have done.

## 7. Fixtures

Roadmap §14 rule 4: "Compatibility fixtures are shared by committed schema/example artifacts,
not copied prose." Read with §6b rule 5 — these demonstrate the schemas, they do not define
them.

Minimum set, produced by this repository:

- one `computed` bundle with decimal-string estimates and intervals;
- one `withheld` bundle with a minimum-data blocker;
- one `refused` bundle with a policy blocker;
- one `unavailable` bundle from a missing optional dependency;
- one bundle at an unsupported contract version, for the consumer's fail-closed test;
- one bundle carrying a decimal value that IEEE 754 cannot hold exactly.

Both repositories validate all six independently. That is the roadmap's Phase 2 acceptance
criterion, and it is achievable **before** any distribution question is answered — the fixtures
are committed files, not a package. Doing it first surfaces schema disagreements while they are
still cheap to fix.

## 8. Open questions

1. ~~Contract authority for an uncontracted dataset.~~ **Closed as a precondition in §4**, not
   an open question. The *mechanism* is parked to the integration specification; whether the
   precondition applies is settled.
2. Does `DataSnapshot` need to span file and database at v1, or can v1 be file-only with the
   database shape reserved? **File-only is recommended** — the roadmap's Phase 9 is far away
   and a reserved shape is cheaper than a wrong one.
3. ~~Where does the contract package live?~~ **Answered by the session direction — no package** — and
   §6b states the five rules that replace one. A contracts-only distribution stays available as
   a future option if the integration is revived and a real pin is needed.
4. Does `SemanticRole` publish this kit's seven roles as-is, or a superset? As-is. A superset
   invents roles no method consumes.

**Genuinely open: only 2 and 4**, and neither gates anything while the integration is deferred.
