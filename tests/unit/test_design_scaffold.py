"""`seshat scaffold-design` self-sufficiency (issues #440, #441).

The six Stage-6/7 design + handoff templates (dashboard-page-blueprint.yaml,
visual-spec.yaml, report-composition.yaml, design/grids/16x9-grid.yaml,
handoff/bi-handoff-pack.md, handoff/handoff-review-checklist.md) previously
shipped only with the development repository, and no verb materialized them
into a pip-only workspace -- so `blueprint_preview` / `dashboard_coordinator` /
the `publish_pack` rule (all of which read these as repo-relative paths) had
nothing to read. `scaffold_design` closes that gap the same way
`stage1_scaffold.scaffold_source` does for the Stage-1 templates: bundled
package data (wheel force-include), a dev-checkout fallback, and a
non-destructive write via the shared `safe_write.write_if_absent`.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]

_DESIGN_FILES = (
    "templates/dashboard-page-blueprint.yaml",
    "templates/visual-spec.yaml",
    "templates/report-composition.yaml",
    "design/grids/16x9-grid.yaml",
    "templates/handoff/bi-handoff-pack.md",
    "templates/handoff/handoff-review-checklist.md",
)

# (repo source path, packaged destination) -- the packaged layout is
# deliberately flattened under seshat/design_templates/ (no templates/ prefix,
# grids/ instead of design/grids/); see the pyproject force-include comment.
_FORCE_INCLUDE_MAP = {
    "templates/dashboard-page-blueprint.yaml": (
        "seshat/design_templates/dashboard-page-blueprint.yaml"
    ),
    "templates/visual-spec.yaml": "seshat/design_templates/visual-spec.yaml",
    "templates/report-composition.yaml": (
        "seshat/design_templates/report-composition.yaml"
    ),
    "design/grids/16x9-grid.yaml": "seshat/design_templates/grids/16x9-grid.yaml",
    "templates/handoff/bi-handoff-pack.md": (
        "seshat/design_templates/handoff/bi-handoff-pack.md"
    ),
    "templates/handoff/handoff-review-checklist.md": (
        "seshat/design_templates/handoff/handoff-review-checklist.md"
    ),
}


def test_pyproject_ships_design_templates_into_the_package() -> None:
    """The wheel force-include (and sdist include) must carry all six Stage-6/7
    design + handoff templates under the package, so `scaffold_design` finds
    them in a non-editable install (issues #440, #441)."""
    raw = (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    document = tomllib.loads(raw)
    force_include = document["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ]
    sdist_include = document["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]
    for source, destination in _FORCE_INCLUDE_MAP.items():
        assert force_include.get(source) == destination, (
            f"{source} must force-include into the package as {destination}"
        )
        assert f"/{source}" in sdist_include, (
            f"{source} must be in the sdist include list so the wheel can "
            f"force-include it"
        )


def test_scaffold_design_writes_all_six_templates_to_repo_relative_paths(
    tmp_path: Path,
) -> None:
    from seshat.design_scaffold import scaffold_design

    report = scaffold_design(tmp_path)

    for rel in _DESIGN_FILES:
        target = tmp_path / rel
        assert target.is_file(), f"missing {rel}"
        assert rel in report.written
    assert report.kept == ()


def test_scaffold_design_is_non_destructive_and_idempotent(tmp_path: Path) -> None:
    from seshat.design_scaffold import scaffold_design

    scaffold_design(tmp_path)
    edited = tmp_path / "templates" / "visual-spec.yaml"
    edited.write_text("# hand-edited\n", encoding="utf-8")

    second = scaffold_design(tmp_path)

    assert "templates/visual-spec.yaml" in second.kept
    assert second.written == ()
    assert edited.read_text(encoding="utf-8") == "# hand-edited\n"


def test_scaffold_design_dev_checkout_fallback_resolves(tmp_path: Path) -> None:
    """No wheel data needed in the dev suite: the _SOURCE_ROOT fallback must
    find the repo-root templates/ and design/ dirs so all six files still
    materialize byte-for-byte."""
    from seshat.design_scaffold import scaffold_design

    report = scaffold_design(tmp_path)

    assert len(report.written) == len(_DESIGN_FILES)
    for rel in _DESIGN_FILES:
        assert (tmp_path / rel).read_bytes() == (_REPO_ROOT / rel).read_bytes()


def test_scaffold_design_refuses_symlinked_destination(tmp_path: Path) -> None:
    """Reuse the safe_write containment guarantee: a symlinked `templates/`
    directory component must be refused, not followed out of --repo."""
    import os

    from seshat.design_scaffold import scaffold_design
    from seshat.safe_write import SafeWriteError

    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, repo / "templates", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError):
        scaffold_design(repo)

    assert not any(outside.iterdir())


def test_scaffold_design_creates_missing_parent_dirs(tmp_path: Path) -> None:
    from seshat.design_scaffold import scaffold_design

    assert not (tmp_path / "templates").exists()
    assert not (tmp_path / "design").exists()
    scaffold_design(tmp_path)
    assert (tmp_path / "templates" / "handoff" / "bi-handoff-pack.md").is_file()
    assert (tmp_path / "design" / "grids" / "16x9-grid.yaml").is_file()


def test_cli_scaffold_design_smoke(tmp_path: Path) -> None:
    """The `scaffold-design` verb is wired into the CLI dispatch table and
    writes the six templates via `seshat scaffold-design --repo <dir>`."""
    from seshat.cli import main

    exit_code = main(["scaffold-design", "--repo", str(tmp_path)])

    assert exit_code == 0
    for rel in _DESIGN_FILES:
        assert (tmp_path / rel).is_file()


def test_cli_scaffold_design_carries_repo_into_next_hint(
    tmp_path: Path, capsys
) -> None:
    """Codex #451 P2: when `--repo` points elsewhere than the cwd, the governed
    `next` follow-up must carry `--repo <dir>` (mirroring scaffold-source) so
    `next` inspects THIS workspace, not the caller's cwd."""
    from seshat.cli import main

    exit_code = main(["scaffold-design", "--repo", str(tmp_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert f"next --repo {tmp_path} --table" in out


def test_cli_scaffold_design_omits_repo_flag_when_repo_is_cwd(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """When --repo is the default '.', the next hint omits the redundant flag."""
    from seshat.cli import main

    monkeypatch.chdir(tmp_path)
    exit_code = main(["scaffold-design", "--repo", "."])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "next --table" in out
    assert "--repo ." not in out


def test_cli_scaffold_design_refuses_a_non_directory_repo(
    tmp_path: Path, capsys
) -> None:
    """Codex #451 P2: an unwritable/misnamed --repo (here a regular file, so the
    write raises NotADirectoryError -- an OSError subclass) must surface as the
    documented `[refused]` line + exit 1, NOT a raw traceback."""
    from seshat.cli import main

    not_a_dir = tmp_path / "regular_file"
    not_a_dir.write_text("i am a file, not a repo\n", encoding="utf-8")

    exit_code = main(["scaffold-design", "--repo", str(not_a_dir)])

    assert exit_code == 1
    assert "[refused]" in capsys.readouterr().err
