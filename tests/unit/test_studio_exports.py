"""Phase A/D -- the disclosure boundary (spec 141).

Every artifact leaving Studio passes through `exports.py`. The claims under test:

- an allowlist keeps only named fields, so a field added upstream later is absent by
  default rather than disclosed until someone notices (FR-141-012);
- allowlisting a FIELD does not bless its CONTENT -- both redaction layers still run
  (FR-141-008);
- a narrative adds no claim absent from its selection (FR-141-022);
- acknowledgement cannot carry a ruling (FR-141-011);
- a bundle excludes secrets structurally, and a failed scan leaves NO artifact
  (FR-141-013, FR-141-014).
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seshat.studio import exports  # noqa: E402

pytestmark = pytest.mark.unit

#: Assembled from parts on purpose. A literal DSN in a committed file trips the repo's
#: own C2 secret scanner (`CONN_URI_RE`), and rightly so -- a scanner that recognised
#: "obviously fake" credentials would be one heuristic from passing a real one.
#: `rules/git_meta.py:547` builds its scheme the same way, for the same reason.
_SCHEME = "postgres" + "ql://"
FAKE_DSN = _SCHEME + "u:p@h/db"


# --- Task A4: the allowlist scrubber -------------------------------------------------


def test_only_allowlisted_fields_survive(tmp_path: Path):
    payload = {"metric": "net_sales", "dsn": FAKE_DSN, "note": "ok"}

    result = exports.scrub_for_export(
        payload, allowed=("metric", "note"), workspace_root=tmp_path
    )

    assert result == {"metric": "net_sales", "note": "ok"}


def test_a_field_added_upstream_is_absent_without_changing_export_code(tmp_path: Path):
    """O2: an allowlist fails CLOSED. A denylist would disclose this new field."""
    payload = {"metric": "net_sales", "secret_added_later": "sk-live-abcd1234"}

    result = exports.scrub_for_export(
        payload, allowed=("metric",), workspace_root=tmp_path
    )

    assert "secret_added_later" not in result


def test_an_allowlisted_value_is_still_scrubbed(tmp_path: Path):
    """Allowlisting a FIELD does not bless its CONTENT: both layers still run."""
    payload = {"note": f"connect via {FAKE_DSN} to check"}

    result = exports.scrub_for_export(
        payload, allowed=("note",), workspace_root=tmp_path
    )

    assert _SCHEME not in result["note"]
    assert "u:p@h" not in result["note"]


def test_there_is_no_denylist_shaped_entry_point():
    """A "scrub everything except" helper would reintroduce the fail-open."""
    names = [n for n in dir(exports) if not n.startswith("_")]

    assert not [n for n in names if "denylist" in n.lower() or "exclude" in n.lower()]


def test_allowed_is_required_with_no_default():
    """A default allowlist is a default disclosure. Absent must be a TypeError."""
    with pytest.raises(TypeError):
        exports.scrub_for_export({"a": 1}, workspace_root=Path("."))  # type: ignore[call-arg]


# --- Task D2: the narrative adds no claim -------------------------------------------


def test_the_narrative_contains_only_selected_facts():
    draft = exports.build_narrative(
        selected_facts=("net sales is reported net of returns",),
        pending_items=("margin definition awaiting sign-off",),
    )

    assert "net of returns" in draft
    assert "margin definition" in draft, "pending items must be VISIBLE, not dropped"


def test_a_pending_item_is_not_described_as_approved():
    draft = exports.build_narrative(
        selected_facts=(), pending_items=("margin definition awaiting sign-off",)
    )

    assert "approved" not in draft.lower()
    assert "pending" in draft.lower()


def test_an_empty_selection_produces_no_claims():
    """A narrative with nothing selected must not invent a summary."""
    draft = exports.build_narrative(selected_facts=(), pending_items=())

    assert "approved" not in draft.lower()
    assert "complete" not in draft.lower()


# --- Task D3: acknowledgement is not approval ---------------------------------------


def test_acknowledgement_cannot_carry_a_ruling():
    """FR-141-011 as a type constraint: the two cannot collapse."""
    fields = {f.name for f in dataclasses.fields(exports.ClientAcknowledgment)}

    assert not fields & {"answer", "approval", "decision", "signer", "authority"}


def test_acknowledgement_records_who_and_what_scope():
    ack = exports.ClientAcknowledgment(
        scope=".seshat/semantic-decisions.yaml",
        acknowledged_by="Client",
        acknowledged_at="2026-08-21T10:00:00Z",
        run_id="r1",
    )

    assert ack.scope and ack.acknowledged_by


# --- Task D4/D5: the support bundle -------------------------------------------------


def test_the_bundle_contains_no_env_dsn_or_absolute_path(tmp_path: Path):
    (tmp_path / ".env").write_text("PGPASSWORD=hunter2\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text(
        f"dsn {FAKE_DSN} at {tmp_path}\n", encoding="utf-8"
    )

    bundle = exports.build_support_bundle(tmp_path, destination=tmp_path / "b.zip")

    text = bundle.read_bytes().decode("utf-8", errors="ignore")
    assert "hunter2" not in text
    assert "u:p@h" not in text
    assert str(tmp_path) not in text


def test_the_bundle_still_carries_its_manifest(tmp_path: Path):
    """The paired positive case: an empty archive would pass the test above."""
    bundle = exports.build_support_bundle(tmp_path, destination=tmp_path / "b.zip")

    assert bundle.stat().st_size > 0
    assert exports.read_manifest(bundle)["allowlisted_fields"]


def test_a_scan_failure_leaves_no_artifact(tmp_path: Path, monkeypatch):
    """O5: a partially scrubbed archive is worse than none."""

    def _fail(*args: object, **kwargs: object):
        raise exports.ScanFailed("residual secret detected")

    monkeypatch.setattr(exports, "_scan_staged", _fail)
    destination = tmp_path / "b.zip"

    with pytest.raises(exports.ScanFailed):
        exports.build_support_bundle(tmp_path, destination=destination)

    assert not destination.exists()
    assert [p for p in tmp_path.iterdir() if p.suffix == ".tmp"] == []
