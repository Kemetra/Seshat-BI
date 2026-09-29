import builtins
from argparse import Namespace
from pathlib import Path

import pytest

from seshat.governor.service import OPERATIONS, GovernorService

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


@pytest.mark.unit
def test_static_check_scrubs_secret_shaped_finding_text(
    tmp_path: Path, monkeypatch
) -> None:
    import seshat.runner as runner
    from seshat.core import Finding, Severity

    leaked = Finding(
        "X9",
        Severity.ERROR,
        "value postgresql://admin:S3cretPw@10.1.2.3:5432/prod leaked",
        "cfg.txt:1 password=hunter2",
    )
    monkeypatch.setattr(runner, "collect_findings", lambda *a, **k: [leaked])
    root = _workspace(tmp_path)
    result = GovernorService(root).call(
        "seshat_run_static_check", {"workspace": str(root)}
    )
    text = repr(result)
    assert "S3cretPw" not in text
    assert "hunter2" not in text
    assert result["outcome"] == "blocked"
