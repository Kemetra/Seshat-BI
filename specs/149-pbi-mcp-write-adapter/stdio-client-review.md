# Adversarial review — the #660 stdio client (branch `fix/660-mcp-stdio-client`)

**Date**: 2026-08-20 · **Verdict**: BLOCK · **Reviewer**: adversarial external agent (Opus),
findings independently re-verified against the tree before acceptance.

The three new modules (`protocol.py`, `session.py`, `vendor_ops.py`) are sound and the vendor
protocol diagnosis is correct. But the write path **still cannot execute end to end**, for a
reason the original issue did not name. 432 tests pass because no test exercises the runner
against the *gate's* path contract — the defect sits in the seam between two individually
correct components.

## CRITICAL — accepted, blocking

### C1 — The runner sends a FILE path where the vendor requires a FOLDER

- `gate.py:543` — `if not contained.is_file(): return False, (BLOCKER_TARGET_ABSENT,)`
- `runner.py:276` — `{"operation": "ConnectFolder", "folderPath": target_path}`
- `runner.py:305` — `{"operation": "ExportToTmdlFolder", "tmdlFolderPath": target_path}`

Two exhaustive, mutually exclusive branches:

| Allowlist holds | Gate | Vendor |
|---|---|---|
| a **file** (`models/x.tmdl` — what `is_file()` requires, what every fixture uses) | clears | `ConnectFolder` fails: it needs a directory |
| a **folder** (`X.SemanticModel/`) | `BLOCKER_TARGET_ABSENT` — never clears | would work |

Independently confirmed: the probe that established the protocol passed a **directory**
(`powerbi/RetailStoreSales.SemanticModel`), and the server resolved `…/definition` itself.
The client was built against the probe and never checked against the gate. **The issue's
premise — "no real write can execute" — survives this fix.**

Fixing it is a decision, not a patch: either the allowlist declares folder targets (and
`_path_blockers` accepts a directory, which widens what "contained target" means for a
**gate input**), or the runner derives the model folder from the file path (inventing a
path the approval never named). Both need an owner ruling.

### C2 — The authorized operation is issued with no parameters — but this is a RATIFIED DEFERRAL, not a new defect

`runner.py:289` sends `{"operation": operation}` only. The probe's real write was
`{"operation":"Update","definitions":[{"name":"TotalSales","tableName":"…","formatString":"#,0.000"}]}`.
A bare `Update` mutates nothing, and `GateVerdict` (`gate.py:150-172`) has no payload field.

**This must NOT be "fixed" by synthesising a payload.** `spec.md:165` — "the adapter never
invents the definition"; `spec.md:228` — the `approved_definitions[]` block is
**"Unblocked by: a companion spec"**. Supplying `definitions` from anywhere but an approved
record is the same fail-open as T012b's invented hash. The correct disposition is to keep the
deferral and make it **loud**: refuse a write whose operation needs a payload we do not have,
rather than issuing a no-op that reports success.

## HIGH — accepted

- **H1 — the effect check blocks every legitimate write.** `orchestrate._effect_blockers`
  (lines 122-139) is unmodified. R8 item 5 — added by this very PR — records that the flush
  rewrites all 11 TMDL files. Proved: target + 11 siblings changed → `PBIMCP-EFF-02` →
  `outcome="failed"`. The moment C1 is fixed, this blocks every apply. Coordinate with #663.
- **H2 — the per-call deadline is not enforced during a blocking read.** `session.py:95`
  checks `time.monotonic()` *before* the blocking `read_line()`; no `select`, thread, or
  socket timeout. A chatty server hits the bound; a **silent** one blocks forever
  (reproduced: `deadline_seconds=2` still blocked at 6.0s). `runner.py:17-18`'s "a run with
  no bound can hang forever" is therefore a prose over-claim.
- **H3 — a non-`SessionError` exception escapes `invoke`, so FR-015 is violated.**
  `SubprocessTransport.read_line` (`session.py:183`) does not wrap `OSError`;
  `_converse` catches only `SessionError`. Reproduced: an `OSError` mid-read escaped as a
  traceback — no `RunResult`, so orchestrate never reaches `_terminate` and writes **no
  evidence record**.
- **H4 — 69 of 103 operation verbs have no probe evidence, and the docstring claims they do.**
  `vendor_ops.py:66-69` says "DERIVED from the 21 probed tool descriptions". Only
  `measure_operations`' 9 verbs are actually documented in the captures. `READ_OPERATIONS`
  contains `ExportTMDL`, `ExportTMSL`, `ExportJSON` — unsourced, and from the same verb family
  as `ExportToTmdlFolder`, which the PR proved rewrites 11 files while self-reporting
  `readOnlyHint: true`. A mutating verb misfiled as a read gets `attempted=False`, **no
  cross-check, no flush, `succeeded=True`**. The cited cross-check test asserts a tool COUNT
  plus six spot-checks; it does not constrain the verb enums at all.
- **H5 — `stderr=PIPE` with no reader.** `session.py:167`. `stderr_text()` has zero production
  callers. Once the ~64KB buffer fills, the child blocks on stderr while we block on stdout.
  The vendor is known to be chatty there (`IsWrite=…`, `ConnectionName=…`). This repo's known
  "tested code, zero callers" class.

## MEDIUM — accepted

- **M1 — `orchestrate` hardcodes `mutation_attempted=True`** (lines 308, 325, 337), discarding
  the runner's value. Reproduced with `measure_operations.List`: runner says False, evidence
  asserts True, and rollback guidance is emitted for a run that attempted nothing. Missed
  because `test_pbi_mcp_orchestrate.py:25` defines only an `Update` pair — there is no
  orchestrate-level read-pair test.
- **M2 — every `SessionError` maps to exit 124 / `RUNTIME_STALLED`** (`runner.py:312-315`). An
  impostor-server refusal is reported as "did not finish within 900s and was killed".
- **M3 — `outcome.error` is never surfaced.** On a JSON-RPC error frame `raw_text` is `""`, so
  `BLOCKER_VENDOR_REFUSED` ships with empty output — no diagnosis on the most important
  failure path.

## Attacked and found SOUND

- The flush guard `if writes and not blockers` — no suppression path; `blockers` is
  function-local with two adjacent append sites.
- `SubprocessTransport.__init__` — `Popen` is the last statement; no child leak.
- Redaction — correct order (`redact` → `SECRET_PATTERNS` → slice); DSN, tenant GUID and
  Windows user path all scrubbed live.
- Markers — all four new test files carry `pytestmark = pytest.mark.unit`.
- Mutation testing — four mutants each fail tests (flush deleted: 14 fail; `is_write`→False:
  19 fail; cross-check deleted: 1; deadline check deleted: 1).
- No unmigrated single-token operation ids survive in `docs/`, `specs/`, or `contracts/`.

## Disposition

The branch is **not** merge-ready and the PR is not opened. C1 and H1 need an owner ruling on
the folder-vs-file target contract (a gate input). C2 stays deferred by ratified decision but
must become a loud refusal. H2/H3/H5/M1-M3 are ordinary defects fixable without a ruling.
