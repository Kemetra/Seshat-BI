from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# tests/unit/test_cseam.py -> parents[2] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"


@pytest.mark.unit
def test_ci_workflow_parses_and_references_retail_check() -> None:
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)  # raises if the YAML is invalid
    assert parsed is not None
    assert "retail check" in text


@pytest.mark.unit
def test_pre_commit_config_parses_and_references_retail_check() -> None:
    text = PRE_COMMIT.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text)  # raises if the YAML is invalid
    assert parsed is not None
    assert "retail check" in text
