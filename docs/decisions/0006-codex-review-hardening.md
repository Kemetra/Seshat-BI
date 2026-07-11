# 0006 -- Codex PR-review hardening (an independent reviewer found a second wave of defects)

- **Date:** 2026-06-25
- **Status:** Accepted
- **Context:** After the first end-to-end run hardened the live surfaces (ADR 0005),
  the `training`-DB work was opened as PR #23. An automated reviewer (Codex,
  configured on the repo) reviewed the diff and raised **nine** findings (one P1,
  the rest P2-class). Each was VERIFIED against the actual code/SQL/artifacts before
  acting -- not relayed on the bot's severity badge alone -- and all nine were real.
  They fall in four classes: a hole in the governance TOOL itself, a date-model
  correctness trap that passes every existing gate, CSV-loader robustness gaps, and
  governance-consistency split-brain (a `pass` recorded while the machine-readable
  artifact still held a template placeholder). This ADR records the class of each and
  the hardening, continuing ADR 0005's "robust for ANY data, not just this instance"
  intent. The crucial meta-lesson: **a green unit suite AND a green `retail check` AND
  a green `retail validate` together still missed all nine** -- an independent review
  pass caught what self-testing structurally could not.

## The nine findings (each fixed TDD on `feat/training-e2e-and-tool-maturity`)

| # | Sev | Defect | Why every existing gate missed it | Generalized prevention |
|---|-----|--------|-------------------------------------|------------------------|
| 4 | P-high | `strip_sql_comments` tracked NO quote state, so a `--` inside a `'...'` string literal opened a phantom comment that blanked the rest of the line -- an **S1 false negative** (a real bad quoted identifier after the literal went unseen). | Fixtures had no `--` inside a literal; the sibling helpers (`tokenize_sql`, `_strip_sql_noise`) handle quotes, but `strip_sql_comments` did not. A hole in the GOVERNANCE TOOL hides defects rather than reporting them. | Track quote state: a `--`/`/*` inside a `'...'`/`"..."` span is data, copied through verbatim. RULE: a comment-stripper that feeds an identifier rule MUST be quote-aware, or it manufactures false negatives. |
| 1 | P1 | The gold `dim_date*` carried a `-1, NULL` unknown member, but that table is MARKED (`dataCategory: Time`). Power BI validates marked date tables as unique/contiguous/**no nulls** -> refresh / time-intelligence can fail. **Present in BOTH `0004` (rss) AND C086's committed `0002`.** | `D7` only checks a date marker EXISTS; `V-RC15` only checks the calendar SPANS the data; `S6` actively REQUIRED a `-1` member on every gold dim (date dim included) -- the tool was pushing toward the bug. Nothing checked "marked date table has no null member". | New rule **S8** (ERROR): a `gold.dim_date*` must carry NO `-1`/NULL member. `S6` now EXEMPTS `dim_date*` (the documented Kimball exception). The two are inverse + complementary. Both migrations fixed (member dropped). |
| 2 | P2 | The fact `date_sk = COALESCE(dd.date_sk, -1)` over a hard-coded calendar span: a real date OUTSIDE the span silently buckets to the `-1` Unknown member, and `V-RC15` stays green (the `-1` member is a valid FK target). | The reconcile/orphan/coverage checks all pass because the `-1` member exists and absorbs the unmatched date -- a false green on genuinely-wrong data. | Debare the join: `date_sk = dd.date_sk` with `date_sk NOT NULL`. An unmatched/NULL fact date now yields NULL and FAILS the load loudly (a real calendar-coverage bug), never masquerades as "Unknown date". |
| 5 | P2 | CSV header dedup added the ORIGINAL name to `seen` but never the GENERATED suffix name, so `["A","A","A_2"]` -> `a, a_2(gen), a_2(real)` collide -> duplicate `CREATE TABLE` columns -> load fails. | No fixture had a real header colliding with a generated suffix; the one collision case tested was simple duplicates. | Reserve the generated name too: loop bumping the suffix until genuinely unused; add each emitted name to a `used` set. Result is always all-unique. |
| 6 | P2 | A ragged row with MORE fields than the header was silently truncated (`[:ncols]`) before COPY; reconcile (row-count only) still passed -> corrupts the faithful-landing contract (an unescaped delimiter / extra column shifts data). | Reconcile compares COUNTS, not widths; the clean Kaggle CSV had no ragged rows. | FAIL LOUD on a row wider than the header (raise with the offending row index + width). A SHORT row stays padded (dirty-faithful); only OVER-wide rows are a corruption risk. |
| 8 | P2 | Reconcile counted PHYSICAL file lines (`sum(1 for _ in f) - 1`); a quoted field with an embedded newline is ONE CSV record across several lines -> `file_rows` over-counts -> a correct COPY reports a false reconcile FAIL. | The Kaggle CSV had no embedded newlines; counting lines == counting records there. | `count_csv_records()` counts with the SAME `csv.reader` COPY consumes. Count records, never physical lines, when reconciling a parsed format. |
| 3 | P2 | `psycopg2` imported at module top, so even `--help` (or importing a pure helper in a db-less / static env) crashed with a traceback instead of the enable steps. | The dev env has the `db` extra; no test imported the loader without it. | Lazy-load inside `connect()` with `ImportError -> "pip install 'retail[db]'"`. The optional driver must never be imported at module scope of an operational script. |
| 7 | P2 | `mapping_ready: pass` recorded, but `source-map.yaml` still held `reviewed_by: "<analyst / reviewer>"` / `reviewed_on: "<YYYY-MM-DD>"` -- a consumer reading the canonical map sees it as UNapproved. | No check cross-reads the machine-readable artifact against the readiness `pass` it underwrites. | Backfill the artifact field FROM the recorded `approvals[]` (data_owner, 2026-06-25). Propagating an approval already given is NOT self-granting. A recorded `pass` must not stand on a placeholder field. |
| 9 | P2 | All 5 metric contracts recorded `readiness.status: pass` (and underwrite `semantic_model_ready: pass`) while their `owner:` field was still the F009 template placeholder. | Same blind spot as #7 -- the readiness status and the contract's own owner field were never reconciled. | Backfill `owner: data_owner` on each (the approval was already in each contract's `readiness.evidence`). The owner field must MATCH the recorded approval. |

## Decision

1. **The four TOOL defects are fixed** (#4 quote-aware strip; #1 the new S8 rule +
   S6 date exemption; #3/#5/#6/#8 loader), each RED-then-GREEN. The static checker
   grew from **27 to 28 rules** (S8); the unit suite from **256 to 272** tests.
2. **S8 is ERROR, deliberately** (not WARNING like S6/S7). S6/S7 enforce
   "override-when" RC defaults (reviewable, non-blocking); S8 is a hard correctness
   invariant whose violation reaches Power BI silently -- exactly what a static gate
   must PREVENT, so it must block. ERROR is coherent here BECAUSE both offending
   migrations were fixed in the same change (CI never goes red on an un-fixed file).
3. **The date-model policy is now explicit (for ANY future table):** a marked date
   table (`dataCategory: Time`) carries NO unknown/sentinel member; an
   unmatched/NULL FACT date is handled OUTSIDE the calendar -- either fail-loud (the
   chosen default: `date_sk NOT NULL` rejects it) or a nullable date FK plus DAX that
   treats blank dates explicitly. It is NEVER absorbed by a `-1` date member. A future
   dataset WITH null transaction dates will therefore hard-fail the gold build by
   design, forcing a conscious decision rather than a silent mislabel.
4. **The #1/#2 fix was re-validated LIVE** for `retail_store_sales` (re-applied
   `0004` to the `training` DB; 0 date `-1` members, 0 NULL `date_sk`, all 12,575 fact
   rows preserved, `retail validate` exit 0 WITH banner across PK/coverage/orphans/
   reconcile). C086's identical fix is **authored + static-checked only** -- C086 is
   not materialized in any reachable DB, so its live re-validation remains its
   standing deferred boundary (Principle VIII); this ADR does NOT claim C086 was
   re-validated.
5. **The two governance-consistency gaps (#7/#9) are reconciled** by backfilling the
   artifact fields from the already-recorded `approvals[]` -- NOT a new approval. The
   ONE field deliberately left as a placeholder is the `publish_ready` approval block
   in the handoff pack: that gate is genuinely pending (Principle V; no self-grant).

## Consequences

- The tool now catches the marked-date-table null trap (S8) and refuses to be fooled
  by the quote-blind comment strip (S1), the silent date bucketing (debared join +
  `NOT NULL`), and three CSV-loader corruptions -- for ARBITRARY future data.
- C086, the worked example, carried the SAME #1/#2 date bug; fixing it means the
  reference migration now models the corrected pattern, not the buggy one.
- The generalized RULES are recorded in `docs/medallion-playbook.md` Appendix A
  (traps 17-20) and the cross-project `~/.claude/global-lessons.md` (2026-06-25), so
  they apply to every future table and outlive this PR.
- **Process lesson (the load-bearing one):** an independent review pass found nine
  real defects that a green self-test suite, a green static checker, AND a green live
  validation all missed. "All my gates are green" is necessary, not sufficient; an
  outside reviewer (human or bot) is part of "done" for a tool meant to handle data
  it has never seen.

## See also

- The worked instance + PR: `mappings/retail_store_sales/` (the `training` DB run),
  PR #23 on `feat/training-e2e-and-tool-maturity`.
- The first hardening wave: `docs/decisions/0005-live-surface-hardening.md`.
- The new rule + its inverse: `S8`/`S6` in `src/seshat/rules/sql.py`; the wiring
  guard `tests/unit/test_rules_wiring.py`; the date-model authority
  `docs/readiness/semantic-model-ready.md`.
- The generalized traps: `docs/medallion-playbook.md` Appendix A (17-20).
- The static-first posture this continues: `.specify/memory/constitution.md`
  Principle VIII; the no-fake-confidence rule: `docs/roadmap/roadmap.md` (#9).
