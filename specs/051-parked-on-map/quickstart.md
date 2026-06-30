# Quickstart: DF1 Parked-On Map

## Run the rule (unit tests)

```bash
python -m pytest tests/unit/test_parked_on.py -m unit -q
```

The suite mirrors `test_status_claims.py`: synthetic manifests + roadmap docs +
evidence/shipped artifacts staged under `tmp_path` into a real `RuleContext`, plus a
live-manifest-vs-real-repo guard that asserts the shipped `docs/quality/parked-on.yaml`
reconciles to zero findings against `git ls-files`.

## Run the full gate

```bash
retail check          # DF1 runs as part of the static rule set; non-zero exit on any DF1 ERROR
```

## Regenerate the rule-registry manifest (after wiring DF1)

```bash
retail manifest --repo .     # rewrites docs/rules/rules-manifest.json from the live registry (37 -> 38 entries)
```

The rule-registry snapshot test fails if the committed JSON drifts from the live
registry, so run this whenever a rule is added/removed.

## Edit the parked-on manifest

Add an edge to `docs/quality/parked-on.yaml` under `edges:` with `id`, `blocked`,
`parked_on`, `doc`, `anchor` (a literal sentence from the cited doc), and `evidence` (a
tracked deferred-spec/spec path). Optionally add `shipped_when_tracked` so the park is
auto-flagged when the target ships. Keep entries generic (no C086/pharmacy facts).

## Verify wiring drift guard

```bash
python -m pytest tests/unit/test_rules_wiring.py -m unit -q
```

Passes only when `"DF1"` is in `EXPECTED_RULE_IDS` and the live registry matches.
