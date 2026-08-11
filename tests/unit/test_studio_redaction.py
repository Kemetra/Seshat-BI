"""T008 -- Studio boundary redaction, tested before it is applied anywhere.

Contract: "The raw token and cookie value never enter logs, agent context, events,
errors, or durable files" and "Browser responses show a safe relative reference or
label, never an absolute path" (FR-026, security-boundary.md).

Two secret classes, deliberately handled differently:

* **Session material** -- high-entropy, exact-match, always redacted.
* **Absolute paths** -- rewritten to a workspace-relative reference so the reader
  still learns WHICH file is at fault without learning the operator's directory
  layout.

Over-redaction is a real defect, not a safe default. `seshat/dbt/redaction.py`
documents the incident this module must avoid: redacting every configured value
mangled innocent text -- the English word "require" destroyed the governed const
"named-human approval required", and a bare port number matched unrelated digits.
Studio's projection is supposed to be TRUTHFUL, so a redactor that corrupts
evidence defeats the feature.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# --------------------------------------------------------------------------- #
# Session material                                                            #
# --------------------------------------------------------------------------- #


def test_a_session_token_is_redacted_from_text() -> None:
    from seshat.studio import redaction, session

    token = session.generate_bootstrap_token()
    text = f"exchange failed for token {token} at startup"

    scrubbed = redaction.redact(text, secrets=[token])

    assert token not in scrubbed
    assert redaction.REDACTED in scrubbed


def test_every_occurrence_is_redacted() -> None:
    from seshat.studio import redaction, session

    token = session.generate_bootstrap_token()

    scrubbed = redaction.redact(f"{token} ... {token}", secrets=[token])

    assert token not in scrubbed


def test_redaction_survives_a_none_or_empty_secret() -> None:
    """An empty secret must not turn into a match-everything pattern."""
    from seshat.studio import redaction

    text = "nothing secret here"

    assert redaction.redact(text, secrets=["", None]) == text  # type: ignore[list-item]


def test_a_cookie_value_is_redacted() -> None:
    from seshat.studio import redaction, session

    token = session.generate_bootstrap_token()
    store = session.SessionStore(token)
    cookie = store.exchange(token)
    assert cookie is not None

    scrubbed = redaction.redact(
        f"Cookie: {session.SESSION_COOKIE_NAME}={cookie}", secrets=[cookie]
    )

    assert cookie not in scrubbed
    # The cookie NAME is not a secret; keeping it preserves a useful diagnostic.
    assert session.SESSION_COOKIE_NAME in scrubbed


# --------------------------------------------------------------------------- #
# Absolute paths -- rewritten, not blanked                                    #
# --------------------------------------------------------------------------- #


def test_an_absolute_path_inside_the_root_becomes_a_relative_reference(
    tmp_path: Path,
) -> None:
    """The reader must still learn WHICH file, without the directory layout."""
    from seshat.studio import redaction

    target = tmp_path / "mappings" / "readiness-status.yaml"

    scrubbed = redaction.redact_paths(
        f"failed to parse {target}", workspace_root=tmp_path
    )

    assert str(tmp_path) not in scrubbed
    assert "mappings/readiness-status.yaml" in scrubbed


def test_an_absolute_path_outside_the_root_is_labelled_not_leaked(
    tmp_path: Path,
) -> None:
    """A path outside the workspace has no safe relative form, so it is a label."""
    from seshat.studio import redaction

    outside = Path("C:/Users/someone/.codex/auth.json")

    scrubbed = redaction.redact_paths(f"read {outside}", workspace_root=tmp_path)

    assert "someone" not in scrubbed
    assert redaction.REDACTED_PATH in scrubbed


def test_a_unc_path_is_not_leaked(tmp_path: Path) -> None:
    """Found by adversarial probing: `\\\\server\\share\\...` bypassed the pattern.

    A UNC path has no drive letter and does not start with a single `/`, so the
    drive-letter and POSIX-root branches both missed it and the server and share
    names reached the reader verbatim.
    """
    from seshat.studio import redaction

    # Built from chr(92) so no escaping layer can silently halve the backslashes:
    # a two-backslash string is NOT a UNC path, and asserting on one would make
    # this test pass without exercising the UNC branch at all.
    backslash = chr(92)
    unc = f"{backslash * 2}fileserver{backslash}finance{backslash}secret.txt"
    assert unc.startswith(backslash * 2), "the fixture must be a real UNC path"

    scrubbed = redaction.redact_paths(f"failed {unc}", workspace_root=tmp_path)

    assert "fileserver" not in scrubbed
    assert "finance" not in scrubbed
    assert "secret.txt" not in scrubbed
    assert redaction.REDACTED_PATH in scrubbed


def test_the_workspace_root_itself_is_named_not_rendered_as_a_dot(
    tmp_path: Path,
) -> None:
    """`relative_to(root)` yields `.` for the root, which tells the reader nothing."""
    from seshat.studio import redaction

    scrubbed = redaction.redact_paths(f"root is {tmp_path}", workspace_root=tmp_path)

    assert str(tmp_path) not in scrubbed
    assert scrubbed.rstrip() != "root is ."
    assert "workspace" in scrubbed.lower()


def test_a_url_path_is_not_mistaken_for_a_filesystem_path(tmp_path: Path) -> None:
    """API routes in a diagnostic are not filesystem paths and must survive."""
    from seshat.studio import redaction

    message = "see http://127.0.0.1:8931/api/v1/workspace"

    assert redaction.redact_paths(message, workspace_root=tmp_path) == message


def test_relative_references_are_left_intact(tmp_path: Path) -> None:
    """Workspace-relative text is already safe; rewriting it destroys evidence."""
    from seshat.studio import redaction

    message = "blocked at mappings/retail_store_sales/source-map.yaml"

    assert redaction.redact_paths(message, workspace_root=tmp_path) == message


# --------------------------------------------------------------------------- #
# Over-redaction guards -- the `dbt/redaction.py` lesson                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "innocent",
    [
        "none; named-human approval required",
        "status: blocked",
        "stage mapping is current",
        "5432",
        "require",
    ],
)
def test_innocent_governed_text_is_never_corrupted(
    innocent: str, tmp_path: Path
) -> None:
    """Short, dictionary-like, public values must pass through untouched.

    This is the property `seshat/dbt/redaction.py` had to learn the hard way: a
    redactor that treats every configured value as a secret rewrites innocent
    substrings and corrupts the tool's own governed evidence.
    """
    from seshat.studio import redaction

    assert redaction.redact_paths(innocent, workspace_root=tmp_path) == innocent
    assert redaction.redact(innocent, secrets=[]) == innocent


def test_a_short_secret_is_refused_rather_than_applied() -> None:
    """A 3-character "secret" would match everywhere; that is a caller error.

    Refusing beats silently corrupting the payload, and beats silently ignoring a
    value the caller believed was being protected.
    """
    from seshat.studio import redaction

    with pytest.raises(ValueError, match="too short"):
        redaction.redact("the cat sat on the mat", secrets=["cat"])


# --------------------------------------------------------------------------- #
# Composition -- the boundary applies both                                    #
# --------------------------------------------------------------------------- #


def test_the_boundary_redactor_applies_secrets_and_paths(tmp_path: Path) -> None:
    from seshat.studio import redaction, session

    token = session.generate_bootstrap_token()
    target = tmp_path / "gold" / "fct_sales.sql"
    text = f"token={token} while reading {target}"

    scrubbed = redaction.redact_for_boundary(
        text, secrets=[token], workspace_root=tmp_path
    )

    assert token not in scrubbed
    assert str(tmp_path) not in scrubbed
    assert "gold/fct_sales.sql" in scrubbed


@pytest.mark.parametrize(
    "dsn",
    [
        # No component reaches the length filter: the span replace was already the
        # only thing doing the work here, so this case always passed.
        "postgresql://u:hunter2pass@db.int:5432/app",
        # The regression: an 18-character HOST is replaced by the fragment pass,
        # which mutates the string so the full-match fallback no longer matches --
        # leaving the 11-character password in the clear.
        "postgresql://u:hunter2pass@db.example.invalid:5432/app",
        # Long password AND long host: both cleared even before the fix, which is
        # why the defect stayed invisible.
        "postgresql://u:sixteencharacterpw@db.example.invalid:5432/app",
        # A long DATABASE NAME triggers the same mutation with a short password.
        "postgresql://u:shortpw@db.example.invalid:5432/averylongdbname1",
    ],
)
def test_a_dsn_is_redacted_whole_regardless_of_component_lengths(dsn: str) -> None:
    """Regression: the DSN span must be replaced BEFORE any component fragment.

    `_MINIMUM_SECRET_LENGTH` is the right guard for free-text search, where a short
    fragment would corrupt innocent prose. It is the wrong guard for URI components,
    whose POSITION already proves they are credentials. Replacing long components
    first destroyed the span the full-match fallback needed, so every DSN with one
    long component and a short password leaked that password.

    Proven by reverting the order in `redact_credentials`: these cases go red.
    """
    from seshat.studio import redaction

    scrubbed = redaction.redact_for_boundary(f"connect failed: {dsn}")

    assert "hunter2pass" not in scrubbed
    assert "shortpw" not in scrubbed
    assert "@" not in scrubbed, "a surviving userinfo separator means a partial redact"
    assert "connect failed:" in scrubbed, "redaction destroyed the diagnostic"
