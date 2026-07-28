# Governed statistical evidence workflow

Use this route when a decision question needs numerical evidence beyond the
display-only guardrails in the framing cards. The engine computes derived
evidence from approved business meaning; it never defines a metric, grants an
approval, changes readiness, or proves a causal claim.

## Preconditions

The analysis must cite:

- one committed per-table readiness status whose Gold and Semantic Model stages
  pass and whose Gold evidence includes a successful live validation;
- every metric contract used by the analysis, with explicit metric-owner
  approval and one compatible observation grain;
- only approved `gold.*` bindings and, when applicable, existing PII approval
  evidence;
- a committed analysis specification using one closed method and repo-relative
  output paths.

Never self-grant a missing approval. A failed precondition is a concrete blocker,
not an invitation to edit readiness.

## Eight-step route

1. Confirm the decision question, population, observation grain, and already
   approved metric. If meaning is unclear, stop at the metric-contract owner.
2. Read the cited readiness status and metric contracts. Record any factual
   blocker; do not skip the Gold or Semantic Model gates.
3. Draft and commit the analysis specification. Choose only roles and parameters
   allowed by the closed schema. Do not write an approval into its inputs.
4. Validate without acquiring data:

   ```console
   seshat analyze validate --repo . --spec <analysis.analysis.yaml> --format json
   ```

5. Run exactly one governed provider:

   ```console
   seshat analyze run --repo . --spec <analysis.analysis.yaml> \
     --provider local_csv --input <approved-extract.csv> --format json
   ```

   For the read-only Gold adapter, use `--provider gold` and keep connection
   settings only in the gitignored `.env`.
6. Inspect the categorical outcome, estimates, intervals, tests, diagnostics,
   cautions, blockers, governance hashes, and input digest. `withheld`,
   `refused`, `failed`, and `unavailable` each require the recorded recovery
   action; never convert one to a numerical claim.
7. Stop for the named human. The review remains `pending`, authority remains
   `derived-evidence-only`, and `readiness_effect` remains
   `none; named-human approval required`. Never self-grant acceptance.
8. Permit the narrative brief to cite only accepted review evidence, within the
   claim and caveats the named reviewer recorded. Rejection or requested changes
   return to the specification; they do not authorize silent recomputation.

## Method and provider boundary

The closed method catalog is documented in
`../../docs/architecture/statistical-evidence-engine.md`. The local CSV provider
is an offline Product Module input seam. The Gold provider is a read-only
Execution Adapter that runs compiler-produced Gold-only `SELECT` statements.
Neither provider exposes raw rows in evidence.

Use `seshat analyze render` only to reconstruct a Markdown review from valid
immutable evidence. It does not recompute the method or rewrite the evidence.
