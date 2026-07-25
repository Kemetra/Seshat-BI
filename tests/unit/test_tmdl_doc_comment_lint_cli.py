"""CLI-level tests for `seshat tmdl-doc-comment-lint` (#494).

Mirrors ``test_pbir_validate_bindings_cli.py``: exercises the wired
``_DISPATCH`` entry through ``seshat.cli.main``, not the library directly.
Read-only -- the exit code communicates the ONE rule's outcome, the CLI never
writes a file and never grants approval.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit

_UNATTACHED = (
    "/// Star relationships: many-to-one from the fact to each dimension.\n"
    "\n"
    "relationship fct_to_dim_product\n"
    "\tfromColumn: 'gold fct_sales_c086'.product_sk\n"
)

_ATTACHED = (
    "/// Star relationships: many-to-one from the fact to each dimension.\n"
    "relationship fct_to_dim_product\n"
    "\tfromColumn: 'gold fct_sales_c086'.product_sk\n"
)


def _model(tmp_path: Path, text: str) -> Path:
    model_dir = tmp_path / "Demo.SemanticModel"
    target = model_dir / "definition" / "relationships.tmdl"
    target.parent.mkdir(parents=True)
    target.write_text(text, encoding="utf-8")
    return model_dir


def _run(model_dir: Path) -> int:
    return main(["tmdl-doc-comment-lint", "--model", str(model_dir)])


def test_unattached_block_exits_one_and_names_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(_model(tmp_path, _UNATTACHED)) == 1
    out = capsys.readouterr().out
    assert "status: blocked" in out
    assert "doc-comment-not-attached" in out
    assert "relationships.tmdl" in out


def test_attached_block_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(_model(tmp_path, _ATTACHED)) == 0
    assert "status: pass" in capsys.readouterr().out


def test_missing_model_dir_fails_closed(tmp_path: Path) -> None:
    assert _run(tmp_path / "Absent.SemanticModel") == 1


def test_output_states_it_is_not_a_syntax_validator(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The disclaimer must ride along with a PASS, where over-reading happens."""
    _run(_model(tmp_path, _ATTACHED))
    out = capsys.readouterr().out
    assert "NOT a TMDL syntax validator" in out
    assert "does NOT mean the TMDL is valid" in out
    assert "Desktop can load the model" in out
    assert "grants no approval" in out


def test_verb_is_not_named_or_described_as_general_validation() -> None:
    """The ruling's crux: the name must not read as general TMDL validation.

    Pinned so a future rename toward `tmdl-validate` -- or a description that
    drops the disclaimer -- fails here rather than silently recreating #494's
    over-claim.
    """
    import argparse

    from seshat.cli.parser import _build_parser

    parser = _build_parser()
    sub = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    assert "tmdl-doc-comment-lint" in sub.choices
    assert "tmdl-validate" not in sub.choices
    doclint = sub.choices["tmdl-doc-comment-lint"]
    assert "NOT a TMDL syntax validator" in (doclint.description or "")
