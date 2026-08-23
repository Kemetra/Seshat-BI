# Onboarding -- Seshat BI

**Seshat BI answers one question:** *is this retail source ready to become
trusted Power BI?* It profiles sources, governs mappings, validates the medallion
warehouse, binds metrics to contracts, and prepares Power BI delivery -- without
skipping the human decisions that make analytics trustworthy.

This page is a **router**. It owns no knowledge of its own: it sends you to the
one document written for your situation, and each destination below says plainly
who it is for. Read this page once, then leave it.

## Pick your arrival

| You are... | Start here | You will end with |
|---|---|---|
| **Using the tool** on a retail source | [`COMPASS.md`](./COMPASS.md) | the correct next action, or a clarifying question |
| **An agent** working in this repo | [`AGENTS.md`](./AGENTS.md) | the operating contract, then `COMPASS.md` |
| **Contributing code** for the first time | [`docs/contributing/first-contribution.md`](./docs/contributing/first-contribution.md) | a claimed starter lane and a PR |
| **Looking for a specific task or symptom** | [`docs/knowledge-map.md`](./docs/knowledge-map.md) | the one skill/doc route that handles it |

If none of those fit, route 22 of the knowledge map ("unknown / ambiguous
request") is the documented catch-all.

## The four ideas worth knowing before you start

You do not need these to *begin* -- the routes above work without them -- but
they explain why the tool behaves as it does.

1. **Readiness is a stage, not a score.** Every table moves through seven
   stages: `source_ready` -> `mapping_ready` -> `silver_ready` -> `gold_ready` ->
   `semantic_model_ready` -> `dashboard_ready` -> `publish_ready`. A stage opens
   only once the prior one passes. See
   [`docs/readiness/readiness-model.md`](./docs/readiness/readiness-model.md).

2. **The agent never approves its own work.** Approvals are a human seam. An
   agent can prepare a request and show the evidence, but `never_self_grant_approval`
   is a hard stop, and readiness is never a made-up confidence number.

3. **Data flows bronze -> silver -> gold, and Power BI reads `gold` only.** The
   route is [`docs/medallion-playbook.md`](./docs/medallion-playbook.md).

4. **Business meaning is decided before it is implemented.** What a KPI *means*
   (grain, additivity, ambiguity) is settled in the retail-KPI layer and recorded
   as a contract; SQL and DAX then implement that contract rather than inventing
   the meaning.

## Setting up a workstation

Dev setup -- Python 3.13, `pip install -e ".[dev]"`, and PR mechanics -- lives in
[`CONTRIBUTING.md`](./CONTRIBUTING.md). Tooling one maintainer actually leans on
(notably the CodeScene MCP, which backs a CI gate on every PR) is listed in
[`docs/contributing/claude-code-usage-snapshot.md`](./docs/contributing/claude-code-usage-snapshot.md).

## Reference shelf

Reach for these when a specific need arises; none is required reading.

- [`docs/glossary.md`](./docs/glossary.md) -- terms, abbreviations, and the
  static rule-id families (`D8`, `C2`, `S2`, `G1`, ...).
- [`docs/faq.md`](./docs/faq.md) -- common questions, each answer source-cited.
- [`docs/worked-examples/README.md`](./docs/worked-examples/README.md) -- the
  worked-example index; its full-spine example (`retail-store-sales.md`) is the
  documented starting point for new retail mart work.
- [`docs/conventions.md`](./docs/conventions.md) -- SQL and DAX naming rules.
- [`docs/roadmap/roadmap.md`](./docs/roadmap/roadmap.md) -- the authoritative
  roadmap. (`docs/roadmap/idea-backlog.md` is exploratory and commits to nothing.)
