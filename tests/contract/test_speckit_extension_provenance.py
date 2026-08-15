"""Fail-closed provenance contract for the vendored Spec Kit extensions (issue #603).

`test_speckit_provenance.py` pins the fourteen Claude *skills*. This pins the
*generator* that produces five of them, plus the workflow/registry files -- the gap
that closure explicitly did not claim: drift in the thing that makes a verified
artifact stayed undetectable while the artifact itself verified.

Two properties here are not shared with the skill contract:

1. **Hashes are of the git BLOB, not the working tree.** The extension surface spans
   three `.gitattributes` classes (`eol=lf`, `eol=crlf`, unspecified `text=auto`), so a
   working-tree hash of a `.ps1` differs between a Windows checkout and `ubuntu-latest`.
   That is the PLATFORM-BRANCH vacuity that makes a gate green on one OS and red on the
   other. Blob hashing is platform-independent by construction, and it is also what the
   two upstream manifests were already doing -- verified, all 24 entries.

2. **The pinned set is swept, not enumerated.** A file ADDED by a re-vendor must fail,
   not slip through unpinned, so the manifest is compared against `git ls-files` rather
   than trusted as a list.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST = Path(".specify/integrations/extensions.manifest.json")
_SPECKIT_MANIFEST = Path(".specify/integrations/speckit.manifest.json")
_CLAUDE_MANIFEST = Path(".specify/integrations/claude.manifest.json")

#: The inventory issue #603 enumerates: 18 under `.specify/extensions/`, plus
#: `extensions.yml`, `integration.json`, and the two `workflows/` files. Pinned as a
#: COUNT so that dropping a root from `PINNED_ROOTS` and regenerating cannot shrink
#: both sides in lockstep and still read clean -- the same lockstep-shrink defence the
#: skill contract applies to its fourteen.
_EXPECTED_PINNED_COUNT = 22


def _load_pinner():  # type: ignore[no-untyped-def]
    """Import the generator by path; `scripts/` is not an installed package."""
    path = _REPO_ROOT / "scripts" / "pin_speckit_extensions.py"
    spec = importlib.util.spec_from_file_location("pin_speckit_extensions", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extension_manifest_has_no_drift() -> None:
    """The real repository's pinned extension surface is intact."""
    assert _load_pinner().verify(_REPO_ROOT) == []


def test_extension_manifest_pins_the_full_inventory() -> None:
    """Twenty-two files, not merely a non-empty set."""
    declared = json.loads((_REPO_ROOT / _MANIFEST).read_text(encoding="utf-8"))

    assert len(declared["files"]) == _EXPECTED_PINNED_COUNT


def test_every_tracked_extension_file_is_pinned() -> None:
    """Sweep, don't trust the list: an added file must be caught, not ignored."""
    pinner = _load_pinner()
    declared = json.loads((_REPO_ROOT / _MANIFEST).read_text(encoding="utf-8"))

    assert set(pinner.pinned_paths(_REPO_ROOT)) == set(declared["files"])


def test_the_five_git_command_sources_are_pinned() -> None:
    """The specific gap #603 names: sources of the five pinned `speckit-git-*` skills.

    Named individually rather than left to the count above, because these are the
    files whose drift KF-2's closure could not see.
    """
    declared = json.loads((_REPO_ROOT / _MANIFEST).read_text(encoding="utf-8"))

    for command in ("commit", "feature", "initialize", "remote", "validate"):
        path = f".specify/extensions/git/commands/speckit.git.{command}.md"
        assert path in declared["files"], path


def test_executable_scripts_are_pinned() -> None:
    """Bash and PowerShell carry more drift risk than prose, so pin them explicitly."""
    declared = json.loads((_REPO_ROOT / _MANIFEST).read_text(encoding="utf-8"))
    scripts = [path for path in declared["files"] if path.endswith((".sh", ".ps1"))]

    assert len(scripts) == 8, scripts


@pytest.mark.parametrize("manifest", [_CLAUDE_MANIFEST, _SPECKIT_MANIFEST, _MANIFEST])
def test_blob_hashing_reproduces_every_pinned_manifest(manifest: Path) -> None:
    """One convention verifies all three manifests -- the evidence for choosing it.

    This is the load-bearing claim. If a future change adopts working-tree hashing for
    any manifest, this fails on the `.ps1` entries, which is the intended alarm: those
    are exactly the files whose checkout bytes differ per platform.
    """
    pinner = _load_pinner()
    declared = json.loads((_REPO_ROOT / manifest).read_text(encoding="utf-8"))

    mismatched = [
        path
        for path, digest in declared["files"].items()
        if pinner.blob_sha256(path, root=_REPO_ROOT) != digest
    ]

    assert mismatched == [], mismatched


def test_speckit_manifest_hashes_are_actually_verified() -> None:
    """Closes a second, smaller gap found while pinning the extensions.

    `test_speckit_provenance.py` reads `speckit.manifest.json` for its `integration`
    and `version` fields but never checks its ten hashes, so those files were pinned
    on paper and unverified in practice. Ten entries, all matching.
    """
    pinner = _load_pinner()
    declared = json.loads((_REPO_ROOT / _SPECKIT_MANIFEST).read_text(encoding="utf-8"))

    assert len(declared["files"]) == 10
    for path, digest in declared["files"].items():
        assert pinner.blob_sha256(path, root=_REPO_ROOT) == digest, path
