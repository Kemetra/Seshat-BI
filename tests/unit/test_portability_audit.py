"""`portability-audit-v1` is a GATE over shipping skill text, never a rewriter.

Spec 138 User Story 3, `contracts/portability-audit.md`.

The defect it prevents: a skill that reads `templates/source-map.yaml` works
perfectly in this repository and instructs a consumer agent to open a path their
workspace has never contained. The audit fails the export instead of shipping
that instruction.

The hard part is that classification is by INTENT, not by path. The same
`templates/` path is a defect in a bare read-instruction, correct in a
scaffold-output reference, and correct again when scoped to the development
repository -- so every test here pairs a failing and a permitted use of the SAME
path rather than asserting on the path alone.
"""

from __future__ import annotations

from typing import Any

import pytest

# A path no scaffolded workspace contains. `mappings/` is the counterpart the
# scaffold does create -- see `workspace_init._EMPTY_DIRS`.
UNSCAFFOLDED = "templates/source-map.yaml"
SCAFFOLDED = "mappings/retail_store_sales/source-map.yaml"


def _audit() -> Any:
    """The transform T047 must provide.

    Imported inside each test so its absence reads as the missing feature rather
    than collapsing the module into a collection error.
    """
    try:
        from seshat import portability_audit  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover -- the RED state
        pytest.fail(
            "portability-audit-v1 has no implementation: expected "
            "`seshat.portability_audit.audit_skill_text(skill, text) -> "
            f"list[Finding]` with fields skill/path/line/reason -- {exc}"
        )
    return portability_audit


def test_a_read_instruction_to_an_unscaffolded_path_fails() -> None:
    """Obligation 1 -- the defect the transform exists to catch."""
    audit = _audit()
    findings = audit.audit_skill_text(
        "source-mapping", f"Read `{UNSCAFFOLDED}` before you propose a grain.\n"
    )
    assert findings, (
        f"a bare read-instruction to {UNSCAFFOLDED} must fail the export: no "
        "scaffolded workspace contains it"
    )


def test_a_finding_reports_skill_path_line_and_reason() -> None:
    """Obligation 2 -- fixable without re-deriving the finding."""
    audit = _audit()
    text = f"Intro line.\nRead `{UNSCAFFOLDED}` before you propose a grain.\n"
    finding = audit.audit_skill_text("source-mapping", text)[0]
    assert finding.skill == "source-mapping"
    assert finding.path == UNSCAFFOLDED
    assert finding.line == 2, (
        "the line number must locate the instruction, not the file"
    )
    assert finding.reason, "a finding with no reason cannot be acted on"


def test_a_scaffold_output_reference_is_permitted() -> None:
    """Obligation 3, as narrowed by the owner ruling of 2026-07-31.

    The ruling ("name the scaffold verb") resolved eight findings without widening
    `_EMPTY_DIRS`: a shipped skill says "run <verb>, which writes this file"
    instead of instructing a read. That phrasing must pass.
    """
    audit = _audit()
    findings = audit.audit_skill_text(
        "source-mapping",
        f"Run `seshat scaffold`, which writes `{UNSCAFFOLDED}`, then fill it in.\n",
    )
    assert not findings, (
        "a reference naming an output a scaffold step produces must be permitted; "
        f"got {findings}"
    )


def test_a_development_scoped_reference_is_permitted() -> None:
    """Obligation 4 -- `source-mapping` line 35 is the working precedent."""
    audit = _audit()
    findings = audit.audit_skill_text(
        "source-mapping",
        f"`{UNSCAFFOLDED}` exists only in the Seshat development repo; skip it "
        "in a consumer workspace.\n",
    )
    assert not findings, f"an explicitly dev-scoped reference must pass; got {findings}"


def test_a_read_instruction_to_a_scaffolded_path_is_permitted() -> None:
    """The gate must not fire on paths a workspace genuinely has."""
    audit = _audit()
    findings = audit.audit_skill_text(
        "source-mapping", f"Read `{SCAFFOLDED}` and confirm the grain.\n"
    )
    assert not findings, (
        f"`mappings/` is created by the scaffold, so reading {SCAFFOLDED} is "
        f"legitimate; got {findings}"
    )


def test_presence_is_derived_from_workspace_init_not_duplicated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Obligation 5 -- and it MUST NOT carry its own duplicate list.

    Behavioural rather than source-inspecting: widen the scaffold and the same
    text must stop failing. A module-level copy of the tuple would survive this
    monkeypatch and keep failing, which is exactly the duplication the obligation
    forbids.
    """
    audit = _audit()
    from seshat import workspace_init  # noqa: PLC0415

    text = f"Read `{UNSCAFFOLDED}` before you propose a grain.\n"
    assert audit.audit_skill_text("source-mapping", text), "precondition"

    monkeypatch.setattr(
        workspace_init, "_EMPTY_DIRS", (*workspace_init._EMPTY_DIRS, "templates")
    )
    assert not audit.audit_skill_text("source-mapping", text), (
        "the audit must read the scaffold shape from "
        "`workspace_init._EMPTY_DIRS` at call time, not copy it"
    )


def test_classification_is_by_intent_not_by_path_prefix() -> None:
    """Prohibition -- a prefix rule is wrong in both directions.

    Two references to the SAME prefix in one skill: one bare read-instruction and
    one dev-scoped. A prefix rule flags both or neither; only an intent rule
    separates them.
    """
    audit = _audit()
    findings = audit.audit_skill_text(
        "source-mapping",
        f"`{UNSCAFFOLDED}` exists only in the Seshat development repo.\n"
        f"Read `templates/kpi-contract.yaml` before you begin.\n",
    )
    assert [f.path for f in findings] == ["templates/kpi-contract.yaml"], (
        "the dev-scoped reference must pass and the bare read-instruction under "
        f"the same prefix must fail; got {findings}"
    )


def test_an_incidental_production_word_does_not_excuse_a_read_instruction() -> None:
    """The scaffold-output exemption must not become a loophole.

    Obligation 3 is matched on production verbs rather than a closed list of
    phrases, so that "the record is written by that verb as `…`" passes. That
    breadth would otherwise exempt any sentence happening to contain "generated".
    A read verb therefore beats a production verb: this pins the boundary that the
    broadening could quietly have moved.
    """
    audit = _audit()
    findings = audit.audit_skill_text(
        "source-mapping",
        f"Read `{UNSCAFFOLDED}`, generated last quarter, before you begin.\n",
    )
    assert findings, (
        "a read-instruction must still fail when its sentence merely mentions that "
        "something was generated"
    )


def test_no_inline_suppression_is_honoured() -> None:
    """Prohibition -- a suppression mechanism recreates silent divergence.

    A finding is resolved by rewriting canonical text or by not shipping the
    skill; never by marking it.
    """
    audit = _audit()
    findings = audit.audit_skill_text(
        "source-mapping",
        f"Read `{UNSCAFFOLDED}` before you begin. <!-- portability-audit: ignore -->\n",
    )
    assert findings, "an inline ignore marker must not suppress a finding"


def test_the_module_exposes_no_rewriting_entry_point() -> None:
    """Prohibition -- it MUST NOT modify content (FR-018).

    Rewriting at export time would let a generated skill diverge silently from
    its canonical source, destroying the single-source property the design rests
    on. The gate therefore has no repair surface at all.
    """
    audit = _audit()
    # Token-wise, not substring: a substring match reports `scaffolded_prefixes`
    # because "prefixes" contains "fix", which is a defect in the test rather
    # than a rewriting entry point in the module.
    verbs = ("rewrite", "fix", "repair", "apply")
    rewriters = sorted(
        name
        for name in dir(audit)
        if not name.startswith("_")
        and any(
            token.startswith(verb)
            for token in name.lower().split("_")
            for verb in verbs
        )
    )
    assert not rewriters, (
        f"the audit is a gate, not a rewriter, but exposes: {rewriters}"
    )
