---
description: Route Power BI theme, palette, typography, background, and canvas work
---

Load the `powerbi-workflows` skill and follow its theme route. Use the
installed helpers when available: `seshat theme-gen` and `seshat theme-compile`
to produce theme artifacts, and
`seshat pbir-apply-theme --repo . --table <table>` /
`seshat pbir-set-page-background --repo . --table <table>` to apply them to a
committed report. Themes
set palette, typography, visual/page defaults, and filter-pane/filter-card
defaults -- the filter pane's look, never what it filters. Theme and background
files carry style and structure only -- never business data, metric meaning,
secrets, or PII. Applying a theme changes presentation, not readiness.
