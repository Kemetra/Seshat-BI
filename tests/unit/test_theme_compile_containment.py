"""meta.compiles_to containment tests for the tokens->theme compiler (F234)."""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.theme_compile import ThemeCompileError, compile_theme
from tests.unit.test_theme_compile import TOKENS, _write_tokens

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("escape", ["../escaped.theme.json", "ABS"])
def test_compiles_to_outside_the_repo_is_refused(tmp_path: Path, escape: str):
    """meta.compiles_to is committed content; it may not name a path outside
    the repository (F234). --out stays the explicit operator override."""
    repo = tmp_path / "repo"
    target = tmp_path / "escaped.theme.json"
    compiles_to = str(target) if escape == "ABS" else escape
    doc = {**TOKENS, "meta": {**TOKENS["meta"], "compiles_to": compiles_to}}
    tokens = _write_tokens(repo, doc)
    with pytest.raises(ThemeCompileError, match="outside the repository"):
        compile_theme(tokens, out_path=None, force=False)
    assert not target.exists()


def test_compiles_to_escape_refused_for_a_relative_tokens_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A relative tokens path must not let the containment check resolve a
    doubled root while the write lands outside the repository (F234)."""
    monkeypatch.chdir(tmp_path)
    doc = {**TOKENS, "meta": {**TOKENS["meta"], "compiles_to": "../escaped.theme.json"}}
    _write_tokens(tmp_path / "repo", doc)
    tokens = Path("repo/design/tokens/executive-dark-design-tokens.yaml")
    with pytest.raises(ThemeCompileError, match="outside the repository"):
        compile_theme(tokens, out_path=None, force=False)
    assert not (tmp_path / "escaped.theme.json").exists()
