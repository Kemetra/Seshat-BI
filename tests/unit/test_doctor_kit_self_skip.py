"""doctor honors the same KIT_SELF / foreign-repo skip that check does (#377).

`retail check` skips the KIT_SELF rules (A1/A3/SC1) with an INFO in a repo that
is not kit-bootstrapped (Spec A), so a client's workspace is never told its
(nonexistent) kit-internal manifests are in error. `doctor` aggregated the same
checks directly, bypassing that skip -- so the two verbs DISAGREED on the same
tree. These tests pin doctor to agree with check.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from seshat.core import RuleContext, Severity
from seshat.doctor import collect_findings, run_doctor

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap(repo: Path) -> None:
    """Make `repo` kit-bootstrapped (seed + compass) so KIT_SELF checks run."""
    (repo / ".seshat").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        _REPO_ROOT / ".seshat" / "kit-source.yaml", repo / ".seshat" / "kit-source.yaml"
    )
    shutil.copyfile(
        _REPO_ROOT / ".seshat" / "compass.yaml", repo / ".seshat" / "compass.yaml"
    )


# ---------------------------------------------------------------------------
# Non-bootstrapped (foreign / fresh) repo: doctor must NOT error on kit manifests
# ---------------------------------------------------------------------------


def test_doctor_skips_kit_self_checks_when_not_bootstrapped(tmp_path: Path) -> None:
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = collect_findings(ctx)
    # No ERROR/WARNING for the kit-internal manifests a foreign repo can't have.
    hard = [f for f in findings if f.severity in (Severity.ERROR, Severity.WARNING)]
    assert hard == [], (
        f"doctor over-reported on a foreign repo: {[f.message for f in hard]}"
    )


def test_doctor_strict_exits_zero_when_not_bootstrapped(tmp_path: Path) -> None:
    # The strict gate must not fail a foreign repo for its (skipped) kit manifests.
    assert run_doctor(tmp_path, strict=True) == 0


# ---------------------------------------------------------------------------
# Bootstrapped repo with genuine drift: doctor STILL surfaces it (intent kept)
# ---------------------------------------------------------------------------


def test_doctor_surfaces_drift_on_bootstrapped_repo(tmp_path: Path) -> None:
    # A bootstrapped repo that is MISSING the kit manifests genuinely has drift --
    # doctor must still report it (the checks run when bootstrapped).
    _bootstrap(tmp_path)
    ctx = RuleContext(repo_root=tmp_path, tracked_files=())
    findings = collect_findings(ctx)
    hard = [f for f in findings if f.severity in (Severity.ERROR, Severity.WARNING)]
    assert hard, "a bootstrapped repo missing its manifests should still surface drift"


def test_doctor_strict_exits_nonzero_on_bootstrapped_drift(tmp_path: Path) -> None:
    _bootstrap(tmp_path)
    assert run_doctor(tmp_path, strict=True) == 1
