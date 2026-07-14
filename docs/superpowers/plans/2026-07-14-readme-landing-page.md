# README Landing-Page Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `README.md` as a marketing-appeal landing page for Seshat BI, feature the new hieroglyphic-goddess brand assets, and amend the brand's seven-point-star rule so docs and shipped art agree.

**Architecture:** Docs + assets only, one branch (`docs/readme-landing-page`) stacked on PR #269 (`docs/v0.2.0-public-install-support`). Three coordinated edits: (1) amend `docs/brand/visual-identity.md` to relax the seven-point rule; (2) add two brand PNGs; (3) rewrite `README.md` into an 8-section landing page with the two biggest tables behind `<details>` collapsibles. Truthfulness and brand-conformance are verified MANUALLY (no gate checks README claim accuracy).

**Tech Stack:** GitHub-flavored Markdown, `<div align="center">` + `<details>` blocks, mermaid, `retail check` / `retail kit-lint` static gates.

## Global Constraints

Copied verbatim from the spec (`docs/superpowers/specs/2026-07-14-readme-landing-page-design.md`); every task's requirements include these:

- **Scope:** only `README.md`, `docs/brand/visual-identity.md`, and two new `assets/brand/*.png` may change. No source, tests, manifests, CI, package metadata, version numbers, tags, release assets, or any other doc.
- **Tone:** bold but strictly true. No invented metrics, testimonials, "used by" logos, download counts, or fabricated readiness/confidence scores.
- **Availability wording:** matches PR #269's install docs exactly — `v0.2.0` published on public PyPI; Claude plugin validated (with the fresh-profile limitation noted); Codex install/discovery-only. NO "after public availability is verified" / "not yet published" caveats.
- **Install commands (verbatim):** `pipx install seshat-bi`; Claude Code `/plugin marketplace add ahmed-shaaban-94/Seshat_BI` then `/plugin install seshat-bi@seshat-bi-marketplace`; Codex `codex plugin marketplace add https://github.com/ahmed-shaaban-94/Seshat_BI` then `codex plugin add seshat-bi@seshat-bi-repository`.
- **Brand amendment:** relax "star must be seven-pointed"; keep the seven-*stage* readiness concept and the spine diagram. Owner decision — isolated to `visual-identity.md` + README brand lines, called out in PR body.
- **Encoding:** UTF-8 without BOM (authoring convention; no gate enforces it on `.md`).
- **Staging:** never `git add -A`; stage only the named files.
- **No secrets:** no real DSN / connection string anywhere in README (C2 gate fires on secret-shaped lines).

## File structure

| File | Responsibility |
|------|----------------|
| `docs/brand/visual-identity.md` | Brand law. Amend §3 (rules 1-2), §4, §10 so no line asserts "always seven-pointed" while the shipped mark is not. |
| `assets/brand/seshat-bi-hero-lockup.png` | New README hero image (already copied into the worktree; needs committing). |
| `assets/brand/seshat-bi-mark.png` | New square logo mark for the Brand section (already copied; needs committing). |
| `README.md` | The landing page. Full rewrite into 8 sections, 2 big tables behind `<details>`. |

Baseline facts (verified): `retail check` and `retail kit-lint` both pass clean on the current tree. The two PNGs exist in `assets/brand/` as untracked files (hero 931x524 RGBA; mark 1254x1254 RGB). The seven-point rule text lives in `visual-identity.md` lines 42, 52, 53, 68, 71, 72, 76, 141, 177, 181 and `README.md` lines ~50, ~307, ~368, ~371. The constitution has NO seven-point rule.

---

### Task 1: Amend the brand rule (`docs/brand/visual-identity.md`)

Do this FIRST — the README brand section and the star-point claims depend on the amended rule being in place, and doing it first prevents a window where README and brand doc contradict.

**Files:**
- Modify: `docs/brand/visual-identity.md` (§2 table line 42; §3 rules 1-2; §4 table lines 68/71/72/76; §10 lines 177/181)

**Interfaces:**
- Produces: an amended brand doc where the emblem is "the Seshat/compass star paired with the seated goddess figure + teal network", NOT "exactly seven points". README Task 4 (Brand section) and Task 3 (hero/spine copy) rely on this.

- [ ] **Step 1: Read the current file** so every seven-point reference is caught.

Run: `grep -n -i "seven-point\|seven-pointed\|eight-pointed\|compass star\|always.*seven" docs/brand/visual-identity.md`
Expected: the lines listed in "Baseline facts" above.

- [ ] **Step 2: Amend §3 "Non-negotiable brand rules" (rules 1-2).**

Replace rule 1 ("The Seshat star must be **seven-pointed**, not eight-pointed.") and rule 2 ("Do not use compass stars, generic north stars, or eight-ray asterisks as substitutes.") with:

```markdown
1. The Seshat emblem is a gold star (the Seshat/compass star) paired with the
   seated Seshat figure and the teal data network. The star's exact point count is
   not fixed; the goddess figure + gold star + teal network together are the mark.
2. Keep the star geometric and deliberate (a clean multi-point star, not a generic
   sparkle or asterisk). The *seven readiness stages* remain the product concept and
   are shown by the seven-stage spine diagram, independent of the logo's point count.
```

- [ ] **Step 3: Amend §2 core-symbol table (line 42)** — change "Seven-point Seshat star" to "Seshat/compass star" in the "Ancient cue" column, keeping the BI interpretation ("canonical truth, navigation, measured structure").

- [ ] **Step 4: Amend §4 logo-system table** — in lines 68/71/72 replace "seven-point star" with "Seshat star"; in line 76 replace "simple seven-point star" with "simple Seshat star".

- [ ] **Step 5: Amend §8 table (line 141)** — replace "simple seven-point star badge" with "simple Seshat star badge".

- [ ] **Step 6: Amend §10 "Current asset decision" (lines 177, 181).**

Replace the block:

```text
All stars/emblems must be seven-pointed.
All hieroglyphic/Seshat figures must be cleaned toward a historically coherent seated/writing form.
```

with:

```text
The gold star emblem is paired with the seated/writing Seshat figure and teal
network; the star's point count is not fixed (amended 2026-07-14 to feature the
hieroglyphic-goddess mark). The seven readiness stages remain the product concept.
All hieroglyphic/Seshat figures must be cleaned toward a historically coherent seated/writing form.
```

And replace line 181 ("…verify the seven-point star in every logo variant.") with "…verify the goddess mark (figure + gold star + teal network) reads cleanly in every logo variant."

- [ ] **Step 7: Verify no "seven-pointed" survivors.**

Run: `grep -n -i "seven-point\|seven-pointed\|eight-pointed" docs/brand/visual-identity.md`
Expected: no matches (or only the deliberate "seven readiness stages" concept phrasing, which does NOT contain "point").

- [ ] **Step 8: Run the static gate.**

Run: `retail check; echo "exit: $?"`
Expected: `exit: 0`.

- [ ] **Step 9: Commit.**

```bash
git add docs/brand/visual-identity.md
git commit -m "docs: amend brand rule to feature the hieroglyphic-goddess mark (relax seven-point star)"
```

---

### Task 2: Add the brand image assets

**Files:**
- Add: `assets/brand/seshat-bi-hero-lockup.png` (already present, untracked)
- Add: `assets/brand/seshat-bi-mark.png` (already present, untracked)

**Interfaces:**
- Produces: two committed image paths the README (Task 3 hero, Task 4 brand) references.

- [ ] **Step 1: Confirm both files exist and are valid PNGs.**

Run: `file assets/brand/seshat-bi-hero-lockup.png assets/brand/seshat-bi-mark.png`
Expected: both report `PNG image data` (hero 931x524, mark 1254x1254).

- [ ] **Step 2: Stage exactly these two files.**

Run: `git add assets/brand/seshat-bi-hero-lockup.png assets/brand/seshat-bi-mark.png`

- [ ] **Step 3: Confirm nothing else is staged.**

Run: `git status --short`
Expected: only the two `A  assets/brand/...png` lines.

- [ ] **Step 4: Commit.**

```bash
git commit -m "assets: add hieroglyphic-goddess hero lockup and logo mark"
```

---

### Task 3: Rewrite README top half — hero through why-different (sections 1-7)

**Files:**
- Modify: `README.md` (replace from the top `<div align="center">` hero block through the end of the current "Quickstart" section, up to but NOT including "## What is built today")

**Interfaces:**
- Consumes: `assets/brand/seshat-bi-hero-lockup.png` (Task 2); the amended brand rule (Task 1); PR #269's install wording (already on this branch's base in `README.md` / `docs/install/*`).
- Produces: sections 1-7 of the landing page. Task 4 appends the trimmed reference below.

- [ ] **Step 1: Re-read the current top of the README** (hero + Why Seshat + seven-star spine + Quickstart) and PR #269's install block so wording is reused verbatim.

Run: `sed -n '1,175p' README.md`
Expected: current hero SVG reference, badges, "Why Seshat", the mermaid spine, and the #269 availability/install text.

- [ ] **Step 2: Replace the hero image** — swap the `<img src="assets/brand/seshat-bi-hero.svg" ...>` for the new lockup:

```html
<img src="assets/brand/seshat-bi-hero-lockup.png" alt="Seshat BI -- Retail BI Readiness System -- from messy retail data to trusted, governed BI" width="820" />
```

Keep the existing badge row unchanged (it is accurate). Add ONE bold value line beneath the badges:

```markdown
**From messy retail data to trusted, governed BI -- with an agent that refuses to skip a step.**
```

- [ ] **Step 3: Write section 2 "The hook"** (2-3 sentences, reusing the true framing already in the repo):

```markdown
## Why Seshat

Ungoverned BI ships wrong numbers with total confidence. Seshat BI takes the
opposite stance, named for the ancient Egyptian figure of writing and
measurement: **nothing advances without recorded evidence and a passed gate.**
Readiness is never a faked confidence score -- it is `status` + `evidence` +
`blocking_reasons`, at every one of seven stages.
```

- [ ] **Step 4: Write section 3 "Who it's for"** (three true blurbs):

```markdown
## Who it's for

- **BI developers & data engineers** -- a governed medallion (`bronze -> silver -> gold`) and Power BI delivery that refuses to skip mapping, validation, or metric contracts.
- **AI-agent builders** -- an agent-first tool (Claude Code & Codex plugins) that stays truthful on real data: it withholds PII, won't invent a mapping, and won't fake a pass.
- **Analytics leads** -- trust and auditability by construction. Every dashboard traces to a metric contract; every stage carries its evidence.
```

- [ ] **Step 5: Write section 4 "See it in 15 seconds"** — reuse the existing demo commands + screenshot + honest boundary:

```markdown
## See it in 15 seconds

No database, no Power BI Desktop. Run the bundled synthetic retail fixture offline:

```bash
seshat demo init
seshat demo run
seshat demo report --format html
```

![Seshat BI readiness proof showing seven evidence-backed readiness stages](assets/demo/readiness-proof.png)

The report shows evidence, blockers, approvals, and the next allowed action for all
seven stages. Offline proof stops honestly at Gold Ready -- live validation needs a
database.
```

- [ ] **Step 6: Write section 5 "Install"** — reuse #269's PUBLISHED wording; no "not yet published" caveats:

```markdown
## Install

`seshat-bi` `v0.2.0` is on public PyPI (clean-install verified -- see the
[public acceptance record](docs/releases/v0.2.0-public-acceptance.md)).

**Python CLI**

```bash
pipx install seshat-bi
seshat init-project my-bi
```

**Claude Code plugin** (validated on Claude Code 2.1.209, Windows)

```text
/plugin marketplace add ahmed-shaaban-94/Seshat_BI
/plugin install seshat-bi@seshat-bi-marketplace
```

**Codex plugin** (install/discovery validated)

```text
codex plugin marketplace add https://github.com/ahmed-shaaban-94/Seshat_BI
codex plugin add seshat-bi@seshat-bi-repository
```

Full guides: [user install](docs/install/user-install.md) - [agent install](docs/install/agent-install.md) - [support matrix](docs/install/support-matrix.md). The Python CLI (`seshat` / `retail`) and the agent plugins are separate: the CLI runs governance checks; a plugin gives an agent session the skills and commands.
```

- [ ] **Step 7: Write section 6 "The seven-star readiness spine"** — keep the EXISTING mermaid diagram verbatim (copy it from the current README's spine section) plus the non-negotiable-ordering callout, reframed as the differentiator with one lead sentence:

```markdown
## The seven-star readiness spine

Seven stages, each a gate: a stage is never entered before the prior one passes. This ordering is the product.
```

(Then paste the current README's existing ```mermaid flowchart block and the `> [!IMPORTANT]` ordering callout unchanged.)

- [ ] **Step 8: Write section 7 "Why Seshat is different"** (true differentiators only):

```markdown
## Why Seshat is different

- **Evidence over scores.** Readiness is `status` + `evidence` + `blocking_reasons`, never a fabricated number.
- **The gates are the product.** No source goes straight to silver; no gold reaches Power BI unvalidated; no dashboard is designed before its metrics are defined.
- **Agent-safe by construction.** The `seshat mcp` governor and the plugins refuse execution and approval; they withhold PII and won't invent mappings.
- **Power BI reads `gold` only.** Reporting is the target, never the source of truth.
- **Honest offline proof.** The demo renders real evidence and stops truthfully at the live boundary.
```

- [ ] **Step 9: Verify no forbidden claims and no stale caveats in the new top half.**

Run: `sed -n '1,120p' README.md | grep -n -i "not yet published\|after public availability\|trusted by\|users\b.*[0-9].*compan\|confidence score of\|[0-9]\+ *stars on"`
Expected: no matches (the only "confidence score" mention is the negation "never a fabricated number").

- [ ] **Step 10: Run the static gate.**

Run: `retail check; echo "exit: $?"`
Expected: `exit: 0`.

- [ ] **Step 11: Commit.**

```bash
git add README.md
git commit -m "docs: rewrite README top half as a landing page (hero, hook, install, spine)"
```

---

### Task 4: Trim the deep reference — collapsibles + Brand mark (section 8)

**Files:**
- Modify: `README.md` (from "## What is built today" through the end of the file)

**Interfaces:**
- Consumes: `assets/brand/seshat-bi-mark.png` (Task 2); the amended brand rule (Task 1).
- Produces: the finished landing page — deep reference retained but the two largest tables collapsed.

- [ ] **Step 1: Wrap the "What is built today" capability table in a `<details>`** with an inline highlight strip above it. Keep a short lead + a 5-item highlight list visible, then:

```markdown
## What is built today

Everything below is on `main`, spec-backed, and held by the `retail check` gate. Highlights:

- The static `retail check` gate over SQL, TMDL/PBIR, DAX, config, and docs.
- Live `retail validate` (PK uniqueness, date coverage, orphan FKs, reconciliation).
- The full seven-stage readiness spine (source intelligence -> handoff pack).
- Agent surfaces: `seshat status` / `next`, offline HTML proof, read-only MCP governor, review/SARIF output.
- The `seshat` CLI + `init-project`, PBIR authoring adapters, and companion dbt / Dagster adapters.

<details>
<summary>Full capability list</summary>

<!-- PASTE THE CURRENT FULL "What is built today" TABLE HERE, UNCHANGED, plus the
"A green static check is necessary but not sufficient..." sentence that follows it -->

</details>
```

Do NOT delete any table row — move the entire existing table verbatim inside the `<details>`.

- [ ] **Step 2: Keep Architecture, "Start here as an agent", and Power BI policy sections unchanged** (they are already concise and true). Leave them in place, in order.

- [ ] **Step 3: Wrap the "Repository layout" table in a `<details>`:**

```markdown
## Repository layout

<details>
<summary>Where everything lives</summary>

<!-- PASTE THE CURRENT FULL "Repository layout" TABLE HERE, UNCHANGED -->

</details>
```

- [ ] **Step 4: Keep the Roadmap section unchanged** — including the `> [!WARNING]` "not current capabilities" callout, verbatim (it is a truthfulness guardrail).

- [ ] **Step 5: Update the Brand section** — swap the brand text so it no longer says "always seven-pointed", and add the new square mark:

Replace the current brand paragraph ("The public identity is **Seshat BI**: a seven-point gold star ... The star is always seven-pointed.") with:

```markdown
The public identity is **Seshat BI**: the seated Seshat figure with a stylus
(mapping and documentation before transformation), a gold star (canonical truth and
the seven readiness gates), and a teal data network (lineage and the BI model).

<div align="center">
<img src="assets/brand/seshat-bi-mark.png" alt="Seshat BI logo mark: seated Seshat figure, gold star, and teal data network on deep navy" width="240" />
</div>
```

Keep the existing links to `docs/brand/visual-identity.md` and the palette line.

- [ ] **Step 6: Update line ~307 repo-layout/brand-assets row** (if the "Repository layout" table describes `assets/brand/` as "logo, seven-point star") to "logo, Seshat star" so it matches the amended rule.

- [ ] **Step 7: Keep the Contributing section unchanged.**

- [ ] **Step 8: Verify no "seven-pointed" / "always seven" survivors in README.**

Run: `grep -n -i "seven-point\|always.*seven-point\|the star is always" README.md`
Expected: no matches. (The "seven readiness stages" / "seven-star readiness spine" concept phrasing is fine and expected.)

- [ ] **Step 9: Run the static gate + kit-lint.**

Run: `retail check; echo "check: $?"; retail kit-lint; echo "lint: $?"`
Expected: `check: 0` and `lint: 0` with "no projection drift".

- [ ] **Step 10: Commit.**

```bash
git add README.md
git commit -m "docs: trim README reference into collapsibles and add goddess mark"
```

---

### Task 5: Final verification pass (the manual gates the static checker cannot do)

**Files:** none modified — verification + link check only.

- [ ] **Step 1: Whitespace check.**

Run: `git diff --check origin/docs/v0.2.0-public-install-support..HEAD`
Expected: no output.

- [ ] **Step 2: Link check** — every relative link in the README resolves.

Run: `grep -oE '\]\(([^)]+)\)' README.md | sed -E 's/\]\(//; s/\)//' | grep -vE '^https?:|^#' | while read p; do [ -e "$p" ] || echo "MISSING: $p"; done`
Expected: no `MISSING:` lines.

- [ ] **Step 2b: Anchor check** — the two internal `#` links still resolve to headings that exist.

Run: `grep -oE '\(#[a-z0-9-]+\)' README.md`
Expected: each anchor (e.g. `#what-is-built-today`) corresponds to a heading still present in the rewritten README (manually confirm; the capability heading is retained above its `<details>`).

- [ ] **Step 3: Claim-by-claim truthfulness pass (MANUAL — the real safeguard).**

Read every marketing sentence in the new top half. For each, confirm it maps to a shipped capability or to #269's recorded availability evidence. Specifically confirm:
- "v0.2.0 is on public PyPI" — matches `docs/install/user-install.md` + `docs/releases/v0.2.0-public-acceptance.md`.
- Claude "validated" / Codex "install-discovery only" — matches `docs/install/support-matrix.md`.
- No testimonials, star/download counts, "trusted by", or numeric readiness/confidence score anywhere.
Expected: every claim traces; note any that don't and fix before proceeding.

- [ ] **Step 4: Brand-conformance pass (MANUAL — no gate can count star points).**

Confirm: (a) no doc (`README.md`, `docs/brand/visual-identity.md`) still asserts "always seven-pointed"; (b) the new mark + hero are referenced and render; (c) the seven-*stage* spine diagram is intact.

Run: `grep -rn -i "always.*seven-point\|must be seven-pointed\|not eight-pointed" README.md docs/brand/visual-identity.md`
Expected: no matches.

- [ ] **Step 5: No-secrets check** (C2 guard).

Run: `grep -nE 'postgres(ql)?://[^ ]*:[^ ]*@|password *= *[^ ]|@[a-z0-9.-]+/[a-z0-9_]+ *$' README.md`
Expected: no matches (no real DSN or credential-shaped line).

- [ ] **Step 6: Staging discipline** — confirm the whole branch touched only the allowed files.

Run: `git diff --stat origin/docs/v0.2.0-public-install-support..HEAD`
Expected: only `README.md`, `docs/brand/visual-identity.md`, `assets/brand/seshat-bi-hero-lockup.png`, `assets/brand/seshat-bi-mark.png`, and the spec/plan docs under `docs/superpowers/`.

- [ ] **Step 7: Push and open a DRAFT PR** (stacked on #269).

```bash
git push -u origin docs/readme-landing-page
gh pr create --draft --base main --title "docs: README landing-page rewrite + brand-mark refresh" --body "<summary; note: stacked on #269; note the brand-rule amendment needs owner sign-off>"
```

Note in the PR body: (1) depends on / stacked on PR #269; (2) contains an OWNER brand-rule amendment (relaxes the seven-point star rule) — call it out explicitly for sign-off; (3) documentation + assets only.

---

## Self-review

**Spec coverage:** hero lockup (T3.2), hook (T3.3), who-it's-for (T3.4), 15-sec demo (T3.5), install with #269 wording (T3.6), seven-star spine (T3.7), why-different (T3.8), trimmed reference/collapsibles (T4.1/T4.3), brand mark (T4.5), brand-rule amendment (T1), manual truthfulness + brand-conformance + availability-coherence checklist (T5.3-T5.5), stacked-on-#269 branch (T2/T5.7). All spec sections map to a task.

**Placeholder scan:** the `<!-- PASTE ... -->` markers in T3.7, T4.1, T4.3 are deliberate "move this existing block verbatim" instructions with the exact source named, not vague TODOs. No "add appropriate X" placeholders.

**Consistency:** asset filenames (`seshat-bi-hero-lockup.png`, `seshat-bi-mark.png`), the marketplace/plugin ids (`seshat-bi@seshat-bi-marketplace`, `seshat-bi@seshat-bi-repository`), and the base branch (`origin/docs/v0.2.0-public-install-support`) are used identically across all tasks.
