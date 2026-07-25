"""Spec A end-to-end: the CLI check seam honors the drop-in rule tier.

These drive the REAL ``main(["check", ...])`` -> ``is_bootstrapped`` ->
``run(bootstrapped=)`` path (the unit tests in test_rule_tier.py call ``run``
directly and never exercise the CLI wiring). This locks the one line that makes
Spec A real: a repo the kit was downloaded into skips KIT_SELF rules; the kit's
own bootstrapped repo runs them.
"""

from pathlib import Path

import pytest

from seshat.cli import main as main_under_test
from tests.unit._gitfix import make_git_repo, make_kit_self_repo

# A rule that reads a kit-internal manifest, so it errors in a foreign repo unless
# the tier gate skips it. SC1 is tagged KIT_SELF (reconciles status-claims.yaml).
_KIT_SELF_ID = "SC1"


def _bootstrap(repo: Path) -> None:
    """Write the ``.seshat/`` substrate -- what ``seshat init`` leaves behind.

    Note this is NOT kit identity: the same two files land in any consumer repo
    that ran ``seshat init`` (issue #486).
    """
    seshat = repo / ".seshat"
    seshat.mkdir(parents=True, exist_ok=True)
    (seshat / "kit-source.yaml").write_text("name: t\n", encoding="utf-8")
    (seshat / "compass.yaml").write_text("name: t\n", encoding="utf-8")


@pytest.mark.unit
def test_check_skips_kit_self_rule_in_foreign_repo(tmp_path, capsys):
    # A bare git repo with NO .seshat kit substrate == a repo the kit was merely
    # downloaded into. The KIT_SELF rule must SKIP (INFO), not ERROR.
    repo = make_git_repo(tmp_path)
    rc = main_under_test(["check", "--repo", str(repo)])
    out = capsys.readouterr().out
    assert f"[info] {_KIT_SELF_ID} skipped (kit-self rule" in out
    assert f"[error] {_KIT_SELF_ID}" not in out
    # rc may be 0 or 1 depending on other portable rules; the tier behavior is the
    # assertion here, not the aggregate exit. But the kit-self rule must not error.
    assert isinstance(rc, int)


@pytest.mark.unit
def test_check_runs_kit_self_rule_in_the_kits_own_repo(tmp_path, capsys):
    # Shaped as the KIT ITSELF -> the KIT_SELF rule RUNS (its skip line is absent).
    # Its manifest is missing, so it fires as an ERROR -> no skip line.
    #
    # This replaces test_check_runs_kit_self_rule_in_bootstrapped_repo, whose
    # premise (substrate == kit) WAS the defect in issue #486: `seshat init` writes
    # that substrate into consumer repos, so it unblocked the tier on the golden
    # path. The intent -- "the tier runs where the manifests genuinely belong" --
    # is unchanged; only the activation signal is.
    repo = make_git_repo(tmp_path)
    _bootstrap(repo)
    make_kit_self_repo(repo)
    main_under_test(["check", "--repo", str(repo)])
    out = capsys.readouterr().out
    assert f"[info] {_KIT_SELF_ID} skipped (kit-self rule" not in out


@pytest.mark.unit
def test_check_skips_kit_self_rule_after_init_in_a_consumer_repo(tmp_path, capsys):
    # The regression itself: substrate present (init ran) but NOT the kit -> skip.
    repo = make_git_repo(tmp_path)
    _bootstrap(repo)
    main_under_test(["check", "--repo", str(repo)])
    out = capsys.readouterr().out
    assert f"[info] {_KIT_SELF_ID} skipped (kit-self rule" in out
    assert f"[error] {_KIT_SELF_ID}" not in out


@pytest.mark.unit
def test_check_json_seam_skips_kit_self_in_foreign_repo(tmp_path, capsys):
    import json

    repo = make_git_repo(tmp_path)
    main_under_test(["check", "--repo", str(repo), "--format", "json"])
    doc = json.loads(capsys.readouterr().out)
    sc1 = [f for f in doc["findings"] if f["rule_id"] == _KIT_SELF_ID]
    assert sc1 and all(f["severity"] == "info" for f in sc1)
