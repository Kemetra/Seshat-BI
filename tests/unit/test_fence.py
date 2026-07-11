"""TDD tests for the SESHAT-KIT fence reader/writer (feature 070).

Covers the fence contract (contracts/fence.contract.md):
* F1/F2 fence-only writes + outside-fence byte-invariance (SC-002);
* F3 idempotency -- exactly one fence, no duplicate on re-run (SC-003);
* F4 safe insertion when markers absent; STOP+report on unsafe placement;
* F5 distinct from the SPECKIT fence -- coexist untouched.

tmp_path repos only; no real repo file is mutated.
"""

from __future__ import annotations

import pytest

from seshat.fence import (
    END,
    START,
    FenceResult,
    write_fence,
)

pytestmark = pytest.mark.unit


def _fenced(body: str) -> str:
    return f"{START}\n{body}\n{END}"


def test_insert_when_absent_appends_one_fence(tmp_path) -> None:
    f = tmp_path / "AGENTS.md"
    original = "# AGENTS\n\n- a rule\n- another\n"
    f.write_text(original, encoding="utf-8")

    result = write_fence(f, "GENERATED BODY")

    assert isinstance(result, FenceResult)
    assert result.ok
    text = f.read_text(encoding="utf-8")
    # exactly one START and one END
    assert text.count(START) == 1
    assert text.count(END) == 1
    # the original content is still present, unchanged, ahead of the fence
    assert text.startswith(original)
    assert "GENERATED BODY" in text


def test_replace_only_fenced_body_outside_bytes_identical(tmp_path) -> None:
    f = tmp_path / "CLAUDE.md"
    before = f"# top\nlaw line\n\n{_fenced('OLD BODY')}\n\ntail law\n"
    f.write_text(before, encoding="utf-8")

    write_fence(f, "NEW BODY")

    after = f.read_text(encoding="utf-8")
    # everything outside the fence is byte-identical
    before_outside = before.replace(_fenced("OLD BODY"), "")
    after_outside = after.replace(_fenced("NEW BODY"), "")
    assert before_outside == after_outside
    assert "OLD BODY" not in after
    assert "NEW BODY" in after


def test_idempotent_double_run_one_fence_outside_unchanged(tmp_path) -> None:
    f = tmp_path / "AGENTS.md"
    original = "# AGENTS\n\n- rule\n"
    f.write_text(original, encoding="utf-8")

    write_fence(f, "BODY V1")
    after_first = f.read_text(encoding="utf-8")
    write_fence(f, "BODY V1")  # same body, second run
    after_second = f.read_text(encoding="utf-8")

    assert after_first == after_second  # idempotent for identical body
    assert after_second.count(START) == 1
    assert after_second.count(END) == 1


def test_reproject_updates_body_keeps_single_fence(tmp_path) -> None:
    f = tmp_path / "AGENTS.md"
    f.write_text("# AGENTS\n\n- rule\n", encoding="utf-8")
    write_fence(f, "BODY V1")
    write_fence(f, "BODY V2")
    text = f.read_text(encoding="utf-8")
    assert text.count(START) == 1
    assert "BODY V1" not in text
    assert "BODY V2" in text


def test_coexists_with_speckit_fence_untouched(tmp_path) -> None:
    f = tmp_path / "CLAUDE.md"
    speckit = "<!-- SPECKIT START -->\nplan pointer\n<!-- SPECKIT END -->"
    before = f"# law\n\n{speckit}\n"
    f.write_text(before, encoding="utf-8")

    write_fence(f, "KIT BODY")

    after = f.read_text(encoding="utf-8")
    assert speckit in after  # the SPECKIT fence is byte-identical
    assert after.count(START) == 1  # our fence added once


def test_malformed_only_start_marker_stops_no_write(tmp_path) -> None:
    f = tmp_path / "AGENTS.md"
    broken = f"# law\n{START}\ndangling body with no end\n"
    f.write_text(broken, encoding="utf-8")

    result = write_fence(f, "BODY")

    assert not result.ok
    assert result.stopped_reason is not None
    # file unchanged on a STOP
    assert f.read_text(encoding="utf-8") == broken


def test_writes_utf8_no_bom_lf(tmp_path) -> None:
    f = tmp_path / "AGENTS.md"
    f.write_text("# a\n", encoding="utf-8")
    write_fence(f, "BODY")
    raw = f.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # no BOM
    assert b"\r\n" not in raw  # LF only
