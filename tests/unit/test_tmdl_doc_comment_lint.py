"""Unit tests for the ///-must-attach TMDL lint (#494).

Deterministic: pure text and tmp_path files. No Power BI, no .NET, no network --
ADR 0001's headless boundary is a property of the module under test, so these
tests would fail if it were ever crossed.

The headline test (`test_exact_defect_from_issue_494`) reproduces the defect
verbatim from the issue: a `///` block at the top of a `relationships.tmdl`
followed by a blank line, which made Desktop reject the whole project with
`InvalidLineType / Unexpected line type: Empty!`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.tmdl_doc_comment_lint import (
    FINDING_DOC_COMMENT_NOT_ATTACHED,
    collect_tmdl_files,
    lint_model,
    lint_text,
)

pytestmark = pytest.mark.unit


# The defect exactly as issue #494 reports it: two /// lines, then the blank at
# line 5 the parser died on, then the relationship it was meant to document.
_ISSUE_494_RELATIONSHIPS = (
    "/// Star relationships: many-to-one from the fact to each dimension, single\n"
    "/// filter direction (the default). Each fromColumn is the fact's surrogate\n"
    "/// key; each toColumn is the dimension's primary key.\n"
    "\n"
    "relationship fct_to_dim_product\n"
    "\tfromColumn: 'gold fct_sales_c086'.product_sk\n"
    "\ttoColumn: 'gold dim_product_c086'.product_sk\n"
)

_ATTACHED_RELATIONSHIPS = (
    "/// Star relationships: many-to-one from the fact to each dimension, single\n"
    "/// filter direction (the default).\n"
    "relationship fct_to_dim_product\n"
    "\tfromColumn: 'gold fct_sales_c086'.product_sk\n"
    "\ttoColumn: 'gold dim_product_c086'.product_sk\n"
)


def _model(tmp_path: Path, name: str, text: str, *, encoding: str = "utf-8") -> Path:
    model_dir = tmp_path / "Demo.SemanticModel"
    target = model_dir / "definition" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding=encoding)
    return model_dir


# --------------------------------------------------------------------------
# The exact defect from the issue
# --------------------------------------------------------------------------


def test_exact_defect_from_issue_494(tmp_path: Path) -> None:
    """The reported defect blocks, and names the file and the offending blank."""
    model_dir = _model(tmp_path, "relationships.tmdl", _ISSUE_494_RELATIONSHIPS)
    result = lint_model(model_dir)
    assert result.status == "blocked"
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.kind == FINDING_DOC_COMMENT_NOT_ATTACHED
    assert finding.document.endswith("definition/relationships.tmdl")
    # The block's last /// line is 3; the blank Desktop reported is line 4 here
    # (the issue's line 5 counted its file's extra leading content).
    assert finding.doc_line == 3
    assert finding.blank_line == 4
    assert "must attach directly" in finding.message


def test_removing_the_blank_line_clears_the_finding(tmp_path: Path) -> None:
    """The fix the reporter applied (delete the blank) makes the lint pass."""
    model_dir = _model(tmp_path, "relationships.tmdl", _ATTACHED_RELATIONSHIPS)
    result = lint_model(model_dir)
    assert result.status == "pass"
    assert result.findings == ()


def test_defect_survives_a_utf8_bom(tmp_path: Path) -> None:
    """Power BI writes UTF-8-with-BOM; a BOM must not hide a line-1 /// block."""
    model_dir = _model(
        tmp_path, "relationships.tmdl", _ISSUE_494_RELATIONSHIPS, encoding="utf-8-sig"
    )
    result = lint_model(model_dir)
    assert result.status == "blocked"
    assert result.findings[0].doc_line == 3


# --------------------------------------------------------------------------
# Correctly-attached blocks stay silent
# --------------------------------------------------------------------------


def test_attached_measure_doc_is_silent() -> None:
    """The shape used throughout this repo's committed TMDL: an indented block."""
    text = (
        "table 'gold fct_sales_rss'\n"
        "\tlineageTag: b8181b29\n"
        "\n"
        "\t/// Total money taken across all retail transactions.\n"
        "\tmeasure TotalSales = SUM('gold fct_sales_rss'[total_spent])\n"
        "\t\tformatString: #,0.00\n"
    )
    assert lint_text(text, document="t.tmdl") == ()


def test_multi_line_block_is_one_block_not_many() -> None:
    """A run of /// lines reports at most once, at its attachment point."""
    text = '/// one\n/// two\n/// three\n\nexpression Server = "h"\n'
    findings = lint_text(text, document="e.tmdl")
    assert len(findings) == 1
    assert findings[0].doc_line == 3


def test_attached_expression_doc_is_silent() -> None:
    """Matches committed `expressions.tmdl`: doc, declaration, blank, doc, ..."""
    text = (
        "/// Postgres host:port. Real value supplied at refresh.\n"
        'expression Server = "<your-db-host>:25060"\n'
        "\tlineageTag: 5d36ae75\n"
        "\n"
        "/// Postgres database name.\n"
        'expression Database = "<your-database>"\n'
    )
    assert lint_text(text, document="expressions.tmdl") == ()


def test_a_file_with_no_doc_comments_is_silent() -> None:
    text = "table Sales\n\tcolumn Amount\n\t\tdataType: decimal\n\n"
    assert lint_text(text, document="t.tmdl") == ()


# --------------------------------------------------------------------------
# Edge cases: EOF, whitespace-only, CRLF
# --------------------------------------------------------------------------


def test_doc_block_at_eof_blocks() -> None:
    """A trailing /// documents nothing -- there is no next line to attach to."""
    text = "table Sales\n\tcolumn Amount\n/// dangling documentation\n"
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1
    assert findings[0].blank_line is None
    assert "end of file" in findings[0].message


def test_doc_block_at_eof_without_trailing_newline_blocks() -> None:
    text = "table Sales\n/// dangling"
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1
    assert findings[0].blank_line is None


def test_whitespace_only_following_line_counts_as_blank() -> None:
    """Tabs/spaces are indentation, not content -- Desktop still says Empty!."""
    text = "/// doc\n\t   \nmeasure M = 1\n"
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1
    assert findings[0].blank_line == 2


def test_crlf_input_is_handled_by_splitlines() -> None:
    """CRLF files are normal here; splitlines() consumes the terminator, so the
    blank line between a /// block and its object is still seen as blank."""
    text = "/// doc\r\n\r\nmeasure M = 1\r\n"
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1
    assert findings[0].blank_line == 2


def test_two_independent_violations_are_both_reported() -> None:
    text = "/// a\n\nmeasure M = 1\n\n/// b\n\nmeasure N = 2\n"
    findings = lint_text(text, document="t.tmdl")
    assert [f.doc_line for f in findings] == [1, 5]


# --------------------------------------------------------------------------
# Enumeration: the whole definition/ tree, not just tables/
# --------------------------------------------------------------------------


def test_enumeration_covers_relationships_not_just_tables(tmp_path: Path) -> None:
    """A tables/-only walk is exactly why the #494 defect went uncaught."""
    model_dir = tmp_path / "Demo.SemanticModel"
    (model_dir / "definition" / "tables").mkdir(parents=True)
    (model_dir / "definition" / "relationships.tmdl").write_text(
        "x\n", encoding="utf-8"
    )
    (model_dir / "definition" / "tables" / "t.tmdl").write_text("y\n", encoding="utf-8")
    (model_dir / "definition" / "model.tmdl").write_text("z\n", encoding="utf-8")
    names = [p.name for p in collect_tmdl_files(model_dir)]
    assert "relationships.tmdl" in names
    assert "t.tmdl" in names
    assert "model.tmdl" in names


def test_non_tmdl_files_are_ignored(tmp_path: Path) -> None:
    model_dir = _model(tmp_path, "model.tmdl", "table Sales\n")
    (model_dir / "definition" / "notes.md").write_text("/// doc\n\n", encoding="utf-8")
    assert lint_model(model_dir).status == "pass"


# --------------------------------------------------------------------------
# Fail-closed inputs
# --------------------------------------------------------------------------


def test_missing_model_dir_is_blocked(tmp_path: Path) -> None:
    result = lint_model(tmp_path / "Absent.SemanticModel")
    assert result.status == "blocked"
    assert any("not found" in line for line in result.evidence)


def test_model_with_no_tmdl_is_blocked_not_passed(tmp_path: Path) -> None:
    """Checking nothing must not look like checking successfully."""
    model_dir = tmp_path / "Demo.SemanticModel"
    (model_dir / "definition").mkdir(parents=True)
    result = lint_model(model_dir)
    assert result.status == "blocked"
    assert any("nothing was checked" in line for line in result.evidence)


# --------------------------------------------------------------------------
# The narrow-scope contract itself
# --------------------------------------------------------------------------


def test_result_grants_no_approval_and_has_no_way_to(tmp_path: Path) -> None:
    model_dir = _model(tmp_path, "relationships.tmdl", _ATTACHED_RELATIONSHIPS)
    result = lint_model(model_dir)
    assert result.grants_approval is False
    for name in dir(result):
        assert "approve" not in name.lower()
        assert "grant" not in name.lower() or name == "grants_approval"


def test_evidence_disclaims_being_a_syntax_validator(tmp_path: Path) -> None:
    """A pass must carry its own boundary, so it cannot be over-read (#494)."""
    model_dir = _model(tmp_path, "relationships.tmdl", _ATTACHED_RELATIONSHIPS)
    joined = " ".join(lint_model(model_dir).evidence)
    assert "NOT a TMDL syntax validator" in joined
    assert "Desktop" in joined


def test_a_syntax_defect_this_lint_does_not_cover_still_passes() -> None:
    """Honesty check: garbage TMDL with no /// problem is NOT this lint's job.

    Pinned deliberately. If someone later widens this into a general validator,
    this test fails and forces them to revisit the name and the disclaimers
    rather than silently growing the claim (the #494 over-claim, recreated).
    """
    text = "table Sales\n\t!!! this is not valid TMDL at all @@@\n"
    assert lint_text(text, document="t.tmdl") == ()
