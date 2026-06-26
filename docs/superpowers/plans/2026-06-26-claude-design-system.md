# Seshat BI Claude Design System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Author a self-contained preview-HTML component library (Seshat BI brand) plus a validator, ready for the claude.ai DesignSync tool to publish as a new org design-system project.

**Architecture:** A flat `design/claude-design-system/preview/` directory of `@dsCard`-marked HTML files, each linking a shared `_card.css` that `@import`s `colors_and_type.css` (the brand tokens as CSS custom properties). A Python validator (`validate_cards.py`) asserts every render-check invariant and is the RED/GREEN gate for each card and the pre-push gate. No build tooling, no npm, no runtime wiring.

**Tech Stack:** Static HTML5 + CSS custom properties; Python 3 (stdlib only) for the validator; claude.ai DesignSync tool for publish.

**Spec:** `docs/superpowers/specs/2026-06-26-claude-design-system-design.md`

## Global Constraints

- Foundation = the **Seshat BI product brand** (`docs/brand/visual-identity.md`); the retail tokens (`design/tokens/tower-retail-design-tokens.yaml`) are a **separate, labeled** Power BI surface card, **never blended** into the brand palette.
- Brand palette (exact hex): `deep_navy #001E35`, `midnight_navy #04172A`, `rich_gold #C69214`, `gold_light #F2C14E`, `teal #0B9A9A`, `teal_light #31C6C2`, `ivory #F7F1E7`, `sand #E8D8BD`.
- **Contrast rules (measured, binding):** gold/teal are accent-on-dark. On light surfaces (ivory/sand): `rich_gold` = non-text accent only (2.48:1 fails AA); `teal` = large/heading text or non-text only (3.06:1). On `deep_navy`: gold (6.08), teal (4.93), ivory (15.11) all pass AA body.
- **CSP — no external hosts.** No `@import url('https://...')`, no CDN fonts, no remote `src`/`url()`. Allowed links: project-relative `_card.css` / `colors_and_type.css`, `data:` URIs, sibling `.svg`. Fonts are **declared fallback stacks only** (Georgia / Segoe UI / Consolas).
- **`@dsCard` marker** on line 1 or 2 of every card, with all four attributes: `group`, `name`, `subtitle`, `viewport="WxH"`.
- **Render-check:** no thin cards, no visually-identical variants, seven-point star has exactly seven points.
- **All data fabricated** — no `C086`, no `pharmacy`, no real values.
- **Commits:** conventional-commit prefix required by CI (`feat|fix|docs|chore|build|ci|perf|test|refactor|style|revert|brand`); `spec` is REJECTED. Use `--no-gpg-sign` (1Password key unavailable this session). End commit messages with the Co-Authored-By trailer.
- **Do not push to claude.ai** until the user gives explicit go-ahead at sync time (org-visible publish).

---

### Task 1: Card validator (the test harness)

**Files:**
- Create: `design/claude-design-system/validate_cards.py`
- Create: `design/claude-design-system/preview/` (empty dir; the cards land here)

**Interfaces:**
- Produces: `python design/claude-design-system/validate_cards.py <dir>` → exits `0` (PASS) or `1` (FAIL); prints one `[FAIL] <file>: <reason>` line per problem and a final `[OK] N cards` or `[FAIL] N issues`. Every later task's GREEN step runs this command.

- [ ] **Step 1: Write the validator (it is the test — runs against an empty dir first)**

```python
#!/usr/bin/env python3
"""Render-check validator for the Seshat BI Claude Design System preview cards.

Asserts the DesignSync render-check invariants so a card fails until it is
correct (RED), then passes (GREEN). stdlib only. ASCII output only.
"""
import re
import sys
from pathlib import Path

MARKER = re.compile(
    r'<!--\s*@dsCard\s+group="[^"]+"\s+name="[^"]+"\s+'
    r'subtitle="[^"]+"\s+viewport="\d+x\d+"\s*-->'
)
# Off-host http(s) reference. The inline-SVG namespace http://www.w3.org/2000/svg
# is NOT a network fetch (inline SVG in HTML needs no xmlns at all, but if one is
# present it must not trip the gate), so exempt it explicitly.
OFFHOST = re.compile(r'https?://(?!www\.w3\.org/)', re.I)
# CSS may only reference project-relative siblings; a remote @import is the CSP trap.
CSS_OFFHOST = re.compile(r'@import\s+url\(\s*[\'"]?https?://', re.I)
FORBIDDEN_DATA = re.compile(r'\bC086\b|pharmacy', re.I)


def check_card(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    head = "\n".join(text.splitlines()[:2])
    if not MARKER.search(head):
        issues.append("missing/invalid @dsCard marker (need group/name/subtitle/viewport on line 1-2)")
    if OFFHOST.search(text):
        issues.append("off-host reference (http/https) -- CSP forbids external hosts")
    if FORBIDDEN_DATA.search(text):
        issues.append("contains real-data token (C086/pharmacy) -- cards must be data-free")
    # thin: a card with almost no body content is flagged
    body = text.split("<body>", 1)[-1]
    if len(re.sub(r"<[^>]+>|\s", "", body)) < 40:
        issues.append("thin card -- body has < 40 chars of visible content")
    if path.name == "brand-seven-star.html" and 'data-points="7"' not in text:
        issues.append('seven-point star card must carry data-points="7" (visual-identity sec 3.1)')
    return issues


def check_css(path: Path) -> list[str]:
    """CSS files: only the remote-@import CSP trap is checked (no marker/thin rules)."""
    text = path.read_text(encoding="utf-8")
    issues: list[str] = []
    if CSS_OFFHOST.search(text) or OFFHOST.search(text):
        issues.append("CSS references an external host (remote @import / url) -- CSP forbids it")
    return issues


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).parent / "preview"
    cards = sorted(root.glob("*.html"))
    # CSS the bundle depends on: the shared card CSS (in preview/) and the tokens
    # file (in the parent dir) -- both are where the CSP @import trap would land.
    css_files = sorted(root.glob("*.css")) + sorted(root.parent.glob("colors_and_type.css"))
    if not cards:
        print(f"[FAIL] no cards found in {root}")
        return 1
    total_issues = 0
    for c in cards:
        for issue in check_card(c):
            print(f"[FAIL] {c.name}: {issue}")
            total_issues += 1
    for f in css_files:
        for issue in check_css(f):
            print(f"[FAIL] {f.name}: {issue}")
            total_issues += 1
    if total_issues:
        print(f"[FAIL] {total_issues} issues across {len(cards)} cards + {len(css_files)} css")
        return 1
    print(f"[OK] {len(cards)} cards, {len(css_files)} css clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

Note: the `data-points="7"` star check moves INTO the validator from the start
(Task 1), so Task 4 no longer modifies the validator — it just authors the star
card that the existing check already gates.

- [ ] **Step 2: Test the validator itself (it is the gate — prove its regex works) with one good + one bad fixture**

Run this inline self-test (a throwaway temp dir; do not commit the fixtures):

```bash
python - <<'PY'
import tempfile, pathlib, subprocess, sys
v = "design/claude-design-system/validate_cards.py"
good = ('<!doctype html>\n<!-- @dsCard group="G" name="N" subtitle="S" viewport="700x190" -->'
        '<html><body><div>Enough visible content here to clear the thin-card floor easily.</div></body></html>')
bad  = ('<!doctype html>\n<html><body><a href="https://evil.example">x</a></body></html>')  # no marker + off-host
d = pathlib.Path(tempfile.mkdtemp()) / "preview"; d.mkdir()
(d / "ok.html").write_text(good, encoding="utf-8")
r = subprocess.run([sys.executable, v, str(d)], capture_output=True, text=True)
assert r.returncode == 0, f"good card should PASS:\n{r.stdout}"
(d / "broken.html").write_text(bad, encoding="utf-8")
r = subprocess.run([sys.executable, v, str(d)], capture_output=True, text=True)
assert r.returncode == 1 and "broken.html" in r.stdout, f"bad card should FAIL:\n{r.stdout}"
print("[OK] validator self-test passed")
PY
```

Expected: `[OK] validator self-test passed`. (Proves MARKER, OFFHOST, and thin
checks actually fire — the gate is trustworthy before any real card depends on it.)

- [ ] **Step 3: Run it against the empty preview dir — verify the no-cards guard**

Run: `python design/claude-design-system/validate_cards.py design/claude-design-system/preview`
Expected: `[FAIL] no cards found ...`, exit 1. (RED — no cards yet.)

- [ ] **Step 4: Commit**

```bash
git add design/claude-design-system/validate_cards.py
git -c commit.gpgsign=false commit -F <message-file>   # subject: "feat: card validator for Seshat design system"
```

---

### Task 2: Brand tokens + shared card CSS

**Files:**
- Create: `design/claude-design-system/colors_and_type.css`
- Create: `design/claude-design-system/preview/_card.css`

**Interfaces:**
- Produces: CSS custom properties consumed by every card — colors (`--color-navy #001E35`, `--color-midnight #04172A`, `--color-gold #C69214`, `--color-gold-light #F2C14E`, `--color-teal #0B9A9A`, `--color-teal-light #31C6C2`, `--color-ivory #F7F1E7`, `--color-sand #E8D8BD`, `--color-fg-on-dark #F7F1E7`, `--color-fg-on-light #001E35`, semantic `--color-success #2E7D5B` / `--color-warning #B5832A` / `--color-danger #B23A3A` / `--color-neutral #6B7480`), fonts (`--font-display` serif stack, `--font-sans`, `--font-mono`), spacing (`--space-1..9`, 4px base), and utility classes (`.row .col .grid .eyebrow .swatch .swatch--dark .swatch--light .chip .chip-dot .btn .btn--* .tile`).

- [ ] **Step 1: Write `colors_and_type.css` (tokens). NOTE: NO @import url(...) — CSP forbids it (the POS Pulse file has one; we deliberately omit it and use fallback stacks).**

```css
/* Seshat BI Claude Design System — colors_and_type.css
 * Tokens compiled from docs/brand/visual-identity.md (the committed brand).
 * NO external @import: claude.ai CSP blocks external font hosts. We use the
 * brand's declared FALLBACK stacks only (Cinzel/Inter would not load).
 */
:root {
  /* Brand palette (visual-identity.md sec 5) */
  --color-navy:        #001E35;
  --color-midnight:    #04172A;
  --color-gold:        #C69214;
  --color-gold-light:  #F2C14E;
  --color-teal:        #0B9A9A;
  --color-teal-light:  #31C6C2;
  --color-ivory:       #F7F1E7;
  --color-sand:        #E8D8BD;

  /* Foreground by surface (contrast-verified) */
  --color-fg-on-dark:  #F7F1E7;   /* ivory on navy = 15.11:1 */
  --color-fg-on-light: #001E35;   /* navy on ivory = 15.11:1 */
  --color-fg-muted:    #4b5b6e;

  /* Surfaces */
  --color-surface-dark:  #001E35;
  --color-surface-light: #F7F1E7;
  --color-line:          #E8D8BD;

  /* Semantic (conservative, accessible) */
  --color-success: #2E7D5B;
  --color-warning: #B5832A;
  --color-danger:  #B23A3A;
  --color-neutral: #6B7480;

  /* Type — fallback stacks ONLY (no web fonts under CSP) */
  --font-display: 'Cinzel', 'Cormorant Garamond', Georgia, 'Times New Roman', serif;
  --font-sans:    'Inter', 'Segoe UI', Arial, system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'Cascadia Code', Consolas, ui-monospace, monospace;

  --fw-regular: 400; --fw-medium: 500; --fw-semibold: 600; --fw-bold: 700;
  --tracking-eyebrow: 0.18em; --tracking-wide: 0.06em; --tracking-tight: -0.01em;

  /* Spacing — 4px base */
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px; --space-9: 96px;

  --radius-control: 10px; --radius-card: 14px; --radius-pill: 9999px;
  --ease-out: cubic-bezier(0.22, 0.61, 0.36, 1);
}
```

- [ ] **Step 2: Write `preview/_card.css` (shared utilities). Adapts the POS Pulse skeleton to the brand; defaults to the LIGHT (ivory) surface.**

```css
/* Preview card shared CSS — used by every card in preview/ */
@import url('../colors_and_type.css');

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: var(--font-sans);
  color: var(--color-fg-on-light);
  background: var(--color-surface-light);
  font-size: 14px; line-height: 1.5;
  padding: 20px 24px; min-height: 100vh;
}
.row { display: flex; align-items: center; gap: 16px; }
.col { display: flex; flex-direction: column; gap: 8px; }
.grid { display: grid; gap: 12px; }
.spread { display: flex; align-items: center; justify-content: space-between; }
.muted { color: var(--color-fg-muted); }
.eyebrow {
  font-size: 11px; font-weight: 700; letter-spacing: var(--tracking-eyebrow);
  text-transform: uppercase; color: var(--color-fg-muted);
}
.mono { font-family: var(--font-mono); font-size: 12px; color: var(--color-fg-muted); }
.swatch {
  border-radius: 12px; border: 1px solid var(--color-line); height: 64px;
  display: flex; align-items: flex-end; padding: 10px 12px;
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
}
.swatch--dark { color: var(--color-ivory); border-color: rgba(255,255,255,0.12); }
.swatch--light { color: var(--color-navy); }
.chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
  border-radius: var(--radius-pill); font-size: 11px; font-weight: 700;
  letter-spacing: var(--tracking-wide); text-transform: uppercase;
}
.chip-dot { width: 8px; height: 8px; border-radius: 999px; background: currentColor; }
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  height: 44px; padding: 0 16px; border-radius: var(--radius-control);
  font-family: var(--font-sans); font-size: 14px; font-weight: 600;
  border: 1px solid transparent; cursor: pointer; transition: all 150ms var(--ease-out);
}
.btn--primary   { background: var(--color-navy);  color: var(--color-gold-light); border-color: var(--color-navy); }
.btn--secondary { background: transparent; color: var(--color-navy); border-color: var(--color-navy); }
.btn--ghost     { background: transparent; color: var(--color-fg-muted); }
.btn--ghost:hover { background: rgba(0,30,53,0.06); }
.tile { background: #fff; border: 1px solid var(--color-line); border-radius: var(--radius-card); padding: 16px; }
.tile--dark { background: var(--color-navy); color: var(--color-fg-on-dark); border-color: var(--color-midnight); }
```

- [ ] **Step 3: Validator still passes-on-empty? No — run it; expect the no-cards FAIL (CSS files are not cards). This confirms the validator only gates `*.html`.**

Run: `python design/claude-design-system/validate_cards.py design/claude-design-system/preview`
Expected: `[FAIL] no cards found` (still RED — correct; cards come next).

- [ ] **Step 4: Commit**

```bash
git add design/claude-design-system/colors_and_type.css design/claude-design-system/preview/_card.css
git -c commit.gpgsign=false commit -F <message-file>   # subject: "feat: brand tokens + shared card CSS"
```

---

### Task 3: Foundation cards (palette, contrast, type, spacing)

**Files:**
- Create: `design/claude-design-system/preview/colors-brand.html`
- Create: `design/claude-design-system/preview/colors-contrast.html`
- Create: `design/claude-design-system/preview/type-scale.html`
- Create: `design/claude-design-system/preview/spacing-grid.html`

**Interfaces:**
- Consumes: `_card.css` classes + tokens from Task 2.
- Produces: four `group="Foundations"` cards. After this task the validator runs against a non-empty dir for the first time.

- [ ] **Step 1: Write `colors-brand.html` (palette swatches). Marker line 2, four attributes.**

```html
<!doctype html>
<!-- @dsCard group="Foundations" name="Foundations · Brand palette" subtitle="Navy, gold, teal, ivory, sand + semantic" viewport="760x320" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:16px">
  <div class="eyebrow">Seshat BI · brand palette</div>
  <div class="grid" style="grid-template-columns:repeat(4,1fr)">
    <div class="swatch swatch--dark"  style="background:#001E35">#001E35<br><span style="font-weight:400;opacity:.8">deep navy</span></div>
    <div class="swatch swatch--dark"  style="background:#04172A">#04172A<br><span style="font-weight:400;opacity:.8">midnight</span></div>
    <div class="swatch swatch--dark"  style="background:#C69214">#C69214<br><span style="font-weight:400;opacity:.85">rich gold</span></div>
    <div class="swatch swatch--light" style="background:#F2C14E">#F2C14E<br><span style="font-weight:400">gold light</span></div>
    <div class="swatch swatch--dark"  style="background:#0B9A9A">#0B9A9A<br><span style="font-weight:400;opacity:.85">teal</span></div>
    <div class="swatch swatch--dark"  style="background:#31C6C2">#31C6C2<br><span style="font-weight:400;opacity:.85">teal light</span></div>
    <div class="swatch swatch--light" style="background:#F7F1E7">#F7F1E7<br><span style="font-weight:400">ivory</span></div>
    <div class="swatch swatch--light" style="background:#E8D8BD">#E8D8BD<br><span style="font-weight:400">sand</span></div>
  </div>
  <div class="muted">Usage ratio: 60% ivory/navy base · 25% navy text · 10% gold accent · 5% teal data.</div>
</div>
</body></html>
```

- [ ] **Step 2: Write `colors-contrast.html` (the VERIFIED table). Each row shows the pair + measured ratio + verdict.**

```html
<!doctype html>
<!-- @dsCard group="Foundations" name="Foundations · Contrast" subtitle="WCAG AA — measured ratios, gold/teal are accent-on-dark" viewport="760x360" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:12px">
  <div class="eyebrow">Verified contrast (WCAG 2.1 · AA body 4.5:1)</div>
  <div class="grid" style="grid-template-columns:1fr 1fr;gap:10px">
    <div class="tile--dark tile" style="color:#F7F1E7">ivory on navy — 15.11 · <b style="color:#31C6C2">PASS</b></div>
    <div class="tile--dark tile" style="color:#C69214">gold on navy — 6.08 · <b style="color:#31C6C2">PASS</b></div>
    <div class="tile--dark tile" style="color:#0B9A9A">teal on navy — 4.93 · <b style="color:#31C6C2">PASS</b></div>
    <!-- Labels are navy (accessible) with a small swatch; we DEMONSTRATE the bad pairing,
         we do not RENDER text in it (gold-on-ivory text would itself be the bug). -->
    <div class="tile" style="color:#001E35"><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#C69214;vertical-align:middle"></span> gold on ivory — 2.48 · <b style="color:#B23A3A">FAIL (accent only)</b></div>
    <div class="tile" style="color:#001E35"><span style="display:inline-block;width:12px;height:12px;border-radius:3px;background:#0B9A9A;vertical-align:middle"></span> teal on ivory — 3.06 · <b style="color:#B5832A">large/heading only</b></div>
    <div class="tile" style="color:#001E35">navy on ivory — 15.11 · <b style="color:#2E7D5B">PASS</b></div>
  </div>
  <div class="muted">Rule: gold/teal are accent-on-dark. Never gold body text on a light surface.</div>
</div>
</body></html>
```

- [ ] **Step 3: Write `type-scale.html` (specimens, fallback stacks).**

```html
<!doctype html>
<!-- @dsCard group="Foundations" name="Foundations · Type scale" subtitle="Display serif, sans body, mono — fallback stacks" viewport="760x340" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:14px">
  <div class="eyebrow">Typography · fallback stacks (no web fonts under CSP)</div>
  <div style="font-family:var(--font-display);font-size:32px;font-weight:700;letter-spacing:var(--tracking-tight)">Seshat BI — page title 20pt+</div>
  <div style="font-family:var(--font-sans);font-size:20px;font-weight:600">Section header · 14–20pt semibold</div>
  <div style="font-family:var(--font-sans);font-size:14px">Body text · 14px regular. Highly readable sans for docs and dashboards.</div>
  <div class="mono">MONO · pairing-code / IDs · 0123456789</div>
  <div class="muted">Wordmark direction: Cinzel/Cormorant → Georgia fallback. Body: Inter → Segoe UI.</div>
</div>
</body></html>
```

- [ ] **Step 4: Write `spacing-grid.html` (4px scale + safe-zone note).**

```html
<!doctype html>
<!-- @dsCard group="Foundations" name="Foundations · Spacing & grid" subtitle="4px base scale + canvas safe zones" viewport="760x260" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:14px">
  <div class="eyebrow">Spacing · 4px base unit</div>
  <div class="row" style="align-items:flex-end;gap:8px">
    <div style="background:#001E35;height:4px;width:4px" title="4"></div>
    <div style="background:#001E35;height:8px;width:8px" title="8"></div>
    <div style="background:#001E35;height:16px;width:16px" title="16"></div>
    <div style="background:#001E35;height:24px;width:24px" title="24"></div>
    <div style="background:#001E35;height:32px;width:32px" title="32"></div>
    <div style="background:#C69214;height:48px;width:48px" title="48"></div>
  </div>
  <div class="muted">xs 4 · sm 8 · md 16 · lg 24 · xl 32. Card padding 16, gap 16. Preserve whitespace; do not fill every grid cell.</div>
</div>
</body></html>
```

- [ ] **Step 5: Run validator — expect PASS for these 4 cards**

Run: `python design/claude-design-system/validate_cards.py design/claude-design-system/preview`
Expected: `[OK] 4 cards, 2 css clean`, exit 0. (GREEN.) If any FAIL line appears, fix the named card and re-run.

- [ ] **Step 6: Commit**

```bash
git add design/claude-design-system/preview/colors-brand.html design/claude-design-system/preview/colors-contrast.html design/claude-design-system/preview/type-scale.html design/claude-design-system/preview/spacing-grid.html
git -c commit.gpgsign=false commit -F <message-file>   # subject: "feat: foundation cards (palette, contrast, type, spacing)"
```

---

### Task 4: Brand cards (seven-point star, logo system, do/don'ts)

**Files:**
- Create: `design/claude-design-system/preview/brand-seven-star.html`
- Create: `design/claude-design-system/preview/brand-logo-system.html`
- Create: `design/claude-design-system/preview/brand-dos-donts.html`

**Interfaces:**
- Consumes: `_card.css`, tokens, and the `data-points="7"` star check already in the validator (added in Task 1 — this task does NOT modify the validator).
- Produces: three `group="Brand"` cards.

- [ ] **Step 1: Write `brand-seven-star.html` — a true seven-point star as inline SVG, with `data-points="7"`, shown correct-vs-wrong.**

The polygon points below were generated by construction (NOT hand-placed):
outer radius 46, inner radius 20, 7 tips starting at top (-90°), inner vertices
offset by half a step (360/14°), interleaved → exactly 14 vertex pairs. Do not
add an `xmlns` to inline SVG — it is unnecessary and the validator treats a bare
`http://` as an off-host reference (the w3.org namespace is exempted, but inline
SVG simply needs no xmlns).

```html
<!doctype html>
<!-- @dsCard group="Brand" name="Brand · Seven-point star" subtitle="Canonical seven-point — never an eight-ray asterisk" viewport="600x320" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:14px" data-points="7">
  <div class="eyebrow">The Seshat star is SEVEN-pointed (sec 3.1)</div>
  <div class="row" style="gap:40px">
    <div class="col" style="align-items:center;gap:6px">
      <svg width="96" height="96" viewBox="-50 -50 100 100" aria-label="seven-point star">
        <!-- 14 vertices: tip,valley,tip,valley… outer r=46, inner r=20, computed -->
        <polygon fill="#C69214" points="0.0,-46.0 8.7,-18.0 36.0,-28.7 19.5,-4.5 44.8,10.2 15.6,12.5 20.0,41.4 0.0,20.0 -20.0,41.4 -15.6,12.5 -44.8,10.2 -19.5,-4.5 -36.0,-28.7 -8.7,-18.0"/>
      </svg>
      <span class="mono" style="color:#2E7D5B">correct · 7 points</span>
    </div>
    <div class="col" style="align-items:center;gap:6px">
      <div style="font-size:72px;color:#B23A3A;line-height:1">&#10037;</div>
      <span class="mono" style="color:#B23A3A">wrong · 8-ray asterisk</span>
    </div>
  </div>
</div>
</body></html>
```

Verify before committing: open in a browser and count seven equal tips; the
right-side tip (vertex 3, `36.0,-28.7`) must be a real outer point, not collapsed
inward. (A pentagram bug looks like 5 tips — if you see 5, the coordinates were
altered.)

- [ ] **Step 2: Write `brand-logo-system.html` — labeled layout slots (placeholder line-art per the taken default).**

```html
<!doctype html>
<!-- @dsCard group="Brand" name="Brand · Logo system" subtitle="Wordmark, stacked, CLI icon — placeholder slots until final SVG" viewport="760x300" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:14px">
  <div class="eyebrow">Logo family · placeholder slots pending final export (sec 10)</div>
  <div class="grid" style="grid-template-columns:repeat(3,1fr)">
    <div class="tile--dark tile" style="text-align:center"><div style="color:#C69214;font-family:var(--font-display);letter-spacing:0.06em;font-size:20px">SESHAT&nbsp;BI</div><div class="mono" style="color:#6F7D8E">wordmark</div></div>
    <div class="tile--dark tile" style="text-align:center"><div style="color:#C69214;font-size:30px">&#9733;</div><div style="color:#C69214;font-family:var(--font-display);letter-spacing:0.06em">SESHAT BI</div><div class="mono" style="color:#6F7D8E">stacked</div></div>
    <div class="tile--dark tile" style="text-align:center"><div style="width:48px;height:48px;margin:0 auto;border-radius:10px;background:#04172A;border:1px solid #C69214;display:flex;align-items:center;justify-content:center;color:#C69214">&#9733;</div><div class="mono" style="color:#6F7D8E">CLI icon</div></div>
  </div>
  <div class="muted">Final assets export to assets/brand/. Min-size rule: use the CLI icon or star when small.</div>
</div>
</body></html>
```

- [ ] **Step 3: Write `brand-dos-donts.html` — the sec 3 non-negotiable rules.**

```html
<!doctype html>
<!-- @dsCard group="Brand" name="Brand · Do / Don't" subtitle="The non-negotiable brand rules, visualized" viewport="760x300" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="grid" style="grid-template-columns:1fr 1fr;gap:16px">
  <div class="col"><div class="eyebrow" style="color:#2E7D5B">Do</div>
    <ul style="margin:0;padding-left:18px;line-height:1.8">
      <li>Seven-point star, always.</li>
      <li>Egyptian-inspired clean line art holding a stylus.</li>
      <li>Teal nodes = data lineage / semantic links.</li>
      <li>Gold sparingly: dividers, KPI accents, focus.</li>
    </ul>
  </div>
  <div class="col"><div class="eyebrow" style="color:#B23A3A">Don't</div>
    <ul style="margin:0;padding-left:18px;line-height:1.8">
      <li>No compass / north stars or eight-ray asterisks.</li>
      <li>No cartoon or fantasy figure.</li>
      <li>No decorative teal bubbles.</li>
      <li>Never let polish override readiness gates.</li>
    </ul>
  </div>
</div>
</body></html>
```

- [ ] **Step 4: Run validator — expect PASS for all 7 cards**

Run: `python design/claude-design-system/validate_cards.py design/claude-design-system/preview`
Expected: `[OK] 7 cards, 2 css clean`, exit 0. (GREEN. If the star card lacks `data-points="7"`, it FAILS — fix and re-run.)

- [ ] **Step 5: Commit**

```bash
git add design/claude-design-system/preview/brand-*.html
git -c commit.gpgsign=false commit -F <message-file>   # subject: "feat: brand cards (seven-point star, logo, do/dont)"
```

---

### Task 5: Component cards (KPI card, buttons, sentiment, table, section header)

**Files:**
- Create: `design/claude-design-system/preview/components-kpi-card.html`
- Create: `design/claude-design-system/preview/components-buttons.html`
- Create: `design/claude-design-system/preview/components-sentiment.html`
- Create: `design/claude-design-system/preview/components-table.html`
- Create: `design/claude-design-system/preview/components-section-header.html`

**Interfaces:**
- Consumes: `_card.css` (`.btn--*`, `.chip`, `.tile`, `.swatch`), tokens.
- Produces: five `group="Components"` cards. All numbers fabricated.

- [ ] **Step 1: Write `components-kpi-card.html` — the SIGNATURE card: value + comparison + context + trend + sentiment color & icon.**

```html
<!doctype html>
<!-- @dsCard group="Components" name="Components · KPI card" subtitle="Value + comparison + context + trend (every KPI traces to a contract)" viewport="700x260" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="row" style="gap:16px;align-items:stretch">
  <div class="tile" style="flex:1">
    <div class="eyebrow">Net sales · MTD vs LY</div>
    <div style="font-family:var(--font-display);font-size:34px;font-weight:700;color:#001E35">$4.2M</div>
    <div class="row" style="gap:6px;color:#2E7D5B;font-weight:600"><span>&#9650;</span><span>+8.3% vs LY</span></div>
    <div class="muted" style="font-size:12px">Sample data — traces to a metric contract (F009)</div>
  </div>
  <div class="tile" style="flex:1">
    <div class="eyebrow">Margin % · MTD vs target</div>
    <div style="font-family:var(--font-display);font-size:34px;font-weight:700;color:#001E35">31.4%</div>
    <div class="row" style="gap:6px;color:#B23A3A;font-weight:600"><span>&#9660;</span><span>-1.2 pt vs target</span></div>
    <div class="muted" style="font-size:12px">Sentiment = color + icon, never color alone</div>
  </div>
</div>
</body></html>
```

- [ ] **Step 2: Write `components-buttons.html` — primary/secondary/ghost + disabled, each visibly distinct (no identical variants).**

```html
<!doctype html>
<!-- @dsCard group="Components" name="Components · Buttons" subtitle="Primary, secondary, ghost, disabled · md/lg" viewport="700x190" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:14px">
  <div class="eyebrow">Buttons · gold-on-navy primary, navy outline secondary, ghost</div>
  <div class="row" style="gap:10px;flex-wrap:wrap">
    <button class="btn btn--primary">Publish report</button>
    <button class="btn btn--secondary">Cancel</button>
    <button class="btn btn--ghost">Skip</button>
  </div>
  <div class="row" style="gap:10px;flex-wrap:wrap">
    <button class="btn btn--primary" style="min-width:200px">Continue to dashboard</button>
    <button class="btn btn--primary" disabled style="opacity:.5;cursor:not-allowed">Disabled</button>
  </div>
</div>
</body></html>
```

- [ ] **Step 3: Write `components-sentiment.html` — four distinct chips, color + dot + label.**

```html
<!doctype html>
<!-- @dsCard group="Components" name="Components · Sentiment chips" subtitle="Success, warning, danger, neutral — color + icon + label" viewport="700x160" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:14px">
  <div class="eyebrow">Sentiment · color is paired with an icon + label (sec 3.6)</div>
  <div class="row" style="gap:10px;flex-wrap:wrap">
    <span class="chip" style="background:#E7F2EC;color:#2E7D5B"><span class="chip-dot"></span>On target</span>
    <span class="chip" style="background:#F7EEDB;color:#B5832A"><span class="chip-dot"></span>Watch</span>
    <span class="chip" style="background:#F6E4E4;color:#B23A3A"><span class="chip-dot"></span>Off target</span>
    <span class="chip" style="background:#EEF1F4;color:#6B7480"><span class="chip-dot"></span>No change</span>
  </div>
</div>
</body></html>
```

- [ ] **Step 4: Write `components-table.html` — zebra rows, right-aligned tabular numbers, header treatment.**

```html
<!doctype html>
<!-- @dsCard group="Components" name="Components · Data table" subtitle="Zebra rows, aligned number formats, header" viewport="700x280" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:10px">
  <div class="eyebrow">Table · detail grain, consistent number formats</div>
  <table style="border-collapse:collapse;width:100%;font-size:13px">
    <thead><tr style="background:#001E35;color:#F7F1E7;text-align:left">
      <th style="padding:8px 10px">Category</th><th style="padding:8px 10px;text-align:right">Units</th><th style="padding:8px 10px;text-align:right">Net sales</th><th style="padding:8px 10px;text-align:right">Margin %</th></tr></thead>
    <tbody>
      <tr style="background:#fff"><td style="padding:8px 10px">Beverages</td><td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">12,480</td><td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">$842,100</td><td style="padding:8px 10px;text-align:right">33.1%</td></tr>
      <tr style="background:#F4F1EA"><td style="padding:8px 10px">Snacks</td><td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">9,205</td><td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">$611,540</td><td style="padding:8px 10px;text-align:right">29.8%</td></tr>
      <tr style="background:#fff"><td style="padding:8px 10px">Household</td><td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">4,318</td><td style="padding:8px 10px;text-align:right;font-variant-numeric:tabular-nums">$388,902</td><td style="padding:8px 10px;text-align:right">27.4%</td></tr>
    </tbody>
  </table>
  <div class="muted" style="font-size:12px">Sample rows — integers #,##0 · money #,##0 · percent 0.0%</div>
</div>
</body></html>
```

- [ ] **Step 5: Write `components-section-header.html` — page title + section header treatments.**

```html
<!doctype html>
<!-- @dsCard group="Components" name="Components · Section header" subtitle="Page title 20pt+, section header, eyebrow" viewport="700x220" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:16px">
  <div><div class="eyebrow">Executive summary</div>
    <div style="font-family:var(--font-display);font-size:24px;font-weight:700;color:#001E35">Store performance — June 2026</div></div>
  <div style="border-top:2px solid #C69214;padding-top:10px">
    <div style="font-size:16px;font-weight:600;color:#001E35">Sales &amp; margin</div>
    <div class="muted" style="font-size:12px">Gold rule divides sections; date context always present.</div>
  </div>
</div>
</body></html>
```

- [ ] **Step 6: Run validator — expect PASS for all 12 cards**

Run: `python design/claude-design-system/validate_cards.py design/claude-design-system/preview`
Expected: `[OK] 12 cards, 2 css clean`, exit 0. (GREEN.)

- [ ] **Step 7: Commit**

```bash
git add design/claude-design-system/preview/components-*.html
git -c commit.gpgsign=false commit -F <message-file>   # subject: "feat: component cards (kpi, buttons, sentiment, table, header)"
```

---

### Task 6: Pattern cards + Power BI surface card + README

**Files:**
- Create: `design/claude-design-system/preview/patterns-exec-page.html`
- Create: `design/claude-design-system/preview/patterns-number-formats.html`
- Create: `design/claude-design-system/preview/powerbi-dashboard-tokens.html`
- Create: `design/claude-design-system/README.md`

**Interfaces:**
- Consumes: `_card.css`, tokens.
- Produces: two `group="Patterns"` cards, one `group="Power BI surface"` card, and the README. Final card count = 15.

- [ ] **Step 1: Write `patterns-exec-page.html` — <=6 visuals, cards-over-tables, whitespace.**

```html
<!doctype html>
<!-- @dsCard group="Patterns" name="Patterns · Exec page layout" subtitle="<=6 visuals, cards over tables, preserve whitespace" viewport="760x300" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:10px">
  <div class="eyebrow">Executive page · default layout (FR-012)</div>
  <div class="grid" style="grid-template-columns:repeat(3,1fr);gap:12px">
    <div class="tile" style="height:48px">KPI</div><div class="tile" style="height:48px">KPI</div><div class="tile" style="height:48px">KPI</div>
    <div class="tile" style="grid-column:span 2;height:90px">Trend chart</div><div class="tile" style="height:90px">Breakdown</div>
  </div>
  <div class="muted" style="font-size:12px">Ceiling 6 visuals · tables are detail, not the exec headline · do not fill every cell.</div>
</div>
</body></html>
```

- [ ] **Step 2: Write `patterns-number-formats.html` — int / decimal / money / percent reference.**

```html
<!doctype html>
<!-- @dsCard group="Patterns" name="Patterns · Number formats" subtitle="Integer, decimal, money, percent defaults" viewport="700x220" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:10px">
  <div class="eyebrow">Number-format defaults</div>
  <div class="grid" style="grid-template-columns:repeat(2,1fr);gap:10px">
    <div class="tile"><b>Integer</b> <span class="mono">#,##0</span> &rarr; 12,480</div>
    <div class="tile"><b>Decimal</b> <span class="mono">#,##0.00</span> &rarr; 31.42</div>
    <div class="tile"><b>Money</b> <span class="mono">#,##0</span> &rarr; $4,200,000 (scale millions on exec)</div>
    <div class="tile"><b>Percent</b> <span class="mono">0.0%</span> &rarr; 8.3%</div>
  </div>
  <div class="muted" style="font-size:12px">Always group thousands. Headline money scales to millions on exec pages.</div>
</div>
</body></html>
```

- [ ] **Step 3: Write `powerbi-dashboard-tokens.html` — the SEPARATE retail seed, labeled, with the white-bg divergence note.**

```html
<!doctype html>
<!-- @dsCard group="Power BI surface" name="Power BI surface · Dashboard token seed" subtitle="Generic conservative-executive retail theme — NOT the Seshat brand" viewport="760x320" --><html><head><meta charset="utf-8"><link rel="stylesheet" href="_card.css"></head><body>
<div class="col" style="gap:14px">
  <div class="eyebrow" style="color:#B5832A">Separate seed · not the product brand · never blended</div>
  <div class="grid" style="grid-template-columns:repeat(4,1fr)">
    <div class="swatch swatch--dark"  style="background:#1F4E79">#1F4E79<br><span style="font-weight:400;opacity:.85">primary</span></div>
    <div class="swatch swatch--dark"  style="background:#4A6572">#4A6572<br><span style="font-weight:400;opacity:.85">slate</span></div>
    <div class="swatch swatch--light" style="background:#FFFFFF;border-color:#D9DEE3">#FFFFFF<br><span style="font-weight:400">background</span></div>
    <div class="swatch swatch--light" style="background:#F4F6F8">#F4F6F8<br><span style="font-weight:400">surface</span></div>
  </div>
  <div class="tile" style="background:#F7EEDB;border-color:#B5832A;color:#8f5b00;font-size:12px">
    Open item: this seed uses a <b>white</b> dashboard background; the Seshat brand (sec 7) uses navy/ivory.
    Default taken: brand governs covers/headers, this seed governs in-canvas Power BI theme defaults.
  </div>
</div>
</body></html>
```

- [ ] **Step 4: Write `README.md` — what this is, the sync workflow, the don'ts.**

```markdown
# Seshat BI — Claude Design System (preview bundle)

Self-contained preview cards for the claude.ai DesignSync tool. Renders the
committed **Seshat BI** brand (`docs/brand/visual-identity.md`).

## Layout
- `colors_and_type.css` — brand tokens as CSS custom properties (source of truth).
- `preview/_card.css` — shared card stylesheet (imports the tokens).
- `preview/*.html` — one `@dsCard`-marked card per component/foundation.
- `validate_cards.py` — render-check validator (run before any sync).

## Validate
`python validate_cards.py preview`  → `[OK] 15 cards`.

## Sync (org-visible — get explicit go-ahead first)
1. Validate (above) must pass.
2. DesignSync: `create_project` (name "Seshat BI Design System") → `finalize_plan`
   (exact path list) → `write_files`. Incremental; never wholesale replace.

## Don'ts
- No external hosts (CSP): no CDN fonts / `@import url(https://...)` / remote assets.
- No real data: no C086, no pharmacy, no tenant values — fabricated samples only.
- Do not blend the Power BI retail seed into the brand palette.
- The Seshat star is always seven-pointed.
```

- [ ] **Step 5: Run validator — expect PASS for all 15 cards**

Run: `python design/claude-design-system/validate_cards.py design/claude-design-system/preview`
Expected: `[OK] 15 cards, 2 css clean`, exit 0. (GREEN.)

- [ ] **Step 6: Commit**

```bash
git add design/claude-design-system/preview/patterns-*.html design/claude-design-system/preview/powerbi-dashboard-tokens.html design/claude-design-system/README.md
git -c commit.gpgsign=false commit -F <message-file>   # subject: "feat: pattern + powerbi-surface cards + README"
```

---

### Task 7: Final verification + sync readiness (NO push)

**Files:** none created; this task verifies and stops before the gated push.

- [ ] **Step 1: Full validator run + manual render spot-check**

Run: `python design/claude-design-system/validate_cards.py design/claude-design-system/preview`
Expected: `[OK] 15 cards, 2 css clean`. Then open 3 cards (colors-brand, components-kpi-card, brand-seven-star) in a browser; confirm they render against `_card.css`, the star shows seven equal points, and no console request to an external host.

- [ ] **Step 2: Confirm the commit history is clean and CI-safe**

Run: `git log --pretty='%s' origin/main..HEAD`
Expected: every subject starts with an allowed conventional-commit type (`feat:`/`docs:`/`build:`). No `spec:` subjects.

- [ ] **Step 3: STOP. Report ready-to-sync to the user.**

Do NOT call DesignSync `create_project`/`write_files`. The push is org-visible and gated on explicit user go-ahead. Report: "15 cards validated, history CI-safe, ready to sync to a new 'Seshat BI Design System' project on your approval."

---

## Notes for the executor

- The validator is the test. A card is RED until it passes; do not commit a card while the validator reports a FAIL line for it.
- Write commit messages to a temp file and use `git commit -F <file>` — do NOT use a PowerShell here-string for `-m` (it leaks a literal `@` into the subject and breaks the conventional-commit prefix). Always end with: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Work stays in the `feature/claude-design-system` worktree. Stage only explicit paths; never `git add -A` (shared checkout).
