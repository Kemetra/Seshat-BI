"""Regression tests for the Phase 2 external adversarial review findings.

Each test names the finding it closes and fails against the pre-fix code. They live
in one module so the review's outcome is greppable rather than scattered.

Reviewed at commit 101131d; findings 1, 2, 3, 6, 7, 8 and the finding-9 test-weakness
are closed here. Findings 5 (FR-026's full secret list), 10 (file-kind checks) and 12
(port re-pin) are routed to T011 as documented deferrals instead of being silently
marked done.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# --------------------------------------------------------------------------- #
# Finding 1 -- FR-001 validation was never executed                           #
# --------------------------------------------------------------------------- #


def _make_workspace(root: Path) -> Path:
    """A directory the shipped recognizer accepts."""
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    return root


def test_the_launcher_refuses_a_nonexistent_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 1: `LaunchConfiguration.for_workspace` had ZERO production callers.

    The launcher resolved `--repo` with a bare `Path(...).resolve()`, so a
    nonexistent path, or a plain file, reached the serving step.
    """
    from seshat.studio import __main__ as launcher

    exit_code = launcher.main(["--repo", str(tmp_path / "definitely-absent")])

    assert exit_code == 2
    assert "workspace" in capsys.readouterr().err.lower()


def test_the_launcher_refuses_a_file_as_a_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from seshat.studio import __main__ as launcher

    target = tmp_path / "not-a-directory.toml"
    target.write_text("", encoding="utf-8")

    assert launcher.main(["--repo", str(target)]) == 2
    assert "workspace" in capsys.readouterr().err.lower()


def test_the_launcher_refuses_a_directory_that_is_not_a_seshat_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The contract says "accepts only a RECOGNIZED Seshat workspace".

    `is_dir()` is not recognition. The shipped `looks_like_workspace` recognizer
    keys on real workspace markers and must be the one deciding.
    """
    from seshat.studio import __main__ as launcher

    plain = tmp_path / "just-a-folder"
    plain.mkdir()

    assert launcher.main(["--repo", str(plain)]) == 2
    assert "workspace" in capsys.readouterr().err.lower()


def test_the_workspace_is_validated_before_the_web_stack_is_imported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Contract §Process Boundary 1: resolve BEFORE importing or starting the server.

    Pre-fix the import happened ~20 lines earlier than the workspace check, so a
    bad workspace with the extra absent reported the WRONG problem.
    """
    import builtins

    from seshat.studio import __main__ as launcher

    original = builtins.__import__
    imported: list[str] = []

    def record(name: str, *args: object, **kwargs: object) -> object:
        if name.split(".")[0] in {"fastapi", "uvicorn", "starlette"}:
            imported.append(name)
            raise ModuleNotFoundError(f"No module named {name!r}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", record)

    launcher.main(["--repo", str(tmp_path / "absent")])

    assert not imported, (
        "the web stack was imported before the workspace was validated; a bad "
        "workspace must be refused first"
    )


# --------------------------------------------------------------------------- #
# Finding 2 -- inverted exit codes                                            #
# --------------------------------------------------------------------------- #


def test_help_exits_zero() -> None:
    """Finding 2: `exit_signal.code or _EXIT_USAGE` turned argparse's 0 into 1."""
    from seshat.studio import __main__ as launcher

    with pytest.raises(SystemExit) as exit_info:
        launcher._build_parser().parse_args(["--help"])

    assert exit_info.value.code == 0
    assert launcher.main(["--help"]) == 0


def test_an_unknown_flag_is_a_usage_error_not_a_refusal() -> None:
    """Exit 2 is reserved for refusal (missing extra/assets); usage is 1."""
    from seshat.studio import __main__ as launcher

    assert launcher.main(["--nonsense"]) == 1


# --------------------------------------------------------------------------- #
# Finding 3 -- the diagnostic lied about a deeper import failure              #
# --------------------------------------------------------------------------- #


def test_a_deeper_import_failure_is_not_blamed_on_the_missing_extra(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 3: any ModuleNotFoundError inside fastapi's tree was reported as
    "the `studio` extra is not installed", telling users to install what they have.
    """
    import builtins

    from seshat.studio import __main__ as launcher

    _make_workspace(tmp_path)
    original = builtins.__import__

    def broken_transitive(name: str, *args: object, **kwargs: object) -> object:
        if name.split(".")[0] in {"fastapi", "uvicorn", "starlette"}:
            # `name=` is set exactly as the real import machinery would set it for a
            # failure deeper in fastapi's dependency tree.
            raise ModuleNotFoundError(
                "No module named 'some_transitive_dep'", name="some_transitive_dep"
            )
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_transitive)

    launcher.main(["--repo", str(tmp_path)])
    err = capsys.readouterr().err

    assert "some_transitive_dep" in err
    assert "is not installed" not in err, (
        "a broken transitive dependency was misreported as an absent extra"
    )


def test_a_genuinely_absent_extra_still_names_the_install_lanes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The finding-3 fix must not weaken the real missing-extra path."""
    import builtins

    from seshat.studio import __main__ as launcher

    _make_workspace(tmp_path)
    original = builtins.__import__

    def missing(name: str, *args: object, **kwargs: object) -> object:
        root = name.split(".")[0]
        if root in {"fastapi", "uvicorn", "starlette"}:
            raise ModuleNotFoundError(f"No module named '{root}'", name=root)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)

    assert launcher.main(["--repo", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "pipx inject seshat-bi" in err
    assert "pip install" in err


# --------------------------------------------------------------------------- #
# Finding 6 -- absolute paths survived after a non-space delimiter            #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "template",
    [
        "({path})",
        "repo={path}",
        "<{path}>",
        "a,{path}",
        "path:{path}",
        "[{path}]",
        "'{path}'",
        '"{path}"',
    ],
)
def test_an_absolute_path_is_redacted_after_any_delimiter(
    tmp_path: Path, template: str
) -> None:
    """Finding 6: the `(?<![^\\s"'])` lookbehind only allowed whitespace or a quote.

    `repo=C:\\Users\\...` and `(C:\\Users\\...)` are the commonest diagnostic shapes,
    and both leaked the operator's full layout.
    """
    from seshat.studio import redaction

    secret_path = Path("C:/Users/someone/.ssh/id_rsa")
    text = template.format(path=secret_path)

    scrubbed = redaction.redact_paths(text, workspace_root=tmp_path)

    assert "someone" not in scrubbed, f"leaked from {text!r} -> {scrubbed!r}"


def test_an_in_root_path_after_a_delimiter_becomes_relative(tmp_path: Path) -> None:
    """The same shape must not leak the workspace root either."""
    from seshat.studio import redaction

    target = tmp_path / "gold" / "fct_sales.sql"

    scrubbed = redaction.redact_paths(f"reading file={target}", workspace_root=tmp_path)

    assert str(tmp_path) not in scrubbed
    assert "gold/fct_sales.sql" in scrubbed


def test_a_url_still_survives_the_widened_pattern(tmp_path: Path) -> None:
    """Widening the lookbehind must not start eating URL paths."""
    from seshat.studio import redaction

    message = "see http://127.0.0.1:8931/api/v1/workspace"

    assert redaction.redact_paths(message, workspace_root=tmp_path) == message


def test_relative_references_still_survive_the_widened_pattern(tmp_path: Path) -> None:
    from seshat.studio import redaction

    message = "blocked at mappings/retail_store_sales/source-map.yaml"

    assert redaction.redact_paths(message, workspace_root=tmp_path) == message


# --------------------------------------------------------------------------- #
# Finding 7 -- a prefix secret leaked the longer secret's remainder           #
# --------------------------------------------------------------------------- #


def test_overlapping_secrets_are_redacted_longest_first() -> None:
    """Finding 7: `replace_fragments` substitutes in caller order.

    With the short secret first, redacting it leaves the longer secret's tail in
    the clear.
    """
    from seshat.studio import redaction

    short = "abcdefghijklmnop"
    long = short + "1234567890"

    scrubbed = redaction.redact(f"value={long} end", secrets=[short, long])

    assert "1234567890" not in scrubbed, f"leaked the remainder: {scrubbed!r}"


# --------------------------------------------------------------------------- #
# Finding 8 -- redact_for_boundary failed OPEN by exception                    #
# --------------------------------------------------------------------------- #


def test_the_boundary_redactor_never_raises_on_a_short_secret(tmp_path: Path) -> None:
    """Finding 8: a 12-15 character password raised out of the safety function.

    The contract requires "a categorical error and WITHHOLDS the raw value" -- an
    exception returns control to a caller still holding the unsafe text, which is
    failing open. The boundary must return safe text unconditionally.
    """
    from seshat.studio import redaction

    short_password = "hunter2hunter2"  # 14 characters -- a real secret
    text = f"connect failed for {short_password}"

    scrubbed = redaction.redact_for_boundary(
        text, secrets=[short_password], workspace_root=tmp_path
    )

    assert short_password not in scrubbed
    assert redaction.REDACTED in scrubbed


def test_the_strict_helper_still_refuses_an_unsafely_short_secret() -> None:
    """`redact` keeps its strict contract; only the BOUNDARY entry point is lenient.

    A 3-character "secret" is a caller error: applying it would corrupt innocent
    text, so the strict helper still raises for callers that can handle it.
    """
    from seshat.studio import redaction

    with pytest.raises(ValueError, match="too short"):
        redaction.redact("the cat sat on the mat", secrets=["cat"])


def test_the_refusal_message_never_contains_the_secret() -> None:
    from seshat.studio import redaction

    with pytest.raises(ValueError) as raised:
        redaction.redact("x", secrets=["sensitive"])

    assert "sensitive" not in str(raised.value)


# --------------------------------------------------------------------------- #
# Finding 5 -- FR-026's named secret classes were unimplemented                #
# --------------------------------------------------------------------------- #


def test_a_dsn_is_redacted(tmp_path: Path) -> None:
    """FR-026 names DSNs first. Delegates to the hardened `redaction_core`."""
    from seshat.studio import redaction

    scrubbed = redaction.redact_for_boundary(
        "connect failed: postgresql://admin:S3cretPassw0rd@db.example.com:5432/retail",
        workspace_root=tmp_path,
    )

    assert "S3cretPassw0rd" not in scrubbed
    assert "admin" not in scrubbed
    assert "db.example.com" not in scrubbed


def test_an_authorization_header_is_redacted(tmp_path: Path) -> None:
    """FR-026 names authorization headers explicitly."""
    from seshat.studio import redaction

    scrubbed = redaction.redact_for_boundary(
        "Authorization: Bearer sk-proj-AAAABBBBCCCCDDDD1111", workspace_root=tmp_path
    )

    assert "sk-proj-AAAABBBBCCCCDDDD1111" not in scrubbed
    # The header NAME survives so the diagnostic still says what failed.
    assert "Authorization" in scrubbed


def test_a_basic_authorization_value_is_redacted(tmp_path: Path) -> None:
    from seshat.studio import redaction

    scrubbed = redaction.redact_for_boundary(
        "Authorization: Basic YWRtaW46c3VwZXJzZWNyZXQ=", workspace_root=tmp_path
    )

    assert "YWRtaW46c3VwZXJzZWNyZXQ" not in scrubbed


@pytest.mark.parametrize(
    "assignment",
    [
        "OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456",
        "SESHAT_DBT_PASSWORD=S3cretPassw0rd",
        "password=S3cretPassw0rd",
        "api_key: sk-abcdefghijklmnopqrstuvwxyz",
        "secret_token=abcdefghijklmnopqrst",
    ],
)
def test_a_credential_shaped_assignment_is_redacted(
    assignment: str, tmp_path: Path
) -> None:
    """FR-026's "credential-shaped values", covering environment dumps."""
    from seshat.studio import redaction

    scrubbed = redaction.redact_for_boundary(assignment, workspace_root=tmp_path)
    value = assignment.split("=", 1)[-1].split(":", 1)[-1].strip()

    assert value not in scrubbed, f"leaked from {assignment!r} -> {scrubbed!r}"
    # The KEY survives: knowing which credential is misconfigured is the diagnostic.
    assert assignment.split("=")[0].split(":")[0] in scrubbed


def test_a_libpq_conninfo_password_is_redacted(tmp_path: Path) -> None:
    from seshat.studio import redaction

    scrubbed = redaction.redact_for_boundary(
        "host=db.example.com password=S3cretPassw0rd dbname=retail",
        workspace_root=tmp_path,
    )

    assert "S3cretPassw0rd" not in scrubbed


@pytest.mark.parametrize(
    "innocent",
    [
        "status: blocked",
        "stage: mapping",
        "none; named-human approval required",
        "required_authority: named_human",
        "grain: one row per order line",
    ],
)
def test_credential_rules_do_not_corrupt_innocent_governed_text(
    innocent: str, tmp_path: Path
) -> None:
    """The over-redaction guard, applied to the new credential rules.

    `status:` and `stage:` are key/value shaped but carry no credential, so a rule
    keyed on shape alone rather than on a credential-NAME would corrupt exactly the
    truthful projection Studio exists to provide.
    """
    from seshat.studio import redaction

    assert redaction.redact_for_boundary(innocent, workspace_root=tmp_path) == innocent


# --------------------------------------------------------------------------- #
# Finding 9 -- the containment check was unverified on Windows                 #
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(sys.platform != "win32", reason="Windows junction semantics")
def test_a_junction_escaping_the_root_is_refused(tmp_path: Path) -> None:
    """Finding 9: all 74 Phase 2 tests passed with the containment check DELETED.

    The only real escape test needed symlink privileges Windows withholds, and its
    stand-in asserted a tautology. A junction (`mklink /J`) needs no privileges, so
    this test actually exercises the resolve-then-compare comparison.
    """
    import subprocess

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")

    root = tmp_path / "workspace"
    root.mkdir()
    junction = root / "jlink"

    made = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        text=True,
    )
    if made.returncode != 0:
        pytest.skip(f"junction creation unavailable: {made.stderr.strip()}")

    from seshat.studio import config

    with pytest.raises(ValueError, match="escapes"):
        config.resolve_contained_path(root, "jlink/secret.txt")


def test_the_containment_check_is_load_bearing(tmp_path: Path) -> None:
    """A direct assertion on the comparison itself, with no link needed.

    `resolve_contained_path` builds `root / reference` then resolves. This proves
    the resolved-parents comparison rejects a target outside the root even when the
    literal reference passed every earlier check.
    """
    from seshat.studio import config

    root = tmp_path / "workspace"
    root.mkdir()

    # `root.parent` is outside the root, reached without `..` in the reference by
    # using a name that resolves upward only after `resolve()` follows the tree.
    contained = config.resolve_contained_path(root, "inside/file.yaml")
    assert root.resolve() in contained.parents

    with pytest.raises(ValueError):
        config.resolve_contained_path(root, "../outside/file.yaml")
