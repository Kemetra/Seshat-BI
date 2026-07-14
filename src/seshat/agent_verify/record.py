"""Assemble, serialize, and (gated) publish a VerifyRecord (spec 129, US4).

Read-only except the one local evidence-record JSON write under
`.seshat-output/`. Reuses the shared containment guard
(`seshat.cli.guards.resolve_local_output`), the shared publication-intent +
disclosure gate (`seshat.cli.guards.require_publication_intent`), and the
shared disclosure scanner (`seshat.disclosure.scan_disclosure`) rather than
inventing a parallel write/publish/disclosure path.
"""

from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from seshat.cli.guards import require_publication_intent, resolve_local_output
from seshat.disclosure import scan_disclosure

from .model import PerCheckResult, VerifyRecord


def tool_version(repo_root: Path | str) -> str:
    """Best-effort tool version read from the repo's pyproject.toml.

    Never fabricated: an unreadable/missing pyproject.toml yields
    ``"unknown"`` rather than a guessed version string.
    """
    path = Path(repo_root) / "pyproject.toml"
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        return str(document["project"]["version"])
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError):
        return "unknown"


def build_record(
    target: str,
    results: Iterable[PerCheckResult],
    *,
    repo_root: Path | str,
    generated_at: str | None = None,
) -> VerifyRecord:
    """Assemble one VerifyRecord from a completed run's per-check results."""
    return VerifyRecord(
        target=target,
        tool_version=tool_version(repo_root),
        generated_at=generated_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        results=tuple(results),
    )


def disclosure_report(record: VerifyRecord) -> dict[str, Any]:
    """Run the shared disclosure scan over the record's rendered document."""
    return scan_disclosure(record.to_document())


def write_record(
    record: VerifyRecord, *, repo_root: Path | str, output: Path | str
) -> Path:
    """Serialize the record as JSON under `.seshat-output/` -- the only
    write this feature performs. Raises ``ValueError`` (the CLI maps this to
    exit 2) if ``output`` is not contained under `.seshat-output/`."""
    target_path = resolve_local_output(repo_root, output)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(record.to_document(), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return target_path


def publish_record(record: VerifyRecord, *, requested: bool) -> dict[str, Any]:
    """The owner-controlled publication seam (FR-022).

    Publication (or external catalog submission) is deliberately NOT
    implemented here (YAGNI: add the seam, not the implementation) -- this
    only enforces the refusal gate: an explicit ``requested=True`` intent
    AND a clean disclosure scan. Raises ``ValueError`` when refused (the CLI
    maps this to exit 2); never publishes automatically and never performs
    any network call.
    """
    disclosure = disclosure_report(record)
    require_publication_intent(
        requested=requested, disclosure_status=disclosure["status"]
    )
    return {"status": "publish_intent_confirmed", "disclosure": disclosure}
