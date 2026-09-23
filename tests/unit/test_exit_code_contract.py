"""Snapshot of every verb's exit-code meaning (audit F139).

The same number means different things in different verbs -- e.g. 2 is a
refusal for ``report``/``analyze``/``studio`` but a post-write validation
failure for ``pbi-mcp``. The values are public contract, so they are NOT
renumbered; this table pins each verb's code -> meaning map so a change (or a
new colliding verb) is a deliberate, reviewed edit rather than silent drift.
A caller must key on the verb's own table (or its ``--json`` outcome field),
never on a cross-verb reading of the bare number.
"""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit

#: verb -> (module, {attribute: expected value}). Attributes may be ints or dicts.
EXIT_CONTRACT: dict[str, tuple[str, dict[str, object]]] = {
    "pbi-mcp": (
        "seshat.pbi_mcp_adapter.orchestrate",
        {
            "EXIT_OK": 0,
            "EXIT_REFUSED": 1,
            "EXIT_VALIDATION_FAILED": 2,
            "EXIT_INDETERMINATE": 3,
        },
    ),
    "report": (
        "seshat.cli.commands.report",
        {"EXIT_OK": 0, "EXIT_HARNESS_ERROR": 1, "EXIT_REFUSED": 2},
    ),
    "analyze": (
        "seshat.cli.commands.analyze",
        {
            "_EXIT_CODES": {
                "computed": 0,
                "withheld": 1,
                "refused": 2,
                "failed": 3,
                "unavailable": 4,
            }
        },
    ),
    "studio": (
        "seshat.studio.__main__",
        {"_EXIT_OK": 0, "_EXIT_USAGE": 1, "_EXIT_REFUSED": 2},
    ),
    "gap-detector": ("seshat.cli.commands.gap_detector", {"_EXIT_USAGE": 2}),
    "xray / model-diff": (
        "seshat.cli.commands.xray",
        {"_EXIT": {"completed": 0, "blocked": 3}},
    ),
}


@pytest.mark.parametrize("verb", sorted(EXIT_CONTRACT))
def test_verb_exit_codes_match_the_snapshot(verb: str) -> None:
    module_name, expected = EXIT_CONTRACT[verb]
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:  # an optional extra absent in this job
        pytest.skip(f"{module_name} needs an optional extra: {exc}")
    actual = {name: getattr(module, name, None) for name in expected}
    assert actual == expected, (
        f"{verb} exit codes changed; they are public contract -- update this "
        "snapshot deliberately and note the change in the release notes"
    )


def test_the_known_cross_verb_collision_is_recorded() -> None:
    """Exit 2 is NOT a uniform 'refused': pinning the collision keeps any
    wrapper author from assuming one meaning per number."""
    pbi = EXIT_CONTRACT["pbi-mcp"][1]
    report = EXIT_CONTRACT["report"][1]
    assert pbi["EXIT_VALIDATION_FAILED"] == report["EXIT_REFUSED"] == 2
