"""Packaged frontend asset location and its absence diagnostic (FR-005).

The React/TypeScript frontend ships PREBUILT inside the wheel so end users need no
Node.js. A wheel built without that step must say so plainly -- serving a blank page
would present a build defect as an empty workspace.

Import-light by contract: standard library only.
"""

from __future__ import annotations

from pathlib import Path

#: Directory name of the packaged build output, relative to this package.
STATIC_DIRECTORY_NAME = "static"

#: The file a complete build always produces.
INDEX_FILENAME = "index.html"


def packaged_static_directory() -> Path:
    """Where the prebuilt frontend lives in an installed layout."""
    return Path(__file__).resolve().parent / STATIC_DIRECTORY_NAME


def describe_missing_assets(directory: Path) -> str | None:
    """Return a named diagnostic if ``directory`` holds no usable build, else None.

    Returns a string rather than raising: a missing frontend is a reported state
    with a recovery action, and the launcher decides how to present it.
    """
    if not directory.is_dir():
        return (
            f"Studio frontend assets are missing: {directory} does not exist. "
            "This wheel was built without the frontend build step. Rebuild with "
            "the documented Studio build command, or reinstall a wheel that "
            "includes the prebuilt assets."
        )
    if not (directory / INDEX_FILENAME).is_file():
        return (
            f"Studio frontend assets are incomplete: {directory} exists but "
            f"{INDEX_FILENAME} is absent. Rebuild the Studio frontend with the "
            "documented build command."
        )
    return None
