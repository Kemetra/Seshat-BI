"""Golden-file snapshot test for the rule-registry manifest (feature 043).

Asserts the committed ``docs/rules/rules-manifest.json`` matches the LIVE
registry (``registry.all_rules()``). Fails closed on any drift -- a rule added,
removed, renamed, or re-titled without regenerating the manifest breaks this
test. The fix is always: run ``retail manifest`` and commit the manifest in the
same change.

This test adds NO new ``EXPECTED_RULE_ID`` and registers NO rule -- it is a
test-only golden assertion, not a ``retail check`` rule.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
from pathlib import Path

import pytest

from seshat.manifest import MANIFEST_REL_PATH, build_manifest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = _REPO_ROOT / MANIFEST_REL_PATH

_REGEN_HINT = (
    "rule-registry manifest is out of date. Regenerate it and commit the result "
    "in the same change:\n    retail manifest\n"
)


def _live_rules():
    # Force a clean re-registration so this test does not depend on global
    # registry state left by sibling tests (test_registry.py / test_cli.py clear
    # registry._RULES for isolation). A plain import_module is a no-op for an
    # already-imported module, so the @register decorators would NOT re-fire after
    # a clear -- we must importlib.reload each submodule. This mirrors the proven
    # pattern in test_rules_wiring.py (clear + reload) and is order-proof.
    import seshat.rules as rules_pkg
    from seshat import registry

    registry._RULES.clear()
    for info in pkgutil.iter_modules(rules_pkg.__path__):
        importlib.reload(importlib.import_module(f"seshat.rules.{info.name}"))
    rules = registry.all_rules()
    assert rules, "no rules registered -- seshat.rules submodules failed to reload"
    return rules


def _load_committed() -> list[dict[str, str]]:
    # Read as UTF-8 and parse JSON; JSON parsing is line-ending agnostic, so a
    # Windows CRLF round-trip under core.autocrlf cannot flake this comparison.
    text = _MANIFEST_PATH.read_text(encoding="utf-8")
    return json.loads(text)


def test_committed_manifest_matches_live_registry() -> None:
    assert _MANIFEST_PATH.exists(), (
        f"{MANIFEST_REL_PATH} does not exist. " + _REGEN_HINT
    )
    expected = build_manifest(_live_rules())
    committed = _load_committed()

    if committed != expected:
        exp_ids = {e["id"] for e in expected}
        com_ids = {e["id"] for e in committed}
        missing = sorted(exp_ids - com_ids)  # live rules absent from the manifest
        unexpected = sorted(com_ids - exp_ids)  # manifest rules no longer live
        exp_by_id = {e["id"]: e["title"] for e in expected}
        com_by_id = {e["id"]: e["title"] for e in committed}
        retitled = sorted(i for i in exp_ids & com_ids if exp_by_id[i] != com_by_id[i])
        pytest.fail(
            "rule-registry manifest drift:\n"
            f"  missing (live but not in manifest): {missing}\n"
            f"  unexpected (in manifest but not live): {unexpected}\n"
            f"  retitled: {retitled}\n" + _REGEN_HINT
        )


def test_generation_is_idempotent() -> None:
    # Generating twice yields byte-identical data (determinism / SC-002).
    from seshat.manifest import render_manifest

    assert render_manifest() == render_manifest()


def test_manifest_adds_no_new_rule() -> None:
    # The manifest entry count equals the live registry size -- this feature adds
    # NO new registered rule (test-only golden assertion). Guards FR-007 / SC-004.
    rules = _live_rules()
    assert len(build_manifest(rules)) == len(rules)
