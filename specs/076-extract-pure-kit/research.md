# Phase 0 Research: Extract the pure kit

## R1. The tool is already package-clean (the key finding)

**Decision**: Treat "extract the pure tool" as *mostly already done at the package
boundary* — the remaining work is cleaning the SOURCE TREE + a history decision.

**Evidence**: `pyproject.toml:41` → `packages = ["src/retail"]`. The built wheel
therefore contains ONLY `src/retail/**` — no `mappings/`, `warehouse/`, `pipelines/`, or
worked examples. Verified conceptually against the packaging config; the acceptance
criteria include a `unzip -l dist/*.whl` check to prove it empirically in the future PR.
So an adopter who `pip install`s already gets a data-free tool; `retail init` then
bootstraps the kit into their repo. This is why the RECOMMENDATION is package+archive,
not a repo split — the package split already exists.

## R2. Data-independence of the tool (non-regression basis)

**Decision**: The tool depends on `mappings/<table>/…` as a runtime PATH CONVENTION, not
on the C086 instances — so removing the instances cannot regress it.

**Evidence**: `grep -rn "mappings/" src/retail/` shows only convention regexes
(`^mappings/[^/]+/metrics/[^/]+\.ya?ml$` in `assumptions.py` / `assumption_coherence.py`)
and help text (`cli.py`) — never a hardcoded `c086`/`sales_c086` path. The unit suite
uses tmp-repo fixtures + the committed `.seshat/kit-source.yaml`, not the C086 data
(confirmed by 070-074 test authoring). The one risk is a stray test that reads a C086
instance → the migration plan makes "migrate data-coupled tests FIRST" step 2.

## R3. The security posture is scoped by WHAT is committed

**Decision**: current-tip redaction now; git-history purge only on a public-release /
erasure trigger (see plan Security section).

**Evidence**:
- `git ls-files mappings/ warehouse/ | grep -iE '\.csv|\.parquet|\.xlsx'` → EMPTY. No raw
  customer rows committed; the exposure is client-identifying schema/business content
  (`ezaby`, `insurance_no`, segment rollups), not PII data.
- No credential/DSN in the tree (PBIP uses `<your-db-host>` placeholders). **BUT
  (corrected post-review): the real cluster id `db-pgsql-fra1-29712` + db name
  `ezaby_demo` ARE committed in 7 files** — host-identifying, not a secret. It evades the
  C2 gate (FQDN-only regex) and the first-draft grep; both the redaction list and
  acceptance markers now include it.
- **`powerbi/` ships a full client BI model** (`c086 _sales.*` + the generically-named
  `Retailgold.*` = the same c086 star). This was MISSED by the first classification —
  the fix adds `powerbi/` + a complete top-level enumeration + a catch-all so no dir is
  classified on its NAME alone.
- `git rev-list --count HEAD` → 302. A purge rewrites all 302 (breaks hashes/PR links).
  Cost is disproportionate to a private repo whose shipped artifact (the wheel) never
  held the data. Host id is not a secret → does not force a purge NOW; add it to the
  redaction, escalate to purge only on public-release / erasure trigger.

**Alternatives**: *purge now* — rejected as default (302-commit blast radius, no current
public/erasure trigger); kept as the explicit escalation if the repo goes public.

## R4. The ASSESS-row method (the 3 undecided artifacts)

**Decision**: Three artifacts need a per-file look before final classification, and the
migration plan makes that look STEP 1 (never remove before classifying):

- `mappings/retail_store_sales/` — is it a fictional/synthetic store (→ promote to the
  shipped SYNTHETIC example) or client-derived (→ ARCHIVE)? Determined by reading its
  `source-map.yaml` `source_system` / whether names are fictional.
- `warehouse/schema/` + `warehouse/gold/` — generic DDL conventions (→ KEEP) vs
  C086-specific tables (→ ARCHIVE). Determined by whether table/column names are generic.
- `pipelines/load_bronze.py` — a generic loader pattern (→ KEEP/genericize) vs
  C086-specific ingestion (→ ARCHIVE; also YAGNI per CLAUDE.md "no automated ingestion").

**Rationale**: These are genuine judgment reads, not guessable from the file name. Making
them explicit steps (with the decision rule for each) keeps the classification honest and
lets the future PR execute without re-deciding.

## R5. Ordering dependency on the in-flight c086 work

**Decision**: The extraction PR is BLOCKED until the c086 supersession work
(uncommitted edits to `mappings/c086/{source-map,assumptions,reconciliation-report,…}` +
the new `README.md`, and `sales_c086/` gaining its `readiness-status.yaml`) lands or is
discarded.

**Rationale**: Removing/archiving `mappings/c086` + `sales_c086` while a human is mid-
reorganizing them would collide and could lose their work. The two operations touch the
same files. Sequence, don't overlap. This spec touched none of it (SC-006).

## R6. Synthetic-example approach

**Decision (recommended, ratify-confirmed)**: narrative-only worked example + ONE tiny
synthetic table.

**Rationale**: `first-hour-compass` offers a worked example to "steer by" — it needs
*something*. A narrative example (structure + prose, no data) covers the pattern; one
tiny synthetic table (a fictional 2-3 column store-sales sample) lets `profile` have a
demoable target without any live DB or client data. Building a large synthetic warehouse
is YAGNI; narrative + a token table is the honest minimum. Final call at ratify.
