"""Regenerate the DAX/TMDL/reason golden fixtures under tests/fixtures/golden/dax/.

OPTIONAL, HUMAN-RUN ONLY (spec 100-generated-artifact-golden-tests, FR-008). This
script is NOT a pytest test or fixture, is NOT a `retail` CLI subcommand, is NOT
wired into `retail check`, and is NEVER invoked by CI. Run it manually after an
INTENTIONAL change to `src/seshat/dax_gen.py`'s emission logic, then review the
resulting `git diff tests/fixtures/golden/dax/` yourself before staging/committing
-- this script asserts nothing and returns no pass/fail signal.

Usage:
    python tests/fixtures/golden/regenerate_dax_golden.py

It reproduces the exact `retail generate` CLI call shape
(`src/seshat/cli.py::_run_generate`):

    generate_measure(contract.get("definition") or {}, name=contract.get("name"),
                      doc_intent=contract.get("formula_intent"))

-- no `format_string`/`display_folder` override -- against the three committed
contract fixtures under tests/fixtures/contracts/, and overwrites ONLY the five
golden files this feature defines:

    tests/fixtures/golden/dax/base_revenue.dax.txt
    tests/fixtures/golden/dax/base_revenue.tmdl.txt
    tests/fixtures/golden/dax/ratio_disc.dax.txt
    tests/fixtures/golden/dax/ratio_disc.tmdl.txt
    tests/fixtures/golden/dax/refuse_no_column.reason.txt

It never writes a contract fixture, a golden SQL file, or any file under src/ or
warehouse/.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Standalone script: pytest gets `src` on sys.path via conftest; a script invoked
# directly (`python tests/fixtures/golden/regenerate_dax_golden.py`) does not, so
# bootstrap it from this file's own location before importing `retail`.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from seshat.dax_gen import generate_measure, load_contract  # noqa: E402

_CONTRACTS_DIR = _REPO_ROOT / "tests" / "fixtures" / "contracts"
_GOLDEN_DAX_DIR = _REPO_ROOT / "tests" / "fixtures" / "golden" / "dax"

# Fixed corpus (spec Assumptions): two success-case stems, one refusal-case stem.
_SUCCESS_STEMS = ("base_revenue", "ratio_disc")
_REFUSAL_STEMS = ("refuse_no_column",)


def _write_golden(path: Path, text: str) -> None:
    """Write `text` verbatim with a single trailing newline, UTF-8, no BOM."""
    body = text if text.endswith("\n") else text + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")


def _generate(stem: str):
    contract = load_contract(str(_CONTRACTS_DIR / f"{stem}.yaml"))
    return generate_measure(
        contract.get("definition") or {},
        name=contract.get("name"),
        doc_intent=contract.get("formula_intent"),
    )


def main() -> None:
    for stem in _SUCCESS_STEMS:
        result = _generate(stem)
        if not result.ok:
            print(f"[skip] {stem}: unexpectedly refused ({result.reason})")
            continue
        _write_golden(_GOLDEN_DAX_DIR / f"{stem}.dax.txt", result.dax or "")
        _write_golden(_GOLDEN_DAX_DIR / f"{stem}.tmdl.txt", result.tmdl_block or "")
        print(f"wrote {stem}.dax.txt and {stem}.tmdl.txt")

    for stem in _REFUSAL_STEMS:
        result = _generate(stem)
        if result.ok:
            print(f"[skip] {stem}: unexpectedly succeeded (expected a refusal)")
            continue
        _write_golden(_GOLDEN_DAX_DIR / f"{stem}.reason.txt", result.reason or "")
        print(f"wrote {stem}.reason.txt")

    print(
        "\ndone. Review the diff yourself:\n"
        "    git diff tests/fixtures/golden/dax/\n"
        "This script never commits on your behalf."
    )


if __name__ == "__main__":
    main()
