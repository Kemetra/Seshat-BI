# Autopilot Run — Final Report (2026-06-26)

> An autonomous overnight run executing three optimized prompts end-to-end: an external
> multi-lens audit, a DAX-fortification increment, and a tool-integration research brief.
> Each mission: work → report → commit → PR → **merge on green CI**. Every decision point
> was checked with an advisor subagent (operator-authorized) and logged. Model policy
> (operator-corrected mid-run): **Sonnet** for review/assessment/verification, **Opus** for
> synthesis/judgment/architecture — never Haiku for reasoning-heavy work.

---

## Executive summary

Three missions completed and merged to `main` with green CI, plus this report.

| Mission | Outcome | PR | Tests |
|---------|---------|----|-------|
| **1 — External multi-lens audit + fixes** | 59 confirmed findings (16 refuted); fixed 3 HIGH bugs + dead code + doc rot | **#34 merged** | 343 passed |
| **2 — Fortify DAX (next increment)** | D4 false-positive fix + D10 ALL-variants widening; design doc for deferrals | **#35 merged** | 349 passed |
| **3 — Tool-integration research** | ADR-0013 + research brief: 2 pilots, 1 scoped, 3 defer, 1 no | *this PR* | 349 passed |

**Headline:** the DAX governance spine is materially stronger and the codebase's real
defects are fixed. The audit confirmed the architecture is sound (stdlib-only core intact,
engine-vs-brain authority model unbreakable at runtime, 31-rule registry matches its
wiring) with **no CRITICAL issues**. The two highest-leverage forward bets (Tabular Editor
BPA, pbi-tools) are identified as safe `.NET-binary-under-`tools/`` adapters; the deferred
DAX work is reaffirmed as **build-in-stdlib, not buy**.

---

## Mission 1 — External multi-lens audit

**Method:** 7 parallel review lenses (correctness, security, architecture, dead/stale code,
test quality, DAX depth, cross-artifact consistency) on Sonnet/high → adversarial
verification (refute-by-default) on Sonnet/high → Opus synthesis. 75 raw → **59 confirmed,
16 refuted**. 83 agents, ~2.3M tokens.

**What was confirmed healthy:** stdlib-only core chain intact (`retail check` runs on a
bare install); engine-vs-brain authority model cannot be violated at runtime; 31-rule
registry exactly matches `EXPECTED_RULE_IDS`. **Zero CRITICAL findings survived.**

**What was fixed (PR #34) — the low-risk, fully-tested subset (advisor-scoped):**
- **3 HIGH bugs:** S4b `START` false-negative (bare `START` suppressed later DDL findings);
  S4b `CREATE OR REPLACE FUNCTION` false-positive; L3 3-arg `DIVIDE(num,den,alt)` wrongly
  escalated.
- **profile hardening:** `.match` → `.fullmatch` (newline-terminated identifier).
- **Dead code removed:** `TmdlModel`, `_DB_PART_KEYS`, `LIVE_CHECKS` (grep-verified).
- **Doc rot:** rule count 27/28 → **31**; Silver `S1-S7` → S1-S8; Semantic `D1-D8` →
  D1-D11; `rules/sql.py` docstring; **ADR-0007 addendum** (history preserved, not rewritten).

**Verification:** 335 → 343 tests (+8), ruff clean, `retail check` on the real repo
produced no new findings (S4b changes are additive/narrowing).

**Deferred to Mission 2** (advisor judgment — too high-blast-radius / policy / re-verify for
an unattended run): `$$` dollar-quote tokenizer, C2 `docs/` scan policy, D4 single-quote
strip, D10 ALL-variants, shared SQL stripper, DSN-redaction scope, LOW-severity latent items.

Full detail: `docs/superpowers/specs/2026-06-26-external-audit-report.md`.

---

## Mission 2 — Fortify DAX

**Method:** 6 candidate increments assessed in parallel (Sonnet/high) → Opus judge scored
leverage × effort × stdlib-purity × **unattended-safety** and selected the SHIP set.

**Scored candidates:**

| candidate | verdict | why |
|-----------|---------|-----|
| D4 single-quote strip | **SHIP** | narrows an ERROR false-positive surface; never broadens |
| D10 ALLSELECTED/ALLEXCEPT | **SHIP** | WARNING-only, additive, same anti-pattern |
| `$$` tokenizer | DESIGN-ONLY | 8-rule blast radius incl. ERROR-severity |
| L1 paren/arity | DEFER | maintenance-debt false positives; PBI Desktop already filters |
| L4 value proxy | DESIGN-ONLY | not stdlib-pure; breaks the headless gate |
| L3 new ops | DESIGN-ONLY | frozen-dataclass + contract-schema migration |

**Shipped (PR #35):**
- **D4** now strips single-quoted DAX table/column delimiters (`'Table'[col]`, `''` escape)
  before the bare-`/` scan — a `/` inside a quoted name no longer false-positives the
  ERROR-severity D4. Direction: narrows only.
- **D10** widened from `FILTER(ALL(...))` to also flag
  `FILTER(ALLSELECTED/ALLEXCEPT/ALLNOBLANKROW(...))` — same full-iteration anti-pattern.
  Stays **WARNING** (ALLSELECTED has legitimate percent-of-selection uses).

**Verification:** 343 → 349 tests (+6), ruff clean, **0 D4/D10 findings on the real model**
(gate satisfied), 31 rules unchanged.

Design + deferred outlines: `docs/superpowers/specs/2026-06-26-dax-fortification-m2-design.md`.

---

## Mission 3 — Tool-integration research

**Method:** rubric distilled from the real adapter pattern (ADR-0008/0009/0010 + dbt/dagster
adapter skills) on Sonnet → 7 tools assessed in parallel (Sonnet/high) → Opus synthesis.

**The rubric:** an adapter is an advisory **engine** behind a gate; Tower BI keeps
**authority**. It writes derived `evidence[]` (never `pass`), adds no core dependency, ships
as a skill, and honors the entry gate + human seams + publish wall.

**Verdicts:**

| tool | verdict | one-line |
|------|---------|----------|
| Tabular Editor 2 BPA | **PILOT** | L2 best-practice breadth; `.NET` binary in `tools/`; F038 spike |
| pbi-tools (extract+diff) | **PILOT** | closes the opaque-`.pbix` hole; `compile` walled off (F016) |
| sqlglot + DuckDB | PILOT (scoped to `tools/`) | the real DAX fixes need neither |
| Great Expectations | DEFER | ~40 transitive deps; needs a new evidence-category ADR |
| sqlfluff | DEFER | no open S-rule gap; future dbt-Jinja lint |
| OpenLineage | DEFER | emitter not a gated reader; external backend |
| DAX Formatter API | **NO** | network service breaks the headless invariant |

**Decisive finding:** none of the surveyed tools change the build-vs-buy call on the
deferred DAX work — **$$ tokenizer → build in stdlib** (one regex branch, not an sqlglot
rewrite); **L4 value proxy → build with lazy psycopg2** (already `[db]`, not DuckDB);
**L3 ops → already shipped stdlib-only**. The two real pilots are safe `tools/`-tier
adapters that strengthen the Semantic Model stage without touching the core.

Decision: `docs/decisions/0013-bi-tool-adapter-shortlist.md`.
Brief: `docs/superpowers/specs/2026-06-26-tool-integration-research.md`.

---

## DAX governance — where the spine stands now

| Layer | Before this run | After this run |
|-------|-----------------|----------------|
| **L1 parse** | deferred | deferred (confirmed low-leverage; DAX Formatter API rejected) |
| **L2 form/hygiene** | D1–D11 | D1–D11, **D4 false-positive fixed, D10 widened to ALL-variants**; BPA pilot identified for breadth |
| **L3 contract drift** | gates CI; 2-arg DIVIDE only | gates CI; **3-arg DIVIDE now checked**; new ops scoped as design-only |
| **L4 value** | deferred | deferred with a concrete build plan (lazy-psycopg2 `retail value-check`) |

Plus: the SQL substrate (S-rules) had two real bugs fixed (S4b `START`, `OR REPLACE
FUNCTION`), and the `$$` tokenizer hole is the named next correctness fix.

---

## Recommended next steps (for when you're awake)

1. **Ship the `$$` dollar-quote tokenizer branch** — smallest, most urgent correctness fix
   (a single regex branch in `src/retail/sql.py`, stdlib-only). The M2 design has the sketch.
2. **Run the F038 Tabular Editor BPA spike** — prove the six gates against committed TMDL;
   make-or-break is headless TMDL parsing without `.bim`/Desktop.
3. **Run the pbi-tools extract spike** — confirm the extracted `model.tmdl` parses under
   `tmdl.py` (shares the .NET runtime with F038).
4. **(Larger, human-reviewed)** L4 value proxy and the L3 new ops — both have design
   outlines; both need a contract-schema decision (a Principle-V human call).

---

## Run metadata

- **Worktree:** `worktree-autopilot` → per-mission branches (`worktree-autopilot`,
  `autopilot-m2`, `autopilot-m3`), each off the prior merged `main`.
- **Model policy:** Sonnet (review/assess/verify), Opus (synth/judge) — corrected mid-run
  after Haiku was caught defaulting on the `Explore` agent type.
- **Advisor checks:** fix-scope (M1), increment selection (M2) — both Opus; rationale logged.
- **Merges:** PR #34 (M1), PR #35 (M2), this PR (M3 + final report) — all squash, CI-green.
- **Guardrails held:** stdlib-only core invariant; tests + ruff gate every change; real-model
  re-verify on rule changes; nothing risky auto-merged.
