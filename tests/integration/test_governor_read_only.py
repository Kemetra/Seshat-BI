from pathlib import Path

from seshat.governor.service import OPERATIONS, GovernorService

FIXTURE = Path(__file__).parents[1] / "fixtures/readiness/run_next/us1_blocked.yaml"


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_every_governor_probe_preserves_workspace_bytes(tmp_path: Path) -> None:
    table = tmp_path / "mappings/example_table"
    table.mkdir(parents=True)
    (table / "readiness-status.yaml").write_bytes(FIXTURE.read_bytes())
    powerbi = tmp_path / "powerbi/model"
    powerbi.mkdir(parents=True)
    (powerbi / "model.tmdl").write_text("model Model\n", encoding="utf-8")
    before = _snapshot(tmp_path)
    service = GovernorService(tmp_path)
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
        service.call(operation, {"workspace": str(tmp_path), **requests[operation]})
        assert _snapshot(tmp_path) == before
        assert not (tmp_path / ".seshat-output").exists()
