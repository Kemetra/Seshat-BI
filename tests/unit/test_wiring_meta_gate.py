"""5-place wiring meta-gate / registry lockstep self-check (feature 061).

This module IS the deliverable. It is a test-only, stdlib-only meta-gate that
proves the five wiring places stay in mutual lockstep with the live rule
registry, and that the rules package is internally symmetric (import list ==
``__all__`` == on-disk submodule set). It fails closed on any drift, naming the
offending symbol/id and the disagreeing place.

It adds NO registered rule, NO new EXPECTED_RULE_ID, and NO new golden file. It
registers nothing and never appears in the registry, the manifest, or the
posture record. It reads only: the in-process registry (after a deterministic
clear-and-reload), the rules package object (``__all__`` + imported submodules),
and two committed golden JSON files (read as UTF-8 without BOM).

Principles honored:
- I  (fail-closed, no advisory mode): every check is a hard assert/failure.
- VII (ADD not REPLACE): the per-place tests are left untouched.
- VIII (single source of truth reconciled, not duplicated): the expected-id set
  is imported from the existing wiring test, never re-listed here.
- IX (determinism/portability): set/dict comparisons only, never raw bytes;
  UTF-8 without BOM; paths derived from the package location, MAX_PATH-safe.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# ``pytest.fail(...)`` raises ``Failed``, which subclasses BaseException (NOT
# Exception), so a planted-drift RED case must expect this specific type.
_Failed = pytest.fail.Exception


# --------------------------------------------------------------------------- #
# Phase 1 -- shared read-only helpers                                         #
# --------------------------------------------------------------------------- #


def _live_snapshot() -> tuple[frozenset[str], dict[str, str], int]:
    """Return the deterministic live-registry snapshot.

    Clears the registry and reloads every rules submodule so the ``@register``
    decorators re-fire against a freshly-cleared registry -- order-proof against
    sibling tests that clear ``registry._RULES``. Reuses the exact technique in
    ``test_rules_wiring.py::test_registered_rule_ids_match_expected_set``.

    Returns ``(live_ids, live_id_title, live_count)`` where ``live_count`` is
    ``len(all_rules())`` (kept separate from ``len(live_ids)`` so C7 can catch a
    duplicate id).
    """
    import seshat.rules as rules_pkg
    from seshat import registry

    registry._RULES.clear()
    for info in pkgutil.iter_modules(rules_pkg.__path__):
        importlib.reload(importlib.import_module(f"seshat.rules.{info.name}"))

    rules = registry.all_rules()
    live_ids = frozenset(r.id for r in rules)
    live_id_title = {r.id: r.title for r in rules}
    live_count = len(rules)
    return live_ids, live_id_title, live_count


# The golden files live under docs/rules/ at the repo root. tests/unit/ is two
# levels below the repo root; parents[2] is the repo root (mirrors the proven
# resolution in test_rules_manifest_snapshot.py / test_severity_posture.py).
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_golden(rel_name: str) -> object:
    """Read a committed golden JSON file under docs/rules/ as UTF-8 without BOM.

    ``rel_name`` is one of ``rules-manifest.json`` / ``severity-posture.json``.
    Returns parsed content only; JSON parsing is line-ending/BOM agnostic so a
    Windows CRLF round-trip under core.autocrlf cannot flake the comparison.
    """
    path = _REPO_ROOT / "docs" / "rules" / rel_name
    assert path.exists(), f"golden file missing: docs/rules/{rel_name}"
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Phase 2 -- discovery helpers and the ADR-0007 exemption constant            #
# --------------------------------------------------------------------------- #


def _package_symmetry_sets() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Return ``(on_disk, import_list, dunder_all)`` name sets for the rules pkg.

    - ``on_disk``: submodule names via ``pkgutil.iter_modules`` over the package
      path (the package initializer is not a submodule, so it is excluded
      naturally).
    - ``import_list``: the imported-submodule attribute set on the package object
      (each side-effecting import binds the submodule as a package attribute).
    - ``dunder_all``: the ``__all__`` export list.
    """
    import seshat.rules as rules_pkg

    on_disk = frozenset(m.name for m in pkgutil.iter_modules(rules_pkg.__path__))
    dunder_all = frozenset(getattr(rules_pkg, "__all__", ()))
    # The imported-submodule set: names bound on the package that are themselves
    # submodules (their module __name__ is seshat.rules.<name>). This reflects the
    # side-effecting import list, independently of __all__.
    import_list = frozenset(
        name
        for name in dir(rules_pkg)
        if getattr(getattr(rules_pkg, name), "__name__", "") == f"seshat.rules.{name}"
    )
    return on_disk, import_list, dunder_all


# ADR-0007: the L3 verdict-to-finding surface is a non-registered severity
# surface that legitimately carries no rule id. It is the ONE known exemption.
# A new non-registered posture surface must be added here DELIBERATELY; until
# then C5 fails closed on it (this is intended, not a bug).
_ADR0007_NONREGISTERED_EXEMPT: frozenset[str] = frozenset({"L3:verdict_to_finding"})


def _posture_nonregistered_keys(posture: dict) -> frozenset[str]:
    """Return the non-registered surface keys recorded in the posture golden.

    The posture golden's top level has a ``registered`` section (keyed by rule id)
    plus one-or-more sibling sections whose leaf keys are non-registered surfaces.
    We collect every leaf key under any top-level section that is NOT
    ``registered``.
    """
    keys: set[str] = set()
    for section, body in posture.items():
        if section == "registered":
            continue
        if isinstance(body, dict):
            keys.update(body.keys())
        else:
            keys.add(section)
    return frozenset(keys)


# --------------------------------------------------------------------------- #
# Pure check helpers (fail closed, name the offender)                         #
# --------------------------------------------------------------------------- #


def _check_c1_symmetry(
    on_disk: frozenset[str],
    import_list: frozenset[str],
    dunder_all: frozenset[str],
) -> None:
    """C1: prove on-disk == import-list == ``__all__``; fail naming the offender."""
    if on_disk != import_list:
        pytest.fail(
            "C1 package asymmetry (on-disk vs import list): "
            f"on-disk-only={sorted(on_disk - import_list)}, "
            f"import-list-only={sorted(import_list - on_disk)}"
        )
    if on_disk != dunder_all:
        pytest.fail(
            "C1 package asymmetry (on-disk vs __all__): "
            f"missing-from-__all__={sorted(on_disk - dunder_all)}, "
            f"extra-in-__all__={sorted(dunder_all - on_disk)}"
        )


def _check_c2_ids(live_ids: frozenset[str], expected_ids: frozenset[str]) -> None:
    """C2: live registry ids reconcile with the expected-rule-id set (G6 class)."""
    if live_ids != expected_ids:
        pytest.fail(
            "C2 id source-of-truth drift (expected-rule-id set): "
            f"missing={sorted(expected_ids - live_ids)}, "
            f"unexpected={sorted(live_ids - expected_ids)}"
        )


def _check_c3_manifest(
    live_id_title: dict[str, str], manifest: list[dict[str, str]]
) -> None:
    """C3: golden manifest ``{id,title}`` matches the live ``{id,title}`` map."""
    man_by_id = {e["id"]: e["title"] for e in manifest}
    live_ids = set(live_id_title)
    man_ids = set(man_by_id)
    missing = sorted(live_ids - man_ids)  # live but not in manifest
    unexpected = sorted(man_ids - live_ids)  # in manifest but not live
    retitled = sorted(i for i in live_ids & man_ids if live_id_title[i] != man_by_id[i])
    if missing or unexpected or retitled:
        pytest.fail(
            "C3 manifest place drift: "
            f"missing={missing}, unexpected={unexpected}, retitled={retitled}"
        )


def _check_c4_posture(live_ids: frozenset[str], registered_ids: frozenset[str]) -> None:
    """C4: every live id appears in the posture golden ``registered`` section."""
    absent = sorted(live_ids - registered_ids)
    if absent:
        pytest.fail(
            f"C4 posture place: live ids absent from posture registered: {absent}"
        )


def _check_c5_exemption(
    nonregistered_keys: frozenset[str], exempt: frozenset[str]
) -> None:
    """C5: every non-registered posture surface key must be on the exemption list."""
    unexempted = sorted(nonregistered_keys - exempt)
    if unexempted:
        pytest.fail(
            "C5 non-registered surface not exempted (add deliberately per ADR-0007): "
            f"{unexempted}"
        )


def _check_c6_vacuity(submodule_count: int, rule_count: int) -> None:
    """C6: neither the on-disk submodule count nor the live rule count is zero."""
    if submodule_count == 0:
        pytest.fail("C6 vacuity trap: zero on-disk rule submodules")
    if rule_count == 0:
        pytest.fail("C6 vacuity trap: zero live registered rules")


def _check_c7_duplicates(live_count: int, live_ids: frozenset[str]) -> None:
    """C7: ``len(all_rules()) == len(live_ids)`` -- no duplicate registration."""
    if live_count != len(live_ids):
        # A duplicated id inflates the count beyond the unique-id set.
        pytest.fail(
            f"C7 duplicate registration: len(all_rules())={live_count} != "
            f"len(unique ids)={len(live_ids)}"
        )


# --------------------------------------------------------------------------- #
# Phase 3 -- User Story 1: un-guarded package-symmetry seam (P1)              #
# --------------------------------------------------------------------------- #


def test_c1_fails_on_missing_from_dunder_all() -> None:
    # RED-turned-guard: a name present on-disk and in the import list but missing
    # from __all__ must fail C1 naming the __all__ omission.
    on_disk = frozenset({"alpha", "beta"})
    import_list = frozenset({"alpha", "beta"})
    dunder_all = frozenset({"alpha"})  # beta omitted from __all__
    with pytest.raises(_Failed) as exc:
        _check_c1_symmetry(on_disk, import_list, dunder_all)
    assert "beta" in str(exc.value)
    assert "__all__" in str(exc.value)


def test_package_symmetry_live() -> None:
    # Known-good: the REAL discovered sets are equal.
    on_disk, import_list, dunder_all = _package_symmetry_sets()
    _check_c1_symmetry(on_disk, import_list, dunder_all)


def test_orphan_submodule_detected() -> None:
    # An on-disk name absent from both the import list and __all__ (an orphan
    # module) must fail C1 naming the orphan.
    on_disk, import_list, dunder_all = _package_symmetry_sets()
    orphan = on_disk | {"orphan_module"}
    with pytest.raises(_Failed) as exc:
        _check_c1_symmetry(orphan, import_list, dunder_all)
    assert "orphan_module" in str(exc.value)


# --------------------------------------------------------------------------- #
# Phase 4 -- User Story 2: five places in mutual lockstep (P1)                #
# --------------------------------------------------------------------------- #


def _expected_rule_ids() -> frozenset[str]:
    # Import the single source of truth; never re-list it here (Principle VIII).
    from tests.unit.test_rules_wiring import EXPECTED_RULE_IDS

    return frozenset(EXPECTED_RULE_IDS)


def test_c2_fails_on_missing_expected_id() -> None:
    # RED-turned-guard (G6 omission-symmetry class): drop one id from a COPY of
    # the expected set; C2 must fail with `missing=` naming that id.
    live_ids, _, _ = _live_snapshot()
    dropped = next(iter(live_ids))
    broken_expected = live_ids - {dropped}
    with pytest.raises(_Failed) as exc:
        _check_c2_ids(live_ids, broken_expected)
    assert "missing" in str(exc.value)
    assert dropped in str(exc.value)


def test_ids_match_expected_live() -> None:
    # Known-good: real live ids == real EXPECTED_RULE_IDS.
    live_ids, _, _ = _live_snapshot()
    _check_c2_ids(live_ids, _expected_rule_ids())


def test_manifest_matches_live() -> None:
    # C3 known-good + planted-drift RED.
    _, live_id_title, _ = _live_snapshot()
    manifest = _read_golden("rules-manifest.json")
    _check_c3_manifest(live_id_title, manifest)

    # Planted drift: retitle one manifest entry -> C3 must fail naming it + manifest.
    victim = manifest[0]["id"]
    drifted = [dict(e) for e in manifest]
    drifted[0]["title"] = drifted[0]["title"] + " DRIFT"
    with pytest.raises(_Failed) as exc:
        _check_c3_manifest(live_id_title, drifted)
    assert "retitled" in str(exc.value)
    assert victim in str(exc.value)


def test_posture_covers_live() -> None:
    # C4 known-good + planted-drift RED.
    live_ids, _, _ = _live_snapshot()
    posture = _read_golden("severity-posture.json")
    registered_ids = frozenset(posture["registered"].keys())
    _check_c4_posture(live_ids, registered_ids)

    # Planted drift: a live id absent from the posture registered set -> C4 fails.
    victim = next(iter(live_ids))
    broken = registered_ids - {victim}
    with pytest.raises(_Failed) as exc:
        _check_c4_posture(live_ids, broken)
    assert "posture" in str(exc.value)
    assert victim in str(exc.value)


def test_no_duplicate_registration() -> None:
    # C7 known-good + planted-drift RED.
    live_ids, _, live_count = _live_snapshot()
    _check_c7_duplicates(live_count, live_ids)

    # Planted drift: an inflated count (a duplicated id) -> C7 fails.
    with pytest.raises(_Failed) as exc:
        _check_c7_duplicates(live_count + 1, live_ids)
    assert "duplicate" in str(exc.value).lower()


def test_registry_not_vacuous() -> None:
    # C6 known-good + planted-drift RED for each zero-count side.
    on_disk, _, _ = _package_symmetry_sets()
    _, _, live_count = _live_snapshot()
    _check_c6_vacuity(len(on_disk), live_count)

    with pytest.raises(_Failed) as exc:
        _check_c6_vacuity(0, live_count)
    assert "submodule" in str(exc.value)

    with pytest.raises(_Failed) as exc:
        _check_c6_vacuity(len(on_disk), 0)
    assert "rule" in str(exc.value)


# --------------------------------------------------------------------------- #
# Phase 5 -- User Story 3: non-registered-surface exemption (P2)             #
# --------------------------------------------------------------------------- #


def test_c5_fails_on_unexempted_surface() -> None:
    # RED-turned-guard: a new non-registered surface key not on the exemption
    # list must fail C5 naming the un-exempted key.
    posture = _read_golden("severity-posture.json")
    nonreg = _posture_nonregistered_keys(posture)
    planted = nonreg | {"L4:brand_new_surface"}
    with pytest.raises(_Failed) as exc:
        _check_c5_exemption(planted, _ADR0007_NONREGISTERED_EXEMPT)
    assert "L4:brand_new_surface" in str(exc.value)


def test_adr0007_surface_exempted_live() -> None:
    # Known-good: the REAL posture non-registered surfaces are all exempted (the
    # one L3 surface), no rule id demanded of it.
    posture = _read_golden("severity-posture.json")
    nonreg = _posture_nonregistered_keys(posture)
    _check_c5_exemption(nonreg, _ADR0007_NONREGISTERED_EXEMPT)


# --------------------------------------------------------------------------- #
# Phase 6 -- polish: end-to-end known-good sweep                              #
# --------------------------------------------------------------------------- #


def test_meta_gate_all_green() -> None:
    # SC-003: single-pass lockstep contract. Run C1-C7 over the REAL repo state
    # and assert a clean pass. If any place drifts, exactly one of these fails
    # closed with a locating message -- there is no advisory/warn-only mode.
    live_ids, live_id_title, live_count = _live_snapshot()
    on_disk, import_list, dunder_all = _package_symmetry_sets()
    manifest = _read_golden("rules-manifest.json")
    posture = _read_golden("severity-posture.json")
    registered_ids = frozenset(posture["registered"].keys())
    nonreg = _posture_nonregistered_keys(posture)

    _check_c1_symmetry(on_disk, import_list, dunder_all)  # C1
    _check_c2_ids(live_ids, _expected_rule_ids())  # C2
    _check_c3_manifest(live_id_title, manifest)  # C3
    _check_c4_posture(live_ids, registered_ids)  # C4
    _check_c5_exemption(nonreg, _ADR0007_NONREGISTERED_EXEMPT)  # C5
    _check_c6_vacuity(len(on_disk), live_count)  # C6
    _check_c7_duplicates(live_count, live_ids)  # C7
