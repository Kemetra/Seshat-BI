# Headless analysis engine — boundary proposal

- **Status:** **DRAFT — planning only.** Not authored, not ratified, not an ADR, not a spec.
  Written 2026-08-05 during a cross-repository planning pass against
  `Kemetra/Khepri@db98f4b` (its merged architecture package, PR #97) and this repository at
  `728de12`. It authorizes nothing and adds no
  runtime code.
- **Would become:** `[SESHAT-ADR-BOUNDARY]` — a new ADR. Its number is derived from `docs/decisions/`
  at drafting time and is not allocated here. The implementing spec
  `[SESHAT-SPEC-ENGINE]` is **deferred** — see below.
- **Direction reflected (not evidence):** define the boundary now, **defer the integration** past
  the consuming product's first two milestones. Given by that product's owner in a working session
  on 2026-08-05 and recorded in neither repository, so it is a planning input rather than an
  approval. Only the ADR proceeds. **No spec number is
  allocated or reserved** — this repository already carries four documented duplicate-number
  pairs, so a number claimed early and left unused is a hazard, not a safeguard.
- **Read with:** `khepri-consumer-boundary.md`, `analysis-evidence-contracts.md`,
  `statistical-evidence-engine.md` (the current engine), `product-modules.md` (the authority
  taxonomy this must not weaken).
- **Depends on:** spec 138 closing. `CLAUDE.md` — "At most ONE of the two may be in
  implementation at a time (spec 138 FR-026)."

---

## One line

> The statistical core already is a governed engine; it is not yet *reachable* by a caller who
> has no Seshat repository. Removing the repository root is the whole of the change.

## Why this exists

`Kemetra/Khepri` is a commercial retail analytics product. An owner-supplied cross-repository
roadmap (2026-08-05) directs that Khepri consume governed analytical evidence from this
repository rather than build a second statistical engine — which is the outcome both
repositories want, since a second engine producing numbers is the failure the contract-binding
rules exist to prevent.

Khepri cannot consume this engine today. Not because of policy, but because of a signature.

## The blocking fact

```python
# src/seshat/statistical/runtime.py:399
def run_analysis(repo_root: Path, spec: AnalysisSpec, provider: DataProvider) -> ...

# src/seshat/statistical/policy.py:284
def evaluate_policy(repo_root: Path, spec: AnalysisSpec) -> PolicyDecision
```

`evaluate_policy` reads governance off the working set: readiness documents
(`policy.py:59`), metric contract authority (`policy.py:117`), and PII evidence
(`policy.py:103`). `_governance_reference` (`runtime.py:84-98`) resolves cited paths against
`repo_root` and digests them into the evidence.

A caller with no Seshat checkout has no `repo_root` to pass. That is the entire gap.

## What is already right, and must not be disturbed

Three properties make this a small change rather than a rewrite.

**1. The contract surface is already dependency-free.**

```python
# src/seshat/statistical/__init__.py
"""Governed statistical evidence contracts.
The numerical implementations are imported lazily by the method registry.
Importing this package keeps every optional numerical dependency unloaded.
"""
ENGINE_VERSION = "1.0"
```

A consumer can import `AnalysisSpec`, `AnalysisEvidence`, `Outcome`, `Estimate`, `Interval`,
`Blocker`, `Diagnostic`, `MethodSpec`, `ColumnBinding`, and `TestStatistic` without pulling
NumPy, SciPy, statsmodels, or ruptures.

**2. The coupling has exactly two importers.**

`src/seshat/cli/commands/analyze.py` and `src/seshat/statistical/registry.py`. The CLI is the
only consumer that supplies a repository root. There is no diffuse dependency to untangle.

**3. The authority model is already correct and is not what changes.**

`statistical-evidence-engine.md`: the core "cannot define or revise a metric contract; cannot
grant grain, PII, rollup, evidence, or publication approval; cannot change a readiness status;
cannot promote association to causation; `computed` is a numerical completion state, not
acceptance." Evidence records `authority: derived-evidence-only`, `review_state: pending`,
`readiness_effect: none; named-human approval required`.

**None of that weakens.** ADR-0008 gives create-truth and grant-approval to Core Authority
alone. This proposal changes *where policy inputs come from*, never *what policy decides*.

## The proposed shape: invert the read

Replace the `Path` parameter with an already-materialized governance context.

```text
TODAY
  caller ──► run_analysis(repo_root, spec, provider)
                 └──► evaluate_policy(repo_root, spec)
                          └──► reads readiness-status.yaml, metric contracts,
                               PII evidence from the working set

PROPOSED
  CLI ──► load_governance_context(repo_root)  ──┐   (new; preserves today's behaviour)
                                                 ├──► run_analysis(context, spec, provider)
  headless caller ──► GovernanceContext(...) ───┘         └──► evaluate_policy(context, spec)
                                                                   └──► same rules, injected inputs
```

- `GovernanceContext` carries metric contracts, readiness states, PII evidence, and the
  governance references currently digested into evidence.
- `load_governance_context(repo_root)` is the CLI's loader. Today's behaviour is preserved
  byte-for-byte, and the existing `seshat analyze` tests are the regression suite for that.
- No policy rule changes. `evaluate_policy`'s body is unchanged apart from its input type.

## The one hazard, named

**A headless boundary is exactly where an approval bypass would enter.** If a caller can
construct a `GovernanceContext`, a caller can construct one that *claims* readiness.

The context must carry **evidence to be evaluated, never a verdict**:

- no field means "this is approved";
- readiness states are inputs to `_readiness_blockers`, not substitutes for it;
- a claimed approval with no evidence behind it produces `refused`.

**Required adversarial test:** a request whose context asserts a passing readiness stage with
no supporting evidence must be `refused`, with the blocker naming the missing evidence. Without
that test, the facade is a hole in Principle V, and no amount of prose closes it.

## Constraints the proposal must satisfy

From the cross-repository roadmap's Phase 3, checked against current state:

| Constraint | Today | After |
|---|---|---|
| No CLI subprocess requirement | Met — `run_analysis` is a Python function | Met |
| No repository-root lock requirement | **Not met** — `repo_root: Path` | Met |
| No Power BI state requirement | Met | Met |
| No dbt or Dagster requirement | Met — `statistical/` imports neither | Met |
| No customer authentication state | Met | Met |
| No readiness approval side effects | **Partially** — reads readiness, never writes it; but the read is a filesystem coupling | Met, with the §hazard test |
| No arbitrary executable method registration | Met — eight methods, closed by schema | Met |

## What does not change

- The closed catalog: eight methods, all version `1.0`. Nothing is added for Khepri.
- Outcome semantics: `computed` / `withheld` / `refused` / `unavailable` / `failed`, and the
  categorical exit codes 0–4.
- Minimum-data floors, prior-only time methods, degenerate-baseline detection,
  association-not-causation retention.
- The Gold provider's read-only, count-checked, ceilinged, PostgreSQL-only boundary.
- The local CSV provider's content-digest-instead-of-path discipline.
- Every adapter: dbt, Dagster, Power BI, PBIR. This proposal does not touch them.
- `src/seshat/report/`. It renders governed BI evidence for this kit's clients and is out of
  scope here.

## What this proposal does **not** propose

- **No retail methods.** This engine has no revenue, margin, growth-decomposition,
  concentration, or basket method, and this proposal adds none. Those live in Khepri under its
  approved specifications RRA-004 and RRA-008 and stay there. The cross-repository decision
  draft (the Khepri boundary decision (`[DEC-BOUNDARY]`; not yet allocated)) records the condition under which any transfer could later happen —
  a parity fixture both implementations pass — and no transfer is proposed.
- **No dependency on Khepri.** In any direction. Seshat must remain testable with no Khepri
  state, per the roadmap's own §14 rule 8 and this kit's independence.
- **No forecast consumption by Khepri.** `Khepri/governance/families/RRA.md` excludes
  forecasting. This engine keeps its `forecast` method for its own consumers; the Khepri
  boundary does not carry it.
- **No new authority category.** The statistical core stays an `execution-capable` Product
  Module under ADR-0008. A headless facade does not cross an external trust boundary — the
  caller is in-process — so it does not become an Execution Adapter.

## The metric-authority precondition

**What does a caller with no Seshat metric contract get?** Settled, and it constrains the
facade's shape directly: either the request carries **Khepri-approved metric authority through a
versioned consumer-authority contract** that this engine evaluates and whose origin the evidence
records on its face, or the request is **`refused`**. There is no relaxed profile — see
`analysis-evidence-contracts.md` §4, which withdraws the earlier recommendation of one.

**Consequence for `GovernanceContext`.** It must be able to carry consumer authority *as
evidence to be evaluated*, with its origin attributable — not as a flag that switches policy off.
That is the same constraint as the hazard above, arriving from a different direction, and it is
why the two must be designed together.

## Open questions

1. **Is `GovernanceContext` a contract or an internal type?** If a consumer constructs one, it
   is a contract. If a consumer only sends an `AnalysisRequest` and the context is derived from
   it, it stays internal. **The second is preferable** — it keeps the governance vocabulary
   inside this repository, where ADR-0008 governs it.
2. ~~Does the facade ship before or after distribution is answered?~~ **Answered by the direction
   above, not by an approval:**
   contracts are exchanged as committed files under the five source-of-truth rules
   (`analysis-evidence-contracts.md` §6b); no package is published; the facade is deferred with
   the rest of the integration. The facade would still be worth building for this kit's own
   callers if a non-CLI consumer appears internally — that would be its own spec, on its own
   merits, not a cross-repository obligation.
