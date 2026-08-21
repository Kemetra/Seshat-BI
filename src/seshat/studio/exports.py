"""Export assembly and scrubbing -- the disclosure boundary (spec 141).

Every artifact leaving Studio passes through here, which is why this module stays small:
the whole disclosure path should be auditable in one read.

Three failure modes, each with its own structural guard:

- **Softening**: `build_narrative` labels pending items as pending and never emits an
  approval word for them (FR-141-022).
- **Leaking**: `scrub_for_export` takes a REQUIRED allowlist. There is no
  "scrub everything except" entry point, because a denylist fails open on the field
  nobody enumerated (FR-141-012).
- **Acting**: nothing here mutates a decision. `ClientAcknowledgment` has no answer
  field, so an acknowledgement cannot become a ruling (FR-141-011).
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from seshat.studio import redaction

#: Files a support bundle may contain. An ALLOWLIST: `.env`, data extracts and
#: credential stores are absent because they are not named here, not because a
#: filter removed them.
#: Structural exclusion (FR-141-013).
BUNDLE_ALLOWED_FILES: tuple[str, ...] = (
    "readiness-status.yaml",
    "source-map.yaml",
    "manifest.yaml",
)

#: Fields a support bundle manifest may carry.
BUNDLE_ALLOWED_FIELDS: tuple[str, ...] = (
    "seshat_version",
    "python_version",
    "platform",
    "component_states",
)

_MANIFEST_NAME = "manifest.json"


class ScanFailed(Exception):
    """The staged content still contained something the redaction corpus flagged.

    Raised instead of finalizing. A partially scrubbed archive is worse than none,
    because whoever receives it assumes it was scrubbed (FR-141-014).
    """


@dataclass(frozen=True, slots=True)
class ClientAcknowledgment:
    """A client's acknowledgement that they saw a result.

    Deliberately carries NO answer, approval, decision, signer or authority field. An
    acknowledgement is not a ruling, and making it structurally incapable of holding one
    stops the two collapsing under UI pressure (FR-141-011). A scoped business answer
    goes through spec 140's `POST /decisions/record`.
    """

    scope: str
    acknowledged_by: str
    acknowledged_at: str
    run_id: str | None = None

    def as_dict(self) -> dict:
        return {
            "scope": self.scope,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "run_id": self.run_id,
        }


@dataclass(frozen=True, slots=True)
class ClientFeedbackItem:
    """A clarification a client asked for, routed to the analyst workflow."""

    scope: str
    question: str
    raised_by: str
    raised_at: str


def scrub_for_export(
    payload: dict[str, Any], *, allowed: tuple[str, ...], workspace_root: Path
) -> dict[str, Any]:
    """Keep only allowlisted fields, then scrub what remains.

    Two steps, both required. Allowlisting a FIELD does not bless its CONTENT: a note an
    analyst wrote may still contain a DSN, so surviving values go through the shipped
    redaction layers (FR-141-008).

    `allowed` is keyword-only and has NO default. A default allowlist is a default
    disclosure, so omitting it is a TypeError rather than a quiet pass-through.
    """
    narrowed = {key: value for key, value in payload.items() if key in allowed}
    return redaction.scrub_payload(narrowed, workspace_root=workspace_root)


def build_narrative(
    *, selected_facts: tuple[str, ...], pending_items: tuple[str, ...]
) -> str:
    """Compose a client narrative from the selection and nothing else.

    Every sentence comes from a supplied string. Nothing is inferred, summarized or
    graded, so the narrative cannot introduce a claim the analyst did not select
    (FR-141-022).

    Pending items get their own labelled section rather than being folded in, because a
    reader skimming prose will otherwise take everything as settled.
    """
    sections: list[str] = []
    if selected_facts:
        sections.append("Confirmed:")
        sections.extend(f"- {fact}" for fact in selected_facts)
    if pending_items:
        sections.append("Still pending -- not yet decided:")
        sections.extend(f"- {item}" for item in pending_items)
    if not sections:
        # No selection means no claims. Emitting "everything is fine" here would be the
        # softening failure in its purest form.
        return "Nothing has been selected for review yet."
    return "\n".join(sections)


def _manifest_for(root: Path, staged: list[Path]) -> dict[str, Any]:
    """The manifest: what was included, and proof of what each file held."""
    return {
        "allowlisted_fields": list(BUNDLE_ALLOWED_FIELDS),
        "allowlisted_files": list(BUNDLE_ALLOWED_FILES),
        "included_files": [p.name for p in staged],
        "file_hashes": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in staged
        },
        "redaction_scan": "passed",
    }


def _scan_staged(root: Path, staged: list[Path]) -> None:
    """Scan staged content with the shipped redaction corpus before finalizing.

    Raises `ScanFailed` rather than returning a verdict, so a caller cannot proceed by
    ignoring a return value.
    """
    for path in staged:
        text = path.read_text(encoding="utf-8", errors="ignore")
        scrubbed = redaction.redact_paths(
            redaction.redact_credentials(text), workspace_root=root
        )
        if scrubbed != text:
            raise ScanFailed(f"{path.name} still contained redactable content")


def _stage_allowlisted(root: Path, staging: Path) -> list[Path]:
    """Copy allowlisted files into staging, scrubbed.

    Only names in `BUNDLE_ALLOWED_FILES` are considered. `.env` is never a candidate --
    it is not on the list, so its exclusion needs no filter and cannot be forgotten.
    """
    staged: list[Path] = []
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file() or candidate.name not in BUNDLE_ALLOWED_FILES:
            continue
        text = candidate.read_text(encoding="utf-8", errors="ignore")
        cleaned = redaction.redact_paths(
            redaction.redact_credentials(text), workspace_root=root
        )
        target = staging / candidate.name
        target.write_text(cleaned, encoding="utf-8")
        staged.append(target)
    return staged


def build_support_bundle(root: Path, *, destination: Path) -> Path:
    """Assemble a support bundle atomically, aborting if the scan fails.

    Order is the contract: stage -> scan -> finalize. The archive is written to a
    temporary path and moved into place only after the scan passes, so a failure leaves
    no artifact at all rather than a half-scrubbed one (FR-141-014).
    """
    root = Path(root)
    with tempfile.TemporaryDirectory(dir=root) as staging_dir:
        staging = Path(staging_dir)
        staged = _stage_allowlisted(root, staging)
        _scan_staged(root, staged)

        manifest = _manifest_for(root, staged)
        handle_fd, temporary = tempfile.mkstemp(dir=root, suffix=".tmp")
        os.close(handle_fd)
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(_MANIFEST_NAME, json.dumps(manifest, indent=2))
                for path in staged:
                    archive.write(path, arcname=path.name)
            os.replace(temporary, destination)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
    return destination


def read_manifest(bundle: Path) -> dict[str, Any]:
    """The manifest inside a built bundle."""
    with zipfile.ZipFile(bundle) as archive:
        return json.loads(archive.read(_MANIFEST_NAME).decode("utf-8"))
