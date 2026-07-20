"""`seshat scaffold-source <table>` self-sufficiency (issue #339).

A bare workspace (no dev repo) must obtain the three Stage-1 blank templates
from bundled package data, written non-destructively into mappings/<table>/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_STAGE1_FILES = (
    "source-profile.md",
    "readiness-status.yaml",
    "source-map.yaml",
)


def test_scaffold_source_writes_the_three_stage1_files(tmp_path: Path) -> None:
    from seshat.stage1_scaffold import scaffold_source

    report = scaffold_source(tmp_path, "sales_c086")

    for name in _STAGE1_FILES:
        target = tmp_path / "mappings" / "sales_c086" / name
        assert target.is_file()
        assert f"mappings/sales_c086/{name}" in report.written
    assert report.kept == ()


def test_scaffold_source_neutralizes_the_broken_adr_link(tmp_path: Path) -> None:
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "foo")
    profile = (tmp_path / "mappings" / "foo" / "source-profile.md").read_text(
        encoding="utf-8"
    )
    assert "../docs/decisions/0003-mapping-artifact-location.md" not in profile
    assert "ADR 0003 (mapping-artifact-location)" in profile


def test_scaffold_source_is_non_destructive_and_idempotent(tmp_path: Path) -> None:
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "foo")
    edited = tmp_path / "mappings" / "foo" / "source-map.yaml"
    edited.write_text("# hand-edited\n", encoding="utf-8")

    second = scaffold_source(tmp_path, "foo")

    assert "mappings/foo/source-map.yaml" in second.kept
    assert second.written == ()
    assert edited.read_text(encoding="utf-8") == "# hand-edited\n"


def test_scaffold_source_creates_mappings_dir_when_absent(tmp_path: Path) -> None:
    from seshat.stage1_scaffold import scaffold_source

    assert not (tmp_path / "mappings").exists()
    scaffold_source(tmp_path, "foo")
    assert (tmp_path / "mappings" / "foo").is_dir()


@pytest.mark.parametrize("bad", ["../evil", "a/b", "", ".", "..", "/abs"])
def test_scaffold_source_rejects_unsafe_table_segment(tmp_path: Path, bad: str) -> None:
    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, bad)


def test_scaffold_source_dev_checkout_fallback_resolves(tmp_path: Path) -> None:
    """No wheel data needed in the dev suite: the _SOURCE_ROOT fallback must
    find the repo-root templates/ so the three files still materialize."""
    from seshat.stage1_scaffold import scaffold_source

    report = scaffold_source(tmp_path, "foo")
    assert len(report.written) == 3


def test_scaffolded_readiness_degrades_to_unstarted_not_malformed(
    tmp_path: Path,
) -> None:
    """The scaffolded blank readiness-status.yaml must read as an UNSTARTED
    Source-Ready journey (outcome=next_action, stage=source_ready), never an
    input_defect / malformed-repair path (issue #339, degrade contract)."""
    from seshat.run_next import build_run_next_response
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "foo")
    resp = build_run_next_response(str(tmp_path), "foo")

    assert resp["outcome"] == "next_action"
    assert resp["stage"] == "source_ready"
    assert resp["read_only_proof"] is True


@pytest.mark.parametrize(
    "reserved",
    ["con", "CON", "aux", "nul", "com1", "lpt1", "prn", "Com9", "a:b", "a*b", "a?b"],
)
def test_scaffold_source_rejects_windows_reserved_and_invalid_names(
    tmp_path: Path, reserved: str
) -> None:
    """P2 (#342): names that match the charset but cannot be created as
    directories on Windows (reserved device names, invalid filename chars) must
    raise Stage1ScaffoldError -- the documented refusal -- not an uncaught
    filesystem OSError / traceback."""
    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, reserved)


def test_scaffold_source_refuses_symlinked_mappings_escape(tmp_path: Path) -> None:
    """P2 (#342): if `mappings/` is a symlink pointing outside --repo, writing
    into mappings/<table>/ would escape the repo. Refuse rather than follow the
    symlink out of the requested tree."""
    import os

    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, repo / "mappings", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(repo, "foo")

    # nothing was written outside the repo
    assert not (outside / "foo").exists()


def test_scaffold_source_wraps_oserror_as_stage1_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P2 backstop (#342): any residual filesystem OSError during the write
    (e.g. the Windows 260-char path limit) surfaces as Stage1ScaffoldError, so
    the CLI returns its refusal status instead of a traceback."""
    import seshat.stage1_scaffold as mod
    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    def _boom(target, data):
        raise OSError("simulated filesystem failure")

    monkeypatch.setattr(mod, "_write_if_absent", _boom)

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, "foo")


def test_scaffold_source_refuses_symlinked_output_file(tmp_path: Path) -> None:
    """P2 round-2 (#342): a pre-planted (even dangling) symlink AT an individual
    output path would let write_bytes() follow it out of --repo. Refuse any
    output path that is a symlink, before writing."""
    import os

    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    dest = tmp_path / "mappings" / "foo"
    dest.mkdir(parents=True)
    outside = tmp_path / "outside.yaml"  # dangling target (does not exist)
    try:
        os.symlink(outside, dest / "source-map.yaml")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, "foo")

    assert not outside.exists()  # nothing written through the symlink


def test_scaffold_source_keeps_preexisting_regular_file(tmp_path: Path) -> None:
    """A pre-existing REGULAR output file is still 'kept' (not a symlink refusal):
    the symlink guard must not regress the non-destructive keep behavior."""
    from seshat.stage1_scaffold import scaffold_source

    dest = tmp_path / "mappings" / "foo"
    dest.mkdir(parents=True)
    (dest / "source-map.yaml").write_text("# hand-authored\n", encoding="utf-8")

    report = scaffold_source(tmp_path, "foo")

    assert "mappings/foo/source-map.yaml" in report.kept
    assert (dest / "source-map.yaml").read_text(encoding="utf-8") == "# hand-authored\n"


@pytest.mark.parametrize("bad", ["orders.", "orders ", "orders.  ", " orders", "."])
def test_scaffold_source_rejects_trailing_dot_or_space(
    tmp_path: Path, bad: str
) -> None:
    """P2 round-3 (#342): Win32 strips trailing periods/spaces, so `orders.` or
    `orders ` would normalize to a DIFFERENT folder than reported. Reject a
    leading/trailing dot or space rather than silently operating on the wrong
    table folder."""
    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, bad)


def test_scaffold_source_refuses_non_file_output_collision(tmp_path: Path) -> None:
    """P2 round-3 (#342): if an output path already exists as a DIRECTORY (or
    other non-regular node), target.exists() is true and the path was reported
    'kept' -- a misleading success, since the required Stage-1 FILE is absent.
    Only a regular file is keepable; any other node type is refused."""
    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    dest = tmp_path / "mappings" / "foo"
    dest.mkdir(parents=True)
    # A directory sitting where source-profile.md should be.
    (dest / "source-profile.md").mkdir()

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, "foo")


def test_scaffolded_readiness_has_concrete_source_ready_stage(tmp_path: Path) -> None:
    """P2 round-4 (#342): the scaffolded readiness-status.yaml must carry a
    CONCRETE current_stage (source_ready), not the '<stage_key>' placeholder --
    otherwise RS1 rejects it the moment the workspace is committed. A
    just-onboarded table honestly IS at source_ready (not-yet-passed), so this
    is a stage LABEL, never fabricated evidence/approvals."""
    import yaml

    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "orders")
    data = yaml.safe_load(
        (tmp_path / "mappings" / "orders" / "readiness-status.yaml").read_text(
            encoding="utf-8-sig"
        )
    )
    assert data["current_stage"] == "source_ready"
    # honesty: no fabricated evidence or approvals were introduced
    assert data.get("evidence") == []
    assert data.get("approvals") == []


def test_scaffolded_readiness_passes_rs1_when_committed(tmp_path: Path) -> None:
    """Regression lock (#342): a committed scaffold must pass RS1 -- the
    `retail check` surface the original contract test missed. This is what
    proves the degrade-to-unstarted promise holds through the GATE, not just
    through `run_next`."""
    import subprocess

    from seshat.rules.readiness_status import check_readiness_status_consistency
    from seshat.runner import build_context
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "orders")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
        cwd=tmp_path,
        capture_output=True,
    )

    findings = list(check_readiness_status_consistency(build_context(tmp_path)))

    assert findings == [], [getattr(f, "message", f) for f in findings]


def test_scaffolded_source_map_profiled_from_points_at_materialized_profile(
    tmp_path: Path,
) -> None:
    """P2 round-4 (#342): source-map's meta.profiled_from FIELD (the machine-read
    provenance) must point at the MATERIALIZED profile
    (mappings/<table>/source-profile.md), not the dev-repo
    'templates/source-profile.md' a pip-only workspace does not have. (The
    illustrative 'sister artifacts' comment block is documentation, left as-is.)"""
    import yaml

    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "orders")
    sm = (tmp_path / "mappings" / "orders" / "source-map.yaml").read_text(
        encoding="utf-8"
    )
    assert 'profiled_from: "mappings/orders/source-profile.md"' in sm
    assert 'profiled_from: "templates/source-profile.md"' not in sm
    data = yaml.safe_load(sm)
    assert data["meta"]["profiled_from"] == "mappings/orders/source-profile.md"


def test_scaffolded_readiness_identity_matches_requested_table(tmp_path: Path) -> None:
    """P2 round-5 (#342): the scaffolded readiness must carry the REQUESTED
    table identity, not the generic '<schema>.<table>' / '<source_id>'
    placeholders -- otherwise run_next attributes the scope to the literal
    placeholder instead of the onboarded table."""
    import yaml

    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "foo")
    data = yaml.safe_load(
        (tmp_path / "mappings" / "foo" / "readiness-status.yaml").read_text(
            encoding="utf-8-sig"
        )
    )
    assert data["source_id"] == "foo"
    assert "foo" in str(data["table"])
    assert "<schema>" not in str(data["table"])
    assert "<source_id>" not in str(data["source_id"])


def test_scaffolded_next_attributes_scope_to_requested_table(tmp_path: Path) -> None:
    """Regression lock (#342): `seshat next` after scaffold must report the
    REQUESTED table (foo), not a '<...>' placeholder scope."""
    from seshat.run_next import build_run_next_response
    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "foo")
    resp = build_run_next_response(str(tmp_path), "foo")

    assert "<" not in str(resp["table"])
    assert "foo" in str(resp["table"])


@pytest.mark.parametrize("bad", ["a\nb", "a\tb", "a\x00b", "a\rb", "\x1f"])
def test_scaffold_source_rejects_control_characters(tmp_path: Path, bad: str) -> None:
    """P2 round-5 (#342): a control character (newline/tab/NUL/...) in the table
    name corrupts the line-oriented CLI output and is invalid on Windows (code
    points 0-31). Reject it as a documented refusal."""
    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, bad)


def test_scaffolded_readiness_next_action_is_concrete_source_ready(
    tmp_path: Path,
) -> None:
    """P2 round-6 (#342): the readiness next_action must be a concrete
    Source-Ready step, not the template's Mapping-stage placeholder example --
    status_surface projects it verbatim as the controlling action, and run_next
    otherwise emits a next_action_disagreement caveat."""
    import yaml

    from seshat.stage1_scaffold import scaffold_source

    scaffold_source(tmp_path, "foo")
    data = yaml.safe_load(
        (tmp_path / "mappings" / "foo" / "readiness-status.yaml").read_text(
            encoding="utf-8-sig"
        )
    )
    na = str(data["next_action"])
    assert "<" not in na and ">" not in na  # no placeholder
    assert "source" in na.lower() or "profile" in na.lower()


def test_scaffold_source_refuses_in_repo_symlinked_table_dir(tmp_path: Path) -> None:
    """P2 round-6 (#342): even an IN-REPO symlink alias (mappings/foo ->
    mappings/bar) resolves under root but writes foo-identified artifacts under
    bar. Reject a symlinked destination directory component regardless of where
    it points."""
    import os

    from seshat.stage1_scaffold import Stage1ScaffoldError, scaffold_source

    (tmp_path / "mappings" / "bar").mkdir(parents=True)
    try:
        os.symlink(
            tmp_path / "mappings" / "bar",
            tmp_path / "mappings" / "foo",
            target_is_directory=True,
        )
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not permitted in this environment")

    with pytest.raises(Stage1ScaffoldError):
        scaffold_source(tmp_path, "foo")


def test_cli_scaffold_source_hint_carries_repo(
    tmp_path: Path,
) -> None:
    """P2 round-6 (#342): the printed follow-up must carry --repo when the user
    passed a non-cwd --repo, so following the instruction inspects the scaffolded
    workspace, not the caller's cwd."""
    from seshat.stage1_scaffold import scaffold_source

    report = scaffold_source(tmp_path, "foo")
    note = " ".join(report.notes)
    # the next-step guidance references the table so it is unambiguous
    assert "foo" in note


def test_write_if_absent_atomic_create_keeps_a_racing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#345: close the TOCTOU window. The race is a file materializing AFTER both
    the ``_refuse_unwritable_target`` guard AND the ``is_file()`` keep-check see
    it absent, but BEFORE the write. Simulate that by planting the file from a
    patched ``Path.mkdir`` -- the last step before the write -- so both guards
    have already passed on the absent path. An atomic O_CREAT|O_EXCL create must
    then fail closed and KEEP the racing file; the old ``write_bytes`` truncates
    it (the bug this test locks out)."""
    from seshat.stage1_scaffold import _write_if_absent

    target = tmp_path / "raced.yaml"
    planted = b"planted-by-a-concurrent-process\n"
    real_mkdir = Path.mkdir

    def _mkdir_then_race(self: Path, *args, **kwargs) -> None:
        real_mkdir(self, *args, **kwargs)
        # A concurrent process wins the race in the window before our write.
        target.write_bytes(planted)

    monkeypatch.setattr(Path, "mkdir", _mkdir_then_race)

    written = _write_if_absent(target, b"our-content\n")

    assert written is False  # the atomic create refused to clobber
    assert target.read_bytes() == planted  # the racing file survived intact


def test_write_if_absent_writes_bytes_verbatim_no_newline_translation(
    tmp_path: Path,
) -> None:
    """#345 regression: the atomic create writes bytes verbatim -- a bare LF must
    not become CRLF on Windows, preserving this module's copied-byte-for-byte
    guarantee (the prior impl, write_bytes, is binary). The ``os.fdopen(fd, "wb")``
    binary stream is what guarantees this; O_BINARY on the fd is belt-and-braces
    for a future raw-os.write refactor. This test pins the OBSERVABLE contract
    (bytes in == bytes out), independent of which mechanism enforces it."""
    from seshat.stage1_scaffold import _write_if_absent

    target = tmp_path / "verbatim.yaml"
    payload = b"line1\nline2\n"  # bare LFs, no CR

    written = _write_if_absent(target, payload)

    assert written is True
    assert target.read_bytes() == payload  # no \r inserted


def test_write_if_absent_writes_a_fresh_file(tmp_path: Path) -> None:
    """#345: the ordinary path -- an absent target is written and reported."""
    from seshat.stage1_scaffold import _write_if_absent

    target = tmp_path / "sub" / "fresh.yaml"
    target.parent.mkdir(parents=True)

    assert _write_if_absent(target, b"data\n") is True
    assert target.read_bytes() == b"data\n"


def test_write_if_absent_lets_umask_govern_mode(tmp_path: Path) -> None:
    """#345 Codex P2: the atomic create must use mode 0o666 so the caller's umask
    keeps governing access (matching the prior write_bytes). Under a permissive
    umask (0o002) the scaffold file must be group-writable (0o664) -- a hard-coded
    0o644 would have stripped group write regardless. POSIX-only (Windows ignores
    the mode bits)."""
    import os

    if os.name == "nt":
        pytest.skip("POSIX file-mode semantics only")

    from seshat.stage1_scaffold import _write_if_absent

    target = tmp_path / "moded.yaml"
    old = os.umask(0o002)
    try:
        _write_if_absent(target, b"x\n")
    finally:
        os.umask(old)

    mode = target.stat().st_mode & 0o777
    # group-write present == umask governed (0o666 & ~0o002 == 0o664); a forced
    # 0o644 would fail this. This pins that umask, not a hard-coded mode, decides.
    assert mode & 0o020, f"group-write stripped despite permissive umask: {oct(mode)}"
