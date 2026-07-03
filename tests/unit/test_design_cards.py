"""Adopt the orphaned Claude Design System card validator into the test surface (D2).

``design/claude-design-system/validate_cards.py`` is a stdlib-only render-check
validator that asserts DesignSync invariants over the committed preview-card
bundle (no @dsCard marker -> fail, real-data token -> fail, thin card -> fail,
remote @import in CSS -> fail). It existed but ran on NOTHING in CI. This test
adopts it: it imports ``main()`` and runs it over the committed bundle, asserting

  * exit 0 (every committed card is clean), and
  * the bundle still has exactly the anchored card count (a silently-dropped or
    ungoverned-added card fails here, not silently).

Grounded (idea D2): the script + bundle already exist and pass; this only wires
the existing validator into the governed suite. It is a test, not a @register
rule -- no 5-place wiring, no rule-count change.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).parent.parent.parent
_VALIDATOR = REPO_ROOT / "design" / "claude-design-system" / "validate_cards.py"
_PREVIEW = REPO_ROOT / "design" / "claude-design-system" / "preview"
_COUNT_ANCHOR = REPO_ROOT / "docs" / "quality" / "design-cards-count.yaml"


def _load_validator():
    """Import validate_cards.py by file path (the design/ dir is not a package)."""
    spec = importlib.util.spec_from_file_location("validate_cards", _VALIDATOR)
    assert spec and spec.loader, "could not load validate_cards.py"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _expected_count() -> int:
    data = yaml.safe_load(_COUNT_ANCHOR.read_text(encoding="utf-8"))
    return int(data["expected_card_count"])


def test_validator_script_exists() -> None:
    assert _VALIDATOR.exists(), "validate_cards.py must exist to be governed"
    assert _PREVIEW.is_dir(), "the preview card bundle must exist"


def test_committed_preview_bundle_passes_validation() -> None:
    """validate_cards.main() must exit 0 over the committed bundle -- every card
    is marker-complete, data-free, non-thin, and CSP-clean."""
    validator = _load_validator()
    exit_code = validator.main(["validate_cards.py", str(_PREVIEW)])
    assert exit_code == 0, "committed preview cards failed validate_cards checks"


def test_card_count_matches_anchor_no_silent_drift() -> None:
    """The bundle has exactly the anchored number of cards, so a dropped or
    ungoverned-added card fails here rather than passing silently."""
    actual = len(sorted(_PREVIEW.glob("*.html")))
    assert actual == _expected_count(), (
        f"preview card count {actual} != anchor {_expected_count()} "
        f"(docs/quality/design-cards-count.yaml); update the anchor in the same "
        f"commit that adds/removes a card"
    )
