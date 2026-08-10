---
description: Route Power BI visual formatting, layout, and geometry work
---

Load the `powerbi-workflows` skill and follow its formatting route. Distinguish
planning from mutation: author a formatting plan freely, but change committed
PBIR files only through the installed allow-listed helpers
`seshat pbir-format-visual --repo . --table <table>` and
`seshat pbir-set-geometry --repo . --table <table>`, which preserve data bindings
byte-for-byte. Never edit a visual's data binding, invent a measure, or claim a
readiness pass from formatting work.
