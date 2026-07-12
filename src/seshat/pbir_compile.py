"""PBIR blueprint-to-PBIR compiler (US7, ADR 0017 -- the creation primitive).

Orchestrates the FOUR shipped authoring adapters (theme/format/background/geometry
-- ``pbir_theme_apply.py`` / ``pbir_visual_format.py`` / ``pbir_page_background.py``
/ ``pbir_geometry.py``) and adds exactly ONE new capability those adapters
structurally refuse: creating a new **page** or **visual container** declared by an
APPROVED blueprint (ADR 0017, ratified). This module is NOT a fifth peer adapter --
it is the orchestration layer that reuses their public functions and their
stage -> validate -> commit discipline; it adds no second formatting engine (theme,
per-visual formatting, and geometry stay owned by the four adapters, invoked on a
container this module created).

THE GATES THIS MODULE ENFORCES (fail-closed, never a self-grant):

1. **Approval gate** (FR-023/FR-025): compilation runs only against a
   ``dashboard_blueprint_approval`` decision whose ``status`` is ``approved``
   (a post-approval blueprint change is marked ``superseded`` per DS4 and must be
   re-approved -- FR-023/US7 AC#5), that is valid under the shared
   ``approval_is_valid`` predicate (the SAME oracle DS2 and the readiness gate use
   -- no second approval system), and whose cited evidence is not stale (reusing
   the decision gate's ``_evidence_stale`` oracle when a ``repo_root`` is given).
   A missing, non-``approved``, invalid, or stale approval blocks, naming it.

2. **Verified-sample gate** (FR-029, D10): an element type may be created ONLY if it
   has an entry in ``_VERIFIED_SAMPLES`` -- today exactly ``page_shell`` (the real
   Desktop-authored empty ``RetailStoreSales.Report`` page) and ``lineChart`` (the
   data-goblin ``visual_fmt.Report`` sample). Every other element type (KPI cards,
   column/bar charts, slicers, interactions) blocks naming the missing sample. The
   sample is used ONLY as the wire-format proof for the element's JSON shape -- its
   business content (bound entity/measure, title, filters) is NEVER copied; that
   would smuggle an orphan bind into the compiled output.

3. **Binding gate** (FR-027): a created visual binds ONLY to a field present on the
   caller-supplied ``binding_map`` (the approved ``visual-contract-binding-map.md``,
   already parsed by the caller into ``{binding_key: {bound_contract, measures,
   dimensions}}``). A ``binding_key`` absent from the map blocks as an orphan bind.

4. **Deterministic ID minting** (FR-027/US7#4): every created page/visual ``name`` is
   ``mint_element_id(report_id, slug)`` -- a truncated SHA-256 digest, NEVER
   random/time-based. Identical inputs mint identical ids on every rerun.

5. **No partial write** (D13): the compiler stages the COMPLETE file tree in a temp
   copy of the report directory, validates the whole batch, then moves the temp copy
   over the real report directory only after every check passes. On any failure
   (gate or validation) nothing under the real report directory changes -- the
   recovery net is simply retrying, never a manual ``git checkout``.

6. **FR-003 inherited**: whenever an existing visual is touched (not the case for the
   two increments here, which only CREATE), the query/visualType snapshot guard from
   the shipped adapters applies unchanged.

No pbi-cli, no live Power BI, no network -- stdlib json/pathlib/shutil/hashlib only.
Grants no readiness pass, emits no score, never publishes (FR-036).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .decision_gate import _evidence_stale
from .decision_store import approval_is_valid

_ID_DIGEST_LEN = 20  # matches the real samples' observed name width (20 hex chars)

# The per-increment creation allow-list (ADR 0017 clause 3 / D10). Only element
# types with a VERIFIED Desktop-authored reference sample may be created. Adding an
# entry here requires a real sample landing under tests/fixtures/pbir/ first --
# never the tests/fixtures/pbir/geometry.Report placeholder (schema 1.0.0,
# Entity: "placeholder"), which was never held to this bar.
_VERIFIED_SAMPLES: frozenset[str] = frozenset({"page_shell", "lineChart"})

_PAGE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/page/2.1.0/schema.json"
)
_VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.2.0/schema.json"
)


class PbirCompileError(Exception):
    """A compilation input/gate/output problem surfaced cleanly (never a traceback)."""


def mint_element_id(report_id: str, slug: str) -> str:
    """Deterministic page/visual ``name``: truncated SHA-256 of ``report_id+slug``.

    NEVER random/time-based (FR-027/US7#4) -- identical inputs always mint the same
    id, on this run and every future rerun."""
    digest = hashlib.sha256(f"{report_id}{slug}".encode("utf-8")).hexdigest()
    return digest[:_ID_DIGEST_LEN]


def _dump(doc: object) -> str:
    """Deterministic JSON text: stable key order, 2-space indent, trailing NL."""
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def _require_verified_sample(element_type: str) -> None:
    if element_type not in _VERIFIED_SAMPLES:
        raise PbirCompileError(
            f"{element_type!r} has no verified reference sample "
            f"(verified today: {sorted(_VERIFIED_SAMPLES)}) -- compilation blocked, "
            f"writing nothing; supply a real Power BI Desktop-authored sample "
            f"before this element type can be created"
        )


def _require_valid_approval(
    approval: dict[str, Any] | None,
    authority: dict[str, frozenset[str]] | None,
    repo_root: Path | str | None = None,
) -> None:
    """Fail closed unless ``approval`` is an ``approved``, valid, non-stale
    ``dashboard_blueprint_approval`` decision.

    Three gates, in order (each names the reason it blocks, FR-034):

    1. **Status** (FR-023 / US7 AC#5): only ``status == "approved"`` may compile.
       A blueprint changed after approval is marked ``superseded`` (DS4), and a
       ``rejected`` / ``pending`` / ``proposed`` decision is not an approval --
       every non-``approved`` status BLOCKS until a renewed approval lands.
       ``approval_is_valid`` validates the approval *block* but never reads
       ``status``, so this check is what closes the FR-023 hole.
    2. **Validity**: the shared ``approval_is_valid`` predicate (the SAME oracle
       DS2 and the readiness gate use -- an agent identity never satisfies
       ``approved_by``).
    3. **Staleness** (research R-10): when a ``repo_root`` is supplied, reuse the
       decision gate's ``_evidence_stale`` oracle rather than forking it, so the
       compiler and the gate can never disagree on whether cited evidence still
       matches its recorded identity."""
    if approval is None:
        raise PbirCompileError(
            "no dashboard_blueprint_approval supplied -- compilation blocked "
            "(FR-025); a named report_owner must approve the blueprint first"
        )
    did = approval.get("id", "<no-id>")
    status = approval.get("status")
    if status != "approved":
        raise PbirCompileError(
            f"dashboard_blueprint_approval {did!r} has status {status!r}, not "
            f"'approved' -- compilation blocked (FR-023/US7 AC#5); a blueprint "
            f"changed after approval is superseded and must be re-approved before "
            f"it can compile"
        )
    ok, reason = approval_is_valid(approval, authority)
    if not ok:
        raise PbirCompileError(
            f"dashboard_blueprint_approval is not valid ({reason}) -- compilation "
            f"blocked (FR-025); an agent identity never satisfies approved_by"
        )
    if repo_root is not None:
        _require_fresh_evidence(did, approval.get("approval", {}), repo_root)


def _require_fresh_evidence(
    did: object, approval_block: dict[str, Any], repo_root: Path | str
) -> None:
    """Block when cited evidence is stale/missing, reusing the decision gate's
    ``_evidence_stale`` oracle so the compiler and gate never disagree (FR-023)."""
    stale = _evidence_stale(repo_root, approval_block)
    if stale:
        raise PbirCompileError(
            f"dashboard_blueprint_approval {did!r} cites stale/missing evidence "
            f"{stale} -- compilation blocked (FR-023); the blueprint's approved "
            f"evidence changed since sign-off and must be re-approved first"
        )


def _require_mapped_binding(
    binding_map: dict[str, Any], binding_key: str
) -> dict[str, Any]:
    entry = binding_map.get(binding_key)
    if not isinstance(entry, dict):
        raise PbirCompileError(
            f"binding key {binding_key!r} is not on the approved binding-map -- "
            f"refusing to create an orphan-bound visual (FR-027); route upstream "
            f"to the visual-contract-binding-map review"
        )
    return entry


class _StagedBatch:
    """A temp copy of a report directory that writes accumulate onto.

    Nothing under the REAL report directory changes until ``commit()`` -- the
    multi-file atomicity D13 requires beyond the shipped single-file adapters."""

    def __init__(self, report_dir: Path) -> None:
        self.report_dir = report_dir
        self._tmp = Path(tempfile.mkdtemp(prefix="pbir_compile_"))
        self.staging_root = self._tmp / "staged"
        shutil.copytree(report_dir, self.staging_root)

    def write(self, rel_path: Path, text: str) -> None:
        target = self.staging_root / rel_path
        if not _within(self.staging_root, target):
            raise PbirCompileError(f"staged path escapes the report dir: {rel_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")

    def read_json(self, rel_path: Path) -> Any:
        target = self.staging_root / rel_path
        try:
            with target.open(encoding="utf-8-sig") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise PbirCompileError(
                f"{rel_path} could not be read as JSON ({exc.__class__.__name__})"
            ) from exc

    def commit(self, written_rel_paths: list[Path]) -> list[Path]:
        """Move the staged tree over the real report dir; return real written paths.

        Only called after the whole batch validates -- this is the one moment the
        real report directory changes."""
        _validate_staged_batch(self.staging_root)
        for rel in written_rel_paths:
            src = self.staging_root / rel
            dst = self.report_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        return [self.report_dir / rel for rel in written_rel_paths]

    def cleanup(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)


def _within(root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _validate_staged_batch(staging_root: Path) -> None:
    """Re-parse and round-trip every JSON file that was just written.

    A hook point tests may monkeypatch to inject a validation-phase failure and
    prove no-partial-write -- the real per-file check is: valid JSON, and
    re-dumping it is byte-identical (round-trip stability)."""
    for path in staging_root.rglob("*.json"):
        try:
            with path.open(encoding="utf-8-sig") as fh:
                doc = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise PbirCompileError(
                f"staged {path.name} is not valid JSON ({exc.__class__.__name__})"
            ) from exc
        text = _dump(doc)
        if _dump(json.loads(text)) != text:
            raise PbirCompileError(f"staged {path.name} is not round-trip stable")


def create_page(
    batch: _StagedBatch, *, report_id: str, page_slug: str, display_name: str
) -> tuple[str, list[Path]]:
    """Stage a new page (``page.json`` + a ``pages.json`` registration).

    Grounded in the verified real Desktop-authored empty-page shape (same
    ``$schema``, same top-level keys as ``powerbi/RetailStoreSales.Report``'s real
    page). Returns ``(page_name, written_rel_paths)``. Pure staging -- writes only
    into ``batch``'s temp copy, never the real report dir."""
    page_name = mint_element_id(report_id, page_slug)
    page_doc = {
        "$schema": _PAGE_SCHEMA,
        "name": page_name,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "height": 720,
        "width": 1280,
    }
    page_rel = Path("definition") / "pages" / page_name / "page.json"
    batch.write(page_rel, _dump(page_doc))

    pages_rel = Path("definition") / "pages" / "pages.json"
    pages_doc = batch.read_json(pages_rel)
    order = list(pages_doc.get("pageOrder", []))
    if page_name not in order:
        order.append(page_name)
    pages_doc["pageOrder"] = order
    batch.write(pages_rel, _dump(pages_doc))

    return page_name, [page_rel, pages_rel]


def _projection_field(kind: str, entity: str, prop: str, query_ref: str) -> dict:
    """One PBIR ``query.queryState`` projection entry (Column or Measure)."""
    return {
        "field": {
            kind: {
                "Expression": {"SourceRef": {"Entity": entity}},
                "Property": prop,
            }
        },
        "queryRef": query_ref,
        "nativeQueryRef": prop,
    }


def _split_table_field(dotted: str) -> tuple[str, str]:
    table, _, field = dotted.partition(".")
    if not table or not field:
        raise PbirCompileError(f"binding field {dotted!r} is not in 'table.field' form")
    return table, field


@dataclass(frozen=True)
class VisualBuildSpec:
    """The per-visual inputs ``create_visual_container`` needs, bundled into one
    value so the creation primitive takes a single spec rather than a long
    keyword-argument list. ``binding`` is one entry from the approved binding-map:
    ``{bound_contract, measures: ["table.field", ...], dimensions: [...]}``."""

    report_id: str
    page_name: str
    visual_slug: str
    visual_type: str
    binding: dict[str, Any]
    position: dict[str, Any]


def _query_state(binding: dict[str, Any]) -> dict[str, Any]:
    """The PBIR ``query.queryState`` (Category/Y projections) for a binding.

    Binds ONLY the approved binding's fields; raises if there is no measure to
    bind (refusing to create a data-less visual, FR-027)."""
    dimensions = binding.get("dimensions") or []
    measures = binding.get("measures") or []
    if not measures:
        raise PbirCompileError(
            f"binding {binding.get('bound_contract')!r} has no measures to bind -- "
            f"refusing to create a visual with no data (FR-027)"
        )
    query_state: dict[str, Any] = {}
    if dimensions:
        table, field = _split_table_field(dimensions[0])
        query_state["Category"] = {
            "projections": [_projection_field("Column", table, field, dimensions[0])]
        }
    query_state["Y"] = {
        "projections": [
            _projection_field("Measure", *_split_table_field(measure), measure)
            for measure in measures
        ]
    }
    return query_state


def create_visual_container(
    batch: _StagedBatch, spec: VisualBuildSpec
) -> tuple[str, list[Path]]:
    """Stage a new ``visual.json`` bound ONLY to the approved ``spec.binding``.

    The projection SHAPE (Column/Measure wrapper, queryState Category/Y layout) is
    grounded in the verified ``visual_fmt.Report`` lineChart sample -- but only the
    shape; the sample's own bound entity ("On-Time Delivery"), title, and filters
    are never copied (that would bind an orphan/unapproved field, FR-027). Returns
    ``(visual_name, written_rel_paths)``."""
    visual_name = mint_element_id(spec.report_id, spec.visual_slug)
    position = spec.position
    visual_doc = {
        "$schema": _VISUAL_SCHEMA,
        "name": visual_name,
        "position": {
            "x": position.get("x", 0),
            "y": position.get("y", 0),
            "z": position.get("z", 0),
            "width": position.get("width", 0),
            "height": position.get("height", 0),
            "tabOrder": position.get("tabOrder", position.get("z", 0)),
        },
        "visual": {
            "visualType": spec.visual_type,
            "query": {"queryState": _query_state(spec.binding)},
        },
    }
    visual_rel = (
        Path("definition")
        / "pages"
        / spec.page_name
        / "visuals"
        / visual_name
        / "visual.json"
    )
    batch.write(visual_rel, _dump(visual_doc))
    return visual_name, [visual_rel]


@dataclass(frozen=True)
class CompileContext:
    """The fail-closed gate inputs every compile entry point shares: the report
    directory to write into, the ``dashboard_blueprint_approval`` decision +
    authority map the approval gate checks, and an optional ``repo_root`` that
    enables the evidence-staleness leg (FR-023)."""

    report_dir: Path
    approval: dict[str, Any] | None
    authority: dict[str, frozenset[str]] | None
    repo_root: Path | str | None = None


@dataclass(frozen=True)
class PageShellRequest:
    """What ``compile_page_shell`` creates: one new page."""

    report_id: str
    page_slug: str
    display_name: str


@dataclass(frozen=True)
class LineChartRequest:
    """What ``compile_line_chart`` creates: one lineChart visual, bound to the
    approved binding-map entry found at ``binding_key``."""

    report_id: str
    page_name: str
    visual_slug: str
    visual_type: str
    binding_map: dict[str, Any]
    binding_key: str
    position: dict[str, Any]


def compile_page_shell(ctx: CompileContext, request: PageShellRequest) -> list[Path]:
    """Compile Increment 1 (page shells): create one new page, registered in order.

    Fails closed on an approval that is missing, not ``approved`` (FR-023/US7
    AC#5), invalid (FR-025), or -- when ``ctx.repo_root`` is supplied -- backed by
    stale evidence (FR-023), before touching anything. Grounded in the verified
    real Desktop-authored empty-page sample (D10). Stages the whole batch,
    validates it, and commits only if everything passes -- on any failure the real
    report_dir is untouched (D13)."""
    report_dir = Path(ctx.report_dir)
    _require_valid_approval(ctx.approval, ctx.authority, ctx.repo_root)
    _require_verified_sample("page_shell")

    batch = _StagedBatch(report_dir)
    try:
        _page_name, written = create_page(
            batch,
            report_id=request.report_id,
            page_slug=request.page_slug,
            display_name=request.display_name,
        )
        return batch.commit(written)
    finally:
        batch.cleanup()


def compile_line_chart(ctx: CompileContext, request: LineChartRequest) -> list[Path]:
    """Compile Increment 3's lineChart: create one visual bound to an approved field.

    Fails closed, in order, on: an approval that is missing, not ``approved``
    (FR-023/US7 AC#5), invalid (FR-025), or (with ``ctx.repo_root``) stale
    (FR-023); a visual_type with no verified sample (FR-029 -- only ``lineChart``
    today); a binding_key absent from the approved binding-map (FR-027, orphan
    bind). Grounded in the data-goblin ``visual_fmt.Report`` sample's wire format
    (D10); never copies that sample's own bound content. Same stage -> validate ->
    commit discipline as ``compile_page_shell``."""
    report_dir = Path(ctx.report_dir)
    _require_valid_approval(ctx.approval, ctx.authority, ctx.repo_root)
    _require_verified_sample(request.visual_type)
    binding = _require_mapped_binding(request.binding_map, request.binding_key)

    batch = _StagedBatch(report_dir)
    try:
        spec = VisualBuildSpec(
            report_id=request.report_id,
            page_name=request.page_name,
            visual_slug=request.visual_slug,
            visual_type=request.visual_type,
            binding=binding,
            position=request.position,
        )
        _visual_name, written = create_visual_container(batch, spec)
        return batch.commit(written)
    finally:
        batch.cleanup()
