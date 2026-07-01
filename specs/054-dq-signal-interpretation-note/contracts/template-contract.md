# Artifact Contract: dq-signal-interpretation.md template

**Feature**: `054-dq-signal-interpretation-note` | **Date**: 2026-07-01

There is NO code contract (no code is added). This is the structural contract for
the single new documentation artifact,
`templates/handoff/dq-signal-interpretation.md`.

## MUST contain

1. **Generic banner** stating: copy per table to `mappings/<table>/handoff/`; fill
   every `<placeholder>`; the count is sourced by reference from `data-issues.md`
   (single source of truth), never re-measured here; C086 is a linked filled
   instance only; ASCII / UTF-8 no BOM; NO numeric confidence / health / readiness
   score.
2. **Per-signal interpretation table** with columns, all placeholders in a blank
   template:
   - `dim` -- `<dim_<x>>` from `data-issues.md`
   - `count (by reference)` -- `<N, from data-issues.md row #>` (never a new number)
   - `affected KPI` -- `<analyst fill-in>` (owner-gated; not auto-decided)
   - `direction` -- `<understate | overstate | none -- analyst fill-in>`
   - `plain-language caveat` -- `<one-line consumer-readable sentence>`
   - `owner` -- `<named analyst / governance>`
   - `PII review` -- `<n/a | governance sign-off required if person/customer dim>`
3. **Direction-of-distortion semantics note** distinguishing TOTAL (unaffected --
   `-1` absorbs the row, total reconciles) vs SLICED/grouped view (distorted -- the
   `-1` bucket steals share). Presented as the analyst's ruling to state precisely
   (Principle V); the template does NOT assert the claim for them.
4. **"None recorded" path** -- explicit statement + zero caveats when no `-1` signal
   is recorded for the table.
5. **Feeds-not-duplicates note** -- the confirmed caveat is carried verbatim into the
   Stage-7 handoff pack Known-gaps section (`bi-handoff-pack.md` L59-73); this note
   is the interpretive source, not a second home for the count.
6. **RC14 citation** -- names the ratified `-1` unknown-member + FK COALESCE default
   (constitution Principle VI) as the accepted default whose consequence is being
   interpreted; does not re-litigate it.
7. **See also** block linking `data-issues.md`, `bi-handoff-pack.md`,
   `publish-ready.md`, `gold-ready.md`, the constitution (Principle V / VI, RC14),
   and C086 (`docs/worked-examples/c086-pharmacy.md`,
   `docs/c086-adr0002-compliance.md`) as a filled instance.

## MUST NOT contain

- Any pharmacy/C086 specific: no `salesperson_sk`, no `71`, no `ezaby_demo`, no fixed
  dim list, no fixed measure list.
- Any new / re-measured number (the count comes only by reference).
- Any pre-decided KPI or direction value (those are analyst fill-ins).
- Any numeric confidence / health / readiness score.
- Any executor, rule id, validator hook, DB driver import, query, or live-connection
  reference.
- Any self-granted readiness pass.

## Acceptance (by inspection -- no automated test)

Maps to spec SC-001..SC-005. A grep over the new template for `salesperson`,
`ezaby`, `\b71\b`, and a fixed measure name returns zero hits (SC-002).
