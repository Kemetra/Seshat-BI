# PBIR Geometry Writer (Increment D) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `retail pbir-set-geometry` — a writer that sets an existing visual's `position` rectangle (x/y/width/height/z/tabOrder), preserving its data binding (FR-003) and refusing off-canvas rectangles read from the real `page.json` canvas.

**Architecture:** A new `src/seshat/pbir_geometry.py` mirrors `pbir_visual_format.py` (allow-list, binding snapshot-preserve, round-trip check, clean `PbirGeometryError`, `_main`). It adds an on-canvas guard that reads the REAL `page.json` `width`/`height` (never hardcoded). A dedicated generic fixture with a non-default 1600×900 canvas enforces the read-real-dims invariant.

**Tech Stack:** Python 3.13, stdlib only (`json`, `pathlib`, `sys`). pytest (`@pytest.mark.unit`).

## Global Constraints

- Writes ONLY a visual's `position` rectangle keys: `x`, `y`, `width`, `height`, `z`, `tabOrder`. Any other key is refused.
- NEVER touches `visualType`, `query`, bindings, or creates/deletes visuals/pages (ADR 0016 exclusions; FR-003).
- Off-canvas guard MUST read real `page.json` `width`/`height`; NEVER hardcode a canvas size. Missing/non-numeric `page.json` dims → clean error, no fallback.
- Overlap between visuals is ALLOWED (not checked); only off-canvas/negative/non-numeric rectangles are rejected (ratified ADR 0016 Q3).
- Every failure raises `PbirGeometryError` (clean, no traceback). No score/confidence. No self-granted pass.
- NO `--force` / overwrite gate. Position keys ALWAYS pre-exist on a visual, so moving a visual necessarily changes them — a "refuse if the value already differs" gate (the increment-B analogy) would fire on every real move and make the verb unusable. The overwrite safety net is the reviewable git diff + human ratification, not a per-call flag. `set_geometry(visual_json, position)` takes no `force`; there is no `--force` CLI arg. (Idempotent re-set writes identical bytes and needs no gate.)
- All values written must be numbers (int/float). Staged JSON must be round-trip stable. Write utf-8, `newline="\n"`; read utf-8-sig.
- Target must live under a `*.Report/` tree (traversal guard, same as increment B).
- Fixture is GENERIC (Principle VII): placeholder page/visual names, generic dims; SHAPE copied from c086, never its literals.
- Commit messages `<type>: <description>`. Never `--no-verify`. Branch `feat/pbir-geometry-increment-d` (already checked out).

---

## File Structure

- **Create `tests/fixtures/pbir/geometry.Report/`** — a minimal generic PBIR report: one `page.json` (canvas 1600×900) + two `visual.json` files with `position` blocks. The test substrate.
- **Create `src/seshat/pbir_geometry.py`** — the writer + on-canvas guard + `pbir_geometry_main`. ~140 lines.
- **Modify `src/seshat/cli.py`** — add the `pbir-set-geometry` subparser (after the `pbir-set-page-background` parser block) + its dispatch branch (after that verb's dispatch).
- **Create `tests/unit/test_pbir_geometry.py`** — module tests (valid write, FR-003, allow-list, off-canvas incl. the non-default-canvas decoy, overlap-allowed, missing page.json, repeated-move-no-force-gate).
- **Create `tests/unit/test_pbir_geometry_cli.py`** — CLI exit 0/2.

---

### Task 1: The generic geometry fixture

**Files:**
- Create: `tests/fixtures/pbir/geometry.Report/definition/pages/pg/page.json`
- Create: `tests/fixtures/pbir/geometry.Report/definition/pages/pg/visuals/vA/visual.json`
- Create: `tests/fixtures/pbir/geometry.Report/definition/pages/pg/visuals/vB/visual.json`

**Interfaces:**
- Produces: a fixture tree later tasks read. Canvas is 1600×900 (non-default). `vA` at a safe rectangle; `vB` overlapping `vA` (to prove overlap is allowed).

- [ ] **Step 1: Create the page.json (canvas 1600×900)**

`tests/fixtures/pbir/geometry.Report/definition/pages/pg/page.json`:
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json",
  "name": "pg",
  "displayName": "Placeholder Page",
  "displayOption": "FitToPage",
  "height": 900,
  "width": 1600
}
```

- [ ] **Step 2: Create vA/visual.json (safe rectangle, bound)**

`tests/fixtures/pbir/geometry.Report/definition/pages/pg/visuals/vA/visual.json`:
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.0.0/schema.json",
  "name": "vA",
  "position": { "x": 100, "y": 100, "z": 1000, "height": 300, "width": 300, "tabOrder": 1000 },
  "visual": {
    "visualType": "columnChart",
    "query": { "queryState": { "Category": { "projections": [ { "field": { "Column": { "Expression": { "SourceRef": { "Entity": "placeholder" } }, "Property": "cat" } }, "queryRef": "placeholder.cat" } ] } } }
  }
}
```

- [ ] **Step 3: Create vB/visual.json (overlaps vA — proves overlap is allowed)**

`tests/fixtures/pbir/geometry.Report/definition/pages/pg/visuals/vB/visual.json`:
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.0.0/schema.json",
  "name": "vB",
  "position": { "x": 300, "y": 250, "z": 2000, "height": 300, "width": 300, "tabOrder": 2000 },
  "visual": {
    "visualType": "card",
    "query": { "queryState": { "Values": { "projections": [ { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "placeholder" } }, "Property": "total" } }, "queryRef": "placeholder.total" } ] } } }
  }
}
```

- [ ] **Step 4: Verify the fixture parses as valid JSON**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && python -c "import json,glob; [json.load(open(f,encoding='utf-8-sig')) for f in glob.glob('tests/fixtures/pbir/geometry.Report/**/*.json', recursive=True)]; print('all fixture JSON valid')"`
Expected: `all fixture JSON valid`

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/pbir/geometry.Report
git commit -m "test: generic geometry fixture (1600x900 canvas, two positioned visuals)"
```

---

### Task 2: The geometry writer + on-canvas guard

**Files:**
- Create: `src/seshat/pbir_geometry.py`
- Test: `tests/unit/test_pbir_geometry.py`

**Interfaces:**
- Produces:
  - `class PbirGeometryError(Exception)`
  - `set_geometry(visual_json: Path, position: dict) -> Path` — sets the allow-listed position keys, preserving binding, validating on-canvas against the sibling page.json; returns the written path. NO force param (see Global Constraints).
  - `pbir_geometry_main(args) -> int` (added in Task 3).

- [ ] **Step 1: Write the failing test for a valid write + binding preservation**

```python
# tests/unit/test_pbir_geometry.py
"""Unit tests for the PBIR geometry writer (increment D)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from retail.pbir_geometry import PbirGeometryError, set_geometry

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).parent.parent / "fixtures" / "pbir" / "geometry.Report"


def _report(tmp_path: Path) -> Path:
    dst = tmp_path / "geometry.Report"
    shutil.copytree(FIXTURE, dst)
    return dst


def _visual(report: Path, v: str) -> Path:
    return report / "definition" / "pages" / "pg" / "visuals" / v / "visual.json"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8-sig"))


def test_valid_move_writes_position_and_preserves_binding(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    before = _load(vp)["visual"]
    out = set_geometry(vp, {"x": 200, "y": 150, "width": 400, "height": 250})
    assert out == vp
    after = _load(vp)
    assert after["position"]["x"] == 200
    assert after["position"]["width"] == 400
    # untouched position keys preserved
    assert after["position"]["z"] == 1000
    assert after["position"]["tabOrder"] == 1000
    # binding byte-identical (FR-003)
    assert after["visual"] == before
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_pbir_geometry.py::test_valid_move_writes_position_and_preserves_binding -q`
Expected: FAIL — `No module named 'retail.pbir_geometry'`.

- [ ] **Step 3: Write the module**

```python
# src/seshat/pbir_geometry.py
"""PBIR visual geometry writer (adapter increment D).

Sets an existing, binding-mapped visual's ``position`` rectangle -- ``x``, ``y``,
``width``, ``height``, ``z``, ``tabOrder`` -- the layout a human drags/resizes in
the Power BI canvas. Authorized by ADR 0016 (ratified).

THE FR-003 GUARANTEE (unchanged): the writer NEVER touches the visual's data
binding. It asserts ``visual.query`` and ``visual.visualType`` are byte-identical
before and after, and refuses to write if either would change. Geometry is added
BESIDE the binding guard, never through it. It NEVER changes visualType, creates or
deletes a visual, or moves an unbound visual (ADR 0016 exclusions).

THE ON-CANVAS GUARD: the result rectangle must fit the page's REAL canvas, read from
the sibling ``page.json`` (top-level ``width``/``height``) -- never a hardcoded size.
Off-canvas / negative / non-numeric rectangles are refused (objective validity);
overlap between visuals is ALLOWED (a design judgment the lint must not make).

Companion authoring adapter (ADR 0015/0016): committed PBIR JSON, deterministic,
validated, all-or-nothing. No pbi-cli, no live Power BI, no network -- stdlib only.
Grants no readiness pass, emits no score.
"""

from __future__ import annotations

import json
from pathlib import Path

# The only position keys this increment may write (ADR 0016). Anything else refused.
_ALLOWED_KEYS = frozenset({"x", "y", "width", "height", "z", "tabOrder"})


class PbirGeometryError(Exception):
    """A geometry input/output problem surfaced cleanly (never a traceback)."""


def _dump(doc: object) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def _load_json(p: Path, what: str) -> dict:
    try:
        with p.open(encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise PbirGeometryError(
            f"{what} is not valid JSON ({exc.__class__.__name__}): {p}"
        ) from exc
    if not isinstance(doc, dict):
        raise PbirGeometryError(f"{what} is not a JSON object: {p}")
    return doc


def _canvas_dims(visual_json: Path) -> tuple[float, float]:
    """Read the REAL canvas width/height from the sibling page.json.

    Path: .../pages/<page>/visuals/<v>/visual.json -> .../pages/<page>/page.json,
    i.e. visual_json.parents[2] / 'page.json'. NEVER hardcode a fallback size.
    """
    page_json = visual_json.parents[2] / "page.json"
    if not page_json.is_file():
        raise PbirGeometryError(
            f"page.json not found next to the visual ({page_json}); cannot validate "
            f"on-canvas without the real canvas dimensions"
        )
    page = _load_json(page_json, "page.json")
    w, h = page.get("width"), page.get("height")
    if not isinstance(w, (int, float)) or isinstance(w, bool) or not isinstance(
        h, (int, float)
    ) or isinstance(h, bool):
        raise PbirGeometryError(
            f"page.json has no numeric width/height ({page_json}); cannot validate "
            f"on-canvas"
        )
    return float(w), float(h)


def set_geometry(visual_json: Path, position: dict) -> Path:
    """Set the allow-listed ``position`` keys on the visual, on-canvas + binding-safe."""
    visual_json = Path(visual_json)
    if not visual_json.is_file():
        raise PbirGeometryError(f"visual.json not found: {visual_json}")
    if ".Report" not in str(visual_json.resolve()):
        raise PbirGeometryError("target is not inside a *.Report/ tree")

    doc = _load_json(visual_json, "visual.json")
    if not isinstance(doc.get("visual"), dict):
        raise PbirGeometryError("visual.json has no 'visual' object")
    if not isinstance(doc.get("position"), dict):
        raise PbirGeometryError("visual.json has no 'position' object")

    # Validate the requested keys + numeric values up front.
    if not isinstance(position, dict) or not position:
        raise PbirGeometryError("position must be a non-empty object")
    for key, val in position.items():
        if key not in _ALLOWED_KEYS:
            raise PbirGeometryError(
                f"position key {key!r} is not in the geometry allow-list "
                f"(allowed: {sorted(_ALLOWED_KEYS)})"
            )
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise PbirGeometryError(
                f"position.{key} must be a number, got {type(val).__name__}: {val!r}"
            )

    binding_before = _dump(
        {"query": doc["visual"].get("query"),
         "visualType": doc["visual"].get("visualType")}
    )

    # Compute the RESULT rectangle (existing merged with requested) and validate on-canvas.
    result = {**doc["position"], **position}
    canvas_w, canvas_h = _canvas_dims(visual_json)
    rx, ry = result.get("x", 0), result.get("y", 0)
    rw, rh = result.get("width", 0), result.get("height", 0)
    for label, v in (("x", rx), ("y", ry), ("width", rw), ("height", rh)):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise PbirGeometryError(f"result {label} is not numeric: {v!r}")
    if rx < 0 or ry < 0 or rx + rw > canvas_w or ry + rh > canvas_h:
        raise PbirGeometryError(
            f"result rectangle x={rx} y={ry} w={rw} h={rh} is off-canvas "
            f"(canvas {canvas_w}x{canvas_h}); refusing to write"
        )

    # No overwrite gate: moving a visual necessarily changes always-present position
    # keys, so a "differs -> refuse" gate would block every real move. Overwrite safety
    # is the reviewable git diff + human ratification, not a per-call flag.
    doc["position"] = result

    binding_after = _dump(
        {"query": doc["visual"].get("query"),
         "visualType": doc["visual"].get("visualType")}
    )
    if binding_after != binding_before:
        raise PbirGeometryError(
            "refusing to write: the edit would alter the visual's data binding "
            "(query/visualType) -- this adapter lays out only, never binds (FR-003)"
        )

    text = _dump(doc)
    if _dump(json.loads(text)) != text:
        raise PbirGeometryError("staged visual.json is not round-trip stable")
    visual_json.write_text(text, encoding="utf-8", newline="\n")
    return visual_json
```

Note to implementer: DELETE the dead `if ... : pass  # placeholder replaced below` block — it is a drafting artifact. The real overwrite gate is the `changed` set check that follows it. Keep only the `changed`-set version.

- [ ] **Step 4: Run to verify it passes**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_pbir_geometry.py::test_valid_move_writes_position_and_preserves_binding -q`
Expected: PASS.

- [ ] **Step 5: Write the guard tests (THE canvas-dims invariant + FR-003 + allow-list + overlap)**

```python
def test_offcanvas_rejected_using_REAL_canvas_not_hardcoded_default(tmp_path: Path):
    # Canvas is 1600x900. This rectangle (x=1300,w=400 -> right edge 1700) is
    # off-canvas at 1600 wide, but WOULD fit a hardcoded 1280x720? No -- 1700>1280 too.
    # Use a decoy that fits 1280x720 but NOT 1600x900... impossible (1600>1280).
    # The decoy must be off-canvas at the REAL 1600x900 while on-canvas at 1280x720:
    # choose y so it overruns 900 but not 720 is impossible (900>720). Height instead:
    # place y=800,h=150 -> bottom 950 > 900 (off-canvas real) but 950 > 720 too.
    # The correct decoy: a WRITER THAT HARDCODES 1280x720 would MISS a real-canvas
    # violation only where real<default. Since 1600x900 > 1280x720, we instead prove
    # the guard READS the file by making a rectangle that is ON-canvas at 1600x900
    # but OFF-canvas at 1280x720: x=1300,w=250 -> right 1550 (<=1600 OK) but >1280.
    # A writer hardcoding 1280 REJECTS this valid write -> test asserts it SUCCEEDS.
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    out = set_geometry(vp, {"x": 1300, "y": 100, "width": 250, "height": 200})
    assert out == vp  # valid at real 1600 wide; a hardcoded-1280 writer would reject


def test_truly_offcanvas_rejected(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="off-canvas"):
        set_geometry(vp, {"x": 1500, "y": 100, "width": 300, "height": 200})  # 1800>1600


def test_negative_coord_rejected(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="off-canvas"):
        set_geometry(vp, {"x": -10, "y": 100, "width": 100, "height": 100})


def test_overlap_is_allowed(tmp_path: Path):
    # Move vA to fully overlap vB's rectangle -> must NOT raise (overlap allowed).
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    out = set_geometry(vp, {"x": 300, "y": 250, "width": 300, "height": 300})
    assert out == vp


def test_visualtype_key_is_not_in_allowlist(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="allow-list"):
        set_geometry(vp, {"visualType": "line"})


def test_nonnumeric_value_rejected(tmp_path: Path):
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="must be a number"):
        set_geometry(vp, {"x": "left"})


def test_missing_page_json_is_clean_error_no_hardcode(tmp_path: Path):
    report = _report(tmp_path)
    (report / "definition" / "pages" / "pg" / "page.json").unlink()
    vp = _visual(report, "vA")
    with pytest.raises(PbirGeometryError, match="page.json not found"):
        set_geometry(vp, {"x": 200, "y": 150, "width": 300, "height": 300})


def test_repeated_move_is_allowed_no_force_gate(tmp_path: Path):
    # Moving a visual repeatedly is the operation, not an error -- there is no
    # force gate (position keys always pre-exist; a differs->refuse gate would
    # block every real move). Each call just re-lays-out.
    report = _report(tmp_path)
    vp = _visual(report, "vA")
    assert set_geometry(vp, {"x": 200}) == vp     # 100 -> 200, no force needed
    assert set_geometry(vp, {"x": 250}) == vp     # 200 -> 250, still fine
    assert _load(vp)["position"]["x"] == 250
```

- [ ] **Step 6: Run all module tests**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_pbir_geometry.py -q`
Expected: all PASS. (If `test_offcanvas...REAL...` fails, the guard is hardcoding canvas dims instead of reading page.json.)

- [ ] **Step 7: Commit**

```bash
git add src/seshat/pbir_geometry.py tests/unit/test_pbir_geometry.py
git commit -m "feat: pbir geometry writer -- position rectangle, binding-safe, on-canvas (increment D)"
```

---

### Task 3: CLI subcommand `pbir-set-geometry`

**Files:**
- Modify: `src/seshat/cli.py`
- Modify: `src/seshat/pbir_geometry.py` (add `pbir_geometry_main`)
- Create: `tests/unit/test_pbir_geometry_cli.py`

**Interfaces:**
- Consumes: `set_geometry`, `PbirGeometryError`.
- Produces: `pbir_geometry_main(args) -> int` (0 on success, 2 on `PbirGeometryError` or bad `--position` JSON).

- [ ] **Step 1: Write the failing CLI test**

```python
# tests/unit/test_pbir_geometry_cli.py
"""CLI-level test for `retail pbir-set-geometry`."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from retail.cli import main

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).parent.parent / "fixtures" / "pbir" / "geometry.Report"


def _visual(tmp_path: Path) -> Path:
    dst = tmp_path / "geometry.Report"
    shutil.copytree(FIXTURE, dst)
    return dst / "definition" / "pages" / "pg" / "visuals" / "vA" / "visual.json"


def test_cli_sets_geometry_exit_zero(tmp_path: Path):
    vp = _visual(tmp_path)
    rc = main(["pbir-set-geometry", "--visual", str(vp),
               "--position", '{"x": 200, "y": 150, "width": 400, "height": 250}'])
    assert rc == 0


def test_cli_bad_position_json_exit_two(tmp_path: Path):
    vp = _visual(tmp_path)
    rc = main(["pbir-set-geometry", "--visual", str(vp), "--position", "not-json"])
    assert rc == 2


def test_cli_offcanvas_exit_two(tmp_path: Path):
    vp = _visual(tmp_path)
    rc = main(["pbir-set-geometry", "--visual", str(vp),
               "--position", '{"x": 1500, "width": 300, "height": 200}'])
    assert rc == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_pbir_geometry_cli.py -q`
Expected: FAIL — `pbir-set-geometry` unknown subcommand.

- [ ] **Step 3: Add `pbir_geometry_main` to the module**

Append to `src/seshat/pbir_geometry.py`:
```python
def pbir_geometry_main(args) -> int:
    """CLI entry: set a visual's position rectangle from a JSON string/file."""
    import sys

    raw = args.position
    try:
        if raw and Path(raw).is_file():
            position = json.loads(Path(raw).read_text(encoding="utf-8"))
        else:
            position = json.loads(raw) if raw else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"pbir-set-geometry: bad --position ({exc})", file=sys.stderr)
        return 2
    try:
        written = set_geometry(Path(args.visual), position)
    except PbirGeometryError as exc:
        print(f"pbir-set-geometry: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {written}")
    print(
        "note: layout only -- the visual's data binding (query/visualType) is "
        "unchanged; this grants no readiness pass (a human render + review does)."
    )
    return 0
```

- [ ] **Step 4: Add the subparser in cli.py**

In `src/seshat/cli.py`, immediately AFTER the `pbir-set-page-background` subparser block (after its last `.add_argument(...)`, before the next `sub.add_parser(...)` — e.g. `manifest`), add:
```python
    # PBIR visual geometry (adapter increment D). Sets a visual's position rectangle
    # (x/y/width/height/z/tabOrder), preserving its data binding (FR-003) and refusing
    # off-canvas rectangles read from the real page.json canvas. NEVER visualType /
    # creation / unbound moves (ADR 0016). Allow-list-only; no external dependency.
    pbirgeom = sub.add_parser(
        "pbir-set-geometry",
        help="set a PBIR visual's position rectangle (adapter increment D)",
    )
    pbirgeom.add_argument(
        "--visual", required=True, metavar="PATH", help="the visual.json to lay out"
    )
    pbirgeom.add_argument(
        "--position",
        required=True,
        metavar="JSON_OR_PATH",
        help='position as a JSON string or path: {"x": 100, "y": 80, "width": 400, "height": 300}',
    )
```

- [ ] **Step 5: Add the dispatch branch in cli.py**

In `src/seshat/cli.py`, immediately AFTER the `pbir-set-page-background` dispatch (`return pbir_page_bg_main(args)`), add:
```python
    if args.command == "pbir-set-geometry":
        from .pbir_geometry import pbir_geometry_main

        return pbir_geometry_main(args)
```

- [ ] **Step 6: Run the CLI tests**

Run: `cd C:/Users/user/Documents/GitHub/Seshat_BI && PYTHONPATH=src python -m pytest tests/unit/test_pbir_geometry_cli.py -q`
Expected: 3 PASS.

- [ ] **Step 7: Commit**

```bash
git add src/seshat/cli.py src/seshat/pbir_geometry.py tests/unit/test_pbir_geometry_cli.py
git commit -m "feat: wire pbir-set-geometry CLI subcommand (increment D)"
```

---

### Task 4: Docs + full gate

**Files:**
- Modify: `docs/integrations/pbir-adapter.md` (add increment D to the verb list)

- [ ] **Step 1: Add increment D to the adapter doc**

In `docs/integrations/pbir-adapter.md`, in the verb list/increment section, add a bullet matching the existing style:
```markdown
- **`retail pbir-set-geometry`** (increment D) — sets a visual's `position` rectangle
  (x/y/width/height/z/tabOrder), preserving its data binding (FR-003) and refusing
  off-canvas rectangles read from the real `page.json` canvas. Never changes
  `visualType`, creates/deletes visuals, or moves an unbound visual (ADR 0016). Ships
  latent (proven on a fixture; latent until a real multi-visual report lands).
```

- [ ] **Step 2: Run the full gate**

Run:
```bash
cd C:/Users/user/Documents/GitHub/Seshat_BI
ruff format --check src tests && ruff check src tests && PYTHONPATH=src python -m pytest tests/unit/test_pbir_geometry.py tests/unit/test_pbir_geometry_cli.py -q && PYTHONPATH=src python -c "from retail.cli import main; import sys; sys.exit(main(['check']))"
```
Expected: format clean, lint clean, geometry tests PASS, `retail check` → Passed (exit 0).

- [ ] **Step 3: Commit**

```bash
git add docs/integrations/pbir-adapter.md
git commit -m "docs: note pbir-set-geometry (increment D) in the adapter doc"
```

---

## Self-Review

**1. Spec coverage:** writer + position allow-list (Task 2); FR-003 preserve (Task 2 test); on-canvas guard reading real page.json (Task 2 `_canvas_dims` + the REAL-canvas test); overlap allowed (test); off-canvas/negative/non-numeric rejected (tests); missing page.json clean error no-hardcode (test); repeated-move-no-force-gate (test); CLI (Task 3); latent + doc (Task 4). ✓ (NO force gate — dropped; see Global Constraints.)

**2. Placeholder scan:** one intentional drafting artifact flagged for deletion in Task 2 Step 3 (the `pass  # placeholder` block) — the implementer is told explicitly to delete it and keep the `changed`-set gate. No other placeholders; all code + commands complete. ✓

**3. Type consistency:** `set_geometry(visual_json, position) -> Path` (no force) consumed identically by `pbir_geometry_main` and every test. `PbirGeometryError` is the raised type throughout. `_canvas_dims -> tuple[float,float]`. Position keys `_ALLOWED_KEYS` match the fixture's `position` keys and the ADR. ✓

**Note on the REAL-canvas test:** its long comment works through why a naive decoy is impossible (1600×900 > 1280×720) and lands on the correct invariant — a rectangle valid at 1600 wide (x=1300,w=250→1550) that a writer hardcoding 1280 would WRONGLY reject; the test asserts the write SUCCEEDS, so a hardcoding writer fails it. Keep the final assertion; the comment may be trimmed by the implementer.
