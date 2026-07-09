# Personal-Data-Touch Notice -- <table>

<!--
  Generic copy-me shape (Principle VII): NO worked-example column names or PII
  categories baked in. The `retail pii-notice` composer FILLS this from the
  table's committed source-map.yaml; a human never hand-authors it. It echoes
  each pii:true column's committed flag + recorded governance disposition
  VERBATIM (joined by the column's deviation_ref), GAP-marks any pii:true column
  with no recorded decision, renders NO publish-safety verdict of its own, emits
  NO score, and adds NO gate. Optional post-publish companion (answerability-
  summary precedent); never a prerequisite for any readiness stage.
-->

Source: mappings/<table>/source-map.yaml
This notice echoes committed PII flags and recorded governance dispositions.
It records no new judgment, grants no approval, and moves no stage.

## PII-flagged columns

- <column> -- flagged pii:true, decision:keep. Recorded disposition:
  "<verbatim deviation reason>" (mappings/<table>/source-map.yaml,
  defaults.deviations[<id>].reason).
- <column> -- flagged pii:true, decision:drop. Recorded reason:
  "<verbatim column reason>" (mappings/<table>/source-map.yaml,
  columns[<column>].reason).

<!-- when no column is flagged pii:true, the section reads instead: -->
<!-- No column in this table is flagged as personal data (pii:true) in source-map.yaml. -->

## Gaps

- GAP: <column> -- pii:true with NO recorded governance disposition
  (checked: mappings/<table>/source-map.yaml columns[<column>], defaults.deviations).
  This column is NOT cleared; a named human decision is not recorded.

<!-- a missing/unreadable source-map yields instead a single line: -->
<!-- GAP: document -- source-map.yaml missing or unreadable (checked: ...). No PII finding could be composed. -->
