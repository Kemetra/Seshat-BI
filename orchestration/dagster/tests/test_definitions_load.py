"""SC-001 / US6: the Definitions object loads with the full graph, both jobs,
and BOTH automations shipped STOPPED -- and the pinned pair is consistent."""

from __future__ import annotations

from dagster import DefaultScheduleStatus, DefaultSensorStatus

from tower_bi_orchestration.definitions import build_definitions

from conftest import make_fixture_repo


def test_definitions_load_with_full_graph(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path)
    monkeypatch.setenv("SESHAT_REPO_ROOT", str(root))
    defs = build_definitions(root)
    asset_names = {
        key.path[-1] for asset in defs.assets for key in asset.keys  # type: ignore[union-attr]
    }
    assert asset_names == {
        "raw_source_file",
        "bronze_table",
        "source_profile",
        "source_map",
        "silver_tables",
        "gold_tables",
        "live_validate",
        "metric_contracts",
        "semantic_model",
        "dashboard_blueprint",
        "handoff_pack",
        "publish_execution_evidence",
    }
    job_names = {job.name for job in defs.jobs}
    assert {"full_sequence_job", "through_gold_job"} <= job_names


def test_exactly_one_schedule_and_one_sensor_both_stopped(tmp_path, monkeypatch) -> None:
    root = make_fixture_repo(tmp_path)
    monkeypatch.setenv("SESHAT_REPO_ROOT", str(root))
    defs = build_definitions(root)
    schedules = list(defs.schedules)
    sensors = list(defs.sensors)
    assert len(schedules) == 1
    assert len(sensors) == 1
    assert schedules[0].default_status is DefaultScheduleStatus.STOPPED
    assert sensors[0].default_status is DefaultSensorStatus.STOPPED


def test_pinned_pair_is_consistent_with_the_control_layer_constants() -> None:
    import dagster
    import dagster_dbt

    from seshat.dagster_adapter import PINNED_DAGSTER, PINNED_DAGSTER_DBT

    assert dagster.__version__ == PINNED_DAGSTER
    assert dagster_dbt.__version__ == PINNED_DAGSTER_DBT
