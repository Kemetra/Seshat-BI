"""`--explain` guidance must come from the INSTALLED kit, not the repo being checked.

The first cut of this flag loaded `docs/rules/rule-fixes.yaml` relative to `--repo`.
In the kit's own tree that path exists, so every test passed -- but in the primary
shipped scenario (a wheel/pipx install checking a consumer workspace) the file is
neither created by `seshat init` nor carried by the wheel, so the fail-soft `{}`
turned into silence: findings printed with no guidance, looking like rules that
simply have none.

Guidance is a property of the RULES, which ship with the package; it is not a
property of the workspace under inspection. These tests pin that, and pin the
packaging that makes it true -- a data file outside `packages` vanishes from the
wheel while unit tests stay green (the `packs` schemas hit this same class).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_guidance_resolves_for_a_repo_that_has_no_docs_dir(tmp_path):
    """Fails while the loader keys on the inspected workspace instead of the kit."""
    from seshat.cli import _explain_guidance

    guidance = _explain_guidance(tmp_path)

    assert guidance, "a consumer workspace must still get the kit's own guidance"
    assert "D8" in guidance


@pytest.mark.unit
def test_annotation_renders_for_a_consumer_workspace(tmp_path, capsys):
    """Fails if a foreign repo's findings print bare -- the shipped-product case."""
    from seshat.cli import _explain_guidance
    from seshat.core import Finding, RegisteredRule, RuleContext, Severity
    from seshat.runner import explain_renderer, run

    finding = Finding("D8", Severity.ERROR, "bad partition", "model.tmdl:12")
    rules = (RegisteredRule(id="D8", rule=lambda ctx: [finding], title="D8"),)
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())

    run(rules, ctx, annotate=explain_renderer(_explain_guidance(tmp_path)))

    assert "means:" in capsys.readouterr().out


@pytest.mark.unit
def test_guidance_file_is_carried_into_the_wheel():
    """Fails if the YAML is not force-included -- it lives outside `packages`."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = config["tool"]["hatch"]["build"]["targets"]["wheel"]
    forced = wheel.get("force-include", {})

    assert "docs/rules/rule-fixes.yaml" in forced, (
        "rule-fixes.yaml is under docs/, outside `packages`, so a bare wheel "
        "would not ship it and --explain would silently annotate nothing"
    )


@pytest.mark.unit
def test_the_shipped_copy_is_the_committed_one():
    """Fails if the packaged path drifts from the authored source of truth."""
    from seshat.rule_fix_table import FIXES_REL

    assert FIXES_REL.as_posix() == "docs/rules/rule-fixes.yaml"
    assert (REPO_ROOT / FIXES_REL).is_file()
