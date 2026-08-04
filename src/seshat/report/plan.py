"""A figure plan: which figures to render and how to format them, never their values.

This is the input `--from-gold` needs and the warehouse cannot supply. A table can
say what the revenue *is*; it cannot say that the board pack opens with revenue, or
that revenue is money rather than a count.

Domain logic rather than CLI plumbing, so it lives here: reading a plan, checking
it against the signed bindings, and loading the approved contracts are all
testable without argparse, and the command handler is left holding only the driver.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import yaml

from seshat.report.binding import BindingMap
from seshat.report.model import ReportError
from seshat.report.observe import FigureRequest
from seshat.report.reading import required_list


def load_figure_plan(path: Path) -> list[dict]:
    """Read the plan, refusing one that carries values.

    A plan is NOT an observations file with the numbers deleted. Discarding a
    stated value silently would leave an operator who reused a stale observations
    file believing those numbers had been checked against the warehouse.
    """
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ReportError(f"cannot read figure plan {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReportError(f"figure plan {path} is not a mapping")
    entries = required_list(payload, "figures", refusal=f"{path} declares no figures")
    figures = [entry for entry in entries if isinstance(entry, dict)]
    _assert_valueless(figures, path)
    return figures


def _assert_valueless(figures: Sequence[dict], path: Path) -> None:
    for entry in figures:
        if entry.get("value") is not None:
            raise ReportError(
                f"{path} figure {entry.get('visual_id')!r} carries a value. A figure "
                "plan states what to render; --from-gold supplies every value, so "
                "this one would be discarded. Remove it, or drop --from-gold and use "
                "--observations."
            )


def figure_requests(
    figures: Sequence[dict], binding_map: BindingMap
) -> list[FigureRequest]:
    """Each plan entry as a request, with its citation taken from the signed map."""
    return [_request(entry, binding_map) for entry in figures]


def _request(entry: dict, binding_map: BindingMap) -> FigureRequest:
    """One request. The plan does not get to choose the contract.

    Which contract a visual cites is the design review's decision, so it is read
    from the signed binding map. A plan may omit it; a plan that states a
    DIFFERENT one is refused rather than overridden, because a silent override
    leaves the operator believing the citation they wrote is the one on the page.
    """
    visual_id = str(entry.get("visual_id") or "")
    governed = binding_map.contract_for(visual_id)
    declared = entry.get("contract_id")
    if declared is not None and str(declared) != governed:
        raise ReportError(
            f"figure plan binds visual {visual_id!r} to {declared!r}, but the approved "
            f"binding map binds it to {governed!r}. The design review decides the "
            "citation; fix the plan or have the design re-reviewed."
        )
    label = entry.get("label")
    return FigureRequest(
        visual_id=visual_id,
        contract_id=governed,
        unit_kind=str(entry.get("unit_kind") or ""),
        label=str(label) if label is not None else None,
    )


def contract_payloads(repo_root: Path, table: str) -> dict[str, dict]:
    """Every approved contract for the table, parsed.

    An unreadable contract refuses rather than being skipped: a skipped contract
    would make its figure look unattributable, which reads as a design fault
    rather than a broken file.
    """
    payloads: dict[str, dict] = {}
    for path in sorted((repo_root / "mappings" / table / "metrics").glob("*.yaml")):
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ReportError(f"cannot read contract {path}: {exc}") from exc
        if isinstance(loaded, dict):
            payloads[path.stem] = loaded
    return payloads
