# Cross-Star Conformed-Dimension Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the #418 remainder — a shared star-discovery module that lets `seshat dbt scaffold` validate a conformed dimension's declared owner, refuse silent attribute loss, and allow a fully-conformed (zero-owned-dim) reuser.

**Architecture:** Extract HR1's private star-discovery helpers into a dependency-free `seshat/dbt/stars.py` (pure core; I/O injected as a `load` callable, mirroring the repo's driver-free discipline). HR1 delegates to it (behavior-preserving). Scaffold uses it with a `git show HEAD:` loader to reconcile each reused dim against its owner star before dropping the dim's model, failing closed on a missing owner or a reuser-only attribute.

**Tech Stack:** Python 3.11+, pytest, ruff, PyYAML (lazy), git CLI (via subprocess).

## Global Constraints

- Python: type annotations on every signature; `from __future__ import annotations`.
- `seshat/dbt/stars.py` MUST be import-safe with NO database driver and MUST NOT import `psycopg2`; `yaml` imported LAZILY inside functions (mirrors HR1's "kept out of the retail check static-core chain").
- `seshat/dbt/stars.py` MUST NOT import from `seshat.rules.*` or `seshat.core` (no `RuleContext`) — it is a pure lower layer both rules and dbt consume.
- Fail-closed: every new scaffold refusal is a `model_plan.ScaffoldError` (code `DBT_SCAFFOLD_INVALID`) with an actionable message. I/O failures fail SAFE to "star not found" → the owner-existence refusal, never a traceback.
- Ruff clean at CI scope: `ruff check src tests scripts` AND `ruff format --check src tests scripts` (plus the dagster scope if touched — it is NOT touched here).
- Never fabricate provenance; never mutate another table's committed/generated model; never self-grant a merge.
- HR1's existing behavior MUST NOT change — its full existing test suite is the regression guard for the extraction.

---

### Task 1: Create the shared star-discovery module `seshat/dbt/stars.py`

Extracts HR1's discovery primitives into a pure, dependency-free module. I/O is
injected via a `load` callable so HR1 (worktree read) and scaffold (committed
read) each supply their own strategy — the module itself touches neither git nor
`RuleContext`.

**Files:**
- Create: `src/seshat/dbt/stars.py`
- Test: `tests/unit/dbt/test_stars.py`

**Interfaces:**
- Produces:
  - `bare_dim_name(name: object) -> str | None` — strip optional `<schema>.`, lowercased; None if not a usable string.
  - `star_id(document: dict, table_dir: str) -> str` — `meta.table_id` → `source_id` → `table_dir`.
  - `is_star(document: dict) -> bool` — has `gold_star.fact`.
  - `star_dimensions(document: dict) -> dict[str, dict]` — bare name → raw dim dict (explicit dims last-wins, `date_dimension` first-wins, degenerate excluded).
  - `discover_stars(tracked_files, load) -> dict[str, dict]` where `tracked_files: Iterable[str]`, `load: Callable[[str], dict | None]`; returns `{star_id: document}` for every non-test `mappings/<dir>/source-map.yaml` that `is_star`.

- [ ] **Step 1: Write the failing test**

```python
"""Shared star-discovery primitives (seshat/dbt/stars.py) -- pure, driver-free."""

from __future__ import annotations

import pytest

from seshat.dbt import stars

pytestmark = pytest.mark.unit


def test_bare_dim_name_strips_schema_and_lowercases() -> None:
    assert stars.bare_dim_name("gold.Dim_Customer") == "dim_customer"
    assert stars.bare_dim_name("dim_customer") == "dim_customer"
    assert stars.bare_dim_name("") is None
    assert stars.bare_dim_name(None) is None


def test_star_id_resolution_order() -> None:
    assert stars.star_id({"meta": {"table_id": "t"}}, "dir") == "t"
    assert stars.star_id({"source_id": "sid"}, "dir") == "sid"
    assert stars.star_id({"meta": {}}, "dir") == "dir"


def test_is_star_requires_gold_star_fact() -> None:
    assert stars.is_star({"gold_star": {"fact": {"name": "f"}}}) is True
    assert stars.is_star({"gold_star": {}}) is False
    assert stars.is_star({}) is False


def test_star_dimensions_collects_dims_and_date_excludes_degenerate() -> None:
    doc = {
        "gold_star": {
            "dimensions": [
                {"name": "gold.dim_customer", "surrogate_key": "customer_sk"},
                {"name": "gold.dim_product", "surrogate_key": "product_sk"},
            ],
            "date_dimension": {"name": "dim_date", "surrogate_key": "date_sk"},
            "degenerate_dimensions": ["transaction_id"],
        }
    }
    dims = stars.star_dimensions(doc)
    assert set(dims) == {"dim_customer", "dim_product", "dim_date"}
    assert "transaction_id" not in dims


def test_discover_stars_keys_on_governed_star_id_via_injected_load() -> None:
    docs = {
        "mappings/dir_a/source-map.yaml": {
            "meta": {"table_id": "sales"},
            "gold_star": {"fact": {"name": "fct_sales"}},
        },
        "mappings/dir_b/source-map.yaml": {
            "source_id": "returns",
            "gold_star": {"fact": {"name": "fct_returns"}},
        },
        "mappings/dir_c/source-map.yaml": {"gold_star": {}},  # not a star
    }
    tracked = list(docs) + ["docs/quality/conformed-dimension-map.yaml"]
    found = stars.discover_stars(tracked, docs.get)
    # keyed on GOVERNED id (meta.table_id / source_id), not the directory
    assert set(found) == {"sales", "returns"}


def test_discover_stars_skips_test_paths_and_load_failures() -> None:
    docs = {
        "mappings/real/source-map.yaml": {
            "meta": {"table_id": "real"},
            "gold_star": {"fact": {"name": "f"}},
        },
        "mappings/broken/source-map.yaml": None,  # load returned None
    }
    tracked = list(docs) + ["tests/fixtures/mappings/x/source-map.yaml"]
    found = stars.discover_stars(tracked, docs.get)
    assert set(found) == {"real"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_stars.py -p no:cacheprovider -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'seshat.dbt.stars'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Shared star-discovery primitives (issue #418).

Pure and dependency-free: NO database driver, NO ``seshat.rules`` /
``RuleContext`` import, and ``yaml`` is never needed here (callers parse YAML
themselves and inject a ``load`` callable). Both HR1 (worktree read via its
``RuleContext``) and ``seshat dbt scaffold`` (committed ``git show HEAD:`` read)
consume this, so the governance gate and the generator can never disagree on
what a star is, how a star id resolves, or which dimensions a star declares.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from seshat.core import is_test_path

_MAPPING_RE = re.compile(r"^mappings/([^/]+)/source-map\.yaml$")


def bare_dim_name(name: object) -> str | None:
    """Bare dimension name: strip an optional ``<schema>.`` prefix, lowercased."""
    if not isinstance(name, str) or not name.strip():
        return None
    return name.rsplit(".", 1)[-1].strip().lower()


def star_id(document: dict, table_dir: str) -> str:
    """The governed star id: ``meta.table_id`` -> ``source_id`` -> ``table_dir``."""
    meta = document.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("table_id"), str):
        return meta["table_id"]
    if isinstance(document.get("source_id"), str):
        return document["source_id"]
    return table_dir


def is_star(document: dict) -> bool:
    gs = document.get("gold_star")
    return isinstance(gs, dict) and gs.get("fact") is not None


def _add_dim(out: dict[str, dict], raw: object, *, overwrite: bool) -> None:
    if not isinstance(raw, dict):
        return
    b = bare_dim_name(raw.get("name"))
    if not b:
        return
    if overwrite:
        out[b] = raw
    else:
        out.setdefault(b, raw)


def star_dimensions(document: dict) -> dict[str, dict]:
    """bare-name -> raw dim dict (explicit dims + date_dimension; degenerate excluded)."""
    out: dict[str, dict] = {}
    gs = document.get("gold_star")
    if not isinstance(gs, dict):
        return out
    dims = gs.get("dimensions")
    if isinstance(dims, list):
        for dim in dims:
            _add_dim(out, dim, overwrite=True)
    _add_dim(out, gs.get("date_dimension"), overwrite=False)
    return out


def discover_stars(
    tracked_files: Iterable[str],
    load: Callable[[str], dict | None],
) -> dict[str, dict]:
    """``{star_id: document}`` for every non-test ``mappings/<dir>/source-map.yaml``
    that ``load`` returns and that ``is_star``. ``load`` (returning ``None`` on any
    parse/read failure) is the caller's I/O strategy -- worktree or committed."""
    found: dict[str, dict] = {}
    for rel in sorted(tracked_files):
        if is_test_path(rel):
            continue
        m = _MAPPING_RE.match(rel)
        if not m:
            continue
        data = load(rel)
        if data is None or not is_star(data):
            continue
        found[star_id(data, m.group(1))] = data
    return found
```

Note: `seshat.core.is_test_path` is stdlib-only (import-safe). Verify it exists
(HR1 already imports it): `grep -n "def is_test_path" src/seshat/core.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_stars.py -p no:cacheprovider -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Ruff + commit**

```bash
ruff check src/seshat/dbt/stars.py tests/unit/dbt/test_stars.py
ruff format src/seshat/dbt/stars.py tests/unit/dbt/test_stars.py
git add src/seshat/dbt/stars.py tests/unit/dbt/test_stars.py
git commit -m "feat: shared star-discovery module (seshat.dbt.stars) for #418"
```

---

### Task 2: HR1 delegates to `seshat.dbt.stars` (behavior-preserving)

Replace HR1's local `_bare` / `_star_id` / `_is_star` / `_add_dim` /
`_star_dimensions` / `_discover_stars` with the shared module. HR1's
`_discover_stars(ctx)` becomes a thin adapter that supplies a `RuleContext`-based
loader. Existing HR1 tests are the regression guard — they MUST stay green with
zero edits.

**Files:**
- Modify: `src/seshat/rules/conformed_dimension.py` (remove the 6 helpers; import from `seshat.dbt.stars`; adapt `_discover_stars`)
- Test: `tests/unit/test_conformed_dimension.py` (UNCHANGED — the regression guard)

**Interfaces:**
- Consumes (from Task 1): `stars.bare_dim_name`, `stars.star_id`, `stars.is_star`, `stars.star_dimensions`, `stars.discover_stars`.
- Produces: no new public surface; `_bare` alias retained internally for the call sites that still reference it (`_load_declarations`, divergence helpers) to minimize churn.

- [ ] **Step 1: Run the existing HR1 suite to establish the green baseline**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_conformed_dimension.py -p no:cacheprovider -q`
Expected: PASS (all existing HR1 tests). Record the count.

- [ ] **Step 2: Refactor — import shared module, delete local dupes, adapt discover**

In `src/seshat/rules/conformed_dimension.py`:

Add to imports (after `from ..registry import register`):
```python
from seshat.dbt import stars
```

Delete the local definitions of `_star_id`, `_is_star`, `_add_dim`,
`_star_dimensions` (lines ~78-124), and the body of `_discover_stars`.

Replace `_bare` with a thin alias (keep the name — many call sites use it):
```python
_bare = stars.bare_dim_name
```

Replace `_discover_stars` with an adapter that injects the `RuleContext` loader:
```python
def _discover_stars(ctx: RuleContext) -> dict[str, dict]:
    """star_id -> source-map dict for every committed mappings/<t>/source-map.yaml
    that is a star. Worktree read via the RuleContext loader; discovery logic lives
    in seshat.dbt.stars so scaffold and HR1 agree on star identity."""
    return stars.discover_stars(
        ctx.tracked_files, lambda rel: _load_yaml(ctx, rel)
    )
```

Update the two internal call sites that used `_star_dimensions(data)` to
`stars.star_dimensions(data)` (in `_index_dims_by_name`) and any `_star_id(...)`
references to `stars.star_id(...)`. Leave `_attr_silver_types`,
`_load_declarations`, and the divergence helpers untouched.

- [ ] **Step 3: Run the HR1 suite — must match the baseline exactly**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_conformed_dimension.py -p no:cacheprovider -q`
Expected: PASS, same count as Step 1 (behavior-preserving).

- [ ] **Step 4: Ruff + commit**

```bash
ruff check src/seshat/rules/conformed_dimension.py
ruff format src/seshat/rules/conformed_dimension.py
git add src/seshat/rules/conformed_dimension.py
git commit -m "refactor: HR1 delegates star discovery to seshat.dbt.stars (#418)"
```

---

### Task 3: Scaffold uses `stars.star_id`, retiring the `_governed_star_id` duplicate

Replace the hand-mirrored `_governed_star_id` in `model_plan.py` (added in #419)
with `stars.star_id`, closing the drift risk between scaffold and HR1.

**Files:**
- Modify: `src/seshat/dbt/scaffold/model_plan.py` (delete `_governed_star_id` ~lines 460-475; import + use `stars.star_id`)
- Test: `tests/unit/dbt/test_scaffold_conformed_reuse.py` (existing star-id-resolution tests are the regression guard)

**Interfaces:**
- Consumes: `stars.star_id`.
- Produces: no signature change to `build_scaffold_plan`.

- [ ] **Step 1: Run existing reuse tests (baseline)**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_scaffold_conformed_reuse.py -p no:cacheprovider -q`
Expected: PASS. Record count.

- [ ] **Step 2: Replace `_governed_star_id` with `stars.star_id`**

In `src/seshat/dbt/scaffold/model_plan.py`:

Add to imports:
```python
from seshat.dbt import stars
```

Delete the `_governed_star_id` function. In `build_scaffold_plan`, change:
```python
star_id = _governed_star_id(source.document, table_id)
```
to:
```python
star_id = stars.star_id(source.document, table_id)
```

- [ ] **Step 3: Run reuse tests — must match baseline**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_scaffold_conformed_reuse.py -p no:cacheprovider -q`
Expected: PASS, same count.

- [ ] **Step 4: Ruff + commit**

```bash
ruff check src/seshat/dbt/scaffold/model_plan.py
ruff format src/seshat/dbt/scaffold/model_plan.py
git add src/seshat/dbt/scaffold/model_plan.py
git commit -m "refactor: scaffold uses stars.star_id, retire _governed_star_id dup (#418)"
```

---

### Task 4: Orchestrator builds the committed owner-lookup and threads it into the plan

`_build_plan` discovers all governed stars from committed HEAD (via a
`git show HEAD:` loader + `git ls-files`) and passes an `owner_view` — the
`{star_id: star_dimensions(doc)}` map — into `build_scaffold_plan`, which stores
it on `MapSource`. Reconciliation logic itself is Task 5.

**Files:**
- Modify: `src/seshat/dbt/scaffold/orchestrator.py` (add `_committed_source_map` loader + `_discover_owner_view`; thread into `_build_plan`)
- Modify: `src/seshat/dbt/scaffold/model_plan.py` (`MapSource` gains `owner_view: dict[str, dict[str, dict]] | None = None`)
- Test: `tests/unit/dbt/test_scaffold_conformed_orchestration.py`

**Interfaces:**
- Consumes: `stars.discover_stars`, `stars.star_dimensions`.
- Produces: `MapSource.owner_view` (`{star_id: {bare_dim: raw_dim_dict}}`), consumed by Task 5.

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/dbt/test_scaffold_conformed_orchestration.py` (reuse its
`_git`/`_commit_map` helpers; commit two source-maps so discovery finds them):

```python
def test_discover_owner_view_reads_committed_stars(tmp_path: Path) -> None:
    """The owner-view is discovered from COMMITTED source-maps, keyed on governed
    star id, exposing each star's dimensions (#418)."""
    _git(tmp_path, "init", "-q")
    owner_dir = tmp_path / "mappings" / "sales"
    owner_dir.mkdir(parents=True)
    (owner_dir / "source-map.yaml").write_text(
        "meta:\n  table_id: sales\n"
        "gold_star:\n  fact:\n    name: fct_sales\n"
        "  dimensions:\n    - name: gold.dim_customer\n"
        "      surrogate_key: customer_sk\n"
        "      attributes: [customer_id, customer_segment]\n",
        encoding="utf-8",
    )
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed")

    view = orchestrator._discover_owner_view(tmp_path)
    assert "sales" in view
    assert "dim_customer" in view["sales"]
    assert view["sales"]["dim_customer"]["attributes"] == [
        "customer_id",
        "customer_segment",
    ]


def test_discover_owner_view_empty_without_git(tmp_path: Path) -> None:
    """No git repo -> empty owner-view (fail-safe), never a traceback (#418)."""
    assert orchestrator._discover_owner_view(tmp_path) == {}
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_scaffold_conformed_orchestration.py -k owner_view -p no:cacheprovider -q`
Expected: FAIL — `AttributeError: module ... has no attribute '_discover_owner_view'`

- [ ] **Step 3: Implement the loader + owner-view in orchestrator.py**

Add to `src/seshat/dbt/scaffold/orchestrator.py`:

```python
from seshat.dbt import stars


def _git_tracked_files(root: Path) -> list[str]:
    """`git ls-files` (posix rel paths) or [] on any failure (fail-safe)."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=False
        )
    except (OSError, ValueError):
        return []
    return result.stdout.splitlines() if result.returncode == 0 else []


def _committed_source_map(root: Path):
    """A `load(rel) -> dict | None` that reads rel from committed HEAD, so the
    owner-view reflects committed governance state, never an uncommitted edit."""
    import subprocess

    def _load(rel: str) -> dict | None:
        try:
            result = subprocess.run(
                ["git", "show", f"HEAD:{rel}"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        except (OSError, ValueError):
            return None
        if result.returncode != 0:
            return None
        try:
            data = yaml.safe_load(result.stdout)
        except yaml.YAMLError:
            return None
        return data if isinstance(data, dict) else None

    return _load


def _discover_owner_view(root: Path) -> dict[str, dict[str, dict]]:
    """`{star_id: {bare_dim: raw_dim_dict}}` across all committed governed stars --
    the cross-table view reconciliation needs (#418). Fail-safe to {} (no git /
    no stars): reconciliation then treats every owner as absent (fails closed)."""
    discovered = stars.discover_stars(
        _git_tracked_files(root), _committed_source_map(root)
    )
    return {sid: stars.star_dimensions(doc) for sid, doc in discovered.items()}
```

In `_build_plan`, pass the view into `MapSource`:
```python
    source = model_plan.MapSource(
        document=_load_map_document(working_set.source_map),
        source_map=working_set.source_map.relative_to(root).as_posix(),
        source_map_revision=working_set.source_map_revision,
        conformed_map=_load_conformed_map(root),
        owner_view=_discover_owner_view(root),
    )
```

In `src/seshat/dbt/scaffold/model_plan.py`, add to `MapSource` (after `conformed_map`):
```python
    # {star_id: {bare_dim: raw_dim_dict}} for every committed governed star, so
    # reuse can validate a reused dim against its OWNER (#418). None -> no owner
    # view (reconciliation treats every owner as absent -> fails closed).
    owner_view: dict[str, dict[str, dict]] | None = None
```

- [ ] **Step 4: Run to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_scaffold_conformed_orchestration.py -k owner_view -p no:cacheprovider -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Ruff + commit**

```bash
ruff check src/seshat/dbt/scaffold/orchestrator.py src/seshat/dbt/scaffold/model_plan.py tests/unit/dbt/test_scaffold_conformed_orchestration.py
ruff format src/seshat/dbt/scaffold/orchestrator.py src/seshat/dbt/scaffold/model_plan.py tests/unit/dbt/test_scaffold_conformed_orchestration.py
git add -A
git commit -m "feat: scaffold discovers committed owner-view for reconciliation (#418)"
```

---

### Task 5: Owner-existence + attribute-divergence refusal; allow zero-owned-dim plan

The core reconciliation. In `_partition_dimensions`, before a dim is reused,
validate it against the owner-view: refuse (fail closed) if the owner star is
absent, does not declare the dim, or the reuser declares an attribute the owner
lacks. Then remove the "at least one owned dimension is required" refusal so a
fully-conformed reuser builds a zero-owned-dim plan.

**Files:**
- Modify: `src/seshat/dbt/scaffold/model_plan.py` (`_partition_dimensions`, new `_reconcile_reused`; pass `owner_view` + `reuse` owners through)
- Test: `tests/unit/dbt/test_scaffold_conformed_reuse.py`

**Interfaces:**
- Consumes: `MapSource.owner_view` (Task 4), `stars.bare_dim_name`, the existing `_conformed_reuse` (bare dim → owner star id), `ScaffoldError`.
- Produces: no signature change to `build_scaffold_plan`; `_partition_dimensions(inputs, conformed_map, star_id, owner_view)`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/dbt/test_scaffold_conformed_reuse.py`. These use an
`owner_view` passed via `MapSource`; add an `_owner_view` helper mirroring the
owner's dims:

```python
def _owner_view(*, attributes: list[str]) -> dict[str, dict[str, dict]]:
    """An owner-view where OWNER_TABLE owns dim_customer_rss with `attributes`."""
    return {
        _OWNER_TABLE: {
            "dim_customer_rss": {
                "name": "gold.dim_customer_rss",
                "surrogate_key": "customer_sk",
                "attributes": attributes,
            }
        }
    }


def _source_full(document, conformed_map, owner_view):
    return model_plan.MapSource(
        document=document,
        source_map=SOURCE_MAP,
        source_map_revision=REVISION,
        conformed_map=conformed_map,
        owner_view=owner_view,
    )


def test_reuse_ok_when_owner_declares_a_superset_of_attributes() -> None:
    """The reuser uses the shared canonical dim; owner having MORE attributes is
    fine -- reuse proceeds (#418)."""
    plan = model_plan.build_scaffold_plan(
        _source_full(
            _doc_for(_REUSER_TABLE),
            _conformed_map(),
            _owner_view(attributes=["customer_id", "customer_segment"]),
        ),
        _REUSER_TABLE,
        _FACT,
    )
    assert plan.reused_dimensions == ("dim_customer_rss",)


def test_reuse_refused_when_owner_star_is_absent() -> None:
    """Owner star id resolves to NO committed star -> fail closed, not a dangling
    ref() at dbt parse (#418)."""
    with pytest.raises(model_plan.ScaffoldError, match="dim_customer_rss") as err:
        model_plan.build_scaffold_plan(
            _source_full(_doc_for(_REUSER_TABLE), _conformed_map(), {}),
            _REUSER_TABLE,
            _FACT,
        )
    assert _OWNER_TABLE in str(err.value)


def test_reuse_refused_when_owner_does_not_declare_the_dim() -> None:
    """Owner star exists but declares no dim of this name -> fail closed (#418)."""
    view = {_OWNER_TABLE: {"dim_other": {"name": "gold.dim_other"}}}
    with pytest.raises(model_plan.ScaffoldError, match="dim_customer_rss"):
        model_plan.build_scaffold_plan(
            _source_full(_doc_for(_REUSER_TABLE), _conformed_map(), view),
            _REUSER_TABLE,
            _FACT,
        )


def test_reuse_refused_when_reuser_declares_an_attribute_owner_lacks() -> None:
    """The reuser's dim_customer_rss declares customer_id, but the owner's dim has
    only `customer_ref` -> the reuser attribute would be silently lost -> fail
    closed naming the attribute + both stars (#418)."""
    with pytest.raises(model_plan.ScaffoldError, match="customer_id") as err:
        model_plan.build_scaffold_plan(
            _source_full(
                _doc_for(_REUSER_TABLE),
                _conformed_map(),
                _owner_view(attributes=["customer_ref"]),
            ),
            _REUSER_TABLE,
            _FACT,
        )
    assert _OWNER_TABLE in str(err.value) and _REUSER_TABLE in str(err.value)


def test_all_dims_reused_builds_a_zero_owned_dim_plan() -> None:
    """A fully-conformed reuser (every dim owned elsewhere, all validated) builds:
    NO dim models, but a real fact + staging + audit; parity has zero
    dimension_member_count rows and validates exactly (#418)."""
    from seshat.dbt.contracts import ParityAssertion
    from seshat.dbt.evidence import _validate_parity_set

    # a map whose ONLY dim is the conformed dim_customer_rss (drop the date dim)
    single = {
        **_MAP,
        "meta": {**_MAP["meta"], "table_id": _REUSER_TABLE},
        "gold_star": {
            k: v for k, v in _MAP["gold_star"].items() if k != "date_dimension"
        },
    }
    plan = model_plan.build_scaffold_plan(
        _source_full(
            single,
            _conformed_map(),
            _owner_view(attributes=["customer_id"]),
        ),
        _REUSER_TABLE,
        _FACT,
    )
    assert plan.dimensions == ()  # zero owned dim models
    assert plan.reused_dimensions == ("dim_customer_rss",)
    assert plan.fact_model is not None and plan.staging is not None
    # the fact still carries the reused dim FK
    assert any(c.name == "customer_sk" for c in plan.fact_model.columns)
    # parity has NO dimension_member_count rows and validates exactly
    assert _member_count_subjects(plan) == set()
    assertions = tuple(
        ParityAssertion(
            assertion_id=r.assertion_id,
            assertion_class=r.assertion_class,
            subject=r.subject,
            expected="1",
            actual="1",
            delta="0",
            tolerance=r.tolerance,
            passed=True,
        )
        for r in plan.parity
    )
    unique_ids = tuple(sorted(f"model.seshat_bi.{m.name}" for m in _all_models(plan)))
    _validate_parity_set(assertions, unique_ids, plan.fact)  # must not raise
```

- [ ] **Step 2: Run to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_scaffold_conformed_reuse.py -k "owner or all_dims_reused or superset" -p no:cacheprovider -q`
Expected: FAIL (the reconciliation + zero-owned behavior does not exist yet; e.g. `test_all_dims_reused` raises the current "at least one owned dimension" `ScaffoldError`, and the refusal tests do not raise because owner-view is unused).

- [ ] **Step 3: Implement reconciliation + drop the zero-owned refusal**

In `src/seshat/dbt/scaffold/model_plan.py`, add the reconciler:

```python
def _reconcile_reused(
    reused: tuple[ModelSpec, ...],
    owners: dict[str, str],
    declared_raw: dict[str, dict],
    owner_view: dict[str, dict[str, dict]] | None,
) -> None:
    """Validate each REUSED dim against its owner before its model is dropped
    (#418). Fail closed (ScaffoldError) if the owner star is absent from the
    committed view, does not declare the dim, or lacks an attribute the reuser
    declares (a silently-lost governed field). ``declared_raw`` maps this star's
    bare dim name -> its raw dim dict (for the reuser's declared attributes)."""
    view = owner_view or {}
    for dim in reused:
        bare = _bare_dim_name(dim.name)
        owner = owners[bare]
        owner_dims = view.get(owner)
        if owner_dims is None or bare not in owner_dims:
            raise ScaffoldError(
                f"conformed dimension {bare!r} names owner star {owner!r}, but no "
                f"committed governed star with that id materializes it. Fix the "
                f"stars[] owner in the conformed-dimension map, or ensure the owner "
                f"star's source-map declares {bare!r}."
            )
        reuser_attrs = _dim_attributes(declared_raw.get(bare))
        owner_attrs = _dim_attributes(owner_dims[bare])
        missing = [a for a in reuser_attrs if a not in owner_attrs]
        if missing:
            raise ScaffoldError(
                f"reuser {declared_raw.get('__star_id__', '?')!r} declares "
                f"attribute(s) {', '.join(missing)} on conformed dimension {bare!r} "
                f"that its owner star {owner!r} does not carry -- reuse would "
                f"silently drop them. Add the attribute(s) to the owner star's "
                f"{bare!r}, or declare the dimension 'distinct' in the map."
            )


def _dim_attributes(raw: dict | None) -> tuple[str, ...]:
    if not isinstance(raw, dict):
        return ()
    attrs = raw.get("attributes")
    return tuple(a for a in attrs if isinstance(a, str)) if isinstance(attrs, list) else ()
```

Rework `_partition_dimensions` to take `owner_view`, build the reuser's raw-dim
map, reconcile, and DROP the zero-owned refusal:

```python
def _partition_dimensions(
    inputs: _PlanInputs,
    conformed_map: dict | None,
    star_id: str,
    owner_view: dict[str, dict[str, dict]] | None,
) -> _PartitionedDimensions:
    declared = _dimensions(inputs)
    reuse = _conformed_reuse(conformed_map, star_id)
    owned = tuple(dim for dim in declared if _bare_dim_name(dim.name) not in reuse)
    reused = tuple(dim for dim in declared if _bare_dim_name(dim.name) in reuse)
    # reuser's raw dims (bare -> raw dict) from its OWN gold_star, for attribute
    # comparison; tag the star id so the refusal message can name the reuser.
    reuser_raw = stars.star_dimensions({"gold_star": inputs.gold_star})
    reuser_raw["__star_id__"] = star_id  # sentinel for the message (not a dim)
    _reconcile_reused(reused, reuse, reuser_raw, owner_view)
    return _PartitionedDimensions(
        declared=declared, owned=owned, reused=reused, owners=reuse
    )
```

Remove the `if not owned: raise ScaffoldError("every declared dimension ...")`
block entirely (a zero-owned plan is now valid once every reused dim is
reconciled). In `build_scaffold_plan`, pass the view:
```python
    dims = _partition_dimensions(inputs, source.conformed_map, star_id, source.owner_view)
```

Note on `reuser_raw` sentinel: the `"__star_id__"` key is a string→str entry, not
a dim dict; `_reconcile_reused` reads it only via `.get('__star_id__', '?')` and
never iterates it as a dimension (it iterates `reused`, whose names come from
real dims). If a linter/readability review objects, thread `star_id` as an
explicit param to `_reconcile_reused` instead — functionally identical.

- [ ] **Step 4: Run the new tests + the full reuse suite**

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_scaffold_conformed_reuse.py -p no:cacheprovider -q`
Expected: PASS (all — new refusal/zero-owned tests + #419 regression tests).

Then confirm the #419 owner/reuser tests still pass — they pass `conformed_map`
directly but NO `owner_view`, so a reused dim now hits reconciliation with an
empty view and would REFUSE. **This is expected breakage to fix in Step 5:** those
older tests must supply an `owner_view` for their reuser cases.

- [ ] **Step 5: Update the #419 reuse tests to supply an owner-view**

Every existing test in `test_scaffold_conformed_reuse.py` that builds a REUSER
plan with `_conformed_map()` must now pass an `owner_view` where the owner
declares the reused dim with compatible attributes (`customer_id`). Update
`_source_with_map` reuser call sites to `_source_full(..., _owner_view(attributes=["customer_id"]))`, or give `_source_with_map` a default owner-view. Re-run:

Run: `PYTHONPATH=src python -m pytest tests/unit/dbt/test_scaffold_conformed_reuse.py -p no:cacheprovider -q`
Expected: PASS (all).

- [ ] **Step 6: Update `build_scaffold_plan` callers + docstrings; ruff; commit**

Correct the `_partition_dimensions` docstring NOTE (it currently says owner
validation is a #418 follow-up — it is now DONE) and the design-spec-referenced
limitation notes in the module. Also update the #419 spec's "Known limitation"
sections to point at this reconciliation (or note them resolved).

```bash
ruff check src/seshat/dbt/scaffold/model_plan.py tests/unit/dbt/test_scaffold_conformed_reuse.py
ruff format src/seshat/dbt/scaffold/model_plan.py tests/unit/dbt/test_scaffold_conformed_reuse.py
git add -A
git commit -m "feat: owner-existence + attribute-divergence refusal; allow zero-owned-dim plan (#418)"
```

---

### Task 6: Full pre-PR gates + combined PR

**Files:** none (verification + PR).

- [ ] **Step 1: Ruff (both scopes)**

```bash
ruff check src tests scripts && ruff format --check src tests scripts
# dagster scope only if touched (it is NOT in this plan) -- skip otherwise
```
Expected: all pass.

- [ ] **Step 2: seshat check**

Run: `PYTHONPATH=src python -m seshat.cli check; echo "EXIT=$?"`
Expected: EXIT=0

- [ ] **Step 3: Full main-package suite (note the 2 pre-existing local-only failures)**

Run: `PYTHONPATH=src python -m pytest -p no:cacheprovider -q --deselect tests/integration/test_python_release_artifacts.py::test_real_wheel_sdist_and_isolated_rebuild --deselect tests/integration/test_python_release_artifacts.py::test_normalized_wheel_parity_rejects_governed_content_change --deselect tests/unit/test_cli_identity_version.py::test_version_resolver_matches_pyproject_when_installed`
Expected: all pass (the 3 deselected are pre-existing local-only failures confirmed on clean main — CI installs the package and passes them).

- [ ] **Step 4: CodeScene DELTA pre-flight**

Commit all work, then run the `analyze_change_set` MCP tool (base_ref `main`).
Expected: `quality_gates: passed`. If a complexity/LOC finding appears, address it
WITHOUT an extraction cascade (see the codescene-delta-gate-quirks memory).

- [ ] **Step 5: Adversarial review gate**

Write the `main...HEAD` diff to the scratchpad and dispatch a fable-model
high/xhigh adversarial external reviewer (close the class, not the instance),
focused on: never-fabricate provenance, the refuse-vs-silent-loss posture,
owner-view fail-safe (empty view → refuse, never pass), the `__star_id__`
sentinel not leaking into dim iteration, and zero-owned parity exactness. Fix
confirmed findings TDD-first before opening the PR.

- [ ] **Step 6: Open the combined PR**

```bash
git push -u origin feat/418-conformed-reconciliation
gh pr create --base main --title "feat: cross-star conformed-dimension reconciliation (#418 remainder)" --body "<summary: shared stars.py; HR1 delegation; owner-existence + attribute-divergence refusal; zero-owned-dim plan. Closes #418. Test plan + gates.>"
```
Then work the codex bot / conversation-resolution loop to convergence
(resolve-with-reasoning; the ruleset requires conversation-resolution).

---

## Self-Review

**Spec coverage:** shared module (Task 1) ✓; HR1 delegation (Task 2) ✓; retire
`_governed_star_id` (Task 3) ✓; owner-view load committed (Task 4) ✓;
owner-existence + attribute REFUSE + zero-owned (Task 5) ✓; gates + PR (Task 6) ✓.
The spec's `discover_stars(root, *, committed)` interface is refined to the
cleaner injected-`load` seam (Task 1) — the committed-vs-worktree choice lives in
each caller's loader (orchestrator's `git show HEAD` vs HR1's `RuleContext`),
keeping `stars.py` dependency-free. All spec sections covered.

**Placeholder scan:** every code step shows complete code; no TBD/TODO; the PR
body is the one bracketed summary (expected — filled at Task 6 from the diff).

**Type consistency:** `star_id`/`star_dimensions`/`discover_stars`/`bare_dim_name`
names match across Tasks 1→2→3→4→5. `owner_view: dict[str, dict[str, dict]]`
consistent (MapSource field, orchestrator producer, `_partition_dimensions` param,
`_reconcile_reused` consumer). `ScaffoldError` is the existing type.
