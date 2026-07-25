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

Recording an approval a named human has already given: a stage approval lives in
a **top-level** `approvals:` list in `mappings/<table>/readiness-status.yaml`,
sibling to `stages:` -- never as prose inside `stages.<stage>.evidence[]`, which
does not satisfy any gate. Each entry needs all three fields:

```yaml
approvals:
  - stage: mapping_ready
    owner: "Ada Lovelace (data_owner)"   # "Name (authority_class)" -- a bare name
                                          # or a bare role does NOT count
    at: "2026-07-25"                      # required, ISO; quoted
```

Authority classes: `analyst`, `governance`, `data_owner`, `metric_owner`,
`report_owner`. Transcribe only a decision a named human actually gave -- writing
this block is not the same as granting the approval, and the first hard stop above
still applies. `seshat approvals` lists the stages still awaiting one.

If `seshat` is unavailable, explain that the Python package `seshat-bi` must be
installed. If a live DSN or optional database extra is absent, report
`[PENDING LIVE PROFILE]`, provide enable steps, and remain at the current gate.
Never require the Seshat development repository for normal use.
