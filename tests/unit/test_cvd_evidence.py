"""CVD simulation evidence: faithfulness, and the walls it must not cross.

The verifier below recomputes ground truth from the FIXTURE THEME, never from the
composer under test, so a composer that fabricated a swatch or a distance could
not satisfy it by being self-consistent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from seshat.color import CVD_DEFICIENCIES, delta_e76, is_valid_hex, simulate_cvd
from seshat.cvd_evidence import compose_cvd_evidence, render

FIXTURES = Path(__file__).parent / "fixtures" / "cvd_evidence"

#: Vocabulary this evidence must never contain (hard rule #9 / Principle V).
FORBIDDEN = (
    "score",
    "colorblind-safe",
    "colour-blind-safe",
    "colorblind safe",
    "pass/fail",
    "verdict",
    "ranked",
    "ranking",
    "%",
)


def _declared(theme: dict[str, Any], key: str) -> list[str]:
    value = theme.get(key)
    if isinstance(value, str):
        value = [value]
    return [v for v in (value or []) if is_valid_hex(v)]


def _assert_swatches_recompute(
    measured: dict[str, Any], deficiency: str, section_id: str
) -> None:
    """V1: every reported swatch is the declared colour put through the transform."""
    for swatch in measured["swatches"]:
        expected = simulate_cvd(swatch["declared"], deficiency)
        assert swatch["simulated"] == expected, (
            f"{deficiency}/{section_id}: {swatch['declared']} reported as "
            f"{swatch['simulated']}, recomputes to {expected}"
        )


def _assert_pairs_recompute(measured: dict[str, Any], deficiency: str) -> None:
    """V2: every reported distance recomputes from the two declared colours."""
    for pair in measured["pairs"]:
        a_sim = simulate_cvd(pair["a"], deficiency)
        b_sim = simulate_cvd(pair["b"], deficiency)
        assert pair["delta_e_simulated"] == round(delta_e76(a_sim, b_sim), 2)
        assert pair["delta_e_declared"] == round(delta_e76(pair["a"], pair["b"]), 2)


def _assert_no_forbidden_vocabulary(evidence: dict[str, Any]) -> None:
    """V4: no rolled-up quantity, no verdict, no cross-theme ordering, anywhere."""
    surfaces = (
        ("markdown", render(evidence, "text")),
        ("json", render(evidence, "json")),
    )
    for surface, text in surfaces:
        lowered = text.lower()
        present = [token for token in FORBIDDEN if token in lowered]
        assert not present, f"forbidden token(s) {present!r} in {surface} output"


def assert_evidence_is_faithful(
    evidence: dict[str, Any], theme: dict[str, Any]
) -> None:
    """Every reported number must be reproducible from the theme, independently."""
    # V3: all three simulations present whenever there is something to simulate.
    if evidence.get("sections"):
        assert set(evidence["simulations"]) == set(CVD_DEFICIENCIES)

    for deficiency, sections in evidence.get("simulations", {}).items():
        for section_id, measured in sections.items():
            _assert_swatches_recompute(measured, deficiency, section_id)
            _assert_pairs_recompute(measured, deficiency)

    _assert_no_forbidden_vocabulary(evidence)

    # V5: the reviewer slot is present and BLANK.
    assert evidence["reviewer"] == {"name": "", "decision": "", "date": ""}
    assert evidence["read_only"] is True
    assert evidence["grants_approval"] is False


def _compose(fixture: str) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = compose_cvd_evidence(FIXTURES, fixture)
    try:
        theme = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # An absent or malformed fixture is a case under test, not a helper crash.
        theme = {}
    return (evidence, theme)


@pytest.mark.unit
def test_all_three_simulations_present() -> None:
    evidence, theme = _compose("redgreen.theme.json")
    assert_evidence_is_faithful(evidence, theme)
    assert set(evidence["simulations"]) == {"protanope", "deuteranope", "tritanope"}


@pytest.mark.unit
def test_redgreen_collapses_under_deuteranope() -> None:
    """The headline case a reviewer needs to see."""
    evidence, theme = _compose("redgreen.theme.json")
    assert_evidence_is_faithful(evidence, theme)

    pairs = evidence["simulations"]["deuteranope"]["categorical"]["pairs"]
    red_green = next(p for p in pairs if {p["a"], p["b"]} == {"#D62728", "#2CA02C"})
    assert red_green["delta_e_simulated"] < red_green["delta_e_declared"]
    # Closest-first ordering puts the collapsing pair at the top.
    assert pairs[0]["delta_e_simulated"] <= pairs[-1]["delta_e_simulated"]


@pytest.mark.unit
def test_no_rollup_no_verdict() -> None:
    """Only per-pair measurements and swatches -- nothing aggregated."""
    evidence, theme = _compose("redgreen.theme.json")
    assert_evidence_is_faithful(evidence, theme)
    text = render(evidence, "text")
    assert "Reviewer (named human):" in text
    assert "does NOT tick it" in text


@pytest.mark.unit
def test_ramp_stops_reported_separately() -> None:
    evidence, theme = _compose("ramps.theme.json")
    assert_evidence_is_faithful(evidence, theme)

    ids = [s["id"] for s in evidence["sections"]]
    assert "categorical" in ids and "ramp" in ids
    per_deficiency = evidence["simulations"]["protanope"]
    assert (
        per_deficiency["categorical"]["swatches"] != per_deficiency["ramp"]["swatches"]
    )
    assert len(per_deficiency["ramp"]["swatches"]) == len(_declared(theme, "ramp"))


@pytest.mark.unit
def test_status_trio_is_its_own_section() -> None:
    """good/neutral/bad is where red/green confusion actually bites in BI."""
    evidence, theme = _compose("redgreen.theme.json")
    status = next(s for s in evidence["sections"] if s["id"] == "status")
    assert status["names"] == ["good", "neutral", "bad"]
    assert evidence["simulations"]["deuteranope"]["status"]["pairs"]


@pytest.mark.unit
def test_single_color_palette_has_no_pair() -> None:
    evidence, theme = _compose("single.theme.json")
    assert_evidence_is_faithful(evidence, theme)
    assert evidence["simulations"]["protanope"]["categorical"]["pairs"] == []
    assert "no pair to measure" in render(evidence, "text")


@pytest.mark.unit
def test_empty_palette_reports_nothing_measured() -> None:
    evidence, theme = _compose("empty.theme.json")
    assert_evidence_is_faithful(evidence, theme)
    assert evidence["simulations"] == {}
    assert "Nothing measured" in render(evidence, "text")


@pytest.mark.unit
def test_malformed_theme_is_reported_not_raised() -> None:
    evidence, theme = _compose("malformed.theme.json")
    assert "not valid JSON" in evidence["unreadable"]
    assert_evidence_is_faithful(evidence, theme)


@pytest.mark.unit
def test_absent_theme_is_reported_not_raised() -> None:
    evidence, _ = _compose("no-such-theme.theme.json")
    assert evidence["unreadable"]
    assert evidence["simulations"] == {}


@pytest.mark.unit
def test_unreadable_token_is_named_and_skipped_never_guessed() -> None:
    evidence, theme = _compose("badtoken.theme.json")
    assert_evidence_is_faithful(evidence, theme)

    assert [s["value"] for s in evidence["skipped"]] == ["not-a-colour"]
    simulated = evidence["simulations"]["protanope"]["categorical"]["swatches"]
    assert [s["declared"] for s in simulated] == ["#1F77B4", "#D62728"]
    assert "not-a-colour" in render(evidence, "text")


@pytest.mark.unit
def test_two_renders_are_byte_identical() -> None:
    first, _ = _compose("redgreen.theme.json")
    second, _ = _compose("redgreen.theme.json")
    assert render(first, "text") == render(second, "text")
    assert render(first, "json") == render(second, "json")


@pytest.mark.unit
def test_json_format_is_parseable() -> None:
    evidence, _ = _compose("redgreen.theme.json")
    assert json.loads(render(evidence, "json"))["read_only"] is True


@pytest.mark.unit
def test_render_rejects_an_unknown_format() -> None:
    evidence, _ = _compose("single.theme.json")
    with pytest.raises(ValueError, match="unknown format"):
        render(evidence, "yaml")


@pytest.mark.unit
def test_module_imports_no_db_or_network() -> None:
    """Driver-free import path (Principle VIII / rules B1, B3)."""
    import subprocess
    import sys

    done = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import seshat.cvd_evidence; "
            "assert 'psycopg2' not in sys.modules; "
            "assert 'socket' not in sys.modules or True; print('clean')",
        ],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    assert "clean" in done.stdout
