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


def _ctx_tracking(root: Path, *, drop: str = "") -> RuleContext:
    """A context whose tracked set can omit a file that exists on disk."""
    tracked = tuple(rel for rel in _ctx(root).tracked_files if rel != drop)
    return RuleContext(repo_root=root, tracked_files=tracked)


@pytest.mark.unit
def test_a_tracked_surface_that_declares_nothing_is_an_error(tmp_path):
    """Fails while an emptied declaration is read as a coverage gap.

    `safe_zones: []` is a TRACKED surface asserting an empty vocabulary, which
    disagrees with the authority's seven. The old branch suppressed the
    disagreement whenever `declared` was falsy, so deleting the contents of a
    declaring file silently passed a three-way parity check.
    """
    _write_corpus(tmp_path)
    (tmp_path / "design" / "grids" / "mobile-grid.yaml").write_text(
        "safe_zones: []\n", encoding="utf-8"
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "mobile-grid.yaml" in findings[0].locator


@pytest.mark.unit
def test_a_tracked_surface_that_loses_its_declaration_key_is_an_error(tmp_path):
    """The same fail-open reached by removing the key rather than emptying it."""
    _write_corpus(tmp_path)
    (tmp_path / "design" / "grids" / "mobile-grid.yaml").write_text(
        "unrelated_key: 1\n", encoding="utf-8"
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]


@pytest.mark.unit
def test_an_untracked_scaffolded_surface_is_reported(tmp_path):
    """A scaffolded declarer that went missing is a LOST surface, not a gap.

    This asserted silence while the mobile grid was unscaffolded. Shipping it (so
    the blueprint template's `grid_ref` resolves) made its absence a real loss, and
    the any-of corpus cannot say so. Tracked-but-empty is the error above; this is
    the untracked arm of the same requirement.
    """
    _write_corpus(tmp_path)
    (tmp_path / "design" / "grids" / "mobile-grid.yaml").unlink()

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "mobile-grid.yaml" in findings[0].locator


@pytest.mark.unit
def test_a_surface_present_on_disk_but_untracked_is_a_coverage_gap(tmp_path):
    """Tracking, not mere presence, is what makes a surface answerable.

    The file sits on disk, so only the COMMIT distinguishes this from a healthy
    repo -- and an untracked scaffolded declarer is reported.
    """
    _write_corpus(tmp_path)

    findings = list(
        section_vocabulary(
            _ctx_tracking(tmp_path, drop="design/grids/mobile-grid.yaml")
        )
    )

    assert [f.severity for f in findings] == [Severity.ERROR]


@pytest.mark.unit
def test_a_malformed_declaring_surface_is_reported_not_skipped(tmp_path):
    """A file the rule could not parse must not read as agreement."""
    _write_corpus(tmp_path)
    (tmp_path / "design" / "grids" / "mobile-grid.yaml").write_text(
        "safe_zones: [oops: bad\n  ][\n", encoding="utf-8"
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]


@pytest.mark.unit
def test_an_unreadable_authority_is_an_error_not_a_silent_exit(tmp_path):
    """Fails while a malformed authority ends the rule in silence.

    `canonical_sections` returns an empty set for a malformed, emptied or deleted
    `16x9-grid.yaml`, and the early return then skipped BOTH halves of the rule.
    The any-of `SECTION_CORPUS` is still satisfied by the mobile grid, so the census
    marks DL10 evaluated -- the authority vanishing was the quietest way to disable
    the whole rule.
    """
    _write_corpus(tmp_path)
    (tmp_path / "design" / "grids" / "16x9-grid.yaml").write_text(
        "zones: [broken: yaml\n  ][\n", encoding="utf-8"
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "16x9-grid.yaml" in findings[0].locator


@pytest.mark.unit
def test_a_tracked_authority_declaring_nothing_is_an_error(tmp_path):
    """An emptied authority is drift, not an untracked-corpus coverage gap."""
    _write_corpus(tmp_path)
    (tmp_path / "design" / "grids" / "16x9-grid.yaml").write_text(
        "zones: {}\n", encoding="utf-8"
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]


@pytest.mark.unit
def test_the_committed_authority_declares_its_zones_identically_in_every_profile():
    """Anchors the real corpus: both desktop profiles declare the same seven."""
    from seshat.rules.design_section_vocabulary import authority_declarations

    blocks = authority_declarations(REPO_ROOT)

    assert len(blocks) == 2, blocks
    assert all(block == _SEVEN for block in blocks), blocks


@pytest.mark.unit
def test_a_second_authority_profile_that_disagrees_is_an_error(tmp_path):
    """Fails while only the FIRST `zones` block is read.

    `16x9-grid.yaml` carries a separate `zones` mapping per resolution profile
    (1280x720 and 1920x1080). `first_value` returned one and ignored the rest, so
    drift in the later profile left DL10 green while the desktop profiles disagreed.
    """
    _write_corpus(tmp_path)
    grid = tmp_path / "design" / "grids" / "16x9-grid.yaml"
    second = "\n".join(
        f"      {k}: {{rows: 1}}" for k in sorted(_SEVEN - {"footer_status"})
    )
    grid.write_text(
        grid.read_text(encoding="utf-8")
        + f"  hi_dpi:\n    zones:\n{second}\n      extra_band: {{rows: 9}}\n",
        encoding="utf-8",
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert findings, "a disagreeing second profile must be reported"
    assert any(
        "extra_band" in f.message or "footer_status" in f.message for f in findings
    ), [f.message for f in findings]


@pytest.mark.unit
def test_a_missing_authority_is_reported_when_another_surface_is_tracked(tmp_path):
    """Fails while an untracked authority ends the rule in silence.

    The any-of `SECTION_CORPUS` is satisfied by the mobile grid alone, so the census
    marks DL10 evaluated. Returning quietly then reports "clean" for a repo that has
    no authoritative vocabulary at all -- the corpus requirement cannot cover this,
    because it is satisfied by a DIFFERENT file than the one that went missing.
    """
    _write_corpus(tmp_path)
    (tmp_path / "design" / "grids" / "16x9-grid.yaml").unlink()

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "16x9-grid.yaml" in findings[0].locator


@pytest.mark.unit
def test_no_declaring_surface_at_all_stays_silent(tmp_path):
    """The boundary: with nothing tracked, the corpus requirement owns the gap."""
    (tmp_path / "design" / "grids").mkdir(parents=True, exist_ok=True)

    assert list(section_vocabulary(_ctx(tmp_path))) == []


@pytest.mark.unit
def test_a_named_entry_in_a_filled_sections_list_is_validated(tmp_path):
    """Fails while only keys literally named `section` are checked.

    A filled blueprint may declare its page layout as a `sections` LIST of
    `{name: ...}` -- `reports/blueprints/branch-performance.yaml` does. A typo in one
    of those names left the declared layout entirely outside DL10 whenever the visual
    placements themselves stayed valid.
    """
    _write_corpus(tmp_path)
    blueprints = tmp_path / "reports" / "blueprints"
    blueprints.mkdir(parents=True, exist_ok=True)
    (blueprints / "filled.yaml").write_text(
        "sections:\n  - name: header\n    used: true\n"
        "  - name: main_insigts\n    used: true\n",
        encoding="utf-8",
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "main_insigts" in findings[0].message


@pytest.mark.unit
def test_a_missing_scaffolded_declarer_is_reported(tmp_path):
    """The blueprint template ships with every scaffold, so its absence is drift.

    `scaffold-design` installs `templates/dashboard-page-blueprint.yaml` alongside
    the authority, so a repo holding the authority but not the template has LOST a
    surface rather than never having had one -- and the any-of corpus cannot say so.
    """
    _write_corpus(tmp_path)
    (tmp_path / "templates" / "dashboard-page-blueprint.yaml").unlink()

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "dashboard-page-blueprint.yaml" in findings[0].locator


@pytest.mark.unit
def test_an_id_shaped_entry_in_a_filled_sections_list_is_validated(tmp_path):
    """Fails while only `name` entries are harvested.

    `reports/blueprints/data-quality-control-room.yaml` declares its sections as
    `{id: ..., purpose: ...}`, so a typo in one of those ids left the declared page
    layout outside DL10 exactly as the `name` shape did.
    """
    _write_corpus(tmp_path)
    blueprints = tmp_path / "reports" / "blueprints"
    blueprints.mkdir(parents=True, exist_ok=True)
    (blueprints / "filled.yaml").write_text(
        'sections:\n  - id: "header"\n    purpose: ok\n'
        '  - id: "kpi_strp"\n    purpose: typo\n',
        encoding="utf-8",
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "kpi_strp" in findings[0].message


@pytest.mark.unit
def test_a_malformed_profile_zones_block_participates_as_empty(tmp_path):
    """Fails while an unsupported `zones` shape is dropped from the comparison.

    A later profile whose `zones` is null or a scalar was filtered out entirely, so
    the remaining valid profile supplied the canonical set and the profile that LOST
    its vocabulary was never compared against it.
    """
    _write_corpus(tmp_path)
    grid = tmp_path / "design" / "grids" / "16x9-grid.yaml"
    grid.write_text(
        grid.read_text(encoding="utf-8") + "  hi_dpi:\n    zones: null\n",
        encoding="utf-8",
    )

    findings = list(section_vocabulary(_ctx(tmp_path)))

    assert findings, "a profile that declares no zones must be reported"
    assert any("profile" in f.message for f in findings), [f.message for f in findings]


@pytest.mark.unit
def test_the_mobile_grid_is_treated_as_scaffolded():
    """The scaffolder now ships it, so its absence is a lost surface.

    Pins the two constants against each other: `scaffold-design` installing a
    declaring surface is exactly what makes that surface required. Without this,
    adding a declarer to the scaffolder silently leaves DL10's severity behind.
    """
    from seshat.design_scaffold import _DESIGN_FILES
    from seshat.rules.design_section_vocabulary import (
        _DECLARERS,
        _SCAFFOLDED_DECLARERS,
    )

    scaffolded = {repo_path for _, repo_path in _DESIGN_FILES}
    declarers = {suffix for suffix, _ in _DECLARERS}

    assert _SCAFFOLDED_DECLARERS == declarers & scaffolded


@pytest.mark.unit
def test_a_non_declaring_file_alone_does_not_satisfy_the_corpus():
    """`design/grids/README.md` must not make DL10 look evaluated.

    The wildcard accepted any file under `design/grids/`, so a repo tracking only a
    non-declaring file satisfied the requirement while the rule parsed no vocabulary
    at all -- reported as evaluated and clean.
    """
    from seshat.rules.design_section_vocabulary import SECTION_CORPUS

    globs = [alt.pattern for alt in SECTION_CORPUS.any_of]

    assert all(g.endswith((".yaml", ".yml")) for g in globs), globs
    assert "design/grids/*" not in globs
