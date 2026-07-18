"""Shell-free dbt invocation boundary with a bounded cross-process lock."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sysconfig
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_hex

from seshat.dbt.contracts import InvocationResult, Operation, RunContext
from seshat.dbt.redaction import sanitize, secret_values

_SAFE_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
_LIST_UNIQUE_ID = re.compile(r"^(model|test)\.seshat_bi\.[A-Za-z0-9_.-]+$")
_OPERATION_COMMAND = {
    Operation.PARSE: "parse",
    Operation.LIST: "ls",
    Operation.BUILD: "build",
    Operation.TEST: "test",
    Operation.SHOW: "show",
}


class DbtUnavailable(RuntimeError):
    """The controlled dbt process cannot be launched or complete in bounds."""


class LockUnavailable(RuntimeError):
    """The table/target artifact boundary is already owned or unsafe."""


def resolve_dbt_executable(scripts_dir: Path | None = None) -> Path:
    """Resolve dbt only from the current Python environment's scripts path."""

    configured = scripts_dir or Path(sysconfig.get_path("scripts"))
    root = configured.resolve(strict=False)
    for name in ("dbt.exe", "dbt"):
        candidate = root / name
        if not candidate.is_file():
            continue
        resolved = candidate.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError:
            continue
        return resolved
    raise DbtUnavailable(
        "dbt is unavailable in the current Python environment; install '.[dbt]'"
    )


def _validate_context(context: RunContext) -> None:
    expected_selector = f"seshat_table_{context.table_id}"
    checks = (
        (
            _SAFE_IDENTIFIER.fullmatch(context.table_id) is not None,
            "table ID is not a safe governed identifier",
        ),
        (
            context.selector == expected_selector,
            "dbt selector does not match the governed table",
        ),
        (context.target == "shadow", "dbt target must be the fixed shadow target"),
        (context.timeout_s > 0, "dbt timeout must be positive"),
    )
    message = next((message for valid, message in checks if not valid), None)
    if message is not None:
        raise DbtUnavailable(message)


def build_dbt_argv(operation: Operation, context: RunContext) -> tuple[str, ...]:
    """Build the closed, governed argv for one supported dbt operation."""

    _validate_context(context)
    try:
        command = _OPERATION_COMMAND[operation]
    except KeyError as exc:
        raise DbtUnavailable("unsupported dbt operation") from exc

    log_format = "text" if operation is Operation.LIST else "json"
    argv = [str(resolve_dbt_executable())]
    if operation is Operation.LIST:
        argv.append("--quiet")
    argv.append(command)
    if operation is Operation.SHOW:
        argv.extend(("--select", f"audit_{context.table_id}_parity"))
    elif operation is not Operation.PARSE:
        argv.extend(("--select", f"selector:{context.selector}"))
    argv.extend(
        (
            "--target",
            context.target,
            "--profiles-dir",
            str(context.profiles_dir),
            "--project-dir",
            str(context.project_dir),
            "--target-path",
            str(context.run_dir / "target"),
            "--log-path",
            str(context.run_dir / "logs"),
            "--no-use-colors",
            "--log-format",
            log_format,
        )
    )
    if operation is Operation.SHOW:
        # --limit caps dbt show's preview rows; its default (5) silently truncates
        # a parity audit with more assertions, so the evidence layer would see an
        # incomplete set. A high explicit cap returns every governed assertion row
        # (a governed star has far fewer than this many parity assertions).
        argv.extend(("--output", "json", "--limit", "1000"))
    elif operation is Operation.LIST:
        argv.extend(("--output", "json", "--output-keys", "unique_id"))
    return tuple(argv)


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _sanitized_text(value: object, context: RunContext) -> str:
    cleaned = sanitize(
        value or "", secret_values(context.environment), context.repo_root
    )
    return str(cleaned)


def _argv_summary(argv: tuple[str, ...], context: RunContext) -> tuple[str, ...]:
    cleaned = sanitize(argv[1:], secret_values(context.environment), context.repo_root)
    if not isinstance(cleaned, tuple):
        raise DbtUnavailable("dbt argv could not be normalized safely")
    return tuple(str(part) for part in cleaned)


def _list_unique_id(line: str) -> str:
    try:
        row = json.loads(line)
    except json.JSONDecodeError as exc:
        raise DbtUnavailable("dbt list output is not allowlisted JSON rows") from exc
    unique_id = row.get("unique_id") if isinstance(row, dict) else None
    if not isinstance(unique_id, str) or not _LIST_UNIQUE_ID.fullmatch(unique_id):
        raise DbtUnavailable("dbt list output is not allowlisted JSON rows")
    return unique_id


def _list_stdout(stdout: str) -> str:
    rows = (
        json.dumps({"unique_id": _list_unique_id(line)}, sort_keys=True)
        for line in stdout.splitlines()
        if line.strip()
    )
    return "\n".join(rows)


def _normalized_stdout(stdout: str, context: RunContext) -> str:
    if context.operation is Operation.LIST:
        return _list_stdout(stdout)
    return _sanitized_text(stdout, context)


def invoke_dbt(context: RunContext, argv: tuple[str, ...]) -> InvocationResult:
    """Invoke dbt without a shell and return only sanitized process output."""

    _validate_context(context)
    if argv != build_dbt_argv(context.operation, context):
        raise DbtUnavailable("dbt argv does not match the governed argument set")
    target_dir = context.run_dir / "target"
    log_dir = context.run_dir / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    started_at = _timestamp()
    try:
        completed = subprocess.run(
            argv,
            cwd=context.project_dir,
            env=context.environment,
            capture_output=True,
            text=True,
            timeout=context.timeout_s,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise DbtUnavailable(
            f"dbt command timed out after {context.timeout_s:g} seconds"
        ) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        detail = _sanitized_text(exc, context)
        raise DbtUnavailable(f"dbt process could not run: {detail}") from exc
    completed_at = _timestamp()
    return InvocationResult(
        invocation_id=context.run_dir.name,
        operation=context.operation,
        argv_summary=_argv_summary(argv, context),
        return_code=completed.returncode,
        started_at=started_at,
        completed_at=completed_at,
        stdout=_normalized_stdout(completed.stdout, context),
        stderr=_sanitized_text(completed.stderr, context),
        target_dir=target_dir,
        log_dir=log_dir,
    )


def _lock_path(repo_root: Path, table_id: str, target: str) -> Path:
    if not _SAFE_IDENTIFIER.fullmatch(table_id) or not _SAFE_IDENTIFIER.fullmatch(
        target
    ):
        raise LockUnavailable("lock keys must be safe identifiers")
    return repo_root / ".seshat" / "dbt" / "locks" / f"{table_id}-{target}.lock"


def _try_acquire_lock(path: Path) -> int | None:
    try:
        return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return None


def _acquire_lock(path: Path, table_id: str, target: str, timeout_s: float) -> int:
    deadline = time.monotonic() + min(max(timeout_s, 0.0), 1.0)
    while (descriptor := _try_acquire_lock(path)) is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LockUnavailable(
                f"dbt invocation already in progress for {table_id}/{target}"
            )
        time.sleep(min(0.05, remaining))
    return descriptor


def _lock_payload(table_id: str, target: str) -> bytes:
    metadata = {
        "acquired_at": _timestamp(),
        "owner_token": token_hex(16),
        "pid": os.getpid(),
        "table_id": table_id,
        "target": target,
    }
    return json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()


def _unlink_lock(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _write_lock(path: Path, descriptor: int, payload: bytes) -> None:
    try:
        os.write(descriptor, payload)
    except OSError as exc:
        _unlink_lock(path)
        raise LockUnavailable("dbt lock metadata could not be written") from exc
    finally:
        os.close(descriptor)


def _create_lock(
    repo_root: Path, table_id: str, target: str, timeout_s: float
) -> tuple[Path, bytes]:
    path = _lock_path(repo_root, table_id, target)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _lock_payload(table_id, target)
    _write_lock(path, _acquire_lock(path, table_id, target, timeout_s), payload)
    return path, payload


def _release_lock(path: Path, payload: bytes) -> None:
    try:
        current = path.read_bytes()
    except OSError:
        return
    if current == payload:
        _unlink_lock(path)


@contextmanager
def target_lock(
    repo_root: Path, table_id: str, target: str, timeout_s: float = 1.0
) -> Iterator[Path]:
    """Own one table/target artifact boundary for at most the body duration."""

    path, payload = _create_lock(repo_root, table_id, target, timeout_s)
    try:
        yield path
    finally:
        _release_lock(path, payload)
