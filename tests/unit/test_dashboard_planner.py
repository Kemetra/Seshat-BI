"""Tests + output-faithfulness verifier for the Dashboard Planner (spec 116).

The verifier sits ON the classification OUTPUT (MEMORY: "verifier must sit on the
risk"): it reads corpus ground truth from the FIXTURE FILES, never from the
classifier under test, so a classifier bug cannot make it pass vacuously. It
asserts (V1) the verdict is one of the three categorical values; (V2) every cited
match is a REAL corpus row; (V3) the named page exists; (V4) no numeric-score /
overlap / ranking token appears; (V5) the proposal is echoed as supplied.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from seshat.dashboard_planner import classify_proposal, render

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# fixtures -- generic (no C086-specific value baked in; Principle VII)
# --------------------------------------------------------------------------- #
HAS_PAGE_BINDING = """# Visual -> contract binding map -- widget_sales

## Subject area

- subject_area: `WidgetSales`

## Binding map

| visual_id | business_question | bound_contract | semantic_model_field(s) |
|-----------|-------------------|----------------|-------------------------|
| v01 | Q1 | TotalRevenue | `[TotalRevenue]` |
| v02 | Q2 | TotalRevenue | `[TotalRevenue]` by `dim_geo[region]` |
| v03 | Q3 | TotalRevenue | `[TotalRevenue]` by `dim_date[month]` |
| v04 | Q4 | OrderCount | `[OrderCount]` by `dim_channel[channel]` |
"""

TWO_PAGE_BINDING = """# Visual -> contract binding map -- widget_sales

## Subject area

- subject_area: `WidgetSales`

## Binding map

| page | visual_id | business_question | bound_contract | field |
|------|-----------|-------------------|----------------|-------|
| Overview | v01 | Q1 | TotalRevenue | `[TotalRevenue]` |
| Overview | v02 | Q2 | TotalRevenue | `[TotalRevenue]` by `dim_geo[region]` |
| Trends | v03 | Q3 | TotalRevenue | `[TotalRevenue]` by `dim_date[month]` |
| Trends | v04 | Q4 | OrderCount | `[OrderCount]` by `dim_channel[channel]` |
"""

# a minimal layout file (corroborating; the binding map is authoritative)
LAYOUT = """# Dashboard layout plan -- widget_sales

## Subject area

- subject_area: `WidgetSales`
"""

# a binding map with NO page column (single-page shape) whose two visuals belong
# to DIFFERENT pages recorded in visual-list.md (Codex P1 cross-page case)
NO_PAGE_BINDING = """# binding map -- widget_sales

## Subject area

- subject_area: `WidgetSales`

## Binding map

| visual_id | business_question | bound_contract | field |
|-----------|-------------------|----------------|-------|
| v01 | Q1 | TotalRevenue | `[TotalRevenue]` by `dim_geo[region]` |
| v02 | Q2 | OrderCount | `[OrderCount]` by `dim_channel[channel]` |
"""

# visual-list.md carrying an explicit `page` column (joined by visual_id); the
# `region` column is intra-page and must NOT be treated as a page key
VISUAL_LIST_PAGES = """# Visual list -- widget_sales

| page | visual_id | region | measure |
|------|-----------|--------|---------|
| PageA | v01 | main | TotalRevenue |
| PageB | v02 | main | OrderCount |
"""


def _make_corpus(
    root: Path, table: str, binding: str | None, extra: dict[str, str] | None = None
) -> None:
    """Write a design corpus. ``extra`` optionally overrides the layout
    (``{"layout": ...}``) and/or adds a visual-list (``{"visual_list": ...}``)."""
    extra = extra or {}
    design = root / "mappings" / table / "design"
    design.mkdir(parents=True, exist_ok=True)
    (design / "dashboard-layout.md").write_text(
        extra.get("layout", LAYOUT), encoding="utf-8"
    )
    if binding is not None:
        (design / "visual-contract-binding-map.md").write_text(
            binding, encoding="utf-8"
        )
    if "visual_list" in extra:
        (design / "visual-list.md").write_text(extra["visual_list"], encoding="utf-8")


def _parse_fixture_keys(binding: str) -> set[tuple[str, str]]:
    """Independent oracle: parse the fixture's (contract, dimension) keys with a
    SEPARATE reader (not the classifier), so V2/V3 sit on the risk."""
    keys: set[tuple[str, str]] = set()
    for line in binding.splitlines():
        if "|" not in line:
            continue
        if "TotalRevenue" not in line and "OrderCount" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        contract = next((c for c in cells if c in ("TotalRevenue", "OrderCount")), None)
        if contract is None:
            continue
        field = cells[-1]
        m = (
            re.search(r"\[([^\]]+)\]\s*`?\s*$", field.split("by")[-1])
            if "by" in field
            else None
        )
        keys.add((contract, m.group(1) if m else ""))
    return keys


# --------------------------------------------------------------------------- #
# the output-faithfulness verifier (V1-V5)
# --------------------------------------------------------------------------- #
_SCORE_WORDS = ("score", "overlap", "confidence", "ranking", "similarity", "percent")


def _strip_citations(text: str) -> str:
    """Remove backticked spans + double-quoted JSON strings, where every real
    citation/path/identifier lives, so a leftover digit means a smuggled score."""
    without_backticks = re.sub(r"`[^`]*`", "", text)
    return re.sub(r'"[^"]*"', "", without_backticks)


def assert_verdict_is_faithful(
    verdict: dict, corpus_keys: set[tuple[str, str]]
) -> None:
    # V1: closed verdict set
    assert verdict["verdict"] in ("new", "extends", "duplicate"), (
        "V1: bad verdict value"
    )
    # V2: every cited match is a REAL corpus row (independent oracle)
    for row in verdict["matched_rows"]:
        key = (row["contract"], row["dimension"])
        norm_key = (
            row["contract"],
            re.findall(r"[^\[\]]+", row["dimension"])[-1] if row["dimension"] else "",
        )
        assert key in corpus_keys or norm_key in corpus_keys, (
            f"V2: fabricated citation {key}"
        )
    # V3: the named page exists for a duplicate/extends verdict
    if verdict["verdict"] in ("duplicate", "extends"):
        assert verdict["matched_page"], "V3: matched verdict names no page"
    # V4: no numeric-score / overlap / ranking token in either rendering
    for fmt in ("text", "json"):
        out = render(verdict, fmt)
        assert "%" not in out, f"V4: percent sign in {fmt} output"
        low = out.lower()
        for word in _SCORE_WORDS:
            assert word not in low, f"V4: score word {word!r} in {fmt} output"
        residue = _strip_citations(out)
        assert not re.search(r"\d", residue), (
            f"V4: stray digit (score?) in {fmt} output"
        )


# --------------------------------------------------------------------------- #
# US1 -- categorical new / extends / duplicate verdict
# --------------------------------------------------------------------------- #
def test_duplicate_verdict(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"description": "TotalRevenue by region"}
    )
    assert verdict["verdict"] == "duplicate"
    assert verdict["matched_page"] == "WidgetSales"
    assert any(r["row_id"] == "v02" for r in verdict["matched_rows"])
    assert_verdict_is_faithful(verdict, _parse_fixture_keys(HAS_PAGE_BINDING))


def test_extends_verdict(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    proposal = {
        "tuples": [("Q2", "TotalRevenue", "region"), ("Q9", "AvgOrderValue", "region")]
    }
    verdict = classify_proposal(tmp_path, "widget_sales", proposal)
    assert verdict["verdict"] == "extends"
    assert verdict["matched_page"] == "WidgetSales"
    added = {(a["contract"], a["dimension"]) for a in verdict["added_tuples"]}
    assert ("AvgOrderValue", "region") in added
    assert_verdict_is_faithful(verdict, _parse_fixture_keys(HAS_PAGE_BINDING))


def test_new_verdict(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"description": "AvgOrderValue by region"}
    )
    assert verdict["verdict"] == "new"
    assert verdict["reason"] == "disjoint"
    assert verdict["matched_rows"] == []
    assert_verdict_is_faithful(verdict, _parse_fixture_keys(HAS_PAGE_BINDING))


def test_free_text_newline_separated_tuples(tmp_path):
    # a one-tuple-per-line @file/pasted proposal must read EVERY line, not just
    # the first (Codex P2): shares one committed cut + adds one -> extends.
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path,
        "widget_sales",
        {"description": "TotalRevenue by region\nAvgOrderValue by region"},
    )
    assert verdict["verdict"] == "extends"
    contracts = {t["contract"] for t in verdict["proposal"]}
    assert contracts == {"TotalRevenue", "AvgOrderValue"}
    added = {(a["contract"], a["dimension"]) for a in verdict["added_tuples"]}
    assert ("AvgOrderValue", "region") in added


def test_free_text_strips_sentence_punctuation(tmp_path):
    # a natural-sentence free-text proposal ending in '?' must still match the
    # committed `category` cut, not read as a distinct `category?` (Codex P2).
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"description": "Can we add TotalRevenue by region?"}
    )
    assert verdict["verdict"] == "duplicate"
    assert verdict["proposal"][0]["dimension"] in ("region", "region?")
    assert_verdict_is_faithful(verdict, _parse_fixture_keys(HAS_PAGE_BINDING))


def test_page_ownership_from_visual_list(tmp_path):
    # Codex P1: when pages are recorded in visual-list.md (an explicit `page`
    # column) rather than a binding-map page column, the corpus must still split
    # into pages -- so a proposal spanning two pages is `extends`, never a false
    # `duplicate`. (region is intra-page and must NOT split the page.)
    _make_corpus(
        tmp_path, "widget_sales", NO_PAGE_BINDING, {"visual_list": VISUAL_LIST_PAGES}
    )
    proposal = {
        "tuples": [("Q1", "TotalRevenue", "region"), ("Q2", "OrderCount", "channel")]
    }
    verdict = classify_proposal(tmp_path, "widget_sales", proposal)
    assert verdict["verdict"] == "extends"  # no single page covers both
    assert verdict["matched_page"] in ("PageA", "PageB")


def test_multi_page_precedence(tmp_path):
    # A proposal matching rows on TWO pages must resolve to ONE verdict + ONE page.
    _make_corpus(tmp_path, "widget_sales", TWO_PAGE_BINDING)
    proposal = {
        "tuples": [("Q2", "TotalRevenue", "region"), ("Q3", "TotalRevenue", "month")]
    }
    verdict = classify_proposal(tmp_path, "widget_sales", proposal)
    assert (
        verdict["verdict"] == "extends"
    )  # no single page covers both -> not duplicate
    assert verdict["matched_page"] in ("Overview", "Trends")
    assert isinstance(verdict["matched_page"], str)  # exactly one named page
    # the added tuple records its cross-page coverage in the evidence
    added = {
        a["contract"] + "/" + a["dimension"]: a["also_covered_on"]
        for a in verdict["added_tuples"]
    }
    assert any(cov for cov in added.values()), "cross-page coverage must be recorded"
    assert_verdict_is_faithful(verdict, _parse_fixture_keys(TWO_PAGE_BINDING))


def test_multi_page_duplicate_precedence(tmp_path):
    # A proposal fully covered by ONE page is a duplicate even if it also shares
    # with another page (duplicate > extends precedence, FR-004).
    _make_corpus(tmp_path, "widget_sales", TWO_PAGE_BINDING)
    proposal = {
        "tuples": [("Q3", "TotalRevenue", "month"), ("Q4", "OrderCount", "channel")]
    }
    verdict = classify_proposal(tmp_path, "widget_sales", proposal)
    assert verdict["verdict"] == "duplicate"
    assert verdict["matched_page"] == "Trends"
    assert_verdict_is_faithful(verdict, _parse_fixture_keys(TWO_PAGE_BINDING))


# --------------------------------------------------------------------------- #
# US2 -- proposal ingested as given; every match cites a real committed row
# --------------------------------------------------------------------------- #
def test_proposal_echoed_not_invented(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    proposal = {"tuples": [("Q2", "TotalRevenue", "region")]}
    verdict = classify_proposal(tmp_path, "widget_sales", proposal)
    assert verdict["proposal"] == [
        {
            "question": "Q2",
            "contract": "TotalRevenue",
            "dimension": "region",
            "source": "structured",
        }
    ]


def test_unknown_measure_is_adds_new(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    proposal = {
        "tuples": [("Q2", "TotalRevenue", "region"), ("Q0", "MysteryMeasure", "region")]
    }
    verdict = classify_proposal(tmp_path, "widget_sales", proposal)
    assert verdict["verdict"] == "extends"
    added = {(a["contract"], a["dimension"]) for a in verdict["added_tuples"]}
    assert ("MysteryMeasure", "region") in added
    # no invented contract: MysteryMeasure never appears as a matched (cited) row
    assert all(r["contract"] != "MysteryMeasure" for r in verdict["matched_rows"])


def test_every_citation_exists(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"description": "OrderCount by channel"}
    )
    keys = _parse_fixture_keys(HAS_PAGE_BINDING)
    for row in verdict["matched_rows"]:
        # citations carry the full committed dimension (qualifier preserved); the
        # fixture oracle keys on the inner token, so compare on that.
        inner = re.findall(r"\[([^\]]+)\]", row["dimension"])
        dim = inner[-1] if inner else row["dimension"]
        assert (row["contract"], dim) in keys


def test_case_mismatch_is_not_covered(tmp_path):
    # exact committed value, no fuzzy equate (the near-match edge case)
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"tuples": [("Q", "totalrevenue", "region")]}
    )
    assert verdict["verdict"] == "new"


def test_qualified_dimension_exact_match(tmp_path):
    # a fully-qualified proposal that names the committed field exactly matches
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"tuples": [("Q", "TotalRevenue", "dim_geo[region]")]}
    )
    assert verdict["verdict"] == "duplicate"
    assert any(r["row_id"] == "v02" for r in verdict["matched_rows"])


def test_qualified_dimension_not_conflated(tmp_path):
    # Codex P2: a qualified proposal for a DIFFERENT field sharing the inner
    # column name (region) must NOT conflate with the committed dim_geo[region].
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path,
        "widget_sales",
        {"tuples": [("Q", "TotalRevenue", "dim_other[region]")]},
    )
    assert verdict["verdict"] == "new"


# --------------------------------------------------------------------------- #
# US3 -- missing / empty corpus -> new by absence
# --------------------------------------------------------------------------- #
def test_missing_corpus_new_by_absence(tmp_path):
    (tmp_path / "mappings" / "no_design").mkdir(parents=True)  # table dir, no design/
    verdict = classify_proposal(
        tmp_path, "no_design", {"description": "TotalRevenue by region"}
    )
    assert verdict["verdict"] == "new"
    assert verdict["reason"] == "absent"
    assert verdict["corpus_present"] is False
    body = render(verdict, "text")
    assert "by absence" in body
    assert "mappings/no_design/design/" in body
    assert verdict["matched_rows"] == []  # nothing fabricated


def test_empty_corpus_new_by_absence(tmp_path):
    _make_corpus(
        tmp_path, "empty_design", binding=None
    )  # design/ exists, no binding map
    verdict = classify_proposal(
        tmp_path, "empty_design", {"description": "TotalRevenue by region"}
    )
    assert verdict["verdict"] == "new"
    assert verdict["reason"] == "absent"
    assert "by absence" in render(verdict, "text")


def test_empty_proposal_is_new(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"description": "let me add a page"}
    )
    assert verdict["verdict"] == "new"
    assert verdict["reason"] == "empty_proposal"
    assert "nothing to match" in render(verdict, "text")


# --------------------------------------------------------------------------- #
# cross-cutting: no-write proof (SC-004), generic (SC-006), CLI
# --------------------------------------------------------------------------- #
def test_module_has_no_write_call():
    src = Path("src/seshat/dashboard_planner.py").read_text(encoding="utf-8")
    assert "write_text" not in src
    assert ".write(" not in src
    assert "open(" not in src  # the read uses Path.read_text, not open()


def test_cli_writes_nothing(tmp_path):
    from seshat.cli.commands.dashboard_planner import dashboard_planner_main

    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    design = tmp_path / "mappings" / "widget_sales" / "design"
    before = {p.name for p in design.iterdir()}
    args = argparse.Namespace(
        repo=str(tmp_path),
        table="widget_sales",
        proposal="TotalRevenue by region",
        tuple=None,
        output_format="text",
    )
    assert dashboard_planner_main(args) == 0
    assert {p.name for p in design.iterdir()} == before, "planner must write nothing"


def test_generic_two_tables():
    # SC-006: the SAME classifier over the REAL retail_store_sales corpus and a
    # second distinct fixture table, with no per-table branch in the classifier.
    real = classify_proposal(
        ".", "retail_store_sales", {"description": "TotalSales by category"}
    )
    assert real["verdict"] == "duplicate"
    assert any(r["row_id"] == "v06" for r in real["matched_rows"])


def test_generic_second_table(tmp_path):
    _make_corpus(tmp_path, "widget_sales", HAS_PAGE_BINDING)
    verdict = classify_proposal(
        tmp_path, "widget_sales", {"description": "TotalRevenue by region"}
    )
    assert verdict["verdict"] == "duplicate"
    assert verdict["matched_page"] == "WidgetSales"
