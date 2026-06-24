# Capturing the real golden PBIP (MANUAL, LOCAL — requires Power BI Desktop or pbi-cli)

> NOT run in CI or by the coding agent. Do this once on a Windows machine with Power BI
> Desktop (PBIP preview enabled) or `pbi-cli` installed, then commit the result.

## Option A — pbi-cli (preferred, scriptable)

From the repo root:

    pbi report create --name RetailGold --output tests/fixtures/golden_pbip

Then add one `Sales` table, one `Date` table, one `TotalSales` measure, and one
relationship, and **Mark the Date table as a date table** in Desktop (the whole point
of this capture is the real "Mark as Date Table" TMDL literal — D7's anchor).

## Option B — Power BI Desktop Save As

1. Enable PBIP: File > Options > Preview features > "Power BI Project (.pbip) save option".
2. Build the minimal model: `Sales` (with `Amount`), `Date` (with `Date`), measure
   `TotalSales = SUM(Sales[Amount])`, a `Sales.Date -> Date.Date` relationship.
3. Mark `Date` as a date table (Table tools > Mark as date table).
4. File > Save as > Power BI Project (.pbip), target `tests/fixtures/golden_pbip`.

## After capture — reconcile and verify

1. Open the real `*.SemanticModel/definition/*.tmdl` and compare each pinned literal in
   `src/retail/tmdl.py`'s docstring against the real text. The likely mismatch is the
   date-table marker (table-level annotation vs `dataCategory: Time`). Update the
   docstring literal, the fixture, AND the `test_model_pins_provisional_date_table_marker`
   assertion in `tests/unit/test_tmdl.py`. Remove the `*** PROVISIONAL ***` banner once
   confirmed.
2. Verify the real definition files are tracked and the local-only files are ignored:

       git add tests/fixtures/golden_pbip
       git ls-files tests/fixtures/golden_pbip | grep "definition/"
       git check-ignore "tests/fixtures/golden_pbip/RetailGold.SemanticModel/.pbi/cache.abf"

   The first must list the `definition/` TMDL/PBIR files; the second must print the
   `cache.abf` path (ignored). If `definition/` files are missing from `git ls-files`,
   the model is being dropped from git — fix `.gitignore` before committing.
3. Re-run `pytest -m unit tests/unit/test_tmdl.py -v` — it must stay green against the
   real fixture.
