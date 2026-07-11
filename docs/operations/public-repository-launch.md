# Public repository launch guide

How to present, launch, and measure this repository publicly (spec 120,
FR-012 / SC-012). Everything here follows one rule: **public claims must
trace to shipped, gate-held capability** — a phase that has not shipped is
described as planned, or not at all.

## Repository metadata (FR-012)

Set these on the GitHub repository before announcing anything:

- **Description** (concise product statement):
  *"Agent-first Retail BI readiness system: evidence-gated medallion
  warehouse + Power BI governance. Statuses, never scores."*
- **Topics** (discoverable domains): `business-intelligence`, `power-bi`,
  `data-governance`, `postgresql`, `medallion-architecture`, `ai-agents`,
  `mcp`, `dax`, `data-quality`.
- **Social preview**: the brand board (`assets/brand/seshat-bi-brand-board.png`).
- **Installation status**: the README states plainly that `seshat-bi` is not
  yet on PyPI; install commands are labeled as targets. Keep that label
  accurate — remove it only in the release that actually publishes.

## Proof entry point

The first thing a visitor should be able to do is the five-minute offline
proof (US1):

```bash
seshat demo init && seshat demo run && seshat demo report --format html
```

Keep the README's proof screenshot current with the shipped renderer, and
keep the "expected blocked boundary" wording intact: the offline proof stops
honestly at the live-validation boundary. That truthful stop *is* the pitch.

## Integration entry point

Teams adopt review governance first (US2): point them at
`integrations/github-action/README.md`. The action is read-only, works from
a pinned released package, and needs no PR-comment token. Do not publish a
Marketplace wrapper until the one-way export seam
(`scripts/export_github_action.py`) verifies against this canonical source.

## Extension packs

Pack authors start at `docs/ecosystem/extension-packs.md` and the three
reference packs under `packs/reference/`. The pack proposal issue form is
the contribution path; there is no registry, and none should be implied.

## Benchmark

Present the safety benchmark (US7) strictly per its non-leaderboard policy
(`docs/ecosystem/agent-safety-benchmark.md`): categorical scenario outcomes,
full run disclosure, no aggregate anything. Decline requests to rank vendors.

## Explorer

The readiness explorer (US8) is a locally generated artifact. If a public
demo of it is desired, generate it from a synthetic workspace, review the
page manually, and host the reviewed file — publication is a human action
after disclosure review, never CI automation.

## Contribution entry point

The newcomer path is three documents
(`docs/contributing/first-contribution.md`, `contribution-lanes.yaml`,
`CONTRIBUTING.md`) plus five structured issue forms. Keep the maintainer
response expectations declared in the lanes file honest — if capacity drops,
change the declared expectation rather than silently missing it.

## Measuring adoption (SC-012)

SC-012 is measured **after** public availability, from public activity and
volunteered confirmations only — no hidden telemetry exists or may be added:

| Indicator | Source | Target (90 days) |
|-----------|--------|------------------|
| External issue participants | GitHub issue authors/commenters outside the maintainer team | ≥ 5 |
| External pull requests | PRs from non-maintainer accounts | ≥ 3 |
| Independent installations completing first success | Volunteered confirmations (compatibility reports, discussions) | ≥ 3 |

These are **adoption indicators, not readiness scores**; they are recorded
in the release notes as counts with sources, and a shortfall is reported as
a shortfall.

## Launch checklist

1. `CHANGELOG.md` and `README.md` claims reconciled with what is actually on
   `main` (per-phase availability, no forward claims).
2. All gates green: `ruff format --check`, `ruff check`, `pytest`,
   `retail check`, `retail semantic-check`, `retail kit-lint`.
3. Repository metadata set as above.
4. Issue forms and PR template render correctly on GitHub (open the new
   issue chooser and a draft PR to verify).
5. First release notes drafted with the release-notes-generator skill and
   approved by the named release owner.
