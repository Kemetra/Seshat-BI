"""Rule-registry snapshot manifest generator.

Serializes the live rule registry (``registry.all_rules()``) to a golden-file
inventory at ``docs/rules/rules-manifest.json`` so the rule set is recorded by
code, not by a hand-typed count. A companion snapshot test
(``tests/unit/test_rules_manifest_snapshot.py``) asserts ``live == committed`` and
fails closed on any drift.

Serialization contract (Principle IX -- cross-platform stable):

- entries are ``{"id": ..., "title": ...}`` and nothing else (the only two
  serializable fields of ``RegisteredRule``; ``rule`` is a callable);
- the list is sorted by ``id`` (single deterministic ordering);
- key order within each entry is ``id`` then ``title``;
- output is UTF-8 without BOM, ``\\n`` line endings, with a single trailing
  newline.

This module adds NO new registered rule and NO new ``EXPECTED_RULE_ID``: it is a
generator + a test-only golden assertion, never a ``retail check`` rule.
"""

from __future__ import annotations

import json
from pathlib import Path

from .registry import RegisteredRule, all_rules

# repo-relative location of the committed golden manifest.
MANIFEST_REL_PATH = "docs/rules/rules-manifest.json"


def build_manifest(rules: tuple[RegisteredRule, ...]) -> list[dict[str, str]]:
    """Return the ordered manifest data from a rule tuple.

    Sorted by ``id``; each entry carries exactly ``id`` and ``title``. Generated
    from the live registry, never a hand-typed literal.
    """
    return [{"id": r.id, "title": r.title} for r in sorted(rules, key=lambda r: r.id)]


def serialize_manifest(data: list[dict[str, str]]) -> str:
    """Serialize manifest data to the stable JSON text form.

    Deterministic: ``indent=2``, ``sort_keys=True`` (so key order is stable
    regardless of insertion order), a single trailing newline, ``\\n`` endings.
    """
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def render_manifest() -> str:
    """Render the manifest text for the CURRENT live registry."""
    return serialize_manifest(build_manifest(all_rules()))


def write_manifest(repo_root: Path | str = ".") -> Path:
    """Write the manifest to ``<repo_root>/docs/rules/rules-manifest.json``.

    Writes UTF-8 without BOM and ``\\n`` line endings (``newline="\\n"`` keeps the
    bytes identical on Windows under ``core.autocrlf=true``). Returns the path.
    """
    path = Path(repo_root) / MANIFEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_manifest(), encoding="utf-8", newline="\n")
    return path
