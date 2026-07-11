# Provably-Accessible Gated Theme Layer -- Design

> Design doc for 6 visual-track enhancements to the DEFINE-only `theme_gen`
> pipeline. Produced by a recon -> design -> adversarial -> synthesize workflow
> (17 agents) grounded in the real code seams. ASCII-only. Owner-approval gate
> before writing-plans / implementation.

## 1. Overview

Harden the DEFINE-only `theme_gen` pipeline into a **provably-accessible gated
theme layer**: pure-stdlib arithmetic checks + generation extensions that either
PROVE a narrow computable accessibility fact (contrast, color separation, font
floor) and fail closed on a real defect, or FLAG a declared-correspondence drift
-- while leaving every human-judgment seam (CVD distinguishability, on-screen
legibility, saturation, blend-space, transparency-role schema, sentiment-map
faithfulness) explicitly OPEN for a named reviewer.

All six ideas pass both hard gates:
- **Gate 1 -- DEFINE-only:** pure stdlib arithmetic on the palette; no render, no
  network, no live Power BI, no writing `visual.json`/PBIR.
- **Gate 2 -- non-pass-granting (Principle V / rule #9):** may ADD a proven check
  or FLAG a failure; never self-grants readiness `pass`; no `score:`/`confidence:`
  field; human seams stay OPEN (`[ ]`).

The adversarial pass surfaced buildability and internal-consistency fixes, NOT
gate violations. Those fixes are folded into the per-idea designs below.

## 2. Per-idea designs (fixes folded in)

### Idea 1 -- Adjacent ramp deltaE floor (rule `CT2`)
Detects near-duplicate *adjacent* ramp / `data_colors` entries -- a deterministic
near-collapse bug, NOT a colorblind-safe claim.
- **Files:** shared `color.py` deltaE helper (Sec 3); `theme_gen.py` adds
  `check_ramp_deltae_or_raise(palette, floor) -> None`; new
  `src/seshat/rules/design_ramp_deltae.py` registered as **`CT2`** (contrast/
  color-math family, sibling to CT1 -- NOT a `DL-*` slug; DL1-DL7 are exhausted).
- **Wiring:** called in `generate()` right after `check_contrast_or_raise` (line
  253), before `targets` built. Rule re-reads a DECLARED `min_adjacent_delta_e`
  from tokens YAML at governance time; missing key -> no finding.
- **BLOCKER (floor):** proposed `10.0` is empirically wrong -- the shipped default
  `#2E7D5B` 6-step ramp has min adjacent deltaE = **9.13 < 10.0**, so `generate()`
  would hard-fail a shipping default. Re-derive from real `derive_ramp` output
  (candidate ~7-8) before committing a constant. OWNER ratifies the value.
- **Naming:** CIE76 / `delta_e76` consistently (not "CIEDE2000-lite").
- **Scope:** the floor also constrains caller `--data-colors`; a hand-picked
  close-analogous palette will hard-fail. Real behavior change, acknowledged.
- **spec_md:** evidence line stays `[ ]` (near-collapse guard != colorblind-safe).

### Idea 2 -- Gated transparency (composite-contrast proof)
Composite a foreground over a background at a declared transparency, prove the
result still clears AA.
- **Files:** shared `color.py` `composite_over` (Sec 3); `theme_gen.py`
  `check_composite_contrast_or_raise(palette, floor=AA_FLOOR) -> None` feeding the
  composite hex through the existing `contrast_ratio`.
- **DECISION -- land UNWIRED:** `ThemeSeed`/`build_palette` carry zero alpha fields
  today, so a `generate()`-wired call is a permanent no-op. Land both functions
  as standalone, independently unit-tested; wiring waits on an OWNER-approved
  transparency-role schema on `ThemeSeed`/`build_palette` + tokens emission + a
  CT1 parallel path.
- **BLOCKER (validation):** `composite_over` MUST raise `ValueError` for
  `transparency_pct` outside `[0,100]` (else a malformed 7-char hex leaks a bare
  stdlib traceback, breaking the "never a traceback" `ThemeGenError` contract).
- **BLOCKER (Principle V):** any composite evidence is stdout-only, or if in
  `render_spec_md` it is a `[ ]` OPEN line beside CVD/render/saturation -- never
  `[x]`.
- **OPEN:** `visualStyles` transparency key shape + sRGB-vs-linear blend space.

### Idea 3 -- Categorical distinguishability gate (whole-set)
Detects near-identical swatches anywhere in `data_colors` (min over all `i<j`
pairs) -- a normal-vision collapse bug.
- **Files:** shared deltaE helper; `theme_gen.py`
  `min_categorical_delta_e(data_colors) -> float`,
  `check_categorical_distinctness_or_raise(palette, floor=MIN_CATEGORICAL_DELTAE)
  -> None`, constant `MIN_CATEGORICAL_DELTAE = 2.0` (CIE76 JND-adjacent floor);
  new rule `design_categorical_distinctness.py`.
- **Wiring:** `generate()` after `check_contrast_or_raise`. Does NOT auto-widen
  hue (auto-correction can't be justified CVD-safe without a reviewer).
- **BLOCKER (ASCII):** all generated strings/identifiers use `deltaE76`/`dE76` --
  never the Greek glyph (charmap codec risk on Windows write).
- **BLOCKER (emits-on-main):** committed `executive-dark` + `tower-retail` tokens
  have an `accessibility:` block but no `min_categorical_deltae`. Missing key =
  **silent skip**, NOT `ERROR` (mirror CT1's `background is None: return`), else
  the rule ERRORs on main day one.
- **Finding:** real shape `Finding(rule_id, severity, message, locator)`; register
  `@register(RULE_ID, "<title>")`, `RuleContext`-typed, `Iterable[Finding]`.
- **spec_md:** new `[x]` line (narrow computed normal-vision claim, CT1 tier). CVD
  line + `colorblind_considerate_categoricals: false` untouched.

### Idea 4 -- Min font-size floor + tap-target doc
Parametrize the two hardcoded font literals, refuse sub-floor fonts before write,
document (never encode) a tap-target minimum.
- **Files:** `theme_gen.py` AND `theme_compile.py`. `ThemeSeed` gains
  `title_font_pt: float = 12.0`, `label_font_pt: float = 9.0`; `render_theme_json`
  reads them (lines 205-206); tokens_yaml/spec_md gain a typography block;
  `cli/parser.py` gains exactly **two** flags (`--title-font-pt`,
  `--label-font-pt`).
- **BLOCKER (Gate 2):** `MIN_TITLE_FONT_PT=12.0`, `MIN_LABEL_FONT_PT=9.0`,
  `TAP_TARGET_MIN_PX=44` stay FIXED module constants, NOT CLI-settable (a tunable
  floor of 0 makes the refusal decoration).
- `check_font_floor_or_raise(seed) -> None` called inline in `generate()` AND in
  `compile_theme` (so a committed sub-floor font cannot compile unrefused).
- **BLOCKER (round-trip):** `seed_from_tokens` must read
  `typography.title_font_pt`/`label_font_pt`, falling back to constants only when
  a pre-feature tokens file has no `typography:` block -- else non-default fonts
  trip a phantom DL3 `_deferred_field_conflicts` on a byte-identical recompile.
- **tap-target:** doc-only note in spec_md; no `tapTarget` key ever written.
- **spec_md:** new `[x]` Font floor line; existing `[ ]` legibility line preserved
  verbatim (a number proves the number, not on-screen legibility).

### Idea 5 -- Light/dark theme pair from one seed (SOUND)
Derive a dark seed from a light seed by inverting background/text lightness;
validate + write both sets all-or-nothing.
- **Files:** `theme_gen.py` only -- `derive_dark_seed(light) -> ThemeSeed`, extract
  `_targets_for(seed, repo_root, palette) -> dict[Path,str]` from `generate()`'s
  target-dict literal (no behavior change), `generate_pair(light, repo_root,
  force=False) -> tuple[list[Path], list[Path]]`; `cli/parser.py` gains `--pair`.
- **Derivation:** new frozen `ThemeSeed`, `mode="dark"`, `name=f"{name}-dark"`,
  bg/text lightness inverted via existing `_hex_to_hls`/`_hls_to_hex`;
  accent/data_colors/sentiment pass through.
- **All-or-nothing:** phase 1 (validate + collect + collision check) for BOTH
  seeds; writes nothing if either fails AA or collides.
- **Only fix:** `--pair` must reject `mode="dark"` on the input seed up front (else
  `--pair --mode dark` double-inverts an already-dark palette).
- **spec_md:** each mode gets its own independent spec with its own OPEN checklist
  -- never merged into a "pair approved" claim.

### Idea 6 -- Sentiment 4->3 fidelity rule (`DL8`, shell + human ruling)
FLAGS drift between `colors.sentiment[k]` and `theme[v]` for a human-declared
correspondence; provably inert until the OWNER declares the map.
- **BLOCKER (rule ID):** register as **`DL8`**, NOT `DL4` (already
  `design_review_evidence`; DL1-DL7 taken). Own module-scope constant
  `SENTIMENT_RULE_ID = "DL8"`; do NOT inherit `design_theme_fidelity.py`'s
  `RULE_ID = "DL3"`. Two rules on one ID deterministically fails
  `test_registered_rule_ids_match_expected_set`.
- **Files:** second `@register` fn in `design_theme_fidelity.py`, reusing
  `_iter_tokens_files`/`_theme_rel_for`/`_load_yaml`/`_load_json`; add
  `_sentiment_map_for(tokens_doc) -> dict[str,str] | None` +
  `_reconcile_sentiment(tokens_rel, theme_rel, ctx) -> Iterable[Finding]`.
- **Behavior:** reads opt-in `meta.sentiment_map`. `None` -> skip, no finding
  (never defaults / guesses / infers). Once declared, FLAGS any
  `colors.sentiment[k] != theme[v]` or a mapped key absent from either side as
  `ERROR`. Pure YAML/JSON read + `!=` -- no perceptual math.
- **OWNER STOP:** `executive-dark` is byte-exact faithful -> OWNER may add its
  `sentiment_map` now (DL8 lands green there). `tower-retail` has real 3-value
  color drift + name ambiguity -> its map stays **unwritten (rule inert)** until
  the OWNER reconciles the hexes. Do not write tower-retail's map in this PR.
- **Human ruling:** a dated spec_md Clarifications entry records the frozen 4->3
  correspondence (neutral-by-name vs warning-by-color tie; `neutral` has no theme
  counterpart). The rule only reads its output.

## 3. Shared infrastructure -- `src/seshat/color.py`

Pure-stdlib primitives (no numpy/scipy), mirroring `contrast_ratio`'s shape.
**CVD simulation is deliberately NOT built** -- it stays an OPEN human seam (a
simulated "looks distinguishable" verdict would be a rule #9 violation).

One canonical deltaE helper (shared by ideas 1 and 3 -- do NOT add two):
```python
def hex_to_lab(hex_color: str) -> tuple[float, float, float]: ...  # sRGB->linRGB->XYZ(D65)->Lab
def delta_e76(a: str, b: str) -> float: ...                        # Euclidean Lab distance (CIE76)
```
- Idea 1 calls it on adjacent ramp pairs; idea 3 whole-set (`min` over `i<j`).
- Reference check: black/white `delta_e76` ~= 100.0.

Alpha-composite (idea 2):
```python
def composite_over(fg: str, bg: str, transparency_pct: float) -> str: ...
# #RRGGBB of fg over bg. pct in [0,100]; 0=opaque fg. alpha = 1 - pct/100.
# Raises ValueError outside [0,100]. Validated: 50% black over white -> #808080.
```
All signatures typed, ASCII-only, functions < 50 lines.

## 4. Build order (dependency-aware)

- **Phase 0 -- shared foundation (blocks 1/2/3):** add `hex_to_lab` + `delta_e76`
  + `composite_over` to `color.py` with unit tests.
- **Phase 1 -- re-derive idea-1 floor (blocks idea 1; OWNER decision):** compute
  `delta_e76` on real `derive_ramp` output across shipping accents (incl.
  `#2E7D5B`); pick ~7-8 that clears real ramps and catches duplicates.
- **Phase 2 -- `generate()` call-site edits (SERIALIZE; all touch line ~253):**
  1. Idea 5 phase-1/phase-2 refactor + `_targets_for` extraction (structural) --
     FIRST, so later self-checks land in the split structure.
  2. Idea 4 font floor (`theme_gen.py` + `theme_compile.py` `seed_from_tokens` +
     `compile_theme` call site).
  3. Idea 3 categorical distinctness self-check.
  4. Idea 1 ramp deltaE self-check (once floor is fixed).
- **Phase 3 -- static rules (parallelizable after their generator counterparts;
  each needs the ~9 wiring surfaces):** `CT2` (idea 1),
  `design_categorical_distinctness` (idea 3), `DL8` (idea 6). Rule file,
  `rules/__init__.py` import tuple + `__all__` (DL8 skips -- module already
  imported), regenerated `docs/rules/rules-manifest.json` (via generator, never
  hand-appended), `docs/rules/severity-posture.json`, `docs/glossary.md` row +
  rule-count anchor, `docs/quality/rule-count-claims.yaml`, `EXPECTED_RULE_IDS` in
  `tests/unit/test_rules_wiring.py`. Each MUST verify `<no-finding>` against every
  committed `*-design-tokens.yaml` on main before landing.
- **Phase 4:** idea 5 `generate_pair` + `--pair` + `--pair --mode dark` guard;
  idea 2 lands standalone unwired.

**OWNER STOPS (human seams that halt the build):**
- Idea 1 floor value -- OWNER ratifies the re-derived constant.
- Idea 2 transparency-role schema -- OWNER approves alpha fields on
  `ThemeSeed`/`build_palette` before idea 2 is wired; until then standalone.
- Idea 6 sentiment-map ruling -- OWNER writes `executive-dark`'s `sentiment_map`;
  `tower-retail` stays inert until hexes reconciled; the dated Clarifications
  ruling is authored by the OWNER, not the rule.

## 5. Risks & open questions

OPEN human seams (stay `[ ]`, never auto-checked, never scored): CVD
distinguishability (no simulation built), on-screen/small-size legibility,
saturation, composite blend space + `visualStyles` transparency key shape,
sentiment-map faithfulness.

Risks:
- **Idea 1 floor regression (highest):** `10.0` hard-fails a shipping default
  (min adjacent 9.13). Re-derive before landing. Also constrains `--data-colors`.
- **Idea 4 phantom DL3 conflict:** unfixed `seed_from_tokens` trips a
  byte-identical-recompile failure on any non-default font, even with `--force`.
- **Idea 2 dead-code / traceback:** wiring today is a no-op; unbounded pct leaks a
  bare stdlib `ValueError`.
- **Rule-ID collisions:** `CT2` (not `DL-*`), `DL8` (not `DL4`) -- verified free.
- **Emits-on-main:** ideas 1/3/6 rules must be `<no-finding>` on main at merge
  (missing declared key -> silent skip, never ERROR).
- **Gate-2 erosion to hold the line on:** idea 2 evidence never `[x]`; idea 4 MIN
  font constants never CLI-settable; idea 6 inert when `sentiment_map` absent.

Open questions for the OWNER:
1. Idea 1: what deltaE floor clears real ramps while catching duplicates? (~7-8)
2. Idea 2: approve a transparency-role schema on `ThemeSeed`/`build_palette`?
3. Idea 6: write `executive-dark`'s `sentiment_map` now; when is `tower-retail`
   reconciled?

## 6. Test plan summary

- **`color.py`:** `delta_e76` reference (black/white ~= 100.0); `composite_over`
  50% black-over-white -> `#808080`, 0%/100% boundaries, out-of-range raises.
- **Idea 1 (CT2):** default ramp passes RE-DERIVED floor; two near-identical
  colors raise naming both hexes; floor honored as param; rule declared-vs-missing
  fixture (missing -> no finding); spec_md `[ ]` never `[x]`; emits-on-main clean.
- **Idea 2:** raises below floor, passes at/above; no-transparency palette no-op;
  out-of-range test; evidence line stdout-only or `[ ]`, never `[x]`.
- **Idea 3:** default ramp passes; identical colors raise; rule reads YAML floor,
  missing -> silent skip; spec_md `[ ]` CVD line + no `score:`; ASCII `deltaE76`.
- **Idea 4:** `title_font_pt=11.9`/`label_font_pt=8.9` raise; defaults round-trip;
  custom values verbatim; `"tapTarget" not in` json; legibility `[ ]` preserved;
  MIN constants not CLI-settable; 14pt round-trip through `theme-compile` keeps
  `fontSize:14`, no phantom conflict.
- **Idea 5:** `derive_dark_seed` inverts + clears AA; mode-only diff = background/
  foreground; `generate_pair` writes 6 files; dark AA failure -> zero files;
  `--name foo-dark` and `--pair --mode dark` raise before writing.
- **Idea 6 (DL8):** faithful -> `[]`; drift/key-missing/malformed -> `ERROR`;
  `sentiment_map`-absent -> `[]` (refuse-to-invent trip-wire); `EXPECTED_RULE_IDS`
  includes `DL8`; wiring/manifest snapshots pass; emits-on-main clean.
- **Cross-cutting:** `ruff format --check` + `ruff check`, `pytest -m unit`,
  rules-manifest snapshot, rules-wiring set-equality, CodeScene new-code-health
  10.0 on every touched file.
