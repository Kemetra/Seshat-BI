"""#488's deferred half: signpost the canonical source-map shape EARLY.

`source-map.yaml`'s canonical shape is enforced only by `seshat validate`, at Gold
Ready -- so a map hand-authored at Mapping Ready survives the whole silver/gold
build and fails four stages later as a CLI error.

A fail-closed shape rule at Mapping Ready is NOT landable, and the census pinned
below is why: `demo_sample_orders` is a committed gate artifact whose map has
`gold_star` but no `meta`, with `gold_star.fact` a bare STRING where the canonical
shape has a mapping. Any required-shape rule -- and even a present-only structural
one -- would fire on main's own artifact. So only the SIGNPOSTING half shipped:
`next` names the shape while the map is still being written.

The census tests here pass on the pre-fix tree by design. They pin existing ground
truth, and exist to FAIL if that ground truth ever changes -- at which point the
rejected half becomes worth revisiting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.unit._next_guidance_fixtures import (
    GUIDANCE_KEYS as _GUIDANCE_KEYS,
)
from tests.unit._next_guidance_fixtures import (
    REPO_ROOT as _REPO_ROOT,
)
from tests.unit._next_guidance_fixtures import (
    document as _document,
)
from tests.unit._next_guidance_fixtures import (
    write_status as _write_status,
)

pytestmark = pytest.mark.unit


def test_next_signposts_the_canonical_source_map_shape_at_the_mapping_gate(
    tmp_path: Path,
) -> None:
    """#488's second suggested direction: name the shape while the map is authored,
    so it is not discovered as a CLI error four stages later at Gold Ready."""
    _write_status(tmp_path, "orders", "mapping_ready")

    signpost = _document(tmp_path)["source_map_shape_signpost"]

    assert signpost is not None
    assert "scaffold-source" in signpost
    assert "source-map.yaml" in signpost


# Only Mapping Ready may carry an author/repair imperative for source-map.yaml.
# Every later stage is POST-APPROVAL: a named human signed off on that artifact, so
# an unqualified "repair the map" there would mutate an approved input with no gate
# reset and no re-approval -- routing around never_self_grant_approval by changing
# WHAT WAS APPROVED rather than by claiming an approval (PR #506 review, P1).
_SIGNPOST_STAGES: dict[str, bool] = {
    "source_ready": False,
    "mapping_ready": True,
    "silver_ready": False,
    "gold_ready": False,
    "semantic_model_ready": False,
    "dashboard_ready": False,
    "publish_ready": False,
}


def test_repair_signpost_is_emitted_at_mapping_ready_only() -> None:
    """P1 governance guard: pins exactly which stages may carry the imperative."""
    from seshat.agent_next import _source_map_shape_signpost

    for stage, expected in _SIGNPOST_STAGES.items():
        emitted = _source_map_shape_signpost(stage) is not None
        assert emitted is expected, f"{stage}: emitted={emitted}, expected={expected}"
    assert _source_map_shape_signpost(None) is None


@pytest.mark.parametrize(
    "stage", [s for s, emitted in _SIGNPOST_STAGES.items() if not emitted]
)
def test_no_post_approval_stage_invites_editing_the_approved_map(
    tmp_path: Path, stage: str
) -> None:
    """End-to-end: no authoring imperative reaches a post-approval document.

    Asserted on the whole document, not just the signpost field, so the imperative
    cannot reappear via some other guidance channel.
    """
    _write_status(tmp_path, "orders", stage)

    document = _document(tmp_path)

    assert document["source_map_shape_signpost"] is None
    guidance = "\n".join(
        str(document[key]) for key in _GUIDANCE_KEYS if document.get(key)
    )
    for imperative in ("Author source-map.yaml", "repair source-map.yaml"):
        assert imperative not in guidance, f"{stage}: {imperative!r} leaked"


def test_agent_mode_doc_describes_the_signpost_as_mapping_only() -> None:
    """PR #506 review P2: the doc said "mapping/silver" after the P1 narrowed it.

    A host following the documented contract would have waited at Silver for
    guidance that never arrives -- or worse, read Silver as a map-authoring stage,
    which is the very thing the P1 fix forbids. The earlier doc test only checked
    that the KEYS were documented, not their stage scope; this closes that gap.
    """
    doc = (_REPO_ROOT / "docs" / "agent-mode.md").read_text(encoding="utf-8")

    assert "Mapping Ready only" in doc
    assert "mapping/silver stages" not in doc
    # The reason must travel with the scope, or the null reads as an omission.
    assert "re-entering that gate" in doc
    assert "do not treat Silver as a map-authoring stage" in doc

    # And the doc's claim matches the code, stage by stage.
    emitting = [stage for stage, emitted in _SIGNPOST_STAGES.items() if emitted]
    assert emitting == ["mapping_ready"]


def test_the_mapping_signpost_warns_that_the_map_becomes_immutable() -> None:
    """The reader must learn the shape decision is final at the gate.

    Naming the shape is only half the point; if the map can be quietly edited after
    approval the gate means nothing, so the signpost says so where it is emitted.
    """
    from seshat.agent_next import _source_map_shape_signpost

    signpost = _source_map_shape_signpost("mapping_ready")

    assert signpost is not None
    assert "re-entering Mapping Ready" in signpost
    assert "named-human approval" in signpost


def test_hint_names_the_nested_fields_not_just_the_top_level_sections() -> None:
    """PR #506 review P2: naming only `meta` + `gold_star` was not actionable.

    A reader who added a bare `meta:`/`gold_star:` still discovered
    `gold_star.fact.name` as a CLI error at Gold Ready -- the exact late discovery
    #488 is about. The hint must name the nested fields the loader really reads.
    """
    from seshat.validate_targets import (
        CANONICAL_SOURCE_MAP_SHAPE_HINT,
        REQUIRED_NESTED_FIELDS,
    )

    assert "gold_star.fact.name" in REQUIRED_NESTED_FIELDS
    for field in REQUIRED_NESTED_FIELDS:
        assert field in CANONICAL_SOURCE_MAP_SHAPE_HINT, field


def test_every_named_nested_field_is_really_required_by_the_loader(
    tmp_path: Path,
) -> None:
    """Under-claim discipline: the hint may not demand a field the loader ignores.

    Each named field is removed from an otherwise-complete map; the loader must
    reject it and name that field. A field that can be dropped without error would
    be an over-claim and fails here.
    """
    from seshat.validate_targets import REQUIRED_NESTED_FIELDS, load_targets

    def _complete() -> dict[str, Any]:
        return {
            "meta": {"table_id": "orders", "primary_key": ["order_id"]},
            "gold_star": {
                "fact": {"name": "fct_orders", "measures": ["amount"]},
                "dimensions": [{"name": "dim_store", "surrogate_key": "store_sk"}],
                "date_dimension": {"name": "dim_date", "surrogate_key": "date_sk"},
            },
        }

    def _drop(document: dict[str, Any], dotted: str) -> dict[str, Any]:
        cursor: Any = document
        parts = dotted.split(".")
        for part in parts[:-1]:
            cursor = cursor[part.removesuffix("[]")]
            if isinstance(cursor, list):
                cursor = cursor[0]
        del cursor[parts[-1]]
        return document

    def _load(payload: dict[str, Any]) -> Any:
        path = tmp_path / "source-map.yaml"
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        return load_targets(path)

    # Positive control: the complete map loads, so each failure below is caused by
    # the dropped field and not by an unrelated defect in the fixture.
    assert _load(_complete()) is not None

    for field in REQUIRED_NESTED_FIELDS:
        with pytest.raises(ValueError, match=field.split(".")[-1]):
            _load(_drop(_complete(), field))


def test_hint_gives_a_non_destructive_route_for_an_already_authored_map(
    tmp_path: Path,
) -> None:
    """PR #506 review P2: `scaffold-source` cannot repair an EXISTING bad map.

    `_write_if_absent` keeps every file already present, so in #488's own scenario
    the bad map is merely reported as "kept" and the reader is stuck. The hint must
    say so, and must route the reader somewhere that needs no cleanup.
    """
    from seshat.stage1_scaffold import scaffold_source
    from seshat.validate_targets import (
        CANONICAL_SOURCE_MAP_SHAPE_HINT,
        REQUIRED_NESTED_FIELDS,
    )

    # The hint is honest about the limitation...
    assert "will NOT rewrite it" in CANONICAL_SOURCE_MAP_SHAPE_HINT
    assert "cannot repair a map" in CANONICAL_SOURCE_MAP_SHAPE_HINT
    # ...and routes to an IN-PLACE comparison, materializing no extra directory.
    assert "in place" in CANONICAL_SOURCE_MAP_SHAPE_HINT
    for field in REQUIRED_NESTED_FIELDS:
        assert field in CANONICAL_SOURCE_MAP_SHAPE_HINT, field

    # The limitation is real: an existing map is kept, not corrected.
    existing = tmp_path / "mappings" / "orders"
    existing.mkdir(parents=True)
    (existing / "source-map.yaml").write_text("grain: one line\n", encoding="utf-8")
    report = scaffold_source(tmp_path, "orders")
    assert "mappings/orders/source-map.yaml" in report.kept
    assert (existing / "source-map.yaml").read_text(encoding="utf-8").strip() == (
        "grain: one line"
    )


# Destructive verbs across the shells this repo supports. Emitted guidance is
# COPYABLE, and `mappings/<name>/` may hold a real table's source-map.yaml,
# source-profile.md, readiness-status.yaml and approvals -- so no delete instruction
# may target it, qualified or otherwise (PR #506 review, P2).
_DESTRUCTIVE_TOKENS = (
    "rm ",
    "rm -",
    "rmdir",
    "Remove-Item",
    "del ",
    "erase ",
    "unlink ",
    "delete",
    "Delete",
    "DELETE",
)


def test_emitted_guidance_never_instructs_a_delete(tmp_path: Path) -> None:
    """A copyable destructive command with a caveat is still destructive.

    The earlier repair route said "delete that reference folder". Because
    `scaffold-source` is non-destructive, a colliding folder name would keep a real
    table's artifacts -- and the delete would then destroy someone else's work. The
    instruction is gone entirely rather than qualified: the required fields are
    listed in the hint itself, so nothing has to be materialized or cleaned up.

    Asserted across EVERY guidance surface, not just the hint, so the instruction
    cannot reappear through the signpost or the checkpoint.
    """
    from seshat.cli.commands.next_guidance_render import guidance_lines
    from seshat.validate_targets import CANONICAL_SOURCE_MAP_SHAPE_HINT

    surfaces = {"hint": CANONICAL_SOURCE_MAP_SHAPE_HINT}
    for stage in ("mapping_ready", "silver_ready", "gold_ready", "source_ready"):
        root = tmp_path / stage
        _write_status(root, "t0", stage)
        _write_status(root, "t1", stage)
        surfaces[stage] = "\n".join(guidance_lines(_document(root)))

    for name, text in surfaces.items():
        for token in _DESTRUCTIVE_TOKENS:
            assert token not in text, f"{name}: destructive instruction {token!r}"
        # And no scratch directory is proposed under the real table namespace.
        assert "_canonical_reference" not in text, name


def test_signpost_quotes_the_one_hint_owned_by_the_enforcing_module() -> None:
    """The whole point of #488 is that the shape is enforced in ONE place and
    described elsewhere. Both descriptions must quote that one place, or they drift
    apart again -- the same shared-hint fix #487 used for approvals."""
    from seshat.agent_next import _source_map_shape_signpost
    from seshat.validate_targets import CANONICAL_SOURCE_MAP_SHAPE_HINT

    signpost = _source_map_shape_signpost("mapping_ready")

    assert signpost is not None
    assert CANONICAL_SOURCE_MAP_SHAPE_HINT in signpost


def test_shared_hint_names_exactly_the_keys_the_loader_requires(tmp_path: Path) -> None:
    """Guard the hint against over-claiming -- the prose-under-claim discipline.

    `load_targets` requires `meta` and `gold_star`. `columns` is read by OTHER
    consumers (drift / PII / currency) and never by this loader, so the hint must
    not present it as required. PR #495's inlined message said "meta + columns +
    gold_star", which over-claimed; the shared constant states it precisely.

    Both directions are checked: every declared-required key IS required (dropping
    it raises, naming that key), and `columns` is NOT (a map without it loads).
    """
    from seshat.validate_targets import (
        CANONICAL_SOURCE_MAP_SHAPE_HINT,
        REQUIRED_TOP_LEVEL_KEYS,
        load_targets,
    )

    for key in REQUIRED_TOP_LEVEL_KEYS:
        assert key in CANONICAL_SOURCE_MAP_SHAPE_HINT

    complete = {
        "meta": {"table_id": "orders", "primary_key": ["order_id"]},
        "gold_star": {
            "fact": {"name": "fct_orders", "measures": ["amount"]},
            "dimensions": [{"name": "dim_store", "surrogate_key": "store_sk"}],
            "date_dimension": {"name": "dim_date", "surrogate_key": "date_sk"},
        },
    }

    def _load(payload: dict[str, Any]) -> Any:
        path = tmp_path / "source-map.yaml"
        path.write_text(yaml.safe_dump(payload), encoding="utf-8")
        return load_targets(path)

    # `columns` absent -> still loads. It is genuinely NOT required here.
    assert _load(complete) is not None
    assert "columns" not in complete

    for key in REQUIRED_TOP_LEVEL_KEYS:
        with pytest.raises(ValueError, match=key):
            _load({k: v for k, v in complete.items() if k != key})


def test_validate_load_failure_quotes_the_same_shared_hint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`seshat validate`'s late error and `next`'s early signpost must agree."""
    from seshat.cli import main
    from seshat.validate_targets import CANONICAL_SOURCE_MAP_SHAPE_HINT

    bad_map = tmp_path / "source-map.yaml"
    bad_map.write_text("this: [is not: a valid map\n", encoding="utf-8")

    main(["validate", "--repo", str(tmp_path), "--source-map", str(bad_map)])
    err = capsys.readouterr().err

    # Only assert once the load actually failed; some environments short-circuit
    # earlier (no db extra / no DSN), and then there is nothing to assert.
    if "could not load source-map" in err:
        assert CANONICAL_SOURCE_MAP_SHAPE_HINT in err


def test_committed_maps_would_defeat_a_blanket_shape_rule() -> None:
    """Pins the census that rules out #488's fail-closed half.

    `demo_sample_orders` is a REAL committed gate artifact (six `pass` stages), not
    a disposable fixture -- and its map has `gold_star` but NO `meta`, with
    `gold_star.fact` a bare STRING where the canonical shape has a mapping. So a
    required-shape rule at Mapping Ready would fire on main's own artifact, and
    even a PRESENT-ONLY structural rule on `gold_star` would too. Neither can be
    <no-finding> on main, which is why only the signposting half shipped.

    If a future change makes this census false (e.g. the demo map gains `meta`),
    this test fails -- and the fail-closed half becomes worth revisiting.
    """
    demo = yaml.safe_load(
        (_REPO_ROOT / "mappings" / "demo_sample_orders" / "source-map.yaml").read_text(
            encoding="utf-8"
        )
    )
    canonical = yaml.safe_load(
        (_REPO_ROOT / "mappings" / "retail_store_sales" / "source-map.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert "meta" not in demo, "demo_sample_orders gained `meta`; revisit #488's rule"
    assert "gold_star" in demo
    assert isinstance(demo["gold_star"]["fact"], str), (
        "the demo map's gold_star.fact is no longer a bare string; a present-only "
        "structural rule may now be landable -- revisit #488"
    )
    # The canonical shape, for contrast: `fact` is a mapping with a `name`.
    assert isinstance(canonical["gold_star"]["fact"], dict)
    assert "meta" in canonical


def test_demo_sample_orders_is_a_signed_gate_artifact_not_a_fixture() -> None:
    """Why the census above is decisive rather than fixable: this table's readiness
    file records real passes, so its map cannot be edited to suit a new rule."""
    status = yaml.safe_load(
        (
            _REPO_ROOT / "mappings" / "demo_sample_orders" / "readiness-status.yaml"
        ).read_text(encoding="utf-8")
    )

    passes = {
        name
        for name, block in status["stages"].items()
        if isinstance(block, dict) and block.get("status") == "pass"
    }
    # Measured, not assumed: this artifact records passes THROUGH Silver, and its
    # mapping_ready pass is exactly the one a Mapping-Ready shape rule would have
    # had to reject.
    assert {"source_ready", "mapping_ready", "silver_ready"} <= passes, passes
    assert status["stages"]["mapping_ready"]["status"] == "pass"
