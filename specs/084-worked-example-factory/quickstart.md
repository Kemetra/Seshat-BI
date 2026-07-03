# Quickstart: Using the Worked-Example Factory

**Feature**: `specs/084-worked-example-factory/` | **Phase**: 1 (design)

**Audience**: a future author (human or agent) who has decided to build a new,
generic worked example and wants to know where to start. This quickstart
assumes the process is already ratified/adopted -- it does not itself authorize
starting a new example (that is a separate, future decision, out of scope for
this spec chain).

## Before you start

1. Read `docs/worked-examples/retail-store-sales.md` once, for the *shape* of
   a finished example -- not to copy its answers (Constitution Principle VII).
2. Read `research.md` Sec 1 in this spec dir and pick a candidate domain that
   stresses a genericity axis the existing example(s) do not yet cover.
3. Confirm the domain is expressible with the currently-shipped RC1-RC16
   defaults and `retail check` rule set (contract item C-A2). If it is not,
   STOP -- defer the domain or propose the new default/rule as its own,
   separate spec (never bundled into a worked-example PR).
4. Confirm there is no client-specific fact anywhere near the candidate
   (contract item C-A3). If the "domain" is really C086 or derived from it,
   STOP -- that example is archived and MUST NOT be resurrected.

## The sequence (mirrors the readiness spine, one gate at a time)

This is not a new method -- it is `docs/medallion-playbook.md`'s phases,
formalized by the five mapping-gate templates, exactly as Constitution
Principle IV describes. The factory adds nothing here except the completeness
checklist to apply at the end of each stage.

1. **Profile the source** (Source Ready). Fill
   `templates/source-profile.md` -> `mappings/<table>/source-profile.md`. Cite
   numbers, not adjectives (the template's own rule). Apply contract items
   C-B1-C-B2.
2. **Map it** (Mapping Ready -- artifacts). Fill `templates/source-map.yaml`,
   `templates/assumptions.md`, `templates/unresolved-questions.md` into
   `mappings/<table>/`. Decide grain and PK first. Record only *deviations*
   from the RC defaults, each with a triggering data fact. Drive
   `unresolved-questions.md` to `Gate status: CLEARED` -- every question
   `answered`, not left `open`. Apply contract items C-C1-C-C4.
   **STOP here if any question requires a judgment call the agent cannot make
   alone** (grain ambiguity, PII, business rollups, sentinel-vs-null, returns
   identification) -- per Constitution Principle V, raise it and wait for the
   named owner; do not guess.
3. **Human reviews the map** (Mapping Ready -- the approval; Tier 2, human/live-
   gated). This is a named-human action the factory process cannot perform.
   Absent it, the example stops here and stays at Tier 1 (repo-only)
   completeness for this stage.
4. **Build silver, then gold** (Silver Ready, Gold Ready). Author the numbered
   migrations following RC7/RC13 (silver) and RC14/RC15 (gold). Run
   `retail check` -- it must exit 0. If a live DB is reachable, run
   `retail validate` and fill `reconciliation-report.md` with real numbers; if
   not, mark those stages `blocked` / `[PENDING LIVE PROFILE]` in
   `readiness-status.yaml` and continue -- never fabricate a pass (AGENTS.md
   "Live DB steps"). Apply contract items C-D1-C-D4.
5. **Define metric contracts, build the semantic model** (Semantic Model
   Ready). Author `mappings/<table>/metrics/*.yaml` per
   `templates/metric-contract.yaml`; author the governed PBIP/TMDL model with
   a parameterized connection (never a baked-in host). Apply contract items
   C-E1-C-E2. The `semantic_model_ready` approval (a named metric owner) is
   Tier 2.
6. **Design the dashboard from the approved contracts** (Dashboard Ready).
   Author `mappings/<table>/design/` (layout, visual list, binding map); every
   measure-bearing visual binds to exactly one contract. Apply contract items
   C-F1-C-F2. The `dashboard_ready` approval (a named report owner) is Tier 2.
7. **Assemble the handoff pack** (Publish Ready). Author
   `mappings/<table>/handoff/` per `templates/handoff/`. Apply contract item
   C-G1. The `publish_ready` approval (data-owner/governance) is Tier 2; if an
   approved artifact later changes materially, retract the approval honestly
   (`warning`, not silently kept `pass`) -- this is the precedent
   retail_store_sales itself sets (its doc Sec 7), not a failure state.
8. **Write the narrative doc and register it**. Author
   `docs/worked-examples/<table>.md` following the section structure of
   `retail-store-sales.md`; add a row to `docs/worked-examples/README.md`.
   Apply contract items C-H1-C-H5.

## Where the process legitimately stops

- **No live DB available**: stop at Tier 1 (repo-only) completeness for every
  stage from Gold Ready onward. This is a valid, honest stopping point -- report
  it as such, never as a failure or as a silent `pass`.
- **No human reviewer available**: stop before any `approvals[]` entry. An
  agent-run factory process can produce a fully Tier-1-complete example and
  then hand it to a human for the four approval seams; it cannot grant them
  itself (Constitution Principle V).
- **A judgment call arises mid-build**: stop and record it in
  `unresolved-questions.md`; do not proceed past a blocking question.
- **A domain needs a new default or rule**: stop describing it as viable under
  this process; that is a separate spec.

## Applying the completeness contract

At any point, `contracts/worked-example-completeness.md` tells you exactly
which items are satisfied and which are not -- check items off with a cited
file/run, never mark an item done from memory. Use it both mid-build (to know
what is left) and at the end (to state a verdict: Tier-1 complete, or
Tier-1-and-2 complete, or "not complete, missing item X").

## What this quickstart is not

- Not a guarantee that any specific domain (inventory, loyalty) will turn out
  to be buildable -- that is discovered during Source Ready profiling, not
  decided here.
- Not an automation: every step above is the same manual/agent-assisted
  process retail_store_sales already went through; this quickstart names the
  steps and the stopping points, it does not add tooling.
- Not a shortcut past any existing gate: the source-mapping gate, `retail
  check`, `retail validate`, and the four named-human approvals all apply
  exactly as they do for any table (Constitution Principles I, IV, V, VIII).
