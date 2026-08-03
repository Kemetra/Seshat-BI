"""The governed answer to "which contract does this visual cite?".

Increment A took that answer from the same operator-written file that supplied the
numbers, which made a whole class of wrong report look right: pair the revenue
card with the discount-rate contract and the page renders, cites a real approved
contract, and is false in a way no reader could detect.

The answer already exists in a signed artifact.
``mappings/<table>/design/visual-contract-binding-map.md`` carries a fenced
``seshat.binding-map/v1`` front section -- a FROZEN schema -- and it is the
artifact the design review signs off. So it is read here and treated as
authoritative, and a report accepts no other answer.

**Only two fields are consumed:** ``visual_id`` and ``contract``. The committed
map records its front section as awaiting owner re-sign under issue #514 (D5);
what is unratified there is the ``decision_questions`` leg, which reports do not
read, and the two fields below are identical in the front section and in the
signed prose table. This module therefore does not depend on the unratified part
and does not resolve D5.

**The prose table is not a fallback.** It is a review artifact for humans, and
recovering bindings from markdown pipes would mean a report's citations came from
whichever of two representations happened to parse. A file with no front section
refuses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from seshat.report.model import ReportError
from seshat.report.reading import required_list, required_mapping, required_text

BINDING_MAP_SCHEMA = "seshat.binding-map/v1"
BINDING_MAP_NAME = "visual-contract-binding-map.md"

# Fenced yaml blocks, in document order. The front section is identified by its
# `schema` value rather than by position, so prose or a comment above it -- both
# present in the committed artifact -- cannot displace it.
_FENCE = re.compile(r"^```ya?ml[ \t]*\n(.*?)^```[ \t]*$", re.M | re.S)


@dataclass(frozen=True, slots=True)
class VisualBinding:
    """One measure-bearing visual and the single approved contract behind it."""

    visual_id: str
    contract: str
    page: str | None = None
    headline: bool = False


@dataclass(frozen=True, slots=True)
class BindingMap:
    table: str
    bindings: tuple[VisualBinding, ...]

    @property
    def visual_ids(self) -> tuple[str, ...]:
        return tuple(binding.visual_id for binding in self.bindings)

    def binding_for(self, visual_id: str) -> VisualBinding:
        for binding in self.bindings:
            if binding.visual_id == visual_id:
                return binding
        raise ReportError(
            f"visual {visual_id!r} is not bound in the approved binding map for "
            f"{self.table!r}. A report cites what the design review signed off, so "
            "an unbound visual cannot appear -- bind it and have the design "
            "re-reviewed, or remove it from the layout."
        )

    def contract_for(self, visual_id: str) -> str:
        return self.binding_for(visual_id).contract


def binding_map_path(repo_root: Path, table: str) -> Path:
    return repo_root / "mappings" / table / "design" / BINDING_MAP_NAME


def load_binding_map(path: Path, *, expect_table: str | None = None) -> BindingMap:
    """Read the front section, or refuse.

    ``expect_table`` guards against rendering one table from another's approved
    bindings -- a mistake that would otherwise produce a fully-cited, entirely
    wrong document.
    """
    front = _front_section(path)
    table = str(front.get("table") or "")
    if expect_table is not None and table != expect_table:
        raise ReportError(
            f"{path} binds {table!r}, not {expect_table!r}; a report cannot take its "
            "bindings from another table's approved design"
        )
    return BindingMap(table=table, bindings=_bindings(front, path))


def _front_section(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReportError(f"no binding map at {path}: {exc}") from exc
    for block in _FENCE.findall(text):
        parsed = _parsed(block)
        if parsed.get("schema") == BINDING_MAP_SCHEMA:
            return parsed
    raise ReportError(
        f"{path} carries no {BINDING_MAP_SCHEMA} front section. The prose table is a "
        "review artifact, not a machine-readable source, so there is nothing to read "
        "bindings from."
    )


def _parsed(block: str) -> dict:
    """A fenced block, or an empty mapping when it is not one.

    A malformed or non-mapping block is skipped rather than raised on: a markdown
    file may legitimately fence yaml that is not this schema, and the refusal that
    matters -- no front section at all -- is raised by the caller.
    """
    try:
        loaded = yaml.safe_load(block)
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _bindings(front: dict, path: Path) -> tuple[VisualBinding, ...]:
    raw = required_list(front, "visuals", refusal=f"{path} declares no visuals")
    bindings: list[VisualBinding] = []
    seen: set[str] = set()
    for entry in raw:
        binding = _binding(entry, path)
        if binding.visual_id in seen:
            raise ReportError(
                f"{path} declares {binding.visual_id!r} twice; the map has to decide "
                "which contract a visual cites, and a last-one-wins read would pick "
                "a citation silently"
            )
        seen.add(binding.visual_id)
        bindings.append(binding)
    return tuple(bindings)


def _binding(entry: object, path: Path) -> VisualBinding:
    visual = required_mapping(entry, refusal=f"{path} has a non-mapping visual entry")
    visual_id = required_text(
        visual, "visual_id", refusal=f"{path} has a visual with no visual_id"
    )
    page = visual.get("page")
    return VisualBinding(
        visual_id=visual_id,
        contract=required_text(
            visual,
            "contract",
            refusal=(
                f"{path} visual {visual_id!r} has no contract; an unattributed visual "
                "cannot be rendered"
            ),
        ),
        page=page if isinstance(page, str) else None,
        headline=visual.get("headline") is True,
    )
