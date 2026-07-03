# Contract: Worked-Example Completeness

**Feature**: `specs/084-worked-example-factory/` | **Phase**: 1 (design)

**What this is.** The checkable bar for "this candidate worked example is
complete," at each of the two tiers defined in `data-model.md`. A reviewer
(human or a future governance skill) applies this contract item-by-item against
a candidate `mappings/<table>/` + `docs/worked-examples/<table>.md` set. It is
calibrated against `retail_store_sales` (SC-002: applying it to that example
must yield "complete").

**What this is not.** Not a new `retail check` rule (this feature adds none -- FR-012, Non-Goals). Not an automated validator. Not a numeric score -- every
item is a binary yes/no with a cited artifact, same discipline as
`templates/maturity-report.md`'s rungs and `docs/readiness/readiness-model.md`'s
four statuses.

---

## Tier 1 -- Repo-only completeness (factory-achievable)

Every item below MUST be satisfiable by an author with no live DB and no
human reviewer present, and MUST cite a specific file/line, not an assertion.

### A. Domain selection (done before any artifact is authored)

- [ ] C-A1. The candidate domain is named and at least one genericity axis it
      stresses (relative to existing examples) is stated in prose, per
      `research.md` Sec 1's selection rule.
- [ ] C-A2. The domain is confirmed expressible with the currently-shipped RC
      defaults and `retail check` rule set -- no new default or rule is required
      (if this fails, the domain is deferred per spec.md FR-012; not a
      completeness failure of the *process*, but the example cannot proceed).
- [ ] C-A3. No client-specific fact (C086 billing codes, segment rollups,
      insurance/PII columns) appears anywhere in the candidate's artifacts.

### B. Source Ready

- [ ] C-B1. `mappings/<table>/source-profile.md` exists, every `<placeholder>`
      filled, missingness measured as `'' OR NULL` (not `IS NULL` alone), grain
      and candidate PK stated with numbers (per the template's own Exit Gate
      checklist).
- [ ] C-B2. If the source is a file (csv/excel), the File-source addendum is
      filled (format, encoding `[PROPOSED]`, delimiter, header row, in-scope
      sheet list) per the template's own file-source completeness rule.

### C. Mapping Ready (artifacts; the human approval is Tier 2)

- [ ] C-C1. `mappings/<table>/source-map.yaml` exists: grain and primary key
      decided first (`meta.grain`, `meta.primary_key`), every source column
      has an entry (`columns[]`), every deviation from RC1-RC16 listed under
      `defaults.deviations[]`.
- [ ] C-C2. `mappings/<table>/assumptions.md` exists: the 16-row adopted/
      deviated table filled, and the **integrity invariant** holds -- every row
      marked `[x]` there has a matching entry in its Deviations section, and
      every deviation cites a triggering data fact from `source-profile.md`
      (per the template's own stated invariant).
- [ ] C-C3. `mappings/<table>/unresolved-questions.md` exists with `Gate
      status: CLEARED` -- every row's `Status` is `answered` with a filled
      `Resolution`, not left `open`.
- [ ] C-C4. No deviation, question, or resolution was invented to "fill the
      shape" -- each cites a real profiled number or a real recorded answer
      (per `assumptions.md`'s own "No fabricated examples" rule).

### D. Silver Ready / Gold Ready (build artifacts)

- [ ] C-D1. A numbered, idempotent silver migration exists
      (`warehouse/migrations/NNNN_create_silver_<table>.sql`), builds the
      table at the declared grain, and `retail check` exits 0 over it.
- [ ] C-D2. A numbered gold migration exists, builds a Kimball star (fact +
      conformed dims, `-1` unknown member, FK `COALESCE`, degenerate dims per
      RC14), and includes a contiguous `generate_series` date dimension
      (RC15).
- [ ] C-D3. `mappings/<table>/readiness-status.yaml`'s `silver_ready` and
      `gold_ready` stages are recorded as `pass` **only if** backed by a real
      `retail check` exit-0 run (silver) and a real `retail validate` exit-0
      run (gold) with cited evidence; if no live DB was available, these
      stages are `blocked` or carry `[PENDING LIVE PROFILE]` evidence -- never a
      `pass` without the run that backs it.
- [ ] C-D4. `mappings/<table>/reconciliation-report.md` exists; if no live DB
      was reachable, every numeric cell stays an unfilled `<placeholder>` (or
      is explicitly marked pending) rather than a fabricated number.

### E. Semantic Model Ready (contracts; artifacts only -- approval is Tier 2)

- [ ] C-E1. At least one `mappings/<table>/metrics/*.yaml` metric contract
      exists per `templates/metric-contract.yaml`'s shape, each with a stated
      grain and formula intent -- no contract has an invented `expected_value`
      (that field, if present, must cite the live aggregate it was checked
      against; absent a live run, it stays unfilled).
- [ ] C-E2. A governed PBIP/TMDL model exists under `powerbi/<Table>.
      SemanticModel/`, with a parameterized connection (no baked-in host or
      DSN -- repo CLAUDE.md hard rule).

### F. Dashboard Ready (design artifacts only -- approval is Tier 2)

- [ ] C-F1. `mappings/<table>/design/` contains a layout, a visual list, and a
      binding map; every measure-bearing visual binds to exactly one metric
      contract (zero orphan visuals, mirroring retail_store_sales Sec 6).
- [ ] C-F2. The design records what is explicitly out of answerable scope
      (e.g. no margin metric if no cost data exists) rather than inventing a
      metric to fill a visual (mirroring retail_store_sales Sec 6's stated
      practice).

### G. Publish Ready (pack artifacts only -- approval is Tier 2)

- [ ] C-G1. `mappings/<table>/handoff/` contains a filled handoff pack and a
      review checklist per `templates/handoff/`'s shape.

### H. Readiness status, narrative, and index (cross-cutting)

- [ ] C-H1. `mappings/<table>/readiness-status.yaml` exists, covers all seven
      stages, and every `pass` entry cites real `evidence[]` -- no stage is
      marked `pass` without evidence (hard rule: no fake confidence).
- [ ] C-H2. `mappings/<table>/readiness-status.yaml`'s `approvals[]` is either
      empty or contains only entries with a genuinely named human + authority
      class (never a bare role, never the authoring agent's own name) -- see
      Tier 2 below for when entries are expected to exist.
- [ ] C-H3. `docs/worked-examples/<table>.md` exists, follows the section
      structure of `docs/worked-examples/retail-store-sales.md` (readiness-at-
      a-glance table, one section per stage reached, "copy / watch" notes for
      future tables, a "See also" section).
- [ ] C-H4. `docs/worked-examples/README.md` "The examples" table has a new
      row for `<table>.md`.
- [ ] C-H5. `retail check` exits 0 over the full new artifact set (repo-wide,
      or scoped to the new paths) -- reported with the exact command and exit
      code, never claimed without having been run.

---

## Tier 2 -- Human/live-gated completeness (never factory-produced)

These items can ONLY be satisfied by a named human and/or a live DB
connection. A factory process (agent, no human present, no DB) MUST leave every
one of these as an explicit gap, never simulate, pre-fill, or infer a
satisfying value.

- [ ] C-T2-0 (**file-source candidates only**). If the candidate's `source_kind`
      is `csv` or `excel` (see `templates/readiness-status.yaml`'s own
      conditional comment), `approvals[]` additionally contains a
      `source_ready` entry with a named data-owner confirming the `[PROPOSED]`
      encoding/delimiter/header the profile's numbers rest on. This item does
      not apply to a DB-table source (the default). *(Added on review -- see
      `analysis/analyze-report.md` Sec 3: the original draft of this contract
      omitted the fifth, conditional approval seam that a file source
      requires.)*
- [ ] C-T2-1. `approvals[]` contains a `mapping_ready` entry with a named human
      + authority class (`analyst` or `data_owner`), dated.
- [ ] C-T2-2. A live `retail validate` run backs `gold_ready: pass`, with the
      real PK-uniqueness / date-coverage / 0-orphan-FK / penny-exact-
      reconciliation numbers filled into `reconciliation-report.md`.
- [ ] C-T2-3. `approvals[]` contains a `semantic_model_ready` entry with a
      named metric owner, dated, confirming every model measure binds 1:1 to
      an approved contract.
- [ ] C-T2-4. `approvals[]` contains a `dashboard_ready` entry with a named
      report owner, dated, confirming the visual-to-contract binding map.
- [ ] C-T2-5. `approvals[]` contains a `publish_ready` entry with a named
      data-owner/governance approval, dated -- understanding that, per
      retail_store_sales' own precedent, this entry may later be honestly
      retracted (`warning`) if the approved artifact materially changes; a
      `warning` terminal state at Publish Ready is an acceptable, not a
      failing, outcome of this contract.

---

## Verdict rule

- **Tier-1 complete**: every unchecked item in sections A-H above is checked,
  each against a cited real file/run -- not merely "exists" but "exists and
  matches its own template's stated exit criteria."
- **Tier-1-and-2 complete** (the retail_store_sales bar): Tier 1, plus every
  C-T2-* item checked with a named human recorded.
- **Not complete**: any unchecked Tier-1 item. Report the specific item, never
  a percentage (e.g. "6/9 items" is itself a soft score and MUST NOT be
  reported as the verdict -- report the item, per hard rule #9's spirit).

## Calibration check (SC-002)

Applying this contract to `mappings/retail_store_sales/` +
`docs/worked-examples/retail-store-sales.md` (read during this feature's
research):

- Tier 1 sections A-H: all satisfied (source profile filled with numbers;
  source-map + assumptions + unresolved-questions gate CLEARED; silver+gold
  migrations exist and are cited as `retail check`/`retail validate` exit 0;
  metrics + governed TMDL model exist; design set with zero orphan visuals;
  handoff pack exists; readiness-status.yaml's `pass` entries all cite
  evidence; narrative doc follows its own stated section structure; indexed in
  `docs/worked-examples/README.md`).
- Tier 2: C-T2-1 through C-T2-4 satisfied (data_owner approvals recorded,
  2026-06-25, for mapping_ready / semantic_model_ready / dashboard_ready).
  C-T2-5 (`publish_ready`) is at `warning`, not `pass` -- an approval was
  recorded then honestly retracted after a contract correction (doc Sec 7). Per
  this contract's own Verdict rule, a `warning` terminal state at Publish Ready
  is an acceptable outcome, so retail_store_sales is judged **Tier-1-and-2
  complete through Dashboard Ready, with Publish Ready honestly at `warning`** -- matching the doc's own stated verdict exactly. This confirms the contract
  is calibrated to the existing trusted instance (SC-002), neither stricter
  (which would fail retail_store_sales) nor looser (which would pass an
  incomplete example).
