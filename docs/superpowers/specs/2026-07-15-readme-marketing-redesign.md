# README Marketing Redesign

**Date:** 2026-07-15  
**Status:** Approved direction  
**Scope:** Replace the repository README with a product-led, evidence-first public
landing page for adopters, contributors, and sponsors.

## Objective

Make a first-time visitor understand Seshat BI in under 30 seconds, believe its
claims, and find one clear next action. The README should turn product credibility
into three outcomes, in this order:

1. Try or evaluate Seshat BI.
2. Contribute through a bounded starter path.
3. Sponsor a useful, public roadmap lane.

## Positioning

Seshat BI is the evidence-gated path from messy retail data to trusted Power BI.
Its differentiator is not automatic dashboard generation. It is an agent-first
readiness system that refuses to skip mapping, validation, metric definition, or
human approval.

Primary promise:

> From messy retail data to trusted Power BI -- with evidence at every gate.

Supporting proof statement:

> Seven readiness stages. No invented mappings. No fabricated scores. No dashboard
> before its metrics are defined.

## Audience hierarchy

### 1. Adopters

BI developers, analytics engineers, data engineers, analytics leaders, and agent
builders evaluating whether Seshat BI is credible and usable.

Their CTA is `Run the demo`, supported by a short install path and links to the
architecture, readiness model, and worked example.

### 2. Contributors

Open-source contributors who need to see why the project matters, where their
skills fit, and how to make a first change without learning the entire repository.

Their CTA is `Find your first contribution`, linked to the existing newcomer guide
and bounded starter lanes.

### 3. Sponsors

Individuals and organizations that benefit from safer BI delivery, open governance
patterns, and agent reliability.

Their CTA is `Sponsor a roadmap lane`. Because the repository has no verified
funding destination today, the README must not invent a GitHub Sponsors account or
payment link. It will direct prospective sponsors to a labeled GitHub inquiry path
and explain what support accelerates. A future verified funding URL can replace
that link without changing the narrative.

## Page structure

### Hero

- Use the supplied Seshat logo, already committed as
  `assets/brand/seshat-bi-logo.png`, at a size that remains legible without forcing
  excessive scrolling.
- Lead with the primary promise and one-sentence product definition.
- Keep badges to factual signals only: release, Python, license, PostgreSQL, and
  Power BI/PBIP.
- Present three text CTAs: run the demo, contribute, and sponsor.

### The problem and product answer

Open with the cost of ungoverned BI: polished dashboards can still carry undefined
metrics, unsafe source assumptions, or unreconciled numbers. Then explain Seshat's
answer in plain language: stage order, recorded evidence, blockers, and named human
approvals.

### Seven-stage readiness spine

Keep one compact Mermaid flow showing Source -> Mapping -> Silver -> Gold ->
Semantic Model -> Dashboard -> Publish. Follow it with the four non-negotiable
stops. This is the core product mental model.

### Fast proof

Place the offline demo before long capability lists. Show the three demo commands,
the existing readiness-proof image, and an honest note that offline proof stops at
the live database boundary.

### Why teams choose Seshat

Use four concise value pillars:

- Evidence over confidence scores.
- Human judgment stays human.
- Agent-safe sequencing by construction.
- Power BI consumes governed gold data and approved metric contracts.

### How it works

Use a small workflow diagram from source to governed Power BI and a short table that
maps each layer to its responsibility. Avoid duplicating the full capability ledger.

### Built today

Show a curated list of the strongest shipped capabilities, then place the complete
catalog inside a collapsed details block. Planned or gated work must be visibly
separate and never presented as shipped.

### Contributor invitation

Make contribution feel bounded and welcoming:

- Link the first-contribution guide.
- Link starter issues and contribution lanes.
- Name useful contribution types: governance rules, database compatibility,
  documentation, fixtures, Power BI artifacts, and agent workflows.
- Keep setup and commit rules in `CONTRIBUTING.md`; the README only previews them.

### Sponsor invitation

Explain that sponsorship can accelerate public, evidence-backed work such as
database compatibility, reproducible demo coverage, documentation, and contributor
support. State that sponsorship cannot buy a readiness approval or weaken a gate.
Do not show an empty sponsor-logo grid.

### Technical reference and footer

Close with compact install options, repository map, support/docs links, roadmap,
license, and the brand line: `Governed knowledge. Measured structure. Trusted BI.`

## Visual and editorial rules

- Use the existing navy, gold, teal, and ivory identity.
- Let the brand logo carry the Egyptian motif; keep diagrams technical and clean.
- Use short sections, descriptive headings, and progressive disclosure.
- Prefer proof near each claim rather than a large unsupported feature list.
- Preserve the distinction between `seshat` as the primary command and `retail` as
  the compatibility alias.
- Use ASCII punctuation in committed prose.
- Avoid hype terms such as revolutionary, magical, fully automated, or AI-powered
  without qualification.
- Never imply live validation passed when only static or offline proof exists.

## Truth and scope constraints

- No readiness score.
- No self-granted approvals.
- No silver before Mapping Ready passes.
- No Power BI before gold validation.
- No dashboard before metric contracts.
- No claim that the deferred execution adapter is available.
- No fabricated adoption, contributor, star, download, or sponsor statistics.
- No unverified funding link.

## Verification

The completed README will be checked for:

1. Every local image and documentation link resolving in the repository.
2. Mermaid blocks using valid syntax.
3. Install and demo commands matching the current CLI and package metadata.
4. ASCII/UTF-8 text compliance and no accidental secret or real DSN.
5. `seshat check` passing for the documentation change.
6. The first screen communicating product, proof, and the three CTAs without
   requiring readers to scan the full document.

## Non-goals

- Redesigning the logo or generating new brand art.
- Changing product behavior, readiness rules, or the roadmap.
- Creating a funding account or asserting a sponsorship platform exists.
- Replacing the detailed contribution, installation, architecture, or governance
  documentation.
