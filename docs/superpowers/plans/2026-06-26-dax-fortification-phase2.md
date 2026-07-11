# DAX Fortification — Phase 2 (L2 hygiene D-rules) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a batch of stdlib-pure, lexical L2 hygiene rules (WARNING) to the registered `retail check` chain that catch real DAX perf/clarity problems without needing a DAX AST.

**Architecture:** Each rule is a pure `RuleContext -> Iterable[Finding]` function in `src/seshat/rules/dax.py`, registered via `@register`, discovered by the existing runner, and scanning committed TMDL via `iter_model_files` (which auto-exempts `tests/`). All findings are WARNING severity. No new dependencies.

**Tech Stack:** Python 3.13 (stdlib only), pytest. Reuses the existing `parse_tmdl` / `TmdlMeasure` / `iter_model_files` machinery.

## Global Constraints

- **Depends on Phase 1 Task 1 (G6 wiring fix) being merged first.** This plan edits `EXPECTED_RULE_IDS` and the wiring tuples; they must already include `G6`/`g6`.
- **Python:** `requires-python >=3.13`; run tests via `./.venv/Scripts/python.exe -m pytest`.
- **Stdlib-only:** `dependencies = []`. These rules are registered (in the core chain), so they MUST import only stdlib + intra-package modules.
- **Lexical only:** detect via regex over TMDL text / parsed `TmdlMeasure.expression`. NO DAX AST, NO live model, NO type inference.
- **Severity:** all Phase 2 rules are **WARNING** (hygiene/perf, not correctness). Promotion to ERROR is a later owner decision, not this plan.
- **Adding a rule = 3 coordinated edits in one commit:** `@register` decorator in `dax.py`, the new id in `EXPECTED_RULE_IDS`, and the 4-test set.
- **4-test pattern per rule:** `flags_*`, `passes_clean`, locator (`endswith(":N")`), `exempts_tests_prefix`.
- **Locators:** repo-relative POSIX `path:line`.
- **Commits:** end every message with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## File Map

- `src/seshat/rules/dax.py` — MODIFY (Tasks 1-3): add D9, D10, D11 rule functions.
- `tests/unit/test_dax.py` — MODIFY (Tasks 1-3): 4-test set per rule.
- `tests/unit/test_rules_wiring.py` — MODIFY (Tasks 1-3): add each id to `EXPECTED_RULE_IDS`.
- `tests/fixtures/tmdl/` — CREATE (Tasks 1-3): `bad_*` / `clean_*` fixtures per rule.

**Rule batch (contiguous ids, all WARNING, all lexical):**
- **D9** — no hardcoded date literals in measures (use the date table, not `DATE(y,m,d)`).
- **D10** — no `FILTER(ALL(...))` full-table-scan anti-pattern in measures.
- **D11** — every measure carries a `///` doc comment (documentation gate).

(The recon's 4th candidate — a division-hygiene rule — is CUT: D4 already flags bare `/` in measure expressions, so a second rule adds test surface with no new signal. The AST-dependent candidates (circular deps, filter-context correctness, type-match) are CUT under YAGNI; the repo has no DAX AST and L3's escalate path already covers "can't lexically prove this.")

---

## Task 1: D9 — no hardcoded date literals in measures

**Why:** `DATE(2024,1,1)` and quoted ISO date literals in a measure bypass the model's date table and bake in fixed dates — a maintainability + correctness smell. Flag them so authors route through the date dimension.

**Files:**
- Modify: `src/seshat/rules/dax.py` (add rule near the other D-rules)
- Test: `tests/unit/test_dax.py`
- Modify: `tests/unit/test_rules_wiring.py` (add `"D9"`)
- Create: `tests/fixtures/tmdl/bad_date_literal.tmdl`, `tests/fixtures/tmdl/clean_no_date_literal.tmdl`

**Interfaces:**
- Consumes: `iter_model_files(ctx, ".tmdl")`, `parse_tmdl(text) -> TmdlTable | None`, `TmdlMeasure.expression`, `_strip_dax_comments_and_strings` (already in dax.py — strips comments + string literals so a date inside a string is ignored), `Finding`, `Severity`.
- Produces: `d9_no_hardcoded_dates(ctx) -> Iterable[Finding]` (WARNING, rule_id "D9").

- [ ] **Step 1: Create the fixtures**

`tests/fixtures/tmdl/bad_date_literal.tmdl`:

```
table T

	measure SalesSince = CALCULATE([TotalSales], 'gold dim_date'[date] >= DATE(2024, 1, 1))
		displayFolder: Sales
```

`tests/fixtures/tmdl/clean_no_date_literal.tmdl`:

```
table T

	measure TotalSales = SUM('gold fct_sales_rss'[total_spent])
		displayFolder: Sales
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/unit/test_dax.py` (import `d9_no_hardcoded_dates` in the existing `from retail.rules.dax import (...)` block):

```python
def test_d9_flags_date_literal(tmp_path: Path) -> None:
    findings = list(d9_no_hardcoded_dates(_ctx(tmp_path, "bad_date_literal.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D9"
    assert findings[0].severity is Severity.WARNING
    assert "SalesSince" in findings[0].message


def test_d9_passes_clean(tmp_path: Path) -> None:
    assert list(d9_no_hardcoded_dates(_ctx(tmp_path, "clean_no_date_literal.tmdl"))) == []


def test_d9_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(d9_no_hardcoded_dates(_ctx(tmp_path, "bad_date_literal.tmdl")))
    assert findings[0].locator.endswith(":3")


def test_d9_exempts_tests_prefix(tmp_path: Path) -> None:
    rel = "tests/fixtures/tmdl/bad_date_literal.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / "bad_date_literal.tmdl").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d9_no_hardcoded_dates(ctx)) == []
```

- [ ] **Step 3: Run the tests to verify they FAIL**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_dax.py -q --no-cov -k d9`
Expected: FAIL — `ImportError: cannot import name 'd9_no_hardcoded_dates'`.

- [ ] **Step 4: Implement D9 in `dax.py`**

Add near the other D-rules in `src/seshat/rules/dax.py`:

```python
# ---------------------------------------------------------------------------
# D9 — no hardcoded date literals in measures
# ---------------------------------------------------------------------------

# DATE(yyyy, m, d) constructor or a quoted ISO date literal "yyyy-mm-dd".
_DATE_LITERAL = re.compile(r"DATE\s*\(\s*\d{3,4}\s*,|\b\d{4}-\d{2}-\d{2}\b")


@register("D9", "No hardcoded date literals in measures")
def d9_no_hardcoded_dates(ctx: RuleContext) -> Iterable[Finding]:
    """Warn when a measure embeds a hardcoded date (DATE(y,m,d) or "yyyy-mm-dd").

    Dates belong in the date dimension; baked-in literals bypass the model's date
    table and freeze the logic. Comments and string literals are stripped first so
    a date mentioned in a comment/string is not flagged.
    """
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            cleaned = _strip_dax_comments_and_strings(m.expression)
            if _DATE_LITERAL.search(cleaned):
                yield Finding(
                    rule_id="D9",
                    severity=Severity.WARNING,
                    message=(
                        f"Measure '{m.name}' embeds a hardcoded date literal;"
                        " use the date dimension instead"
                    ),
                    locator=f"{rel}:{m.line}",
                )
```

- [ ] **Step 5: Add `"D9"` to `EXPECTED_RULE_IDS`**

In `tests/unit/test_rules_wiring.py`, add `"D9"` next to the other D-family ids:

```python
        "D7",
        "D8",  # TMDL/DAX
        "D9",  # TMDL/DAX hygiene: no hardcoded date literals
```

- [ ] **Step 6: Run the D9 tests + wiring test to verify they PASS**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_dax.py tests/unit/test_rules_wiring.py -q --no-cov -k "d9 or wiring or rule_ids"`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/rules/dax.py tests/unit/test_dax.py tests/unit/test_rules_wiring.py tests/fixtures/tmdl/bad_date_literal.tmdl tests/fixtures/tmdl/clean_no_date_literal.tmdl
git commit -m "feat: add D9 (no hardcoded date literals in measures)

Lexical WARNING rule: flags DATE(y,m,d) / quoted ISO date literals in
measure expressions (comments + strings stripped first). Routes through
iter_model_files (auto-exempts tests/).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: D10 — no `FILTER(ALL(...))` full-table-scan anti-pattern

**Why:** `CALCULATE([X], FILTER(ALL('T'), 'T'[c]="v"))` forces a full-table scan where a column filter (`CALCULATE([X], 'T'[c]="v")`) is faster and clearer. Flag the anti-pattern.

**Files:**
- Modify: `src/seshat/rules/dax.py`
- Test: `tests/unit/test_dax.py`
- Modify: `tests/unit/test_rules_wiring.py` (add `"D10"`)
- Create: `tests/fixtures/tmdl/bad_filter_all.tmdl`, `tests/fixtures/tmdl/clean_column_filter.tmdl`

**Interfaces:**
- Consumes: same machinery as D9.
- Produces: `d10_no_filter_all(ctx) -> Iterable[Finding]` (WARNING, rule_id "D10").

- [ ] **Step 1: Create the fixtures**

`tests/fixtures/tmdl/bad_filter_all.tmdl`:

```
table T

	measure CashSales = CALCULATE([TotalSales], FILTER(ALL('gold dim_billing_type'), 'gold dim_billing_type'[type] = "Cash"))
		displayFolder: Sales
```

`tests/fixtures/tmdl/clean_column_filter.tmdl`:

```
table T

	measure CashSales = CALCULATE([TotalSales], 'gold dim_billing_type'[type] = "Cash")
		displayFolder: Sales
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/unit/test_dax.py` (import `d10_no_filter_all`):

```python
def test_d10_flags_filter_all(tmp_path: Path) -> None:
    findings = list(d10_no_filter_all(_ctx(tmp_path, "bad_filter_all.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D10"
    assert findings[0].severity is Severity.WARNING
    assert "CashSales" in findings[0].message


def test_d10_passes_clean(tmp_path: Path) -> None:
    assert list(d10_no_filter_all(_ctx(tmp_path, "clean_column_filter.tmdl"))) == []


def test_d10_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(d10_no_filter_all(_ctx(tmp_path, "bad_filter_all.tmdl")))
    assert findings[0].locator.endswith(":3")


def test_d10_exempts_tests_prefix(tmp_path: Path) -> None:
    rel = "tests/fixtures/tmdl/bad_filter_all.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / "bad_filter_all.tmdl").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d10_no_filter_all(ctx)) == []
```

- [ ] **Step 3: Run the tests to verify they FAIL**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_dax.py -q --no-cov -k d10`
Expected: FAIL — `ImportError: cannot import name 'd10_no_filter_all'`.

- [ ] **Step 4: Implement D10 in `dax.py`**

```python
# ---------------------------------------------------------------------------
# D10 — no FILTER(ALL(...)) full-table-scan anti-pattern
# ---------------------------------------------------------------------------

# FILTER ( ALL ( ... -- a full-table scan where a column filter usually suffices.
_FILTER_ALL = re.compile(r"FILTER\s*\(\s*ALL\s*\(", re.IGNORECASE)


@register("D10", "No FILTER(ALL(...)) full-table-scan anti-pattern")
def d10_no_filter_all(ctx: RuleContext) -> Iterable[Finding]:
    """Warn when a measure uses FILTER(ALL(...)); prefer a column filter in CALCULATE.

    Comments and string literals are stripped first so the pattern is only matched
    in live DAX, not in a comment or string.
    """
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        for m in table.measures:
            cleaned = _strip_dax_comments_and_strings(m.expression)
            if _FILTER_ALL.search(cleaned):
                yield Finding(
                    rule_id="D10",
                    severity=Severity.WARNING,
                    message=(
                        f"Measure '{m.name}' uses FILTER(ALL(...));"
                        " prefer a column filter inside CALCULATE"
                    ),
                    locator=f"{rel}:{m.line}",
                )
```

- [ ] **Step 5: Add `"D10"` to `EXPECTED_RULE_IDS`**

```python
        "D9",  # TMDL/DAX hygiene: no hardcoded date literals
        "D10",  # TMDL/DAX hygiene: no FILTER(ALL(...)) anti-pattern
```

- [ ] **Step 6: Run the D10 tests + wiring test to verify they PASS**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_dax.py tests/unit/test_rules_wiring.py -q --no-cov -k "d10 or wiring or rule_ids"`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/rules/dax.py tests/unit/test_dax.py tests/unit/test_rules_wiring.py tests/fixtures/tmdl/bad_filter_all.tmdl tests/fixtures/tmdl/clean_column_filter.tmdl
git commit -m "feat: add D10 (no FILTER(ALL(...)) anti-pattern)

Lexical WARNING rule: flags FILTER(ALL( in measure expressions; prefer
a column filter inside CALCULATE. Comments + strings stripped first.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: D11 — every measure carries a `///` doc comment

**Why:** A measure with no description is undocumented analytical truth. TMDL writes measure docs as `///` lines immediately above the `measure` block. Flag measures lacking one. (This requires a small parser extension: `parse_tmdl` does not currently capture the `///` doc line, so D11 re-scans the raw text by line rather than relying on `TmdlMeasure`.)

**Files:**
- Modify: `src/seshat/rules/dax.py`
- Test: `tests/unit/test_dax.py`
- Modify: `tests/unit/test_rules_wiring.py` (add `"D11"`)
- Create: `tests/fixtures/tmdl/bad_no_doc.tmdl`, `tests/fixtures/tmdl/clean_with_doc.tmdl`

**Interfaces:**
- Consumes: `iter_model_files`, `parse_tmdl` (to get measure names + line numbers), `Finding`, `Severity`. Reads the raw TMDL lines to check for a preceding `///` line.
- Produces: `d11_measures_documented(ctx) -> Iterable[Finding]` (WARNING, rule_id "D11").

- [ ] **Step 1: Create the fixtures**

`tests/fixtures/tmdl/bad_no_doc.tmdl`:

```
table T

	measure UndocumentedSales = SUM('gold fct_sales_rss'[total_spent])
		displayFolder: Sales
```

`tests/fixtures/tmdl/clean_with_doc.tmdl`:

```
table T

	/// Total money taken across all transactions.
	measure DocumentedSales = SUM('gold fct_sales_rss'[total_spent])
		displayFolder: Sales
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/unit/test_dax.py` (import `d11_measures_documented`):

```python
def test_d11_flags_undocumented_measure(tmp_path: Path) -> None:
    findings = list(d11_measures_documented(_ctx(tmp_path, "bad_no_doc.tmdl")))
    assert len(findings) == 1
    assert findings[0].rule_id == "D11"
    assert findings[0].severity is Severity.WARNING
    assert "UndocumentedSales" in findings[0].message


def test_d11_passes_documented(tmp_path: Path) -> None:
    assert list(d11_measures_documented(_ctx(tmp_path, "clean_with_doc.tmdl"))) == []


def test_d11_locator_includes_line_number(tmp_path: Path) -> None:
    findings = list(d11_measures_documented(_ctx(tmp_path, "bad_no_doc.tmdl")))
    assert findings[0].locator.endswith(":3")


def test_d11_exempts_tests_prefix(tmp_path: Path) -> None:
    rel = "tests/fixtures/tmdl/bad_no_doc.tmdl"
    dest = tmp_path / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        (FIXTURES / "bad_no_doc.tmdl").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    ctx = RuleContext(repo_root=tmp_path, tracked_files=(rel,))
    assert list(d11_measures_documented(ctx)) == []
```

- [ ] **Step 3: Run the tests to verify they FAIL**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_dax.py -q --no-cov -k d11`
Expected: FAIL — `ImportError: cannot import name 'd11_measures_documented'`.

- [ ] **Step 4: Implement D11 in `dax.py`**

D11 uses `parse_tmdl` for measure names + 1-based line numbers, then inspects the raw text line immediately above each measure for a `///` doc comment:

```python
# ---------------------------------------------------------------------------
# D11 — every measure carries a /// doc comment
# ---------------------------------------------------------------------------


@register("D11", "Each measure must have a /// doc comment")
def d11_measures_documented(ctx: RuleContext) -> Iterable[Finding]:
    """Warn when a measure has no TMDL `///` doc comment on the line above it.

    TMDL writes a measure description as one or more `///` lines immediately
    preceding the `measure` header. A measure with no such line is undocumented.
    Uses parse_tmdl for measure names + line numbers, then checks the raw line
    above each measure header (skipping blank lines) for a `///` prefix.
    """
    for rel, text in iter_model_files(ctx, ".tmdl"):
        table = parse_tmdl(text)
        if table is None:
            continue
        lines = text.splitlines()
        for m in table.measures:
            # m.line is 1-based; the line above is index m.line - 2.
            idx = m.line - 2
            documented = False
            while idx >= 0 and not lines[idx].strip():
                idx -= 1  # skip blank lines between the doc and the measure
            if idx >= 0 and lines[idx].strip().startswith("///"):
                documented = True
            if not documented:
                yield Finding(
                    rule_id="D11",
                    severity=Severity.WARNING,
                    message=f"Measure '{m.name}' has no /// doc comment",
                    locator=f"{rel}:{m.line}",
                )
```

- [ ] **Step 5: Add `"D11"` to `EXPECTED_RULE_IDS`**

```python
        "D10",  # TMDL/DAX hygiene: no FILTER(ALL(...)) anti-pattern
        "D11",  # TMDL/DAX hygiene: every measure documented (///)
```

- [ ] **Step 6: Run the D11 tests + wiring test to verify they PASS**

Run: `./.venv/Scripts/python.exe -m pytest tests/unit/test_dax.py tests/unit/test_rules_wiring.py -q --no-cov -k "d11 or wiring or rule_ids"`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/rules/dax.py tests/unit/test_dax.py tests/unit/test_rules_wiring.py tests/fixtures/tmdl/bad_no_doc.tmdl tests/fixtures/tmdl/clean_with_doc.tmdl
git commit -m "feat: add D11 (every measure must have a /// doc comment)

Lexical WARNING rule: flags measures with no TMDL /// doc line above the
measure header (blank lines skipped). Uses parse_tmdl for names/lines.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Reconcile the committed model + full-suite verification

**Why:** D9–D11 are WARNING (they never fail the build), but they WILL fire against the real committed TMDL if any shipped measure embeds a date literal, uses FILTER(ALL()), or lacks a `///` doc. Confirm the real model's hygiene state and make the warnings honest (not noise).

**Files:** possibly `powerbi/**/*.tmdl` (only if a shipped measure legitimately needs a doc/refactor — do NOT suppress real signal).

- [ ] **Step 1: Run the new rules against the real repo to see what fires**

Run: `./.venv/Scripts/python.exe -m retail.cli check --repo . 2>&1 | grep -E "\[warning\] D(9|10|11)"`
Expected: a list (possibly empty) of D9/D10/D11 warnings against committed measures.

- [ ] **Step 2: Decide per warning (judgment, not blanket suppression)**

For each warning:
- **D11 (missing doc):** the shipped measures already carry `///` docs (verified: `gold fct_sales_rss.tmdl` lines 16/22/28). If any genuinely lacks one, add a real one-line `///` description — do not fabricate.
- **D9 / D10:** if a shipped measure truly embeds a date literal or FILTER(ALL()), that is real signal — leave it surfaced (WARNING does not fail CI) and note it for a follow-up refactor; do NOT weaken the rule to hide it.

If edits are made, stage the specific TMDL files.

- [ ] **Step 3: Full-suite run with coverage (project default)**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: PASS — all prior tests plus the 12 new D9–D11 tests (4 each), 0 failed. `EXPECTED_RULE_IDS` now has 31 ids (28 + D9 + D10 + D11); the wiring test confirms `len(all_rules()) == 31`.

- [ ] **Step 4: Style check**

Run: `./.venv/Scripts/python.exe -m ruff check src/seshat/rules/dax.py tests/unit/test_dax.py tests/unit/test_rules_wiring.py`
Then: `./.venv/Scripts/python.exe -m black --check src/seshat/ tests/unit/`
Expected: clean.

- [ ] **Step 5: Commit any model doc edits (if Step 2 made them)**

```bash
git add powerbi/
git commit -m "docs: add measure /// docs flagged by D11

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

(Skip if Step 2 made no edits.)

- [ ] **Step 6: Final confirmation**

Phase 2 complete: 3 stdlib-pure lexical L2 hygiene rules (D9 dates, D10 FILTER(ALL), D11 docs) added to the registered `retail check` gate as WARNINGs; wiring test validates all 31 rules; AST-dependent candidates cut under YAGNI.

---

## Self-Review Notes (author)

- **Spec coverage:** Phase 2 batch (D9/D10/D11) = Tasks 1-3; cut list (division-hygiene dup of D4, AST-dependent rules) documented in the File Map. WARNING severity per spec. 4-test pattern per rule. Wiring-test update per rule.
- **Dependency on Phase 1 Task 1** stated as a Global Constraint (G6 fix must precede `EXPECTED_RULE_IDS` edits).
- **Type consistency:** every rule is `RuleContext -> Iterable[Finding]`, `@register("D#", "...")`, `Finding(rule_id, severity=Severity.WARNING, message, locator=f"{rel}:{m.line}")` — uniform across the three tasks. Fixture line `:3` matches the measure header line in each `bad_*` fixture (table line 1, blank line 2, measure line 3; D11's documented fixture has the `///` on line 3 and measure on line 4, but the `bad_no_doc` fixture keeps measure on line 3).
- **No placeholders:** every rule body, test, fixture, and command is concrete.
- **Honest warnings:** Task 4 reconciles against the real model rather than assuming zero warnings.
