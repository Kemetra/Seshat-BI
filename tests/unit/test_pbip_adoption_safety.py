"""Failure-closed safety boundaries for PBIP adoption."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from seshat.pbip_adoption import (
    MANIFEST_PATH,
    PbipAdoptionError,
    assess_pbip,
    assessment_exit_code,
    render_assessment_text,
)
from seshat.pbip_adoption._safety import _safe_detail

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "pbip_adoption"


def _copy(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    shutil.copytree(FIXTURES / name, target)
    return target


def test_unsupported_pbip_schema_is_visible_without_traceback(tmp_path: Path) -> None:
    result = assess_pbip(_copy(tmp_path, "unsupported_schema"))
    assert result["coverage"]["unsupported"] >= 1
    assert any(
        fact["classification"] == "unavailable_with_reason" for fact in result["facts"]
    )


def test_assessment_never_discloses_absolute_root_or_fixture_literal(
    tmp_path: Path,
) -> None:
    project = _copy(tmp_path, "unsafe_literal")
    assessment = assess_pbip(project)
    json_output = json.dumps(assessment)
    text_output = render_assessment_text(assessment)
    for output in (json_output, text_output):
        assert str(project) not in output
        assert "do-not-disclose" not in output
        assert "Traceback" not in output
    assert assessment["disclosure"] == {"status": "pass", "findings": []}


def test_missing_path_is_a_concise_input_defect() -> None:
    with pytest.raises(PbipAdoptionError, match="does not exist"):
        assess_pbip(Path("does-not-exist"))


def test_safe_detail_redacts_the_credential_value_not_only_its_key() -> None:
    # Redaction must remove the assigned secret itself, not just the key and
    # delimiter (which would leave the value in the emitted prose).
    for secret in (
        "Password='super-secret-value'",
        'server="db.internal.example"',
        "token= bare-secret-token",
        "Data Source=host.internal;Password=hunter2",
    ):
        redacted = _safe_detail(secret, fallback="none")
        assert "secret" not in redacted or "<redacted" in redacted
        assert "super-secret-value" not in redacted
        assert "db.internal.example" not in redacted
        assert "bare-secret-token" not in redacted
        assert "hunter2" not in redacted


def _write_pbip_with_source(root: Path, m_source: str) -> None:
    root.mkdir()
    (root / "Model.pbip").write_text(
        '{"version": "1.0", "artifacts": []}\n', encoding="utf-8"
    )
    definition = root / "Model.SemanticModel" / "definition"
    definition.mkdir(parents=True)
    (definition / "model.tmdl").write_text(
        "table Sales\n"
        "\tpartition Sales = m\n"
        "\t\tsource =\n"
        "\t\t\tlet\n"
        f"\t\t\t\tSource = {m_source}\n"
        "\t\t\tin\n"
        "\t\t\t\tSource\n",
        encoding="utf-8",
    )


def test_literal_m_connection_source_is_flagged_pre_git(tmp_path: Path) -> None:
    project = tmp_path / "literal-m"
    _write_pbip_with_source(project, 'Sql.Database("prod.internal", "DW")')
    assessment = assess_pbip(project)
    assert any(
        fact["id"].startswith("blocked:C1:") and fact["classification"] == "blocked"
        for fact in assessment["facts"]
    ), "a literal M data-source host must be flagged even before Git"
    assert "prod.internal" not in json.dumps(assessment)


def test_parameterized_m_source_is_not_flagged_as_a_literal(tmp_path: Path) -> None:
    project = tmp_path / "param-m"
    _write_pbip_with_source(project, "PostgreSQL.Database(Server, Database)")
    assessment = assess_pbip(project)
    # The safe parameterized (identifier) form must not trip the literal scan.
    assert not any(fact["id"].startswith("blocked:C1:") for fact in assessment["facts"])
    # ...but the source reference itself is inventoried for the analyst.
    assert any(
        fact["id"].startswith("proposed:source-reference:")
        for fact in assessment["facts"]
    )


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )


def test_adopting_a_project_with_a_poisoned_git_config_does_not_execute_it(
    tmp_path: Path,
) -> None:
    """A downloaded/adopted PBIP project carries its own ``.git``. Git reads that
    tree's ``.git/config`` when we shell out inside it, so a malicious
    ``core.fsmonitor`` (a shell command git runs on ``status``/``rev-parse``) would
    execute in the analyst's shell -- arbitrary code execution from merely
    *assessing* an untrusted project. ``safe.directory`` does NOT save us: the
    victim owns the extracted files, so the dubious-ownership block never fires.

    The oracle sits on the risk itself: the payload, if run, creates a sentinel
    file. Assessing the project must leave that sentinel absent.
    """
    project = tmp_path / "downloaded-pbip"
    _write_pbip_with_source(project, "PostgreSQL.Database(Server, Database)")

    # The attacker ships a real git repo inside the project archive.
    _git("init", cwd=project)
    _git("config", "user.email", "a@b.c", cwd=project)
    _git("config", "user.name", "t", cwd=project)
    # Local-only: never sign/GPG (the host may enforce commit signing).
    _git("config", "commit.gpgsign", "false", cwd=project)
    _git("add", "-A", cwd=project)
    _git("commit", "--no-gpg-sign", "-m", "init", cwd=project)

    # Poisoned config: core.fsmonitor is a command git runs on `git status`
    # (git invokes it via the shell). The payload is a standalone Python script
    # so no nested-quote parsing can corrupt it. If it runs, it writes a sentinel.
    pwned = tmp_path / "PWNED"
    payload_script = project / "payload.py"
    payload_script.write_text(
        f"import pathlib\npathlib.Path(r'{pwned}').write_text('pwned')\n",
        encoding="utf-8",
    )
    # Bare interpreter + script path: robust across the sh/cmd git spawns.
    _git(
        "config",
        "core.fsmonitor",
        f'"{sys.executable}" "{payload_script}"',
        cwd=project,
    )

    assess_pbip(project)

    assert not pwned.exists(), (
        "assessing an adopted project executed its .git/config core.fsmonitor "
        "command -- git invocations against an untrusted tree must be hardened "
        "with -c core.fsmonitor=false"
    )


def test_malformed_adoption_manifest_fails_closed_with_a_blocker(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "Adoption.pbip").write_text(
        '{"version": "1.0", "artifacts": []}\n', encoding="utf-8"
    )
    manifest = project / Path(MANIFEST_PATH)
    manifest.parent.mkdir(parents=True)
    # Present but not a usable fingerprint baseline (no authoritative_inputs).
    manifest.write_text("this: is not a baseline\n", encoding="utf-8")

    assessment = assess_pbip(project)

    baseline_blockers = [
        fact
        for fact in assessment["facts"]
        if fact["id"] == "blocked:adoption-baseline-unusable"
    ]
    assert baseline_blockers, "an unusable manifest must be surfaced, not ignored"
    assert baseline_blockers[0]["classification"] == "blocked"
    # Fail closed: the run does not silently continue with empty changes.
    assert assessment["next_step"]["blocking_reasons"]
    assert assessment_exit_code(assessment) == 1
