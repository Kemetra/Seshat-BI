"""TDD tests for the compass projection generator + drift checks (feature 070).

Covers:
* compass.yaml is projected from kit-source.yaml with NO current_stage (FR-005, SC-004);
* verbs include the profiling front door retail-onboard-table (MAJOR-2, SC-007);
* drift check (a): compass.yaml == project_yaml(source) byte-exact (P1);
* drift check (b): fenced_body == render_prose(source) render-compare (FC1, MINOR-6);
* manifests are written; agent can enumerate verbs + hard-stops from compass.yaml alone.

tmp_path repos only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from retail.compass_project import (
    check_prose_drift,
    check_yaml_drift,
    load_source,
    project_all,
    render_compass_yaml,
    render_prose,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REL = ".seshat/kit-source.yaml"


@pytest.fixture
def repo(tmp_path) -> Path:
    """A tmp repo holding a copy of the real canonical source."""
    src = REPO_ROOT / SOURCE_REL
    dst = tmp_path / SOURCE_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return tmp_path


def test_source_loads_and_has_no_current_stage(repo) -> None:
    source = load_source(repo)
    assert source["kit"] == "seshat-bi"
    assert "current_stage" not in source
    assert "current_stage" not in source.get("orient", {})


def test_compass_yaml_has_no_current_stage(repo) -> None:
    compass_text = render_compass_yaml(load_source(repo))
    parsed = yaml.safe_load(compass_text)
    assert "current_stage" not in parsed
    assert "current_stage" not in parsed.get("orient", {})
    # verbatim carry of the source's declarative blocks
    assert parsed["verbs"] == load_source(repo)["verbs"]
    assert parsed["hard_stops"] == load_source(repo)["hard_stops"]


def test_verbs_include_profiling_front_door(repo) -> None:
    parsed = yaml.safe_load(render_compass_yaml(load_source(repo)))
    ids = {v["id"] for v in parsed["verbs"]}
    assert "retail-onboard-table" in ids  # MAJOR-2: profiling front door discoverable
    assert "first-hour-compass" in ids


def test_agent_can_enumerate_verbs_and_hardstops_from_compass_alone(repo) -> None:
    # SC-007: reading ONLY compass.yaml yields the verbs + hard-stops.
    parsed = yaml.safe_load(render_compass_yaml(load_source(repo)))
    assert len(parsed["verbs"]) >= 5
    assert "never_self_grant_approval" in parsed["hard_stops"]
    assert "never_fabricate_a_confidence_score" in parsed["hard_stops"]


def test_project_all_writes_substrate(repo) -> None:
    written = project_all(repo)
    assert (repo / ".seshat/compass.yaml").exists()
    assert (repo / ".seshat/manifest.yaml").exists()
    assert (repo / ".seshat/integrations/claude.json").exists()
    assert (repo / ".seshat/integrations/codex.json").exists()
    assert any("compass.yaml" in w for w in written)


def test_yaml_drift_check_passes_on_fresh_projection(repo) -> None:
    project_all(repo)
    # (a) byte-exact: freshly written compass.yaml matches project_yaml(source)
    assert check_yaml_drift(repo) is True


def test_yaml_drift_check_fails_when_compass_edited(repo) -> None:
    project_all(repo)
    compass = repo / ".seshat/compass.yaml"
    compass.write_text(
        compass.read_text(encoding="utf-8") + "\n# tamper\n", encoding="utf-8"
    )
    assert check_yaml_drift(repo) is False


def test_prose_drift_is_render_and_compare_not_byte_vs_yaml(repo) -> None:
    # (b) FC1/MINOR-6: prose render compared to a fenced body, distinct from YAML.
    source = load_source(repo)
    prose = render_prose(source)
    # a faithful fenced body (== the render) passes
    assert check_prose_drift(source, fenced_body=prose) is True
    # a drifted body fails
    assert check_prose_drift(source, fenced_body=prose + "\nextra line") is False
    # the prose is NOT valid-yaml-equal to compass (different shape) -- sanity:
    assert prose != render_compass_yaml(source)


def test_prose_mentions_verbs_and_hardstops(repo) -> None:
    prose = render_prose(load_source(repo))
    assert "retail-onboard-table" in prose
    assert "never_self_grant_approval" in prose


def test_written_files_are_utf8_no_bom_lf(repo) -> None:
    project_all(repo)
    raw = (repo / ".seshat/compass.yaml").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in raw
