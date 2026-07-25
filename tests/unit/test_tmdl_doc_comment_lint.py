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
    embedded_body_lines,
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
# Embedded M/DAX bodies: `///` there is a legal line comment, NOT TMDL doc.
#
# Found in review on PR #503. Both directions are pinned: the false positive
# must not fire (blocking a VALID model is worse than a missed detection for a
# brand-new lint), and the real rule must not be blunted while fixing it.
# --------------------------------------------------------------------------


# The shape the committed corpus actually uses: `source =` at indent 2, body
# indented strictly deeper. `///` is a legal M comment and M bodies may contain
# blank lines, so this VALID model must produce no finding.
_VALID_M_BODY = (
    "table 'gold fct_sales_rss'\n"
    "\tpartition 'gold fct_sales_rss' = m\n"
    "\t\tmode: import\n"
    "\t\tsource =\n"
    "\t\t\t\tlet\n"
    "\t\t\t\t  /// pull the gold star; host+db come from parameters\n"
    "\n"
    "\t\t\t\t  Source = PostgreSQL.Database(Server, Database),\n"
    '\t\t\t\t  #"Navigation 1" = Source{[Schema = "gold"]}[Data]\n'
    "\t\t\t\tin\n"
    '\t\t\t\t  #"Navigation 1"\n'
)


def test_doc_marker_inside_m_source_body_is_not_flagged() -> None:
    """THE false positive: `///` + blank inside an M body must stay silent."""
    assert lint_text(_VALID_M_BODY, document="t.tmdl") == ()


def test_doc_marker_inside_multiline_dax_measure_body_is_not_flagged() -> None:
    """`//` starts a DAX comment too, so `///` is legal inside a measure body."""
    text = (
        "table Sales\n"
        "\tmeasure Margin =\n"
        "\t\t\tVAR Rev = SUM(Sales[amount])\n"
        "\t\t\t/// denominator excludes unknowns\n"
        "\n"
        "\t\t\tVAR Cost = SUM(Sales[cost])\n"
        "\t\t\tRETURN DIVIDE(Rev - Cost, Rev)\n"
    )
    assert lint_text(text, document="t.tmdl") == ()


def test_genuine_indented_measure_doc_is_still_checked() -> None:
    """Do not over-correct: an INDENTED doc is real TMDL documentation (the
    shape this repo's committed TMDL uses), so it is still subject to the rule."""
    text = (
        "table 'gold fct_sales_rss'\n"
        "\tlineageTag: b8181b29\n"
        "\n"
        "\t/// Total money taken across all retail transactions.\n"
        "\n"
        "\tmeasure TotalSales = SUM('gold fct_sales_rss'[total_spent])\n"
    )
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1
    assert findings[0].doc_line == 4


def test_body_closes_on_dedent_so_later_top_level_doc_is_still_flagged() -> None:
    """The anti-blunting guard: a "suppress everything after the first `=`"
    bug would silently kill the whole rule and STILL show a clean census."""
    text = (
        "table 'gold fct_sales_rss'\n"
        "\tpartition p = m\n"
        "\t\tsource =\n"
        "\t\t\t\tlet\n"
        "\t\t\t\t  /// legal M comment\n"
        "\n"
        "\t\t\t\t  Source = X\n"
        "\t\t\t\tin\n"
        "\t\t\t\t  Source\n"
        "\n"
        "\tannotation PBI_NavigationStepName = Navigation\n"
        "\n"
        "/// a genuinely unattached top-level block\n"
        "\n"
        "relationship r\n"
    )
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1, findings
    assert findings[0].doc_line == 13
    assert findings[0].blank_line == 14


def test_blank_line_does_not_close_a_body() -> None:
    """Pinned so nobody "simplifies" blank-transparency away: real body content
    follows the blank, and the `///` before it must stay unflagged."""
    lines = _VALID_M_BODY.splitlines()
    inside = embedded_body_lines(lines)
    # index 5 is the `///` comment, index 7 the body content after the blank.
    assert 5 in inside
    assert 7 in inside


def test_property_lines_do_not_swallow_a_following_top_level_doc() -> None:
    """`expression X = "v"`, `annotation X = Y` and `partition p = m` DO open a
    body (their property lines are indented deeper), but that body closes at the
    dedent -- so a later top-level `///` is still reached and still checked.

    Deliberately NOT asserted as "these open no body": they do. `expression
    Server = "..."` at indent 0 is followed by `lineageTag:` at indent 1, which
    is deeper, so a body opens. Asserting otherwise would be a false claim.
    """
    text = (
        '/// Postgres host:port.\nexpression Server = "<host>:25060"\n'
        "\tlineageTag: 5d36ae75\n"
        "\n"
        "\tannotation PBI_ResultType = Text\n"
        "\n"
        "/// unattached, and must still be caught\n"
        "\n"
        "relationship r\n"
    )
    findings = lint_text(text, document="expressions.tmdl")
    assert len(findings) == 1
    assert findings[0].doc_line == 7


def test_committed_corpus_shape_has_no_findings(tmp_path: Path) -> None:
    """End-to-end on the real `source =` shape through lint_model."""
    model_dir = _model(tmp_path, "tables/fct.tmdl", _VALID_M_BODY)
    assert lint_model(model_dir).status == "pass"


# The VAR/RETURN idiom with the first DAX token kept INLINE on the declaration
# line. Found in a second review round on PR #503: an "ends with `=`" predicate
# matched ZERO real measures (every measure in this repo's committed TMDL is
# inline), so it left the false positive live one form over.
_INLINE_VAR_MEASURE = (
    "table Sales\n"
    "\tmeasure Margin = VAR Revenue = [Revenue]\n"
    "\t\t\tVAR Cost = SUM(Sales[cost])\n"
    "\t\t\t/// exclude unknown-status rows from the denominator\n"
    "\n"
    "\t\t\tRETURN DIVIDE(Revenue - Cost, Revenue)\n"
    "\t\tformatString: 0.0%\n"
)


def test_inline_first_token_measure_body_is_not_flagged() -> None:
    """A multiline measure keeping its first DAX token on the declaration line
    still opens a body, so an indented `///` inside it is not TMDL doc."""
    assert lint_text(_INLINE_VAR_MEASURE, document="t.tmdl") == ()


def test_inline_measure_body_closes_so_later_top_level_doc_is_flagged() -> None:
    """Body-exit guard for the inline form: the widened predicate must not
    swallow the rest of the file."""
    text = _INLINE_VAR_MEASURE + (
        "\n/// a genuinely unattached top-level block\n\nrelationship r\n"
    )
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1, findings
    assert findings[0].doc_line == 9


def test_single_line_inline_measures_stay_checkable() -> None:
    """The real corpus shape: single-line inline measures with attached docs.

    Their docs stay silent (correctly attached) and a genuinely unattached
    top-level block after them is still caught -- the widened predicate must not
    make the real committed shape unlintable.
    """
    text = (
        "table 'gold fct_sales_rss'\n"
        "\t/// Total money taken across all retail transactions.\n"
        "\tmeasure TotalSales = SUM('gold fct_sales_rss'[total_spent])\n"
        "\t\tformatString: #,0.00\n"
        "\n"
        "/// unattached top-level block, must be caught\n"
        "\n"
        "relationship r\n"
    )
    findings = lint_text(text, document="t.tmdl")
    assert len(findings) == 1, findings
    assert findings[0].doc_line == 6


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
