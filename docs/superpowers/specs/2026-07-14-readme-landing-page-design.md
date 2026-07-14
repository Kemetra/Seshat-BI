# README landing-page rewrite -- design

**Date:** 2026-07-14
**Status:** Draft (awaiting user review) -- revised after external review (2026-07-14)
**Scope:** Documentation + brand assets + one **brand-rule amendment**
(`docs/brand/visual-identity.md` + README brand text). No source, tests, manifests,
CI, package metadata, version numbers, tags, or release assets.

> **Governance note:** this spec now includes a deliberate amendment to the brand's
> "star must be seven-pointed" rule. That is an owner brand decision, made
> explicitly by the owner ("show the uniqueness of the hieroglyphic goddess brand"),
> not an agent-initiated rule change. It ships on its own branch/PR for owner
> sign-off before merge.

## Goal

Rewrite `README.md` as a marketing-appeal landing page that attracts users, while
keeping every factual claim strictly true.

**Truthfulness is a manual discipline, not a gate guarantee.** External review
established that no static rule verifies README claim truthfulness: the prose-honesty
rules (SC1 `status-claims.yaml`, SC2 `rule-count-claims.yaml`, DR1
`design-stale-phrases.yaml`) all anchor on *other* files (glossary.md,
capability-state.md, etc.), and DR1's phrase list is empty. The only README-touching
gate risks are C2 (fires on a secret-shaped line, e.g. a pasted
`postgresql://user:pass@host` DSN) and P1/G3/G4 (README must exist / structural). So
`retail check` staying green does NOT prove the marketing copy is accurate -- a
claim-by-claim manual truthfulness pass (below) is the real safeguard.

## Decisions (from brainstorming)

- **Primary goal:** full rewrite for marketing appeal.
- **Tone:** bold but strictly true -- confident, benefits-first, emotionally
  engaging, but no invented metrics, testimonials, "used by" logos, or fabricated
  scores. Every factual claim must remain accurate (v0.2.0 is on PyPI; seven-stage
  gate; readiness is `status` + `evidence` + `blocking_reasons`, never a number).
- **Audience:** broad -- a strong universal hook first, then short per-role angles
  for BI developers, AI-agent builders, and analytics leads.
- **Structure:** Approach A -- landing page on top; deep reference retained below but
  **genuinely trimmed**: the two largest tables (the ~26-row "What is built today"
  capability table and the Repository-layout table) move behind `<details>`
  collapsibles, with a short inline highlight strip left in the open body. This
  honors the owner's "trim deep detail into links" choice. (Correcting an earlier
  draft that said content is "not moved" -- see amendment note below.)
- **Assets:** two new brand PNGs added to `assets/brand/`. The existing
  `seshat-bi-hero.svg` is NOT claimed as a "fallback" (an unreferenced file is not a
  fallback); it simply remains in the repo, unused by the README.
- **Branch (CORRECTED after review):** `docs/readme-landing-page` is branched off
  `docs/v0.2.0-public-install-support` (PR #269), NOT plain `origin/main`. Reason:
  PR #269 carries the corrected "v0.2.0 is published" install wording AND the docs it
  references (`docs/releases/v0.2.0-public-acceptance.md`,
  `docs/install/support-matrix.md`). Basing on plain `main` (commit `2903267`) would
  either force stale "not yet published" caveats into a marketing README or create
  broken links to docs that do not exist on `main`. This rewrite therefore stacks on
  #269 and its own PR should merge after (or together with) #269.

## Brand-rule amendment (owner decision)

The two new PNGs do NOT satisfy the current brand rule that the Seshat star must be
seven-pointed:

- `seshat-bi-hero-lockup.png` (931x524) -- the star behind the figure is
  **six-pointed**.
- `seshat-bi-mark.png` (1254x1254) -- the primary compass-star is **eight-pointed**
  (four long cardinal + four short diagonal points); the small secondary star is also
  eight-pointed.

The current rule lives in `docs/brand/visual-identity.md` (section 3 rule 1: "must be
seven-pointed, not eight-pointed"; section 3 rule 2: "Do not use compass stars…";
section 10: "All stars/emblems must be seven-pointed"; plus the section-10
verification step) and in README lines ~50, ~307, ~368, ~371 ("The star is always
seven-pointed"). The constitution itself contains NO seven-point rule (the external
reviewer's `constitution.md:371` citation was actually README.md:371).

**Owner decision (recorded 2026-07-14):** feature the hieroglyphic goddess brand;
relax the hard "exactly seven points" constraint. The amendment:

- Keeps the **seven readiness stages** as the product concept and keeps the
  seven-stage spine diagram in the README (that meaning is unchanged).
- Reframes the *logo star* rule from "must be seven-pointed" to "a gold star emblem
  (the Seshat/compass star), paired with the seated Seshat figure and teal data
  network" -- i.e. the goddess mark, not a specific point count, is the emblem.
- Updates `docs/brand/visual-identity.md` sections 3, 4, 10 and the README brand
  lines so no doc still asserts "always seven-pointed" while the shipped mark is not.
- This is an OWNER brand decision, not an agent rule change; it is called out in the
  PR body for explicit sign-off.

`seshat-bi-brand-board.png`, `seshat-seven-star.svg`, and `seshat-bi-hero.svg` are
left in the repo unchanged.

## New README structure (top -> bottom)

1. **Hero** -- `seshat-bi-hero-lockup.png` centered, existing badge row beneath, and
   one bold one-line value statement. Keeps the current alt-text discipline
   (descriptive alt text).
2. **The hook** -- 2-3 sentences: ungoverned BI ships wrong numbers; Seshat's stance
   is that nothing advances without recorded evidence and a passed gate. Reuses the
   true framing already in the repo ("readiness is never a faked confidence score").
3. **Who it's for** -- three short blurbs:
   - *BI developers / data engineers* -- governed medallion + Power BI delivery.
   - *AI-agent builders* -- an agent-first tool that stays truthful and refuses to
     skip gates (Claude Code / Codex plugins).
   - *Analytics leads* -- trust and auditability; evidence, not vibes.
4. **See it in 15 seconds** -- the existing 3-command offline demo
   (`seshat demo init` / `run` / `report --format html`) and the
   `assets/demo/readiness-proof.png` screenshot. Preserves the honest
   "stops at Gold Ready offline" note.
5. **Install** -- compact three-surface block using PR #269's **corrected published**
   wording (`v0.2.0` is on public PyPI): `pipx install seshat-bi`; Claude Code
   `/plugin marketplace add ahmed-shaaban-94/Seshat_BI` +
   `/plugin install seshat-bi@seshat-bi-marketplace`; Codex `codex plugin ...`.
   Links to `docs/install/user-install.md`, `docs/install/agent-install.md`,
   `docs/install/support-matrix.md`, and
   `docs/releases/v0.2.0-public-acceptance.md` (all present on the #269 base). The
   marketing README will NOT carry "after public availability is verified" / "not
   yet published" caveats -- those are false on the #269 base and self-defeating for
   an attractor.
6. **The seven-star readiness spine** -- the existing mermaid diagram + the
   non-negotiable-ordering callout, framed as the core differentiator. (The
   seven-*stage* concept is retained even though the logo star-point rule is relaxed;
   see brand amendment.)
7. **Why Seshat is different** -- a short strip of TRUE differentiators: evidence
   over scores; the gates are the product; agent-safe by construction; Power BI reads
   `gold` only; offline proof with an honest live boundary.
8. **Deeper reference** (retained, genuinely trimmed) -- Architecture, Start here as
   an agent, Power BI policy, Roadmap, Brand (adds `seshat-bi-mark.png`),
   Contributing kept inline. The **"What is built today" capability table** and the
   **Repository-layout table** move inside `<details><summary>` collapsibles so the
   open page stays scannable; a 4-6 item highlight strip stays inline above the
   collapsible. No content is deleted (every capability row is preserved inside the
   collapsible); it is relocated within the same README only. This is safe: a
   repo-wide grep found **zero** inbound references to any README anchor
   (`README.md#...`), so no doc or rule depends on a heading staying at top level.

## What stays factually locked (no exaggeration)

- v0.2.0 availability language matches PR #269's corrected install docs exactly
  (`v0.2.0` published on PyPI; Claude plugin validated with the fresh-profile
  limitation noted; Codex install/discovery-only).
- No testimonials, star counts, "trusted by", download counts, or benchmarks-as-marketing.
- No readiness/confidence score is implied anywhere.
- Roadmap "not current capabilities" warning is preserved verbatim in intent.
- Committed README text stays UTF-8 without BOM as an authoring convention (note:
  no gate enforces BOM/ASCII on `.md` -- G3 checks `.tmdl/.pbir/.json/.pbism` only;
  the current README already uses non-ASCII dashes, which is fine).

## Non-goals (YAGNI)

- No second overview/landing file (keeps it one README).
- No doc changes beyond `README.md` and the brand amendment
  (`docs/brand/visual-identity.md`).
- No CSS/HTML micro-site; GitHub-flavored Markdown + centered `<div>` and
  `<details>` blocks only (matching the current README's existing `<div align>` use).

## Validation plan

Gates verify structure, not truth -- so the real checks here are manual:

1. **Brand conformance (manual):** a human confirms the shipped mark matches the
   amended brand rule (the goddess emblem is present); no doc still says "always
   seven-pointed" while the mark is not. No gate can count star points.
2. **Claim-by-claim truthfulness (manual):** every marketing line maps to a cited,
   shipped capability or to PR #269's recorded availability evidence. No invented
   metric/testimonial/score.
3. **Availability coherence (manual):** README install wording matches
   `docs/install/user-install.md` + `agent-install.md` on the #269 base (no "not yet
   published" survivors -- grep them).
4. **Automated:** `git diff --check` clean; `retail check` exit 0; `retail kit-lint`
   no drift (baseline already green -- these prove no *structural* regression, not
   copy accuracy); C2 secret-shape scan implicitly guarded by using no real DSN.
5. **Links:** every relative link resolves on the #269 base.
6. **Staging discipline:** only `README.md`, `docs/brand/visual-identity.md`, and the
   two new `assets/brand/*.png` staged (never `git add -A`).

## Risks

- **Truthfulness is unenforced by gates.** The static gate cannot detect an
  exaggerated or false README claim. Mitigation: the manual claim-by-claim pass
  above; keep availability/score wording identical to the #269 install docs.
- **Brand amendment scope.** Relaxing the seven-point rule is a real governance
  change. Mitigation: it is an explicit owner decision, isolated to
  `visual-identity.md` + README brand lines, and called out in the PR for sign-off.
- **Stacked-branch dependency.** This PR depends on #269; if #269 changes, rebase.
  Mitigation: note the dependency in the PR body; merge after/with #269.
- **Tone vs. precision:** "bold" must not become "overstated". Mitigation: every
  benefit line maps to an existing true capability.
