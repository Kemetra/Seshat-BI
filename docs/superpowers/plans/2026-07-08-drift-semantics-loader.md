# Live-drift semantics loader — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the returns/PII semantic rulings from `source-map.yaml` into a `DriftSemantics`, and wire it into `retail drift`'s live leg so the `returns_rule_drift` / `pii_surface_drift` classes can fire end-to-end.

**Architecture:** A new lazy-pyyaml module `src/retail/drift_semantics.py` (mirrors `validate_targets.py`) exposing `load_drift_semantics(path) -> DriftSemantics`. The CLI live leg resolves a source-map path (`--source-map` override, else the sibling of `--baseline`), loads semantics if the file exists, and threads it into `to_findings_dict`. The pure `drift.py` is unchanged; only the CLI grows a wiring step.

**Tech Stack:** Python 3.13, pyyaml (lazy import — optional dep, never on the static-core import path), frozen dataclasses, argparse, pytest (`pytest.mark.unit`), ruff.

**Working directory:** `.claude/worktrees/015-retail-drift-runtime`, branch `feat/drift-semantics-loader` (off `origin/main`). Run tests with `PYTHONPATH=src` so imports resolve to THIS worktree, not the editable install pointing at the main checkout.

## Global Constraints

- `src/retail/drift.py` stays PURE + stdlib-only; the yaml dep is lazy-imported inside the loader, never at `drift.py`/CLI module scope (mirrors `validate_targets` + the psycopg2 lazy pattern).
- Never fabricate a PII-drop the map did not state; a missing `pii` field is `false`, a missing `decision` is not-drop, a placeholder `derived_from` (`<...>`) is None.
- Deterministic output: `dropped_pii_columns` is a `frozenset` (order-independent by construction).
- ASCII, UTF-8 no BOM. Test with `PYTHONPATH=src python -m pytest ... -q --no-cov`.
- Honest-skip: against the only filled mapping the loader is a documented no-op; prove non-empty paths with synthetic fixture yaml. State this in the PR.

---

## Interfaces this plan builds against (verbatim, from the tree)

From `src/retail/drift.py` (shipped, PR #231):

```python
@dataclass(frozen=True)
class DriftSemantics:
    returns_column: str | None = None
    dropped_pii_columns: frozenset[str] = field(default_factory=frozenset)
```

`source-map.yaml` shape (relevant fields only):

```yaml
columns:
  - source_name: "customer_id"
    decision: "keep"      # keep | drop | derive
    pii: true             # bool
derived_columns:          # may be [] (RC8 deviation)
  - name: "is_return"
    derived_from: "<authoritative_type_col>"   # the AUTHORITATIVE source column
```

CLI live-leg wiring point — `src/retail/cli/commands/drift.py`, inside `_run_live_drift`, the `to_findings_dict(...)` call currently passes no `semantics`. The parser (`_add_drift_parser` in `src/retail/cli/parser.py`) already has `--baseline`, `--dsn`, `--format`; this plan adds `--source-map`.

---

## File Structure

- **Create** `src/retail/drift_semantics.py` — `load_drift_semantics(path) -> DriftSemantics`; private `_dropped_pii(columns)`, `_returns_column(doc)`. Lazy pyyaml.
- **Create** `tests/unit/test_drift_semantics.py` — synthetic-yaml + real-mapping unit tests.
- **Modify** `src/retail/cli/parser.py` — add `--source-map` to `_add_drift_parser`.
- **Modify** `src/retail/cli/commands/drift.py` — resolve path + load + thread `semantics` into `_run_live_drift`.
- **Modify** `tests/unit/test_cli_drift.py` — CLI wiring tests (monkeypatched, no DB).

---

## Task 1: the loader module (source-map.yaml -> DriftSemantics)

**Files:**
- Create: `src/retail/drift_semantics.py`
- Test: `tests/unit/test_drift_semantics.py`

**Interfaces:**
- Consumes: `retail.drift.DriftSemantics`.
- Produces: `load_drift_semantics(source_map_path: str | Path) -> DriftSemantics`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_drift_semantics.py
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]

_SYNTH = """\
meta:
  table_id: t
columns:
  - source_name: keep_clean
    decision: keep
    pii: false
  - source_name: kept_pii
    decision: keep
    pii: true
  - source_name: dropped_pii
    decision: drop
    pii: true
  - source_name: dropped_plain
    decision: drop
    pii: false
derived_columns:
  - name: is_return
    derived_from: txn_type
"""


def _write(tmp_path, text):
    p = tmp_path / "source-map.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_dropped_pii_is_pii_true_and_decision_drop_only(tmp_path):
    from retail.drift_semantics import load_drift_semantics

    sem = load_drift_semantics(_write(tmp_path, _SYNTH))
    # only dropped_pii qualifies: kept_pii is kept, dropped_plain isn't pii
    assert sem.dropped_pii_columns == frozenset({"dropped_pii"})


def test_returns_column_is_the_derived_from_source_column(tmp_path):
    from retail.drift_semantics import load_drift_semantics

    sem = load_drift_semantics(_write(tmp_path, _SYNTH))
    assert sem.returns_column == "txn_type"  # NOT "is_return" (the derived name)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift_semantics.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'retail.drift_semantics'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/retail/drift_semantics.py
"""Extract the returns/PII semantic rulings from a source-map.yaml into a
retail.drift.DriftSemantics, so retail drift's live leg can fire the
returns_rule_drift / pii_surface_drift classes.

SEPARATE MODULE ON PURPOSE (mirrors validate_targets.py): this parses YAML
(pyyaml, an optional/dev dep), so it must NOT be on retail.drift's import path,
whose stdlib-only invariant keeps the static core dependency-free. The CLI
imports this lazily. This module depends on retail.drift (for DriftSemantics),
never the reverse -- the pure core gains no new dependency.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .drift import DriftSemantics


def _dropped_pii(columns: list[dict[str, Any]]) -> frozenset[str]:
    """Columns flagged PII AND dropped -- the only ones that can 'reappear'. A
    pii:true + decision:keep column never left the mapped output, so it is not a
    reappearance candidate. Missing pii -> false; missing decision -> not drop."""
    return frozenset(
        c["source_name"]
        for c in columns
        if c.get("pii") is True
        and c.get("decision") == "drop"
        and c.get("source_name")
    )


def _returns_column(doc: dict[str, Any]) -> str | None:
    """The AUTHORITATIVE SOURCE column the returns rule keys on: the is_return
    derived column's `derived_from`. classify_drift watches the profiled BRONZE
    source columns, so the derived name (is_return, absent from bronze) would
    never fire -- derived_from names the real source column. None when
    derived_columns is empty/absent, no is_return entry exists, or derived_from
    is an unfilled placeholder (<...>)."""
    for d in doc.get("derived_columns") or []:
        if d.get("name") == "is_return":
            src = d.get("derived_from")
            if isinstance(src, str) and src and not src.startswith("<"):
                return src
            return None
    return None


def load_drift_semantics(source_map_path: str | Path) -> DriftSemantics:
    """Parse source-map.yaml into a DriftSemantics. Raises ValueError on
    malformed yaml or a missing top-level `columns` key."""
    import yaml  # lazy: optional dep, never on the static-core import path

    text = Path(source_map_path).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict) or "columns" not in doc:
        raise ValueError(
            f"source-map.yaml: missing required top-level 'columns' "
            f"({source_map_path})"
        )
    columns = doc.get("columns") or []
    return DriftSemantics(
        returns_column=_returns_column(doc),
        dropped_pii_columns=_dropped_pii(columns),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift_semantics.py -q --no-cov`
Expected: PASS (2 passed). If pyyaml is missing: `python -m pip install pyyaml` (it is a dev dep; `validate_targets` already relies on it).

- [ ] **Step 5: Commit**

```bash
git add src/retail/drift_semantics.py tests/unit/test_drift_semantics.py
git commit -m "feat: source-map.yaml -> DriftSemantics loader (returns derived_from + dropped-PII)"
```

---

## Task 2: edge cases + the real-mapping no-op guard

**Files:**
- Modify: `src/retail/drift_semantics.py` (only if an edge case reveals a bug)
- Test: `tests/unit/test_drift_semantics.py`

**Interfaces:**
- Consumes: `load_drift_semantics` (Task 1).
- Produces: nothing new — hardens Task 1.

- [ ] **Step 1: Write the failing test** (append)

```python
def test_empty_derived_columns_means_no_returns_column(tmp_path):
    from retail.drift_semantics import load_drift_semantics

    text = "columns:\n  - source_name: a\n    decision: keep\n    pii: false\nderived_columns: []\n"
    sem = load_drift_semantics(_write(tmp_path, text))
    assert sem.returns_column is None


def test_placeholder_derived_from_means_no_returns_column(tmp_path):
    from retail.drift_semantics import load_drift_semantics

    text = (
        "columns:\n  - source_name: a\n    decision: keep\n    pii: false\n"
        "derived_columns:\n  - name: is_return\n    derived_from: \"<authoritative_type_col>\"\n"
    )
    sem = load_drift_semantics(_write(tmp_path, text))
    assert sem.returns_column is None


def test_missing_columns_key_raises(tmp_path):
    from retail.drift_semantics import load_drift_semantics

    with pytest.raises(ValueError, match="columns"):
        load_drift_semantics(_write(tmp_path, "meta:\n  table_id: t\n"))


def test_missing_pii_or_decision_fields_are_conservative(tmp_path):
    from retail.drift_semantics import load_drift_semantics

    # a column with no pii key and no decision key must NOT count as dropped-PII
    text = "columns:\n  - source_name: bare\n"
    sem = load_drift_semantics(_write(tmp_path, text))
    assert sem.dropped_pii_columns == frozenset()


def test_real_retail_store_sales_mapping_is_a_noop(tmp_path):
    # DOCUMENTED no-op: RC8-deviated (derived_columns: []) + the one pii:true
    # column (customer_id) is decision:keep. Guards against a future mapping
    # change silently activating a class.
    from retail.drift_semantics import load_drift_semantics

    real = _ROOT / "mappings" / "retail_store_sales" / "source-map.yaml"
    sem = load_drift_semantics(real)
    assert sem.returns_column is None
    assert sem.dropped_pii_columns == frozenset()
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift_semantics.py -q --no-cov`
Expected: PASS (7 passed total). The Task-1 implementation already handles all these; if any fails, fix the loader minimally (the fields it reads are all `.get()`-guarded).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_drift_semantics.py
git commit -m "test: drift-semantics loader edge cases + real-mapping no-op guard"
```

---

## Task 3: wire the loader into the retail drift CLI live leg

**Files:**
- Modify: `src/retail/cli/parser.py` (add `--source-map` to `_add_drift_parser`)
- Modify: `src/retail/cli/commands/drift.py` (resolve path + load + thread semantics)
- Test: `tests/unit/test_cli_drift.py`

**Interfaces:**
- Consumes: `load_drift_semantics` (Task 1); `_run_live_drift` (existing).
- Produces: `retail drift --source-map PATH`; the live leg passes `semantics` to `to_findings_dict`.

- [ ] **Step 1: Write the failing test** (append to `tests/unit/test_cli_drift.py`)

```python
_CONFORMANT = "mappings/retail_store_sales/source-profile.md"


def test_drift_live_loads_sibling_source_map(capsys, monkeypatch, tmp_path):
    # The live leg auto-discovers the sibling source-map.yaml and threads its
    # semantics into the comparison. Patched so no real DB is touched.
    from retail import cli
    import retail.cli.commands.drift as drift_cmd

    calls = {}

    monkeypatch.setattr(cli, "_ensure_driver", lambda: True)
    monkeypatch.setattr(cli, "_make_runner", lambda config: "RUNNER")

    def fake_loader(path):
        calls["path"] = str(path)
        from retail.drift import DriftSemantics
        return DriftSemantics()

    monkeypatch.setattr(drift_cmd, "load_drift_semantics", fake_loader, raising=False)

    def fake_profile(runner, table, pk):
        # minimal ProfileResult so to_findings_dict runs
        from retail.profile import ProfileResult, PkProof
        return ProfileResult(table=table, row_count=1, column_count=0,
                             columns=(), pk=PkProof(total=1, distinct_pk=1, null_pk=0, is_unique=True))
    monkeypatch.setattr("retail.profile.profile", fake_profile)

    main(["drift", "--baseline", _CONFORMANT, "--dsn", "postgresql://u@h/db"])
    # sibling source-map.yaml next to the baseline was the loaded path
    assert calls["path"].replace("\\", "/").endswith(
        "mappings/retail_store_sales/source-map.yaml"
    )


def test_drift_source_map_flag_missing_file_is_clean_error(capsys, monkeypatch):
    from retail import cli

    monkeypatch.setattr(cli, "_ensure_driver", lambda: True)
    rc = main(
        ["drift", "--baseline", _CONFORMANT, "--dsn", "postgresql://u@h/db",
         "--source-map", "does/not/exist.yaml"]
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "source-map" in err.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_cli_drift.py -q --no-cov`
Expected: FAIL — argparse rejects `--source-map` (rc 2), and `load_drift_semantics` is not imported in `drift.py`.

- [ ] **Step 3a: Add the `--source-map` argument** — in `src/retail/cli/parser.py`, inside `_add_drift_parser`, after the `--dsn` argument:

```python
    drift.add_argument(
        "--source-map",
        dest="source_map",
        default=None,
        metavar="PATH",
        help="path to the table's source-map.yaml (returns/PII rulings for the "
        "live leg). Default: the source-map.yaml sibling of --baseline. Absent "
        "=> returns/PII drift classes stay silent.",
    )
```

- [ ] **Step 3b: Thread semantics into the live leg** — in `src/retail/cli/commands/drift.py` `_run_live_drift`, add a module-level lazy import inside the function's import block and resolve+load before the `to_findings_dict` call. Add near the other `from retail...` imports inside `_run_live_drift`:

```python
    from pathlib import Path as _Path

    from retail.drift_semantics import load_drift_semantics
```

Then, immediately BEFORE the `try:` that builds the runner, resolve the semantics:

```python
    # Semantics for returns/PII drift: --source-map if given, else the sibling of
    # the baseline. Absent -> None (those classes stay silent). A NAMED path that
    # is missing is a clean error, not a silent skip.
    sm_arg = getattr(args, "source_map", None)
    if sm_arg is not None:
        sm_path = _Path(sm_arg)
        if not sm_path.is_file():
            print(
                f"retail drift: --source-map file not found: {sm_arg}",
                file=sys.stderr,
            )
            return 1
    else:
        sm_path = _Path(args.baseline).parent / "source-map.yaml"
    try:
        semantics = load_drift_semantics(sm_path) if sm_path.is_file() else None
    except (OSError, ValueError) as exc:
        print(f"retail drift: cannot load source-map {sm_path}: {exc}", file=sys.stderr)
        return 1
```

Then change the existing `to_findings_dict(...)` call in `_run_live_drift` to pass `semantics=semantics`:

```python
    doc = to_findings_dict(
        parsed.profile,
        observed,
        ReportContext(
            baseline_ref=str(args.baseline),
            evidence=[str(args.baseline)],
            reprofiled_by="agent (retail.profile, read-only session)",
        ),
        semantics=semantics,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_cli_drift.py -q --no-cov`
Expected: PASS. Run the full drift trio too:
`PYTHONPATH=src python -m pytest tests/unit/test_drift.py tests/unit/test_source_profile_reader.py tests/unit/test_cli_drift.py tests/unit/test_drift_semantics.py -q --no-cov`

- [ ] **Step 5: Commit**

```bash
git add src/retail/cli/parser.py src/retail/cli/commands/drift.py tests/unit/test_cli_drift.py
git commit -m "feat: retail drift --source-map + auto-discover sibling; thread DriftSemantics into the live leg"
```

---

## Task 4: full verification + finish branch

**Files:** none (verification only)

- [ ] **Step 1: ruff format + lint**

Run: `ruff format --check src tests && ruff check src tests`
Expected: clean. If format differs: `ruff format src tests` then re-commit.

- [ ] **Step 2: CodeScene health on the new + modified files**

Verify `src/retail/drift_semantics.py` and `src/retail/cli/commands/drift.py` are >= threshold (ideally 10.0) via the CodeScene MCP `code_health_review`. `_run_live_drift` grew — if it trips Bumpy Road / Complex Method, extract the semantics-resolution block into a `_resolve_semantics(args) -> DriftSemantics | None | int` helper (return an int rc to signal the clean-error early-return) or a small helper that raises a typed sentinel; keep the guard flat.

- [ ] **Step 3: full unit suite**

Run: `PYTHONPATH=src python -m pytest -m unit -q`
Expected: all pass except the 2 pre-existing `test_workspace_init.py` git-signing env failures (documented baseline). No NEW failures.

- [ ] **Step 4: retail check exit 0**

Run: `PYTHONPATH=src python -c "from retail.cli import main; import sys; sys.exit(main(['check','--repo','.']))"`
Expected: exit 0. (Note: `python -m retail check` does NOT work — no `__main__.py`; use the console-script entry.)

- [ ] **Step 5: finish the branch**

Use `superpowers:finishing-a-development-branch`. PR title MUST carry `feat:` (squash-merge subject; rule P2). The PR body MUST state the honest-skip reality: against the only filled mapping the loader is a no-op (RC8-deviated + no dropped-PII), so this wires the seam and is proven with synthetic fixtures, NOT a live returns/PII demonstration.

---

## Self-review notes

- **Spec coverage:** loader module + extraction rules (Task 1), edge cases + real-mapping no-op (Task 2), CLI auto-discover + `--source-map` override + missing-file error (Task 3), verification + honest-skip PR framing (Task 4). All design sections covered.
- **Type consistency:** `load_drift_semantics(path) -> DriftSemantics` stable across tasks; `DriftSemantics(returns_column, dropped_pii_columns)` matches the shipped dataclass; the CLI passes `semantics=` (keyword) matching `to_findings_dict`'s shipped optional param.
- **Boundary:** `drift.py` untouched (pure); yaml stays lazy inside the loader; the loader depends on `drift`, never the reverse.
- **Known residual (flagged):** the live DB round-trip remains untested by design; Task 3's CLI tests monkeypatch the runner + profile. The real returns/PII activation awaits a filled mapping that actually drops a PII column or records a returns `derived_from` (documented, owner-visible in the PR).
