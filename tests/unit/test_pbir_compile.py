"""Unit tests for the PBIR compiler (spec 123, US7, T035/T037/T037a/T038).

Covers the ONE new primitive ADR 0017 authorizes -- ``create_page`` /
``create_visual_container`` -- orchestrated by ``compile_page_shell`` /
``compile_line_chart``. Every test sits on the real danger named in the ADR and
`research.md` D9/D10/D11/D13:

* deterministic ID minting (a pinned hash value, never random/time-based);
* byte-identical determinism across reruns;
* no partial write on a mid-batch failure (stage-validate-commit over a temp copy);
* creation gated on (a) a valid ``dashboard_blueprint_approval`` and (b) a verified
  Desktop-authored reference sample per element type (page shell / lineChart only --
  everything else stays BLOCKED, memory: CRITICAL rail on this task);
* binding only to a field on the approved binding-map (FR-027, no orphan visual);
* the FR-003 guarantee extended to "nothing pre-existing changed" for a page shell;
* the compiled lineChart carries the approved binding, not a copy of the
  ``visual_fmt.Report`` sample's OTD-specific content (proves the sample is used only
  as the wire-format proof, never as copied business content).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from seshat.pbir_compile import (
    CompileContext,
    LineChartRequest,
    PageShellRequest,
    PbirCompileError,
    compile_line_chart,
    compile_page_shell,
    mint_element_id,
)

pytestmark = pytest.mark.unit

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "pbir"
_PAGE_SHELL_SAMPLE = _FIXTURES / "page_shell.Report"
_LINECHART_SAMPLE = _FIXTURES / "visual_fmt.Report"

_REPORT_ID = "RetailStoreSales"

_VALID_APPROVAL = {
    "id": "dashboard_blueprint_approval.branch_perf",
    "decision_type": "dashboard_blueprint_approval",
    "status": "approved",
    "approval": {
        "approved_by": "R. Owner (report_owner)",
        "approved_at": "2026-07-12",
        "source": "review",
        "evidence": ["mappings/retail_store_sales/design/dashboard-layout.md"],
        "evidence_identity": {
            "mappings/retail_store_sales/design/dashboard-layout.md": "deadbeef"
        },
        "reviewed_scope": "{artifacts: [dashboard_blueprint.branch_perf]}",
    },
}

_AGENT_APPROVAL = {
    "id": "dashboard_blueprint_approval.branch_perf",
    "decision_type": "dashboard_blueprint_approval",
    "status": "approved",
    "approval": {
        "approved_by": "agent",
        "approved_at": "2026-07-12",
        "source": "review",
        "evidence": ["mappings/retail_store_sales/design/dashboard-layout.md"],
        "evidence_identity": {
            "mappings/retail_store_sales/design/dashboard-layout.md": "deadbeef"
        },
        "reviewed_scope": "{artifacts: [dashboard_blueprint.branch_perf]}",
    },
}

_AUTHORITY = {"dashboard_blueprint_approval": frozenset({"report_owner"})}

_BINDING_MAP = {
    "v05": {
        "bound_contract": "TotalSales",
        "measures": ["fct_sales_rss.total_sales"],
        "dimensions": ["dim_date_rss.full_date"],
    }
}

_POS = {"x": 10, "y": 20, "width": 400, "height": 200}

# The page-shell request never varies across these tests (same slug/display), so
# it is a shared constant; the compile context does vary (report dir, approval,
# repo_root) and is built per test via _ctx.
_PAGE_REQUEST = PageShellRequest(
    report_id=_REPORT_ID, page_slug="branch_perf", display_name="Branch Performance"
)

_UNSET = object()


def _report(tmp_path: Path, sample: Path, name: str) -> Path:
    dst = tmp_path / name
    shutil.copytree(sample, dst)
    return dst


def _ctx(report: Path, approval: object = _UNSET, *, repo_root: Path | None = None):
    """A CompileContext for ``report``; defaults to the valid approval + the shared
    authority map. Pass ``approval`` explicitly (incl. ``None``) to exercise the
    fail-closed gate; pass ``repo_root`` to enable the staleness leg."""
    resolved = _VALID_APPROVAL if approval is _UNSET else approval
    return CompileContext(
        report_dir=report,
        approval=resolved,
        authority=_AUTHORITY,
        repo_root=repo_root,
    )


def _line_request(
    *,
    visual_slug: str = "sales_trend",
    visual_type: str = "lineChart",
    binding_key: str = "v05",
    position: dict | None = None,
) -> LineChartRequest:
    return LineChartRequest(
        report_id=_REPORT_ID,
        page_name="pg",
        visual_slug=visual_slug,
        visual_type=visual_type,
        binding_map=_BINDING_MAP,
        binding_key=binding_key,
        position=position or _POS,
    )


def _pages_json(report: Path) -> dict:
    return json.loads(
        (report / "definition" / "pages" / "pages.json").read_text(encoding="utf-8-sig")
    )


def _tree_snapshot(report: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(report)): p.read_bytes()
        for p in sorted(report.rglob("*"))
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# Deterministic ID minting (FR-027 / US7#4) -- pinned, not just run1==run2
# ---------------------------------------------------------------------------


def test_mint_element_id_matches_the_spec_algorithm():
    # The algorithm IS the spec: truncated hashlib digest of report_id+slug,
    # never random/time-based. Pin the exact value for a known input so a
    # fast time-based implementation cannot slip through a run1==run2 check.
    expected = hashlib.sha256(f"{_REPORT_ID}branch_perf".encode()).hexdigest()[:20]
    assert mint_element_id(_REPORT_ID, "branch_perf") == expected
    assert len(expected) == 20  # matches the real samples' observed id width


def test_mint_element_id_is_deterministic_across_calls():
    a = mint_element_id(_REPORT_ID, "branch_perf")
    b = mint_element_id(_REPORT_ID, "branch_perf")
    assert a == b


def test_mint_element_id_differs_by_slug():
    a = mint_element_id(_REPORT_ID, "branch_perf")
    b = mint_element_id(_REPORT_ID, "exec_summary")
    assert a != b


# ---------------------------------------------------------------------------
# T037a -- preconditions gate (FR-025/FR-029, US7#2 + US7#5)
# ---------------------------------------------------------------------------


def test_compile_page_shell_blocked_without_valid_approval(tmp_path: Path):
    report = _report(tmp_path, _PAGE_SHELL_SAMPLE, "r.Report")
    before = _tree_snapshot(report)
    with pytest.raises(PbirCompileError, match="dashboard_blueprint_approval"):
        compile_page_shell(_ctx(report, _AGENT_APPROVAL), _PAGE_REQUEST)
    assert _tree_snapshot(report) == before  # writes nothing


def test_compile_page_shell_blocked_with_no_approval_at_all(tmp_path: Path):
    report = _report(tmp_path, _PAGE_SHELL_SAMPLE, "r.Report")
    before = _tree_snapshot(report)
    with pytest.raises(PbirCompileError, match="dashboard_blueprint_approval"):
        compile_page_shell(_ctx(report, None), _PAGE_REQUEST)
    assert _tree_snapshot(report) == before


@pytest.mark.parametrize("status", ["superseded", "rejected", "pending", "proposed"])
def test_compile_page_shell_blocked_when_status_is_not_approved(
    tmp_path: Path, status: str
):
    # H1 (spec 123 US7 AC#5 / FR-023): a blueprint approval carrying a residual
    # well-formed approval block but a status other than "approved" -- e.g. a DS4
    # `superseded` record after the blueprint changed -- must BLOCK compilation and
    # write nothing. approval_is_valid() validates the block but never reads status,
    # so this branch was previously untested and compiled.
    stale_approval = {**_VALID_APPROVAL, "status": status}
    report = _report(tmp_path, _PAGE_SHELL_SAMPLE, "r.Report")
    before = _tree_snapshot(report)
    with pytest.raises(PbirCompileError, match=f"status {status!r}, not 'approved'"):
        compile_page_shell(_ctx(report, stale_approval), _PAGE_REQUEST)
    assert _tree_snapshot(report) == before  # writes nothing


@pytest.mark.parametrize("status", ["superseded", "rejected", "pending", "proposed"])
def test_compile_line_chart_blocked_when_status_is_not_approved(
    tmp_path: Path, status: str
):
    stale_approval = {**_VALID_APPROVAL, "status": status}
    report = _report(tmp_path, _LINECHART_SAMPLE, "r.Report")
    before = _tree_snapshot(report)
    with pytest.raises(PbirCompileError, match=f"status {status!r}, not 'approved'"):
        compile_line_chart(_ctx(report, stale_approval), _line_request())
    assert _tree_snapshot(report) == before


def test_compile_page_shell_blocked_when_approved_evidence_is_stale(tmp_path: Path):
    # H1 staleness leg (research R-10): with a repo_root supplied, the compiler
    # reuses the decision gate's _evidence_stale oracle. _VALID_APPROVAL cites an
    # evidence file that does not exist under this repo_root, so its recorded
    # identity cannot be re-verified -> stale -> BLOCK, writing nothing.
    report = _report(tmp_path, _PAGE_SHELL_SAMPLE, "r.Report")
    before = _tree_snapshot(report)
    with pytest.raises(PbirCompileError, match="stale/missing evidence"):
        compile_page_shell(_ctx(report, repo_root=tmp_path), _PAGE_REQUEST)
    assert _tree_snapshot(report) == before


def test_compile_visual_blocked_for_a_shape_with_no_verified_sample(tmp_path: Path):
    # KPI cards have no verified Desktop sample (D10) -- must block naming it,
    # write nothing, never fall back to the geometry.Report placeholder.
    report = _report(tmp_path, _LINECHART_SAMPLE, "r.Report")
    before = _tree_snapshot(report)
    with pytest.raises(PbirCompileError, match="no verified reference sample"):
        compile_line_chart(
            _ctx(report),
            _line_request(
                visual_slug="exec_kpi_sales",
                visual_type="card",
                position={"x": 0, "y": 0, "width": 200, "height": 120},
            ),
        )
    assert _tree_snapshot(report) == before


def test_compile_visual_blocked_for_unmapped_binding_key(tmp_path: Path):
    report = _report(tmp_path, _LINECHART_SAMPLE, "r.Report")
    before = _tree_snapshot(report)
    with pytest.raises(PbirCompileError, match="not on the approved binding"):
        compile_line_chart(
            _ctx(report),
            _line_request(visual_slug="trend", binding_key="v_orphan"),  # not in map
        )
    assert _tree_snapshot(report) == before


# ---------------------------------------------------------------------------
# T037 -- Increment 1 page shells (UNBLOCKED)
# ---------------------------------------------------------------------------


def test_compile_page_shell_writes_page_and_registers_it(tmp_path: Path):
    report = _report(tmp_path, _PAGE_SHELL_SAMPLE, "r.Report")
    existing_page_dir = report / "definition" / "pages" / "a1b2c3d4e5f600112233"
    before_existing = _tree_snapshot(existing_page_dir)
    before_report_json = (report / "definition" / "report.json").read_bytes()

    written = compile_page_shell(_ctx(report), _PAGE_REQUEST)
    assert written  # non-empty write list

    expected_name = mint_element_id(_REPORT_ID, "branch_perf")
    new_page_json = report / "definition" / "pages" / expected_name / "page.json"
    assert new_page_json.is_file()
    doc = json.loads(new_page_json.read_text(encoding="utf-8-sig"))
    assert doc["name"] == expected_name
    assert doc["displayName"] == "Branch Performance"
    # grounded in the verified sample's real shape -- same schema + canvas fields
    assert doc["$schema"].endswith("page/2.1.0/schema.json")
    assert {"width", "height"} <= doc.keys()

    pages = _pages_json(report)
    assert expected_name in pages["pageOrder"]
    assert "a1b2c3d4e5f600112233" in pages["pageOrder"]  # original page kept

    # FR-003 extended: nothing PRE-EXISTING changed.
    assert _tree_snapshot(existing_page_dir) == before_existing
    assert (report / "definition" / "report.json").read_bytes() == before_report_json


def test_compile_page_shell_is_byte_deterministic_on_rerun(tmp_path: Path):
    report_a = _report(tmp_path, _PAGE_SHELL_SAMPLE, "a.Report")
    report_b = _report(tmp_path, _PAGE_SHELL_SAMPLE, "b.Report")

    compile_page_shell(_ctx(report_a), _PAGE_REQUEST)
    compile_page_shell(_ctx(report_b), _PAGE_REQUEST)

    name = mint_element_id(_REPORT_ID, "branch_perf")
    page_a = report_a / "definition" / "pages" / name / "page.json"
    page_b = report_b / "definition" / "pages" / name / "page.json"
    assert page_a.read_bytes() == page_b.read_bytes()

    pages_a = (report_a / "definition" / "pages" / "pages.json").read_bytes()
    pages_b = (report_b / "definition" / "pages" / "pages.json").read_bytes()
    assert pages_a == pages_b


def test_compile_page_shell_rerun_on_same_report_is_idempotent(tmp_path: Path):
    report = _report(tmp_path, _PAGE_SHELL_SAMPLE, "r.Report")
    compile_page_shell(_ctx(report), _PAGE_REQUEST)
    name = mint_element_id(_REPORT_ID, "branch_perf")
    page_json = report / "definition" / "pages" / name / "page.json"
    first = page_json.read_bytes()

    compile_page_shell(_ctx(report), _PAGE_REQUEST)
    assert page_json.read_bytes() == first
    pages = _pages_json(report)
    assert pages["pageOrder"].count(name) == 1  # no duplicate entry


def test_compile_page_shell_no_partial_write_on_injected_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Inject a failure INSIDE the validate phase of the staged batch (not an OS
    # write error) and assert the real report dir is untouched -- proves the
    # temp-dir stage->validate->commit discipline, not accidental atomicity.
    report = _report(tmp_path, _PAGE_SHELL_SAMPLE, "r.Report")
    before = _tree_snapshot(report)

    import seshat.pbir_compile as compile_mod

    def _boom(*_args, **_kwargs):
        raise PbirCompileError("injected validation failure")

    monkeypatch.setattr(compile_mod, "_validate_staged_batch", _boom)

    with pytest.raises(PbirCompileError, match="injected validation failure"):
        compile_page_shell(_ctx(report), _PAGE_REQUEST)
    assert _tree_snapshot(report) == before  # nothing written


# ---------------------------------------------------------------------------
# T038 -- Increment 3 lineChart (UNBLOCKED, data-goblin visual_fmt.Report sample)
# ---------------------------------------------------------------------------


def test_compile_line_chart_binds_only_to_approved_map_field(tmp_path: Path):
    report = _report(tmp_path, _LINECHART_SAMPLE, "r.Report")

    written = compile_line_chart(_ctx(report), _line_request())
    assert written

    name = mint_element_id(_REPORT_ID, "sales_trend")
    visual_json = (
        report / "definition" / "pages" / "pg" / "visuals" / name / "visual.json"
    )
    assert visual_json.is_file()
    doc = json.loads(visual_json.read_text(encoding="utf-8-sig"))
    assert doc["visual"]["visualType"] == "lineChart"
    raw = visual_json.read_text(encoding="utf-8-sig")

    # Proves the compiler used the sample only as a WIRE-FORMAT proof: the
    # approved contract's fields are present...
    assert "fct_sales_rss" in raw or "total_sales" in raw
    assert "full_date" in raw
    # ...and the sample's OTD-specific business content was NOT dragged along
    # (that would be an orphan bind + FR-027 violation).
    assert "On-Time Delivery" not in raw
    assert "OTD" not in raw


def test_compile_line_chart_is_byte_deterministic_on_rerun(tmp_path: Path):
    report_a = _report(tmp_path, _LINECHART_SAMPLE, "a.Report")
    report_b = _report(tmp_path, _LINECHART_SAMPLE, "b.Report")
    request = _line_request()
    compile_line_chart(_ctx(report_a), request)
    compile_line_chart(_ctx(report_b), request)
    name = mint_element_id(_REPORT_ID, "sales_trend")
    a = (
        report_a / "definition" / "pages" / "pg" / "visuals" / name / "visual.json"
    ).read_bytes()
    b = (
        report_b / "definition" / "pages" / "pg" / "visuals" / name / "visual.json"
    ).read_bytes()
    assert a == b


def test_compile_line_chart_no_partial_write_on_injected_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    report = _report(tmp_path, _LINECHART_SAMPLE, "r.Report")
    before = _tree_snapshot(report)

    import seshat.pbir_compile as compile_mod

    def _boom(*_args, **_kwargs):
        raise PbirCompileError("injected validation failure")

    monkeypatch.setattr(compile_mod, "_validate_staged_batch", _boom)

    with pytest.raises(PbirCompileError, match="injected validation failure"):
        compile_line_chart(_ctx(report), _line_request())
    assert _tree_snapshot(report) == before
