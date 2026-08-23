"""DL10: one section vocabulary across the grid, the mobile grid and blueprints.

Four committed surfaces name page sections, in three different shapes:

* ``design/grids/16x9-grid.yaml`` -- ``zones``, a mapping (the authority);
* ``design/grids/mobile-grid.yaml`` -- ``safe_zones``, a LIST of ``{band: ...}``;
* ``templates/dashboard-page-blueprint.yaml`` -- ``sections``, a mapping;
* filled blueprints under ``reports/blueprints/`` -- ``section:`` values on visuals.

They agree today. Nothing enforced that, and the blueprint template states its
seven keys are what a visual's ``position.section`` MUST name -- so a key added to
one surface and not the others silently splits the vocabulary the whole design
layer routes on.

DL10 pins BOTH halves, because they fail differently and this repo has paid for
conflating them (enum parity proves the contract sound; only instance validation
proves the instances obey it):

* parity -- the three DECLARING surfaces declare the same set, normalized across
  their three shapes;
* instances -- every ``section:`` value in a filled blueprint is in that set.

Out of scope, stated rather than implied: ``templates/background-spec.yaml``
constrains ``static_regions[].section`` in a COMMENT, which no rule can read.
Hoisting that enum into real YAML would edit a template the init scaffolders
bundle and the sdist ships, so it stays a comment and DL10 validates filled
background specs against the grid instead.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_section_vocabulary import (
    RULE_ID,
    canonical_sections,
    section_vocabulary,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_SEVEN = {
    "header",
    "kpi_strip",
    "main_insight",
    "diagnostic",
    "exception_detail",
    "filter_rail",
    "footer_status",
}


def _ctx(root: Path) -> RuleContext:
    tracked = tuple(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )
    return RuleContext(repo_root=root, tracked_files=tracked)


@pytest.mark.unit
def test_the_rule_is_reachable_from_the_registry():
    """Fails if the module is not imported in `rules/__init__.py`.

    Runs in a SUBPROCESS that imports only `seshat.rules`, the way `seshat check`
    does. Asserting in-process cannot fail: this test file imports the rule module
    directly, and that import IS the registration, so the rule would be present
    even with the `__init__.py` line deleted. Without this, removing that one line
    leaves every other test here green while the checker silently stops running the
    rule.
    """
    probe = (
        "import seshat.rules;"
        "from seshat.registry import all_rules;"
        "print('DL10' in {r.id for r in all_rules()})"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )

    assert result.stdout.strip() == "True", result.stderr


@pytest.mark.unit
def test_the_committed_repo_declares_the_seven_section_vocabulary():
    """Anchors the authority: if the real grid changes, this test says so first."""
    assert canonical_sections(REPO_ROOT) == _SEVEN


@pytest.mark.unit
def test_the_committed_repo_passes_its_own_vocabulary_check():
    """DL10 must be silent on the tracked corpus -- it pins working state."""
    findings = list(section_vocabulary(_ctx(REPO_ROOT)))

    assert findings == [], [f.message for f in findings]


@pytest.mark.unit
def test_a_declaring_surface_that_adds_a_key_alone_is_an_error(tmp_path):
    """Fails if parity is unchecked -- the vocabulary splits with nothing red."""
    _write_corpus(tmp_path, mobile_extra="sidebar_rail")

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "sidebar_rail" in findings[0].message


@pytest.mark.unit
def test_a_declaring_surface_that_drops_a_key_is_an_error(tmp_path):
    """Fails if parity only checks one direction (superset but not subset)."""
    _write_corpus(tmp_path, blueprint_drop="filter_rail")

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert findings and findings[0].severity is Severity.ERROR
    assert "filter_rail" in findings[0].message


@pytest.mark.unit
def test_a_filled_blueprint_using_an_unknown_section_is_an_error(tmp_path):
    """Fails if only parity is checked -- a real instance can still be wrong."""
    _write_corpus(tmp_path)
    (tmp_path / "reports" / "blueprints").mkdir(parents=True)
    (tmp_path / "reports" / "blueprints" / "p.yaml").write_text(
        "visuals:\n  - id: v1\n    section: not_a_zone\n", encoding="utf-8"
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert findings and findings[0].severity is Severity.ERROR
    assert "not_a_zone" in findings[0].message
    assert RULE_ID == findings[0].rule_id


@pytest.mark.unit
def test_a_template_placeholder_is_not_reported(tmp_path):
    """Fails if the instance half scans templates -- `<...>` is not a violation."""
    _write_corpus(tmp_path)
    (tmp_path / "templates").mkdir(exist_ok=True)
    (tmp_path / "templates" / "dashboard-page-blueprint.yaml").write_text(
        "sections:\n"
        + "".join(f"  {k}: keep\n" for k in sorted(_SEVEN))
        + 'visuals:\n  - section: "<one of the seven section keys above>"\n',
        encoding="utf-8",
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert findings == [], [f.message for f in findings]


def _write_corpus(
    root: Path, *, mobile_extra: str | None = None, blueprint_drop: str | None = None
) -> None:
    """A minimal three-surface corpus in the three real shapes."""
    grids = root / "design" / "grids"
    grids.mkdir(parents=True, exist_ok=True)
    (grids / "16x9-grid.yaml").write_text(
        "grid_profiles:\n  desktop:\n    zones:\n"
        + "".join(f"      {k}: {{rows: 1}}\n" for k in sorted(_SEVEN)),
        encoding="utf-8",
    )
    bands = sorted(_SEVEN) + ([mobile_extra] if mobile_extra else [])
    (grids / "mobile-grid.yaml").write_text(
        "safe_zones:\n" + "".join(f"  - band: {b}\n    order: 1\n" for b in bands),
        encoding="utf-8",
    )
    templates = root / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    keys = sorted(_SEVEN - {blueprint_drop} if blueprint_drop else _SEVEN)
    (templates / "dashboard-page-blueprint.yaml").write_text(
        "sections:\n" + "".join(f"  {k}: keep\n" for k in keys), encoding="utf-8"
    )
