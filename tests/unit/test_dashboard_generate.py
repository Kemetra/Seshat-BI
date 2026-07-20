from pathlib import Path

import pytest

from seshat.dashboard.generate import generate
from seshat.dashboard.render import render_page
from seshat.status_surface import build_status_projection

pytestmark = pytest.mark.unit


def _make_repo(tmp_path: Path) -> Path:
    d = tmp_path / "mappings" / "orders"
    d.mkdir(parents=True)
    (d / "readiness-status.yaml").write_text(
        'table: "bronze.orders"\n'
        'current_stage: "source_ready"\n'
        "stages:\n"
        "  source_ready:\n"
        '    status: "pass"\n'
        "    evidence: []\n"
        "    blocking_reasons: []\n"
        'next_action: "next"\n',
        encoding="utf-8",
    )
    return tmp_path


def test_generate_writes_file_at_returned_path(tmp_path):
    repo = _make_repo(tmp_path)
    out = generate(repo)
    assert out.exists()
    assert out == repo / "reports" / "dashboard" / "index.html"


def test_generate_output_equals_render_of_projection(tmp_path):
    repo = _make_repo(tmp_path)
    stamp = "2026-07-20 14:30"  # fixed so both sides are deterministic
    out = generate(repo, generated_at=stamp)
    written = out.read_text(encoding="utf-8")
    expected = render_page(build_status_projection(repo), generated_at=stamp)
    assert written == expected


def test_generate_stamps_a_render_timestamp_by_default(tmp_path):
    repo = _make_repo(tmp_path)
    out = generate(repo)  # no generated_at -> generate reads the clock
    written = out.read_text(encoding="utf-8")
    assert "آخر تحديث:" in written  # the impure boundary injected a render time


def test_generate_writes_utf8_without_bom(tmp_path):
    repo = _make_repo(tmp_path)
    out = generate(repo)
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # no BOM


def test_generate_custom_out_path(tmp_path):
    repo = _make_repo(tmp_path)
    target = tmp_path / "custom" / "dash.html"
    out = generate(repo, target)
    assert out == target and target.exists()


def test_generate_unwritable_path_raises_oserror(tmp_path):
    repo = _make_repo(tmp_path)
    # a path whose parent is a FILE, not a dir -> mkdir fails
    blocker = tmp_path / "afile"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(OSError):
        generate(repo, blocker / "nested" / "index.html")
