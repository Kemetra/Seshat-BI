# A11y / RTL readiness checklist -- retail_store_sales / overview

Filled instance (the worked example). Copied from
`templates/a11y-rtl-readiness-checklist.md` and filled against the
`retail_store_sales` executive overview page's already-committed design/theme/
layout artifacts. AUTHORING ONLY -- no publish, no Power BI Desktop / DB
connection, no execution adapter (that is F016). ASCII, UTF-8 no BOM. This
checklist does NOT self-grant `dashboard_ready: pass` -- it is evidence FOR
the existing BI/report-owner design-review sign-off on that gate.

## Header

| Field | Value |
|-------|-------|
| `subject_area` | `retail_store_sales` (gold star `gold.fct_sales_rss`) |
| `page_id` | `overview` (the single executive overview page; see `dashboard-layout.md`) |
| `filled_by` | `agent (docs-only authoring pass, spec 102-dashboard-a11y-rtl-gate)` |
| `filled_at` | `2026-07-05` |

## Dimension 1 -- `contrast`

| Field | Value |
|-------|-------|
| `token_file` | `design/tokens/tower-retail-design-tokens.yaml` |
| `ct1_result` | `clean` -- `retail check` CT1 (`design_contrast.py`) reports 0 findings for this file: `colors.text.primary` (`#1A1D21`), `colors.text.secondary` (`#3C434B`), and `colors.text.muted` (`#6B7480`) each meet the declared `accessibility.min_text_contrast_ratio: "4.5:1"` floor against `colors.background` (`#FFFFFF`) |
| `disposition` | `reviewed-clean` |
| `reason` | -- (not applicable; disposition is clean) |
| `citation` | `["design/tokens/tower-retail-design-tokens.yaml", "retail check CT1 result captured 2026-07-05: 0 findings for this file"]` |

Invariant check: `disposition: reviewed-clean` and `ct1_result: clean` agree
-- this dimension does not contradict CT1's registered finding.

## Dimension 2 -- `colorblind_safe`

| Field | Value |
|-------|-------|
| `palette_source` | `themes/tower-retail.theme.json` (`dataColors`, compiled from `design/tokens/tower-retail-design-tokens.yaml`'s `colors.data_colors`) |
| `criteria_ref` | `docs/powerbi/visual-design-system.md#colorblind-safe-palette-separation` |
| `disposition` | `reviewed-clean` |
| `reason` | -- (not applicable; disposition is clean) |
| `finding_detail` | -- (not applicable; disposition is clean) |
| `citation` | `["themes/tower-retail.theme.json#/dataColors", "design/tokens/tower-retail-design-tokens.yaml#/colors/data_colors"]` |

Review notes: the page's multi-series visuals (`v06`/`v07` category bars,
`v08` location split, `v09` payment-method columns; see `visual-list.md`) draw
from the 8-color `dataColors` sequence (`#1F4E79`, `#4A6572`, `#2E7D5B`,
`#B5832A`, `#7A5C8E`, `#3F7CAC`, `#9E6B4A`, `#5B7B6E`). Against the criteria at
`#colorblind-safe-palette-separation`: no two adjacent entries in the ordered
sequence rely on a red/green pass-fail pairing as the only distinguishing cue,
and the sentiment colors (`success`/`warning`/`danger` at
`design/tokens/tower-retail-design-tokens.yaml#/colors/sentiment`) are a
separate declared set from the categorical `data_colors`, so a category chart
does not conflate sentiment framing with series identity. The tokens file
itself declares `accessibility.colorblind_considerate_categoricals: true` and
`accessibility.do_not_rely_on_color_alone: true` as authored intent; this
review confirms the compiled `dataColors` sequence carries that intent
through to the theme. No CVD-simulation score is computed or implied -- this
is the documented judgment the criteria doc requires, not a numeric result.

## Dimension 3 -- `rtl_arabic_layout`

| Field | Value |
|-------|-------|
| `layout_source` | `mappings/retail_store_sales/design/dashboard-layout.md` |
| `criteria_ref` | `docs/powerbi/visual-design-system.md#rtl-arabic-layout-readiness` |
| `disposition` | `blocked` |
| `scope_ruling_citation` | -- (not applicable; disposition is not `not-applicable-with-reason`. No named-human LTR-only ruling for this page exists, so per the OPEN Q-FR014-SCOPE interim floor this dimension is reviewed as in-scope, not exempted.) |
| `finding_detail` | `dashboard-layout.md` records the page's region order and business questions but contains no text-direction, mirrored-axis, or Arabic numeral/date-formatting statement for any region. Concretely: the "Main insight" region (`v05`, TotalSales over time, per `visual-list.md`) implies a left-to-right time axis with no recorded confirmation that the axis is mirrored for an RTL/Arabic reader, and the Header/Filter-rail/KPI-strip regions carry no recorded number/date-formatting-locale statement. Per `#rtl-arabic-layout-readiness`, this is an open finding, not an assumed pass: the proposed RTL-correct alternative is to add an explicit RTL layout note to `dashboard-layout.md` (or a page-level design note) recording (a) the trend visual's time-axis direction for an RTL reading order, and (b) the number/date format the page uses for an Arabic-reading audience, before this dimension can be re-filled as `reviewed-clean`. |
| `citation` | `["mappings/retail_store_sales/design/dashboard-layout.md"]` |

## Staleness

Not yet applicable -- this is the first fill of this checklist for this page
(`filled_at: 2026-07-05`). Per the template's staleness section, if
`design/tokens/tower-retail-design-tokens.yaml`, `themes/tower-retail.theme.json`,
or `mappings/retail_store_sales/design/dashboard-layout.md` changes after this
date, this checklist becomes STALE and must be re-filled before the next
`dashboard_ready: pass` claim for this page relies on it. There is no
automated detector for this; it is a review-discipline obligation at the next
design-review sign-off.

## Roll-up

| Field | Value |
|-------|-------|
| `overall_status` | `warning` -- the worst of the three dimensions (`reviewed-clean`, `reviewed-clean`, `blocked`), recorded per the OPEN Q-FR014-SEVERITY interim floor as AT LEAST a `warning`-class finding; escalation to `blocked` for `dashboard_ready` as a whole is UNDECIDED pending the named-human ruling and is NOT decided by this checklist |
| `evidence` | `["design/tokens/tower-retail-design-tokens.yaml -- CT1 clean, 2026-07-05", "themes/tower-retail.theme.json#/dataColors -- reviewed against #colorblind-safe-palette-separation, reviewed-clean", "mappings/retail_store_sales/design/dashboard-layout.md -- reviewed against #rtl-arabic-layout-readiness, open finding recorded"] ` |
| `blocking_reasons` | `["rtl_arabic_layout: dashboard-layout.md records no text-direction / mirrored-axis / numeral-date-formatting statement for the v05 trend visual or any other region; see Dimension 3 finding_detail"]` |

This checklist does not itself set `dashboard_ready: pass` or `blocked` for
the `retail_store_sales` overview page -- it records the evidence and the open
finding above for the BI/report owner's existing design-review sign-off to
act on.

## Stop-and-ask: two OPEN Principle-V questions (carried forward, not answered)

Recorded verbatim per the template; NOT resolved by this filled instance.

- **Q-FR014-SCOPE** -- OPEN. No named-human LTR-only ruling exists for the
  `retail_store_sales` overview page, so per the recorded pending default this
  page is reviewed as IN-SCOPE for the RTL/Arabic dimension (which is why
  Dimension 3 above is filled as an active review, not
  `not-applicable-with-reason`).
- **Q-FR014-SEVERITY** -- OPEN. The `rtl_arabic_layout` open finding above is
  recorded as AT LEAST a `warning`-class finding in `blocking_reasons[]`.
  Whether it escalates `dashboard_ready` for this page all the way to
  `blocked` is UNDECIDED pending the named-human ruling; this checklist does
  not decide it.

## See also

- The generic template this instance fills:
  `templates/a11y-rtl-readiness-checklist.md`.
- The mechanical rule cited for Dimension 1: `src/retail/rules/design_contrast.py` (CT1).
- The fixed criteria cited for Dimensions 2 and 3: `docs/powerbi/visual-design-system.md`
  (`#colorblind-safe-palette-separation`, `#rtl-arabic-layout-readiness`).
- The gate this evidences: `docs/readiness/dashboard-ready.md`.
- Sibling design artifacts for this subject area: `dashboard-layout.md`,
  `visual-list.md`, `visual-contract-binding-map.md`.
