"""Read-only colour-vision-deficiency (CVD) simulation EVIDENCE for a theme.

Given a committed Power BI theme JSON, applies the three deterministic CVD
transforms in ``seshat.color`` to the colours the theme declares and measures the
pairwise ``delta_e76`` distance between every colour pair AFTER simulation. The
result is evidence a NAMED HUMAN reads when filling the literal
``- [ ] **CVD distinguishability** -- OPEN`` checkbox that ``seshat.theme_gen``
leaves open (``theme_gen.py:789``).

What this module does NOT do, by design (hard rule #9, Principle V):

* no rolled-up "CVD score", no percentage, no index;
* no pass/fail verdict against any threshold;
* no comparison or ordering BETWEEN themes;
* no statement that a palette is or is not colorblind-safe.

A per-pair delta_e76 is a MEASUREMENT of an already-shipped distance metric --
the shipped CT2 and CT3 rules already surface pairwise deltaE -- so reporting it
is allowed. Ordering pairs by their measured distance is a presentation of those
measured values so a reviewer can find the tightest pairs first; it introduces no
new computed quantity.

Stdlib only, no DB/driver/network import at module load.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

from .color import CVD_DEFICIENCIES, delta_e76, is_valid_hex, simulate_cvd

OPEN_CHECKBOX = "- [ ] **CVD distinguishability** -- OPEN"

#: Theme keys read, in report order: (section id, theme key, human label).
_CATEGORICAL = ("categorical", "dataColors", "categorical palette (dataColors)")
_RAMP = ("ramp", "ramp", "declared sequential/diverging ramp stops")
_STATUS_KEYS = ("good", "neutral", "bad")


def _load_theme(theme_path: Path) -> dict[str, Any]:
    """Read a theme JSON, returning an explicit marker instead of raising.

    An absent or malformed theme is a reportable state, not a crash: the caller
    still emits evidence naming what it could not read.
    """
    try:
        raw = theme_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"unreadable": f"cannot read theme file: {exc.strerror or exc}"}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "unreadable": f"theme file is not valid JSON: {exc.msg} (line {exc.lineno})"
        }
    if not isinstance(parsed, dict):
        return {"unreadable": "theme file does not contain a JSON object"}
    return {"theme": parsed}


def _partition_colors(values: Any) -> tuple[list[str], list[str]]:
    """Split declared values into usable ``#RRGGBB`` colours and skipped tokens."""
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return ([], [])
    usable = [v for v in values if is_valid_hex(v)]
    skipped = [str(v) for v in values if not is_valid_hex(v)]
    return (usable, skipped)


_BAD_TOKEN = "not a #RRGGBB colour token"


def _skipped_entries(section_id: str, values: list[str]) -> list[dict[str, str]]:
    return [{"section": section_id, "value": v, "reason": _BAD_TOKEN} for v in values]


def _list_sections(
    theme: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """The groups declared as a list of colours: the palette and any ramp."""
    sections: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for section_id, key, label in (_CATEGORICAL, _RAMP):
        usable, bad = _partition_colors(theme.get(key))
        skipped += _skipped_entries(section_id, bad)
        if usable:
            sections.append(
                {"id": section_id, "source_key": key, "label": label, "colors": usable}
            )
    return (sections, skipped)


def _status_section(
    theme: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """The declared good/neutral/bad trio, kept apart from the palette.

    Worth its own group because it is green-and-red in practice -- the pair
    deuteranopia collapses hardest -- so conflating it with the categorical
    series would bury the finding a reviewer most needs.
    """
    declared = [(k, theme[k]) for k in _STATUS_KEYS if k in theme]
    usable = [(k, v) for k, v in declared if is_valid_hex(v)]
    skipped = _skipped_entries(
        "status", [str(v) for _, v in declared if not is_valid_hex(v)]
    )
    if not usable:
        return ([], skipped)
    section = {
        "id": "status",
        "source_key": "/".join(k for k, _ in usable),
        "label": "declared status colours (good/neutral/bad)",
        "colors": [v for _, v in usable],
        "names": [k for k, _ in usable],
    }
    return ([section], skipped)


def _collect_sections(
    theme: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Gather the colour groups the theme declares, plus any skipped tokens.

    Reported groups stay SEPARATE and are never conflated: a ramp stop is not a
    categorical series, and the status trio is not either.
    """
    list_sections, list_skipped = _list_sections(theme)
    status_sections, status_skipped = _status_section(theme)
    return (list_sections + status_sections, list_skipped + status_skipped)


def _measure_section(colors: list[str], deficiency: str) -> dict[str, Any]:
    """Simulated swatches plus every pairwise measured distance for one group."""
    swatches = [
        {"declared": c, "simulated": simulate_cvd(c, deficiency)} for c in colors
    ]
    simulated = {s["declared"]: s["simulated"] for s in swatches}
    pairs = [
        {
            "a": a,
            "b": b,
            "delta_e_declared": round(delta_e76(a, b), 2),
            "delta_e_simulated": round(delta_e76(simulated[a], simulated[b]), 2),
        }
        for a, b in combinations(colors, 2)
    ]
    # Closest-first: a presentation of the measured values, not a new quantity.
    pairs.sort(key=lambda p: (p["delta_e_simulated"], p["a"], p["b"]))
    return {"swatches": swatches, "pairs": pairs}


def compose_cvd_evidence(
    repo_root: str | Path, theme_path: str | Path
) -> dict[str, Any]:
    """Compose read-only CVD simulation evidence for one committed theme.

    Returns a dict carrying, per deficiency and per declared colour group, the
    simulated swatch for every colour and the measured pairwise distance for
    every colour pair -- plus a BLANK reviewer slot. Never raises for an absent
    or malformed theme; that state is reported instead.
    """
    root = Path(repo_root)
    path = Path(theme_path)
    resolved = path if path.is_absolute() else root / path

    evidence: dict[str, Any] = {
        "read_only": True,
        "grants_approval": False,
        "theme_path": path.as_posix(),
        "supports_checkbox": OPEN_CHECKBOX,
        "measurement": "delta_e76 (CIE76) between simulated colour pairs",
        # A named human fills this in. Never pre-filled, never derived.
        "reviewer": {"name": "", "decision": "", "date": ""},
    }

    loaded = _load_theme(resolved)
    if "unreadable" in loaded:
        evidence["unreadable"] = loaded["unreadable"]
        evidence["sections"] = []
        evidence["simulations"] = {}
        evidence["skipped"] = []
        return evidence

    theme = loaded["theme"]
    evidence["theme_name"] = theme.get("name", path.stem)
    sections, skipped = _collect_sections(theme)
    evidence["sections"] = [
        {k: v for k, v in s.items() if k != "colors"} | {"colors": s["colors"]}
        for s in sections
    ]
    evidence["skipped"] = skipped

    if not sections:
        evidence["simulations"] = {}
        evidence["note"] = "the theme declares no readable colours to simulate"
        return evidence

    evidence["simulations"] = {
        deficiency: {
            s["id"]: _measure_section(s["colors"], deficiency) for s in sections
        }
        for deficiency in CVD_DEFICIENCIES
    }
    return evidence


_DEFICIENCY_LABELS = {
    "protanope": "protanope -- absent long-wave (red) cones",
    "deuteranope": "deuteranope -- absent medium-wave (green) cones",
    "tritanope": "tritanope -- absent short-wave (blue) cones",
}

_PREAMBLE = (
    "This is MEASURED EVIDENCE for a named human design review. It supports the open\n"
    "review box in the theme spec and deliberately does NOT tick it. It grants no\n"
    "approval, changes no theme value, and touches no readiness stage. Whether these\n"
    "colours remain distinguishable under simulation is the reviewer's judgment; this\n"
    "document only reports what the transforms and the distance metric measured.\n"
)


def _render_section(section: dict[str, Any], measured: dict[str, Any]) -> list[str]:
    """Markdown for one colour group under one deficiency."""
    lines = [f"### {section['label']}", ""]
    lines += ["| declared | simulated |", "|---|---|"]
    lines += [
        f"| `{s['declared']}` | `{s['simulated']}` |" for s in measured["swatches"]
    ]
    lines.append("")

    if not measured["pairs"]:
        lines += ["Only one colour declared, so there is no pair to measure.", ""]
        return lines

    lines += [
        "Pairwise distance, closest measured distance first:",
        "",
        "| pair | dE declared | dE simulated |",
        "|---|---|---|",
    ]
    for p in measured["pairs"]:
        declared, simulated = p["delta_e_declared"], p["delta_e_simulated"]
        lines.append(f"| `{p['a']}` / `{p['b']}` | {declared} | {simulated} |")
    lines.append("")
    return lines


def _render_header(evidence: dict[str, Any]) -> list[str]:
    """Title, provenance of what was read, and the scope preamble."""
    name = evidence.get("theme_name", Path(evidence["theme_path"]).stem)
    return [
        f"# CVD simulation evidence -- {name}",
        "",
        f"Theme: `{evidence['theme_path']}`",
        f"Measurement: {evidence['measurement']}",
        f"Supports the open review box: `{evidence['supports_checkbox']}`",
        "",
        _PREAMBLE,
    ]


def _render_measurements(evidence: dict[str, Any]) -> list[str]:
    """One section per deficiency, or a named reason nothing was measured."""
    if evidence.get("unreadable"):
        return ["## Nothing measured", "", str(evidence["unreadable"]), ""]
    if not evidence.get("sections"):
        return ["## Nothing measured", "", evidence.get("note", ""), ""]

    by_id = {s["id"]: s for s in evidence["sections"]}
    lines: list[str] = []
    for deficiency in CVD_DEFICIENCIES:
        lines += [f"## {_DEFICIENCY_LABELS[deficiency]}", ""]
        for section_id, measured in evidence["simulations"][deficiency].items():
            lines += _render_section(by_id[section_id], measured)
    return lines


def _render_skipped(evidence: dict[str, Any]) -> list[str]:
    """Tokens that could not be read, named rather than guessed at."""
    if not evidence.get("skipped"):
        return []
    lines = ["## Skipped tokens", "", "Named, never guessed at:", ""]
    lines += [
        f"- `{item['value']}` in {item['section']} -- {item['reason']}"
        for item in evidence["skipped"]
    ]
    lines.append("")
    return lines


def _render_reviewer_slot() -> list[str]:
    """The blank slot a named human fills. Never pre-filled by this tool."""
    return [
        "## Reviewer decision",
        "",
        "To be completed by a named human. Left blank by this tool.",
        "",
        "- Reviewer (named human):",
        "- Decision:",
        "- Date:",
        "",
    ]


def render(evidence: dict[str, Any], fmt: str = "text") -> str:
    """Render composed evidence as markdown (``text``) or ``json``.

    Deterministic: the same evidence renders byte-identically every run.
    """
    if fmt == "json":
        return json.dumps(evidence, indent=2, sort_keys=True) + "\n"
    if fmt != "text":
        raise ValueError(f"unknown format: {fmt!r}")

    return "\n".join(
        _render_header(evidence)
        + _render_measurements(evidence)
        + _render_skipped(evidence)
        + _render_reviewer_slot()
    )
