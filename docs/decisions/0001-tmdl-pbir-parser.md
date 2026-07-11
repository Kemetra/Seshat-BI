# 0001 — TMDL / PBIR parser choice

- **Date:** 2026-06-23
- **Status:** Accepted
- **Context:** The static governance core (spec §9) must parse committed TMDL and
  PBIR text with **no Power BI Desktop, no .NET, no network** — it has to run headless
  in CI on any OS (spec §11).

## Decision

- **TMDL → hand-rolled indentation/block tokenizer** in `src/seshat/tmdl.py`.
- **PBIR / report JSON → stdlib `json`**, opened `encoding="utf-8-sig"` (Power BI
  writes UTF-8-with-BOM; a plain `json.load` raises on the BOM).

## Alternatives rejected

- **PyPI TMDL parsers** — surveyed 2026-06; none mature/maintained enough to take as a
  runtime dependency for a gate that must never falsely pass.
- **TOM (Tabular Object Model) / `sempy`** — read TMDL only via the Windows/.NET live
  path or the Fabric service. Both require a live connection and a platform we cannot
  guarantee in CI, so they defeat the headless requirement. Disqualified.

## Consequence

The parser is ours to maintain, but it stays dependency-light and OS-independent. Its
token expectations are pinned as a regression anchor in the `tmdl.py` module docstring
and locked by `tests/fixtures/golden_pbip/` (Task M0.2).
