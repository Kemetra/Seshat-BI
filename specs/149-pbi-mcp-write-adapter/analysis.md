# Specification Analysis Report — spec 149 (F016 slice 5)

**Artifacts analyzed**: `spec.md` (339 L), `plan.md` (254 L), `tasks.md` (252 L),
`data-model.md`, `contracts/cli-contract.md`, `research.md`
**Constitution**: `.specify/memory/constitution.md` (617 L)
**Date**: 2026-08-18 | **Mode**: read-only cross-artifact consistency analysis
**Branch**: `149-pbi-mcp-write-adapter`

Every code-grounded claim in `plan.md` and `tasks.md` was verified against the shipped tree
rather than taken on trust. Results of that verification are recorded inline below.

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Coverage Gap | **CRITICAL** | `data-model.md:102-115`, `tasks.md` T012b, FR-011b | `ApprovedDefinition` (with `content_hash`) is fully specified and gated on by `operation_binds`, but **no approved-definition store exists in the shipped tree** and **no task creates one**. `grep -rn 'content_hash' src/seshat/` returns 0 hits; `grep -rln 'ApprovedDefinition' src/seshat/` returns 0 hits. T012b says "implement resolution + hash verification" against a store that has no producer, and nothing records a hash *at approval time*. | Add a task defining the approved-definition store: where it lives, who writes it, and how a hash is captured at sign-off. Until a producer exists, FR-011b is unbuildable and T012b would have to invent the record it validates — the exact fail-open FR-011a forbids. Decide explicitly whether slice 5 ships the store or narrows to target-binding only. |
| I1 | Inconsistency | HIGH | `plan.md` Verification Gates, `tasks.md` T056/T057, constitution x12 | Plan and tasks specify `seshat check` / `seshat semantic-check`; the constitution says `retail check` **12 times** and `seshat check` **0 times**. `pyproject.toml:57-58` confirms both console scripts point at `seshat.cli:main`, so they are aliases and the gates *run* — but the constitution's normative text is stale relative to the shipped brand. | Gates are functionally correct; no task change needed. The constitution is the stale artifact. Do **not** silently reword it here — per repo rule, constitution amendments are a separate explicit act. Flag for a follow-up constitution update. |
| U1 | Underspecification | HIGH | FR-013, `tasks.md` T035 | FR-013 requires value validation "where an expected value exists and a data leg is available", and T035 says otherwise emit `deferred`. But no artifact defines how "a data leg is available" is *detected*. Given the repo's degrade-without-reporting fail-open history, an undetectable condition silently becomes permanent `deferred`. | Specify the availability probe in T035, and assert in test that `deferred` is **reported** as a typed outcome, never a silent skip. |
| U2 | Underspecification | MEDIUM | Edge Cases ("Two writes concurrently"), FR-008 | The spec says a second concurrent write "must not interleave" and that git-safety is "re-evaluated per invocation, not cached" — but re-evaluation is not mutual exclusion. Two processes can both observe a clean tree and both proceed. No task tests concurrency. | Either add a locking task, or narrow the spec's claim to what per-invocation re-evaluation actually guarantees. Currently the spec promises more than the design delivers. |
| A1 | Ambiguity | MEDIUM | FR-016, `tasks.md` T024 | "fixed authority label" is never given its literal value in any artifact. A test asserting "a fixed label" passes for any constant string. | Pin the exact label string in `data-model.md` so T021's score-free proof and T024 bind to one value. |
| I2 | Inconsistency | LOW | `plan.md` "Correction" section, `tasks.md` Phase 2 | Both cite `pbi_mcp/detect.py:51` for `_FORBIDDEN_FLAG`. Verified actual location: **line 49** (`_FORBIDDEN_FLAG`), line 50 (`_WRITE_FLAGS`). Symbols and both write-flag spellings confirmed exactly as described; only the line number drifted. | Cosmetic. Prefer symbol names over line numbers in prose, since edits invalidate the latter. |
| O1 | Ordering | LOW | `tasks.md` T052, T053 | T052 requires reconciling five `parked_on: F016` edges "once this ships — and not before"; T053 is marked owner-gated. Both sit in Phase 8, ahead of the Phase 9 gate set, so the roadmap flip precedes final verification. | Move T052 after Phase 9, or state that it lands in the same commit as the passing gate set. |

**No finding contradicts a constitution MUST.** Principles I, II, V, VI, VIII and IX are
addressed explicitly and correctly in `plan.md`'s Constitution Check, and the design's
read-only-resting-state posture is stronger than the minimum those principles require.

---

## Verified-correct claims (checked against shipped code, not assumed)

| Claim | Verification |
|---|---|
| `_FORBIDDEN_FLAG = "--skipconfirmation"` exists as the single chokepoint | Confirmed, `detect.py:49` |
| `_WRITE_FLAGS` covers **both** `--readwrite` and `--read-write` | Confirmed, `detect.py:50` |
| Evidence vocabulary is **five** values, not four | Confirmed, `dagster_adapter/__init__.py:43-44`, `OUTCOMES` frozenset |
| `VENDORED_RUNTIME_DIR` still live and contradicts ADR 0018 | Confirmed, `detect.py:47`, consumed at `detect.py:369` |
| `parser_pbi_mcp.py` exists (CLI legs extend, not create) | Confirmed |
| Group help claims "F016 stays parked -- no mutation path" | Confirmed, `parser_pbi_mcp.py:146` — T047 correctly treats this as a governance defect |
| `gitutil.run_subprocess` docstring excludes execution runners | Confirmed, research R4 quotes it accurately |
| `replace_fragments` is a blunt substring replacer | Confirmed, research R5 quotes the implementation |
| Baseline gates green before any change | `ruff format --check` 940 files clean; `ruff check` all passed |

---

## Coverage Summary

| Requirement | Has Task? | Task IDs |
|---|---|---|
| FR-001, FR-003 (read-only default, no `--readwrite` default) | Yes | T005, T041 |
| FR-002 (bypass flag refused in every mode) | Yes | T004, T005, T006, T007 |
| FR-004, FR-009 (stage gate; refusal names blocker) | Yes | T009, T015 |
| FR-005 (fail closed on unreadable) | Yes | T010 |
| FR-006 (approval names target) | Yes | T011, T016 |
| FR-007 (allowlist) | Yes | T012, T017 |
| FR-008 (git safety) | Yes | T013, T018 |
| FR-010, FR-011 (execution boundary, no invention) | Yes | T012, T029 |
| FR-011a, FR-011c (operation resolves; binding is not target-naming) | Yes | T012a, T012b |
| **FR-011b (hash matches approval)** | **Partial — see C1** | T012a, T012b (no store producer) |
| FR-012 (unvendored dependency) | Partial | T053 (owner-gated) |
| FR-013 (post-write validation) | Yes — see U1 | T035 |
| FR-014 (failure blocking + rollback) | Yes | T031, T032, T035 |
| FR-015, FR-016, FR-017 (evidence both paths, shape, score-free) | Yes | T020, T021, T024, T034 |
| FR-018 (no stage moves) | Yes | T022, T059 |
| FR-019, FR-020 (drift; `unknown` never compatible) | Yes | T037, T038, T039 |
| FR-021 (no secrets committed) | Yes | T023, T024 |
| FR-022 (read-only family unchanged) | Yes | T008, T055 |

All eight Success Criteria carry an explicit traceability row in `tasks.md`; spot-checks of
SC-002 to T009 and SC-005 to T004/T005 confirm the mapped tasks genuinely cover the criterion.

**Unmapped tasks**: none. Every task traces to at least one FR, SC, or an explicit
repo-lesson guard (T044 emitted-commands, T048 closed-vocabulary, T058 three proofs).

---

## Metrics

- Functional requirements: **26** (22 numbered + FR-011a/b/c)
- Success criteria: 8
- Tasks: 62
- Requirement coverage: **26/26 have at least one task (100%)**; one (FR-011b) has a task but
  no buildable substrate — counted as covered-but-blocked, not covered
- CRITICAL issues: **1** (C1)
- HIGH: 2 (I1, U1) - MEDIUM: 2 (U2, A1) - LOW: 2 (I2, O1)
- Constitution violations: **0**
- Duplications: 0

---

## Next Actions

**One CRITICAL finding (C1) should be resolved before implementation reaches T012b.**
It does not block Phases 1-3: the bypass chokepoint, the four-precondition gate, target
resolution, and git safety are all fully specified and independently buildable. C1 becomes
blocking exactly at T012b, which is where `operation_binds` needs a real store to resolve
against.

Recommended sequence:

1. Build Phases 1-2 and Phase 3 up to T012 — all unblocked and code-verified.
2. Resolve C1 at T012a/T012b: either add the approved-definition store as an explicit task,
   or narrow slice 5 to target-binding and defer hash-verification with FR-011b marked
   externally blocked. **This is a scope decision for the owner, not an implementation
   detail** — inventing the store would reproduce the fail-open FR-011a exists to prevent.
3. Tighten U1 (data-leg probe) and A1 (literal authority label) while implementing T035/T024.
4. Raise I1 as a separate constitution-amendment item; do not reword the constitution here.

**Quality note**: this artifact set is materially stronger than typical. The plan and tasks
already internalize repo-specific defect lessons — no absence-assertions, no vacuous
branches, derive-then-replace redaction, emitted-commands-must-run, non-circular fixtures,
and an explicit cancellation of a second enforcement path. C1 is a genuine gap, not a
symptom of carelessness.
