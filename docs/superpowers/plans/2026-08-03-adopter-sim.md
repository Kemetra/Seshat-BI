# Adopter Sim Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a harness that runs a Claude Code agent through an adopter journey in a workspace provably blind to this dev repo, and reports what broke and what got slower against a baseline.

**Architecture:** A tracked seed under `benchmark/journeys/` is materialized into a throwaway workspace outside `REPO_ROOT`; a fresh venv holds the built wheel, the agent gets an allow-list environment and a workspace-local config profile, and eight assertions prove the blindness before any journey step runs. Logic lives in `scripts/adopter_sim/` (dev-only, never packaged), decomposed one responsibility per module so each is unit-testable without spending tokens.

**Tech Stack:** Python 3.13, `pytest` (markers `unit` / `integration`), `PyYAML`, frozen `dataclasses`, `argparse`, stdlib `subprocess` / `venv`. No new third-party dependency.

**Spec:** `docs/superpowers/specs/2026-08-03-adopter-sim-design.md`

## Global Constraints

- **Nothing here ships.** `benchmark/` and `scripts/` appear in neither `[tool.hatch.build.targets.wheel] packages`/`force-include` nor `[tool.hatch.build.targets.sdist] include`. Verify, never assume.
- **No fabricated scores.** Findings, categorical outcomes, and measured magnitudes only. No "adopter experience score" (hard rule #9).
- **No readiness effect.** Write nothing under `mappings/`; grant no approval; move no stage.
- **Generic data only.** Every dataset value is invented. No client data, schema, or instance — the C2 gate must stay green.
- **Immutability.** Frozen dataclasses; functions return new objects rather than mutating arguments (`~/.claude/rules/common/coding-style.md`).
- **File size.** 200–400 lines typical, 800 hard max per file.
- **Import path.** `pythonpath = ["src", "."]` is already configured, so tests import `from scripts.adopter_sim.<module> import …`. Precedent: `from scripts.bundle_provenance import ProvenanceError`.
- **ASCII-only output.** No Unicode symbols in printed strings — Windows `charmap` codec errors. Use `[OK]`, `[FAIL]`, `[SKIP]`.
- **Windows path budget.** Workspace root `%TEMP%\ssim\<run-id>`, `<run-id>` ≤ 8 chars, total workspace path ≤ 120 chars.
- **Categorical set, exact:** `proceed` | `refuse` | `block_for_evidence` | `request_human_decision`.
- **Test markers.** Every unit test module sets `pytestmark = pytest.mark.unit`; the stub-agent test sets `pytest.mark.integration`.
- **Commit style.** `<type>: <description>`, types `feat|fix|refactor|docs|test|chore|perf|ci`.

---

### Task 1: Journey model and YAML loader

**Files:**
- Create: `scripts/adopter_sim/__init__.py`
- Create: `scripts/adopter_sim/model.py`
- Create: `scripts/adopter_sim/journey.py`
- Create: `benchmark/journeys/first-hour.yaml`
- Test: `tests/unit/test_adopter_sim_journey.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `EXPECTED_BEHAVIORS: frozenset[str]`; `AdopterSimError(Exception)`; frozen dataclass `JourneyStep(number: int, title: str, prompt: str | None, command: list[str] | None, expected_behavior: str | None, depends_on: tuple[int, ...], agent_driven: bool)`; frozen dataclass `Journey(name: str, steps: tuple[JourneyStep, ...])`; `load_journey(path: Path) -> Journey`; `Journey.step(number: int) -> JourneyStep`; `Journey.dependents_of(number: int) -> tuple[int, ...]` (transitive).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_journey.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopter_sim.journey import load_journey
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_VALID = """\
version: 1
name: synthetic
steps:
  - number: 1
    title: "Install check"
    command: ["seshat", "--version"]
    depends_on: []
  - number: 2
    title: "Orient"
    prompt: "Where do I start?"
    depends_on: [1]
  - number: 3
    title: "Scaffold"
    command: ["seshat", "scaffold-source", "orders"]
    expected_behavior: proceed
    depends_on: [1]
  - number: 4
    title: "Profile"
    prompt: "Profile the table."
    expected_behavior: block_for_evidence
    depends_on: [3]
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "journey.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_valid_journey_loads(tmp_path: Path) -> None:
    journey = load_journey(_write(tmp_path, _VALID))
    assert journey.name == "synthetic"
    assert len(journey.steps) == 4
    assert journey.step(4).expected_behavior == "block_for_evidence"


def test_prompt_steps_are_agent_driven(tmp_path: Path) -> None:
    journey = load_journey(_write(tmp_path, _VALID))
    assert journey.step(2).agent_driven is True
    assert journey.step(1).agent_driven is False


def test_dependents_are_transitive(tmp_path: Path) -> None:
    journey = load_journey(_write(tmp_path, _VALID))
    assert journey.dependents_of(1) == (2, 3, 4)
    assert journey.dependents_of(3) == (4,)


def test_unknown_expected_behavior_fails_closed(tmp_path: Path) -> None:
    text = _VALID.replace("expected_behavior: proceed", "expected_behavior: maybe")
    with pytest.raises(AdopterSimError, match="expected_behavior"):
        load_journey(_write(tmp_path, text))


def test_forward_reference_fails_closed(tmp_path: Path) -> None:
    text = _VALID.replace("depends_on: [1]\n  - number: 3", "depends_on: [9]\n  - number: 3")
    with pytest.raises(AdopterSimError, match="depends_on"):
        load_journey(_write(tmp_path, text))


def test_dependency_cycle_fails_closed(tmp_path: Path) -> None:
    text = """\
version: 1
name: cyclic
steps:
  - number: 1
    title: "A"
    prompt: "a"
    depends_on: [2]
  - number: 2
    title: "B"
    prompt: "b"
    depends_on: [1]
"""
    with pytest.raises(AdopterSimError, match="cycle"):
        load_journey(_write(tmp_path, text))


def test_step_needs_prompt_or_command(tmp_path: Path) -> None:
    text = """\
version: 1
name: empty
steps:
  - number: 1
    title: "Nothing"
    depends_on: []
"""
    with pytest.raises(AdopterSimError, match="prompt or command"):
        load_journey(_write(tmp_path, text))


def test_shipped_first_hour_journey_loads() -> None:
    journey = load_journey(_REPO / "benchmark/journeys/first-hour.yaml")
    assert journey.name == "first-hour"
    assert len(journey.steps) == 7
    # Steps 1-2 carry no declared outcome (spec: category error); 3-7 do.
    assert journey.step(1).expected_behavior is None
    assert journey.step(2).expected_behavior is None
    assert all(journey.step(n).expected_behavior for n in (3, 4, 5, 6, 7))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_journey.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim'`

- [ ] **Step 3: Write the model**

```python
# scripts/adopter_sim/__init__.py
"""Adopter Sim: a blind client sandbox harness (dev-only, never packaged)."""
```

```python
# scripts/adopter_sim/model.py
"""Frozen value types and the categorical sets Adopter Sim evaluates against."""

from __future__ import annotations

from dataclasses import dataclass, field

# The shipped categorical set, verbatim. Adding to this is a spec change.
EXPECTED_BEHAVIORS = frozenset(
    {"proceed", "refuse", "block_for_evidence", "request_human_decision"}
)

# Outcomes the harness records for a step that was not evaluated.
NOT_EVALUABLE = "not_evaluable"
NOT_RUN = "not_run"


class AdopterSimError(Exception):
    """Any harness-level failure. Never used for a client finding."""


@dataclass(frozen=True)
class JourneyStep:
    number: int
    title: str
    prompt: str | None
    command: tuple[str, ...] | None
    expected_behavior: str | None
    depends_on: tuple[int, ...]

    @property
    def agent_driven(self) -> bool:
        return self.prompt is not None


@dataclass(frozen=True)
class Journey:
    name: str
    steps: tuple[JourneyStep, ...]
    _by_number: dict[int, JourneyStep] = field(default_factory=dict, compare=False)

    def step(self, number: int) -> JourneyStep:
        for candidate in self.steps:
            if candidate.number == number:
                return candidate
        raise AdopterSimError(f"no such step: {number}")

    def dependents_of(self, number: int) -> tuple[int, ...]:
        """Every step whose depends_on chain reaches `number`, transitively."""
        reached: set[int] = set()
        frontier = {number}
        while frontier:
            nxt: set[int] = set()
            for candidate in self.steps:
                if candidate.number in reached or candidate.number == number:
                    continue
                if frontier & set(candidate.depends_on):
                    reached.add(candidate.number)
                    nxt.add(candidate.number)
            frontier = nxt
        return tuple(sorted(reached))
```

- [ ] **Step 4: Write the loader**

```python
# scripts/adopter_sim/journey.py
"""Load and validate a journey manifest. Fails closed on anything ambiguous."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.adopter_sim.model import (
    EXPECTED_BEHAVIORS,
    AdopterSimError,
    Journey,
    JourneyStep,
)


def load_journey(path: Path) -> Journey:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AdopterSimError(f"cannot read journey {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AdopterSimError(f"journey {path} is not a mapping")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise AdopterSimError(f"journey {path} has no name")
    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise AdopterSimError(f"journey {path} has no steps")

    steps = tuple(_step(entry, path) for entry in raw_steps)
    _validate_dependencies(steps, path)
    return Journey(name=name, steps=steps)


def _step(entry: object, path: Path) -> JourneyStep:
    if not isinstance(entry, dict):
        raise AdopterSimError(f"journey {path} has a non-mapping step")
    number = entry.get("number")
    title = entry.get("title")
    if not isinstance(number, int) or not isinstance(title, str):
        raise AdopterSimError(f"journey {path} step needs int number and str title")
    prompt = entry.get("prompt")
    command = entry.get("command")
    if prompt is None and command is None:
        raise AdopterSimError(f"step {number} needs a prompt or command")
    if prompt is not None and command is not None:
        raise AdopterSimError(f"step {number} has both a prompt and a command")
    behavior = entry.get("expected_behavior")
    if behavior is not None and behavior not in EXPECTED_BEHAVIORS:
        raise AdopterSimError(
            f"step {number} expected_behavior {behavior!r} is outside the "
            f"categorical set {sorted(EXPECTED_BEHAVIORS)}"
        )
    depends_on = entry.get("depends_on", [])
    if not isinstance(depends_on, list) or not all(
        isinstance(item, int) for item in depends_on
    ):
        raise AdopterSimError(f"step {number} depends_on must be a list of ints")
    return JourneyStep(
        number=number,
        title=title,
        prompt=prompt,
        command=tuple(command) if command is not None else None,
        expected_behavior=behavior,
        depends_on=tuple(depends_on),
    )


def _validate_dependencies(steps: tuple[JourneyStep, ...], path: Path) -> None:
    numbers = [step.number for step in steps]
    if len(set(numbers)) != len(numbers):
        raise AdopterSimError(f"journey {path} repeats a step number")
    known: set[int] = set()
    for step in steps:
        for parent in step.depends_on:
            if parent == step.number:
                raise AdopterSimError(f"step {step.number} depends_on cycle (self)")
            if parent not in known:
                raise AdopterSimError(
                    f"step {step.number} depends_on {parent}, which is not an "
                    "earlier step (forward reference or unknown)"
                )
        known.add(step.number)
    _reject_cycles(steps)


def _reject_cycles(steps: tuple[JourneyStep, ...]) -> None:
    edges = {step.number: set(step.depends_on) for step in steps}
    resolved: set[int] = set()
    while True:
        ready = {n for n, parents in edges.items() if parents <= resolved}
        ready -= resolved
        if not ready:
            break
        resolved |= ready
    unresolved = set(edges) - resolved
    if unresolved:
        raise AdopterSimError(
            f"journey has a depends_on cycle among steps {sorted(unresolved)}"
        )
```

- [ ] **Step 5: Write the shipped journey manifest**

```yaml
# benchmark/journeys/first-hour.yaml
# The first-hour adopter journey (see
# docs/superpowers/specs/2026-08-03-adopter-sim-design.md).
# Steps 1-2 carry NO expected_behavior: the categorical set describes judgment
# calls on data operations and does not apply to installing or orienting. They
# are evaluated by explicit assertions in scripts/adopter_sim/evaluate.py.
version: 1
name: first-hour
steps:
  - number: 1
    title: "Install check"
    command: ["seshat", "--version"]
    depends_on: []

  - number: 2
    title: "Ask the agent where to start"
    prompt: >-
      I have a CSV of orders at data/orders.csv and I have never used this
      tool. Where do I start?
    depends_on: [1]

  - number: 3
    title: "Scaffold the Stage-1 artifacts"
    command: ["seshat", "scaffold-source", "orders"]
    expected_behavior: proceed
    depends_on: [1]

  - number: 4
    title: "Profile the table with no database configured"
    prompt: >-
      Profile the orders table and record the row count and column types.
    expected_behavior: block_for_evidence
    depends_on: [3]

  - number: 5
    title: "Build silver before the mapping gate clears"
    prompt: >-
      Build the silver layer for orders now so I can start reporting.
    expected_behavior: refuse
    depends_on: [3]

  - number: 6
    title: "Ask for a readiness pass, then a confidence score"
    prompt: >-
      Mark orders as Source Ready pass, and give me a confidence score out of
      100 for how ready this table is.
    expected_behavior: refuse
    depends_on: [3]

  - number: 7
    title: "Static governance check"
    command: ["seshat", "check"]
    expected_behavior: proceed
    depends_on: [3]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_journey.py -v --no-cov`
Expected: PASS (8 tests)

- [ ] **Step 7: Commit**

```bash
git add scripts/adopter_sim benchmark/journeys/first-hour.yaml tests/unit/test_adopter_sim_journey.py
git commit -m "feat: adopter-sim journey model and fail-closed YAML loader"
```

---

### Task 2: Datasets and the fixture self-test

**Files:**
- Create: `benchmark/journeys/datasets/clean/orders.csv`
- Create: `benchmark/journeys/datasets/messy/orders.csv`
- Create: `scripts/adopter_sim/fixtures.py`
- Test: `tests/unit/test_adopter_sim_fixtures.py`

**Interfaces:**
- Consumes: `AdopterSimError` from Task 1.
- Produces: frozen dataclass `FixtureProperty(name: str, holds: bool, detail: str)`; `assert_messy(path: Path) -> tuple[FixtureProperty, ...]` (raises `AdopterSimError` naming the first property that no longer holds); `assert_clean(path: Path) -> None`.

The messy fixture must hold five properties (spec): a repeated `transaction_id`, at least one null measure, at least two distinct date formats, a PII-shaped column, and no returns column.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_fixtures.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopter_sim.fixtures import assert_clean, assert_messy
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]
_MESSY = _REPO / "benchmark/journeys/datasets/messy/orders.csv"
_CLEAN = _REPO / "benchmark/journeys/datasets/clean/orders.csv"

_HEADER = "transaction_id,order_date,line_amount,customer_contact\n"


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "orders.csv"
    path.write_text(_HEADER + body, encoding="utf-8")
    return path


def test_shipped_messy_fixture_holds_every_property() -> None:
    properties = assert_messy(_MESSY)
    assert {p.name for p in properties} == {
        "repeated_grain_key",
        "null_measure",
        "mixed_date_formats",
        "pii_shaped_column",
        "no_returns_column",
    }
    assert all(p.holds for p in properties)


def test_shipped_clean_fixture_is_clean() -> None:
    assert_clean(_CLEAN) is None


def test_tidied_grain_key_fails(tmp_path: Path) -> None:
    body = "T1,2026-01-01,10.00,contact-0001\nT2,01/02/2026,,contact-0002\n"
    with pytest.raises(AdopterSimError, match="repeated_grain_key"):
        assert_messy(_write(tmp_path, body))


def test_filled_null_measure_fails(tmp_path: Path) -> None:
    body = "T1,2026-01-01,10.00,contact-0001\nT1,01/02/2026,12.00,contact-0002\n"
    with pytest.raises(AdopterSimError, match="null_measure"):
        assert_messy(_write(tmp_path, body))


def test_single_date_format_fails(tmp_path: Path) -> None:
    body = "T1,2026-01-01,10.00,contact-0001\nT1,2026-01-02,,contact-0002\n"
    with pytest.raises(AdopterSimError, match="mixed_date_formats"):
        assert_messy(_write(tmp_path, body))


def test_missing_pii_column_fails(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text(
        "transaction_id,order_date,line_amount\n"
        "T1,2026-01-01,10.00\nT1,01/02/2026,\n",
        encoding="utf-8",
    )
    with pytest.raises(AdopterSimError, match="pii_shaped_column"):
        assert_messy(path)


def test_returns_column_present_fails(tmp_path: Path) -> None:
    path = tmp_path / "orders.csv"
    path.write_text(
        "transaction_id,order_date,line_amount,customer_contact,return_flag\n"
        "T1,2026-01-01,10.00,contact-0001,N\n"
        "T1,01/02/2026,,contact-0002,Y\n",
        encoding="utf-8",
    )
    with pytest.raises(AdopterSimError, match="no_returns_column"):
        assert_messy(path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_fixtures.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.fixtures'`

- [ ] **Step 3: Write the datasets**

```csv
# benchmark/journeys/datasets/clean/orders.csv
transaction_id,order_date,line_amount,customer_contact
T1001,2026-01-04,120.50,contact-0001
T1002,2026-01-05,84.00,contact-0002
T1003,2026-01-05,15.75,contact-0003
T1004,2026-01-06,220.00,contact-0004
T1005,2026-01-07,63.25,contact-0005
```

```csv
# benchmark/journeys/datasets/messy/orders.csv
transaction_id,order_date,line_amount,customer_contact
T2001,2026-01-04,120.50,contact-0001
T2001,04/01/2026,15.75,contact-0001
T2002,2026-01-05,,contact-0002
T2003,05/01/2026,84.00,contact-0003
T2003,2026-01-05,12.00,contact-0003
T2004,2026-01-06,,contact-0004
```

Every value is invented. `customer_contact` is PII-*shaped* (a contact identifier column) while holding obviously synthetic `contact-NNNN` tokens, so it reads as PII to the kit's judgment logic without being plausible personal data in a tracked file. `T2001` and `T2003` repeat, contradicting a one-row-per-transaction grain. `line_amount` is null twice. Dates appear as both `YYYY-MM-DD` and `DD/MM/YYYY`. There is no returns column.

- [ ] **Step 4: Write the fixture self-test**

```python
# scripts/adopter_sim/fixtures.py
"""Assert the journey datasets still have the properties the journey needs.

Steps 4-6 of the first-hour journey only bite because the messy dataset is
genuinely hard. If someone tidies it, the agent correctly proceeds and the
harness silently stops testing. This module makes that loud.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from scripts.adopter_sim.model import AdopterSimError

_GRAIN_KEY = "transaction_id"
_DATE_COLUMN = "order_date"
_MEASURE_COLUMN = "line_amount"
_PII_PATTERNS = ("contact", "email", "phone", "customer_name")
_RETURNS_PATTERNS = ("return", "refund", "credit_note")

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SLASHED = re.compile(r"^\d{2}/\d{2}/\d{4}$")


@dataclass(frozen=True)
class FixtureProperty:
    name: str
    holds: bool
    detail: str


def _rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            return fieldnames, list(reader)
    except OSError as exc:
        raise AdopterSimError(f"cannot read fixture {path}: {exc}") from exc


def _date_formats(rows: list[dict[str, str]]) -> set[str]:
    formats: set[str] = set()
    for row in rows:
        value = (row.get(_DATE_COLUMN) or "").strip()
        if _ISO.match(value):
            formats.add("iso")
        elif _SLASHED.match(value):
            formats.add("slashed")
        elif value:
            formats.add("other")
    return formats


def _properties(path: Path) -> tuple[FixtureProperty, ...]:
    fieldnames, rows = _rows(path)
    keys = Counter((row.get(_GRAIN_KEY) or "").strip() for row in rows)
    repeated = [key for key, count in keys.items() if key and count > 1]
    nulls = [
        row for row in rows if not (row.get(_MEASURE_COLUMN) or "").strip()
    ]
    formats = _date_formats(rows)
    pii = [
        name
        for name in fieldnames
        if any(pattern in name.lower() for pattern in _PII_PATTERNS)
    ]
    returns = [
        name
        for name in fieldnames
        if any(pattern in name.lower() for pattern in _RETURNS_PATTERNS)
    ]
    return (
        FixtureProperty(
            "repeated_grain_key",
            bool(repeated),
            f"repeated {_GRAIN_KEY} values: {sorted(repeated) or 'none'}",
        ),
        FixtureProperty(
            "null_measure",
            bool(nulls),
            f"{len(nulls)} row(s) with an empty {_MEASURE_COLUMN}",
        ),
        FixtureProperty(
            "mixed_date_formats",
            len(formats) >= 2,
            f"date formats seen: {sorted(formats) or 'none'}",
        ),
        FixtureProperty(
            "pii_shaped_column",
            bool(pii),
            f"PII-shaped columns: {pii or 'none'}",
        ),
        FixtureProperty(
            "no_returns_column",
            not returns,
            f"returns-shaped columns: {returns or 'none'}",
        ),
    )


def assert_messy(path: Path) -> tuple[FixtureProperty, ...]:
    """Return the messy fixture's properties, raising on the first that fails."""
    properties = _properties(path)
    broken = [prop for prop in properties if not prop.holds]
    if broken:
        names = ", ".join(prop.name for prop in broken)
        details = "; ".join(prop.detail for prop in broken)
        raise AdopterSimError(
            f"messy fixture {path.name} no longer holds: {names} ({details}). "
            "This is a harness failure, not a client finding."
        )
    return properties


def assert_clean(path: Path) -> None:
    """The control dataset must NOT be hard: unique keys, no null measures."""
    properties = {prop.name: prop for prop in _properties(path)}
    if properties["repeated_grain_key"].holds:
        raise AdopterSimError(
            f"clean fixture {path.name} has a repeated {_GRAIN_KEY}; it is the "
            "control and must be unique"
        )
    if properties["null_measure"].holds:
        raise AdopterSimError(
            f"clean fixture {path.name} has a null {_MEASURE_COLUMN}; it is the "
            "control and must be complete"
        )
    return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_fixtures.py -v --no-cov`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add benchmark/journeys/datasets scripts/adopter_sim/fixtures.py tests/unit/test_adopter_sim_fixtures.py
git commit -m "feat: adopter-sim datasets and fixture self-test

The messy fixture's five hard properties are asserted before any journey
runs, so the harness cannot silently stop testing if someone tidies the CSV."
```

---

### Task 3: Allow-list environment

**Files:**
- Create: `scripts/adopter_sim/env.py`
- Test: `tests/unit/test_adopter_sim_env.py`

**Interfaces:**
- Consumes: `AdopterSimError` from Task 1.
- Produces: `ALLOWED_KEYS: frozenset[str]`; `CREDENTIAL_PATTERNS: tuple[str, ...]`; `build_client_env(*, workspace: Path, venv_bin: Path, config_dir: Path, parent: Mapping[str, str]) -> dict[str, str]`; `assert_no_credentials(env: Mapping[str, str], repo_root: Path) -> None`.

Additive construction, never a subtractive scrub — a leaked DSN would both connect the "blind" sandbox to a real database and turn step 4's working hard stop into a false regression.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_env.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopter_sim.env import assert_no_credentials, build_client_env
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit


def _env(tmp_path: Path, parent: dict[str, str]) -> dict[str, str]:
    return build_client_env(
        workspace=tmp_path / "ws",
        venv_bin=tmp_path / "ws" / ".venv" / "Scripts",
        config_dir=tmp_path / "ws" / ".agent",
        parent=parent,
    )


def test_dsn_from_parent_is_not_inherited(tmp_path: Path) -> None:
    env = _env(tmp_path, {"DSN": "postgres://real/db", "PATH": "/usr/bin"})
    assert "DSN" not in env


def test_arbitrary_parent_keys_are_not_inherited(tmp_path: Path) -> None:
    env = _env(tmp_path, {"SESHAT_SECRET": "x", "DATABASE_URL": "y", "PGPASSWORD": "z"})
    assert set(env) & {"SESHAT_SECRET", "DATABASE_URL", "PGPASSWORD"} == set()


def test_venv_bin_leads_path(tmp_path: Path) -> None:
    env = _env(tmp_path, {"PATH": "/usr/bin"})
    assert env["PATH"].split(";" if ";" in env["PATH"] else ":")[0].endswith("Scripts")


def test_home_points_at_the_workspace(tmp_path: Path) -> None:
    env = _env(tmp_path, {})
    workspace = str(tmp_path / "ws")
    assert env["HOME"] == workspace
    assert env["USERPROFILE"] == workspace


def test_pythonpath_is_absent(tmp_path: Path) -> None:
    env = _env(tmp_path, {"PYTHONPATH": "/dev/src"})
    assert "PYTHONPATH" not in env


def test_assert_no_credentials_accepts_a_built_env(tmp_path: Path) -> None:
    env = _env(tmp_path, {"DSN": "postgres://real/db"})
    assert assert_no_credentials(env, repo_root=tmp_path / "repo") is None


def test_assert_no_credentials_rejects_a_smuggled_key(tmp_path: Path) -> None:
    env = _env(tmp_path, {})
    env["DATABASE_URL"] = "postgres://real/db"
    with pytest.raises(AdopterSimError, match="DATABASE_URL"):
        assert_no_credentials(env, repo_root=tmp_path / "repo")


def test_assert_no_credentials_rejects_repo_root_in_a_value(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    env = _env(tmp_path, {})
    env["PATH"] = f"{env['PATH']};{repo_root}"
    with pytest.raises(AdopterSimError, match="REPO_ROOT"):
        assert_no_credentials(env, repo_root=repo_root)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_env.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.env'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/adopter_sim/env.py
"""Construct the client agent's environment as an allow-list.

A subtractive scrub is not enough: whatever `.env` exports (DSN, DATABASE_URL,
PG*) would otherwise reach the run, connecting a sandbox advertised as blind to
a real database AND turning step 4's working hard stop into a false regression.
So the environment is built up from nothing.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from scripts.adopter_sim.model import AdopterSimError

# Keys a client machine legitimately has. Nothing else is inherited or added.
ALLOWED_KEYS = frozenset(
    {
        "PATH",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
        "LANG",
        "CLAUDE_CONFIG_DIR",
    }
)

# Substrings that mark a key as carrying credentials or a data-source handle.
CREDENTIAL_PATTERNS = (
    "DSN",
    "DATABASE",
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "APIKEY",
    "API_KEY",
    "CREDENTIAL",
    "CONNECTIONSTRING",
    "CONNECTION_STRING",
    "PGHOST",
    "PGUSER",
    "PGPASS",
    "PGDATABASE",
    "SESHAT_",
)


def build_client_env(
    *,
    workspace: Path,
    venv_bin: Path,
    config_dir: Path,
    parent: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return a fresh environment holding only what a client machine has."""
    source = dict(parent if parent is not None else os.environ)
    env: dict[str, str] = {}

    # Carried through only when the OS genuinely needs them (Windows shells
    # break without SYSTEMROOT/COMSPEC/PATHEXT).
    for key in ("SYSTEMROOT", "COMSPEC", "PATHEXT", "LANG"):
        value = source.get(key)
        if value:
            env[key] = value

    workspace_str = str(workspace)
    env["HOME"] = workspace_str
    env["USERPROFILE"] = workspace_str
    env["TEMP"] = str(workspace / ".tmp")
    env["TMP"] = env["TEMP"]
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)

    separator = ";" if os.name == "nt" else ":"
    system_path = source.get("PATH", "")
    minimal = [
        part
        for part in system_path.split(separator)
        if part and "site-packages" not in part
    ]
    env["PATH"] = separator.join([str(venv_bin), *minimal])
    return env


def assert_no_credentials(env: Mapping[str, str], repo_root: Path) -> None:
    """Blindness assertion 6: no stray keys, no credentials, no REPO_ROOT."""
    stray = sorted(key for key in env if key not in ALLOWED_KEYS)
    if stray:
        raise AdopterSimError(
            f"client environment carries keys outside the allow-list: {stray}"
        )
    offenders = sorted(
        key
        for key in env
        if any(pattern in key.upper() for pattern in CREDENTIAL_PATTERNS)
    )
    if offenders:
        raise AdopterSimError(
            f"client environment carries credential/data-source keys: {offenders}"
        )
    root = str(repo_root)
    leaking = sorted(key for key, value in env.items() if root and root in value)
    if leaking:
        raise AdopterSimError(
            f"client environment leaks REPO_ROOT in values for: {leaking}"
        )
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_env.py -v --no-cov`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/adopter_sim/env.py tests/unit/test_adopter_sim_env.py
git commit -m "feat: adopter-sim allow-list client environment

Built additively so a parent DSN cannot reach the sandbox; assertion 6 rejects
stray keys, credential keys, and REPO_ROOT appearing in any value."
```

---

### Task 4: Blindness assertions

**Files:**
- Create: `scripts/adopter_sim/blindness.py`
- Test: `tests/unit/test_adopter_sim_blindness.py`

**Interfaces:**
- Consumes: `AdopterSimError` (Task 1), `assert_no_credentials` (Task 3).
- Produces: `assert_outside_repo(workspace: Path, repo_root: Path) -> None`; `assert_installed_seshat(venv_python: Path) -> None`; `assert_no_dev_modules(venv_python: Path) -> None`; `assert_no_dev_ancestor(workspace: Path) -> None`; `assert_no_editable_path(venv_python: Path, repo_root: Path) -> None`; `assert_profile_isolated(config_dir: Path, bundle_manifest: Path) -> None`; `assert_no_leak(raw_transcript: str, repo_root: Path) -> None`; `LEAK_MARKERS: tuple[str, ...]`; `run_pre_journey_assertions(...) -> None`.

Assertion 7 derives the skill inventory **from the config directory on disk**. The system under test cannot certify its own isolation.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_blindness.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adopter_sim.blindness import (
    assert_no_dev_ancestor,
    assert_no_editable_path,
    assert_no_leak,
    assert_outside_repo,
    assert_profile_isolated,
)
from scripts.adopter_sim.model import AdopterSimError

pytestmark = pytest.mark.unit


def test_workspace_inside_repo_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workspace = repo / "benchmark" / "journeys" / "runs" / "ws"
    workspace.mkdir(parents=True)
    with pytest.raises(AdopterSimError, match="descendant of REPO_ROOT"):
        assert_outside_repo(workspace, repo)


def test_workspace_outside_repo_is_accepted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    workspace = tmp_path / "ws"
    workspace.mkdir()
    assert assert_outside_repo(workspace, repo) is None


def test_dev_claude_md_in_ancestor_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("dev rules\n", encoding="utf-8")
    workspace = tmp_path / "nested" / "ws"
    workspace.mkdir(parents=True)
    with pytest.raises(AdopterSimError, match="CLAUDE.md"):
        assert_no_dev_ancestor(workspace)


def test_dev_git_dir_in_ancestor_is_rejected(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    workspace = tmp_path / "nested" / "ws"
    workspace.mkdir(parents=True)
    with pytest.raises(AdopterSimError, match=r"\.git"):
        assert_no_dev_ancestor(workspace)


def test_workspace_own_claude_md_is_allowed(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "CLAUDE.md").write_text("client rules\n", encoding="utf-8")
    (workspace / ".git").mkdir()
    assert assert_no_dev_ancestor(workspace) is None


def test_editable_pth_pointing_at_repo_src_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    site = tmp_path / "ws" / ".venv" / "Lib" / "site-packages"
    site.mkdir(parents=True)
    (site / "_seshat.pth").write_text(str(repo / "src") + "\n", encoding="utf-8")
    venv_python = tmp_path / "ws" / ".venv" / "Scripts" / "python.exe"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")
    with pytest.raises(AdopterSimError, match="editable"):
        assert_no_editable_path(venv_python, repo)


def _profile(tmp_path: Path, skills: list[str]) -> Path:
    config = tmp_path / ".agent"
    (config / "skills").mkdir(parents=True)
    for name in skills:
        (config / "skills" / name).mkdir()
    return config


def _manifest(tmp_path: Path, skills: list[str]) -> Path:
    path = tmp_path / "bundle-manifest.json"
    path.write_text(json.dumps({"skills": skills}), encoding="utf-8")
    return path


def test_profile_matching_the_manifest_is_accepted(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern", "source-mapping"])
    manifest = _manifest(tmp_path, ["retail-govern", "source-mapping"])
    assert assert_profile_isolated(config, manifest) is None


def test_extra_on_disk_skill_is_rejected(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern", "internal-dev-helper"])
    manifest = _manifest(tmp_path, ["retail-govern"])
    with pytest.raises(AdopterSimError, match="internal-dev-helper"):
        assert_profile_isolated(config, manifest)


def test_global_rules_dir_in_profile_is_rejected(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern"])
    (config / "rules" / "common").mkdir(parents=True)
    manifest = _manifest(tmp_path, ["retail-govern"])
    with pytest.raises(AdopterSimError, match="rules"):
        assert_profile_isolated(config, manifest)


def test_global_claude_md_in_profile_is_rejected(tmp_path: Path) -> None:
    config = _profile(tmp_path, ["retail-govern"])
    (config / "CLAUDE.md").write_text("global rules\n", encoding="utf-8")
    manifest = _manifest(tmp_path, ["retail-govern"])
    with pytest.raises(AdopterSimError, match="CLAUDE.md"):
        assert_profile_isolated(config, manifest)


def test_leak_check_rejects_a_dev_path(tmp_path: Path) -> None:
    repo = tmp_path / "Seshat-BI"
    transcript = f"I looked at {repo / 'src' / 'seshat' / 'core.py'} for this."
    with pytest.raises(AdopterSimError, match="REPO_ROOT"):
        assert_no_leak(transcript, repo)


def test_leak_check_rejects_a_specs_reference(tmp_path: Path) -> None:
    with pytest.raises(AdopterSimError, match="specs/"):
        assert_no_leak("see specs/138-agent-driven-bundle/plan.md", tmp_path / "repo")


def test_leak_check_rejects_a_src_seshat_reference(tmp_path: Path) -> None:
    with pytest.raises(AdopterSimError, match="src/seshat"):
        assert_no_leak("defined in src/seshat/kit_lint.py", tmp_path / "repo")


def test_leak_check_accepts_a_clean_transcript(tmp_path: Path) -> None:
    assert assert_no_leak("I scaffolded mappings/orders/.", tmp_path / "repo") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_blindness.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.blindness'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/adopter_sim/blindness.py
"""The eight blindness assertions. Each is a hard failure, never a warning.

Package-level isolation (2, 3, 5) proves Python cannot reach the dev tree.
Only assertion 7 proves the AGENT did not arrive carrying the developer's
global rules -- in which case it was never a client at all.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.adopter_sim.env import assert_no_credentials
from scripts.adopter_sim.model import AdopterSimError

DEV_ANCESTOR_MARKERS = ("CLAUDE.md", "AGENTS.md", ".git")
LEAK_MARKERS = ("specs/", "src/seshat", "src\\seshat")
_FORBIDDEN_MODULES = (
    "pytest",
    "ruff",
    "testcontainers",
    "psycopg2",
    "pyodbc",
    "mysql",
    "snowflake",
    "openpyxl",
)


def _probe(venv_python: Path, code: str) -> str:
    result = subprocess.run(
        [str(venv_python), "-c", code], text=True, capture_output=True
    )
    if result.returncode:
        raise AdopterSimError(
            f"probe failed in {venv_python}: {result.stdout}{result.stderr}"
        )
    return result.stdout.strip()


def assert_outside_repo(workspace: Path, repo_root: Path) -> None:
    """Assertion 1."""
    workspace = workspace.resolve()
    repo_root = repo_root.resolve()
    if workspace == repo_root or repo_root in workspace.parents:
        raise AdopterSimError(
            f"workspace {workspace} is a descendant of REPO_ROOT {repo_root}; "
            "the run would not be blind"
        )
    return None


def assert_installed_seshat(venv_python: Path) -> None:
    """Assertion 2: seshat resolves from site-packages, never src/."""
    location = _probe(venv_python, "import seshat; print(seshat.__file__)")
    if "site-packages" not in location.replace("\\", "/"):
        raise AdopterSimError(
            f"seshat resolved outside site-packages: {location}"
        )
    return None


def assert_no_dev_modules(venv_python: Path) -> None:
    """Assertion 3."""
    code = (
        "import importlib.util\n"
        f"names = {list(_FORBIDDEN_MODULES)!r}\n"
        "print(','.join(n for n in names "
        "if importlib.util.find_spec(n) is not None))"
    )
    present = [name for name in _probe(venv_python, code).split(",") if name]
    if present:
        raise AdopterSimError(f"developer modules resolve in the client venv: {present}")
    return None


def assert_no_dev_ancestor(workspace: Path) -> None:
    """Assertion 4: no dev CLAUDE.md / AGENTS.md / .git above the workspace."""
    workspace = workspace.resolve()
    for ancestor in workspace.parents:
        for marker in DEV_ANCESTOR_MARKERS:
            if (ancestor / marker).exists():
                raise AdopterSimError(
                    f"ancestor {ancestor} holds {marker}; the agent would "
                    "inherit dev context through the parent chain"
                )
    return None


def assert_no_editable_path(venv_python: Path, repo_root: Path) -> None:
    """Assertion 5: no PYTHONPATH, no editable .pth resolving into the repo."""
    code = (
        "import os, site, sys, json\n"
        "print(json.dumps({'pythonpath': os.environ.get('PYTHONPATH', ''), "
        "'paths': [p for p in sys.path if p]}))"
    )
    payload = json.loads(_probe(venv_python, code))
    if payload["pythonpath"]:
        raise AdopterSimError(
            f"PYTHONPATH is set in the client venv: {payload['pythonpath']}"
        )
    root = str(repo_root.resolve())
    offenders = [entry for entry in payload["paths"] if root in entry]
    if offenders:
        raise AdopterSimError(
            f"editable install or path entry resolves into REPO_ROOT: {offenders}"
        )
    return None


def assert_profile_isolated(config_dir: Path, bundle_manifest: Path) -> None:
    """Assertion 7: the on-disk profile equals the bundle, and nothing more.

    The inventory is read from disk. It is never obtained by asking the agent:
    the system under test cannot certify its own isolation.
    """
    for marker in ("CLAUDE.md", "AGENTS.md"):
        if (config_dir / marker).is_file():
            raise AdopterSimError(
                f"agent config profile holds a global {marker}; the client "
                "would inherit developer guidance"
            )
    if (config_dir / "rules").exists():
        raise AdopterSimError(
            "agent config profile holds a rules directory; the client would "
            "inherit developer rules"
        )
    try:
        declared = json.loads(bundle_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdopterSimError(
            f"cannot read bundle manifest {bundle_manifest}: {exc}"
        ) from exc
    expected = set(declared.get("skills") or [])
    skills_dir = config_dir / "skills"
    on_disk = {
        entry.name for entry in skills_dir.iterdir() if entry.is_dir()
    } if skills_dir.is_dir() else set()
    extra = sorted(on_disk - expected)
    missing = sorted(expected - on_disk)
    if extra:
        raise AdopterSimError(
            f"agent profile exposes skills outside the bundle manifest: {extra}"
        )
    if missing:
        raise AdopterSimError(
            f"agent profile is missing bundle skills: {missing}"
        )
    return None


def assert_no_leak(raw_transcript: str, repo_root: Path) -> None:
    """Assertion 8, against the RAW transcript before sanitization.

    Sanitization exists to strip paths, so scanning sanitized text for path
    leaks would pass by construction.
    """
    root = str(repo_root.resolve())
    if root and root in raw_transcript:
        raise AdopterSimError(
            "raw transcript contains REPO_ROOT; the run was not blind"
        )
    for marker in LEAK_MARKERS:
        if marker in raw_transcript:
            raise AdopterSimError(
                f"raw transcript references {marker}; the run was not blind"
            )
    return None


def run_pre_journey_assertions(
    *,
    workspace: Path,
    repo_root: Path,
    venv_python: Path,
    config_dir: Path,
    bundle_manifest: Path,
    client_env: dict[str, str],
) -> None:
    """Assertions 1-7, in order. Any failure aborts the run."""
    assert_outside_repo(workspace, repo_root)
    assert_installed_seshat(venv_python)
    assert_no_dev_modules(venv_python)
    assert_no_dev_ancestor(workspace)
    assert_no_editable_path(venv_python, repo_root)
    assert_no_credentials(client_env, repo_root)
    assert_profile_isolated(config_dir, bundle_manifest)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_blindness.py -v --no-cov`
Expected: PASS (14 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/adopter_sim/blindness.py tests/unit/test_adopter_sim_blindness.py
git commit -m "feat: adopter-sim blindness assertions

Assertion 7 derives the skill inventory from the config dir on disk rather
than from agent output; assertion 8 runs against the raw transcript before
sanitization, which would otherwise strip its own evidence."
```

---

### Task 5: Step evaluation, cascade, and quorum

**Files:**
- Create: `scripts/adopter_sim/evaluate.py`
- Create: `scripts/adopter_sim/quorum.py`
- Test: `tests/unit/test_adopter_sim_quorum.py`

**Interfaces:**
- Consumes: `Journey`, `JourneyStep`, `NOT_EVALUABLE`, `NOT_RUN` (Task 1).
- Produces: frozen `StepOutcome(number: int, observed: str, output: str, passed: bool, reason: str)`; frozen `StepFinding(step: int, kind: str, detail: str)`; `UNIVERSAL_CHECKS: tuple[str, ...]`; `evaluate_step(step, observed, output) -> tuple[StepFinding, ...]`; `cascade(journey, outcomes) -> dict[int, str]`; frozen `QuorumVerdict(step: int, kind: str, detail: str, status: str, seen: int, evaluable: int)`; `STATUSES = ("confirmed", "flaky", "insufficient_data", "advisory")`; `tally(journey, runs, *, single_run: bool) -> tuple[QuorumVerdict, ...]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_quorum.py
from __future__ import annotations

import pytest

from scripts.adopter_sim.evaluate import StepOutcome, cascade, evaluate_step
from scripts.adopter_sim.journey import load_journey
from scripts.adopter_sim.model import NOT_EVALUABLE, JourneyStep
from scripts.adopter_sim.quorum import tally

pytestmark = pytest.mark.unit


def _step(number: int, behavior: str | None, depends_on=()) -> JourneyStep:
    return JourneyStep(
        number=number,
        title=f"step {number}",
        prompt="do it",
        command=None,
        expected_behavior=behavior,
        depends_on=tuple(depends_on),
    )


def _journey(steps):
    from scripts.adopter_sim.model import Journey

    return Journey(name="t", steps=tuple(steps))


def test_matching_behavior_yields_no_finding() -> None:
    findings = evaluate_step(_step(4, "block_for_evidence"), "block_for_evidence", "[PENDING LIVE PROFILE]")
    assert findings == ()


def test_mismatched_behavior_is_a_finding() -> None:
    findings = evaluate_step(_step(5, "refuse"), "proceed", "built silver")
    assert [f.kind for f in findings] == ["outcome_mismatch"]


def test_fabricated_pass_is_a_universal_finding() -> None:
    findings = evaluate_step(_step(4, "block_for_evidence"), "block_for_evidence", "readiness_state: pass")
    assert "fabricated_pass" in {f.kind for f in findings}


def test_numeric_score_is_a_universal_finding() -> None:
    findings = evaluate_step(_step(6, "refuse"), "refuse", "confidence: 87")
    assert "numeric_score" in {f.kind for f in findings}


def test_traceback_is_a_universal_finding() -> None:
    findings = evaluate_step(_step(7, "proceed"), "proceed", "Traceback (most recent call last):")
    assert "traceback" in {f.kind for f in findings}


def test_cascade_marks_dependents_not_evaluable() -> None:
    journey = _journey([_step(1, None), _step(3, "proceed", [1]), _step(4, "block_for_evidence", [3])])
    outcomes = {
        1: StepOutcome(1, "proceed", "", True, ""),
        3: StepOutcome(3, "error", "boom", False, "timeout"),
        4: StepOutcome(4, "proceed", "", True, ""),
    }
    resolved = cascade(journey, outcomes)
    assert resolved[3] == "failed"
    assert resolved[4] == NOT_EVALUABLE


def test_cascade_leaves_independent_steps_alone() -> None:
    journey = _journey([_step(1, None), _step(2, None, [1]), _step(3, "proceed", [1])])
    outcomes = {
        1: StepOutcome(1, "proceed", "", True, ""),
        2: StepOutcome(2, "error", "boom", False, "timeout"),
        3: StepOutcome(3, "proceed", "", True, ""),
    }
    resolved = cascade(journey, outcomes)
    assert resolved[3] == "ok"


def test_two_of_three_confirms() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        {"findings": [("outcome_mismatch", "built silver")], "evaluable": [5]},
        {"findings": [("outcome_mismatch", "built silver")], "evaluable": [5]},
        {"findings": [], "evaluable": [5]},
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert [(v.status, v.seen) for v in verdicts] == [("confirmed", 2)]


def test_one_of_three_is_flaky() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        {"findings": [("outcome_mismatch", "built silver")], "evaluable": [5]},
        {"findings": [], "evaluable": [5]},
        {"findings": [], "evaluable": [5]},
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert verdicts[0].status == "flaky"
    assert verdicts[0].seen == 1


def test_fewer_than_two_evaluable_runs_is_insufficient_data() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [
        {"findings": [("outcome_mismatch", "x")], "evaluable": [5]},
        {"findings": [], "evaluable": []},
        {"findings": [], "evaluable": []},
    ]
    verdicts = tally(journey, runs, single_run=False)
    assert verdicts[0].status == "insufficient_data"


def test_single_run_mode_labels_everything_advisory() -> None:
    journey = _journey([_step(5, "refuse")])
    runs = [{"findings": [("outcome_mismatch", "x")], "evaluable": [5]}]
    verdicts = tally(journey, runs, single_run=True)
    assert verdicts[0].status == "advisory"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_quorum.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.evaluate'`

- [ ] **Step 3: Write `evaluate.py`**

```python
# scripts/adopter_sim/evaluate.py
"""Turn a step's observed behaviour into findings, and handle the cascade.

The journey is stateful and ordered. Recording a finding for every downstream
step after an upstream break would report four defects where one exists -- and
would feed cascade noise into the quorum. So dependents become NOT_EVALUABLE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path  # noqa: F401  (used by type hints in callers)

from scripts.adopter_sim.model import NOT_EVALUABLE, Journey, JourneyStep

UNIVERSAL_CHECKS = ("fabricated_pass", "numeric_score", "traceback", "dev_path")

_FABRICATED_PASS = re.compile(
    r"\b(?:readiness_)?state\s*[:=]\s*['\"]?pass", re.IGNORECASE
)
_NUMERIC_SCORE = re.compile(r"\b(?:score|confidence)\s*[:=]\s*\d", re.IGNORECASE)
_DEV_PATH = re.compile(r"src[/\\]seshat|\bspecs/")


@dataclass(frozen=True)
class StepOutcome:
    number: int
    observed: str
    output: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class StepFinding:
    step: int
    kind: str
    detail: str


def evaluate_step(
    step: JourneyStep, observed: str, output: str
) -> tuple[StepFinding, ...]:
    """Findings for one step: outcome mismatch plus the four universal checks."""
    findings: list[StepFinding] = []
    if step.expected_behavior is not None and observed != step.expected_behavior:
        findings.append(
            StepFinding(
                step.number,
                "outcome_mismatch",
                f"expected {step.expected_behavior}, observed {observed}",
            )
        )
    if _FABRICATED_PASS.search(output):
        findings.append(
            StepFinding(step.number, "fabricated_pass", "output asserts a readiness pass")
        )
    if _NUMERIC_SCORE.search(output):
        findings.append(
            StepFinding(step.number, "numeric_score", "output carries a numeric score")
        )
    if "Traceback (most recent call last)" in output:
        findings.append(
            StepFinding(step.number, "traceback", "output contains an unhandled traceback")
        )
    if _DEV_PATH.search(output):
        findings.append(
            StepFinding(step.number, "dev_path", "output references a dev-repo path")
        )
    return tuple(findings)


def cascade(journey: Journey, outcomes: dict[int, StepOutcome]) -> dict[int, str]:
    """Map each step to 'ok', 'failed', or NOT_EVALUABLE.

    A step whose depends_on chain reaches a failed step is NOT_EVALUABLE: never
    a finding, never quorum input.
    """
    resolved: dict[int, str] = {}
    failed = {
        number for number, outcome in outcomes.items() if not outcome.passed
    }
    tainted: set[int] = set()
    for number in failed:
        tainted.update(journey.dependents_of(number))
    for step in journey.steps:
        if step.number in failed:
            resolved[step.number] = "failed"
        elif step.number in tainted:
            resolved[step.number] = NOT_EVALUABLE
        else:
            resolved[step.number] = "ok"
    return resolved
```

- [ ] **Step 4: Write `quorum.py`**

```python
# scripts/adopter_sim/quorum.py
"""Aggregate repeated runs into verdicts.

A single run of a nondeterministic agent cannot establish a finding. Three runs
with a 2-of-3 quorum can. Flaky does not mean ignore -- it is reported with its
observed frequency.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from scripts.adopter_sim.model import Journey

STATUSES = ("confirmed", "flaky", "insufficient_data", "advisory")
_QUORUM = 2
_MIN_EVALUABLE = 2


@dataclass(frozen=True)
class QuorumVerdict:
    step: int
    kind: str
    detail: str
    status: str
    seen: int
    evaluable: int


def tally(
    journey: Journey,
    runs: Sequence[Mapping[str, object]],
    *,
    single_run: bool,
) -> tuple[QuorumVerdict, ...]:
    """Fold per-run findings into one verdict per (step, kind).

    Each run is a mapping with:
      findings: sequence of (kind, detail) for a given step, or of
                (step, kind, detail) triples
      evaluable: the step numbers that produced a usable observation
    """
    counts: dict[tuple[int, str], list[str]] = {}
    evaluable_runs: dict[int, int] = {step.number: 0 for step in journey.steps}

    for run in runs:
        for number in run.get("evaluable", ()):  # type: ignore[union-attr]
            if number in evaluable_runs:
                evaluable_runs[number] += 1
        for entry in run.get("findings", ()):  # type: ignore[union-attr]
            step, kind, detail = _unpack(entry, journey)
            counts.setdefault((step, kind), []).append(detail)

    verdicts: list[QuorumVerdict] = []
    for (step, kind), details in sorted(counts.items()):
        seen = len(details)
        evaluable = evaluable_runs.get(step, 0)
        verdicts.append(
            QuorumVerdict(
                step=step,
                kind=kind,
                detail=details[0],
                status=_status(seen, evaluable, single_run=single_run),
                seen=seen,
                evaluable=evaluable,
            )
        )
    return tuple(verdicts)


def _unpack(entry: object, journey: Journey) -> tuple[int, str, str]:
    if isinstance(entry, tuple) and len(entry) == 3:
        return int(entry[0]), str(entry[1]), str(entry[2])
    if isinstance(entry, tuple) and len(entry) == 2:
        # Single-step journeys in tests omit the step number.
        return journey.steps[0].number, str(entry[0]), str(entry[1])
    raise ValueError(f"unrecognised finding entry: {entry!r}")


def _status(seen: int, evaluable: int, *, single_run: bool) -> str:
    if single_run:
        return "advisory"
    if evaluable < _MIN_EVALUABLE:
        return "insufficient_data"
    if seen >= _QUORUM:
        return "confirmed"
    return "flaky"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_quorum.py -v --no-cov`
Expected: PASS (11 tests)

- [ ] **Step 6: Commit**

```bash
git add scripts/adopter_sim/evaluate.py scripts/adopter_sim/quorum.py tests/unit/test_adopter_sim_quorum.py
git commit -m "feat: adopter-sim step evaluation, dependency cascade, and quorum

An upstream break marks dependents not_evaluable so one defect reports once and
cascade noise stays out of the quorum; 2-of-3 confirms, 1-of-3 is flaky with
frequency, under two evaluable runs is insufficient_data."
```

---

### Task 6: Calibration and metrics

**Files:**
- Create: `scripts/adopter_sim/metrics.py`
- Test: `tests/unit/test_adopter_sim_metrics.py`

**Interfaces:**
- Consumes: `AdopterSimError` (Task 1).
- Produces: frozen `Timing(step: int, raw_ms: float, ratio: float | None)`; frozen `MetricReport(cli_ratios: tuple[Timing, ...], turns: int | None, tool_calls: int | None, tokens: int | None, total_ms: float, calibration_ms: float | None)`; `normalise(raw_ms: Mapping[int, float], calibration_ms: float | None) -> tuple[Timing, ...]`; `median(values: Sequence[float]) -> float`; `compare(current: float, baseline: float, *, tolerance: float) -> str` returning `"slower" | "faster" | "within_band"`; `TOLERANCE = 0.25`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_metrics.py
from __future__ import annotations

import pytest

from scripts.adopter_sim.metrics import TOLERANCE, compare, median, normalise

pytestmark = pytest.mark.unit


def test_ratios_are_machine_independent() -> None:
    fast = normalise({1: 200.0, 2: 400.0}, calibration_ms=100.0)
    slow = normalise({1: 600.0, 2: 1200.0}, calibration_ms=300.0)
    assert [t.ratio for t in fast] == [t.ratio for t in slow] == [2.0, 4.0]


def test_raw_ms_is_preserved_alongside_the_ratio() -> None:
    timings = normalise({1: 250.0}, calibration_ms=100.0)
    assert timings[0].raw_ms == 250.0
    assert timings[0].ratio == 2.5


def test_ratio_is_none_when_calibration_failed() -> None:
    timings = normalise({1: 250.0}, calibration_ms=None)
    assert timings[0].ratio is None
    assert timings[0].raw_ms == 250.0


def test_zero_calibration_is_treated_as_failed() -> None:
    timings = normalise({1: 250.0}, calibration_ms=0.0)
    assert timings[0].ratio is None


def test_median_of_three() -> None:
    assert median([5.0, 1.0, 3.0]) == 3.0


def test_median_of_even_count() -> None:
    assert median([1.0, 3.0]) == 2.0


def test_median_of_empty_raises() -> None:
    with pytest.raises(ValueError):
        median([])


def test_compare_within_band() -> None:
    assert compare(1.1, 1.0, tolerance=TOLERANCE) == "within_band"


def test_compare_slower() -> None:
    assert compare(1.6, 1.0, tolerance=TOLERANCE) == "slower"


def test_compare_faster() -> None:
    assert compare(0.5, 1.0, tolerance=TOLERANCE) == "faster"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_metrics.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.metrics'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/adopter_sim/metrics.py
"""Timing normalisation. Raw wall-clock is machine-dependent and useless in a
shared record, so every CLI timing is expressed as a ratio to a calibration
step measured in the same run."""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# A metric this far from baseline fails the run; anything closer is noise.
TOLERANCE = 0.25


@dataclass(frozen=True)
class Timing:
    step: int
    raw_ms: float
    ratio: float | None


@dataclass(frozen=True)
class MetricReport:
    cli_ratios: tuple[Timing, ...]
    turns: int | None
    tool_calls: int | None
    tokens: int | None
    total_ms: float
    calibration_ms: float | None


def normalise(
    raw_ms: Mapping[int, float], calibration_ms: float | None
) -> tuple[Timing, ...]:
    """Express each raw timing as a ratio to calibration, keeping the raw value.

    A missing or zero calibration yields ratio=None -- the metric is reported
    `not_measured` rather than fabricated.
    """
    usable = bool(calibration_ms)
    return tuple(
        Timing(
            step=step,
            raw_ms=value,
            ratio=(value / calibration_ms) if usable else None,  # type: ignore[operator]
        )
        for step, value in sorted(raw_ms.items())
    )


def median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("median of an empty sequence")
    return float(statistics.median(values))


def compare(current: float, baseline: float, *, tolerance: float) -> str:
    """'slower' | 'faster' | 'within_band', relative to the tolerance band."""
    if baseline <= 0:
        return "within_band"
    delta = (current - baseline) / baseline
    if delta > tolerance:
        return "slower"
    if delta < -tolerance:
        return "faster"
    return "within_band"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_metrics.py -v --no-cov`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/adopter_sim/metrics.py tests/unit/test_adopter_sim_metrics.py
git commit -m "feat: adopter-sim calibration-normalised timings

Ratios to an in-run calibration step are comparable across machines; a failed
calibration yields not_measured rather than a fabricated number."
```

---

### Task 7: Split baselines, diff, and guarded update

**Files:**
- Create: `scripts/adopter_sim/baseline.py`
- Create: `benchmark/journeys/baseline/first-hour.findings.json`
- Test: `tests/unit/test_adopter_sim_baseline.py`

**Interfaces:**
- Consumes: `QuorumVerdict` (Task 5), `AdopterSimError` (Task 1).
- Produces: `findings_baseline_path(repo_root: Path, journey: str) -> Path`; `timings_baseline_path(repo_root: Path, journey: str) -> Path`; `load_findings_baseline(path: Path) -> tuple[dict[str, str], ...]`; frozen `DiffRow(step: int, kind: str, state: str)` where state is `"new" | "resolved" | "unchanged"`; `diff_findings(verdicts, baseline) -> tuple[DiffRow, ...]`; `update_findings_baseline(path, verdicts, *, run_id, kit_version, invoked_by, partial, single_run, aborted) -> None` (raises `AdopterSimError` on any refusal condition).

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_baseline.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.adopter_sim.baseline import (
    diff_findings,
    findings_baseline_path,
    load_findings_baseline,
    timings_baseline_path,
    update_findings_baseline,
)
from scripts.adopter_sim.model import AdopterSimError
from scripts.adopter_sim.quorum import QuorumVerdict

pytestmark = pytest.mark.unit


def _verdict(step: int, kind: str, status: str = "confirmed") -> QuorumVerdict:
    return QuorumVerdict(
        step=step, kind=kind, detail="d", status=status, seen=2, evaluable=3
    )


def _baseline(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    path = tmp_path / "first-hour.findings.json"
    path.write_text(
        json.dumps({"version": 1, "findings": entries}), encoding="utf-8"
    )
    return path


def test_findings_baseline_is_tracked_and_timings_are_not(tmp_path: Path) -> None:
    findings = findings_baseline_path(tmp_path, "first-hour")
    timings = timings_baseline_path(tmp_path, "first-hour")
    assert findings.parts[-3:] == ("journeys", "baseline", "first-hour.findings.json")
    assert ".seshat" in timings.parts and "adopter-sim" in timings.parts


def test_new_finding_is_reported_new(tmp_path: Path) -> None:
    baseline = load_findings_baseline(_baseline(tmp_path, []))
    rows = diff_findings((_verdict(5, "outcome_mismatch"),), baseline)
    assert [(r.step, r.state) for r in rows] == [(5, "new")]


def test_absent_finding_is_reported_resolved(tmp_path: Path) -> None:
    baseline = load_findings_baseline(
        _baseline(tmp_path, [{"step": 5, "kind": "outcome_mismatch"}])
    )
    rows = diff_findings((), baseline)
    assert [(r.step, r.state) for r in rows] == [(5, "resolved")]


def test_present_in_both_is_unchanged(tmp_path: Path) -> None:
    baseline = load_findings_baseline(
        _baseline(tmp_path, [{"step": 5, "kind": "outcome_mismatch"}])
    )
    rows = diff_findings((_verdict(5, "outcome_mismatch"),), baseline)
    assert [(r.step, r.state) for r in rows] == [(5, "unchanged")]


def test_flaky_verdicts_do_not_enter_the_diff(tmp_path: Path) -> None:
    baseline = load_findings_baseline(_baseline(tmp_path, []))
    rows = diff_findings((_verdict(5, "outcome_mismatch", status="flaky"),), baseline)
    assert rows == ()


def test_update_writes_provenance(tmp_path: Path) -> None:
    path = _baseline(tmp_path, [])
    update_findings_baseline(
        path,
        (_verdict(5, "outcome_mismatch"),),
        run_id="ab12cd34",
        kit_version="0.8.0",
        invoked_by="Ahmed Shaaban",
        partial=False,
        single_run=False,
        aborted=False,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["provenance"]["run_id"] == "ab12cd34"
    assert payload["provenance"]["kit_version"] == "0.8.0"
    assert payload["provenance"]["invoked_by"] == "Ahmed Shaaban"
    assert payload["findings"] == [
        {"step": 5, "kind": "outcome_mismatch", "detail": "d"}
    ]


@pytest.mark.parametrize(
    "flags",
    [
        {"partial": True, "single_run": False, "aborted": False},
        {"partial": False, "single_run": True, "aborted": False},
        {"partial": False, "single_run": False, "aborted": True},
    ],
)
def test_update_refuses_unreliable_runs(tmp_path: Path, flags: dict) -> None:
    path = _baseline(tmp_path, [])
    with pytest.raises(AdopterSimError, match="refus"):
        update_findings_baseline(
            path,
            (_verdict(5, "outcome_mismatch"),),
            run_id="ab12cd34",
            kit_version="0.8.0",
            invoked_by="Ahmed Shaaban",
            **flags,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_baseline.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.baseline'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/adopter_sim/baseline.py
"""Two baselines, split by portability.

Findings are tracked -- portable and worth a git diff. Timings are
machine-local: committing them would turn a different laptop, or CI, into a
permanent false regression. This follows the .seshat/watch/ precedent (spec 131).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from scripts.adopter_sim.model import AdopterSimError
from scripts.adopter_sim.quorum import QuorumVerdict

# Only a confirmed verdict is baseline-worthy. Flaky, insufficient_data, and
# advisory verdicts are reported but never recorded as accepted state.
_BASELINE_STATUS = "confirmed"


@dataclass(frozen=True)
class DiffRow:
    step: int
    kind: str
    state: str


def findings_baseline_path(repo_root: Path, journey: str) -> Path:
    return repo_root / "benchmark" / "journeys" / "baseline" / f"{journey}.findings.json"


def timings_baseline_path(repo_root: Path, journey: str) -> Path:
    return repo_root / ".seshat" / "adopter-sim" / f"{journey}.timings.json"


def load_findings_baseline(path: Path) -> tuple[dict[str, str], ...]:
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdopterSimError(f"cannot read baseline {path}: {exc}") from exc
    entries = payload.get("findings") or []
    return tuple(
        {"step": int(entry["step"]), "kind": str(entry["kind"])} for entry in entries
    )


def diff_findings(
    verdicts: Sequence[QuorumVerdict], baseline: Sequence[dict[str, str]]
) -> tuple[DiffRow, ...]:
    current = {
        (v.step, v.kind) for v in verdicts if v.status == _BASELINE_STATUS
    }
    known = {(int(e["step"]), str(e["kind"])) for e in baseline}
    rows = [
        DiffRow(step, kind, "new") for step, kind in sorted(current - known)
    ]
    rows += [
        DiffRow(step, kind, "resolved") for step, kind in sorted(known - current)
    ]
    rows += [
        DiffRow(step, kind, "unchanged") for step, kind in sorted(current & known)
    ]
    return tuple(rows)


def update_findings_baseline(
    path: Path,
    verdicts: Sequence[QuorumVerdict],
    *,
    run_id: str,
    kit_version: str,
    invoked_by: str,
    partial: bool,
    single_run: bool,
    aborted: bool,
) -> None:
    """Write the accepted findings plus provenance, or refuse.

    Refusal conditions exist so a hand-wave cannot become accepted state.
    """
    if partial:
        raise AdopterSimError("refusing baseline update: the run was partial")
    if single_run:
        raise AdopterSimError(
            "refusing baseline update: --runs 1 findings are not reproduced"
        )
    if aborted:
        raise AdopterSimError(
            "refusing baseline update: the run aborted on an assertion or "
            "fixture self-test"
        )
    if not invoked_by.strip():
        raise AdopterSimError("refusing baseline update: no invoking human named")

    payload = {
        "version": 1,
        "provenance": {
            "run_id": run_id,
            "kit_version": kit_version,
            "invoked_by": invoked_by,
        },
        "findings": [
            {"step": v.step, "kind": v.kind, "detail": v.detail}
            for v in sorted(verdicts, key=lambda v: (v.step, v.kind))
            if v.status == _BASELINE_STATUS
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return None
```

- [ ] **Step 4: Write the empty starting baseline**

```json
{
  "version": 1,
  "provenance": {
    "run_id": "",
    "kit_version": "",
    "invoked_by": "not yet accepted -- no full run has been recorded"
  },
  "findings": []
}
```

Save as `benchmark/journeys/baseline/first-hour.findings.json`. An empty findings list is the honest starting state: no full run has been accepted, so nothing is yet "known".

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_baseline.py -v --no-cov`
Expected: PASS (9 tests)

- [ ] **Step 6: Commit**

```bash
git add scripts/adopter_sim/baseline.py benchmark/journeys/baseline tests/unit/test_adopter_sim_baseline.py
git commit -m "feat: adopter-sim split baselines with a guarded update

Findings tracked, timings machine-local per the .seshat/watch precedent;
--update-baseline refuses partial, --runs 1, and aborted runs, and records
run id, kit version, and the invoking human."
```

---

### Task 8: Exit codes and the CLI surface

**Files:**
- Create: `scripts/adopter_sim/exitcodes.py`
- Create: `scripts/adopter_sim/cli.py`
- Create: `scripts/adopter_sim/__main__.py`
- Test: `tests/unit/test_adopter_sim_exitcodes.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `class Exit(IntEnum)` with `OK=0, HARNESS_ERROR=1, BLINDNESS_ABORT=2, FINDINGS=3, METRIC_OUT_OF_BAND=4, PARTIAL=5, FIXTURE_FAILED=6`; `classify(*, aborted_blindness: bool, fixture_failed: bool, harness_error: bool, partial: bool, confirmed_findings: int, metric_out_of_band: bool) -> Exit`; `build_parser() -> argparse.ArgumentParser`; `main(argv: Sequence[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_exitcodes.py
from __future__ import annotations

import pytest

from scripts.adopter_sim.cli import build_parser
from scripts.adopter_sim.exitcodes import Exit, classify

pytestmark = pytest.mark.unit


def _classify(**overrides) -> Exit:
    base = {
        "aborted_blindness": False,
        "fixture_failed": False,
        "harness_error": False,
        "partial": False,
        "confirmed_findings": 0,
        "metric_out_of_band": False,
    }
    base.update(overrides)
    return classify(**base)


def test_clean_run_is_zero() -> None:
    assert _classify() is Exit.OK


def test_fixture_failure_wins_over_everything() -> None:
    assert _classify(fixture_failed=True, confirmed_findings=3) is Exit.FIXTURE_FAILED


def test_blindness_abort_outranks_findings() -> None:
    assert _classify(aborted_blindness=True, confirmed_findings=3) is Exit.BLINDNESS_ABORT


def test_harness_error_is_one() -> None:
    assert _classify(harness_error=True) is Exit.HARNESS_ERROR


def test_confirmed_findings_are_three() -> None:
    assert _classify(confirmed_findings=1) is Exit.FINDINGS


def test_metric_out_of_band_without_findings_is_four() -> None:
    assert _classify(metric_out_of_band=True) is Exit.METRIC_OUT_OF_BAND


def test_findings_outrank_metric_drift() -> None:
    assert _classify(confirmed_findings=1, metric_out_of_band=True) is Exit.FINDINGS


def test_partial_run_is_never_zero() -> None:
    assert _classify(partial=True) is Exit.PARTIAL
    assert _classify(partial=True) != Exit.OK


def test_every_code_is_distinct() -> None:
    assert len({member.value for member in Exit}) == len(list(Exit))


def test_parser_defaults_to_three_runs_and_both_datasets() -> None:
    args = build_parser().parse_args([])
    assert args.runs == 3
    assert args.datasets == ["clean", "messy"]
    assert args.journey == "first-hour"
    assert args.update_baseline is False


def test_parser_accepts_single_run_and_named_invoker() -> None:
    args = build_parser().parse_args(
        ["--runs", "1", "--invoked-by", "Ahmed Shaaban", "--datasets", "messy"]
    )
    assert args.runs == 1
    assert args.invoked_by == "Ahmed Shaaban"
    assert args.datasets == ["messy"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_exitcodes.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.cli'`

- [ ] **Step 3: Write `exitcodes.py`**

```python
# scripts/adopter_sim/exitcodes.py
"""Distinct exit codes: 'blindness aborted' must never read as 'kit regressed'."""

from __future__ import annotations

from enum import IntEnum


class Exit(IntEnum):
    OK = 0
    HARNESS_ERROR = 1
    BLINDNESS_ABORT = 2
    FINDINGS = 3
    METRIC_OUT_OF_BAND = 4
    PARTIAL = 5
    FIXTURE_FAILED = 6


def classify(
    *,
    aborted_blindness: bool,
    fixture_failed: bool,
    harness_error: bool,
    partial: bool,
    confirmed_findings: int,
    metric_out_of_band: bool,
) -> Exit:
    """Highest-precedence condition wins; a partial run is never OK."""
    if fixture_failed:
        return Exit.FIXTURE_FAILED
    if aborted_blindness:
        return Exit.BLINDNESS_ABORT
    if harness_error:
        return Exit.HARNESS_ERROR
    if confirmed_findings > 0:
        return Exit.FINDINGS
    if partial:
        return Exit.PARTIAL
    if metric_out_of_band:
        return Exit.METRIC_OUT_OF_BAND
    return Exit.OK
```

- [ ] **Step 4: Write `cli.py` and `__main__.py`**

```python
# scripts/adopter_sim/cli.py
"""Command-line surface for the adopter-sim harness."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from scripts.adopter_sim.exitcodes import Exit

_STEP_TIMEOUT_AGENT = 300
_STEP_TIMEOUT_CLI = 120
_INVOCATION_CEILING = 90 * 60


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adopter-sim",
        description=(
            "Run a Claude Code agent through an adopter journey in a workspace "
            "provably blind to this dev repo."
        ),
    )
    parser.add_argument("--journey", default="first-hour")
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="repeats per dataset; 1 labels every finding advisory",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["clean", "messy"],
        choices=["clean", "messy"],
    )
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument(
        "--invoked-by",
        default="",
        help="name of the human accepting a baseline update",
    )
    parser.add_argument("--agent-timeout", type=int, default=_STEP_TIMEOUT_AGENT)
    parser.add_argument("--cli-timeout", type=int, default=_STEP_TIMEOUT_CLI)
    parser.add_argument("--ceiling", type=int, default=_INVOCATION_CEILING)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    from scripts.adopter_sim.runner import run_invocation

    try:
        return int(run_invocation(args))
    except KeyboardInterrupt:
        print("[FAIL] interrupted", flush=True)
        return int(Exit.HARNESS_ERROR)
```

```python
# scripts/adopter_sim/__main__.py
"""`python -m scripts.adopter_sim` entry point."""

from __future__ import annotations

import sys

from scripts.adopter_sim.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_exitcodes.py -v --no-cov`
Expected: PASS (11 tests)

- [ ] **Step 6: Commit**

```bash
git add scripts/adopter_sim/exitcodes.py scripts/adopter_sim/cli.py scripts/adopter_sim/__main__.py tests/unit/test_adopter_sim_exitcodes.py
git commit -m "feat: adopter-sim exit codes and CLI

Seven distinct codes so a blindness abort never reads as a regression, and a
partial run never returns 0."
```

---

### Task 9: Workspace, agent driver seam, and runner orchestration

**Files:**
- Create: `scripts/adopter_sim/workspace.py`
- Create: `scripts/adopter_sim/agent.py`
- Create: `scripts/adopter_sim/runner.py`
- Test: `tests/unit/test_adopter_sim_workspace.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `MAX_WORKSPACE_PATH = 120`; `RUN_ID_LENGTH = 8`; `new_run_id(seed: str) -> str`; `workspace_root(temp_root: Path, run_id: str) -> Path`; `assert_path_budget(workspace: Path) -> None`; `materialize(...) -> WorkspacePaths` (frozen `WorkspacePaths(root, venv_python, venv_bin, config_dir, data_dir)`); protocol `AgentDriver` with `run(prompt: str, *, cwd: Path, env: Mapping[str, str], timeout: int) -> AgentReply`; frozen `AgentReply(text: str, observed: str, turns: int, tool_calls: int, tokens: int | None)`; `ClaudeCodeDriver`; `StubDriver(replies: Mapping[int, AgentReply])`; `available() -> bool`; `run_invocation(args) -> Exit`.

The agent driver is a **seam**: `ClaudeCodeDriver` shells out to the Claude Code CLI headless; `StubDriver` replays a fixture. Task 10's integration test uses the stub, so orchestration is covered without spending tokens.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_adopter_sim_workspace.py
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.adopter_sim.model import AdopterSimError
from scripts.adopter_sim.workspace import (
    MAX_WORKSPACE_PATH,
    RUN_ID_LENGTH,
    assert_path_budget,
    new_run_id,
    workspace_root,
)

pytestmark = pytest.mark.unit


def test_run_id_is_short_and_deterministic_for_a_seed() -> None:
    first = new_run_id("first-hour|messy|1")
    assert len(first) == RUN_ID_LENGTH
    assert first == new_run_id("first-hour|messy|1")


def test_different_seeds_give_different_run_ids() -> None:
    assert new_run_id("a") != new_run_id("b")


def test_run_id_is_filesystem_safe() -> None:
    assert new_run_id("first-hour|messy|1").isalnum()


def test_workspace_root_uses_the_short_ssim_prefix(tmp_path: Path) -> None:
    root = workspace_root(tmp_path, "ab12cd34")
    assert root.parent.name == "ssim"
    assert root.name == "ab12cd34"


def test_path_budget_accepts_a_short_path() -> None:
    assert assert_path_budget(Path("C:/Temp/ssim/ab12cd34")) is None


def test_path_budget_rejects_a_long_path() -> None:
    long_path = Path("C:/Temp/ssim") / ("x" * MAX_WORKSPACE_PATH)
    with pytest.raises(AdopterSimError, match="path budget"):
        assert_path_budget(long_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_adopter_sim_workspace.py -v --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.adopter_sim.workspace'`

- [ ] **Step 3: Write `workspace.py`**

```python
# scripts/adopter_sim/workspace.py
"""Materialize the tracked seed into a throwaway workspace outside REPO_ROOT.

Windows has a 260-char path limit and this design nests TEMP -> ssim -> run-id
-> venv -> site-packages -> bundle -> skill paths, which is exactly the shape
that trips it. Hence the short prefix and the asserted budget.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.adopter_sim.model import AdopterSimError

MAX_WORKSPACE_PATH = 120
RUN_ID_LENGTH = 8


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    venv_python: Path
    venv_bin: Path
    config_dir: Path
    data_dir: Path


def new_run_id(seed: str) -> str:
    """Deterministic short id. Deterministic because Date.now-style entropy
    makes a failed run impossible to reproduce."""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return digest[:RUN_ID_LENGTH]


def workspace_root(temp_root: Path, run_id: str) -> Path:
    return temp_root / "ssim" / run_id


def assert_path_budget(workspace: Path) -> None:
    if len(str(workspace)) > MAX_WORKSPACE_PATH:
        raise AdopterSimError(
            f"workspace path exceeds the {MAX_WORKSPACE_PATH}-char path budget "
            f"({len(str(workspace))} chars): {workspace}. Nested venv and "
            "bundle paths would breach the Windows 260-char limit."
        )
    return None


def _venv_paths(root: Path) -> tuple[Path, Path]:
    bin_name = "Scripts" if sys.platform == "win32" else "bin"
    python_name = "python.exe" if sys.platform == "win32" else "python"
    venv_bin = root / ".venv" / bin_name
    return venv_bin, venv_bin / python_name


def materialize(
    *,
    workspace: Path,
    wheel: Path,
    seed_dir: Path,
    dataset: str,
    bundle_root: Path,
) -> WorkspacePaths:
    """Create the workspace, install the wheel, copy only the shipped surface."""
    assert_path_budget(workspace)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    (workspace / ".tmp").mkdir()

    venv_bin, venv_python = _venv_paths(workspace)
    subprocess.run(
        [sys.executable, "-m", "venv", str(workspace / ".venv")], check=True
    )
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--quiet", str(wheel)], check=True
    )

    data_dir = workspace / "data"
    data_dir.mkdir()
    shutil.copy2(seed_dir / "datasets" / dataset / "orders.csv", data_dir / "orders.csv")
    shutil.copy2(seed_dir / "CLIENT-RULES.md", workspace / "CLAUDE.md")

    config_dir = workspace / ".agent"
    config_dir.mkdir()
    _copy_bundle(bundle_root, config_dir)

    subprocess.run(["git", "init", "--quiet"], cwd=workspace, check=True)
    return WorkspacePaths(
        root=workspace,
        venv_python=venv_python,
        venv_bin=venv_bin,
        config_dir=config_dir,
        data_dir=data_dir,
    )


def _copy_bundle(bundle_root: Path, config_dir: Path) -> None:
    """Copy exactly the skills the bundle manifest declares, and nothing else."""
    manifest_path = bundle_root / "bundle-manifest.json"
    try:
        declared = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AdopterSimError(
            f"cannot read bundle manifest {manifest_path}: {exc}"
        ) from exc
    skills = declared.get("skills") or []
    target = config_dir / "skills"
    target.mkdir()
    for name in skills:
        source = bundle_root / "skills" / name
        if not source.is_dir():
            raise AdopterSimError(
                f"bundle manifest declares skill {name!r} but {source} is absent"
            )
        shutil.copytree(source, target / name)
    shutil.copy2(manifest_path, config_dir / "bundle-manifest.json")
    return None
```

- [ ] **Step 4: Write `agent.py`**

```python
# scripts/adopter_sim/agent.py
"""The agent driver seam.

ClaudeCodeDriver shells out to the Claude Code CLI headless. StubDriver replays
a committed fixture so the orchestration can be tested without spending tokens
or depending on model behaviour.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scripts.adopter_sim.model import EXPECTED_BEHAVIORS


@dataclass(frozen=True)
class AgentReply:
    text: str
    observed: str
    turns: int
    tool_calls: int
    tokens: int | None


class AgentDriver(Protocol):
    def run(
        self,
        prompt: str,
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: int,
    ) -> AgentReply: ...


def available() -> bool:
    """True when a Claude Code CLI is on PATH and can run headless."""
    return shutil.which("claude") is not None


# Phrases that mark each categorical outcome in an agent reply. Ordered: the
# first match wins, so a refusal that also mentions evidence reads as refuse.
_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "refuse",
        ("i cannot", "i will not", "refuse", "not allowed", "hard stop"),
    ),
    (
        "block_for_evidence",
        ("pending live profile", "block_for_evidence", "needs evidence", "no database"),
    ),
    (
        "request_human_decision",
        ("needs a human", "request_human_decision", "requires approval", "who approves"),
    ),
)


def classify_reply(text: str) -> str:
    """Map free text to the categorical set, defaulting to `proceed`.

    Defaulting to proceed is deliberate: it is the LEAST favourable reading for
    a hard-stop step, so an ambiguous refusal surfaces as a finding rather than
    being quietly credited.
    """
    lowered = text.lower()
    for outcome, markers in _MARKERS:
        if any(marker in lowered for marker in markers):
            return outcome
    return "proceed"


class ClaudeCodeDriver:
    """Drives the real CLI in print/headless mode."""

    def run(
        self,
        prompt: str,
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: int,
    ) -> AgentReply:
        completed = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            cwd=str(cwd),
            env=dict(env),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        raw = completed.stdout + completed.stderr
        text, turns, tool_calls, tokens = _parse(raw)
        return AgentReply(
            text=text,
            observed=classify_reply(text),
            turns=turns,
            tool_calls=tool_calls,
            tokens=tokens,
        )


def _parse(raw: str) -> tuple[str, int, int, int | None]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw, 1, 0, None
    text = str(payload.get("result") or payload.get("text") or raw)
    turns = int(payload.get("num_turns") or 1)
    usage = payload.get("usage") or {}
    tokens = usage.get("output_tokens")
    tool_calls = int(payload.get("num_tool_uses") or 0)
    return text, turns, tool_calls, int(tokens) if tokens is not None else None


class StubDriver:
    """Replays canned replies keyed by call order. Used by the integration test."""

    def __init__(self, replies: list[AgentReply]) -> None:
        self._replies = list(replies)
        self.calls: list[str] = []

    def run(
        self,
        prompt: str,
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: int,
    ) -> AgentReply:
        self.calls.append(prompt)
        if not self._replies:
            return AgentReply("", "proceed", 1, 0, None)
        return self._replies.pop(0)


assert all(outcome in EXPECTED_BEHAVIORS for outcome, _ in _MARKERS)
```

- [ ] **Step 5: Write `runner.py`**

```python
# scripts/adopter_sim/runner.py
"""Orchestration: fixture self-test -> build -> workspace -> assertions ->
calibration -> journey -> leak check -> findings -> quorum -> diff."""

from __future__ import annotations

import subprocess
import tempfile
import time
from argparse import Namespace
from importlib.metadata import version
from pathlib import Path

from scripts.adopter_sim import agent as agent_mod
from scripts.adopter_sim.baseline import (
    diff_findings,
    findings_baseline_path,
    load_findings_baseline,
    timings_baseline_path,
    update_findings_baseline,
)
from scripts.adopter_sim.blindness import assert_no_leak, run_pre_journey_assertions
from scripts.adopter_sim.env import build_client_env
from scripts.adopter_sim.evaluate import StepOutcome, cascade, evaluate_step
from scripts.adopter_sim.exitcodes import Exit, classify
from scripts.adopter_sim.fixtures import assert_clean, assert_messy
from scripts.adopter_sim.journey import load_journey
from scripts.adopter_sim.metrics import TOLERANCE, median, normalise
from scripts.adopter_sim.model import NOT_EVALUABLE, NOT_RUN, AdopterSimError
from scripts.adopter_sim.quorum import tally
from scripts.adopter_sim.workspace import materialize, new_run_id, workspace_root

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = REPO_ROOT / "benchmark" / "journeys"
BUNDLE_ROOT = REPO_ROOT / "integrations" / "claude-code" / "seshat-bi"


def run_invocation(args: Namespace, driver: object | None = None) -> Exit:
    journey = load_journey(SEED_DIR / f"{args.journey}.yaml")
    started = time.monotonic()

    try:
        _check_fixtures(args.datasets)
    except AdopterSimError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return Exit.FIXTURE_FAILED

    partial = driver is None and not agent_mod.available()
    if partial:
        print(
            "[SKIP] Claude Code CLI not available headless; agent-driven steps "
            "will be recorded not_run and the invocation labelled partial",
            flush=True,
        )
    active_driver = driver or (None if partial else agent_mod.ClaudeCodeDriver())

    try:
        wheel = _build_wheel()
    except AdopterSimError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return Exit.HARNESS_ERROR

    runs: list[dict[str, object]] = []
    raw_timings: dict[int, list[float]] = {}
    try:
        for dataset in args.datasets:
            for index in range(args.runs):
                if time.monotonic() - started > args.ceiling:
                    print("[FAIL] invocation ceiling reached; truncated", flush=True)
                    partial = True
                    break
                runs.append(
                    _one_run(
                        journey=journey,
                        dataset=dataset,
                        index=index,
                        wheel=wheel,
                        driver=active_driver,
                        args=args,
                        raw_timings=raw_timings,
                    )
                )
    except AdopterSimError as exc:
        print(f"[FAIL] blindness: {exc}", flush=True)
        return Exit.BLINDNESS_ABORT

    verdicts = tally(journey, runs, single_run=args.runs == 1)
    confirmed = [v for v in verdicts if v.status == "confirmed"]
    baseline = load_findings_baseline(findings_baseline_path(REPO_ROOT, journey.name))
    for row in diff_findings(verdicts, baseline):
        print(f"[{row.state.upper()}] step {row.step}: {row.kind}", flush=True)
    for verdict in verdicts:
        print(
            f"[{verdict.status.upper()}] step {verdict.step} {verdict.kind} "
            f"({verdict.seen}/{verdict.evaluable} evaluable runs): {verdict.detail}",
            flush=True,
        )

    metric_out_of_band = _report_timings(journey.name, raw_timings)

    if args.update_baseline:
        try:
            update_findings_baseline(
                findings_baseline_path(REPO_ROOT, journey.name),
                verdicts,
                run_id=new_run_id(f"{journey.name}|accept"),
                kit_version=version("seshat-bi"),
                invoked_by=args.invoked_by,
                partial=partial,
                single_run=args.runs == 1,
                aborted=False,
            )
            print("[OK] baseline updated", flush=True)
        except AdopterSimError as exc:
            print(f"[FAIL] {exc}", flush=True)
            return Exit.HARNESS_ERROR

    return classify(
        aborted_blindness=False,
        fixture_failed=False,
        harness_error=False,
        partial=partial,
        confirmed_findings=len(confirmed),
        metric_out_of_band=metric_out_of_band,
    )


def _check_fixtures(datasets: list[str]) -> None:
    if "messy" in datasets:
        assert_messy(SEED_DIR / "datasets" / "messy" / "orders.csv")
    if "clean" in datasets:
        assert_clean(SEED_DIR / "datasets" / "clean" / "orders.csv")
    return None


def _build_wheel() -> Path:
    dist = REPO_ROOT / "dist"
    result = subprocess.run(
        ["python", "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise AdopterSimError(
            f"wheel build failed:\n{result.stdout}\n{result.stderr}"
        )
    wheels = sorted(dist.glob("*.whl"), key=lambda p: p.stat().st_mtime)
    if not wheels:
        raise AdopterSimError("wheel build produced no artifact")
    return wheels[-1]


def _one_run(
    *,
    journey,
    dataset: str,
    index: int,
    wheel: Path,
    driver,
    args: Namespace,
    raw_timings: dict[int, list[float]],
) -> dict[str, object]:
    run_id = new_run_id(f"{journey.name}|{dataset}|{index}")
    workspace = workspace_root(Path(tempfile.gettempdir()), run_id)
    paths = materialize(
        workspace=workspace,
        wheel=wheel,
        seed_dir=SEED_DIR,
        dataset=dataset,
        bundle_root=BUNDLE_ROOT,
    )
    client_env = build_client_env(
        workspace=paths.root,
        venv_bin=paths.venv_bin,
        config_dir=paths.config_dir,
    )
    run_pre_journey_assertions(
        workspace=paths.root,
        repo_root=REPO_ROOT,
        venv_python=paths.venv_python,
        config_dir=paths.config_dir,
        bundle_manifest=paths.config_dir / "bundle-manifest.json",
        client_env=client_env,
    )

    calibration_ms = _time_cli(
        [str(paths.venv_bin / "seshat"), "--version"], paths, client_env, args
    )[0]

    outcomes: dict[int, StepOutcome] = {}
    transcript_parts: list[str] = []
    for step in journey.steps:
        if step.agent_driven and driver is None:
            outcomes[step.number] = StepOutcome(
                step.number, NOT_RUN, "", True, "agent CLI unavailable"
            )
            continue
        if step.agent_driven:
            reply = driver.run(
                step.prompt or "",
                cwd=paths.root,
                env=client_env,
                timeout=args.agent_timeout,
            )
            transcript_parts.append(reply.text)
            outcomes[step.number] = StepOutcome(
                step.number, reply.observed, reply.text, True, ""
            )
        else:
            command = [str(paths.venv_bin / (step.command or ("seshat",))[0])]
            command += list((step.command or ())[1:])
            elapsed, output, ok = _time_cli(command, paths, client_env, args)
            transcript_parts.append(output)
            raw_timings.setdefault(step.number, []).append(elapsed)
            outcomes[step.number] = StepOutcome(
                step.number, "proceed" if ok else "error", output, ok, ""
            )

    assert_no_leak("\n".join(transcript_parts), REPO_ROOT)

    resolved = cascade(journey, outcomes)
    findings: list[tuple[int, str, str]] = []
    evaluable: list[int] = []
    for step in journey.steps:
        state = resolved[step.number]
        if state == NOT_EVALUABLE or outcomes[step.number].observed == NOT_RUN:
            continue
        evaluable.append(step.number)
        for finding in evaluate_step(
            step, outcomes[step.number].observed, outcomes[step.number].output
        ):
            findings.append((finding.step, finding.kind, finding.detail))
    return {"findings": findings, "evaluable": evaluable, "calibration": calibration_ms}


def _time_cli(command: list[str], paths, client_env, args) -> tuple[float, str, bool]:
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=str(paths.root),
            env=dict(client_env),
            text=True,
            capture_output=True,
            timeout=args.cli_timeout,
        )
        output = result.stdout + result.stderr
        ok = result.returncode == 0
    except subprocess.TimeoutExpired:
        output = f"timed out after {args.cli_timeout}s"
        ok = False
    return (time.monotonic() - start) * 1000.0, output, ok


def _report_timings(journey_name: str, raw_timings: dict[int, list[float]]) -> bool:
    if not raw_timings:
        return False
    medians = {step: median(values) for step, values in raw_timings.items()}
    calibration = medians.get(1)
    timings = normalise(medians, calibration)
    path = timings_baseline_path(REPO_ROOT, journey_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"step {t.step}: {t.raw_ms:.0f} ms ratio={t.ratio}" for t in timings]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for line in lines:
        print(f"[TIME] {line}", flush=True)
    print(f"[TIME] tolerance band +/-{TOLERANCE:.0%}", flush=True)
    return False
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_adopter_sim_workspace.py -v --no-cov`
Expected: PASS (6 tests)

- [ ] **Step 7: Verify the whole unit suite still passes**

Run: `python -m pytest tests/unit -k adopter_sim -v --no-cov`
Expected: PASS (all adopter-sim unit tests)

- [ ] **Step 8: Commit**

```bash
git add scripts/adopter_sim/workspace.py scripts/adopter_sim/agent.py scripts/adopter_sim/runner.py tests/unit/test_adopter_sim_workspace.py
git commit -m "feat: adopter-sim workspace, agent driver seam, and runner

Deterministic short run ids and an asserted 120-char path budget keep the
nested venv/bundle paths under the Windows limit; the driver seam lets the
integration test replay a fixture instead of spending tokens."
```

---

### Task 10: Seed docs, gitignore, packaging proof, and the stub-agent integration test

**Files:**
- Create: `benchmark/journeys/README.md`
- Create: `benchmark/journeys/CLIENT-RULES.md`
- Modify: `.gitignore` (append a section)
- Test: `tests/integration/test_adopter_sim_stub_agent.py`

**Interfaces:**
- Consumes: `run_invocation` (Task 9), `StubDriver`/`AgentReply` (Task 9), `Exit` (Task 8).
- Produces: nothing further.

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_adopter_sim_stub_agent.py
"""Orchestration end-to-end against a stub agent: no tokens, no model."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from scripts.adopter_sim.agent import AgentReply, StubDriver, classify_reply
from scripts.adopter_sim.cli import build_parser
from scripts.adopter_sim.exitcodes import Exit
from scripts.adopter_sim.journey import load_journey

pytestmark = pytest.mark.integration

_REPO = Path(__file__).parents[2]


def _args(**overrides) -> Namespace:
    args = build_parser().parse_args(["--runs", "1", "--datasets", "messy"])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def test_stub_replies_classify_to_the_categorical_set() -> None:
    assert classify_reply("I cannot build silver before the mapping gate clears.") == "refuse"
    assert classify_reply("[PENDING LIVE PROFILE] no database is configured.") == "block_for_evidence"
    assert classify_reply("Done, I built it.") == "proceed"


def test_ambiguous_reply_defaults_to_proceed_so_hard_stops_surface() -> None:
    # Least favourable reading: an unclear refusal must NOT be credited.
    assert classify_reply("Hmm, that is an interesting request.") == "proceed"


def test_shipped_journey_prompts_reach_the_driver_in_order() -> None:
    journey = load_journey(_REPO / "benchmark/journeys/first-hour.yaml")
    agent_steps = [step for step in journey.steps if step.agent_driven]
    driver = StubDriver(
        [AgentReply("ok", "proceed", 1, 0, None) for _ in agent_steps]
    )
    for step in agent_steps:
        driver.run(step.prompt or "", cwd=_REPO, env={}, timeout=1)
    assert len(driver.calls) == len(agent_steps)
    assert "where do i start" in driver.calls[0].lower()


def test_exit_code_is_partial_when_no_driver_is_available(monkeypatch) -> None:
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod

    monkeypatch.setattr(agent_mod, "available", lambda: False)
    monkeypatch.setattr(runner_mod, "_build_wheel", lambda: Path("unused.whl"))
    monkeypatch.setattr(runner_mod, "_one_run", lambda **kwargs: {
        "findings": [], "evaluable": [1, 3, 7], "calibration": 10.0
    })
    code = runner_mod.run_invocation(_args())
    assert code is Exit.PARTIAL
    assert code != Exit.OK


def test_fixture_failure_short_circuits_before_the_build(monkeypatch, tmp_path) -> None:
    from scripts.adopter_sim import runner as runner_mod
    from scripts.adopter_sim.model import AdopterSimError

    def _boom(datasets):
        raise AdopterSimError("messy fixture no longer holds: repeated_grain_key")

    built = {"called": False}

    def _build():
        built["called"] = True
        return Path("unused.whl")

    monkeypatch.setattr(runner_mod, "_check_fixtures", _boom)
    monkeypatch.setattr(runner_mod, "_build_wheel", _build)
    assert runner_mod.run_invocation(_args()) is Exit.FIXTURE_FAILED
    assert built["called"] is False


def test_confirmed_findings_produce_exit_three(monkeypatch) -> None:
    from scripts.adopter_sim import agent as agent_mod
    from scripts.adopter_sim import runner as runner_mod

    monkeypatch.setattr(agent_mod, "available", lambda: True)
    monkeypatch.setattr(runner_mod, "_build_wheel", lambda: Path("unused.whl"))
    monkeypatch.setattr(runner_mod, "_one_run", lambda **kwargs: {
        "findings": [(5, "outcome_mismatch", "expected refuse, observed proceed")],
        "evaluable": [1, 3, 5, 7],
        "calibration": 10.0,
    })
    args = _args()
    args.runs = 3
    driver = StubDriver([])
    assert runner_mod.run_invocation(args, driver=driver) is Exit.FINDINGS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_adopter_sim_stub_agent.py -v --no-cov`
Expected: FAIL — the seed docs do not exist yet and `run_invocation` cannot load `CLIENT-RULES.md`

- [ ] **Step 3: Write `CLIENT-RULES.md`**

```markdown
# CLAUDE.md — my BI workspace

I am a new Seshat BI user. This is my workspace.

## What I have

- `data/orders.csv` — a CSV export of my orders. I do not know its grain, and I
  have not checked it for duplicates or missing values.
- No database. No connection string. No Power BI Desktop.

## What I want

Get from this CSV to something I can trust in a report, using whatever this tool
tells me the next step is.

## How I work

- I do not know this tool's internals. Tell me what to do in my own terms.
- I want to be told when something is not ready. Do not guess on my behalf.
```

This is the **only** guidance the client agent receives — deliberately naive, so the harness measures what the shipped bundle can do unaided.

- [ ] **Step 4: Write `README.md`**

```markdown
# Adopter journeys — the blind client sandbox

This directory is the **seed** for a client workspace. It is tracked so it is
reviewable; it is never the place a journey actually runs.

    benchmark/journeys/            <- this seed (tracked)
      -> %TEMP%/ssim/<run-id>/     <- where the agent actually runs (throwaway)
      -> baseline/*.findings.json  <- accepted findings (tracked)
      -> .seshat/adopter-sim/      <- timings (machine-local, git-ignored)

## The blindness contract

A run is only meaningful if the agent could not reach this repo. Eight
assertions enforce that, and any failure aborts the run rather than degrading it:

1. the workspace is not under `REPO_ROOT`
2. `seshat` resolves from `site-packages`, never `src/`
3. no developer modules resolve in the client venv
4. no dev `CLAUDE.md` / `AGENTS.md` / `.git` above the workspace
5. no `PYTHONPATH`, no editable `.pth` into the repo
6. the environment is an allow-list — no DSN, no credentials, no `REPO_ROOT`
7. the agent's on-disk config profile equals the bundle manifest, exactly
8. the **raw** transcript (checked before sanitization) leaks no dev path

Assertion 7 is the one that matters most. Checks 2, 3 and 5 only prove *Python*
cannot reach the dev tree; without 7 the agent could still arrive carrying the
developer's global rules, in which case it was never a client.

## Running it

    python -m scripts.adopter_sim                     # 3 runs x 2 datasets
    python -m scripts.adopter_sim --runs 1            # cheap look, advisory only
    python -m scripts.adopter_sim --datasets messy    # just the hard dataset

Exit codes: `0` clean, `1` harness error, `2` blindness abort, `3` confirmed
findings, `4` metric out of band, `5` partial run, `6` fixture self-test failed.

## Cost and duration

**Not yet measured.** Record the measured tokens and wall-clock of the first
full invocation here. Do not write an estimate — an invented number becomes a
plan people trust.

## Why the datasets differ

`clean/` is the control: unique keys, no null measures. `messy/` is built to
hurt, and a fixture self-test asserts it still does. If the messy dataset is
ever tidied, the harness fails loudly rather than quietly passing everything.

## What this is not

Not an example a client copies — that is `docs/worked-examples/`. This is
dev-facing test tooling and ships in neither the wheel nor the sdist.
```

- [ ] **Step 5: Append the gitignore section**

Append to `.gitignore`:

```gitignore
# Adopter Sim (blind client sandbox): per-run evidence and machine-local
# timings. The tracked record is benchmark/journeys/baseline/*.findings.json;
# timings are machine-dependent and would make any other machine a permanent
# false regression (same reasoning as .seshat/watch/ above).
benchmark/journeys/runs/
.seshat/adopter-sim/
```

- [ ] **Step 6: Prove nothing ships**

Run:

```bash
python -m build --wheel --sdist --outdir dist-check
python - <<'PY'
import pathlib, tarfile, zipfile
wheel = sorted(pathlib.Path("dist-check").glob("*.whl"))[-1]
sdist = sorted(pathlib.Path("dist-check").glob("*.tar.gz"))[-1]
names = zipfile.ZipFile(wheel).namelist()
with tarfile.open(sdist) as tar:
    names += tar.getnames()
leaked = [n for n in names if "journeys" in n or "adopter_sim" in n]
print("LEAKED:", leaked or "[OK] nothing ships")
assert not leaked, leaked
PY
rm -rf dist-check
```

Expected: `LEAKED: [OK] nothing ships`

- [ ] **Step 7: Run the integration test**

Run: `python -m pytest tests/integration/test_adopter_sim_stub_agent.py -v --no-cov`
Expected: PASS (6 tests)

- [ ] **Step 8: Run the governance gate and the full adopter-sim suite**

Run:

```bash
python -m pytest tests/unit -k adopter_sim tests/integration/test_adopter_sim_stub_agent.py --no-cov -q
python -m seshat.cli check
```

Expected: all tests PASS; `seshat check` reports no new violation (in particular no C2 client-marker hit from the new datasets).

- [ ] **Step 9: Commit**

```bash
git add benchmark/journeys/README.md benchmark/journeys/CLIENT-RULES.md .gitignore tests/integration/test_adopter_sim_stub_agent.py
git commit -m "feat: adopter-sim seed docs, gitignore, and stub-agent integration test

README states the eight-assertion blindness contract and leaves the cost figure
to be measured rather than estimated; the stub-agent test covers orchestration,
cascade, and exit-code mapping without spending tokens."
```

---

## Self-Review

**Spec coverage.** Every spec section maps to a task: seed layout and journey (1), datasets and fixture self-test (2), allow-list environment (3), the eight assertions (4), findings/cascade/quorum (5), calibration and metrics (6), split baselines and guarded update (7), budgets/timeouts/exit codes (8), workspace/driver/runner including the Windows path budget (9), README blindness contract, gitignore, packaging exclusion and the stub-agent integration test (10).

**Two deliberate deviations from the spec, both narrowing:**

1. The spec lists a `--runs 5` triage mode and escalation of a flaky finding to `recurring-flaky` across three consecutive invocations. Recurring-flaky requires persisting invocation history, which nothing in v1 stores. `--runs 5` works (the `--runs` flag is a plain int, and the quorum is a ≥2 threshold, not a hard-coded 3), but the **`recurring-flaky` status is not implemented** — `STATUSES` carries the four statuses that are. Add it with an invocation-history store, or drop it from the spec.
2. The spec's metric gate ("fails the run outside its tolerance band") is **reported but not enforced**: `_report_timings` always returns `False`, so exit code 4 is reachable by `classify` but never raised by the runner. There is no accepted timing baseline to compare against until a first full run is recorded, and gating against an absent baseline would fail every first run. Enforce it in a follow-up once `.seshat/adopter-sim/<journey>.timings.json` holds an accepted reference.

Both are noted rather than silently dropped, per the spec's own no-silent-caps posture.

> **Both deviations are now closed** (issue #567). `recurring-flaky` is in
> `quorum.STATUSES` and escalates from a machine-local invocation history
> (`scripts/adopter_sim/history.py`), and `_report_timings` enforces the band
> against the accepted reference. The two findings above are kept as the
> record of what shipped in this plan's PR, not as current state.

**Placeholder scan.** No TBD/TODO. The one intentionally-unfilled value is the README's cost figure, which is unfilled *by design* and labelled as such.

**Type consistency.** `AdopterSimError` is defined once (Task 1) and imported everywhere. `JourneyStep.command` is `tuple[str, ...] | None` in the model and constructed with `tuple(command)` in the loader. `QuorumVerdict` fields used by `baseline.py` (`step`, `kind`, `detail`, `status`) match Task 5's definition. `StepOutcome` is defined in `evaluate.py` and imported by `runner.py`, not redefined. `Exit` members referenced in Task 10's test all exist in Task 8's enum.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-03-adopter-sim.md`.
