"""The binding map is the authority on which contract a visual cites.

Increment A trusted an operator-written file for that, which meant a report could
be fully attributed and still wrong: nothing stopped an observations file from
pairing the revenue card with the discount-rate contract. These tests pin the
governed answer, and pin that a visual nobody bound refuses rather than resolving
to nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.report.binding import (
    BINDING_MAP_SCHEMA,
    binding_map_path,
    load_binding_map,
)
from seshat.report.model import ReportError

pytestmark = pytest.mark.unit

_REPO = Path(__file__).parents[2]

_MAP = """\
# Visual -> contract binding map -- demo

Prose a reviewer reads, which the parser must not mistake for the front section.

```yaml
schema: seshat.binding-map/v1
table: demo_table
visuals:
  - visual_id: v01
    page: overview
    contract: TotalSales
    headline: true
  - visual_id: v02
    page: overview
    contract: TransactionCount
    headline: false
```

| visual_id | bound_contract |
|-----------|----------------|
| v01 | TotalSales |
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "visual-contract-binding-map.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_front_section_is_found_among_prose(tmp_path: Path) -> None:
    binding_map = load_binding_map(_write(tmp_path, _MAP))
    assert binding_map.table == "demo_table"
    assert binding_map.visual_ids == ("v01", "v02")


def test_a_visual_resolves_to_its_governed_contract(tmp_path: Path) -> None:
    binding_map = load_binding_map(_write(tmp_path, _MAP))
    assert binding_map.contract_for("v01") == "TotalSales"
    assert binding_map.contract_for("v02") == "TransactionCount"


def test_an_unbound_visual_refuses_rather_than_returning_nothing(
    tmp_path: Path,
) -> None:
    """A silent None would let an unbound visual render as a pending figure,
    which reads as 'no data yet' rather than 'nobody approved this'."""
    binding_map = load_binding_map(_write(tmp_path, _MAP))
    with pytest.raises(ReportError, match="not bound"):
        binding_map.contract_for("v99")


def test_the_headline_flag_is_carried(tmp_path: Path) -> None:
    binding_map = load_binding_map(_write(tmp_path, _MAP))
    assert binding_map.binding_for("v01").headline is True
    assert binding_map.binding_for("v02").headline is False


def test_a_missing_map_refuses(tmp_path: Path) -> None:
    with pytest.raises(ReportError, match="no binding map"):
        load_binding_map(tmp_path / "absent.md")


def test_a_file_with_no_front_section_refuses(tmp_path: Path) -> None:
    """The prose table is not machine-readable; a map without the front section
    cannot be consumed, and guessing from the table would be worse."""
    with pytest.raises(ReportError, match="no .* front section"):
        load_binding_map(_write(tmp_path, "# just prose\n\nno fenced yaml here\n"))


def test_a_different_schema_version_refuses(tmp_path: Path) -> None:
    """A v2 map read by v1 code is a defect, not a compatible read."""
    text = _MAP.replace(BINDING_MAP_SCHEMA, "seshat.binding-map/v2")
    with pytest.raises(ReportError, match="no .* front section"):
        load_binding_map(_write(tmp_path, text))


def test_an_empty_visuals_list_refuses(tmp_path: Path) -> None:
    text = _MAP.replace(
        "visuals:\n  - visual_id: v01", "visuals: []\nunused:\n  - visual_id: v01"
    )
    with pytest.raises(ReportError, match="declares no visuals"):
        load_binding_map(_write(tmp_path, text))


def test_a_visual_with_no_contract_refuses(tmp_path: Path) -> None:
    text = _MAP.replace("    contract: TotalSales\n", "")
    with pytest.raises(ReportError, match="no contract"):
        load_binding_map(_write(tmp_path, text))


def test_a_duplicate_visual_id_refuses(tmp_path: Path) -> None:
    """Two bindings for one visual means the map does not decide, and a
    last-one-wins read would pick a citation silently."""
    text = _MAP.replace("- visual_id: v02", "- visual_id: v01")
    with pytest.raises(ReportError, match="declares 'v01' twice"):
        load_binding_map(_write(tmp_path, text))


def test_a_malformed_front_section_refuses(tmp_path: Path) -> None:
    text = _MAP.replace("visuals:", "visuals: [oops\n  broken:")
    with pytest.raises(ReportError, match="cannot read|not a mapping|front section"):
        load_binding_map(_write(tmp_path, text))


def test_the_expected_table_is_enforced(tmp_path: Path) -> None:
    """Rendering table A from table B's approved bindings is not a typo to absorb."""
    with pytest.raises(ReportError, match="not 'other_table'"):
        load_binding_map(_write(tmp_path, _MAP), expect_table="other_table")


def test_the_matching_table_is_accepted(tmp_path: Path) -> None:
    binding_map = load_binding_map(_write(tmp_path, _MAP), expect_table="demo_table")
    assert binding_map.table == "demo_table"


def test_the_path_is_the_committed_design_location() -> None:
    path = binding_map_path(_REPO, "retail_store_sales")
    assert path.is_file()
    assert path.name == "visual-contract-binding-map.md"


def test_the_real_committed_map_parses() -> None:
    """The shipped artifact, not a fixture resembling it."""
    binding_map = load_binding_map(
        binding_map_path(_REPO, "retail_store_sales"),
        expect_table="retail_store_sales",
    )
    assert binding_map.contract_for("v01") == "TotalSales"
    assert binding_map.contract_for("v04") == "DiscountedTransactionRate"
    assert len(binding_map.visual_ids) == 10
    # Every bound contract is one of the five approved contract files.
    approved = {
        path.stem
        for path in (_REPO / "mappings/retail_store_sales/metrics").glob("*.yaml")
    }
    assert {b.contract for b in binding_map.bindings} <= approved
