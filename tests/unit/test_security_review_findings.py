"""Regression tests for the multi-lens security review findings.

Each test pins ONE reviewed defect so the fix cannot silently regress:

* ``F0`` -- ``semantic-check`` must NOT report "no drift" when it discovered
  ZERO inputs (a fail-open that is live in CI).
* ``F1`` -- the ``dbt doctor`` git leg must carry the FULL untrusted-tree
  hardening set, not just ``core.fsmonitor``.
* ``F2`` -- every git call site must source the hardening from the single
  ``gitutil._GIT_HARDENING`` tuple rather than re-listing flags locally.
* ``F4`` -- blueprint validation must REPORT an unparseable ``visual.json``
  instead of silently dropping the visual.
* ``DSN`` -- the config-resolution error types must never carry a credential
  value in their message (today true by discipline, untested).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True
    )
    return repo


# --------------------------------------------------------------------------
# F0: semantic-check fail-open on zero discovered inputs
# --------------------------------------------------------------------------


def test_semantic_check_does_not_claim_no_drift_with_zero_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An empty repo has nothing to check, so "no drift" is a FALSE claim.

    Reproduces the reviewed fail-open: with zero contracts and zero TMDL the
    command printed ``no drift (0 findings).`` and exited 0 -- identical to a
    genuinely clean repo. A discovery regression (a renamed path making the
    glob miss every real file) would therefore read as success in CI.
    """
    repo = _git_repo(tmp_path)

    exit_code = main(["semantic-check", "--repo", str(repo)])
    err = capsys.readouterr().err

    assert "no drift" not in err, (
        f"zero discovered inputs must not be reported as 'no drift' -- got: {err!r}"
    )
    assert exit_code != 0 or "no input" in err.lower(), (
        "zero-input must be surfaced as a distinct state (not silent success)"
    )


def test_semantic_check_zero_inputs_is_a_failure_under_require_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--require-inputs` makes zero-discovery BLOCK, which is what CI needs.

    Reporting `[not_started]` on stderr while still exiting 0 leaves CI green: a
    discovery regression would print a line nobody reads on a passing job. On a
    repo that is KNOWN to carry contracts/TMDL (this one), zero discovery is
    always a defect, so CI opts in and gets a real gate.
    """
    repo = _git_repo(tmp_path)

    exit_code = main(["semantic-check", "--repo", str(repo), "--require-inputs"])
    err = capsys.readouterr().err

    assert exit_code == 1, "--require-inputs must FAIL on zero discovered inputs"
    assert "no drift" not in err


def test_semantic_check_require_inputs_passes_when_inputs_exist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--require-inputs` must not fail a repo that does have discoverable inputs."""
    repo = _git_repo(tmp_path)
    tmdl = repo / "powerbi" / "Model.SemanticModel" / "definition" / "model.tmdl"
    tmdl.parent.mkdir(parents=True, exist_ok=True)
    tmdl.write_text("table 'gold fct_x'\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)

    exit_code = main(["semantic-check", "--repo", str(repo), "--require-inputs"])
    err = capsys.readouterr().err

    assert exit_code == 0, f"inputs exist, so --require-inputs must pass: {err!r}"


def test_semantic_check_still_reports_no_drift_on_a_clean_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The zero-input guard must not break the genuine clean-repo path.

    Guards against "fix" by simply deleting the success message: a repo that
    DOES carry a discoverable input and has no drift must still pass.
    """
    repo = _git_repo(tmp_path)
    # Discovery requires the governed layout: a *.SemanticModel/definition/*.tmdl
    # that is TRACKED (the default path uses `git ls-files`).
    tmdl = repo / "powerbi" / "Model.SemanticModel" / "definition" / "model.tmdl"
    tmdl.parent.mkdir(parents=True, exist_ok=True)
    tmdl.write_text("table 'gold fct_x'\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)

    exit_code = main(["semantic-check", "--repo", str(repo)])
    err = capsys.readouterr().err

    assert exit_code == 0, f"a clean repo with a real input must pass: {err!r}"
    assert "no drift" in err


# --------------------------------------------------------------------------
# F1 / F2: git untrusted-tree hardening completeness + single source
# --------------------------------------------------------------------------

_REQUIRED_HARDENING = ("core.fsmonitor", "core.hooksPath", "protocol.ext.allow")


def test_dbt_profile_git_leg_carries_full_hardening_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`dbt doctor`'s git leg runs against a user-supplied --repo tree.

    ``check-ignore`` / ``ls-files`` make git read THAT tree's ``.git/config``,
    so ``core.hooksPath`` and ``protocol.ext`` are live exec vectors. The
    reviewed code carried only ``core.fsmonitor``.

    Asserts on the ARGV actually handed to git -- not on the source text -- so
    the test stays honest whether the flags are inlined or imported.
    """
    from seshat.cli.commands import dbt as dbt_cmd

    seen: dict[str, list[str]] = {}

    def _capture(cmd, **kwargs):
        seen["cmd"] = list(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(dbt_cmd.subprocess, "run", _capture)
    dbt_cmd._profile_git_result(tmp_path, "check-ignore", "--quiet")

    argv = seen["cmd"]
    for flag in _REQUIRED_HARDENING:
        assert any(flag in part for part in argv), (
            f"git argv is missing {flag!r} -- a user-supplied --repo tree can "
            f"drive git's config-driven execution. argv={argv}"
        )


def test_git_hardening_has_a_single_definition() -> None:
    """The hardening tuple must be defined ONCE and imported.

    Ten call sites each re-listing the flags is what let F1 drift: a manual
    "keep in sync" contract with no enforcement. Any module that runs a
    hardened git call must reference the shared constant.
    """
    from seshat import gitutil

    assert hasattr(gitutil, "GIT_HARDENING"), (
        "gitutil must export a public GIT_HARDENING for other modules to import"
    )
    for flag in _REQUIRED_HARDENING:
        assert any(flag in part for part in gitutil.GIT_HARDENING), (
            f"the shared tuple is missing {flag!r}"
        )

    # Trigger on ANY of the three flags, not just `core.hooksPath`: the defect
    # actually found (F1) was a PARTIAL re-listing -- `core.fsmonitor=false` alone,
    # with hooksPath/protocol.ext missing. A hooksPath-only trigger would let that
    # exact regression back in silently, since the offending module never mentions
    # hooksPath. Catch partial and full duplication alike.
    src_root = Path(gitutil.__file__).parent
    offenders: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        if path.name in ("gitutil.py", "severity_posture.py"):
            continue  # the definition itself; and the documented throwaway-repo case
        text = path.read_text(encoding="utf-8")
        names_a_flag = any(flag in text for flag in _REQUIRED_HARDENING)
        if names_a_flag and "GIT_HARDENING" not in text:
            offenders.append(path.name)

    assert not offenders, (
        "these modules name a git hardening flag without importing the shared "
        f"`gitutil.GIT_HARDENING` tuple (partial re-listing is how F1 drifted): "
        f"{offenders}"
    )


# --------------------------------------------------------------------------
# F4: blueprint validation must not silently drop a corrupt visual
# --------------------------------------------------------------------------


def test_blueprint_reports_unparseable_visual_instead_of_dropping_it(
    tmp_path: Path,
) -> None:
    """A corrupt ``visual.json`` must produce a finding, not vanish.

    Dropping it from the discovery map means validation cannot see the visual
    at all: it is neither checked nor reported. Per the repo's own standard,
    gate on the FAILED PARSE rather than degrading to absent.
    """
    from seshat.pbir_validate_blueprint import _iter_committed_visuals

    report_dir = tmp_path / "Report"
    visual_dir = report_dir / "definition" / "pages" / "page1" / "visuals" / "v1"
    visual_dir.mkdir(parents=True)
    (visual_dir / "visual.json").write_text("{ not valid json", encoding="utf-8")

    visuals, unreadable = _iter_committed_visuals(report_dir)

    assert visuals == {}, "a corrupt visual must not enter the validated map"
    assert len(unreadable) == 1, (
        "the corrupt visual must be REPORTED as a blocking deviation, not dropped"
    )
    assert unreadable[0].dimension == "unreadable_source"
    assert "v1" in unreadable[0].message


def test_blueprint_discovers_a_valid_visual(tmp_path: Path) -> None:
    """The unreadable channel must not disturb the normal discovery path."""
    from seshat.pbir_validate_blueprint import _iter_committed_visuals

    report_dir = tmp_path / "Report"
    visual_dir = report_dir / "definition" / "pages" / "page1" / "visuals" / "ok1"
    visual_dir.mkdir(parents=True)
    (visual_dir / "visual.json").write_text(
        json.dumps({"visual": {"visualType": "barChart"}}), encoding="utf-8"
    )

    visuals, unreadable = _iter_committed_visuals(report_dir)

    assert list(visuals) == ["ok1"]
    assert unreadable == []


# --------------------------------------------------------------------------
# DSN: the config-resolution error types must never carry a credential
# --------------------------------------------------------------------------


def test_connection_config_error_never_carries_the_dsn() -> None:
    """`drift`/`profile`/`validate` print this exception's text BARE (no redact).

    That is safe only while the message names variables, never values. Nothing
    enforced it, so a future ``raise ConnectionConfigError(f"...{dsn}...")``
    would leak silently. This pins the invariant.
    """
    from seshat.connection_env import ConnectionConfigError, as_connection_config

    secret = "postgresql://alice:s3cr3t@db.example.com:5432/analytics"

    def _resolve_raising_with_the_dsn():
        raise ValueError(f"could not connect using {secret}")

    with pytest.raises(ConnectionConfigError) as caught:
        as_connection_config(_resolve_raising_with_the_dsn)

    message = str(caught.value)
    for fragment in ("s3cr3t", "alice", "db.example.com"):
        assert fragment not in message, (
            f"ConnectionConfigError leaked {fragment!r} into a message that "
            f"drift/profile/validate print unredacted: {message!r}"
        )


@pytest.mark.parametrize(
    ("label", "message"),
    [
        (
            "labeled",
            "bad config: dsn=postgresql://alice:s3cr3t@db.example.com:5432/analytics",
        ),
        (
            "spaced-conninfo",
            "could not connect: host = db.example.com user = alice password = s3cr3t",
        ),
        (
            "semicolon-separated",
            "bad: host=db.example.com;user=alice;password=s3cr3t",
        ),
    ],
)
def test_connection_config_error_scrubs_awkwardly_spelled_dsns(
    label: str, message: str
) -> None:
    """#527 review (P2): the scrub must not depend on convenient whitespace.

    The first implementation split on whitespace and kept tokens containing
    ``://`` or ``=``, so a LABELED dsn (``dsn=postgresql://...``) and libpq's
    supported SPACED form (``host = x  password = y``) both survived untouched --
    and `drift`/`profile`/`validate` print this text unredacted.
    """
    from seshat.connection_env import ConnectionConfigError, as_connection_config

    def _resolve():
        raise ValueError(message)

    with pytest.raises(ConnectionConfigError) as caught:
        as_connection_config(_resolve)

    scrubbed = str(caught.value)
    for fragment in ("s3cr3t", "alice", "db.example.com"):
        assert fragment not in scrubbed, (
            f"{label} form leaked {fragment!r}: {scrubbed!r}"
        )


def test_connection_config_error_scrubs_keyword_conninfo_too() -> None:
    """libpq accepts TWO DSN spellings and both must be scrubbed.

    ``redaction_core`` documents keyword conninfo (``host=.. password=..``) as a
    distinct form from the URI shape, so a scrub that only decomposed
    ``postgresql://`` would leave this one intact.
    """
    from seshat.connection_env import ConnectionConfigError, as_connection_config

    def _resolve_raising_with_conninfo():
        raise ValueError(
            "could not connect using host=db.example.com user=alice "
            "password=s3cr3t dbname=analytics"
        )

    with pytest.raises(ConnectionConfigError) as caught:
        as_connection_config(_resolve_raising_with_conninfo)

    message = str(caught.value)
    for fragment in ("s3cr3t", "alice", "db.example.com"):
        assert fragment not in message, (
            f"keyword-conninfo form leaked {fragment!r}: {message!r}"
        )
