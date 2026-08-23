"""DL11: design pointers that name a real target must resolve to one.

The design corpora carry ten ``*_ref`` keys, and the suffix does NOT mean "file
path" -- enumerated by hand rather than assumed, they fall in three buckets:

* repo-relative FILE paths -- ``grid_ref``, ``theme_ref``;
* an intra-file TOKEN pointer -- ``value_typography_ref``
  (``typography.scale_pt.kpi_value``) -- a dotted key path into the design-token
  file, not a file at all;
* NOT pointers this rule can resolve -- ``blueprint_ref``, ``spec_ref``,
  ``source_file_ref`` (``<placeholders>`` in templates), ``store_ref``,
  ``model_ref`` (a path-or-id in the F009/F010 stores), ``qa_ref`` (a prose
  design-doc name) and ``sentiment_color_ref``, which carries a dotted token path
  in the token file and free prose in a blueprint -- one key, two grammars.

Guarding all ten as paths would emit false errors on seven of them, and a gate that
cries wolf gets switched off. DL11 therefore guards the three it can actually
resolve and says so; the other seven are named in its docstring rather than silently
skipped.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.rules.design_ref_resolution import (
    FILE_REF_KEYS,
    RULE_ID,
    TOKEN_REF_KEYS,
    ref_resolution,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


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
        "print('DL11' in {r.id for r in all_rules()})"
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
def test_the_guarded_key_sets_are_the_hand_verified_ones():
    """Pins scope: widening it silently is what produces false errors."""
    assert FILE_REF_KEYS == frozenset({"grid_ref", "theme_ref"})
    assert TOKEN_REF_KEYS == frozenset({"value_typography_ref"})


@pytest.mark.unit
def test_the_committed_repo_passes_its_own_pointer_check():
    """DL11 must be silent on the tracked corpus -- it pins working state."""
    findings = list(ref_resolution(_ctx(REPO_ROOT)))

    assert findings == [], [f"{f.locator}: {f.message}" for f in findings]


@pytest.mark.unit
def test_a_dangling_file_ref_is_an_error(tmp_path):
    """Fails while a grid_ref pointing at nothing goes unreported."""
    _corpus(tmp_path, grid_ref="design/grids/does-not-exist.yaml")

    findings = list(ref_resolution(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "does-not-exist.yaml" in findings[0].message
    assert findings[0].rule_id == RULE_ID


@pytest.mark.unit
def test_a_dangling_token_ref_is_an_error(tmp_path):
    """Fails if dotted token pointers are treated as file paths (or ignored)."""
    _corpus(tmp_path, token_ref="typography.scale_pt.no_such_token")

    findings = list(ref_resolution(_ctx(tmp_path)))

    assert findings and findings[0].severity is Severity.ERROR
    assert "no_such_token" in findings[0].message


@pytest.mark.unit
def test_a_resolvable_token_ref_is_silent(tmp_path):
    """Fails if the token resolver cannot walk a real dotted path."""
    _corpus(tmp_path, token_ref="typography.scale_pt.kpi_value")

    assert list(ref_resolution(_ctx(tmp_path))) == []


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "<path to the page's dashboard-page-blueprint.yaml>",
        "<templates/background-spec.yaml filled for this page, or 'none'>",
        "none",
    ],
)
def test_a_placeholder_or_none_is_not_reported(tmp_path, value):
    """Fails if templates' unfilled pointers are read as dangling paths."""
    _corpus(tmp_path, grid_ref=value)

    assert list(ref_resolution(_ctx(tmp_path))) == []


@pytest.mark.unit
def test_an_unguarded_key_is_never_resolved(tmp_path):
    """Fails if scope creeps: store_ref/qa_ref are ids, not paths."""
    _corpus(tmp_path)
    (tmp_path / "design" / "extra.yaml").write_text(
        'store_ref: "not/a/real/path.yaml"\nqa_ref: "visual-qa"\n', encoding="utf-8"
    )

    assert list(ref_resolution(_ctx(tmp_path))) == []


def _corpus(
    root: Path, *, grid_ref: str | None = None, token_ref: str | None = None
) -> None:
    """A design/ corpus with a real token file and an optional pointer under test."""
    design = root / "design"
    (design / "tokens").mkdir(parents=True, exist_ok=True)
    (design / "tokens" / "tokens.yaml").write_text(
        "typography:\n  scale_pt:\n    kpi_value: 28\ncolors:\n  sentiment:\n"
        "    success: '#2E7D5B'\n",
        encoding="utf-8",
    )
    lines = []
    if grid_ref is not None:
        lines.append(f'grid_ref: "{grid_ref}"')
    if token_ref is not None:
        lines.append(f'value_typography_ref: "{token_ref}"')
    (design / "under-test.yaml").write_text(
        "\n".join(lines) + "\n" if lines else "{}\n", encoding="utf-8"
    )


def _ctx_without(root: Path, *untracked: str) -> RuleContext:
    """A context where ``untracked`` exists on disk but is NOT tracked.

    The distinction DL11 has to make: a pointer target that a working tree happens
    to hold is not a committed target. `_ctx` derives tracking from the disk, so it
    cannot express this.
    """
    excluded = {u.replace("\\", "/") for u in untracked}
    return RuleContext(
        repo_root=root,
        tracked_files=tuple(
            rel for rel in _ctx(root).tracked_files if rel not in excluded
        ),
    )


@pytest.mark.unit
def test_a_file_ref_to_an_existing_but_untracked_target_is_an_error(tmp_path):
    """Fails while resolution asks the filesystem instead of the commit.

    DL11 promises a COMMITTED repo-relative target. A local-only file satisfies
    `.exists()` and would let the gate pass on a machine where the artifact is
    present while it is absent from the commit every other consumer clones.
    """
    _corpus(tmp_path, grid_ref="local-only.yaml")
    (tmp_path / "local-only.yaml").write_text("x: 1\n", encoding="utf-8")

    findings = list(ref_resolution(_ctx_without(tmp_path, "local-only.yaml")))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "local-only.yaml" in findings[0].message


@pytest.mark.unit
def test_a_file_ref_escaping_the_repository_is_an_error(tmp_path):
    """Fails while `repo_root / target` lets an absolute path discard the root.

    `Path.__truediv__` with an absolute operand DROPS the left side, so an absolute
    `grid_ref` is resolved against the real filesystem. On a machine where that path
    exists the check passes -- which is why this asserts on a target the rule must
    reject for being outside the repo, not for being absent.
    """
    _corpus(tmp_path, grid_ref="../outside-the-repo.yaml")
    (tmp_path.parent / "outside-the-repo.yaml").write_text("x: 1\n", encoding="utf-8")

    findings = list(ref_resolution(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "outside-the-repo.yaml" in findings[0].message


@pytest.mark.unit
def test_an_absolute_file_ref_is_an_error_even_when_the_path_exists(tmp_path):
    """The platform-independent form of the escape: an absolute path that IS real.

    Pointing at a file this test just created guarantees existence on every
    platform, so the assertion cannot go vacuous the way a hardcoded
    `/etc/passwd` (absent on Windows, present on Linux CI) would.
    """
    real = tmp_path / "absolute-target.yaml"
    real.write_text("x: 1\n", encoding="utf-8")
    _corpus(tmp_path, grid_ref=real.as_posix())

    findings = list(ref_resolution(_ctx(tmp_path)))

    assert [f.severity for f in findings] == [Severity.ERROR]


@pytest.mark.unit
def test_a_tracked_file_ref_stays_silent(tmp_path):
    """The other arm: a genuinely committed target must not be reported."""
    _corpus(tmp_path, grid_ref="design/grids/real-grid.yaml")
    grids = tmp_path / "design" / "grids"
    grids.mkdir(parents=True, exist_ok=True)
    (grids / "real-grid.yaml").write_text("zones: {}\n", encoding="utf-8")

    assert list(ref_resolution(_ctx(tmp_path))) == []
