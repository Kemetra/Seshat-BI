"""`.env`-aware environment for live DB connection resolution (issue #340).

`validate` / `drift` / `value-check` resolved the DB connection AND the engine
from `os.environ` only, so a user who put the `ANALYTICS_DB_*` credentials
(including `ANALYTICS_DB_ENGINE`) in the gitignored `.env` -- exactly as the
tool's own error text, `.env.example`, and the README all instruct -- still got
"no database connection configured" or the wrong engine.

``applied_dotenv(root)`` is a context manager that fills the process
environment from ``root/.env`` for the duration of the command body, so EVERY
`os.environ` read inside it -- engine selection (``cli._current_engine``),
driver choice (``_ensure_driver``), and config resolution -- sees the documented
`.env` values. Two invariants, both deliberate:

  - **Real environment variables win over `.env`** (least surprise: an
    explicitly exported var overrides the file), so `.env` only *fills gaps*.
  - **`os.environ` is restored exactly on exit** (including on exception), so
    the mutation is scoped to the command body and never leaks to the rest of
    the process or the test suite.

The `.env` parser is reused from ``seshat.dbt.redaction`` (governed,
dependency-free); no `python-dotenv` dependency is added. A malformed `.env`
raises ``seshat.dbt.redaction.EnvironmentConfigError``, which each CLI command
boundary converts to a clean, per-family exit code (no traceback): exit 1 for
``validate`` / ``drift`` / ``value-check``, exit 2 (preflight refusal) for the
``dagster`` family (issue #348) whose exit codes are a distinct stable API.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar


class ConnectionConfigError(ValueError):
    """A connection VALUE loaded from the environment/`.env` is invalid.

    Distinct from ``dbt.redaction.EnvironmentConfigError`` (a malformed `.env`
    FILE): this is a syntactically valid setting that cannot resolve -- an
    unknown ``ANALYTICS_DB_ENGINE`` (``get_dialect`` raises), or an unparseable
    ``ANALYTICS_DB_PORT`` (``resolve_config`` raises). Commands catch it at their
    boundary and print a clean exit-1 instead of a raw traceback (#340 review).
    """


_T = TypeVar("_T")


def _scrub_connection_values(message: str) -> str:
    """Strip DSN-shaped credentials out of a wrapped resolution error.

    ``ConnectionConfigError``'s text is printed BARE (no ``dialect.redact``) by
    ``validate`` / ``drift`` / ``profile`` at their config-resolution boundary,
    so whatever an upstream ``ValueError`` says reaches the terminal verbatim.
    Today's upstream raisers are benign (``get_dialect`` names an ENGINE;
    the port path names a PORT), but nothing enforced that -- a future
    ``raise ValueError(f"...{dsn}...")`` anywhere under ``resolve_config`` /
    ``resolve_dsn`` would leak a live credential with no code review signal.
    Scrubbing at the wrapper makes the guarantee structural instead of
    conventional; ``test_connection_config_error_never_carries_the_dsn`` pins it.

    Redaction is by SPAN, not by substring fragment (#527, third review wave).
    Fragment replacement produced five separate leaks across three waves, and
    every one was a property of the mechanism rather than of a pattern:

    * a fragment that was never extracted simply survives (the labeled ``dsn=``
      form, the spaced form, backslash escapes);
    * a shorter fragment replaced before a longer one leaves the tail behind
      (``password=<redacted> cr3t'``);
    * a fragment that also occurs OUTSIDE the value gets replaced there too --
      a secret ``'pass word'`` rewrote the KEY into ``<redacted>word=``, and
      ``.env line 12 is not KEY=VALUE`` (which holds no credential at all)
      became ``KEY=<redacted>``.

    So: consume each ``key = value`` pair whole and re-emit ``key=<redacted>``.
    The key is echoed verbatim, so it can never be mangled; the value span is
    consumed atomically, so no tail can survive; and the substitution only fires
    when the key is a libpq CREDENTIAL keyword, so a benign diagnostic is left
    byte-identical instead of being edited on suspicion.
    """
    import re

    from seshat.redaction_core import _LIBPQ_SECRET_KEYS, replace_fragments
    from seshat.redaction_core import uri_components as _uri_components

    # One libpq value: single-quoted, double-quoted, or bare -- each alternative
    # treating `\<char>` as one unit so an escaped quote/space does not terminate
    # the value early (libpq's documented escaping).
    #
    # The BARE alternative admits `;` and `,` (#528): libpq separates keyword/value
    # pairs by WHITESPACE, so punctuation is ordinary value content. Excluding it
    # cut `password=sec;ret` short and leaked the `;ret` tail. It stops only at
    # whitespace, or at punctuation that is immediately followed by another
    # `key=` pair -- so a `;`-separated conninfo (`host=h;password=p`, a real
    # spelling this must keep splitting) still yields two pairs instead of being
    # swallowed into one. Over-consuming a nonstandard punctuation-separated run
    # into a single redaction would be fail-SAFE, but keeping the split preserves
    # the non-secret keys in the diagnostic.
    bare = r"(?:\\.|[^\s;,]|[;,](?![A-Za-z_][A-Za-z0-9_]*\s*=))+"
    value = rf"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|{bare}"
    pair = re.compile(rf"\b([A-Za-z_][A-Za-z0-9_]*)(\s*=\s*)(?:{value})")

    def _redact_pair(match: re.Match[str]) -> str:
        key, sep = match.group(1), match.group(2)
        if key.lower() not in _LIBPQ_SECRET_KEYS:
            return match.group(0)  # not a credential keyword -- leave it alone
        return f"{key}{sep}<redacted>"

    scrubbed = pair.sub(_redact_pair, message)

    # A URI-shaped DSN carries its credentials POSITIONALLY (userinfo before the
    # `@`, i.e. scheme, then `://`, then `user:password@host`) rather than as
    # key=value, so it needs the component decomposer. NOTE: that example is
    # spelled out in words deliberately -- writing it as a literal would match
    # the release inspector's "credential-bearing URL" scanner and block the
    # publish, even though it is only a comment (see the same guard in
    # `scripts/inspect_release_artifacts.py`). Only the
    # matched URI runs are passed -- handing it the WHOLE message (as this did
    # before) made it emit junk fragments like `"'pass` that then replaced text
    # elsewhere.
    uris = re.findall(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s'\"]+", scrubbed)
    if uris:
        scrubbed = replace_fragments(scrubbed, _uri_components(uris), "<redacted>")
    return scrubbed


def as_connection_config(resolve: Callable[[], _T]) -> _T:
    """Run a connection-config resolution, converting a ``ValueError`` from an
    invalid setting into ``ConnectionConfigError``.

    Wrap ONLY the engine/config resolution (``get_dialect`` + ``resolve_config``
    / ``resolve_dsn``) -- never the live-check body -- so a genuine downstream
    ``ValueError`` is not masked.
    """
    try:
        return resolve()
    except ConnectionConfigError:
        raise
    except ValueError as exc:
        raise ConnectionConfigError(_scrub_connection_values(str(exc))) from exc


def _dotenv_overlay(repo_root: Path | str) -> dict[str, str]:
    """The `.env` keys that should FILL gaps in the process env (env wins).

    Empty when no `.env` exists. Raises ``EnvironmentConfigError`` on a
    malformed file (the governed parser's contract).
    """
    from seshat.dbt.redaction import dotenv_values

    dotenv_path = Path(repo_root) / ".env"
    if not dotenv_path.is_file():
        return {}
    return {
        key: value
        for key, value in dotenv_values(dotenv_path).items()
        if key not in os.environ  # real env wins over .env
    }


@contextmanager
def applied_dotenv(repo_root: Path | str) -> Iterator[None]:
    """Apply ``repo_root/.env`` into ``os.environ`` for the block, then restore.

    Real environment variables win over `.env` (only absent keys are filled).
    ``os.environ`` is restored to its exact prior state on exit, including when
    the block raises. A malformed `.env` raises ``EnvironmentConfigError``
    before any mutation.
    """
    overlay = _dotenv_overlay(repo_root)  # may raise EnvironmentConfigError
    applied_keys = tuple(overlay)  # every key here is absent from os.environ
    os.environ.update(overlay)
    try:
        yield
    finally:
        for key in applied_keys:
            os.environ.pop(key, None)


def connection_environment(repo_root: Path | str) -> dict[str, str]:
    """Process env merged with ``repo_root/.env``; env wins, no mutation.

    A pure-dict view of the same overlay ``applied_dotenv`` applies, for callers
    that want a merged mapping without mutating the process (e.g. a resolver
    that takes an explicit env). Missing `.env` returns a copy of the process
    environment; a malformed `.env` raises ``EnvironmentConfigError``.
    """
    env = dict(os.environ)
    env.update(_dotenv_overlay(repo_root))
    return env
