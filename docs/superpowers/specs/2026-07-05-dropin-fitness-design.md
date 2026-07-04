# Drop-in fitness: making the kit degrade gracefully in a foreign BI repo (Specs A–E)

**Status:** design, approved for full-chain implementation
**Branch:** `spec/dropin-fitness`
**Origin:** eval verdict — running the kit against the `GitHub/BI` fixture (a repo built
from an early kit snapshot) exposed that the kit is *over-fitted to itself*: dropped into a
foreign repo, `retail check` exits 1 with ~24 `[error]`s for kit-internal manifests the repo
can't have, and the smartest rules (SF1 fork detector, SC1, A1) go inert-as-noise.

The end goal: the kit is a **downloadable, agent-driven tool** that works when dropped into
*any* BI repo. This chain makes the tool distinguish "this repo isn't the kit" from "this
repo has a real defect."

## Guiding principle (already proven in the codebase)

`kit_lint` already degrades gracefully: `not bootstrapped → clean report → exit 0` (FR-006,
"absence is not drift"). `check`/`doctor`/generators do NOT. **Every spec below applies
`kit_lint`'s pattern consistently.** The bootstrap predicate `kit_lint._is_bootstrapped(repo)`
(kit source + compass projection present) is the single source of truth for "is this a
foreign/non-bootstrapped repo" and is reused, not reinvented.

## Dependency order

`A → C → D → B → E`. A introduces the rule-tier concept + the shared bootstrap gate; C/D are
independent mechanical guards that slot in beside it; B widens a gate's scope; E is the inverse
of A (lets a work repo opt IN so the tiered rules bite). E consumes A's tier vocabulary, so it
comes last.

---

## Spec A — Graceful-degradation rule tier  *(foundation)*

**Seam:** `core.RegisteredRule` (frozen dataclass), `registry.register`, `runner.run`/`run_json`,
`cli` check handler.

**Design (additive; existing kit behavior byte-identical):**
1. `core.py` — add `tier: str = "work-repo"` to `RegisteredRule`; add `RuleTier` constants
   `KIT_SELF = "kit-self"`, `WORK_REPO = "work-repo"`.
2. `registry.py` — `register(rule_id, title, tier=RuleTier.WORK_REPO)` threads tier through.
3. Tag the kit-internal rules `tier=KIT_SELF` (10): **A1, A3, SC1, SC2, SF1 (I3), AP1, DF1, AQ1, DR1**
   — each reads a KIT manifest a foreign repo cannot have. Everything else keeps the default
   (`WORK_REPO`) and always gates: G1–G6, P1, P2, S1–S8, D-series, C-series, B1, R1, etc.
   **NOTE:** P2 (commit-message convention) is deliberately WORK_REPO, not kit-self — any repo can
   adopt a commit convention; it reads the commit range (which any git repo has), not a kit manifest.
   Its BI-fixture `HEAD~1..HEAD` error is an *empty-history* case handled under Spec D, not here.
4. `runner.py` — `run(rules, ctx, *, bootstrapped=True)` / `run_json(...)`. When `not bootstrapped`,
   a `KIT_SELF` rule is **not executed**; one `INFO` finding is emitted:
   `"<id> skipped (kit-self rule; repo not kit-bootstrapped)"`. `WORK_REPO` rules always run.
   Exit stays 1-iff-any-ERROR.
5. `cli.py` — check handler computes `bootstrapped = kit_lint._is_bootstrapped(repo)` and passes it.

**Tests (RED first):**
- unit: KIT_SELF rule + `bootstrapped=False` → 1 INFO skip, 0 ERROR; `+True` → runs normally.
- unit: WORK_REPO rule runs regardless of bootstrap state.
- integration (BI fixture): `retail check --repo BI` exits **0** (was 1); S4a/P1/G4 still ERROR;
  the kit-self rules appear as INFO skips.
- regression: `retail check` in the kit's own (bootstrapped) repo is byte-identical (nothing skips).
  Guarded by the existing rules-manifest snapshot test (manifest schema unchanged — see C).

**Out of scope (YAGNI):** re-tiering `doctor` (already self-labels advisory) — a later spec.

**Acceptance (measured against the `GitHub/BI` fixture, read-only):** `retail check --repo BI`
→ **0 kit-self ERRORs** (was ~24 kit-manifest errors flooding the run) + **9 KIT_SELF rules skip
as INFO**. The kit's OWN repo → byte-identical (bootstrapped ⇒ nothing skips, 0 findings, exit 0).
Only genuinely-portable defects still gate on BI: P1 (missing READMEs), G4 (.gitattributes),
S4a (migration gap), **C2 (committed secret) + G6 (real host in a PBIP param)** — the latter two
were previously buried under the flood and are real, valuable drop-in signal.

**KNOWN GAP (logged, not fixed here):** P2 (commit-message) is portable and correctly runs on BI,
but errors `could not read commit range 'HEAD~1..HEAD'` on BI's single-commit history. That is a
rule-robustness gap (no prior commit ⇒ *not-applicable*, should be INFO/skip, not ERROR) — orthogonal
to Spec A's tier concept and to Spec D's DSN semantics. Tracked as a follow-up; not in this chain.

---

## Spec C — Generator foreign-target guard

**Problem:** `retail manifest` and `retail severity-posture` wrote `docs/rules/*.json` INTO the
`--repo` target with no guard — inspection mutated a foreign repo. **Seam:** `manifest.write_manifest`
+ the two CLI handlers.

**Design:** at each generator's CLI handler, before writing:
`if not kit_lint._is_bootstrapped(repo) and not args.force: print refusal; return 1`.
Add `--force` to both subparsers. The refusal names why (generators target the kit's own registry
docs, not a work repo). `write_manifest` itself stays pure; the guard is CLI-level.

**Tests:** foreign repo → refusal + exit 1 + no file written; `--force` → writes; bootstrapped repo →
writes as before (regression).

---

## Spec D — Exit-code semantics (env-unconfigured ≠ check-failed)

**Problem:** `value-check` returns 1 for four distinct reasons; only two are "check failed."
**Seam:** `cli._run_value_check` (lines 878–896 no-DSN / no-driver vs the fail-closed / V-L4 paths).

**Design:** introduce two exit constants: `EXIT_SKIPPED_UNCONFIGURED = 0` (environment absent —
no DSN, driver not installed) and keep `1` for genuine failure (malformed contract fail-closed,
V-L4 value mismatch). No-DSN / no-driver print an explanatory *skip* line and return 0. The
fail-closed and value-mismatch paths are UNCHANGED (still 1). A `--strict` flag can promote skip→1
for CI that *requires* a live run. This surgically fixes only the conflation, preserving fail-closed.

**Tests:** no-DSN → exit 0 + "skipped" message; `--strict` + no-DSN → exit 1; malformed contract →
exit 1 (unchanged); value mismatch → exit 1 (unchanged).

---

## Spec B — Semantic-check scope widening

**Problem:** `semantic-check` checks DAX↔contract *drift* only (cli.py:719–801). It never reads
`readiness.status` / `reviewed_by`, so it stays green while the model binds an unreviewed map and
every contract is unapproved. And `if measure.name in definitions` (line 785) silently skips
unpaired measures — "0 findings" can't be told from "0 paired."

**Design:**
1. **Approval dimension:** after pairing, for each paired contract read `readiness.status`. A
   contract that is `not_started`/`blocked` → WARNING (not silent green). `warning` status → INFO.
   `pass`/approved → no finding. (WARNING, not ERROR: this is scope-widening, not a new hard gate —
   avoids surprise-failing existing green runs. Severity escalation to ERROR is a follow-up if wanted.)
2. **Kill the silent-skip ambiguity:** emit a summary line — `paired N, unpaired-measures M,
   contracts-without-measure K` — so "0 drift" always states its denominator. Unpaired items → INFO.
3. Exit unchanged (WARNING/INFO don't fail); a `--require-approved` flag promotes the approval
   WARNINGs to ERROR for teams that want the hard gate.

**Tests:** paired + `not_started` contract → WARNING; paired + approved → none; unpaired measure →
INFO + summary count; `--require-approved` promotes to ERROR + exit 1.

---

## Spec E — Work-repo init (opt-in so the tiered rules bite)

**Problem:** A makes kit-self rules SKIP in a foreign repo. But a work repo that WANTS the fork
detector / status-claims reconciliation has no way to seed the minimal manifests those rules read
(`docs/quality/shared-spine.yaml`, `status-claims.yaml`, per-table `readiness-status.yaml`).

**Design:** a `retail init --work-repo` mode (or a distinct seed step) that writes SKELETON work-repo
manifests — empty-but-valid YAML the kit-self rules can reconcile against. **Respects `kit_init`'s
discipline:** NO DB, NO execution, NO profiling (FR-005) — substrate only. Seeds:
`docs/quality/status-claims.yaml` (empty claims list), `docs/quality/shared-spine.yaml` (empty spine),
and a per-table `readiness-status.yaml` skeleton. Once seeded + bootstrapped, `_is_bootstrapped`
returns true → A no longer skips the kit-self rules → they bite on real evidence.

**Tests:** `init --work-repo` on a bare dir seeds the skeletons; they parse; a subsequent
`retail check` on the seeded repo runs the kit-self rules (no longer skipped); re-run is idempotent.

---

## Cross-cutting constraints
- Every change is ADDITIVE with defaults that preserve current kit behavior (proven by the green
  1077-test baseline + the rules-manifest snapshot test).
- No confidence/health score anywhere (kit hard rule #9).
- All authored files UTF-8 no BOM, `\n` (Principle IX).
- The `GitHub/BI` fixture is READ-ONLY throughout — used only to verify `--repo` behavior, never edited.
- Windows: keep new paths short (MAX_PATH / G5).
