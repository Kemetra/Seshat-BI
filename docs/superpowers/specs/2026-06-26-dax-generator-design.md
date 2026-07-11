# DAX Generator — Phase 1 design

- **Date:** 2026-06-26
- **Status:** Design (approved section-by-section; awaiting spec-review gate before implementation plan)
- **Builds on:** ADR-0007 (L1–L4 governance model), `src/seshat/metric_drift.py` (L3 drift checker, PR #32), `src/seshat/rules/dax.py` (D1–D11, C1), F009 metric-contract store.
- **Phase:** 1 of 3. This spec covers the **DAX Generator** only. Phase 2 (Analyzer/Refiner) and Phase 3 (goal-driven live-data layer) are separate specs that plug into the seams documented here.

---

## 1. Summary & guiding principle

A deterministic, stdlib-pure **DAX Generator**: given a metric contract's structured `definition` block, it emits a best-practice DAX measure (+ a full TMDL block) and **proves the output before returning it**.

**Guiding principle — generate ⇄ verify are inverse functions.**
`metric_drift.check_measure_drift(dax, definition)` answers *"does this DAX match this contract?"*. The generator answers *"what DAX matches this contract?"* — then feeds its own output straight back through the checker. The two compose into a **self-proving loop**: the generator structurally cannot emit a measure that would later fail the L3 gate. This is only possible because the repo already built the checker half.

**Fail-closed everywhere.** `pass` is the only acceptable round-trip result. `drift`, `escalate`, `skip`, parser uncertainty, or an unsupported shape all produce a refusal (`GenResult(ok=False, reason=...)`) — never a warning, never a best-effort emit. Refuse-rather-than-guess mirrors L3's `escalate`-by-default stance.

This is the **first code in the repo that produces DAX** rather than validating it (confirmed greenfield). It is a new layer that *feeds* the existing validators; it collides with no existing seam.

---

## 2. Scope & non-goals

### In scope (Phase 1)
- **Two measure shapes**, discriminated by `definition.kind`:
  - `kind: base` — a single aggregation over a `gold.*` column/table, with optional filters.
  - `kind: ratio` — `DIVIDE(numerator, denominator)` where each side is an **inline** aggregation.
- **5 aggregations:** `sum`, `count`, `distinct_count`, `average`, `count_rows`.
- **Existing predicate whitelist only:** `is_true`, `is_not_null` (reused verbatim from `metric_drift`).
- **CLI:** `retail generate --contract <path>`.
- **Internal API:** `generate_measure(definition, *, name, ...) -> GenResult`.
- **Additive L3 extension:** teach `check_measure_drift` to verify `kind: base` measures, zero-regression for existing ratios.

### Explicit non-goals (deferred / forbidden)
| Non-goal | Why |
|----------|-----|
| Cross-contract measure refs (`numerator: {ref: OtherMeasure}`) | Needs a contract-resolution graph + transitive-trust handling. **Phase 2.** Phase 1 ratios are inline-only and self-contained. |
| Time-intelligence (YoY, MTD, rolling) | Bigger contract schema + new verify logic. Later phase. |
| SUM/COUNT beyond the 5-agg whitelist | YAGNI; the 5 cover the bulk of retail base measures. |
| Writing into the live `powerbi/**` model | Violates "modules never mutate truth." The generator *suggests*; a human pastes. |
| DB connection | Stdlib-pure layer; live data is Phase 3, behind the existing `retail validate` seam. |
| LLM / natural-language intent | Defining meaning from prose is forbidden to the core (ADR-0007). NL front-end is an optional, human-approval-gated Phase-3 add-on. |
| Free-form DAX | Only the two known shapes are emittable. |
| Broad contract migration | This slice touches `templates/metric-contract.yaml` as **comments/documentation only**. No existing contracts are rewritten. |

---

## 3. Architecture & module boundaries

### New module: `src/seshat/dax_gen.py`
A **lazy module**, mirroring `metric_drift.py` exactly:
- **Stdlib-pure at import.** `yaml` is touched **only** inside the contract loader (`load_contract`), never at module scope.
- **Never imported by the `retail check` core chain** (`retail.cli → retail.rules`). The guarded stdlib-only invariant (`dependencies = []`) is preserved; a new subprocess test asserts `import retail.rules` pulls in neither `dax_gen` nor `yaml`.
- Estimated ~250–300 LOC.

### Extended module: `src/seshat/metric_drift.py`
Add a `kind: base | ratio` branch to `check_measure_drift`. **Additive and zero-regression:**
- When `kind` is **absent**, the function behaves exactly as today (the existing path requiring `additive: false` + `denominator`). Existing contracts are byte-for-byte untouched.
- `kind: ratio` is the new explicit spelling of the existing ratio path. **Resolved ambiguity:** today's code escalates unless `definition.additive is False` (`metric_drift.py:246`). So `kind: ratio` implies the ratio/non-additive semantics — the new branch treats `kind: ratio` as equivalent to `additive: false` for routing into the denominator-filter-set check, and does **not** require the contract to also restate `additive: false`. (A `kind: ratio` contract that *also* sets `additive: true` is contradictory → `escalate`.) This means the generator can verify a `kind: ratio` contract that omits `additive`, where the legacy code alone would have escalated it.
- `kind: base` is a new branch: verify the emitted aggregation + filter-set against `definition` (no DIVIDE, no denominator). `additive` is irrelevant to a base measure and is neither required nor consulted.
- New tests assert existing ratio contracts (`kind` absent) produce the same verdict (see §8, regression).

### The define/check boundary (respected verbatim)
`templates/metric-contract.yaml` forbids DAX in *every field* (lines 15–21, 160–162). Therefore:
- The generator's structured input is the **`definition`** block (implementation-side, where `additive`/`numerator`/`denominator` already live) — **not** `formula_intent` or `binds_to` (intent-side).
- `formula_intent` stays plain-language business intent. It feeds **only** the `///` doc comment, as documentation metadata. It **must never** influence DAX generation, drift verification, filter inference, or any semantic decision. The **`definition` block is the sole semantic input.**
- `format_string` / `display_folder` are **generator parameters with defaults**, not new contract-intent fields.

### Data flow
```
contract.yaml ─(load_contract: lazy yaml)→ {definition, name, formula_intent}
                                      │
              definition ───────────────────────────► generate_measure(definition, name=…,
                                      │                  format_string=…, display_folder=…,
              formula_intent ──(doc only)──────────────► doc_intent=…)
                                      │
                  ┌──────── VERIFY (in order) ────────┐
                  │ 1. check_measure_drift(dax, def)  │  ← MUST return "pass" (else REFUSE)
                  │ 2. D1–D11 rules over TMDL block   │  ← MUST have zero ERROR (else REFUSE)
                  └───────────────────────────────────┘
                                      │
                   pass+clean → GenResult(ok=True, …)  │  else → GenResult(ok=False, reason)
```

---

## 4. The contract `definition` schema (additive)

Discriminated by `kind`. **`kind` absent → today's exact ratio behavior** (legacy `additive: false` contracts keep working untouched). `templates/metric-contract.yaml` documents this in comments only — no migration.

### `kind: base`
```yaml
definition:
  kind: base
  aggregation: sum            # sum | count | distinct_count | average | count_rows
  source:
    table: gold.fct_sales     # gold.* ONLY (reuses the gold-only guard)
    column: net_amount        # see column rule below
  filter:                     # OPTIONAL; reuses the EXISTING predicate whitelist
    - {column: discount_applied, op: is_true}     # op ∈ {is_true, is_not_null}
  format_string: "#,0"        # OPTIONAL generator hint (presentation; default by aggregation)
  display_folder: "Sales"     # OPTIONAL generator hint (default: contract-derived)
```

**Aggregation → DAX function (1:1, deterministic):**
| aggregation | DAX | `source.column` |
|-------------|-----|-----------------|
| `sum` | `SUM(T[col])` | **required** |
| `count` | `COUNT(T[col])` | **required** |
| `distinct_count` | `DISTINCTCOUNT(T[col])` | **required** |
| `average` | `AVERAGE(T[col])` | **required** |
| `count_rows` | `COUNTROWS(T)` | **forbidden** (table only) |

**Emit rule:** no filter → bare aggregation; filter present → `CALCULATE(<agg>, <pred>, …)`.
```dax
CALCULATE ( SUM ( 'gold fct_sales'[net_amount] ), 'gold fct_sales'[discount_applied] = TRUE() )
```

### `kind: ratio`
```yaml
definition:
  kind: ratio
  numerator:   {aggregation: count_rows, filter: [{column: discount_applied, op: is_true}]}
  denominator: {aggregation: count_rows, filter: [{column: discount_applied, op: is_not_null}]}
  format_string: "0.0%"
  display_folder: "Rates"
```
Each side is an **inline** aggregation (same shape/rules as base). No cross-contract `ref:` in Phase 1.
```dax
DIVIDE (
  CALCULATE ( COUNTROWS ( 'gold fct_sales' ), 'gold fct_sales'[discount_applied] = TRUE() ),
  CALCULATE ( COUNTROWS ( 'gold fct_sales' ), NOT ( ISBLANK ( 'gold fct_sales'[discount_applied] ) ) )
)
```

**Canonical predicate spellings** (the generator emits exactly the spellings L3 recognizes):
- `is_true` → `col = TRUE()`
- `is_not_null` → `NOT(ISBLANK(col))`

---

## 5. Generate → verify → refuse pipeline

`generate_measure(definition, *, name, format_string=None, display_folder=None, doc_intent=None) -> GenResult`.
**Fail-closed at every step.** The function **never raises** on a bad contract — it returns a refusal. Exceptions are reserved for genuine programmer errors (e.g., `name` not passed).

```
STEP 1 — VALIDATE SHAPE (pre-emit guards)
  • kind ∈ {base, ratio}? else REFUSE
  • base: aggregation in whitelist; column REQUIRED for sum/count/distinct_count/average,
    FORBIDDEN for count_rows; table is gold.* ; filters use known ops {is_true, is_not_null}
  • ratio: numerator & denominator each valid inline aggregations
  • any malformed/unrealizable field → REFUSE("cannot realize field X")

STEP 2 — EMIT CANONICAL DAX (deterministic templates)
  • base no-filter:  SUM('gold t'[col])
  • base + filter:   CALCULATE(SUM(...), <pred>, ...)
  • ratio:           DIVIDE(<num>, <den>)
  • predicates in canonical L3-recognized spelling (is_true → col = TRUE();
    is_not_null → NOT(ISBLANK(col)))

STEP 3 — SEMANTIC VERIFY (the inverse round-trip)  ★ fail-closed, runs BEFORE D-rules
  v = check_measure_drift(dax, definition)
  v.status == "pass"  → continue
  drift | escalate | skip | any uncertainty → REFUSE(v.detail)

STEP 4 — BUILD TMDL BLOCK + FORM VERIFY
  • assemble: name / expression / formatString / displayFolder / /// doc (from doc_intent)
  • run D1–D11 over the block; any ERROR → REFUSE
  • WARNING is collected into GenResult.warnings (non-blocking — matches the gate's WARNING semantics)

RETURN
  GenResult(ok=True, dax, tmdl_block, warnings=(...))    on success
  GenResult(ok=False, reason=...)                         on any refusal
```

**Ordering rationale:** L3 (semantics) before D-rules (form). D-rules prove form/governance, but they are **not a substitute** for L3 — only L3 proves the generated DAX actually *means* the contract. Semantics first, form second.

### `GenResult` — a sum type
Frozen dataclass; the two states never share populated fields:
```python
@dataclass(frozen=True)
class GenResult:
    ok: bool
    dax: str | None = None          # populated iff ok
    tmdl_block: str | None = None   # populated iff ok
    reason: str | None = None       # populated iff NOT ok
    warnings: tuple[str, ...] = ()  # non-blocking D-rule WARNINGs (ok may still be True)
```
- **On `ok=False`, both `dax` and `tmdl_block` are `None`** — structurally impossible for a caller to fish an unverified partial out of a refusal.
- `__post_init__` asserts the invariant (`ok` XOR `reason` populated; `ok` ⟹ `dax` and `tmdl_block` set). A violation is a **programmer error → raise** (consistent with "exceptions for programmer errors only").

---

## 6. CLI surface & internal API

### Internal API (the engine — what Phase 2/3 reuse)
```python
# src/seshat/dax_gen.py
def generate_measure(definition: dict, *, name: str,
                     format_string: str | None = None,
                     display_folder: str | None = None,
                     doc_intent: str | None = None) -> GenResult: ...

def load_contract(path: str) -> dict: ...   # lazy `import yaml` inside — the ONLY yaml touch
```
`doc_intent` is passed **separately** by the CLI (read from `formula_intent`) and reaches only the `///` comment builder — never the generate/verify path. The signature makes the boundary explicit.

### CLI subcommand
Matches the existing `check` / `validate` / `semantic-check` pattern in `cli.py`:
```
retail generate --contract <path> [--out <path>] [--format tmdl|json]
```
| Flag | Behavior |
|------|----------|
| `--contract PATH` | Required. The metric contract YAML. CLI reads `definition` + `name` + `formula_intent`. |
| `--format tmdl` (default) | On success, prints the verified TMDL measure block to stdout. |
| `--format json` | On success, prints `GenResult` as JSON to stdout (for tooling / Phase-2 consumers). |
| `--out PATH` | Optional. Writes the verified TMDL block to a new standalone file the user names. |

### CLI guards ("modules don't mutate truth" + fail-closed)
- **`--out` never mutates the live model.** The target path is **resolved to its real canonical path first** (`Path(out).resolve()` — normalizing `..`, absolute paths, symlinks, and Windows `\`/`/`), then checked against the resolved `powerbi/` tree. Any resolved path inside `powerbi/**` is **refused**. The check is on the resolved path, never the raw string.
- **`--out` refuses to overwrite an existing file** (Phase 1). Protects verified artifacts from accidental replacement. A `--force` flag is a documented future seam, **not built now**.
- **Exit codes:** `0` = generated & verified; `1` = refusal (`ok=False`).
- **stdout = verified output only, always** (format-independent invariant):
  - success: verified content to stdout (TMDL block, or JSON), exit 0.
  - refusal (`--format tmdl`): **stdout empty**, reason to **stderr**, exit 1.
  - refusal (`--format json`): **stdout empty**, refusal JSON/reason to **stderr**, exit 1.
- Consequence: `retail generate --contract c.yaml > out.tmdl` is **fail-closed** — `out.tmdl` is empty on refusal, populated only on a verified pass, in either format.

**Refusal output** (exit 1, stderr): `[refused] DiscRate: denominator filter-set [(discount_applied, is_true)] != contract [(discount_applied, is_not_null)]`

---

## 7. Error handling

- **Bad/unsupported contracts are product-level refusals**, returned as `GenResult(ok=False, reason=...)`. The generator never raises on them. The `reason` carries the precise cause (e.g., the `Verdict.detail` from L3, or "count_rows must not specify source.column").
- **Exceptions are reserved for programmer errors only** — missing required `name` argument, a `GenResult` that violates its sum-type invariant.
- **CLI errors** (missing `--contract`, unreadable file, malformed YAML) print a clear message to stderr and exit 1, matching the other subcommands.

---

## 8. Testing strategy

**Philosophy:** the headline guarantee is *"every emitted measure verifies."* Tests are primarily **table-driven round-trip tests** (`pytest.mark.parametrize`). **No new property-testing dependency** (e.g. Hypothesis) — the repo polices dependency creep and `parametrize` is already in use and sufficient.

### New: `tests/unit/test_dax_gen.py`
| Group | Proves |
|-------|--------|
| **Round-trip (core property)** | For every supported shape (5 aggs × {filter, no-filter} × {base, ratio}), `generate_measure` returns `ok=True` **and** feeding `result.dax` back through `check_measure_drift` returns `pass`. For a **base** measure this re-verifies aggregation + full filter-set. For a **ratio** this re-verifies the **same denominator-filter-set check that gates the model** (L3 is denominator-only by design); the numerator's correctness is pinned separately by the `_emit_*` round-trip/emit tests, not re-derived by the L3 pass. The inverse-function guarantee, mechanically enforced — gating exactly what the model's own gate gates. |
| **D-rule cleanliness** | Every emitted `tmdl_block` passes D1–D11 with **zero ERRORs** (PascalCase, displayFolder, DIVIDE-not-`/`, `///` doc, no hardcoded dates, no `FILTER(ALL(`). |
| **Refusal / fail-closed** | Unknown `kind`; bad aggregation; sum/count/distinct_count/average **without** column; count_rows **with** column; non-`gold.*` table; unknown filter op; malformed `definition` → each returns `ok=False`, **`dax is None` and `tmdl_block is None`**, with a precise `reason`. |
| **Sum-type invariant** | `GenResult.__post_init__` raises on a malformed result (`ok=True` + no dax; `ok=False` + populated dax). |
| **`doc_intent` isolation** | Two contracts with **identical `definition` but different `formula_intent`** produce **identical DAX & verification**, differing only in the `///` comment. Proves intent never touches semantics. |
| **CLI behavior** | exit 0/1; stdout empty on refusal (both formats); reason on stderr; `--format json` shape; via `subprocess`, like existing CLI tests. |
| **`--out` overwrite guard** | Refuses an existing `--out` path. |
| **`--out` path-traversal guard** | `../powerbi/...` and an absolute path resolving inside `powerbi/` are **refused**, asserted on the **resolved** path (Windows separators included). A symlink-into-`powerbi` case is included but **platform-safe**: if Windows symlink privileges are unavailable in CI, the symlink case `skip`s — the `../powerbi` and absolute-path cases **never** skip. |

### Extended: `tests/unit/test_metric_drift.py`
| Group | Proves |
|-------|--------|
| **Zero behavioral regression (the crux)** | Existing ratio contracts (`kind` absent, `additive: false`) yield the **same status + same semantic decision** as before; all existing tests stay green. Byte-identical `Verdict.detail` is the **preference** where stable snapshots exist; the **minimum required guarantee** is zero behavioral regression. |
| **`kind: base` verify** | A base-measure DAX + its `kind: base` definition → `pass`; wrong aggregation/column/filter → `drift`; unrecognized → `escalate`. Closes the loop for base measures. |
| **Stdlib invariant (extend existing guard)** | `import retail.rules` still pulls in **neither** `dax_gen` **nor** `yaml` — same subprocess guard already protecting `metric_drift`. |

### File plan
```
NEW   src/seshat/dax_gen.py            (~250–300 LOC; lazy module, stdlib-pure import)
EDIT  src/seshat/metric_drift.py       (additive kind:base branch + base verify helper)
EDIT  src/seshat/cli.py                (new `generate` subparser + _run_generate handler)
EDIT  templates/metric-contract.yaml   (document the additive definition.kind schema — comments only)
NEW   tests/unit/test_dax_gen.py
EDIT  tests/unit/test_metric_drift.py  (regression + kind:base + stdlib guard)
NEW   tests/fixtures/contracts/*.yaml  (base / ratio / refusal fixtures)
```

### Definition of done
- `ruff format --check src/ tests/` clean.
- `ruff check src/ tests/` clean.
- `pytest -m unit` green, including the full existing suite (349 tests at baseline) **still passing**.
- Round-trip, regression, and path-guard tests present.
- Coverage ≥90% on `dax_gen.py` (repo baseline is 94%).

---

## 9. Phase-2 / Phase-3 seams (documented, NOT built)

### Extensibility invariant (binding)
> **Every Phase-1 narrowing is a refusal guard, not a structural wall. Lifting any one of them in a future phase must be purely additive — a new `kind` value, a new whitelist entry, a new ratio-side branch, or a new verifier branch — and must not require changing existing public signatures or breaking existing contracts.**

**Phase 1 stays small and safe without becoming a dead end.** Concretely, each deferred capability has a known additive path:

| Future capability | Additive path (no rework) |
|---|---|
| Cross-contract `ref:` (Phase 2) | New branch in the single ratio-side parser; inline contracts unaffected. |
| More aggregations (`min`, `max`, …) | New row in the aggregation→DAX dict; unknown-agg refusals become accepts. |
| More filter ops (`is_false`, `value_equality`, `in_set`) | Inherited from L3's own widening whitelist via the shared predicate emitter. |
| Time-intelligence (YoY, MTD) | New `kind:` value — the discriminator was chosen (over a boolean) for exactly this. |
| Analyzer/Refiner (Phase 2) | Reuses the rule-run + verify helpers (kept as reusable functions per below). |
| Live-data goal loop (Phase 3) | Separate module behind the existing `retail validate` lazy-`psycopg2` seam. |
| NL front-end | Optional upstream stage emitting a human-approved `definition`; engine input unchanged. |

Two structural choices make these guards-not-walls and are load-bearing: (a) **`kind` is an open discriminator string, not a boolean flag**; (b) **`GenResult` is a stable return type** Phase 2 reuses verbatim.

### Expansion Roadmap / Deferred Capabilities
The following are **documented seams only — NOT Phase-1 deliverables.** They name where future work attaches without committing to building any of it now. Each is reachable via the additive-only path above.

1. **Cross-contract `ref:`** — a ratio side referencing another contract's measure (`{ref: TotalTxns}`) instead of an inline aggregation.
2. **More aggregations** — extend the agg→DAX map beyond the Phase-1 five (e.g. `min`, `max`, `median`).
3. **Richer filter operators** — `is_false`, `value_equality`, `in_set` (already in the L3 m2 backlog), inherited via the shared predicate emitter.
4. **Time intelligence** — `kind: time_intelligence` for YoY / MTD / rolling patterns, with its own verifier branch.
5. **Composed measures** — measures built from other generated measures (depends on cross-contract `ref:`).
6. **Metric dependency graph** — resolve + order inter-contract references so composed/ref measures generate in dependency order.
7. **Analyzer/Refiner (Phase 2)** — turn findings on an *existing* measure into suggested rewrites + explanations, reusing the same rule-run + verify helpers.
8. **Live-data goal loop (Phase 3)** — behind the existing `retail validate` lazy-`psycopg2` seam; **read-and-compare only, never auto-mutate data to hit a number.**
9. **Optional NL front-end (Phase 3)** — an LLM drafts a `definition` from natural language for **human approval before generation**; meaning-definition stays human-owned.

These exist to prove Phase 1 is not a dead end. None ships in this slice.

### Seams

- **Phase 2 — Analyzer/Refiner.** Will reuse `generate_measure`'s D-rule + L3 plumbing to turn *findings* on an existing measure into *suggested fixes* + explanations. Seam: the rule-running and verify helpers in `dax_gen.py` are written as reusable functions, not inlined into the CLI handler.
- **Phase 2 — cross-contract refs.** `numerator/denominator: {ref: OtherMeasure}` needs a contract-resolution graph. Seam: the ratio-side parser is a single function that today accepts only inline aggregations; adding a `ref` branch is localized.
- **Phase 3 — goal-driven live data.** Sits behind the existing `retail validate` live-DB seam (lazy `psycopg2`, `resolve_dsn`). **Hard rule for that phase: read-and-compare only; never auto-mutate data to hit a target number.** Not designed here.
- **Optional NL front-end (Phase 3).** An LLM could draft a `definition` from natural language, but a **human approves the contract before generation** — meaning-definition stays human-owned. Out of scope here.

---

## 10. Why this is safe to ship

- **Stdlib-pure core preserved** — `dax_gen.py` is a lazy module, never in the `retail check` chain; guarded by a subprocess import test.
- **Zero-regression L3 extension** — `kind` absent ⟹ identical behavior; existing tests untouched and green.
- **Self-proving** — every emitted measure round-trips to `pass` through the very checker that gates the model, then passes D1–D11. For a ratio, that L3 pass is the **same denominator-filter-set check the model's gate applies** (denominator-only by design — the numerator is pinned by the emit tests, not re-derived here); for a base measure it re-verifies aggregation + full filter-set. The generator gates exactly what the model's own gate gates. Unverifiable ⟹ refused.
- **Never mutates truth** — no model writes (`powerbi/**` refused on resolved path), no DB, no LLM, no invented semantics, no free-form DAX, no overwrite of existing artifacts.
- **Fail-closed end to end** — refuse-not-warn in the engine; stdout-verified-only in the CLI; the shell redirect idiom is itself fail-closed.
