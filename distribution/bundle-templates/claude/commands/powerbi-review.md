---
description: Route Power BI screenshot, dashboard QA, blueprint, and PBIR review
---

Load the `powerbi-workflows` skill and follow its review route. Route a
screenshot or built-report review to its visual QA guidance, a page-blueprint
check to the installed `seshat pbir-validate-blueprint` helper when available,
a pre-Desktop field-resolution check to `seshat pbir-validate-bindings`,
hand-authored TMDL to `seshat tmdl-doc-comment-lint` (which checks ONE rule --
a `///` block must attach to a declaration -- and is NOT a TMDL syntax
validator, so a pass does not mean the model loads), and a semantic or metric
question to `bi-dax-knowledge` / `retail-kpi-knowledge`. Findings are advisory
evidence for a named human; a clean review never grants approval or a readiness
pass, and neither helper verifies that Desktop can load the model.
