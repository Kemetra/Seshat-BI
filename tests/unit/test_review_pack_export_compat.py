"""US4 backwards-compatibility tests for the review pack exporter (spec 081)."""

import inspect

import pytest

from seshat.review_pack_export import Pack, Section

pytestmark = pytest.mark.unit


def test_v1_0_consumer_fields_survive_a_minor_bump():
    """T018: every field a "1.0" consumer reads is present + unchanged in a "1.1" doc.

    Simulates the additive-only MINOR bump from backwards-compat-example.md: the
    "1.1" doc adds one OPTIONAL field, and a "1.0" consumer ignoring the unknown
    field still finds every field it was written against.
    """
    from seshat.review_pack_export import to_json

    v10 = to_json(
        Pack(
            schema_version="1.0",
            title="<TABLE>: <STAGE> review pack",
            source_note="composed by <producer>, <date>",
            sections=(
                Section(name="Gate requirement", status="pass", evidence=("e",)),
            ),
        )
    )
    # A "1.1" document = the same doc plus one added optional field on the section.
    v11 = {**v10, "schema_version": "1.1"}
    v11["sections"] = [{**v10["sections"][0], "owner_hint": "<role, informational>"}]

    # The "1.0" consumer contract names these keys; all must survive unchanged.
    v10_pack_keys = {
        "schema_version",
        "title",
        "generated_at",
        "source_note",
        "sections",
    }
    v10_section_keys = {"name", "status", "evidence", "blocking_reasons", "note"}

    assert v10_pack_keys.issubset(v11.keys())
    for k in v10_section_keys:
        # note None -> may be omitted; the rest must be present + equal
        if k in v10["sections"][0]:
            assert v11["sections"][0][k] == v10["sections"][0][k]
    # the unknown field is present; a "1.0" consumer simply ignores it
    assert v11["sections"][0]["owner_hint"] == "<role, informational>"


def test_module_docstring_states_additive_only_rule():
    """T019: the additive-only rule lives adjacent to the code for future editors."""
    import seshat.review_pack_export as mod

    doc = (inspect.getdoc(mod) or "").lower()
    assert "additive" in doc
    assert "major" in doc and "minor" in doc
