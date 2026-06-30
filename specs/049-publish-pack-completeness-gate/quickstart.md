# Quickstart: Publish-pack completeness gate (PP1)

How to exercise and verify the rule. All commands run from the repo root.

## Run the rule's unit tests

```bash
pytest -m unit tests/unit/test_publish_pack.py
```

Proves the behavioral contract (C1-C8, C10-C11): a required section left as a
`<placeholder>` or recorded as `GAP` -> a Finding; a missing section -> a Finding; a
fully filled pack -> no Finding; the generic template and `tests/` fixtures -> no
Finding; an empty tree -> no Finding; an unreadable pack -> a fail-loud Finding; the
approval slot is checked present-and-non-placeholder only (never the sign-off
contents); fixtures are generic/synthetic.

## Run the wiring + snapshot tests

```bash
pytest -m unit tests/unit/test_rules_wiring.py
```

Proves C9: the live registry id set equals `EXPECTED_RULE_IDS`,
`len(all_rules()) == len(EXPECTED_RULE_IDS)`, and the new rule submodule is
auto-discovered by `pkgutil` (no `registry.py` edit needed).

## Regenerate the rules manifest

```bash
retail manifest --repo .
```

Regenerates `docs/rules/rules-manifest.json` from the live registry so it contains
the new id. The 043 golden-snapshot test fails if the manifest is stale -- confirm
the only intended diff is the added id.

## Run the full static gate

```bash
retail check
```

Proves C12/C14: on the current tree (one filled handoff pack at
`mappings/retail_store_sales/handoff/bi-handoff-pack.md`) the rule reports no new
Finding, performs no network/DB access, and writes nothing. It fires only on an
incomplete committed pack.

## Lint

```bash
ruff check src/retail/rules/publish_pack.py tests/unit/test_publish_pack.py
```

Confirm ASCII / UTF-8 no BOM and stdlib-only imports.
