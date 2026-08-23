"""`--explain` annotates each finding with the rule's own means/fix guidance.

An agent that reads `[error] D8 ... (model.tmdl:12)` has the rule id but not what it
means or where to fix it; that guidance already exists, authored per id in
`docs/rules/rule-fixes.yaml` and covering every registered rule as a bijection
(`test_rule_fix_table.py`). Before this flag the only way to reach it was to leave the
failure and open the `retail-govern` skill.

The flag is ADDITIVE and display-only. Two properties carry that claim:

* the annotation never changes the verdict -- exit code and every existing
  `[severity] id message (locator)` line are byte-identical with and without it, so
  the text contract `run`'s docstring pins (CI diffs against it) still holds; and
* guidance stays out of the gate -- `rule-fixes.yaml` says in its own header that
  `seshat check` never reads it, because reader guidance must not become gate input.
  Rendering it is not consulting it, and an id with no guidance renders exactly as it
  does today rather than inventing a line.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.core import Finding, RegisteredRule, RuleContext, Severity
from seshat.runner import explain_renderer, run


def _ctx() -> RuleContext:
    return RuleContext(repo_root=Path("."), tracked_files=())


def _rules(*findings: Finding) -> tuple[RegisteredRule, ...]:
    return tuple(
        RegisteredRule(id=f.rule_id, rule=lambda ctx, _f=f: [_f], title=f.rule_id)
        for f in findings
    )


# The guidance a test supplies, in `load_guidance`'s shape: id -> {means, fix}.
_GUIDANCE = {
    "D8": {
        "means": "A model partition sources from outside `gold`",
        "fix": "Repoint the partition at a `gold` object (`model.tmdl`)",
    }
}


@pytest.mark.unit
def test_explain_appends_the_rules_means_and_fix(capsys):
    """Fails until `run` accepts `explain=` and renders the guidance lines."""
    findings = (Finding("D8", Severity.ERROR, "bad partition", "model.tmdl:12"),)

    run(_rules(*findings), _ctx(), annotate=explain_renderer(_GUIDANCE))

    out = capsys.readouterr().out
    assert "A model partition sources from outside `gold`" in out
    assert "Repoint the partition at a `gold` object (`model.tmdl`)" in out


@pytest.mark.unit
def test_explain_leaves_the_finding_line_byte_identical(capsys):
    """Fails if the annotation rewrites, indents or wraps the existing line."""
    findings = (Finding("D8", Severity.ERROR, "bad partition", "model.tmdl:12"),)

    run(_rules(*findings), _ctx())
    plain = capsys.readouterr().out.splitlines()

    run(_rules(*findings), _ctx(), annotate=explain_renderer(_GUIDANCE))
    annotated = capsys.readouterr().out.splitlines()

    assert plain == ["[error] D8 bad partition (model.tmdl:12)"]
    assert annotated[0] == plain[0]
    assert len(annotated) > len(plain), "explain must add lines, not replace them"


@pytest.mark.unit
def test_explain_does_not_change_the_exit_code(capsys):
    """Fails if guidance lookup ever feeds the verdict -- the gate-input boundary."""
    error = Finding("D8", Severity.ERROR, "bad partition", "model.tmdl:12")
    warning = Finding("D8", Severity.WARNING, "soft", "model.tmdl:13")

    for finding in (error, warning):
        rules = _rules(finding)
        assert run(rules, _ctx()) == run(
            rules, _ctx(), annotate=explain_renderer(_GUIDANCE)
        )
    capsys.readouterr()


@pytest.mark.unit
@pytest.mark.parametrize("entry", ["unfinished", ["a"], 7, None])
def test_a_malformed_entry_degrades_instead_of_crashing(capsys, entry):
    """Fails while a non-mapping entry reaches `.get` and raises AttributeError.

    Valid YAML can still hold a half-edited entry (`rules: {D8: "unfinished"}`).
    The promise is fail-soft, so that must render as an unannotated finding, not
    a traceback out of a display-only path.
    """
    findings = (Finding("D8", Severity.ERROR, "bad partition", "model.tmdl:12"),)

    run(_rules(*findings), _ctx(), annotate=explain_renderer({"D8": entry}))

    assert capsys.readouterr().out == "[error] D8 bad partition (model.tmdl:12)\n"


@pytest.mark.unit
def test_unknown_id_renders_exactly_as_it_does_without_explain(capsys):
    """Fails if a missing entry emits a placeholder instead of staying silent."""
    findings = (Finding("ZZ9", Severity.WARNING, "no guidance", "x.yaml:1"),)

    run(_rules(*findings), _ctx())
    plain = capsys.readouterr().out

    run(_rules(*findings), _ctx(), annotate=explain_renderer(_GUIDANCE))
    annotated = capsys.readouterr().out

    assert annotated == plain


@pytest.mark.unit
def test_without_an_annotator_guidance_is_never_rendered(capsys):
    """Fails if the annotation leaks into the default output CI diffs against."""
    findings = (Finding("D8", Severity.ERROR, "bad partition", "model.tmdl:12"),)

    run(_rules(*findings), _ctx())

    assert "Repoint the partition" not in capsys.readouterr().out
