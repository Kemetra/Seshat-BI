from __future__ import annotations

from pathlib import Path

import pytest

from seshat.statistical.evidence import EvidenceRefused
from seshat.statistical.render import render_review, write_review
from tests.unit.statistical.test_evidence import sample_evidence


def test_render_review_projects_evidence_without_recomputing() -> None:
    rendered = render_review(sample_evidence())

    assert "# Statistical analysis review" in rendered
    assert "one row per week" in rendered
    assert "describe (1.0)" in rendered
    assert "mean: 10.5 USD" in rendered
    assert "bootstrap" in rendered
    assert "STAT_SAMPLE_SIZE" in rendered
    assert "Derived evidence is not a causal claim." in rendered
    assert "readiness effect is none" in rendered.casefold()
    assert "## Human review decision" in rendered
    assert "- [ ] accepted" in rendered
    assert "Reviewer:" in rendered
    assert "Authority class:" in rendered
    assert "Permitted narrative claim:" in rendered


def test_write_review_is_deterministic_and_repo_contained(tmp_path: Path) -> None:
    path = tmp_path / "review.md"

    first = write_review(path, sample_evidence(), repo_root=tmp_path)
    initial = first.read_bytes()
    second = write_review(path, sample_evidence(), repo_root=tmp_path)

    assert second.read_bytes() == initial
    assert initial.endswith(b"\n")


def test_render_review_refuses_unsafe_evidence() -> None:
    unsafe = sample_evidence(
        input_provenance={
            **sample_evidence().input_provenance,
            "rows": ({"metric_value": 10},),
        }
    )

    with pytest.raises(EvidenceRefused):
        render_review(unsafe)
