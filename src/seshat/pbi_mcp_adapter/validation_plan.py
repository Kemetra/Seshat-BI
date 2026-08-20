"""Spec 149 -- which validators a write target implies, and why others did not run.

Pure selection: no subprocess, no git, no database. Separated from
:mod:`validation` for two reasons -- the rules can then be pinned exhaustively
without spawning a validator, and ``validation`` stays well clear of the
file-size gate.

The three questions answered here:

* **Which findings did THIS write introduce?** The corpus is repo-wide and
  cannot be narrowed (``semantic-check`` anchors discovery on ``git rev-parse
  --show-toplevel`` and refuses a subdirectory), so attribution is done by
  diffing rendered finding lines against a pre-write baseline rather than by
  scoping the inputs -- issue #663 gap 3.
* **Which reports could this write have broken?** The ones whose
  ``definition.pbir`` names the mutated model. Read from the artifact, never
  inferred from directory names -- issue #661 gap 1.
* **Is there a data leg to recompute approved values against?** Answered from
  the environment WITHOUT reading or returning any credential -- issue #661
  gap 2.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

#: The binding validator's name in ``checks_run`` / ``checks_skipped``.
BINDING_CHECK = "pbir-validate-bindings"

#: The value validator's name in ``checks_run`` / ``checks_skipped``.
VALUE_CHECK = "value-check"

#: The documented ways a data leg is configured (``docs/install/``). Presence is
#: all that is ever read -- never the value.
_DSN_KEYS = ("DATABASE_URL", "ANALYTICS_DB_HOST")


def finding_lines(stdout: str | None) -> frozenset[str]:
    """Every rendered finding in ``stdout``, as a comparable set.

    ``runner._format`` renders a finding as ``[severity] rule_id message
    (locator)``, so a leading ``[`` is what separates a finding from the
    command's own summary chatter. The WHOLE line is the identity key: it
    already carries severity, rule and locator, so two runs can be diffed
    without parsing any of them -- and a message that changes wording is
    correctly treated as a different finding rather than silently matched.

    ``None`` is accepted because a subprocess whose reader thread died returns
    ``stdout=None`` (issue #663); that must not raise here.
    """
    if not stdout:
        return frozenset()
    return frozenset(
        stripped
        for line in stdout.splitlines()
        if (stripped := line.strip()).startswith("[")
    )


def _referenced_model(report_dir: Path) -> Path | None:
    """The model a report's ``definition.pbir`` points at, or None if unreadable.

    Read from the artifact rather than inferred from directory names: a report
    and its model need not share a stem, so guessing would either miss a real
    pairing or invent one that does not exist.

    Fails CLOSED to None on anything unexpected -- absent file, bad JSON, a
    shape without the reference. The caller turns None into a recorded skip, so
    "cannot tell" never silently becomes "not paired".
    """
    try:
        document = json.loads(
            (report_dir / "definition.pbir").read_text(encoding="utf-8-sig")
        )
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict):
        return None
    reference = document.get("datasetReference")
    by_path = reference.get("byPath") if isinstance(reference, dict) else None
    path = by_path.get("path") if isinstance(by_path, dict) else None
    if not isinstance(path, str) or not path:
        return None
    try:
        return (report_dir / path).resolve()
    except (OSError, ValueError):
        return None


def paired_reports(
    repo_root: Path, model_dir: Path
) -> tuple[tuple[Path, ...], tuple[tuple[str, str], ...]]:
    """Reports in scope for a write to ``model_dir``, plus the ones we cannot place.

    A report is IN SCOPE when its ``definition.pbir`` names this model. A report
    whose pbir is missing or unreadable is neither paired nor ignored: it comes
    back as a recorded skip, because treating unknown pairing as "not paired"
    would silently hide a binding this write may have orphaned.
    """
    target = Path(model_dir).resolve()
    paired: list[Path] = []
    skipped: list[tuple[str, str]] = []
    for report_dir in sorted(Path(repo_root).glob("*.Report")):
        if not report_dir.is_dir():
            continue
        referenced = _referenced_model(report_dir)
        if referenced is None:
            skipped.append(
                (
                    BINDING_CHECK,
                    f"{report_dir.name}: definition.pbir is missing or unreadable, "
                    "so its model pairing is unknown",
                )
            )
            continue
        if referenced == target:
            paired.append(report_dir)
    return tuple(paired), tuple(skipped)


def dsn_is_available(env: Mapping[str, str]) -> bool:
    """Whether a data leg is configured.

    Reads presence only. The value is never returned, logged, or interpolated
    into a reason string -- reason strings reach evidence and stdout.
    """
    return any(env.get(key) for key in _DSN_KEYS)
