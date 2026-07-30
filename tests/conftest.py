"""Session-wide test environment guards.

Kept deliberately free of ``seshat`` imports: several tests assert that importing the
package does not pull heavy or lazy modules, and a conftest import would run before
them and invalidate the assertion.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

_HERMETIC_GITCONFIG = """\
[user]
\tname = Seshat Test
\temail = test@example.invalid
[commit]
\tgpgsign = false
[tag]
\tgpgsign = false
[init]
\tdefaultBranch = main
[protocol "file"]
\tallow = always
"""


@pytest.fixture(scope="session", autouse=True)
def hermetic_git_config(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Path]:
    """Point git at throwaway config files for the whole test session.

    Tests that build a temp repo and commit into it must not inherit the developer's
    global config: a machine with ``commit.gpgsign=true`` and an ssh signer cannot sign
    from a non-interactive subprocess, so ``git commit`` exits 128 and the test fails
    for reasons unrelated to the code under test. CI configures no signing and so never
    reproduces it.

    Redirects the GLOBAL layer only, and restores the previous value on teardown. The
    developer's real config file is never read or written.

    ``GIT_CONFIG_SYSTEM`` is deliberately left alone. On Windows the Git-for-Windows
    installer writes ``core.autocrlf = true`` into the system config
    (``C:/Program Files/Git/etc/gitconfig``), and blanking that layer changes how
    ``git add`` normalizes line endings -- which changes committed blob SHAs and breaks
    every test that compares a cited contract revision against the blob git actually
    stores. Redirecting only the global layer still neutralizes signing: config
    precedence is system < global < local, so the ``gpgsign = false`` below wins even
    against a system-level ``gpgsign = true``.
    """
    root = tmp_path_factory.mktemp("gitconfig")
    global_config = root / "gitconfig"
    global_config.write_text(_HERMETIC_GITCONFIG, encoding="utf-8")

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
        yield global_config
