# `seshat cvd-evidence` -- colour-vision-deficiency simulation evidence

Read-only evidence aid. For one committed Power BI theme, it applies three
deterministic colour-vision-deficiency (CVD) transforms to the colours the theme
declares and reports the pairwise `delta_e76` distance measured **after**
simulation -- so a named human can fill the review box the theme generator
deliberately leaves open.

## What it is for

`seshat theme-gen` emits a literal unchecked box into every generated theme spec:

```
- [ ] **CVD distinguishability** -- OPEN
```

It stays open because whether two colours are *distinguishable* is a human
judgment, not a computation (Principle V). The shipped CT1 / CT2 / CT3 rules all
measure **normal-vision** colour maths and explicitly disclaim any
colour-vision-deficiency claim. This tool closes the evidence gap without closing
the judgment: it gives the reviewer the numbers, and leaves the box for them.

## How to run

```bash
# write the companion file next to the theme
seshat cvd-evidence --theme themes/tower-retail.theme.json

# machine shape, printed rather than written
seshat cvd-evidence --theme themes/tower-retail.theme.json --format json

# place the evidence with a table's design artifacts instead
seshat cvd-evidence --theme themes/tower-retail.theme.json \
  --out mappings/retail_store_sales/design/cvd-simulation-evidence.md
```

The default output path is **theme-adjacent** --
`themes/<theme-name>.cvd-simulation-evidence.md` -- not per-table. One theme can
back many tables, so there is no deterministic theme-to-table resolution to
derive a per-table path from. A reviewer who wants it filed under a table passes
`--out`.

Exit code is always 0. This is not a gate.

## What it measures

Three fixed deficiencies, each a closed-form projection onto a dichromat plane
(Vienot, Brettel & Mollon 1999 matrices, applied to linear-light sRGB):

| Deficiency | Absent cones | Characteristic confusion |
|---|---|---|
| protanope | long-wave (red) | red/green, and notably green/orange |
| deuteranope | medium-wave (green) | red/green -- the most common form |
| tritanope | short-wave (blue) | blue/yellow; red/green stays discriminable |

For each deficiency it reports, per declared colour group:

- the simulated swatch for every colour, and
- the `delta_e76` distance for every colour **pair**, both as declared and as
  simulated, ordered closest-measured-distance first as a reading aid.

Colour groups are kept separate and never conflated: the categorical palette
(`dataColors`), any declared `ramp` stops, and the declared status trio
(`good` / `neutral` / `bad`). The status trio matters disproportionately -- it is
green-and-red in practice, which is exactly the pair deuteranopia collapses.

Same theme in, byte-identical evidence out: no randomness, no data, no model.

## What it will NOT do

- **No rolled-up score, index, or percentage.** A per-pair distance is a
  measurement of an already-shipped metric (CT2/CT3 surface pairwise deltaE
  today); a single aggregate number would be a fabricated confidence score
  (hard rule #9).
- **No pass/fail against a threshold**, and no statement that a palette is or is
  not colourblind-safe. Ordering pairs by measured distance is a presentation of
  the measured values, not a new computed quantity.
- **No comparison or ordering between themes.**
- **It does not tick the box.** It writes one companion file, leaves a blank
  named-reviewer slot, and changes no theme value, no
  `colorblind_considerate_categoricals` flag, and no `readiness-status.yaml`.
- **It adds no `seshat check` rule** and no manifest entry.

## Neighbours

| Surface | Lane |
|---|---|
| `CT1` (`design_contrast`) | normal-vision WCAG contrast |
| `CT2` (`design_ramp_deltae`) | normal-vision adjacent-ramp-stop distance |
| `CT3` (`design_categorical_distinctness`) | normal-vision categorical distance |
| `DL4` (`design_review_evidence`) | the durable design-review evidence artifact this mirrors |
| **`cvd-evidence`** | **the same distance metric, measured under simulation** |

## Reading the output

A large declared distance with a small simulated distance is the signal worth a
reviewer's attention -- two colours that look clearly different to you and nearly
identical to a substantial share of viewers. The tool names those pairs first and
stops there; what to do about them is the reviewer's call, recorded by them in the
blank slot at the foot of the file.
