# External Review Report — Seshat BI (multi-lens audit)

- **Date:** 2026-06-26
- **Method:** 7 parallel review lenses (Sonnet/high) → adversarial verification (Sonnet/high, refute-by-default) → synthesis (Opus/high). 75 raw findings → **59 confirmed, 16 refuted/downgraded**. 83 agents.
- **Scope:** `src/seshat/**`, `tests/unit/**`, `docs/**`, `specs/**`, ADRs, adapter skills.

## Executive summary

The codebase is **architecturally sound and operationally low-risk**. Load-bearing invariants hold: the stdlib-only core chain is intact (`retail check` runs on a bare install), the engine-vs-brain authority model (ADR-0008) cannot be violated at runtime today, and the 31-rule registry exactly matches its test wiring. **No CRITICAL findings survived** the adversarial filter; 16 findings were refuted/downgraded.

Real risk concentrates in two places:
1. **Correctness bugs in the SQL/DAX rule engine** causing silent false-negatives (gate passing things it should flag) and false-positives (eroding trust).
2. **Pervasive documentation rot** — most importantly rule-count drift (docs say 27/28, reality is 31) and stale readiness-gate rule lists that mislead builders about what the gate enforces.

Highest-severity true bugs: `S4b START` false-negative, `S4b CREATE OR REPLACE FUNCTION` false-positive, and `L3 DIVIDE(num,den,0)` three-arg escalation.

## Confirmed findings (ranked)

| # | severity | lens | finding | file:line | fix |
|---|----------|------|---------|-----------|-----|
| 1 | HIGH | correctness | `START` unconditionally sets `in_txn=True`; any `START` token (e.g. `CREATE SEQUENCE … START WITH 1`) suppresses later bare-DDL findings | src/seshat/rules/sql.py:192-194 | require next token `== TRANSACTION` |
| 2 | HIGH | correctness | `_is_guarded` only matches `OR REPLACE VIEW`; `CREATE OR REPLACE FUNCTION/PROCEDURE` → spurious WARNING | src/seshat/rules/sql.py:161-162 | guard on `"OR REPLACE" in joined or "IF NOT EXISTS" in joined` |
| 3 | HIGH | DAX | L3 escalates valid 3-arg `DIVIDE(num,den,0)` as "not exactly two args" | src/seshat/metric_drift.py:263-267 | accept `len in (2,3)`, ignore arg3 |
| 4 | HIGH | DAX | D4: single-quoted DAX string literals not stripped → bare `/` inside them false-positives | src/seshat/rules/dax.py:139 | also strip `'...'` table-name refs before slash scan |
| 5 | MEDIUM | correctness | `tokenize_sql` no dollar-quote (`$$`) branch; PL/pgSQL bodies leak as tokens, corrupting S3/S4b/S5 | src/seshat/sql.py:54 | add `$$`/`$tag$` skip branch |
| 6 | MEDIUM | correctness/sec | `profile._safe_identifier` uses `.match()` not `.fullmatch()`; `valid_id\n` bypasses | src/seshat/profile.py:36 | `.fullmatch` |
| 7 | MEDIUM | security | Partial DSN redaction — psycopg2 auth errors print username/host verbatim | src/seshat/cli.py:156-162,242 | print fixed safe string on connect failure |
| 8 | MEDIUM | security | C2 secret scan skips all `docs/` and `.superpowers/` — a real DSN in a runbook is invisible | src/seshat/rules/git_meta.py:325-329 | scan `docs/`; exclude only `tests/`, or document |
| 9 | MEDIUM | DAX | D10 only matches `FILTER(ALL(`; misses `ALLSELECTED`/`ALLEXCEPT` | src/seshat/rules/dax.py:421 | `FILTER\s*\(\s*ALL(?:SELECTED|EXCEPT)?\s*\(` |
| 10 | MEDIUM | duplication | `strip_sql_comments` (quote-first) vs `_strip_sql_noise` (comment-first) — latent quote-in-comment FN in S6/S8 | src/seshat/sql.py:89; rules/sql.py:333-363 | share one stripper + regression test |
| 11 | MEDIUM | doc rot | Rule count stale: docs say 27/28, reality 31 | roadmap.md:18,192; readiness-pipeline.md:40; tower-bi-agent-kit.md:51,85,167; ADR-0007:102 | update to 31 |
| 12 | MEDIUM | doc rot | readiness-pipeline lists Silver Ready as S1-S7 (omits S8) | readiness/readiness-pipeline.md:16; architecture/readiness-pipeline.md:56 | S1-S8 |
| 13 | MEDIUM | doc rot | Semantic Model Ready lists D1-D8 (omits D9-D11) | readiness-pipeline.md:18; semantic-model-ready.md:34,49; metric-contract-store.md:42 | D1-D11 |
| 14 | MEDIUM | doc rot | ADR-0007 says "28 rules, no D9" after D9-D11 shipped | docs/decisions/0007-…:55,102 | addendum: D9-D11 shipped, count 31 |
| 15 | MEDIUM | consistency | ADR-0012 references non-existent `memory/p2-rule-no-commit-scopes.md` | docs/decisions/0012-…:36,77 | create file or inline + drop ref |
| 16 | MEDIUM | consistency | Specs 040/038 have no roadmap entry; ADR-0007 names 038 "F038" | specs/040,038; ADR-0007:111 | add Tier-5 rows or note out-of-band |
| 17 | MEDIUM | tests | L3 integration tests assert only `severity`, never `rule_id`/measure name | tests/unit/test_semantic.py:67-68,85-86 | add `rule_id=='L3'` + name asserts |
| 18 | MEDIUM | tests | No CLI test for escalate (WARNING, exit 0) semantic-check path | tests/unit/test_cli_semantic.py | add escalate-scenario test |
| 19 | MEDIUM | tests | No G2 passes_clean test | tests/unit/test_git_meta.py | add `test_g2_clean_pbip_passes` |
| 20 | MEDIUM | tests | G6 test writes into live fixture tree, not `tmp_path` | tests/unit/test_g6.py:71-84 | use `tmp_path` |
| 21 | MEDIUM | tests | `test_load_targets_rejects_map_missing_gold_star` writes into live tree | tests/unit/test_validate_targets.py:161-167 | use `tmp_path` |
| 22 | MEDIUM | doc rot | Specs 005/006 say "Draft" but skills shipped | specs/005:7; specs/006:7 | Status → Shipped |
| 23 | MEDIUM | doc rot | Specs 018-027 say "Planned" but skills shipped | specs/019,020,021,022,023,024:11-12 | Status → Shipped/Partial |
| 24 | LOW | security | git `--commit-range` option injection (CI-input only) | gitutil.py:43; git_meta.py:248-250 | allowlist-validate range |
| 25 | LOW | security | regex injection latent: `func` interpolated w/o `re.escape` | metric_drift.py:144 | `re.escape(func)` |
| 26 | LOW | security | path traversal via `--metrics-dir`/`--repo` (no resolve/boundary) | cli.py:278-284,307 | `.resolve()` + `is_relative_to` |
| 27 | LOW | security | git stderr echoed verbatim into RuntimeError/Finding | gitutil.py:15-17; git_meta.py:254-259 | truncate/sanitize |
| 28 | LOW | correctness | `cli.main()` (`-> int`) calls `sys.exit(1)` in one branch | src/seshat/cli.py:108 | `return 1` |
| 29 | LOW | DAX | D8 `_M_STRING_LITERAL` mishandles M escaped `""` | rules/dax.py:295 | `r'"(?:[^"]|"")*"'` |
| 30 | LOW | DAX | D9 ISO branch requires 2-digit m/d; misses `2024-1-1` | rules/dax.py:387 | `\b\d{4}-\d{1,2}-\d{1,2}\b` |
| 31 | LOW | DAX | TMDL column regex mangles calc columns `column Name = expr` (none today) | tmdl.py:292 | exclude `=` from name |
| 32 | LOW | DAX | TMDL measure regex drops single-quoted names containing `=` (none today) | tmdl.py:263-266 | separate quoted/unquoted branches |
| 33 | LOW | DAX | L3 `_outer_call` rejects trailing `;` (non-standard) | metric_drift.py:156-158 | allow trailing whitespace/`;` |
| 34 | LOW | DAX | L3 table-filter denominators always escalate (by design) | metric_drift.py:278-283 | documented gap, note only |
| 35 | LOW | dead code | `TmdlModel` in PUBLIC API, never imported | tmdl.py:184,39 | remove or mark reserved |
| 36 | LOW | dead code | `_DB_PART_KEYS` defined, never referenced | validate.py:52-59 | remove |
| 37 | LOW | dead code | `LIVE_CHECKS` never used by `run_live_checks` | validate.py:316-321 | remove |
| 38 | LOW | dead code | `TmdlTable.partition_sources` populated but consumed by no rule; docstring claims "for D8" | tmdl.py:175,352,37 | correct docstring |
| 39 | LOW | dead code | `top_level_blocks` in PUBLIC API but only a test anchor | tmdl.py:525,46 | drop from API or `_`-prefix |
| 40 | LOW | duplication | `profile.py` identifier validation duplicates `identifiers.py` | profile.py:25-37; identifiers.py:19-55 | shared helper |
| 41 | LOW | doc rot | `rules/sql.py` docstring says "S1-S4b plus D8"; misses S5-S8 | rules/sql.py:1 | update to S1-S8 |
| 42 | LOW | doc rot | Specs 028-037 gap unexplained | specs/; roadmap.md:150-158 | one-line note |
| 43 | LOW | doc rot | Architecture doc says repo `Retail_Tower_analytics` (renamed) | architecture/tower-bi-agent-kit.md:5 | note rename |
| 44 | LOW | doc rot | C086 examples claim "26 rules" | worked-examples/c086-pharmacy.md:182; c086-adr0002-compliance.md:96 | note current 31 |
| 45 | LOW | consistency | Roadmap ADR slug `0011-adapter-safe-auto-updates` ≠ file | roadmap.md:145 | fix slug |
| 46 | LOW | tests | `test_s1_flags_quoted_caps` bare truthiness | tests/unit/test_sql.py:43 | add count+message |
| 47 | LOW | tests | `test_semantic_check_clean_exits_zero` takes `capsys`, never reads | tests/unit/test_cli_semantic.py:63-66 | assert 'no drift' |
| 48 | LOW | tests | S1-S4b have no tests/-prefix exemption tests | tests/unit/test_sql.py | add exemption tests |
| 49 | LOW | tests | reload loop hardcodes 5 submodules (vacuous-pass risk) | tests/unit/test_rules_wiring.py:82 | derive via pkgutil |
| 50 | LOW | tests | no CLI test for measure-without-contract skip | tests/unit/test_cli_semantic.py | add 2nd measure no-contract |

(+ architecture confirmations: stdlib-only intact, engine-vs-brain honored, layers clean, EXPECTED_RULE_IDS matches code — no action.)

## Top 5 to fix first

1. **S4b `START` false-negative** (sql.py:192-194) — HIGH; silently disables rule for any file with a sequence. One-line fix.
2. **L3 three-arg `DIVIDE` escalation** (metric_drift.py:263-267) — HIGH; `DIVIDE(x,y,0)` measures never drift-checked.
3. **S4b `CREATE OR REPLACE FUNCTION` false-positive** (sql.py:161-162) — HIGH; every stored-proc migration warns spuriously.
4. **Rule-count + readiness-gate doc rot** — the single most-read wrong claim; fix 27/28→31, S1-S7→S1-S8, D1-D8→D1-D11 together.
5. **`_strip_sql_noise` quote-ordering + dollar-quoting gap** (sql.py) — latent silent FNs; pair with a `--`-in-string regression test.

## What's missing (completeness critic)

- **Live DB path** under-covered (all static reads) — fuzz `_redact_dsn` against real psycopg2 error formats.
- **DAX false-POSITIVE surface** thinner than false-negative — check D1/D2/D3 against Unicode/reserved-word names, D11 multi-line `///`.
- **No Windows-path / CRLF lens** despite the repo's 260-char + autocrlf rules — verify tokenizers are `\r\n`-agnostic.
- **G1/G3/G4/G5 git-meta rules** not examined for their own FP/FN surface — largest untouched rule cluster.
- **Refuted set (16)** not enumerated — a meta-audit could confirm none were genuine bugs dismissed too fast.

---

## Fixes applied in this PR (2026-06-26)

Scope chosen with an Opus advisor review (low-risk, fully-tested, no stdlib-core-invariant
or rule-surface-broadening changes; everything else deferred to the DAX-fortification
design track).

**Code bugs (TDD, all 8 new tests green):**
- **#1 S4b `START` false-negative** — `START` now opens a transaction only when followed
  by `TRANSACTION`; a bare `START` (e.g. `CREATE SEQUENCE … START WITH 1`) no longer
  suppresses later bare-DDL findings. (`src/seshat/rules/sql.py`)
- **#2 S4b `CREATE OR REPLACE FUNCTION` false-positive** — `_is_guarded` now accepts any
  `OR REPLACE` form, not just `OR REPLACE VIEW`. (`src/seshat/rules/sql.py`)
- **#3 L3 three-arg DIVIDE** — `check_measure_drift` accepts `DIVIDE(num, den, alt)`
  (2 or 3 args), denominator still `args[1]`; drift detection preserved.
  (`src/seshat/metric_drift.py`)
- **#6 `profile._safe_identifier`** — `.match` → `.fullmatch` (defense-in-depth against a
  newline-terminated identifier). (`src/seshat/profile.py`)

**Dead code removed** (grep-verified zero references): `TmdlModel` (`tmdl.py`),
`_DB_PART_KEYS`, `LIVE_CHECKS` (`validate.py`); tmdl public-API docstring updated.

**Doc rot fixed** (current-claim docs only; historical records/ADR bodies preserved):
rule count 27/28 → **31** (roadmap, architecture×3, readiness-pipeline×2); Silver Ready
`S1-S7` → **S1-S8**; Semantic Model Ready `D1-D8` → **D1-D11** (readiness-pipeline,
semantic-model-ready, metric-contract-store); `rules/sql.py` docstring `S1-S4b` → S1-S8;
**ADR-0007 addendum** noting D9-D11 shipped + L3 gating + count 31 (decision body left as
the historical record).

**Verification:** full suite **343 passed** (was 335; +8 audit tests), ruff format+lint
clean, `retail check` on the real repo produced no new S/D-rule findings (the S4b changes
are additive/narrowing and fire nothing on committed migrations).

**Deferred to the DAX-fortification design track** (need design / re-verify, per advisor):
dollar-quote (`$$`) tokenizer gap (8+ consumers); C2 `docs/` scan policy (deliberate
documented exclusion); D4 single-quoted-string stripping (ERROR-severity, re-verify);
D10 `ALLSELECTED`/`ALLEXCEPT` variants; shared SQL stripper refactor; DSN-redaction scope;
the LOW-severity latent items (git option-injection, path traversal, regex-escape).
