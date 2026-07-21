"""Materialize the governed dbt model set from an approved source map (#406).

``seshat dbt init`` gives an empty ``models/`` skeleton; every governed model,
contract, selector row, source row, and the parity-audit model had to be
hand-authored, each requirement surfacing only as a fail-closed gate blocker
(DBT_FACT_SEMANTICS_MISSING, DBT_MODEL_ORPHANED, DBT_MODEL_CONTRACT_MISSING,
DBT_MODEL_AUTHORITY_INVALID, DBT_COLUMN_CITATION_MISSING, DBT_ARTIFACT_INTEGRITY).

``scaffold_models`` closes that gap the way ``scaffold_source`` does for Stage 1:
it derives the star (staging + one gold model per fact/dim + the parity audit)
FROM the approved, committed source map, renders gate-valid ``_models.yml``
contracts (with ADVISORY ``data_type`` per column, NOT an enforced dbt contract)
+ the ``seshat_table_<id>`` selector row + the parity-audit SQL that ``dbt show``
consumes, and writes skeleton transformation SQL the human completes for the
live build. It targets the STATIC gate:
``validate_project`` and ``evidence._validate_parity_set`` must pass offline; the
skeleton SQL bodies (joins, casts, surrogate-key generation) are the human's
remaining live-build work, marked with explicit TODO banners.
"""

from __future__ import annotations

from .orchestrator import ScaffoldReport, scaffold_models

__all__ = ["ScaffoldReport", "scaffold_models"]
