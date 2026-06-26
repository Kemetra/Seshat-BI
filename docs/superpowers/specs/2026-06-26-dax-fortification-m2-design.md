# DAX Fortification — Mission 2 increment design

- **Date:** 2026-06-26
- **Status:** Design (autonomous run; increment selected by an Opus advisor over 6 scored candidates)
- **Builds on:** ADR-0007 (L1–L4 model), PR #32 (L3 gating + D1–D11), PR #34 (audit fixes).
- **Method:** 6 candidates assessed in parallel (Sonnet/high) → Opus judge scored leverage × effort × stdlib-purity × unattended-safety.

## Scored candidates

| candidate | layer | leverage | effort | stdlib-pure | unattended-safe | verdict |
|---|---|---|---|---|---|---|
| **D4: strip single-quoted DAX identifiers before bare-/ scan** | L1/L2 | medium | low | ✅ | ✅ narrows a finding surface (never broadens) | **SHIP** |
| **D10: widen to FILTER(ALLSELECTED/ALLEXCEPT/ALLNOBLANKROW)** | L1/L2 | high | low | ✅ | ✅ WARNING-only, additive | **SHIP** |
| `$$` dollar-quote tokenizer support | L1 | medium | low | ✅ | ❌ 8-rule blast radius, several ERROR | DESIGN-ONLY |
| L1 paren-balance + arity sanity | L1 | low | medium | ✅ | ❌ maintenance-debt false positives; PBI-Desktop already filters | DEFER |
| L4 live-DB value proxy | L4 | high | high | ❌ | ❌ needs psycopg2 + live DB; breaks headless | DESIGN-ONLY |
| L3 new ops (is_false / value_equality / in_set) | L3 | low | medium | ✅ | ❌ frozen-dataclass + contract-schema migration | DESIGN-ONLY |

## SHIP increment (implemented in this PR)

### D4 — strip single-quoted DAX table/column name delimiters

`_strip_dax_comments_and_strings` (shared by D4/D7/D9/D10) stripped only double-quoted
strings. A single-quoted DAX table ref whose name contains `/` (e.g. `'Sales/Returns'[col]`)
survived to the bare-`/` scan and would false-positive D4 (an **ERROR** that blocks the
build). Add one substitution pass for `'(?:[^']|'')*'` (mirrors the double-quote pattern,
handles the `''` escape). This only **removes** a false-positive path — it can never add a
finding. Severity unchanged (D4 stays ERROR).

### D10 — widen the FILTER(ALL(...)) anti-pattern to ALL variants

`ALLSELECTED` and `ALLEXCEPT` inside `FILTER(...)` are the same full-iteration anti-pattern
as `FILTER(ALL(...))` (a row-by-row predicate loop the engine can't push down). Widen the
regex to `FILTER\s*\(\s*ALL(?:SELECTED|EXCEPT|NOBLANKROW)?\s*\(`. Stays **WARNING**
(guidance, not a block — `ALLSELECTED` has legitimate percent-of-selection uses). Anchored
on the `FILTER(` prefix so a bare `ALLSELECTED(...)` outside FILTER is not flagged.

### Real-model re-verify (gate)

Both changes must produce **no finding-count change** on the committed `powerbi/` model
(D4 stays 0, D10 stays 0 — the model has no single-quoted `/` names and no `FILTER(ALL*(`).
If D10 newly fires, that's a real anti-pattern surfaced → report, do not edit the model.

## DESIGN-ONLY / DEFER (human review required — NOT implemented here)

### A. `$$` dollar-quote tokenizer — SHIPPED 2026-06-26
Implemented as a single shared dollar-tag *recognizer* `_dollar_quote_end(text, i)` (NOT the
full shared-stripper refactor, which stays deferred + finding #10) called from all three
strippers (`tokenize_sql`, `strip_sql_comments`, `_strip_sql_noise`), each keeping its own
output contract. `_DOLLAR_TAG = r'\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$'`; close-tag matching uses
the EXACT opening tag (an inner `$other$` in a `$$…$$` span is body); unterminated fails
closed to EOF; `$1`/`$2` positional params do not open a span. A `$` glued to a preceding
identifier-continuation char does not open a span (`a$b$c` is one PG identifier — guarding
this avoids a regression vs the bare lexer; the `i>0` check also guards `text[-1]`). 19 TDD
tests + adversarial verification (4 agents); 0-drift real-model gate.

**Known residual limitations (deferred, all PG-malformed or S1-flagged, absent from tracked
SQL):** `a$$b` / `$$a$$$$b$$` (`$` glued to an identifier/closer) are handled to
*no-worse-than-baseline*, not full PG fidelity; non-ASCII dollar-quote tags (`$café$`) are
not recognized (ASCII tag class) and fall through to baseline. Full PG-identifier-aware
disambiguation is the "buy a real lexer" path ADR-0001 rejected — YAGNI for a zero-`$` corpus.

### B. L4 live-DB value proxy (architectural decision)
New `value_proxy.py` + `retail value-check` subcommand mirroring `retail validate` (lazy
psycopg2, DSN via `resolve_dsn`). New contract block `definition.expected_value:
{value, tolerance_abs, grain}`; missing → skip. Verdict `mismatch`→ERROR. Deferred: not
stdlib-pure, can't run in the headless gate, stale-pin risk, contract-schema review needed.

### C. L3 new predicate ops (3 separate PRs)
`is_false` first (op-whitelist only, no dataclass change). Then `value_equality` (extends
frozen `Filter` with `value`), then `in_set` (`values` frozenset + micro-parser, cardinality
cap ≤10, escalate non-string). Each updates BOTH whitelist sites atomically. Deferred:
frozen-dataclass + contract-schema migration is human-review territory.

### D. L1 paren-balance / arity — DEFER indefinitely
Hand-maintained arity table = permanent false-positive debt; PBI-Desktop already refuses to
serialize unparseable DAX. Low leverage, ongoing cost.
