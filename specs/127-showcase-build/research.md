# Phase 0 Research: Shareable Seshat Proof (Showcase Bundle)

All decisions below resolve the plan's open questions. Each records the decision,
the rationale, and the alternatives rejected. No decision recomputes readiness or
redefines an evidence schema.

## R1. Delivery shape: CLI verb vs skill/composer

- **Recommended default (open_for_human -- ratifier decides)**: a read-only **skill** (`.claude/skills/showcase-build/`) over a reusable **library function** in `src/seshat/showcase/`, no new top-level CLI verb. This is NOT auto-resolved: it is a reversible-but-costly product-identity choice routed to the ratifier (spec FR-005 + "Open for Human"); the ratifier confirms the skill default or amends FR-005 to a CLI verb.
- **Rationale for the default**: `docs/roadmap/decisions/cli-verbs-vs-skill-driven.md` is owner-ratified Option B (2026-07-07): the CLI stays a narrow gate; new capabilities ship as skills/composers. Spec 118 resolved the identical "the brief says a verb" tension the same way. The default rests on applying that ratified policy to a new capability -- but the Option B doc itself calls the verb-vs-skill choice a product-identity decision reserved for the owner, which is why the choice is routed to the ratifier rather than settled here.
- **Sibling-tension note (verified, surfaced for the ratifier)**: the peer `explorer`/`passport` verbs were added by spec 120, **created 2026-07-11 -- AFTER the 2026-07-07 ratification** (verified from `specs/120-agent-ecosystem-growth/spec.md`). They are therefore NOT a pre-ratification "grandfathered" exception; they are a live post-ratification precedent that could argue for verb-parity here. Skill is the recommended default (the ratified policy governs new capabilities), but the ratifier may override to verb-parity. The earlier "grandfathered" reasoning was dropped as factually wrong.
- **Alternatives rejected**: (a) `seshat showcase build` CLI verb -- cuts against ratified Option B and hard rule #1 (ratifier may still choose it for verb-parity with the sibling surfaces); (b) extending the explorer verb with a `--showcase` flag -- would mutate a shipped surface's contract.
- **Reversibility**: costly (a public verb is a compatibility contract); the library function keeps a future verb cheap to add if the owner later directs it.

## R2. "Redacted" (req 4) vs "remove" (req 7) vs Explorer fail-closed posture

- **Decision**: A live disclosure finding (secret, DSN/connection string, PII value, residual machine-local absolute path) **blocks generation fail-closed** -- reuse `disclosure.scan_disclosure`, match the Explorer's block posture (no partial/redacted page written). **CRITICAL correction**: the scan MUST run over the **FULL composed bundle body**, not the base readiness projection. `build_explorer_projection` sets `disclosure = base["disclosure"]`, which was scanned on the base projection BEFORE `_lineage` (metric-contract names + paths) and `_approval_receipts` (owner names) enrich the tables, and before any before/after content exists. Carrying that value through would gate on a result that never saw the bundle's own rendered content -- most dangerously the user-supplied Passport snapshot content in the before/after section. So `build_showcase_bundle` re-runs `scan_disclosure` over its assembled body and MERGES the base projection's invariant findings (pass-without-evidence / blocked-without-reason live only in `build_readiness_projection` and would be lost by a naive re-scan). The manifest's **"redacted"** category names only **by-design portability normalizations** the composer applies BEFORE the scan (absolute path -> repo-relative label, private/internal URL stripped). Pipeline order: compose -> normalize/redact -> scan full body -> fail-closed.
- **Rationale**: A "shareable proof" whose entire value is disclosure-safety cannot claim fail-closed while rendering unscanned content. Running the scan over the full body (after normalization) is the only way FR-009 is actually delivered, and it reconciles FR-010 (abs-path blocks) with FR-019 (abs-path -> repo-relative, redacted): normalization runs first, so only a residual path blocks. "Redacted" as a transparency list (what the composer changed for portability) is the honest reading of req 4 that does not weaken req 7.
- **Alternatives rejected**: masking secrets inline and shipping the bundle -- a masked secret is still a disclosure risk and breaks the fail-closed floor.

## R3. "Private URL" coverage in the disclosure scanner

- **Decision (preferred)**: Add a small **additive rule to the shared `disclosure.py` scanner** that flags private/internal URLs (e.g. RFC-1918 hosts, `localhost`, `*.internal`, `*.local`, bare-host intranet URLs) so the guarantee is central and unit-testable alongside the existing connection-string/abs-path rules.
- **Fallback**: If extending the shared scanner would broaden its blast radius across other consumers (Explorer, Passport) in a way the owner has not sanctioned, strip private URLs in the composer and list each under the manifest "redacted" category.
- **Rationale**: Central beats scattered for a fail-closed guarantee; but the scanner is a shared surface, so the fallback keeps this feature shippable without forcing a cross-surface change. Absolute-path and secret handling stay fail-closed either way.
- **Alternatives rejected**: ignoring private URLs -- req 7 explicitly lists "private URLs".

## R4. Badge semantics

- **Decision**: The badge summarizes the **highest contiguous `pass` stage** and the **count of passed stages** (e.g. "3/7 stages ready -- Gold: blocked"). Rendered as **inline SVG / HTML or a data URI**, fully offline. The richer **project card** adds per-table stage chips, blocker count, and approval count -- all evidence-derived.
- **Rationale**: The readiness spine forbids a fabricated confidence number; a contiguous-stage summary is a faithful, non-numeric-score projection of the evidence. Inline/data-URI rendering satisfies the offline requirement (a shields.io fetch would break req 6).
- **Alternatives rejected**: a percentage or letter grade (fabricated score, constitution-forbidden); an externally-fetched shield image (breaks offline).

## R5. Before/after comparability

- **Decision**: Two Passport snapshots are **comparable** iff they share `schema_version` and `scope` and differ in `source_revision`. When comparable, the diff is expressed in the Passport verify vocabulary (`verified` / `changed` / `missing` / `unavailable` / `incompatible`) plus per-stage status transitions. When not comparable (different scope, different schema, single snapshot, or none), the section is **omitted with a short truthful note** -- never a fabricated delta.
- **Rationale**: Reusing Passport's own `schema_version`/`scope`/`source_revision` and verdict vocabulary keeps comparison semantics consistent with the shipped snapshot and avoids inventing a second diff model.
- **Alternatives rejected**: diffing arbitrary revisions of the live projection (no immutable second snapshot to compare against); fabricating a delta when only one snapshot exists.

## R6. Accessibility / RTL alignment

- **Decision**: The showcase renders its **own shell** (new `showcase.css` / `showcase.js`) over the reused projection data, aligned to the shipped spec-102 rules `design_contrast` (WCAG contrast) and `design_categorical_distinctness` (colorblind-safe). RTL is a render mode: `dir="rtl"`, correct `lang`, mirrored layout, Arabic labels. The shipped `explorer.css` / `explorer.js` are NOT modified.
- **Rationale**: Aligning to the shipped a11y gate avoids inventing new criteria (FR-022) and keeps the proof credible to the Arabic retail audience. A separate shell protects the Explorer's output contract (FR-025).
- **Alternatives rejected**: editing `explorer.css` to add RTL -- mutates a shipped surface and risks the Explorer's browser tests; inventing bespoke contrast thresholds -- diverges from the shipped gate.

## Roadmap placement

- The showcase is a **Layer-6 delivery/handoff rendering surface**. It reads across all seven readiness stages and advances **none**; it gates nothing and grants nothing. It is a shareable projection of committed truth, consistent with the roadmap's "renders a projection of committed truth" framing for the Explorer.
