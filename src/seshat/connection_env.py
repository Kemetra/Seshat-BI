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
        raise ConnectionConfigError(str(exc)) from exc


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
