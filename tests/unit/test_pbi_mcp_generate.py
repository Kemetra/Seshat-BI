"""Safe-generation tests (#450 slice 3): placeholder-only output, the
secret-scan refusal chokepoint, refuse-overwrite, and no-drift pins between
the renderers and the committed example/generated files.

Crafted "would-be secrets" are ASSEMBLED at runtime from parts so this test
source never itself contains a literal the repo's C2 scan would match.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from seshat.pbi_mcp.generate import (
    SETUP_DOC_RELPATH,
    GenerateRefusal,
    render_mcp_template,
    render_setup_doc,
    write_generated,
)
from seshat.pbi_mcp.scan import GeneratedSecretError, scan_text

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# templates: read-only, placeholder-only
# --------------------------------------------------------------------------- #


def test_local_template_is_read_only_and_matches_the_committed_example() -> None:
    rendered = json.loads(render_mcp_template("local"))
    example = json.loads(
        (_REPO_ROOT / ".mcp.json.example").read_text(encoding="utf-8-sig")
    )
    assert rendered == example  # drift between generator and example is a bug
    args = rendered["mcpServers"]["powerbi-modeling"]["args"]
    assert "--readonly" in args
    assert not any("readwrite" in arg or "read-write" in arg for arg in args)
    assert not any("skipconfirmation" in arg for arg in args)


def test_remote_template_carries_only_the_public_endpoint() -> None:
    rendered = json.loads(render_mcp_template("remote"))
    server = rendered["mcpServers"]["powerbi-remote"]
    assert server == {
        "type": "http",
        "url": "https://api.fabric.microsoft.com/v1/mcp/powerbi",
    }


def test_both_template_contains_both_servers_and_scans_clean() -> None:
    text = render_mcp_template("both")
    rendered = json.loads(text)
    assert set(rendered["mcpServers"]) == {"powerbi-modeling", "powerbi-remote"}
    assert scan_text(text) == ()


def test_unknown_transport_is_refused() -> None:
    with pytest.raises(GenerateRefusal, match="unknown transport"):
        render_mcp_template("carrier-pigeon")


# --------------------------------------------------------------------------- #
# setup doc: generated banner + committed-copy parity
# --------------------------------------------------------------------------- #


def test_setup_doc_scans_clean_and_carries_the_generated_banner() -> None:
    text = render_setup_doc()
    assert text.isascii()
    assert "GENERATED -- do not hand-edit" in text
    assert "--readonly" in text
    assert "--skipconfirmation" in text  # named as forbidden
    assert "pbi-mcp-adapter.md" in text  # cites the three-senses doc
    assert scan_text(text) == ()


def test_committed_setup_doc_matches_the_renderer_exactly() -> None:
    committed = (_REPO_ROOT / SETUP_DOC_RELPATH).read_text(encoding="utf-8-sig")
    assert committed.replace("\r\n", "\n") == render_setup_doc()


# --------------------------------------------------------------------------- #
# the secret-scan chokepoint refuses crafted would-be secrets
# --------------------------------------------------------------------------- #


def _crafted(kind: str) -> str:
    # Assembled from parts (see module docstring).
    if kind == "conn-url":
        return "url: " + "postgres" + "ql://analyst:" + "hunter2@dbhost/gold"
    if kind == "odbc":
        return "conn: " + "PW" + "D=" + "hunter2"
    if kind == "win-path":
        return "path: " + "C:" + "\\Users" + "\\jdoe" + "\\project"
    if kind == "guid":
        return "tenant: " + "12345678-90ab-" + "cdef-1234-" + "567890abcdef"
    if kind == "do-endpoint":
        return "host: mydb" + ".db." + "ondigitalocean" + ".com"
    raise AssertionError(kind)


@pytest.mark.parametrize(
    "kind", ["conn-url", "odbc", "win-path", "guid", "do-endpoint"]
)
def test_write_refuses_each_crafted_secret_shape(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "out.json"
    with pytest.raises(GeneratedSecretError, match="secret-shaped"):
        write_generated(target, "{}\n" + _crafted(kind) + "\n")
    assert not target.exists()  # refused BEFORE writing


def test_refusal_never_echoes_the_matched_value(tmp_path: Path) -> None:
    with pytest.raises(GeneratedSecretError) as caught:
        write_generated(tmp_path / "out.txt", _crafted("odbc"))
    assert "hunter2" not in str(caught.value)


def test_placeholders_do_not_trip_the_scan() -> None:
    safe = (
        "password: <your-value-here>\n"
        "host: <your-db-host>" + ".db." + "ondigitalocean" + ".com\n"
        "tenant: <tenant-id>\n"
    )
    assert scan_text(safe) == ()


# --------------------------------------------------------------------------- #
# refuse-overwrite
# --------------------------------------------------------------------------- #


def test_write_generated_refuses_to_overwrite(tmp_path: Path) -> None:
    target = tmp_path / ".mcp.json"
    written = write_generated(target, render_mcp_template("local"))
    assert written.is_file()
    with pytest.raises(GenerateRefusal, match="never overwrites"):
        write_generated(target, render_mcp_template("local"))
