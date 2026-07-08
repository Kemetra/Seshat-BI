# retail drift runtime — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the F014 source-drift detector runtime — a pure `ProfileResult`-vs-`ProfileResult` comparator that classifies drift into the nine taxonomy classes, derives a Source-Ready status, emits the `source-drift-findings.schema.json` shape, reads a template-conformant `source-profile.md` baseline, and exposes a fail-closed `retail drift` CLI command.

**Architecture:** Three layers. (1) `src/retail/drift.py` — pure, I/O-free classify + status + emit over `retail.profile` dataclasses. (2) `src/retail/source_profile_reader.py` — parse a template-conformant committed `source-profile.md` into a `ProfileResult`; report non-conformant baselines as uncomparable. (3) `src/retail/cli/commands/drift.py` + parser + dispatch row — mirrors `validate`'s two-mode (deferred-live vs live) posture. The pure core is invariant across any future baseline-I/O decision.

**Tech Stack:** Python 3.13, dataclasses (frozen), argparse dispatch table, pytest (`pytest.mark.unit`), jsonschema (Draft 2020-12), ruff.

**Working directory:** `.claude/worktrees/015-retail-drift-runtime` (isolated worktree off `origin/main`). Set `PYTHONPATH=src` for pytest so imports resolve to THIS worktree, not the stale editable install pointing at the main checkout.

---

## Interfaces this plan builds against (verbatim, from the tree)

From `src/retail/profile.py`:

```python
@dataclass(frozen=True)
class ColumnProfile:
    name: str
    missing_count: int
    missing_pct: float
    distinct_cardinality: int

@dataclass(frozen=True)
class PkProof:
    total: int
    distinct_pk: int
    null_pk: int
    is_unique: bool

@dataclass(frozen=True)
class ProfileResult:
    table: str
    row_count: int
    column_count: int
    columns: tuple[ColumnProfile, ...]
    pk: PkProof
```

From `schemas/source-drift-findings.schema.json` — top-level `required`:
`["table", "baseline", "observed", "findings", "status", "blocking_reasons", "evidence", "principle_v_handoff"]`, `additionalProperties: false`.
- `status` enum: `not_started | pending_live_reprofile | pass | warning | blocked`
- `finding` required: `["drift_class", "column", "before", "after", "severity", "principle_v"]`; `severity` ∈ `warning | blocked`; `before`/`after` are STRINGS.
- `observed` required: `["available"]`; `available: false` ⇒ status `pending_live_reprofile`.
- `principle_v_handoff` item required: `["question", "drift_class", "measured_fact", "owner"]`.
- `driftClass` enum: `column_added, column_removed, column_retyped, missingness_shift, cardinality_shift, grain_pk_drift, returns_rule_drift, semantic_pair_drift, pii_surface_drift`.

CLI seam: a new command needs a `_lazy(".commands.drift", "run_drift")` row in `src/retail/cli/__init__.py`'s `_DISPATCH`, an `_add_drift_parser(sub)` in `src/retail/cli/parser.py` called from `_build_parser()`, and a `run_drift(args) -> int` handler in `src/retail/cli/commands/drift.py`. Handlers return `int`.

---

## File Structure

- **Create** `src/retail/drift.py` — `DriftFinding`, `HandoffQuestion`, `DriftReport` dataclasses; `classify_drift()`, `derive_status()`, `to_findings_dict()`. Pure.
- **Create** `src/retail/source_profile_reader.py` — `ParsedBaseline` (a `ProfileResult` + `type_by_column` map + `uncomparable` reason); `read_source_profile(path) -> ParsedBaseline`.
- **Create** `src/retail/cli/commands/drift.py` — `run_drift(args) -> int`.
- **Modify** `src/retail/cli/parser.py` — add `_add_drift_parser(sub)`, call it in `_build_parser()`.
- **Modify** `src/retail/cli/__init__.py:124-145` — add `"drift": _lazy(".commands.drift", "run_drift"),` to `_DISPATCH`.
- **Create** `tests/unit/test_drift.py`, `tests/unit/test_source_profile_reader.py`, `tests/unit/test_cli_drift.py`.

Run tests with: `PYTHONPATH=src python -m pytest tests/unit/test_drift.py -q --no-cov` (adjust path per task).

---

## Task 1: drift.py dataclasses + column diff (added/removed)

**Files:**
- Create: `src/retail/drift.py`
- Test: `tests/unit/test_drift.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_drift.py
import pytest

pytestmark = pytest.mark.unit

from retail.profile import ColumnProfile, PkProof, ProfileResult


def _col(name, missing_pct=0.0, card=10):
    return ColumnProfile(name=name, missing_count=0, missing_pct=missing_pct, distinct_cardinality=card)


def _profile(cols, *, table="bronze.t", rows=100, is_unique=True, null_pk=0):
    return ProfileResult(
        table=table,
        row_count=rows,
        column_count=len(cols),
        columns=tuple(cols),
        pk=PkProof(total=rows, distinct_pk=rows, null_pk=null_pk, is_unique=is_unique),
    )


def test_column_added_is_warning():
    from retail.drift import classify_drift
    base = _profile([_col("a")])
    obs = _profile([_col("a"), _col("b")])
    findings = classify_drift(base, obs)
    added = [f for f in findings if f.drift_class == "column_added"]
    assert len(added) == 1
    assert added[0].column == "b"
    assert added[0].severity == "warning"
    assert added[0].principle_v is False


def test_column_removed_is_blocked():
    from retail.drift import classify_drift
    base = _profile([_col("a"), _col("b")])
    obs = _profile([_col("a")])
    findings = classify_drift(base, obs)
    removed = [f for f in findings if f.drift_class == "column_removed"]
    assert len(removed) == 1
    assert removed[0].column == "b"
    assert removed[0].severity == "blocked"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'retail.drift'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/retail/drift.py
"""F014 source-drift detector runtime -- the pure comparator.

Diffs a baseline ProfileResult against an observed re-profile (or None when
the live boundary is absent), classifies each difference into the nine drift
classes of docs/readiness/source-drift.md, derives the Source-Ready status,
and emits the schemas/source-drift-findings.schema.json shape.

PURE + I/O-FREE: no DB, no filesystem, no CLI. Depends only on retail.profile's
frozen dataclasses. Never emits a numeric drift score (hard rule #9). Never
re-decides a Principle-V class (grain/PK, returns, PII, identity) -- it measures,
classifies, and raises a handoff for a named owner.
"""

from __future__ import annotations

from dataclasses import dataclass

from .profile import ProfileResult

# The three always-Principle-V classes (semantic_pair_drift is Principle-V only
# when it underpins identity -- not measured mechanically here).
_ALWAYS_PRINCIPLE_V = frozenset(
    {"grain_pk_drift", "returns_rule_drift", "pii_surface_drift"}
)


@dataclass(frozen=True)
class DriftFinding:
    drift_class: str
    column: str
    before: str
    after: str
    severity: str  # "warning" | "blocked"
    principle_v: bool
    note: str | None = None


@dataclass(frozen=True)
class HandoffQuestion:
    question: str
    drift_class: str
    measured_fact: str
    owner: str


def classify_drift(
    baseline: ProfileResult, observed: ProfileResult | None
) -> list[DriftFinding]:
    """Classify the differences between baseline and observed into drift findings.

    observed=None is the deferred-live case: no comparison is possible, so NO
    findings are fabricated (the caller maps this to pending_live_reprofile).
    """
    if observed is None:
        return []

    findings: list[DriftFinding] = []
    base_cols = {c.name: c for c in baseline.columns}
    obs_cols = {c.name: c for c in observed.columns}

    for name in obs_cols.keys() - base_cols.keys():
        findings.append(
            DriftFinding(
                drift_class="column_added",
                column=name,
                before="absent",
                after="present",
                severity="warning",
                principle_v=False,
                note="not yet mapped; review for adoption",
            )
        )
    for name in base_cols.keys() - obs_cols.keys():
        findings.append(
            DriftFinding(
                drift_class="column_removed",
                column=name,
                before="present",
                after="absent",
                severity="blocked",
                principle_v=False,
                note="any mapping/silver reference is now broken",
            )
        )
    return findings
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift.py -q --no-cov`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/retail/drift.py tests/unit/test_drift.py
git commit -m "feat: drift classifier -- column added/removed (F014 runtime)"
```

---

## Task 2: missingness + cardinality shift, and grain/PK drift (Principle-V)

**Files:**
- Modify: `src/retail/drift.py`
- Test: `tests/unit/test_drift.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tests/unit/test_drift.py

def test_missingness_shift_reports_measured_before_after():
    from retail.drift import classify_drift
    base = _profile([_col("a", missing_pct=3.1)])
    obs = _profile([_col("a", missing_pct=11.7)])
    findings = classify_drift(base, obs)
    ms = [f for f in findings if f.drift_class == "missingness_shift"]
    assert len(ms) == 1
    assert ms[0].before == "3.10%"
    assert ms[0].after == "11.70%"
    assert ms[0].severity == "warning"


def test_cardinality_shift_reported():
    from retail.drift import classify_drift
    base = _profile([_col("a", card=5)])
    obs = _profile([_col("a", card=42)])
    findings = classify_drift(base, obs)
    cs = [f for f in findings if f.drift_class == "cardinality_shift"]
    assert len(cs) == 1
    assert cs[0].before == "5 distinct"
    assert cs[0].after == "42 distinct"


def test_no_shift_when_equal():
    from retail.drift import classify_drift
    base = _profile([_col("a", missing_pct=3.1, card=5)])
    obs = _profile([_col("a", missing_pct=3.1, card=5)])
    assert classify_drift(base, obs) == []


def test_grain_pk_drift_is_blocked_and_principle_v():
    from retail.drift import classify_drift
    base = _profile([_col("a")], is_unique=True, null_pk=0)
    obs = _profile([_col("a")], is_unique=False, null_pk=0)
    findings = classify_drift(base, obs)
    g = [f for f in findings if f.drift_class == "grain_pk_drift"]
    assert len(g) == 1
    assert g[0].severity == "blocked"
    assert g[0].principle_v is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift.py -q --no-cov`
Expected: FAIL — new assertions fail (no missingness/cardinality/grain logic yet).

- [ ] **Step 3: Write minimal implementation**

Insert these column-survivor and PK checks into `classify_drift`, immediately before `return findings`:

```python
    # Per-surviving-column shifts (columns present in BOTH).
    for name in base_cols.keys() & obs_cols.keys():
        b = base_cols[name]
        o = obs_cols[name]
        if b.missing_pct != o.missing_pct:
            findings.append(
                DriftFinding(
                    drift_class="missingness_shift",
                    column=name,
                    before=f"{b.missing_pct:.2f}%",
                    after=f"{o.missing_pct:.2f}%",
                    severity="warning",
                    principle_v=False,
                )
            )
        if b.distinct_cardinality != o.distinct_cardinality:
            findings.append(
                DriftFinding(
                    drift_class="cardinality_shift",
                    column=name,
                    before=f"{b.distinct_cardinality} distinct",
                    after=f"{o.distinct_cardinality} distinct",
                    severity="warning",
                    principle_v=False,
                )
            )

    # Grain / PK drift -- a Principle-V human seam. The candidate PK that was
    # unique on the baseline is no longer unique, or NULLs appeared in the PK.
    if baseline.pk.is_unique and (not observed.pk.is_unique or observed.pk.null_pk > 0):
        before = f"is_unique=true, null_pk={baseline.pk.null_pk}"
        after = f"is_unique={str(observed.pk.is_unique).lower()}, null_pk={observed.pk.null_pk}"
        findings.append(
            DriftFinding(
                drift_class="grain_pk_drift",
                column="(candidate PK)",
                before=before,
                after=after,
                severity="blocked",
                principle_v=True,
                note="grain is never auto-rejudged; raise for the analyst",
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift.py -q --no-cov`
Expected: PASS (all tests to date).

- [ ] **Step 5: Commit**

```bash
git add src/retail/drift.py tests/unit/test_drift.py
git commit -m "feat: drift classifier -- missingness/cardinality shift + grain-PK (Principle-V)"
```

---

## Task 3: derive_status + to_findings_dict (schema-shaped emit) + deferred-live

**Files:**
- Modify: `src/retail/drift.py`
- Test: `tests/unit/test_drift.py`

- [ ] **Step 1: Write the failing test** (schema-validating)

```python
# append to tests/unit/test_drift.py
import json
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "source-drift-findings.schema.json"


def _validate(doc):
    from jsonschema import Draft202012Validator
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(doc)


def test_derive_status_blocked_when_fatal_class_present():
    from retail.drift import classify_drift, derive_status
    base = _profile([_col("a"), _col("b")])
    obs = _profile([_col("a")])  # b removed -> blocked
    assert derive_status(classify_drift(base, obs), observed_available=True) == "blocked"


def test_derive_status_warning_when_only_nonfatal():
    from retail.drift import classify_drift, derive_status
    base = _profile([_col("a", missing_pct=1.0)])
    obs = _profile([_col("a", missing_pct=9.0)])  # missingness shift only
    assert derive_status(classify_drift(base, obs), observed_available=True) == "warning"


def test_derive_status_pass_when_no_findings():
    from retail.drift import classify_drift, derive_status
    base = _profile([_col("a")])
    obs = _profile([_col("a")])
    assert derive_status(classify_drift(base, obs), observed_available=True) == "pass"


def test_deferred_live_is_pending_and_schema_valid():
    from retail.drift import to_findings_dict
    base = _profile([_col("a")])
    doc = to_findings_dict(
        baseline=base, observed=None,
        baseline_ref="mappings/t/source-profile.md@abc",
        evidence=["mappings/t/source-drift-report.md"],
    )
    assert doc["status"] == "pending_live_reprofile"
    assert doc["observed"]["available"] is False
    assert doc["findings"] == []
    _validate(doc)


def test_full_report_schema_valid_with_findings_and_handoff():
    from retail.drift import to_findings_dict
    base = _profile([_col("a")], is_unique=True)
    obs = _profile([_col("a")], is_unique=False)  # grain_pk_drift -> handoff
    doc = to_findings_dict(
        baseline=base, observed=obs,
        baseline_ref="mappings/t/source-profile.md@abc",
        evidence=["mappings/t/source-drift-report.md"],
    )
    assert doc["status"] == "blocked"
    assert any(h["drift_class"] == "grain_pk_drift" for h in doc["principle_v_handoff"])
    assert doc["blocking_reasons"]  # non-empty
    _validate(doc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift.py -q --no-cov`
Expected: FAIL — `derive_status` / `to_findings_dict` not defined.

- [ ] **Step 3: Write minimal implementation** (append to `src/retail/drift.py`)

```python
_DEFAULT_OWNER = {
    "grain_pk_drift": "analyst",
    "returns_rule_drift": "analyst",
    "pii_surface_drift": "governance",
    "semantic_pair_drift": "analyst",
}

_HANDOFF_QUESTION = {
    "grain_pk_drift": "is the new grain acceptable, or is dedup a defect?",
    "returns_rule_drift": "which column is now authoritative for returns?",
    "pii_surface_drift": "is the reappeared/new column publish-safe? (default stays drop)",
    "semantic_pair_drift": "does the fanned-out pair still establish entity identity?",
}


def derive_status(findings: list[DriftFinding], *, observed_available: bool) -> str:
    """Map findings to one Source-Ready spine status. Never a numeric score."""
    if not observed_available:
        return "pending_live_reprofile"
    if any(f.severity == "blocked" for f in findings):
        return "blocked"
    if findings:
        return "warning"
    return "pass"


def _handoffs(findings: list[DriftFinding]) -> list[HandoffQuestion]:
    return [
        HandoffQuestion(
            question=_HANDOFF_QUESTION[f.drift_class],
            drift_class=f.drift_class,
            measured_fact=f"{f.column}: {f.before} -> {f.after}",
            owner=_DEFAULT_OWNER[f.drift_class],
        )
        for f in findings
        if f.principle_v
    ]


def to_findings_dict(
    *,
    baseline: ProfileResult,
    observed: ProfileResult | None,
    baseline_ref: str,
    evidence: list[str],
    reprofiled_at: str | None = None,
    reprofiled_by: str | None = None,
) -> dict:
    """Serialize a drift comparison to the source-drift-findings.schema.json shape."""
    findings = classify_drift(baseline, observed)
    available = observed is not None
    status = derive_status(findings, observed_available=available)
    blocking = [
        f"{f.drift_class} on {f.column}: {f.before} -> {f.after}"
        for f in findings
        if f.severity == "blocked"
    ]
    return {
        "table": baseline.table,
        "baseline": baseline_ref,
        "observed": {
            "available": available,
            "reprofiled_at": reprofiled_at,
            "reprofiled_by": reprofiled_by,
        },
        "findings": [
            {
                "drift_class": f.drift_class,
                "column": f.column,
                "before": f.before,
                "after": f.after,
                "severity": f.severity,
                "principle_v": f.principle_v,
                **({"note": f.note} if f.note is not None else {}),
            }
            for f in findings
        ],
        "status": status,
        "blocking_reasons": blocking,
        "evidence": list(evidence),
        "principle_v_handoff": [
            {
                "question": h.question,
                "drift_class": h.drift_class,
                "measured_fact": h.measured_fact,
                "owner": h.owner,
            }
            for h in _handoffs(findings)
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_drift.py -q --no-cov`
Expected: PASS (all). If jsonschema is missing: `python -m pip install jsonschema` (it is a dev dep; confirm it imports).

- [ ] **Step 5: Commit**

```bash
git add src/retail/drift.py tests/unit/test_drift.py
git commit -m "feat: drift status derivation + schema-shaped findings emit (fail-closed deferred-live)"
```

---

## Task 4: source-profile.md reader (template-conformant; honest-uncomparable)

**Files:**
- Create: `src/retail/source_profile_reader.py`
- Test: `tests/unit/test_source_profile_reader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_source_profile_reader.py
import pytest
from pathlib import Path

pytestmark = pytest.mark.unit

_ROOT = Path(__file__).resolve().parents[2]


def test_reads_template_conformant_profile():
    from retail.source_profile_reader import read_source_profile
    parsed = read_source_profile(_ROOT / "mappings" / "retail_store_sales" / "source-profile.md")
    assert parsed.uncomparable is None
    p = parsed.profile
    assert p.table == "retail_store_sales"
    names = {c.name for c in p.columns}
    assert "transaction_id" in names and "discount_applied" in names
    disc = next(c for c in p.columns if c.name == "discount_applied")
    assert disc.missing_pct == pytest.approx(33.39, abs=0.01)
    assert disc.distinct_cardinality == 3
    assert p.pk.is_unique is True
    assert p.pk.total == 12575


def test_nonconformant_profile_reported_uncomparable():
    from retail.source_profile_reader import read_source_profile
    parsed = read_source_profile(_ROOT / "mappings" / "demo_sample_orders" / "source-profile.md")
    assert parsed.uncomparable is not None
    assert "per-column" in parsed.uncomparable.lower() or "table" in parsed.uncomparable.lower()
    assert parsed.profile is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_source_profile_reader.py -q --no-cov`
Expected: FAIL — module not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# src/retail/source_profile_reader.py
"""Parse a template-conformant committed source-profile.md into a ProfileResult.

The baseline a drift run compares against is the committed source-profile.md that
earned Source Ready pass. This reader parses the template's structured sections
(Header 'Table id', Shape 'Row count', the 'Per-column profile' pipe table with
its measured missingness / distinct cardinality, and the 'Candidate grain &
candidate PK' uniqueness proof) back into a retail.profile.ProfileResult.

HONESTY BOUNDARY: the two filled baselines in the tree have DIFFERENT structures
(retail_store_sales follows the template; demo_sample_orders uses a freeform
3-column layout with no measured missingness/cardinality). A non-conformant
profile is reported as uncomparable -- NEVER guessed at -- matching the taxonomy's
'profile schema-version skew' edge case (compare only what both carry).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .profile import ColumnProfile, PkProof, ProfileResult


@dataclass(frozen=True)
class ParsedBaseline:
    profile: ProfileResult | None
    uncomparable: str | None  # a human reason when profile is None


def _find_table_id(text: str) -> str | None:
    m = re.search(r"\|\s*Table id\s*\|\s*`?([^`|]+?)`?\s*\|", text)
    return m.group(1).strip() if m else None


def _find_row_count(text: str) -> int | None:
    m = re.search(r"\|\s*Row count[^|]*\|\s*([\d,]+)\s*\|", text)
    return int(m.group(1).replace(",", "")) if m else None


# A per-column row: | `name` | TYPE | 1,213 / 9.65% | 201 | ... | ... |
_COL_ROW = re.compile(
    r"\|\s*`([^`]+)`\s*\|"          # column name
    r"\s*([^|]*?)\s*\|"             # type as landed
    r"\s*([\d,]+)\s*/\s*([\d.]+)%\s*\|"  # missing count / pct
    r"\s*([\d,]+)\s*\|"            # distinct cardinality
)


def _parse_columns(text: str) -> list[ColumnProfile]:
    cols: list[ColumnProfile] = []
    for m in _COL_ROW.finditer(text):
        cols.append(
            ColumnProfile(
                name=m.group(1).strip(),
                missing_count=int(m.group(3).replace(",", "")),
                missing_pct=float(m.group(4)),
                distinct_cardinality=int(m.group(5).replace(",", "")),
            )
        )
    return cols


def _parse_pk(text: str, row_count: int) -> PkProof:
    def _num(pattern: str) -> int | None:
        m = re.search(pattern, text)
        return int(m.group(1).replace(",", "")) if m else None

    total = _num(r"COUNT\(\*\)\s*=\s*([\d,]+)") or row_count
    distinct = _num(r"COUNT\(DISTINCT pk\)\s*=\s*([\d,]+)")
    null_pk = _num(r"NULLs/empty in PK\s*=\s*([\d,]+)")
    null_pk = 0 if null_pk is None else null_pk
    is_unique = distinct is not None and distinct == total and null_pk == 0
    return PkProof(
        total=total,
        distinct_pk=distinct if distinct is not None else total,
        null_pk=null_pk,
        is_unique=is_unique,
    )


def read_source_profile(path: str | Path) -> ParsedBaseline:
    text = Path(path).read_text(encoding="utf-8")
    table = _find_table_id(text)
    row_count = _find_row_count(text)
    columns = _parse_columns(text)

    if table is None or row_count is None or not columns:
        missing = []
        if table is None:
            missing.append("Header 'Table id'")
        if row_count is None:
            missing.append("Shape 'Row count'")
        if not columns:
            missing.append("a template 'Per-column profile' table with measured missingness/cardinality")
        return ParsedBaseline(
            profile=None,
            uncomparable=(
                "non-conformant source-profile.md: missing " + ", ".join(missing)
                + " -- cannot compare; re-profile against the template shape"
            ),
        )

    return ParsedBaseline(
        profile=ProfileResult(
            table=table,
            row_count=row_count,
            column_count=len(columns),
            columns=tuple(columns),
            pk=_parse_pk(text, row_count),
        ),
        uncomparable=None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_source_profile_reader.py -q --no-cov`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/retail/source_profile_reader.py tests/unit/test_source_profile_reader.py
git commit -m "feat: source-profile.md reader -- template-conformant baseline, honest-uncomparable"
```

---

## Task 5: `retail drift` CLI command (dispatch + parser, deferred-live fail-closed)

**Files:**
- Create: `src/retail/cli/commands/drift.py`
- Modify: `src/retail/cli/parser.py` (add `_add_drift_parser`, call in `_build_parser`)
- Modify: `src/retail/cli/__init__.py:124-145` (add dispatch row)
- Test: `tests/unit/test_cli_drift.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_cli_drift.py
import pytest

pytestmark = pytest.mark.unit

from retail.cli import main


def test_drift_without_dsn_is_deferred(capsys):
    rc = main(["drift", "--baseline", "mappings/retail_store_sales/source-profile.md"])
    err = capsys.readouterr().err
    assert rc == 1
    assert "PENDING LIVE RE-PROFILE" in err or "deferred" in err.lower()


def test_drift_nonconformant_baseline_reports_uncomparable(capsys):
    rc = main(["drift", "--baseline", "mappings/demo_sample_orders/source-profile.md"])
    out = capsys.readouterr()
    assert rc == 1
    assert "uncomparable" in (out.out + out.err).lower() or "non-conformant" in (out.out + out.err).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_cli_drift.py -q --no-cov`
Expected: FAIL — argparse rejects the unknown `drift` command (SystemExit → rc 2), or import error.

- [ ] **Step 3a: Add the parser** — in `src/retail/cli/parser.py`, add this function next to `_add_validate_parser`:

```python
def _add_drift_parser(sub: argparse._SubParsersAction) -> None:
    """`drift` (F014): compare a committed baseline source-profile.md against a
    live observed re-profile and emit source-drift-findings. Two-mode like
    `validate`: without --dsn (no observed re-profile) it reports the deferred
    [PENDING LIVE RE-PROFILE] state + warning, never a fabricated diff. The DB
    driver is imported LAZILY in run_drift, never here."""
    drift = sub.add_parser(
        "drift",
        help="compare a baseline source-profile.md vs a live re-profile (F014); "
        "needs --dsn + the 'db' extra for the live leg",
    )
    drift.add_argument(
        "--baseline",
        required=True,
        metavar="PATH",
        help="path to the committed source-profile.md that earned Source Ready pass",
    )
    drift.add_argument(
        "--dsn",
        default=None,
        metavar="postgresql://...",
        help="Postgres DSN for the live re-profile. Without it, drift reports the "
        "deferred [PENDING LIVE RE-PROFILE] state. NEVER commit a real DSN.",
    )
    drift.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="'text' (default) human summary; 'json' emits the "
        "source-drift-findings.schema.json document.",
    )
```

- [ ] **Step 3b: Register it** — in `_build_parser()` (`src/retail/cli/parser.py`), add after the `_add_validate_parser(sub)` line:

```python
    _add_drift_parser(sub)
```

- [ ] **Step 3c: Add the dispatch row** — in `src/retail/cli/__init__.py`, inside `_DISPATCH` (after the `"validate": ...` line):

```python
    "drift": _lazy(".commands.drift", "run_drift"),
```

- [ ] **Step 3d: Write the handler** — create `src/retail/cli/commands/drift.py`:

```python
"""`retail drift` handler (F014 source-drift detector runtime).

Two-mode, mirroring `validate`: without a --dsn (no observed re-profile) it
reports the deferred [PENDING LIVE RE-PROFILE] state and returns 1 -- it NEVER
fabricates a comparison (Principle VIII). A non-conformant baseline is reported
as uncomparable rather than guessed at. The live leg (build a QueryRunner, call
retail.profile.profile, diff) is wired through the cli seams so tests patch it
without touching a real DB.
"""

from __future__ import annotations

import argparse
import json
import sys


def run_drift(args: argparse.Namespace) -> int:
    from retail.source_profile_reader import read_source_profile

    parsed = read_source_profile(args.baseline)
    if parsed.uncomparable is not None:
        print(f"retail drift: {parsed.uncomparable}", file=sys.stderr)
        return 1

    if not args.dsn:
        # Deferred-live: emit a schema-valid pending document; never a fake diff.
        from retail.drift import to_findings_dict

        doc = to_findings_dict(
            baseline=parsed.profile,
            observed=None,
            baseline_ref=str(args.baseline),
            evidence=[str(args.baseline)],
        )
        if getattr(args, "output_format", "text") == "json":
            print(json.dumps(doc, indent=2))
        print(
            "retail drift: [PENDING LIVE RE-PROFILE] -- no --dsn given, so no "
            "observed re-profile was taken. status=pending_live_reprofile + "
            "warning; no comparison fabricated. Pass --dsn to run the live leg.",
            file=sys.stderr,
        )
        return 1

    # Live leg: build the read-only runner via the cli seam (patched in tests),
    # re-profile the SAME table + candidate PK, diff, emit.
    from retail import cli
    from retail.drift import to_findings_dict
    from retail.profile import profile as run_profile

    runner = cli._make_runner(args.dsn)
    candidate_pk = tuple(
        c.name for c in parsed.profile.columns if c.name and parsed.profile.pk.is_unique
    )[:1]  # single-column candidate PK from the baseline proof (best-effort)
    observed = run_profile(runner, parsed.profile.table, candidate_pk or (parsed.profile.columns[0].name,))
    doc = to_findings_dict(
        baseline=parsed.profile,
        observed=observed,
        baseline_ref=str(args.baseline),
        evidence=[str(args.baseline)],
        reprofiled_by="agent (retail.profile, read-only session)",
    )
    if getattr(args, "output_format", "text") == "json":
        print(json.dumps(doc, indent=2))
    else:
        print(f"retail drift: status={doc['status']}; {len(doc['findings'])} finding(s)")
        for r in doc["blocking_reasons"]:
            print(f"  blocking_reason: {r}")
    return 0 if doc["status"] in ("pass", "warning") else 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_cli_drift.py -q --no-cov`
Expected: PASS (2 passed). Note: run from the repo root so the relative `mappings/...` baseline paths resolve.

- [ ] **Step 5: Commit**

```bash
git add src/retail/cli/commands/drift.py src/retail/cli/parser.py src/retail/cli/__init__.py tests/unit/test_cli_drift.py
git commit -m "feat: retail drift CLI command -- two-mode, deferred-live fail-closed (F014)"
```

---

## Task 6: full verification + finish branch

**Files:** none (verification only)

- [ ] **Step 1: ruff format + lint**

Run: `ruff format --check src tests && ruff check src tests`
Expected: no diffs, no lint errors. If format differs: `ruff format src tests` then re-commit.

- [ ] **Step 2: full unit suite**

Run: `PYTHONPATH=src python -m pytest -m unit -q`
Expected: all pass except the 2 pre-existing `test_workspace_init.py` git-signing env failures (documented baseline). Confirm no NEW failures.

- [ ] **Step 3: retail check stays exit 0**

Run: `PYTHONPATH=src python -m retail check --repo .`
Expected: exit 0 (this adds a command + pure modules; no rule change).

- [ ] **Step 4: schema-conformance sanity**

Run: `PYTHONPATH=src python -c "from retail.drift import to_findings_dict; from retail.profile import ProfileResult, PkProof; import json; print('emit OK')"`
Expected: `emit OK`.

- [ ] **Step 5: finish the branch**

Use the `superpowers:finishing-a-development-branch` skill. PR title MUST carry a `feat:` prefix (squash-merge uses it as the commit subject; rule P2 fires on main otherwise). Suggested title: `feat: retail drift detector runtime (F014, spec 015 deferred runtime)`.

---

## Self-review notes

- **Spec coverage:** classifier (Tasks 1–3), status/emit + deferred-live fail-closed (Task 3), template-conformant reader + honest-uncomparable (Task 4), CLI two-mode (Task 5), retail-check/green-suite gate (Task 6). All design §2 in-scope items covered.
- **Type consistency:** `DriftFinding`/`HandoffQuestion`/`ParsedBaseline` field names match across tasks; `classify_drift`/`derive_status`/`to_findings_dict`/`read_source_profile`/`run_drift` signatures stable.
- **Known residual (flagged, not hidden):** the live-leg candidate-PK reconstruction in Task 5 is best-effort (the baseline markdown proves uniqueness on a PK whose exact column set is in prose, not a machine field). The unit tests exercise only the deferred + uncomparable paths (no live DB); the live leg is covered by the two filled baselines when a DSN is available (a `tests/live_db` follow-up, consistent with the repo's honest-skip live-test posture).
