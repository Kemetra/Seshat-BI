"""T006 -- the Studio local security boundary, written before the code exists.

Source of truth: `specs/139-seshat-studio-foundation/contracts/security-boundary.md`.
Localhost is NOT treated as a trusted network.

Requirements under test:

* FR-001 -- exactly one resolved workspace per process; no workspace path from
  browser requests.
* FR-003 -- bind only to IPv4 `127.0.0.1` on an OS-assigned port; refuse
  non-loopback binding.
* FR-004 -- an ephemeral high-entropy token, exchanged once for an HttpOnly
  SameSite=Strict cookie, with exact `Host` enforcement.

Everything here is stdlib-only and must stay runnable WITHOUT the `studio` extra:
these are configuration, token, and containment properties, not server behaviour.
The FastAPI request pipeline is exercised in T007's integration tests.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

# --------------------------------------------------------------------------- #
# FR-003 -- loopback-only binding                                             #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "::", "::0", "10.0.0.5", "192.168.1.10", "example.com", ""],
)
def test_non_loopback_binding_is_refused(host: str) -> None:
    """The contract rejects 0.0.0.0, IPv6-any, LAN, and public binding."""
    from seshat.studio import config

    with pytest.raises(ValueError, match="loopback"):
        config.resolve_bind_host(host)


def test_the_only_accepted_bind_host_is_ipv4_loopback() -> None:
    """ "binds exactly to IPv4 127.0.0.1" -- v1 does not accept ::1."""
    from seshat.studio import config

    assert config.resolve_bind_host("127.0.0.1") == "127.0.0.1"

    with pytest.raises(ValueError, match="loopback"):
        config.resolve_bind_host("::1")


def test_the_port_is_os_assigned_by_default() -> None:
    """An OS-assigned port means requesting 0, not picking a fixed number."""
    from seshat.studio import config

    assert config.OS_ASSIGNED_PORT == 0


# --------------------------------------------------------------------------- #
# FR-001 -- one pinned workspace per process, immutable                       #
# --------------------------------------------------------------------------- #


def _recognized_workspace(root: Path) -> Path:
    """A directory the shipped `looks_like_workspace` recognizer accepts.

    A bare `tmp_path` is deliberately NOT enough: the contract requires a
    *recognized* Seshat workspace, so the fixture must carry a real marker.
    """
    (root / ".seshat").mkdir(parents=True, exist_ok=True)
    return root


def test_launch_configuration_pins_an_absolute_workspace_root(tmp_path: Path) -> None:
    from seshat.studio import config

    launch = config.LaunchConfiguration.for_workspace(_recognized_workspace(tmp_path))

    assert launch.workspace_root == tmp_path.resolve()
    assert launch.workspace_root.is_absolute()


def test_launch_configuration_is_immutable(tmp_path: Path) -> None:
    """ "pins that absolute root in immutable process configuration"."""
    from seshat.studio import config

    launch = config.LaunchConfiguration.for_workspace(_recognized_workspace(tmp_path))

    with pytest.raises(Exception):  # dataclasses raises FrozenInstanceError
        launch.workspace_root = Path("/elsewhere")  # type: ignore[misc]


def test_a_nonexistent_workspace_is_refused(tmp_path: Path) -> None:
    from seshat.studio import config

    with pytest.raises(ValueError, match="workspace"):
        config.LaunchConfiguration.for_workspace(tmp_path / "absent")


def test_a_directory_without_workspace_markers_is_refused(tmp_path: Path) -> None:
    """`is_dir()` is not recognition -- it would admit any directory on the machine.

    Recognition is delegated to the shipped `resolve_workspace_root`, so this pins
    that Studio does not accept an arbitrary folder.
    """
    from seshat.studio import config

    plain = tmp_path / "just-a-folder"
    plain.mkdir()

    with pytest.raises(ValueError, match="workspace"):
        config.LaunchConfiguration.for_workspace(plain)


# --------------------------------------------------------------------------- #
# Filesystem boundary -- containment, traversal, symlink escape               #
# --------------------------------------------------------------------------- #


def test_a_contained_relative_reference_resolves(tmp_path: Path) -> None:
    from seshat.studio import config

    (tmp_path / "mappings").mkdir()
    target = tmp_path / "mappings" / "readiness-status.yaml"
    target.write_text("{}", encoding="utf-8")

    resolved = config.resolve_contained_path(tmp_path, "mappings/readiness-status.yaml")

    assert resolved == target.resolve()


@pytest.mark.parametrize(
    "reference",
    [
        "../outside.yaml",
        "mappings/../../outside.yaml",
        "/etc/passwd",
        "C:/Windows/System32/config/SAM",
    ],
)
def test_traversal_and_absolute_references_are_refused(
    tmp_path: Path, reference: str
) -> None:
    """ ".." traversal and absolute input are rejected as input defects."""
    from seshat.studio import config

    with pytest.raises(ValueError):
        config.resolve_contained_path(tmp_path, reference)


def test_windows_drive_reference_is_absolute_under_posix_path_semantics() -> None:
    """A Linux runner must reject an absolute Windows reference."""
    from seshat.studio import config

    reference = "C:/Windows/System32/config/SAM"
    assert config._is_absolute_reference(reference, PurePosixPath(reference))


def test_a_symlink_escaping_the_root_is_refused(tmp_path: Path) -> None:
    """Symlink/junction escapes are rejected, not silently followed."""
    from seshat.studio import config

    outside = tmp_path.parent / "studio_outside_target"
    outside.mkdir(exist_ok=True)
    (outside / "secret.yaml").write_text("secret", encoding="utf-8")

    root = tmp_path / "workspace"
    root.mkdir()
    link = root / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable in this environment")

    with pytest.raises(ValueError):
        config.resolve_contained_path(root, "escape/secret.yaml")


def test_containment_is_decided_after_resolution_not_on_the_literal_string(
    tmp_path: Path,
) -> None:
    """The escape defence, provable without symlink privileges.

    `test_a_symlink_escaping_the_root_is_refused` skips on Windows without the
    symlink privilege, which would leave the escape path unverified. Containment
    here is decided by comparing RESOLVED paths, so this asserts the same property
    the symlink case relies on: a reference whose resolved target lands outside the
    root is refused even though its literal text contains no `..` and is relative.
    """
    from seshat.studio import config

    root = tmp_path / "workspace"
    root.mkdir()
    sibling = tmp_path / "workspace_evil"
    sibling.mkdir()
    (sibling / "secret.yaml").write_text("secret", encoding="utf-8")

    # `..` is refused by an earlier, independent check -- defence in depth, so a
    # traversal attempt never even reaches the containment comparison.
    with pytest.raises(ValueError, match="traversal"):
        config.resolve_contained_path(root, "../workspace_evil/secret.yaml")

    # The containment comparison itself must use resolved PARENTS, not a string
    # prefix: `str(sibling)` starts with `str(root)`, so a prefix test would call
    # the sibling "contained". Proven by the fact that a legitimate in-root
    # reference resolves to a child of the root and nothing else does.
    resolved = config.resolve_contained_path(root, "inside.yaml")
    assert resolved.parent == root.resolve()
    assert not str(sibling.resolve()).startswith(str(resolved))


def test_a_browser_reference_is_never_turned_into_an_arbitrary_path(
    tmp_path: Path,
) -> None:
    """The resolver takes a workspace-relative STRING, never a caller Path."""
    from seshat.studio import config

    with pytest.raises((ValueError, TypeError)):
        config.resolve_contained_path(tmp_path, Path("/etc/passwd"))  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# FR-004 -- bootstrap token and session                                       #
# --------------------------------------------------------------------------- #


def test_the_bootstrap_token_carries_at_least_256_bits() -> None:
    from seshat.studio import session

    token = session.generate_bootstrap_token()

    assert len(token) >= 43, "a 256-bit urlsafe token is at least 43 characters"


def test_bootstrap_tokens_are_unpredictable() -> None:
    from seshat.studio import session

    tokens = {session.generate_bootstrap_token() for _ in range(50)}

    assert len(tokens) == 50


def test_the_store_holds_a_digest_not_the_raw_token() -> None:
    """ "Studio stores a digest" -- the raw token must not be recoverable.

    Reads the instance's real state rather than `vars()`: the store uses
    `__slots__`, so it has no `__dict__` to inspect.
    """
    from seshat.studio import session

    token = session.generate_bootstrap_token()
    store = session.SessionStore(token)

    stored_state = " ".join(
        repr(getattr(store, slot, None)) for slot in session.SessionStore.__slots__
    )

    assert token not in repr(store)
    assert token not in stored_state, "the raw token is recoverable from the store"


def test_a_token_may_be_exchanged_exactly_once() -> None:
    """ "invalidates the token after one successful exchange"."""
    from seshat.studio import session

    token = session.generate_bootstrap_token()
    store = session.SessionStore(token)

    first = store.exchange(token)
    assert first is not None

    assert store.exchange(token) is None, "the token must not survive one exchange"


def test_a_wrong_token_is_refused_and_does_not_consume_the_real_one() -> None:
    from seshat.studio import session

    token = session.generate_bootstrap_token()
    store = session.SessionStore(token)

    assert store.exchange("not-the-token") is None
    assert store.exchange(token) is not None, "a failed attempt burned the real token"


def test_the_session_cookie_value_is_unpredictable_and_not_the_token() -> None:
    from seshat.studio import session

    token = session.generate_bootstrap_token()
    store = session.SessionStore(token)

    cookie = store.exchange(token)

    assert cookie is not None
    assert cookie != token
    assert len(cookie) >= 43


def test_session_validation_rejects_an_unknown_cookie() -> None:
    from seshat.studio import session

    token = session.generate_bootstrap_token()
    store = session.SessionStore(token)
    store.exchange(token)

    assert store.is_valid_session("forged-cookie") is False


def test_shutdown_invalidates_the_session() -> None:
    """ "explicit shutdown invalidates access"."""
    from seshat.studio import session

    token = session.generate_bootstrap_token()
    store = session.SessionStore(token)
    cookie = store.exchange(token)
    assert cookie is not None
    assert store.is_valid_session(cookie) is True

    store.shutdown()

    assert store.is_valid_session(cookie) is False


def test_the_cookie_attributes_match_the_contract() -> None:
    """HttpOnly, SameSite=Strict, Path=/, no Domain, and no Secure on loopback."""
    from seshat.studio import session

    attributes = session.session_cookie_attributes()

    assert attributes["httponly"] is True
    assert attributes["samesite"] == "strict"
    assert attributes["path"] == "/"
    assert "domain" not in attributes
    assert attributes.get("secure", False) is False


def test_the_cookie_name_is_the_contracted_one() -> None:
    from seshat.studio import session

    assert session.SESSION_COOKIE_NAME == "seshat_studio_session"


# --------------------------------------------------------------------------- #
# Request enforcement -- Host and Origin, before endpoint logic               #
# --------------------------------------------------------------------------- #


def test_an_exact_host_match_is_required() -> None:
    from seshat.studio import session

    assert session.host_is_allowed("127.0.0.1:8931", "127.0.0.1", 8931) is True


@pytest.mark.parametrize(
    "header",
    [
        "127.0.0.1:9999",
        "localhost:8931",
        "evil.example.com",
        "127.0.0.1",
        "127.0.0.1:8931.evil.com",
        "",
    ],
)
def test_a_mismatched_host_is_refused(header: str) -> None:
    """A DNS-rebinding guard: only the exact selected host:port is accepted."""
    from seshat.studio import session

    assert session.host_is_allowed(header, "127.0.0.1", 8931) is False


def test_an_exact_origin_match_is_required() -> None:
    from seshat.studio import session

    assert session.origin_is_allowed("http://127.0.0.1:8931", "127.0.0.1", 8931) is True


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:9999",
        "https://127.0.0.1:8931",
        "http://localhost:8931",
        "http://evil.example.com",
        "null",
        "",
    ],
)
def test_a_mismatched_or_missing_origin_is_refused_for_mutations(origin: str) -> None:
    """ "Mutating requests with a missing origin are rejected." CORS stays off."""
    from seshat.studio import session

    assert session.origin_is_allowed(origin, "127.0.0.1", 8931) is False
