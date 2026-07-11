"""Golden tests for the DAX generator's own emission (spec 100).

`test_dax_gen.py` asserts the GENERATOR'S ROUND-TRIP PROPERTY: emitted DAX
re-verifies as `pass` under `check_measure_drift`. It does NOT assert what the
emitted DAX text actually IS. This module adds that byte-level pin: for a fixed
set of contract fixtures, `generate_measure(load_contract(...))` -- using the
SAME argument mapping `retail generate`'s CLI path uses
(`src/seshat/cli.py::_run_generate`) -- must emit `dax` / `tmdl_block` (success
cases) or `reason` (the one refusal case) text identical to a committed golden
file. Any drift, intended or not, fails with a visible diff.

Normalization (FR-006), used identically for every comparison in this module:
replace every "\\r\\n" with "\\n" in both the actual and the golden text, then
strip at most one trailing "\\n" from each side, before an exact string-equality
comparison. This keeps the comparison stable across a CRLF checkout
(`core.autocrlf=true` on Windows) and an LF checkout of the same commit.

This module reads only already-committed repository files and calls a pure
Python function (`generate_measure`); it opens no database connection and
imports no live-execution adapter (Principle VIII).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.dax_gen import generate_measure, load_contract

pytestmark = pytest.mark.unit

_CONTRACTS_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"
_GOLDEN_DAX_DIR = Path(__file__).parent.parent / "fixtures" / "golden" / "dax"

# Fixed fixture corpus (spec Assumptions): as of this spec, this feature does not
# grow this list -- adding a new metric-contract `kind` gets its own golden as a
# follow-on feature, not a silent expansion here.
_SUCCESS_STEMS = ("base_revenue", "ratio_disc")
_REFUSAL_STEM = "refuse_no_column"


def _normalize(text: str) -> str:
    """FR-006: CRLF -> LF, then strip at most one trailing '\\n'."""
    text = text.replace("\r\n", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text


def _read_golden(path: Path) -> str:
    # FR-007: a missing/unreadable golden fails the test explicitly, naming the
    # path -- never a silent skip, never a pass-by-default.
    if not path.is_file():
        pytest.fail(f"missing golden fixture (never a skip): {path}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        pytest.fail(f"could not read golden fixture {path}: {exc}")


def _generate(stem: str):
    """Reproduce the exact `retail generate` CLI call shape (_run_generate)."""
    contract = load_contract(str(_CONTRACTS_DIR / f"{stem}.yaml"))
    return generate_measure(
        contract.get("definition") or {},
        name=contract.get("name"),
        doc_intent=contract.get("formula_intent"),
    )


@pytest.mark.parametrize("stem", _SUCCESS_STEMS)
def test_dax_golden_pin(stem: str) -> None:
    result = _generate(stem)
    assert result.ok is True, (
        f"{stem}: generate_measure unexpectedly refused: {result.reason}"
    )

    golden_dax = _read_golden(_GOLDEN_DAX_DIR / f"{stem}.dax.txt")
    actual_dax = _normalize(result.dax or "")
    expected_dax = _normalize(golden_dax)
    assert actual_dax == expected_dax, (
        f"{stem}: generated DAX drifted from the committed golden.\n"
        f"actual:   {actual_dax!r}\n"
        f"expected: {expected_dax!r}"
    )


@pytest.mark.parametrize("stem", _SUCCESS_STEMS)
def test_tmdl_golden_pin(stem: str) -> None:
    result = _generate(stem)
    assert result.ok is True, (
        f"{stem}: generate_measure unexpectedly refused: {result.reason}"
    )

    golden_tmdl = _read_golden(_GOLDEN_DAX_DIR / f"{stem}.tmdl.txt")
    actual_tmdl = _normalize(result.tmdl_block or "")
    expected_tmdl = _normalize(golden_tmdl)
    assert actual_tmdl == expected_tmdl, (
        f"{stem}: generated TMDL block drifted from the committed golden.\n"
        f"actual:   {actual_tmdl!r}\n"
        f"expected: {expected_tmdl!r}"
    )


def test_refusal_reason_golden_pin() -> None:
    result = _generate(_REFUSAL_STEM)
    assert result.ok is False, f"{_REFUSAL_STEM}: expected a refusal, got ok=True"
    assert result.dax is None
    assert result.tmdl_block is None

    golden_reason = _read_golden(_GOLDEN_DAX_DIR / f"{_REFUSAL_STEM}.reason.txt")
    actual_reason = _normalize(result.reason or "")
    expected_reason = _normalize(golden_reason)
    assert actual_reason == expected_reason, (
        f"{_REFUSAL_STEM}: refusal reason drifted from the committed golden.\n"
        f"actual:   {actual_reason!r}\n"
        f"expected: {expected_reason!r}"
    )


def test_missing_golden_fails_closed_never_skips(tmp_path: Path) -> None:
    """FR-007: a missing golden path is an explicit failure, never a skip.

    This is a dedicated assertion (not just an observation of T007/T008's
    natural RED state before goldens existed) so a future reader does not
    "fix" `_read_golden` into a `pytest.skip` on a missing file.
    """
    missing = tmp_path / "does_not_exist.dax.txt"
    with pytest.raises(pytest.fail.Exception):
        _read_golden(missing)
