"""Disclosure-safe static readiness explorer (spec 120, US8).

Generates one self-contained offline HTML portfolio view over the shared
readiness projection: table-by-stage status, evidence, blockers, approval
receipts, next actions, and available metric lineage. Read-only, no score,
no inferred pass; missing/malformed/deferred evidence stays explicit.
"""
