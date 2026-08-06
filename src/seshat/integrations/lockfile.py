"""The integration lock file: what actually landed, recorded exactly once.

`.seshat/integrations/lock.json` is the record of the resolved coordinates that
were installed and validated. Its rules are all about not lying:

* A normal plan may READ it. A normal plan never contacts the network and never
  writes it.
* `--refresh` may resolve fresh versions and still writes NOTHING.
* The lock is written only AFTER an approved installation succeeded and
  validated -- so its content is evidence, not intent.
* The write is a temp file plus an atomic replace, so a failed or interrupted
  write preserves the previous lock byte-for-byte.
* A malformed or unsupported schema fails CLOSED. An unreadable lock is never
  overwritten, and never silently treated as empty.
* No credential, token, connection string, or secret is ever stored.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from seshat.integrations.catalog import LOCK_FILE
from seshat.integrations.resolvers import Resolution

SCHEMA = "seshat.integrations-lock/v1"

# The only keys a component record may carry. An unexpected key is a signal the
# lock was written by something else, and a `token`/`password` key must never be
# admitted -- so the writer projects onto this allowlist rather than dumping
# whatever it was handed.
_COMPONENT_FIELDS = (
    "channel",
    "source_type",
    "source",
    "version",
    "tag",
    "commit",
    "sha256",
    "signature_verified",
    "mode",
)


class LockError(Exception):
    """A lock file that cannot be trusted. Always fatal, never recovered from."""


@dataclass(frozen=True)
class Lock:
    schema: str
    profile: str
    resolved_at: str
    components: dict[str, dict]


def read_lock(root: Path) -> Lock | None:
    """The existing lock, or None when there is none.

    Raises LockError for a lock that exists but cannot be trusted -- unreadable,
    not JSON, not an object, or carrying an unsupported schema. Failing closed
    matters more than proceeding: silently treating a corrupt lock as absent
    would let a re-install claim it had resolved coordinates it never had.
    """
    path = root / LOCK_FILE
    if not path.exists():
        return None
    body = _load_lock_object(path)
    components = body.get("components")
    if not isinstance(components, dict):
        raise LockError(f"lock file 'components' must be an object: {path}")
    return Lock(
        schema=SCHEMA,
        profile=str(body.get("profile") or ""),
        resolved_at=str(body.get("resolved_at") or ""),
        components=components,
    )


def _load_lock_object(path: Path) -> dict:
    """The lock's JSON object, or LockError naming exactly why it is untrustworthy.

    Separated from the field reads above so each refusal -- unreadable, not JSON,
    not an object, wrong schema -- is one line and none can be skipped.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LockError(f"lock file is unreadable: {path} ({exc})") from exc
    try:
        body = json.loads(raw)
    except ValueError as exc:
        raise LockError(f"lock file is not valid JSON: {path}") from exc
    if not isinstance(body, dict):
        raise LockError(f"lock file must be a JSON object: {path}")
    schema = body.get("schema")
    if schema != SCHEMA:
        raise LockError(
            f"unsupported lock schema {schema!r} in {path}; this Seshat "
            f"understands {SCHEMA}"
        )
    return body


def build_lock(
    profile: str,
    resolved_at: str,
    entries: list[tuple[str, str, str, Resolution]],
) -> dict:
    """The lock document for a set of installed components.

    `entries` are `(component_id, source_type, source, resolution)` for the
    components that actually installed. A component that failed is absent
    entirely rather than recorded with a null version -- the lock records what
    landed.
    """
    components: dict[str, dict] = {}
    for component_id, source_type, source, resolved in entries:
        record = {
            "channel": resolved.channel.value if resolved.channel else None,
            "source_type": source_type,
            "source": source,
            "version": resolved.version,
            "tag": resolved.tag,
            "commit": resolved.commit,
            "sha256": resolved.sha256,
            "signature_verified": resolved.signature_verified,
            "mode": None,
        }
        components[component_id] = {key: record.get(key) for key in _COMPONENT_FIELDS}
    return {
        "schema": SCHEMA,
        "profile": profile,
        "resolved_at": resolved_at,
        "components": components,
    }


def write_lock(root: Path, document: dict) -> Path:
    """Write the lock atomically: temp sibling, fsync, then `os.replace`.

    The temp file is a SIBLING of the target, not a file in the system temp
    directory: `os.replace` is only atomic within one filesystem, and a
    cross-device replace silently degrades to a copy -- which is exactly the
    window where a crash would leave a truncated lock. On any failure the temp
    file is removed and the previous lock is left byte-for-byte intact.
    """
    path = root / LOCK_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(document, indent=2, sort_keys=True) + "\n"
    temp_name: str | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".lock-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:  # pragma: no cover - best-effort cleanup
                pass
    return path
