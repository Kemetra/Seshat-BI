"""Installed coordinates versus resolved ones (coordinate-aware presence).

A component can be installed at one coordinate while another is now resolved.
These helpers decide whether that is an UPGRADE, and describe the coordinate
actually on disk for the lock when an install did not land. Extracted from
:mod:`seshat.integrations.installer`, which re-exports them.
"""

from __future__ import annotations

import re
from pathlib import Path

from seshat.integrations.catalog import Component, SourceType
from seshat.integrations.presence import _is_installed, installed_coordinate
from seshat.integrations.resolvers import Resolution
from seshat.integrations.versions import parse_version


def _wanted_coordinates(item: Component, resolved: Resolution) -> set[str]:
    if item.source_type is SourceType.GITHUB and not item.mcp_server:
        return {ref for ref in (resolved.tag, resolved.commit) if ref}
    return {resolved.version} if resolved.version else set()


def _normalised_version(version: str) -> tuple:
    """A comparison key tolerant of PyPI's unnormalised release keys.

    `1.0` and `1.0.0` compare equal, and so do `1.0.0-rc1` and `1.0.0rc1` (the
    dist-info spelling), so a release key's spelling never produces an upgrade
    that can never settle.
    """
    numeric = parse_version(version)
    if numeric is not None:
        trimmed = list(numeric)
        while len(trimmed) > 1 and trimmed[-1] == 0:
            trimmed.pop()
        return ("release", *trimmed)
    return ("other", re.sub(r"[-_.](?=[a-z])", "", version.strip().lower()))


def _matches(item: Component, on_disk: str, wanted: set[str]) -> bool:
    if item.source_type is SourceType.GITHUB and not item.mcp_server:
        return on_disk in wanted
    key = _normalised_version(on_disk)
    return any(_normalised_version(version) == key for version in wanted)


def _upgrade_from(
    root: Path, item: Component, resolved: Resolution, profile: str
) -> str | None:
    """The installed coordinate when it differs from the resolved one, else None."""
    if not _is_installed(root, item, profile):
        return None
    on_disk = installed_coordinate(root, item, profile)
    wanted = _wanted_coordinates(item, resolved)
    if on_disk and wanted and not _matches(item, on_disk, wanted):
        return on_disk
    return None


def _on_disk_resolution(
    root: Path, item: Component, resolved: Resolution, profile: str
) -> Resolution | None:
    """What the lock should say for a component whose install did not land.

    The component may still be installed at its PREVIOUS coordinate (a failed
    upgrade); the lock then records that coordinate, with no digest, because the
    lock is evidence of what is on disk, not of what was resolved this run.
    """
    if not _is_installed(root, item, profile):
        return None
    on_disk = installed_coordinate(root, item, profile)
    if on_disk is None:
        return None
    return _disk_resolution(item, resolved, on_disk)


def _disk_resolution(item: Component, resolved: Resolution, on_disk: str) -> Resolution:
    """A digest-free resolution describing the coordinate found on disk."""
    is_ref = item.source_type is SourceType.GITHUB and not item.mcp_server
    is_commit = (
        is_ref
        and len(on_disk) == 40
        and all(char in "0123456789abcdef" for char in on_disk)
    )
    return Resolution(
        component_id=item.id,
        ok=True,
        channel=resolved.channel or item.channel,
        version=None if is_ref else on_disk,
        tag=on_disk if is_ref and not is_commit else None,
        commit=on_disk if is_commit else None,
        status="installed",
    )
