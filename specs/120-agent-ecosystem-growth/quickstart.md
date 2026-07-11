# Planning Quickstart: Agent Ecosystem Growth

This is the target acceptance walkthrough. Commands describe the planned observable
surface; they are not claims that feature 120 is implemented yet.

## Prerequisite

Complete spec 119's public-beta installation path and work in a git repository created by
`seshat init-project` or the Seshat BI repository itself.

## Phase 1 - Five-Minute Proof

```powershell
seshat demo init
seshat demo run
seshat demo report --format html --output .seshat-output/demo/index.html
```

Expected: a local static report shows all seven stages. Offline-capable stages cite
evidence; Gold Ready and later remain visibly blocked where live proof is unavailable.
The report contains no score, credentials, source rows, or local absolute path.

## Phase 2 - Change Review

Add the documented Seshat review action to a sample repository and open two changes:

1. A documentation-only compliant change.
2. A seeded silver migration while Mapping Ready is blocked.

Expected: the first reports the checks and their boundary. The second fails with the
mapping gate, blocker, locator, and corrective next action. JSON is always retained;
SARIF is uploaded only where supported. No PR comment token is required.

## Phase 3 - Agent Governor

Install the optional MCP extra and register the local stdio server with an MCP host:

```powershell
pipx inject seshat-bi "mcp>=1.28,<2"
seshat mcp --repo .
```

Call `seshat_get_next_action` for a blocked mapping and then request silver work.

Expected: structured status/evidence/blockers are returned and the premature request is
refused. File, database, Power BI, approval, and readiness-state write probes remain
unchanged.

## Phase 4 - Passport

```powershell
seshat passport export --table retail_store_sales --output .seshat-output/rss.passport.json
seshat passport verify .seshat-output/rss.passport.json
```

Expected: unchanged evidence verifies. After changing a copied referenced fixture, the
verification result is `changed`; the source readiness status is untouched.

## Phase 5 - Packs

```powershell
seshat pack scaffold --category kpi --id example.sales
seshat pack validate .seshat-output/packs/example.sales
seshat pack validate packs/reference/kpi-basic
```

Expected: the reference pack passes. Seeded packs containing executable hooks, a stage
override, duplicate IDs, secrets, or an undeclared conflict fail before contributing to
any projection.

## Phase 6 - Contributor Path

Open the repository's new-issue chooser and verify five structured paths. Open a draft PR
and verify its template requests stage served, scope, tests, evidence, human decisions,
and secret/data safety. Follow one starter lane using no more than three linked documents.

## Phase 7 - Safety Benchmark

```powershell
seshat benchmark run --participant scripted-reference --scenarios benchmark/scenarios --output .seshat-output/benchmark/run.json
seshat benchmark report .seshat-output/benchmark/run.json
```

Expected: every scenario displays expected and observed categorical behavior. The report
shows over-refusal and mismatches, contains no aggregate score, and discloses run
conditions.

## Phase 8 - Static Explorer

```powershell
seshat explorer build --repo . --output .seshat-output/explorer
```

Expected: the generated offline site supports table/stage browsing, evidence, blockers,
approval receipts, next actions, and available metric lineage. Desktop and mobile
screenshots show no overlap or blank content. Generation changes no source artifact.

## Cross-Cutting Failure Tests

- Remove an evidence file: passport and explorer report `missing`, never pass.
- Insert a fake DSN or absolute path into a generated fixture: disclosure blocks output
  publication.
- Select conflicting packs: selection fails before rendering.
- Use an unknown schema major: every consumer fails closed with compatibility guidance.
- Run without network or DB: MVP, passport, packs, reference benchmark, and explorer stay
  usable; live-dependent facts remain pending or blocked.

## Final Verification

```powershell
ruff format --check src tests
ruff check src tests
pytest -m unit
retail check
retail semantic-check --repo .
retail kit-lint --repo .
```

Story-specific contract/integration suites are added during implementation. Full live-DB
validation is not required for this feature because no story claims a new live pass.
