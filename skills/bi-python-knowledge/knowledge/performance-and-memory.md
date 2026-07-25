# Performance and Memory Diagnosis

Use this route only after correctness is established. End on a **performance and
memory verdict** with observed evidence and a boundary decision.

## Decision this route supports

Decide whether a single-node dataframe pipeline can be made safely fast enough, should
push work into SQL, or genuinely requires the Big Data layer.

## Required evidence

- row/column counts and observed memory footprint by stage;
- elapsed time by stage and repeated-action count;
- dtypes, projection/filter boundary, merge cardinality, and output size;
- machine memory budget and required service window;
- evidence that correctness controls still pass.

## Reasoning sequence

- **PY-CN-141 — Measure the dominant stage.** Whole-notebook timing cannot localize
  read, parse, merge, groupby, serialization, or write cost.
- **PY-CN-142 — Working-set size exceeds file size.** Object strings, indexes, copies,
  and intermediate frames can multiply memory.
- **PY-CN-143 — Vectorized expressions avoid Python row overhead.**
- **PY-CN-144 — Projection and filtering reduce every downstream cost.**
- **PY-CN-145 — Dtype choice affects memory and semantics.** Optimize only after the
  logical type is correct.
- **PY-CN-146 — Repeated materialization is evidence of a missing boundary.**
- **PY-CN-147 — Engine choice follows the post-pruning working set.**

**PY-PB-018 — Memory blowup:** compare stage footprints, copies, object columns, and
merge fan-out.  
**PY-PB-019 — Slow-but-correct:** isolate the dominant stage, change one cause, and
remeasure with controls.  
**PY-PB-020 — Scale boundary:** prefer SQL pushdown for heavy relational work; use Big
Data only when the verified post-pruning workload exceeds a safe single node.

## Failure modes

- optimizing before correctness;
- row-wise loops for column-expressible logic;
- retaining unused columns through joins;
- repeated CSV/Excel parsing;
- chunking a global join/groupby without a reconciliation design;
- calling an OOM proof that distributed compute is required when fan-out caused it.

## Evidence-based verdict

- **SINGLE-NODE SOUND** — within memory/time budget with controls unchanged.
- **PUSHDOWN RECOMMENDED** — relational filtering/join/aggregation belongs in SQL.
- **SCALE-OUT HANDOFF** — post-pruning evidence exceeds one safe node.
- **BLOCKED** — no stage timing, memory evidence, or correctness baseline.

## Stop and handoff

Do not write production optimization code here. Hand the categorical verdict and
evidence to Python implementation, SQL, or Big Data.
