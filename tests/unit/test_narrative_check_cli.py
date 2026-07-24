"""CLI-level tests for `seshat narrative-check` (spec 021, T012/T014).

Mirrors ``test_pbir_validate_bindings_cli.py``: exercises the wired ``_DISPATCH``
entry through ``seshat.cli.main``, not the library directly. Read-only -- the
exit code communicates the outcome (0 = pass/warning, 1 = blocked); the CLI
never writes a file and never grants approval. Both ``--format text`` (default)
and ``--format json`` are exercised.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from seshat.cli import main

pytestmark = pytest.mark.unit


_CONTRACT_TEXT = "metric: NetSales\nowner: analytics\nstatus: approved\n"
# Real profile shape: a per-column pipe table of bare column names.
_PROFILE_TEXT = (
    "# source-profile: orders\n\n## Per-column profile\n\n"
    "| Column | Type | Missing | Distinct | PK? | Notes |\n"
    "|--------|------|---------|----------|-----|-------|\n"
    "| `division` | TEXT | 0 / 0.00% | 6 | no | dim attribute |\n"
)


def _blob_sha(path: Path) -> str:
    out = subprocess.run(
        ["git", "hash-object", str(path)], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def _brief(contract_sha: str) -> str:
    return f"""```yaml
schema: seshat.narrative-brief/v1
table: orders
source_profile: mappings/orders/source-profile.md
contracts:
  - id: NetSales
    revision: {contract_sha}
questions:
  - id: Q1
    decision: Where is net sales concentrated?
    stage: overview
    framing: concentration
    cites:
      measures: [NetSales]
      dimensions: [division]
    comparison: portfolio average
    guardrail:
      basis: portfolio average
    callout: One division carries a disproportionate share.
story_order:
  overview:  [Q1]
  change:    []
  why_where: []
  action:    []
gaps: []
```

# body
prose
"""


def _workspace(tmp_path: Path, brief_body: str | None = None) -> Path:
    table_dir = tmp_path / "mappings" / "orders"
    (table_dir / "contracts").mkdir(parents=True)
    contract = table_dir / "contracts" / "NetSales.yaml"
    contract.write_text(_CONTRACT_TEXT, encoding="utf-8")
    (table_dir / "source-profile.md").write_text(_PROFILE_TEXT, encoding="utf-8")
    brief = table_dir / "narrative-brief.md"
    brief.write_text(brief_body or _brief(_blob_sha(contract)), encoding="utf-8")
    return tmp_path


def _run(repo_root: Path, *extra: str) -> int:
    return main(
        ["narrative-check", "--table", "orders", "--report", str(repo_root), *extra]
    )


def test_cli_clean_brief_exit_zero(tmp_path: Path, capsys):
    assert _run(_workspace(tmp_path)) == 0
    out = capsys.readouterr().out
    assert "status: pass" in out
    assert "grants no approval" in out


def test_cli_findings_exit_one(tmp_path: Path, capsys):
    ws = _workspace(tmp_path)
    brief = ws / "mappings" / "orders" / "narrative-brief.md"
    brief.write_text(
        brief.read_text(encoding="utf-8").replace(
            "comparison: portfolio average", "comparison: none"
        ),
        encoding="utf-8",
    )
    assert _run(ws) == 1
    out = capsys.readouterr().out
    assert "status: blocked" in out
    assert "bare_total_headline" in out


def test_cli_missing_brief_fails_closed(tmp_path: Path):
    (tmp_path / "mappings" / "orders").mkdir(parents=True)
    assert _run(tmp_path) == 1


def test_cli_json_format_is_parseable(tmp_path: Path, capsys):
    assert _run(_workspace(tmp_path), "--format", "json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["grants_approval"] is False
    assert payload["findings"] == []


def test_cli_json_format_carries_findings(tmp_path: Path, capsys):
    (tmp_path / "mappings" / "orders").mkdir(parents=True)
    assert _run(tmp_path, "--format", "json") == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "blocked"
    assert any(f["dimension"] == "missing_brief" for f in payload["findings"])


# --------------------------------------------------------------------------- #
# --binding-map: design-stage mode (Phase B). Opt-in so brief-stage callers
# (US1: a brief exists, no map yet) are NOT broken by map-absence fail-close.
# --------------------------------------------------------------------------- #


def _clean_map() -> str:
    return """```yaml
schema: seshat.binding-map/v1
table: orders
brief: mappings/orders/narrative-brief.md
pages:
  - id: overview
    regions: [kpi_strip]
visuals:
  - visual_id: v01
    page: overview
    region: kpi_strip
    visual_type: card
    contract: NetSales
    decision_questions: [Q1]
    headline: true
```
# body
"""


def _workspace_with_map(tmp_path: Path) -> Path:
    ws = _workspace(tmp_path)
    design = ws / "mappings" / "orders" / "design"
    design.mkdir(parents=True)
    (design / "visual-contract-binding-map.md").write_text(
        _clean_map(), encoding="utf-8"
    )
    return ws


def test_cli_binding_map_clean_exit_zero(tmp_path: Path, capsys):
    ws = _workspace_with_map(tmp_path)
    assert _run(ws, "--binding-map") == 0
    out = capsys.readouterr().out
    assert "status: pass" in out
    assert "grants no approval" in out


def test_cli_binding_map_orphan_exit_one(tmp_path: Path, capsys):
    ws = _workspace_with_map(tmp_path)
    m = ws / "mappings" / "orders" / "design" / "visual-contract-binding-map.md"
    m.write_text(
        m.read_text(encoding="utf-8").replace(
            "decision_questions: [Q1]", "decision_questions: [Q99]"
        ),
        encoding="utf-8",
    )
    assert _run(ws, "--binding-map") == 1
    out = capsys.readouterr().out
    assert "status: blocked" in out
    assert "orphan_visual" in out


def test_cli_binding_map_missing_map_fails_closed(tmp_path: Path):
    # A brief exists but no map, and the caller asked for --binding-map ->
    # fail closed (missing_binding_map), never a silent pass.
    ws = _workspace(tmp_path)
    assert _run(ws, "--binding-map") == 1


def test_cli_without_binding_map_ignores_absent_map(tmp_path: Path):
    # Brief-stage (default) mode: a brief with no map is NOT a failure -- the map
    # is out of scope unless --binding-map is asked for (US1 not broken).
    assert _run(_workspace(tmp_path)) == 0


def test_cli_binding_map_json(tmp_path: Path, capsys):
    ws = _workspace_with_map(tmp_path)
    assert _run(ws, "--binding-map", "--format", "json") == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["grants_approval"] is False
