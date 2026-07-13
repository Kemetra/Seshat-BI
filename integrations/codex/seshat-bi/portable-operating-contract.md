# Seshat BI portable operating contract

Orient from the earliest non-pass stage in the seven-stage order: Source,
Mapping, Silver, Gold, Semantic Model, Dashboard, Publish. Return exactly one
truthful next action, or one blocked stop with concrete reasons and evidence.

Hard stops:

- Never self-grant an approval; grain, PII publish-safety, business rollups,
  and sentinel-versus-null decisions belong to a named human.
- Never proceed to Silver until Mapping Ready is cleared.
- Never point Power BI at Gold until live validation passes.
- Never design a dashboard before metric contracts exist.
- Never execute the Power BI adapter from this Public Beta bundle.
- Never invent mappings, expose secrets/PII, skip a readiness gate, or report a
  numeric readiness/confidence score.

If `seshat` is unavailable, explain that the Python package `seshat-bi` must be
installed. If a live DSN or optional database extra is absent, report
`[PENDING LIVE PROFILE]`, provide enable steps, and remain at the current gate.
Never require the Seshat development repository for normal use.
