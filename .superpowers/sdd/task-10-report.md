# Task 10 Report — ruff format + lint fixes (E402/E501/I001)

## Changes per file

### tests/unit/test_dax_gen.py
- **E402 x8**: Moved all mid-file module-level imports to the top of the file (after
  module docstring). Consolidated `from retail.dax_gen import _emit_base`,
  `from retail.dax_gen import _emit_ratio, generate_measure`,
  `from retail.metric_drift import check_measure_drift`,
  `import os`, `import subprocess`, `import sys`, `from pathlib import Path`,
  `from retail.dax_gen import load_contract` into the top import block using a
  parenthesized multi-name import for `retail.dax_gen`.
- **E501 x5**: Reformatted RATIO_DISC constant (lines 129, 131), comment in
  `test_generated_tmdl_passes_d_rules` (line 150), filter dict in
  `test_emit_ratio_inline_count_rows` (line 185), and `subprocess.run` call in
  `test_dax_gen_import_is_stdlib_only` (line 237) to stay within 88 chars.
- **ruff format**: Applied (2 files reformatted including this one).

### tests/unit/test_metric_drift.py
- **E402 x2**: Moved `import subprocess` and `import sys` (originally mid-file at
  line 471-472) to the top import block (after `import os`).
- **E501 x1**: Wrapped `subprocess.run(...)` call in
  `test_retail_rules_pulls_neither_dax_gen_nor_yaml` to stay within 88 chars.
- **ruff format**: Applied (already formatted after edits).

### src/retail/dax_gen.py
- **I001**: Reordered the lazy import block inside `_run_d_rules()` — moved
  `from . import rules as _rules_pkg` before `from .core import ...` to satisfy
  isort (relative imports sorted: `.` before `.core` before `.registry` before
  `.runner`). The imports remain INSIDE the function (lazy — stdlib-only invariant
  preserved).
- **ruff format**: Applied.

### src/retail/metric_drift.py
- **E501 x2**: Split the `if definition and ...` compound condition at line 330
  into a multi-line `if (...)` block. Comment on line 329 shortened by one word
  ("respected" instead of "is respected") to fit within 88 chars.
- **ruff format**: Applied.

## Gate command output

```
$ python -m ruff format --check src/ tests/
47 files already formatted

$ python -m ruff check src/ tests/
All checks passed!
```

## Full suite result

```
$ python -m pytest -m unit -q
389 passed, 1 skipped in 9.64s
```

Coverage: 94% overall. All stdlib-guard subprocess tests (test_dax_gen_import_is_stdlib_only,
test_retail_rules_pulls_neither_dax_gen_nor_yaml) passed — no lazy imports were moved.

## Commit hash

See git log for the commit created after this report.
