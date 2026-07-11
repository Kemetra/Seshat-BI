"""Shared containment and explicit-publication guards for generated output."""

from __future__ import annotations

from pathlib import Path

from seshat.artifact_identity import resolve_within


def resolve_local_output(
    workspace_root: Path | str,
    output: Path | str,
    *,
    output_root: str = ".seshat-output",
) -> Path:
    workspace = Path(workspace_root).resolve()
    allowed = resolve_within(workspace, output_root)
    target = resolve_within(workspace, output)
    if not target.is_relative_to(allowed):
        raise ValueError(f"output must stay under {output_root}/")
    return target


def require_publication_intent(*, requested: bool, disclosure_status: str) -> None:
    if not requested:
        raise ValueError("publication requires an explicit user action")
    if disclosure_status != "pass":
        raise ValueError("publication is blocked by disclosure findings")
