"""TDD tests for the user-workspace initializer (spec 107, roadmap M3).

``init_project`` scaffolds a FRESH, empty Retail-BI project workspace for a new
user -- distinct from `retail init`, which bootstraps `.seshat/` + fenced regions
into an EXISTING repo. Covers FR-001..FR-006:

* FR-001 fresh scaffold creates the workspace shape, deterministic + idempotent;
* FR-002 does not modify/duplicate `retail init`'s behavior;
* FR-003 refuses a non-empty target without --force;
* FR-004 static scaffolding only -- no fabricated data/credentials;
* FR-005 pure stdlib filesystem, no DB/network at module scope;
* FR-006 the generated workspace passes `retail check` (clean baseline).

Deviation from plan.md (recorded, owner-review pending): the workspace does NOT
call `kit_init.bootstrap()` / write `.seshat/compass.yaml`. A spike (see
specs/107-user-workspace-init/tasks.md) proved that bootstrapping flips
`is_bootstrapped()` to True, which activates the KIT_SELF rules (A1, A3, AP1,
SC1, SC2, SF1, DF1, AQ1, DR1) -- these require the KIT's OWN internal manifests
(docs/routing/routes.yaml, docs/quality/status-claims.yaml, a KPI domain corpus,
...), which a user workspace never has and must never fabricate (FR-004). FR-006
("passes retail check") is the harder, must-verify constraint, so the workspace
is shipped as a genuinely non-bootstrapped ("drop-in tier") repo: `.seshat/` is
NOT written at all by init_project (no bootstrap substrate is generated); the
KIT_SELF rules correctly SKIP (INFO) rather than ERROR.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from seshat import cli
from seshat.workspace_init import init_project

pytestmark = pytest.mark.unit


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _git_init_and_commit(repo: Path, message: str = "feat: scaffold workspace") -> None:
    """Init a git repo, stage everything, and commit (needed for `retail check`:
    P1/G1/G4/C2 read git-TRACKED files, and P2 needs >=2 commits for HEAD~1..HEAD)."""
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def target(tmp_path, monkeypatch) -> Path:
    # Realistic shape: "new user, empty folder, `seshat init-project <name>`" --
    # the CWD is the empty folder the user is standing in.
    monkeypatch.chdir(tmp_path)
    return tmp_path / "my-retail-bi"


# ---------------------------------------------------------------------------
# FR-001 -- fresh scaffold creates the workspace shape.
# ---------------------------------------------------------------------------


def test_fresh_scaffold_creates_workspace_shape(target) -> None:
    written = init_project(str(target))
    assert written  # non-empty list of created paths

    assert target.is_dir()
    assert (target / "mappings").is_dir()
    # #349: the medallion SQL home is warehouse/migrations/ (what the readers
    # read), not the unread warehouse/{bronze,silver,gold}/.
    assert (target / "warehouse" / "migrations").is_dir()
    assert (target / "powerbi").is_dir()
    assert (target / "reports").is_dir()
    assert (target / "evidence").is_dir()
    assert (target / ".env.example").is_file()
    assert (target / "README.md").is_file()


def test_scaffold_warehouse_layout_matches_the_readers(target) -> None:
    """#349: the scaffold must create `warehouse/migrations/` -- the ONE medallion
    SQL location every governance rule + Dagster actually read (and the reference
    example ships). It must NOT create the unread `warehouse/{bronze,silver,gold}/`
    that silently swallowed SQL the tool could never see."""
    init_project(str(target))

    # The readers' location exists and is the SQL home.
    assert (target / "warehouse" / "migrations").is_dir()
    # The unread fiction is gone (nothing reads these; SQL here is invisible).
    assert not (target / "warehouse" / "silver").exists()
    assert not (target / "warehouse" / "gold").exists()
    assert not (target / "warehouse" / "bronze").exists()


def test_readmes_direct_sql_to_migrations_not_medallion_dirs(target) -> None:
    """#349: the READMEs must point the user at `warehouse/migrations/` (where the
    readers look), never at `warehouse/{bronze,silver,gold}/` (where SQL is
    invisible). A user who follows the README must land where the tool reads."""
    init_project(str(target))
    root_readme = (target / "README.md").read_text(encoding="utf-8")
    wh_readme = (target / "warehouse" / "README.md").read_text(encoding="utf-8")

    assert "warehouse/migrations" in root_readme
    for readme in (root_readme, wh_readme):
        # no direction to the unread medallion SQL homes
        assert "{bronze,silver,gold}" not in readme
        assert "`bronze/`" not in readme and "`silver/`" not in readme


def test_fresh_scaffold_returns_created_paths_as_path_objects(target) -> None:
    written = init_project(str(target))
    assert all(isinstance(p, Path) for p in written)
    assert all(p.exists() for p in written)


def test_env_example_carries_no_real_values(target) -> None:
    # Mirrors C2's MUST_BE_EMPTY set (rules/git_meta.py): host/name/user/password
    # must be empty. A non-secret default like the port number or SSL mode is
    # not "a real value" in the credential sense and matches the repo's own
    # .env.example convention (ANALYTICS_DB_PORT=25060, ANALYTICS_DB_SSLMODE=require).
    init_project(str(target))
    text = (target / ".env.example").read_text(encoding="utf-8")
    pairs: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        pairs[key.strip()] = value.strip()
    for key in (
        "ANALYTICS_DB_HOST",
        "ANALYTICS_DB_NAME",
        "ANALYTICS_DB_USER",
        "ANALYTICS_DB_PASSWORD",
    ):
        assert pairs.get(key, "") == "", f"{key} must not carry a real value"


def test_readme_points_at_the_readiness_flow(target) -> None:
    init_project(str(target))
    text = (target / "README.md").read_text(encoding="utf-8")
    assert "retail check" in text or "check" in text.lower()


def test_scaffold_does_not_write_seshat_bootstrap(target) -> None:
    # Deviation (see module docstring): init_project must NOT write
    # .seshat/compass.yaml -- that would flip the workspace bootstrapped and
    # fail KIT_SELF rules the workspace can never satisfy (FR-004/FR-006).
    init_project(str(target))
    assert not (target / ".seshat" / "compass.yaml").exists()


def test_scaffold_writes_no_credentials_or_fabricated_content(target) -> None:
    init_project(str(target))
    for path in target.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "BEGIN PRIVATE KEY" not in text
        assert "postgresql://" not in text or "ANALYTICS_DB" in text


# ---------------------------------------------------------------------------
# FR-001 -- deterministic and idempotent (re-run byte-identical).
# ---------------------------------------------------------------------------


def test_rerun_is_idempotent_byte_identical(target) -> None:
    init_project(str(target))
    before = {p: (target / p).read_bytes() for p in _relative_files(target)}
    init_project(str(target), force=True)
    after = {p: (target / p).read_bytes() for p in _relative_files(target)}
    assert before == after


def test_rerun_with_force_does_not_duplicate_rows(target) -> None:
    init_project(str(target))
    env_before = (target / ".env.example").read_text(encoding="utf-8")
    init_project(str(target), force=True)
    env_after = (target / ".env.example").read_text(encoding="utf-8")
    assert env_before == env_after
    # no duplicated ANALYTICS_DB_HOST= lines etc.
    for key in ("ANALYTICS_DB_HOST", "ANALYTICS_DB_PORT"):
        assert env_after.count(key) == 1


def _relative_files(root: Path) -> list[str]:
    return sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file()
    )


# ---------------------------------------------------------------------------
# FR-003 -- refuse a non-empty target without --force; never clobber.
# ---------------------------------------------------------------------------


def test_refuses_nonempty_target_without_force(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "existing"
    target.mkdir()
    (target / "user-file.txt").write_text("do not touch", encoding="utf-8")

    with pytest.raises(FileExistsError):
        init_project(str(target))

    # user's file is untouched
    assert (target / "user-file.txt").read_text(encoding="utf-8") == "do not touch"
    assert not (target / "README.md").exists()


def test_force_scaffolds_into_a_nonempty_target(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "existing"
    target.mkdir()
    (target / "user-file.txt").write_text("keep me", encoding="utf-8")

    written = init_project(str(target), force=True)
    assert written
    assert (target / "README.md").exists()
    # --force scaffolds around existing user files; it does not delete them.
    assert (target / "user-file.txt").read_text(encoding="utf-8") == "keep me"


def test_empty_existing_dir_does_not_need_force(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "empty-dir"
    target.mkdir()
    written = init_project(str(target))
    assert written
    assert (target / "README.md").exists()


# ---------------------------------------------------------------------------
# FR-005 -- path-traversal / outside-CWD guard.
# ---------------------------------------------------------------------------


def test_refuses_path_traversal_outside_cwd(tmp_path, monkeypatch) -> None:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    outside = tmp_path / "outside-target"

    with pytest.raises(ValueError):
        init_project(f"../{outside.name}")


def test_refuses_absolute_path_outside_cwd(tmp_path, monkeypatch) -> None:
    cwd = tmp_path / "cwd2"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    outside = (tmp_path / "elsewhere").resolve()

    with pytest.raises(ValueError):
        init_project(str(outside))


def test_allows_relative_name_under_cwd(tmp_path, monkeypatch) -> None:
    cwd = tmp_path / "cwd3"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    written = init_project("my-retail-bi")
    assert written
    assert (cwd / "my-retail-bi" / "README.md").exists()


def test_allows_absolute_path_that_is_under_cwd(tmp_path, monkeypatch) -> None:
    cwd = tmp_path / "cwd4"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    target = cwd / "nested" / "my-retail-bi"
    written = init_project(str(target))
    assert written
    assert (target / "README.md").exists()


# ---------------------------------------------------------------------------
# FR-005 -- pure filesystem; no DB/network at module scope.
# ---------------------------------------------------------------------------


def test_gitkeep_write_refuses_a_symlink_escape(tmp_path, monkeypatch) -> None:
    """#352: the conditional `.gitkeep` write must not follow a pre-planted
    symlink out of the workspace. Route through the hardened safe_write so a
    symlinked `.gitkeep` (dangling) is refused rather than followed."""
    import os

    from seshat.safe_write import SafeWriteError

    monkeypatch.chdir(tmp_path)
    target = tmp_path / "ws"
    # Pre-create the first empty dir + a symlinked .gitkeep pointing outside.
    from seshat.workspace_init import _EMPTY_DIRS, _GITKEEP_NAME

    first = target / _EMPTY_DIRS[0]
    first.mkdir(parents=True)
    outside = tmp_path / "outside-gitkeep"
    try:
        os.symlink(outside, first / _GITKEEP_NAME)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(SafeWriteError):
        init_project(str(target), force=True)
    assert not outside.exists()  # nothing written through the symlink


def test_module_has_no_module_scope_db_or_network_import() -> None:
    import inspect

    from seshat import workspace_init as wi

    src = inspect.getsource(wi)
    for forbidden in ("import psycopg2", "import requests", "import socket"):
        assert forbidden not in src


# ---------------------------------------------------------------------------
# FR-006 -- the generated workspace passes `retail check` (clean baseline).
# ---------------------------------------------------------------------------


def test_generated_workspace_passes_retail_check(target, capsys) -> None:
    init_project(str(target))
    # P2 needs >=2 commits for the default HEAD~1..HEAD local-fallback range;
    # P1/G1/G4/C2 read git-tracked files (git ls-files), so the shape must be
    # committed. init_project itself never touches git (scope discipline) --
    # the test owns the git state, matching how a real user would `git init`
    # + commit their new workspace.
    _git_init_and_commit(target, "feat: scaffold workspace")
    (target / "README.md").write_text(
        (target / "README.md").read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    _git(target, "add", "-A")
    _git(target, "commit", "-q", "-m", "feat: second commit")

    code = cli.main(["check", "--repo", str(target)])
    out = capsys.readouterr().out
    assert code == 0, out


def test_generated_workspace_passes_retail_check_with_single_commit_via_msg_file(
    target, tmp_path, capsys
) -> None:
    # Alternate path that doesn't require a 2nd commit: pass the commit message
    # via --commit-msg-file (the commit-msg-hook mode), which bypasses the
    # HEAD~1..HEAD local-fallback range entirely.
    init_project(str(target))
    _git_init_and_commit(target, "feat: scaffold workspace")

    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text("feat: scaffold workspace\n", encoding="utf-8")

    code = cli.main(
        ["check", "--repo", str(target), "--commit-msg-file", str(msg_file)]
    )
    out = capsys.readouterr().out
    assert code == 0, out
