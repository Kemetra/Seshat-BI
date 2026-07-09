"""Tests + FR-011 verifier for the Personal-Data-Touch Notice (spec 114).

The verifier `assert_notice_is_faithful` is the mechanical guarantee (the reason
this is a Python composer, not a prose skill): it asserts every quoted
disposition is a verbatim substring of a committed source-map field (V1), every
pii:true column is present and classified (V2), no clearance token is authored on
a GAP line (V3), no score appears (V4), and the join is by deviation_ref not prose
(V7).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from retail.pii_notice import build_pii_notice, render_markdown

pytestmark = pytest.mark.unit

# Closed denylist of clearance tokens the composer must never AUTHOR (they may
# appear only inside a verbatim-quoted disposition).
_CLEARANCE = ("safe", "cleared", "no pii risk", "approved", "ok to publish")


# --------------------------------------------------------------------------- #
# fixtures (T001) -- written to a tmp mappings/<table>/source-map.yaml
# --------------------------------------------------------------------------- #
def _write_source_map(root: Path, table: str, text: str) -> None:
    d = root / "mappings" / table
    d.mkdir(parents=True, exist_ok=True)
    (d / "source-map.yaml").write_text(text, encoding="utf-8")


DECIDED_KEPT = """
defaults:
  deviations:
    - id: "RC4"
      reason: "kept as a pseudonymous surrogate; governance ruled keep, no raw PII."
columns:
  - source_name: "customer_id"
    decision: "keep"
    pii: true
    deviation_ref: "RC4"
  - source_name: "amount"
    decision: "keep"
    pii: false
"""

DECIDED_DROPPED = """
columns:
  - source_name: "phone"
    decision: "drop"
    reason: "personal/sensitive data; dropped before the BI layer (RC4)."
    pii: true
"""

UNDECIDED = """
columns:
  - source_name: "customer_id"
    decision: "keep"
    pii: true
"""

# mis_ref: the column's deviation_ref points at RC4, but a DIFFERENT deviation
# (RC8) is the one whose prose mentions the column name. A prose-scanning composer
# would wrongly attribute RC8; a deviation_ref composer joins RC4. (V7)
MIS_REF = """
defaults:
  deviations:
    - id: "RC8"
      reason: "unrelated returns deviation mentioning customer_id in passing."
    - id: "RC4"
      reason: "the governing ruling: keep the pseudonymous surrogate."
columns:
  - source_name: "customer_id"
    decision: "keep"
    pii: true
    deviation_ref: "RC4"
"""

NO_PII = """
columns:
  - source_name: "amount"
    decision: "keep"
    pii: false
  - source_name: "category"
    decision: "keep"
    pii: false
"""

# inconsistent (FR-010): the SAME source_name appears with BOTH keep and drop --
# a contradictory intra-file decision the notice must GAP, never silently pick.
INCONSISTENT = """
columns:
  - source_name: "customer_id"
    decision: "keep"
    pii: true
    deviation_ref: "RC4"
  - source_name: "customer_id"
    decision: "drop"
    reason: "also listed as a drop -- contradicts the keep entry."
    pii: true
"""


# --------------------------------------------------------------------------- #
# the verifier (T003) -- V1/V2/V3/V4/V7, split into focused checks
# --------------------------------------------------------------------------- #
def _committed_texts(source_map: dict) -> list[str]:
    """Every committed reason string (column + deviation) -- the V1 corpus."""
    texts = [
        c["reason"]
        for c in (source_map.get("columns") or [])
        if isinstance(c, dict) and isinstance(c.get("reason"), str)
    ]
    texts += [
        d["reason"]
        for d in (source_map.get("defaults") or {}).get("deviations") or []
        if isinstance(d, dict) and isinstance(d.get("reason"), str)
    ]
    return texts


def _check_v2_completeness(notice_text: str, source_map: dict) -> None:
    for c in source_map.get("columns") or []:
        if isinstance(c, dict) and c.get("pii") is True:
            assert c["source_name"] in notice_text, (
                f"V2: pii:true column {c['source_name']!r} missing from notice"
            )


def _check_v4_no_score(notice_text: str) -> None:
    # scan COMPOSER-AUTHORED text only: strip double-quoted disposition spans (a
    # committed disposition may contain a % or number -- an echo, not an authored
    # score), mirroring the authored-vs-echoed distinction V3 makes.
    authored = re.sub(r'"[^"]*"', "", notice_text)
    assert "%" not in authored, "V4: authored a percent token"
    assert "N of M" not in authored, "V4: authored an N-of-M count"


def _check_v3_gap_line(line: str) -> None:
    low = line.lower()
    assert "not cleared" in low, f"V3: GAP line lacks 'NOT cleared': {line}"
    scanned = low.replace("not cleared", "")  # keep the legit framing out of scan
    for tok in _CLEARANCE:
        assert tok not in scanned, f"V3: GAP line authored a clearance token {tok!r}"


def _check_v1_decided_line(line: str, committed: list[str]) -> None:
    assert '"' in line, f"V1: decided line has no quoted disposition: {line}"
    quoted = line.split('"')[1]
    assert any(quoted in t for t in committed), (
        f"V1: quoted disposition not a verbatim committed substring: {quoted!r}"
    )


def assert_notice_is_faithful(notice_text: str, source_map: dict) -> None:
    """Raise AssertionError unless the rendered notice is faithful to the
    committed source-map (contracts/verifier.md): V2 completeness, V4 no-score,
    and per-line V3 never-clear / V1 verbatim."""
    _check_v2_completeness(notice_text, source_map)
    _check_v4_no_score(notice_text)
    committed = _committed_texts(source_map)
    for raw in notice_text.splitlines():
        line = raw.strip()
        if line.startswith(("- GAP:", "GAP:")):
            _check_v3_gap_line(line)
        elif line.startswith("- ") and "Recorded" in line:
            _check_v1_decided_line(line, committed)


def _compose(tmp_path: Path, table: str, text: str):
    _write_source_map(tmp_path, table, text)
    notice = build_pii_notice(tmp_path, table)
    body = render_markdown(notice)
    source_map = yaml.safe_load(text)
    return notice, body, source_map


# --------------------------------------------------------------------------- #
# US1 -- decided PII columns disclosed verbatim
# --------------------------------------------------------------------------- #
def test_decided_kept_verbatim(tmp_path):
    notice, body, sm = _compose(tmp_path, "t", DECIDED_KEPT)
    assert notice["no_pii"] is False
    finding = next(f for f in notice["findings"] if f["column"] == "customer_id")
    assert finding["state"] == "decided_kept"
    # verbatim disposition = the RC4 deviation reason, cited to its locus
    assert finding["disposition"] == sm["defaults"]["deviations"][0]["reason"]
    assert "defaults.deviations[RC4]" in finding["disposition_source"]
    assert finding["disposition"] in body
    assert_notice_is_faithful(body, sm)


def test_decided_dropped_verbatim(tmp_path):
    notice, body, sm = _compose(tmp_path, "t", DECIDED_DROPPED)
    finding = notice["findings"][0]
    assert finding["state"] == "decided_dropped"
    assert finding["disposition"] == sm["columns"][0]["reason"]
    assert finding["disposition"] in body
    assert "decision:drop" in body
    assert_notice_is_faithful(body, sm)


def test_no_pii_statement(tmp_path):
    notice, body, sm = _compose(tmp_path, "t", NO_PII)
    assert notice["no_pii"] is True
    assert notice["findings"] == []
    assert "No column in this table is flagged as personal data" in body
    assert_notice_is_faithful(body, sm)


# --------------------------------------------------------------------------- #
# US2 -- undecided PII column is an explicit GAP, never clearance
# --------------------------------------------------------------------------- #
def test_undecided_renders_gap_not_clearance(tmp_path):
    notice, body, sm = _compose(tmp_path, "t", UNDECIDED)
    finding = notice["findings"][0]
    assert finding["state"] == "undecided"
    assert finding["disposition"] is None
    # present (never omitted), rendered as a GAP with NOT-cleared framing
    assert "GAP: customer_id" in body
    assert "NOT cleared" in body
    # no clearance token AUTHORED as a positive claim. "cleared" appears only
    # inside the "NOT cleared" framing, so exclude that phrase before scanning.
    scanned = body.lower().replace("not cleared", "")
    for tok in _CLEARANCE:
        assert tok not in scanned, f"authored a clearance token {tok!r}"
    assert_notice_is_faithful(body, sm)


# --------------------------------------------------------------------------- #
# V7 -- join by deviation_ref, NOT by prose (the safety-critical assertion)
# --------------------------------------------------------------------------- #
def test_join_by_deviation_ref_not_prose(tmp_path):
    notice, body, sm = _compose(tmp_path, "t", MIS_REF)
    finding = notice["findings"][0]
    assert finding["state"] == "decided_kept"
    # RC4 is the deviation_ref target; RC8 (which also names the column in prose)
    # must NOT be the source. Proves join-by-ref, not text-match.
    assert "defaults.deviations[RC4]" in finding["disposition_source"]
    assert finding["disposition"] == sm["defaults"]["deviations"][1]["reason"]  # RC4
    assert "returns deviation" not in finding["disposition"]  # not RC8's prose
    assert_notice_is_faithful(body, sm)


def test_keep_without_deviation_ref_is_gap(tmp_path):
    # a kept pii:true column with NO deviation_ref -> undecided GAP, never a guess
    notice, body, sm = _compose(tmp_path, "t", UNDECIDED)
    assert notice["findings"][0]["state"] == "undecided"
    assert "GAP: customer_id" in body


def test_inconsistent_gaps_both_loci(tmp_path):
    # FR-010: a source_name with BOTH keep and drop -> inconsistent GAP, never a
    # silent pick. The notice must NOT present it as decided/cleared.
    notice, body, sm = _compose(tmp_path, "t", INCONSISTENT)
    states = {f["state"] for f in notice["findings"]}
    assert "inconsistent" in states
    assert "CONTRADICTORY decisions" in body
    assert "NOT cleared" in body
    # never emits a decided disclosure for the contradicted column
    assert "Recorded disposition" not in body
    assert_notice_is_faithful(body, sm)


# --------------------------------------------------------------------------- #
# US3 -- missing / unreadable input surfaced, not fabricated
# --------------------------------------------------------------------------- #
def test_missing_source_map_document_gap(tmp_path):
    # no mappings/<table>/source-map.yaml written
    notice = build_pii_notice(tmp_path, "absent")
    body = render_markdown(notice)
    assert notice["document_gap"] is not None
    assert notice["findings"] == []
    assert "GAP: document" in body
    assert "missing or unreadable" in body


def test_empty_columns_block_document_gap(tmp_path):
    _write_source_map(tmp_path, "t", "defaults: {}\ncolumns: []\n")
    notice = build_pii_notice(tmp_path, "t")
    body = render_markdown(notice)
    assert notice["document_gap"] is not None
    assert "no columns block" in body


# --------------------------------------------------------------------------- #
# SC-005 read-only proof + SC-006 generic proof
# --------------------------------------------------------------------------- #
def test_build_writes_nothing(tmp_path):
    _write_source_map(tmp_path, "t", DECIDED_KEPT)
    before = {p.name for p in (tmp_path / "mappings" / "t").iterdir()}
    build_pii_notice(tmp_path, "t")
    render_markdown(build_pii_notice(tmp_path, "t"))
    after = {p.name for p in (tmp_path / "mappings" / "t").iterdir()}
    assert before == after, "build/render must not write any file"


def test_composer_has_no_write_call():
    # V6: grep the module source for a file-write call (build/render never write).
    src = Path("src/retail/pii_notice.py").read_text(encoding="utf-8")
    assert "write_text" not in src
    assert ".write(" not in src
    assert "open(" not in src


def test_generic_two_tables(tmp_path):
    # SC-006: same composer, two distinct tables, no per-table branch.
    _compose(tmp_path, "table_one", DECIDED_KEPT)
    _compose(tmp_path, "table_two", DECIDED_DROPPED)
    n1 = build_pii_notice(tmp_path, "table_one")
    n2 = build_pii_notice(tmp_path, "table_two")
    assert n1["findings"][0]["state"] == "decided_kept"
    assert n2["findings"][0]["state"] == "decided_dropped"


def test_cli_write_touches_only_the_notice_file(tmp_path):
    # SC-005 exercised through the CLI handler (where the ONLY write lives, not
    # the composer): --write creates exactly mappings/<table>/pii-touch-notice.md
    # and mutates no other file in the table dir.
    import argparse

    from retail.cli.commands.pii_notice import pii_notice_main

    _write_source_map(tmp_path, "t", DECIDED_KEPT)
    tdir = tmp_path / "mappings" / "t"
    before = {p.name for p in tdir.iterdir()}

    args = argparse.Namespace(
        repo=str(tmp_path), table="t", output_format="text", write=True
    )
    rc = pii_notice_main(args)
    assert rc == 0

    after = {p.name for p in tdir.iterdir()}
    new = after - before
    assert new == {"pii-touch-notice.md"}, f"expected only the notice, got {new}"
    # the source-map it read is byte-unchanged
    assert (tdir / "source-map.yaml").read_text(encoding="utf-8") == DECIDED_KEPT
