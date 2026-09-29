"""Small repository-hygiene contracts: shell-script line endings and the npm
alias manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


def test_shell_scripts_are_pinned_to_lf() -> None:
    """`* text=auto` + core.autocrlf=true checks .sh out as CRLF on Windows, which
    breaks it under Git Bash/WSL (`$'\\r': command not found`)."""
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in (r"\*\.sh", r"\*\.bash"):
        assert re.search(rf"^{pattern}\s+text\s+eol=lf\s*$", attributes, re.M), pattern


def test_npm_alias_manifest_is_a_placeholder_and_content_only() -> None:
    """The alias version and its scoped pin are rewritten at stage time; the
    committed copy must not claim a real (stale) release or grow install hooks."""
    alias = json.loads((ROOT / "npm/alias/package.json").read_text(encoding="utf-8"))
    placeholder = "0.0.0-staged"
    assert alias["version"] == placeholder
    assert alias["dependencies"] == {"@kemetra/seshat-bi": placeholder}
    scripts = alias.get("scripts") or {}
    assert not {"preinstall", "install", "postinstall", "prepare"} & set(scripts)
    assert sorted(alias["files"]) == ["README.md", "index.js"]

    stager = (ROOT / "npm/stage-release-packages.js").read_text(encoding="utf-8")
    assert "aliasManifest.version = version;" in stager
    assert 'aliasManifest.dependencies["@kemetra/seshat-bi"] = version;' in stager
