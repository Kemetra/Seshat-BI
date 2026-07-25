"""Regression tests for issues #486 and #487 (fail-closed gate hardening).

Three distinct defects, each reproduced here before it was fixed:

  - #486: ``seshat init`` writes the two files ``is_bootstrapped()`` tests for,
    so the supported consumer setup command made a foreign repo claim to BE the
    kit and unblocked the KIT_SELF rule tier -- 10 hard errors on the golden
    path. The tier needs its own predicate.
  - #487-A: the approval gate is correct but silent. Neither the inbox detail
    nor the agent ``next_allowed_action`` named the shape they require, and the
    default ``next --table`` text surface printed no guidance line at all.
  - #487-B: ``at:`` was required only by RS1's freshness check, not by the
    shape-validity predicate the three surfaces share, so an entry keyed
    ``date:`` made ``approvals``/``next`` report satisfied while ``check``
    rejected it -- a fail-open on the approval path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from seshat.approval_inbox import build_approval_inbox
from seshat.cli import main as cli_main
from tests.unit._gitfix import make_git_repo

pytestmark = pytest.mark.unit

# SC1 reads a kit-internal manifest (docs/quality/status-claims.yaml), so it
# errors in a foreign repo unless the tier gate skips it.
_KIT_SELF_ID = "SC1"


def _write_status(root: Path, table_dir: str, body: str) -> Path:
    path = root / "mappings" / table_dir / "readiness-status.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _status_with_approval(approval_block: str) -> str:
    """A table at mapping_ready: pass, with ``approval_block`` under approvals:."""
    return f"""\
table: "silver.orders"
stages:
  source_ready: {{status: "pass", evidence: ["profile"]}}
  mapping_ready: {{status: "pass", evidence: ["map"]}}
  silver_ready: {{status: "not_started"}}
  gold_ready: {{status: "not_started"}}
  semantic_model_ready: {{status: "not_started"}}
  dashboard_ready: {{status: "not_started"}}
  publish_ready: {{status: "not_started"}}
approvals:
{approval_block}
last_checked_at: "2026-07-25"
"""


# ---------------------------------------------------------------------------
# #486 -- the KIT_SELF tier must not activate just because `init` ran here
# ---------------------------------------------------------------------------


def _simulate_seshat_init(repo: Path) -> None:
    """Write exactly what `seshat init` leaves behind: the `.seshat/` substrate.

    This is the reporter's setup -- ``kit_init.bootstrap`` +
    ``compass_project.seed_kit_source`` materialize these two files into ANY
    repo the kit was installed into.
    """
    seshat = repo / ".seshat"
    seshat.mkdir(parents=True, exist_ok=True)
    (seshat / "kit-source.yaml").write_text("name: t\n", encoding="utf-8")
    (seshat / "compass.yaml").write_text("name: t\n", encoding="utf-8")


def test_init_in_a_consumer_repo_does_not_activate_kit_self_rules(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Issue #486: the golden path (`init` -> `check`) must not fire KIT_SELF.

    A consumer repo that ran `seshat init` has the substrate but is NOT the kit:
    it has no kit source tree and no seshat-bi distribution metadata. KIT_SELF
    rules must still SKIP, because the kit's internal manifests are files such a
    repo cannot have and must never fabricate (FR-004).
    """
    repo = make_git_repo(tmp_path)
    _simulate_seshat_init(repo)

    cli_main(["check", "--repo", str(repo)])
    out = capsys.readouterr().out

    assert f"[info] {_KIT_SELF_ID} skipped (kit-self rule" in out
    assert f"[error] {_KIT_SELF_ID}" not in out


def test_kit_self_rules_still_run_in_the_kits_own_repo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The replacement premise for the old bootstrapped-repo test.

    A repo is the kit itself when it carries the kit's own package source AND
    declares itself as the seshat-bi distribution -- neither of which any `init`
    flow writes. There, KIT_SELF rules must RUN (no skip line).
    """
    repo = make_git_repo(tmp_path)
    _simulate_seshat_init(repo)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "seshat-bi"\nversion = "0.0.0"\n', encoding="utf-8"
    )
    pkg = repo / "src" / "seshat"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    cli_main(["check", "--repo", str(repo)])
    out = capsys.readouterr().out

    assert f"[info] {_KIT_SELF_ID} skipped (kit-self rule" not in out


def test_kit_substrate_alone_is_not_kit_identity() -> None:
    """The two predicates must be genuinely distinct, not aliases."""
    from seshat.kit_lint import is_bootstrapped, is_kit_self_repo

    assert is_bootstrapped is not is_kit_self_repo


# ---------------------------------------------------------------------------
# #487-A -- the gate must name the shape it requires, at the point of failure
# ---------------------------------------------------------------------------


def test_inbox_detail_names_the_required_approval_shape(tmp_path: Path) -> None:
    """Issue #487: "no shape-valid approval is recorded" never said the shape."""
    _write_status(tmp_path, "orders", _status_with_approval("  []"))

    detail = build_approval_inbox(tmp_path)["items"][0]["detail"]

    # Names the container, the required keys, and the owner format.
    assert "approvals" in detail
    assert "stage" in detail and "owner" in detail and "at" in detail
    assert "authority_class" in detail


def test_agent_next_allowed_action_shows_a_concrete_approval_entry(
    tmp_path: Path,
) -> None:
    """The agent surface must show the entry, not just demand one."""
    from seshat.agent_next import build_agent_next_document

    _write_status(tmp_path, "orders", _status_with_approval("  []"))

    document = build_agent_next_document(tmp_path, "orders")
    action = document["next_allowed_action"]

    assert "approvals" in action
    assert "authority_class" in action
    # Still refuses to self-grant -- naming the shape must not soften the gate.
    assert "never self-grant" in action


def test_default_next_table_text_surface_renders_guidance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Issue #487: `next --table X` (default text) printed NO action line.

    The reporter's quoted guidance only ever appeared under --format agent.
    """
    _write_status(tmp_path, "orders", _status_with_approval("  []"))

    cli_main(["next", "--repo", str(tmp_path), "--table", "orders"])
    out = capsys.readouterr().out

    assert "outcome: approval_required" in out
    assert "action:" in out, "default text surface must not stay silent"
    assert "approvals" in out


# ---------------------------------------------------------------------------
# #487-B -- all surfaces must agree on what a shape-valid approval is
# ---------------------------------------------------------------------------

_WRONG_DATE_KEY = """\
  - stage: "mapping_ready"
    owner: "Ahmed Shaaban (analyst)"
    date: "2026-07-25"
"""

_CORRECT = """\
  - stage: "mapping_ready"
    owner: "Ahmed Shaaban (analyst)"
    at: "2026-07-25"
"""


def test_approval_without_at_does_not_satisfy_the_inbox(tmp_path: Path) -> None:
    """Issue #487-B: `date:` instead of `at:` made the inbox report clean.

    RS1 rejects such an entry, so the inbox must not bless it -- otherwise two
    surfaces disagree with the gate rule and the approval path fails OPEN.
    """
    _write_status(tmp_path, "orders", _status_with_approval(_WRONG_DATE_KEY))

    items = build_approval_inbox(tmp_path)["items"]

    assert items, "an approval missing a valid `at:` must still be flagged"
    assert items[0]["stage"] == "mapping_ready"


def test_approval_without_at_does_not_advance_run_next(tmp_path: Path) -> None:
    """Same entry must not let `seshat next` advance past the approval gate."""
    from seshat.run_next import build_run_next_response

    _write_status(tmp_path, "orders", _status_with_approval(_WRONG_DATE_KEY))

    response = build_run_next_response(tmp_path, "orders")

    assert response["outcome"] == "approval_required"


def test_correctly_shaped_approval_still_satisfies_both_surfaces(
    tmp_path: Path,
) -> None:
    """The tightening must not break a properly shaped approval (no-finding).

    Every approvals[] entry committed in this repo uses `at:`, so this is the
    real-world shape and it must keep working.
    """
    from seshat.run_next import build_run_next_response

    _write_status(tmp_path, "orders", _status_with_approval(_CORRECT))

    assert build_approval_inbox(tmp_path)["items"] == []
    assert build_run_next_response(tmp_path, "orders")["outcome"] != "approval_required"


# ---------------------------------------------------------------------------
# #485 (interim) -- say out loud that live evidence carries no DB provenance
# ---------------------------------------------------------------------------

_ALL_PASS_APPROVED = """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "pass", evidence: ["map"]}
  silver_ready:
    status: "pass"
    evidence: ["0003_create_silver_orders.sql applied to training; 12,575 rows"]
  gold_ready: {status: "pass", evidence: ["0004_gold.sql", "validate exit 0"]}
  semantic_model_ready: {status: "pass", evidence: ["powerbi/Orders"]}
  dashboard_ready: {status: "pass", evidence: ["report.json"]}
  publish_ready: {status: "pass", evidence: ["published"]}
approvals:
  - stage: mapping_ready
    owner: "Ada Lovelace (analyst)"
    at: "2026-07-01"
  - stage: semantic_model_ready
    owner: "Ada Lovelace (metric_owner)"
    at: "2026-07-01"
  - stage: dashboard_ready
    owner: "Ada Lovelace (governance)"
    at: "2026-07-01"
  - stage: publish_ready
    owner: "Ada Lovelace (data_owner)"
    at: "2026-07-01"
last_checked_at: "2026-07-02"
"""

_EARLY_STAGES_ONLY = """\
table: "silver.orders"
stages:
  source_ready: {status: "pass", evidence: ["profile"]}
  mapping_ready: {status: "not_started"}
  silver_ready: {status: "not_started"}
  gold_ready: {status: "not_started"}
  semantic_model_ready: {status: "not_started"}
  dashboard_ready: {status: "not_started"}
  publish_ready: {status: "not_started"}
approvals: []
"""

_PROVENANCE_KIND = "unverified_db_provenance"


def _caveat_kinds(response: dict) -> list[str]:
    return [c.get("kind") for c in response.get("caveats", [])]


def test_terminal_pass_says_its_live_evidence_has_no_db_provenance(
    tmp_path: Path,
) -> None:
    """Issue #485 interim: terminal_pass was reported with `caveats: []`.

    The reporter's case -- evidence earned against database "Ex-1", `.env` since
    repointed at a different database -- produced a fully green report with no
    indication anything was unverifiable. Until provenance can be captured
    mechanically, the surface must at least SAY that it cannot correlate.
    """
    from seshat.run_next import build_run_next_response

    _write_status(tmp_path, "orders", _ALL_PASS_APPROVED)

    response = build_run_next_response(tmp_path, "orders")

    assert response["outcome"] == "terminal_pass"
    assert _PROVENANCE_KIND in _caveat_kinds(response)


def test_provenance_caveat_is_non_blocking(tmp_path: Path) -> None:
    """It must not flip a passing table to blocked -- it is a caveat, not a gate.

    Adding a *blocking* provenance check would fail every committed record at
    once, since none carries provenance today.
    """
    from seshat.run_next import build_run_next_response

    _write_status(tmp_path, "orders", _ALL_PASS_APPROVED)

    response = build_run_next_response(tmp_path, "orders")

    assert response["outcome"] == "terminal_pass"
    assert response["stage"] is None


def test_provenance_caveat_is_targeted_not_blanket(tmp_path: Path) -> None:
    """It fires only for stages whose evidence asserts live warehouse objects.

    A blanket caveat on every table at every stage would be tuned out. A table
    that has not built silver/gold has made no database-dependent claim yet, so
    there is nothing to qualify.
    """
    from seshat.run_next import build_run_next_response

    _write_status(tmp_path, "orders", _EARLY_STAGES_ONLY)

    response = build_run_next_response(tmp_path, "orders")

    assert _PROVENANCE_KIND not in _caveat_kinds(response)


def test_provenance_caveat_names_the_dsn_env_vars(tmp_path: Path) -> None:
    """The caveat has to be actionable: say what could not be compared."""
    from seshat.run_next import build_run_next_response

    _write_status(tmp_path, "orders", _ALL_PASS_APPROVED)

    detail = next(
        c["detail"]
        for c in build_run_next_response(tmp_path, "orders")["caveats"]
        if c["kind"] == _PROVENANCE_KIND
    )

    assert "silver_ready" in detail or "gold_ready" in detail
    assert "database" in detail.lower()


def test_agent_document_carries_the_provenance_caveat(tmp_path: Path) -> None:
    """The agent surface is the one an agent trusts -- it must carry it too."""
    from seshat.agent_next import build_agent_next_document

    _write_status(tmp_path, "orders", _ALL_PASS_APPROVED)

    document = build_agent_next_document(tmp_path, "orders")

    assert _PROVENANCE_KIND in [c.get("kind") for c in document.get("caveats", [])]


def test_template_documents_every_authority_class_the_code_accepts() -> None:
    """The template listed four classes; the code accepts five (report_owner).

    A user copying the template cannot discover `report_owner`, so a legitimate
    report-owner approval gets written with an unaccepted class.
    """
    from seshat.rules.readiness_status import _AUTHORITY_CLASSES

    repo_root = Path(__file__).resolve().parents[2]
    template = (repo_root / "templates" / "readiness-status.yaml").read_text(
        encoding="utf-8"
    )

    missing = sorted(c for c in _AUTHORITY_CLASSES if c not in template)
    assert not missing, f"authority classes absent from the template: {missing}"
