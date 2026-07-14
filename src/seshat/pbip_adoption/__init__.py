"""Read-only, governed assessment and opt-in baseline scaffolding for PBIP.

This package deliberately owns no readiness state and grants no approval.  It
collects safe, project-relative structural facts, composes the existing rule and
readiness seams, and exposes one small write operation whose exact assessment
digest must be accepted by a human first.

The implementation is split by responsibility -- ``_safety`` (containment and
redaction), ``_facts``/``_discovery`` (structural discovery), ``_seams``
(governance/readiness/next-step composition), ``_assess`` (assembly),
``_scaffold`` (the one write), and ``_render`` (output) -- and re-exported here
as the stable public surface.
"""

from __future__ import annotations

# Re-exported so tests can monkeypatch ``os.link`` on this package while
# exercising the scaffold publish path.
import os  # noqa: F401

from ._assess import assess_pbip
from ._render import (
    assessment_exit_code,
    render_assessment_text,
    render_scaffold_result_text,
    scaffold_exit_code,
)
from ._safety import (
    MANIFEST_PATH,
    PbipAdoptionError,
    canonical_assessment_digest,
)
from ._scaffold import scaffold_pbip

__all__ = [
    "MANIFEST_PATH",
    "PbipAdoptionError",
    "assessment_exit_code",
    "assess_pbip",
    "canonical_assessment_digest",
    "render_assessment_text",
    "render_scaffold_result_text",
    "scaffold_exit_code",
    "scaffold_pbip",
]
