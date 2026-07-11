# Golden PBIP fixture

Hand-authored minimal PBIP used as the **token-shape regression anchor** for the
TMDL/PBIR rules (M4/M5). It is intentionally NOT globally clean: the `bothDirections`
relationship (a D6 violation) and `summarizeBy: sum` (a D5 warning) are deliberate
anchors. Per-rule pass/fail fixtures live with the rules, not here.

The pinned literals are listed in `src/seshat/tmdl.py`'s module docstring. If you edit
this fixture and a pinned token disappears, `tests/unit/test_tmdl.py` fails — that is
the anchor doing its job. The date-table marker (`annotation PBI_DateTable = true`) is
**PROVISIONAL** until replaced by a real Power BI capture (see Task M0.3).
