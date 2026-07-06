# Formatting Plan (example, slice 1) -- GENERIC fixture

> A fuller CLEAN example: one applyable row per slice-1 anti-pattern (#4/#9/#13),
> an #8 row held at needs-owner-decision (no committed member enumeration), a verb-C
> background row held at needs-owner-decision (the asset choice is the owner's), and a
> render-only #7 note carried as handoff-only. DL7 must pass this. Generic: no
> tenant/subject-area literal (Principle VII); `page:overview` is a placeholder.

| target | container | group | property | value | principle_cited | token_cited | apply_verb | status | rationale |
|---|---|---|---|---|---|---|---|---|---|
| page:overview | visualContainerObjects | title | show | true | #9 | typography.title | B | proposed | title present so the visual is self-explaining (#9) |
| visual:kpi_primary | objects | labels | show | true | #4 | number_format.integer | B | proposed | consistent integer format per #4 |
| visual:trend_line | objects | dataPoint | fill | themeDataColor | #13 | colors.data_colors | B | proposed | inherit theme data color, no ad-hoc override (#13) |
| page:overview | themeCollection | baseTheme | name | generated | #13 | meta.compiles_to | A | proposed | apply the generated theme as the report default (#13) |
| visual:by_category | objects | dataPoint | fill | perCategory | #8 | colors.data_colors | B | needs-owner-decision | pin category colors once members are enumerated (#8) |
| page:overview | background | canvas | image | placeholder-asset | #12 | colors.background | C | needs-owner-decision | static structure only, carries no KPI value; asset choice is the owner's (one of N committed assets fits, or none) |
| page:overview |  | hierarchy | reading_order | header-first | #7 | layout.reading_order | handoff-only | needs-owner-decision | hierarchy is geometry -- a human/Desktop concern, not applyable (#7) |

## Readiness

- readiness.status: warning
- blocking_reasons: [not rendered -- screenshot-review pending]

## Ratification

- ratification.ratified_by:
