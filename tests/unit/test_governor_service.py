import builtins
from argparse import Namespace
from pathlib import Path

import pytest

from seshat.governor.service import OPERATIONS, GovernorService

pytestmark = pytest.mark.unit

FIXTURE = Path(__file__).parents[1] / "fixtures/readiness/run_next/us1_blocked.yaml"


def _workspace(tmp_path: Path) -> Path:
    table = tmp_path / "mappings/example_table"
    table.mkdir(parents=True)
    (table / "readiness-status.yaml").write_bytes(FIXTURE.read_bytes())
    return tmp_path


def test_all_six_operations_return_stable_read_only_envelope(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    service = GovernorService(root)
    requests = {
        "seshat_get_status": {},
        "seshat_get_next_action": {"table": "example_table"},
        "seshat_explain_blockers": {"table": "silver.example_table"},
        "seshat_prepare_approval_request": {
            "table": "silver.example_table",
            "decision_id": "grain-confirmation",
        },
        "seshat_run_static_check": {},
        "seshat_export_evidence_pack": {"table": "example_table"},
    }
    for operation in OPERATIONS:
        result = service.call(
            operation, {"workspace": str(root), **requests[operation]}
        )
        assert result["schema_version"] == "1.0"
        assert result["operation"] == operation
        assert result["read_only_proof"] is True
        assert result["outcome"] in {"ok", "blocked", "input_defect", "unavailable"}


def test_requested_premature_silver_scope_is_refused(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = GovernorService(root).call(
        "seshat_get_next_action",
        {
            "workspace": str(root),
            "table": "example_table",
            "requested_scope": "author silver SQL",
        },
    )
    assert result["outcome"] == "blocked"
    assert result["blockers"] == ["grain not confirmed unique on data"]
    assert any("silver" in item.lower() for item in result["forbidden_scope"])


def test_approval_request_never_becomes_receipt(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = GovernorService(root).call(
        "seshat_prepare_approval_request",
        {
            "workspace": str(root),
            "table": "silver.example_table",
            "decision_id": "grain-confirmation",
        },
    )
    assert result["outcome"] == "blocked"
    assert result["content"]["status"] == "prepared_not_approved"
    assert "grants no readiness" in result["content"]["authority_disclaimer"]


def test_workspace_escape_and_malformed_request_fail_closed(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    service = GovernorService(root)
    escaped = service.call("seshat_get_status", {"workspace": str(root.parent)})
    malformed = service.call("seshat_get_status", [])  # type: ignore[arg-type]
    assert escaped["outcome"] == "input_defect"
    assert str(root) not in escaped["error"]
    assert malformed["error"] == "request must be an object"


def test_table_path_escape_is_rejected(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    result = GovernorService(root).call(
        "seshat_export_evidence_pack",
        {"workspace": str(root), "table": "../secrets"},
    )
    assert result["outcome"] == "input_defect"
    assert result["error"] == "table must be a local table identifier"


def _call(root: Path, operation: str, **request: object) -> dict:
    return GovernorService(root).call(operation, {"workspace": str(root), **request})


def test_directory_name_equals_qualified_table_for_blockers(tmp_path: Path) -> None:
    """Audit F017: the directory name and the recorded table are one table."""
    root = _workspace(tmp_path)
    by_dir = _call(root, "seshat_explain_blockers", table="example_table")
    by_table = _call(root, "seshat_explain_blockers", table="silver.example_table")
    assert by_dir["outcome"] == by_table["outcome"] == "blocked"
    assert by_dir["blockers"] == by_table["blockers"]


def test_unknown_table_is_an_input_defect_not_ok(tmp_path: Path) -> None:
    root = _workspace(tmp_path)
    for operation, extra in (
        ("seshat_explain_blockers", {}),
        ("seshat_prepare_approval_request", {"decision_id": "d"}),
    ):
        result = _call(root, operation, table="no_such_table", **extra)
        assert result["outcome"] == "input_defect", operation


def test_invalid_yaml_is_an_input_defect(tmp_path: Path) -> None:
    """Audit F074: a corrupt record is not a table with nothing blocking."""
    root = _workspace(tmp_path)
    (root / "mappings/example_table/readiness-status.yaml").write_text(
        "stages: [oops\n", encoding="utf-8"
    )
    result = _call(root, "seshat_explain_blockers", table="example_table")
    assert result["outcome"] == "input_defect"
    request = _call(
        root, "seshat_prepare_approval_request", table="example_table", decision_id="d"
    )
    assert request["outcome"] == "input_defect"


def test_short_domain_tokens_hit_the_forbidden_vocabulary(tmp_path: Path) -> None:
    """Audit F078: 'add DAX measures' is semantic-model work before Gold Ready."""
    root = _workspace(tmp_path)
    for scope in ("add DAX measures", "build the PBIP report page"):
        result = _call(
            root, "seshat_get_next_action", table="example_table", requested_scope=scope
        )
        assert result["outcome"] == "blocked", scope


def test_a_committed_keyword_dsn_never_leaves_the_governor(tmp_path: Path) -> None:
    """Audit F079/F137: success payloads are scrubbed, not just error text."""
    root = _workspace(tmp_path)
    status = root / "mappings/example_table/readiness-status.yaml"
    secret = (
        "connect failed: host=db.prod user=svc password=hunter2 "
        "via postgresql://svc:hunter2@db.prod.internal:5432/salesdb"
    )
    guid = "12345678-1234-1234-1234-1234567890ab"
    status.write_text(
        status.read_text(encoding="utf-8").replace(
            "grain not confirmed unique on data", f"{secret} tenant {guid}"
        ),
        encoding="utf-8",
    )
    requests = {
        "seshat_get_status": {},
        "seshat_get_next_action": {"table": "example_table"},
        "seshat_explain_blockers": {"table": "example_table"},
        "seshat_prepare_approval_request": {
            "table": "example_table",
            "decision_id": "d",
        },
        "seshat_run_static_check": {},
        "seshat_export_evidence_pack": {"table": "example_table"},
    }
    for operation in OPERATIONS:
        text = repr(_call(root, operation, **requests[operation]))
        for leaked in ("hunter2", "db.prod", "svc", "5432", "salesdb", guid):
            assert leaked not in text, (operation, leaked)


def test_error_path_scrubs_a_uri_dsn(tmp_path: Path, monkeypatch) -> None:
    root = _workspace(tmp_path)
    service = GovernorService(root)

    def explode(_request: dict) -> dict:
        raise RuntimeError("boom postgresql://svc:pw1@db.prod.internal:5432/salesdb")

    monkeypatch.setitem(service._operations, "seshat_get_status", explode)
    result = service.call("seshat_get_status", {"workspace": str(root)})
    assert result["outcome"] == "input_defect"
    for leaked in ("pw1", "db.prod", "5432", "salesdb"):
        assert leaked not in result["error"]


def test_mcp_parser_binds_repo_without_starting_sdk() -> None:
    from seshat.cli.parser import _build_parser

    args = _build_parser().parse_args(["mcp", "--repo", "workspace"])
    assert args.command == "mcp"
    assert args.repo == "workspace"


def test_missing_mcp_extra_has_actionable_guidance(monkeypatch, capsys) -> None:
    from seshat import cli

    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name.endswith("governor.mcp_server"):
            raise ImportError("missing optional SDK")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    assert cli._run_mcp(Namespace(repo=".")) == 2
    assert "seshat-bi[mcp]" in capsys.readouterr().err
