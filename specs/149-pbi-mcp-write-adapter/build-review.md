# Independent Build Review — spec 149 (F016 slice 5, approval-gated Power BI MCP write adapter)

**Reviewer**: independent external reviewer (no authorship stake) | **Date**: 2026-08-18
**Branch**: `149-pbi-mcp-write-adapter` @ **`b2bb2425`**
**HEAD moved twice during this review** (`61992bae` → `dbed103b` → `b2bb2425`) from a
concurrent session. Findings below are re-verified against `b2bb2425`; the mid-review
regression and its repair are recorded under MISSED/UNVERIFIED because they are evidence about
the *process*, not open defects.
**Method**: read the full diff; **mutation-tested** each claimed guard by reverting exactly one
line and re-running the suite; wrote standalone exploit scripts driving `gate.evaluate` and
`orchestrate.apply_write` against real committed git fixtures. Every finding is reproduced,
not inferred.

VERDICT: REVISE

The gate is well built and the test suite is genuinely load-bearing — I tried to break it five
ways and it caught all five. But three guards that the code's own docstrings describe as active
are **not wired to any production path** (`config_state`, `drift.py`), one precondition is
satisfiable by the party it constrains (`--backup-ref HEAD`), and an indeterminate write can
exit 3 naming no cause at all. None is exploitable in the repo as committed (`targets: []`
refuses everything), which is why this is REVISE and not REJECT — but each is a hole on the day
an owner fills the allowlist in.

## GAPS (ranked, highest severity first)

**[CRITICAL] `--backup-ref HEAD` clears the dirty-tree precondition while backing up nothing — a sixth caller-satisfies-its-own-precondition hole.**
`_ref_resolves` (`gate.py:161-178`) verifies only that the ref *resolves*, never that it
captures the target's content. On a dirty tree the agent passes `--backup-ref HEAD` — which
always resolves — and the git-safety leg passes. Reproduced on `b2bb2425`:
```
tree dirty (agent edited models/sales_model.tmdl, uncommitted)
--backup-ref HEAD  ->  git_safe = True | cleared = True | blockers = ()
```
HEAD is precisely what the uncommitted content is *not* in, so the "backup" recovers nothing.
Worse, `rollback_guidance_for` then emits `git restore --source=HEAD -- <target>`, which
**discards the operator's uncommitted work** and presents that as the rollback. The docstring
at `gate.py:167-170` claims "a backup is *verified*, not attested… A boolean
`--backup-declared` would let the party requesting the mutation satisfy the precondition
protecting it" — but verifying *resolution* instead of *custody* reintroduces exactly that
defect one level down. This is the same class as the `--allow` flag and the `backup_declared`
bool the build already removed.
**Fix**: require the ref to demonstrably contain the target's pre-write state — after
resolving, assert
`run_git(root, "diff", "--quiet", backup_ref, "--", entry.path).returncode == 0`; refuse
otherwise with a new `PBIMCP-GATE-14` ("declared backup does not contain the target's current
content"). Add a positive control (a ref from `git stash create`, or a real commit of the dirty
state, still clears) so the new check cannot refuse everything and pass vacuously.

**[HIGH] `refuse_if_bypass_flag`'s config half is dead code on the only production path — FR-002 is half-unenforced.**
The docstring states "Both inputs are checked because the flag can arrive either way." But
`config_state` has **no production caller**. `grep -rn "config_state" src/` returns only the
parameter definitions (`detect.py:208,220`; `orchestrate.py:86,102`) — never an argument, and
`grep -rn "config_state" src/seshat/cli/commands/pbi_mcp.py` returns nothing. `_run_write_leg`
calls `apply_write(... argv=tuple(sys.argv[1:]), dry_run=dry_run)`, so `config_state` defaults
to `None` and a machine-local `.mcp.json` carrying `--skipconfirmation` is **never detected**
on `seshat pbi-mcp apply` — even though `detect.classify_mcp_config` already computes that
verdict for the read-only `doctor`/`preflight` legs. FR-002 ("MUST refuse, in **every** mode")
holds for argv only. The branch *is* tested
(`test_refuse_if_bypass_flag_raises_on_config_state`; `test_pbi_mcp_orchestrate.py:222` passes
it directly), which is why the gap is invisible: the guard is proven reachable *by tests* and
unreachable *in production* — the `injected-seam-needs-a-populated-registry` defect this repo
has been bitten by before.
**Fix**: in `_run_write_leg`, resolve and pass it —
`config_state=detect.classify_mcp_config(repo_root / ".mcp.json")`. Add a CLI test that writes
a `.mcp.json` containing `--skipconfirmation`, runs `apply` as a **subprocess**, and asserts
exit 1 plus the refusal on stderr: end-to-end, not a direct call to the guard.

**[HIGH] `drift.py` is entirely unwired: the write path never gates on drift, contradicting the module's own contract and FR-020.**
`drift.py:16-18` asserts "the write path gates on **drift**, not on version compatibility. A
drifted runtime blocks". Nothing calls it. `orchestrate.py:24` imports only
`evidence, gate, runner, validation`, and `grep -n "drift"
src/seshat/pbi_mcp_adapter/orchestrate.py` returns nothing.
`RuntimeCapabilityProfile` / `assert_range_never_assumed_compatible` / `PBIMCP-DRIFT-*` match
**only `drift.py` itself** in `src/`; the sole importer anywhere is
`tests/unit/test_pbi_mcp_drift.py`. So those three blockers can never appear in a real verdict,
and the commit titled "feat: add the drift gate and the CLI write legs" added a CLI leg and a
*library*, not a gate. Note `has_baseline` is False for empty `recorded_tools`, so a
correctly-wired check would block every write until a baseline is recorded — likely why it was
left unwired, but that tradeoff is undocumented and the docstring claims the opposite.
**Fix**: either (a) wire it — evaluate the profile between gate and runner, fold
`profile.blockers` into the refusal path, and record the baseline in a committed artifact
alongside the allowlist; or (b) if a baseline producer is out of scope, mark FR-020 EXTERNALLY
BLOCKED in `spec.md` the way FR-011b is, correct `drift.py`'s docstring to say it is a library
awaiting a wiring spec, and stop calling it a gate in the commit log and `tasks.md`. Do not
leave a module whose docstring claims enforcement it does not perform.

**[HIGH] The named human approves a *target*, never an *operation* — and the cheap half of FR-011b is not externally blocked.**
`evaluate` checks `note_names_target(approval.note, target_id)`; nothing compares the approval
note to `operation_id` (`grep -c "note_names_target(approval.note, operation_id)" gate.py` →
**0**). So one `publish_ready` approval reading "approved for sales_model" authorizes **every**
operation the allowlist lists for that target, indefinitely. Two authorities are conflated:
`BLOCKER_OPERATION_UNBOUND`'s text says "did not resolve to an approved definition", but
"approved" there means *committed to a YAML file by whoever edited the allowlist*, not *ruled
on by the named human*. FR-011c requires "Target-naming and operation-binding are two distinct
checks, and both are required" — the second consults a weaker authority than the first.
This is also the answer to whether FR-011b's EXTERNALLY BLOCKED framing is sound. It **is**
sound for the *content hash*: that genuinely needs a sign-off-time producer this spec may not
write, and `spec.md:213-229` argues it well. But the framing covers more than it should —
requiring the note to name the operation as a whole token needs **no external producer** and
reuses `note_names_target` unchanged. `cleared` is therefore weaker than the "every
precondition is DERIVED from committed state" claim implies: the operation's authority derives
from a committed *file*, not a committed *human decision*.
**Fix**: add `approval_names_operation = note_names_target(approval.note, operation_id)` with
its own blocker (`PBIMCP-GATE-15`), require it in `cleared`, and document the note convention
("approved for <target_id>: <operation_id>") in `contracts/pbi-mcp-write-targets.yaml`. Narrow
FR-011b's blocked scope to the hash alone and state that note-level operation naming is in
scope and enforced.

**[MED] Exit 3 is reachable with zero reported blockers; report and evidence disagree; `PBIMCP-RUN-04` is an undefined id.**
`orchestrate.py:192` substitutes a fallback into the *evidence record* only —
`blockers=result.blockers or ("PBIMCP-RUN-04",)` — while line 200 passes `result.blockers` raw
into `WriteReport`. Reproduced with an injected runner returning `returncode=1, blockers=()`:
```
report.exit_code = 3   report.outcome = blocked   report.blockers = ()
evidence['blockers'] = ['PBIMCP-RUN-04']
'PBIMCP-RUN-04' in runner.BLOCKER_DETAIL -> False
```
The operator sees `[blocked]` and exit 3 with **no blocker line** (the CLI loops an empty
tuple), `--json` emits `"blockers": []`, and the evidence names an id absent from every
`BLOCKER_DETAIL` table in `src/` — `detail_for` would echo the raw string. An indeterminate
write naming no cause is the hardest state to audit, and this is the outcome where auditability
matters most.
**Fix**: compute the fallback once before both consumers — `blockers = result.blockers or
(runner.BLOCKER_RUNTIME_UNEXPECTED,)` — pass that same tuple to `_finalize` and `WriteReport`,
and define the constant in `runner.BLOCKER_DETAIL`. Add a test asserting report and evidence
blockers are equal on every terminal path.

**[MED] Redaction covers the evidence file but not the CLI's own stdout/stderr.**
`redact()` is applied only inside `RunEvidence.to_payload()`. `_run_write_leg` prints
`report.blockers` and `report.rollback_guidance` **raw** to stderr and dumps them raw in the
`--json` branch. `rollback_guidance_for(target_path, backup_ref)` interpolates both arguments —
`backup_ref` is caller-supplied argv, `target_path` comes from the allowlist — so a ref name or
path carrying a secret-shaped token reaches the terminal and CI logs unscrubbed, bypassing the
two-layer chokepoint the evidence path is careful about. The file is the *audited* surface;
stdout is the *observed* one, and CI captures it.
(`refuse_if_secret_shaped`'s own message is safe — `scan.py:104` appends "(values not shown)" —
so the `except GeneratedSecretError` print is not itself a leak.)
**Fix**: route every write-leg print through `evidence.redact()`, and pass the fully rendered
human and JSON text through `refuse_if_secret_shaped` before printing, giving stdout the same
posture as the file.

**[MED] TOCTOU: `orchestrate` re-reads the allowlist after the gate, and the mutation target comes from the second read.**
`orchestrate.py:134-135` does `allowlist, _ = gate.read_allowlist(root)` then
`entry = allowlist[target_id]` — a **second** read that discards the `committed` flag, after
`gate.evaluate` already resolved the same entry. The `entry.path` handed to `runner.invoke`,
`validation`, and `rollback_guidance_for` comes from this later read, so the path the gate
validated need not be the path written (a `git checkout` or concurrent process between the two
reads suffices). `dbed103b`'s containment check runs inside `evaluate` on the **first** read,
so a swapped second read is containment-unchecked — the newest guard is the easiest to slip
past. The bare `allowlist[target_id]` also raises `KeyError` instead of refusing if the entry
vanished. Related asymmetry: `target_exists` is a **worktree** `is_file()` check while the
allowlist and readiness records are **HEAD** reads.
**Fix**: carry the resolved entry and its contained absolute path on `GateVerdict` as fields;
have `orchestrate` use only `verdict.entry` and never re-read. Then the gate's decision and the
executed mutation refer to the same bytes by construction.

**[MED] `plan-write` dirties the tree it later reports as clean, composing into a self-inflicted precondition bypass.**
`.seshat/pbi-mcp-write-evidence.json` is **not gitignored** — `git check-ignore -v` returns
nonzero; `.gitignore` covers `.seshat/watch/`, `.seshat/dagster/`, `.seshat/dbt/`,
`.seshat/integrations/`, `.seshat/adopter-sim/`, not this path. Every run writes it, including
the `plan-write` dry run and every refusal. So the documented sequence `plan-write` → `apply`
makes the tree dirty as a side effect of the dry run, and the second invocation's
`_probe_tree_clean` returns False. Combined with CRITICAL-1 the operator is pushed straight to
`--backup-ref HEAD` to proceed: the adapter manufactures the condition whose only escape hatch
is the weakest leg in the gate.
**Fix**: add `.seshat/pbi-mcp-write-evidence.json` (or `.seshat/pbi-mcp/`) to `.gitignore`, or
exclude the evidence path from the cleanliness probe. Add a test running `plan-write` twice on
a clean tree asserting the second still sees `tree_clean=True` — a dry run must be
side-effect-free with respect to its own preconditions.

**[LOW] No staleness bound on the authorizing approval.**
`_shape_valid_approval` takes the **first** shape-valid `publish_ready` row and only checks
that `at:` parses. A two-year-old approval authorizes unlimited future writes; no re-consent is
ever required. `rules/readiness_status.py` already has a `_check_audit_freshness` notion this
gate does not use.
**Fix**: add a maximum approval age committed in the allowlist (not on argv), refusing past it
with `PBIMCP-GATE-16`. If the owner prefers no expiry, record that as an explicit decision in
`spec.md` rather than an unstated omission.

**[LOW] "Superseded" is honest for T017/T018; `detect.py`'s docstring is now stale.**
I checked rather than taking it on faith. T017 (`target.py`) and T018 (`git_safety.py`) are
legitimately superseded: allowlist resolution lives in `gate.read_allowlist` behind the same
`_load_committed_yaml` committed-state path, and the git-safety legs are in `evaluate` using
`gitstate.run_git`. Consolidating genuinely avoids a second reader with its own
committed-vs-worktree posture — the `no-second-approval-trust-path` rule — and I
mutation-confirmed both behaviours load-bearing. The framing is sound, not a rationalization.
T053 is fairly labelled "HALF done… OWNER-GATED", but the residual is broader than stated:
`detect.py:11-14` still describes slice 5 as "owner-ADR-gated, NOT implemented here", stale now
that slice 5 ships in that very module and `refuse_if_bypass_flag` lives there.
**Fix**: update `detect.py`'s module docstring to state slice 5 is implemented and that
`refuse_if_bypass_flag` is its chokepoint. Leave `VENDORED_RUNTIME_DIR` for the owner as stated.

## MISSED / UNVERIFIED

**What I tried to break and could not — the suite is real.** The task asked specifically whether
`test_pbi_mcp_gate.py`'s happy-path fixture could go green with the committed-state check
deleted. **It cannot.** I mutation-tested all five previously-fixed fail-opens, reverting one
line each:

| Mutation | Result |
|---|---|
| delete `is_tracked_and_clean` in `_load_committed_yaml` | **8 failed** (incl. `test_committed_state_guard_is_what_produces_the_refusal`) |
| `tree_clean: bool \| None = True` | **1 failed** (`test_unprobed_git_state_refuses`) |
| `operation_binds = bool(operation_id)` | **6 failed** |
| `_ref_resolves` → `return True` | **6 failed** (incl. `test_backup_ref_guard_is_load_bearing`) |
| `note_names_target` → substring | **8 failed** |

Fixtures run real `git init`/`commit`, so the committed-state proof is not circular, and
`test_uncommitted_but_passing_record_refuses` is a genuine positive control. The "load-bearing
proof" tests do what they claim. I found **no** vacuous tests, no absence-assertions, and no
self-proving fixtures. Full spec-149 suite on `b2bb2425`: **232 passed**.

**A regression shipped and was repaired mid-review — the strongest available evidence about
both suite and process.** `dbed103b` ("fix: enforce target containment…") silently weakened
**two** guards in the same commit that added a real fix: `operation_binds` → `bool(operation_id)`
and `note_names_target` → substring. I reproduced the first as arbitrary unapproved mutation
(`op 'delete_entire_model' not in allowlist → cleared = True, blockers = ()`) and confirmed the
suite was **red on that HEAD** (6 failed / 109 passed) — committed anyway, with a message
asserting "73 gate tests… seshat check exit 0". `b2bb2425` restored both, attributing the cause
to `git add -A` sweeping an unrelated working copy. Two process findings stand independently of
the now-fixed code: (1) a commit whose stated gate evidence did not match its content entered
history, so the audit record is unreliable for `dbed103b`; (2) `git add -A` on a file whose
entire job is to refuse is unsafe, as that commit message itself concludes. **Recommended
control**: a pre-commit hook that blocks any commit touching `pbi_mcp_adapter/gate.py` when the
gate suite is not green, plus a CI assertion that `AllowlistEntry.permits` and
`note_names_target` each have a production caller — an unreferenced authorization primitive is
exactly what exposed this.

**Not verified** (bounded by scope/environment, flagged rather than guessed):
- No live `npx @microsoft/powerbi-modeling-mcp` run — the vendor argv shape (`--readwrite`,
  `--target`, `--operation`) is **unvalidated against the real binary**. If Microsoft's preview
  spells these differently, `build_argv` is wrong and no test would show it (every runner test
  injects a fake). A wired drift check is what would catch this.
- No concurrency test: all runs share one evidence path (`ARTIFACT_RELPATH` is a fixed single
  file), so a second run silently overwrites the first's intent record. `_write_atomically`
  makes each write atomic but nothing prevents interleaving, and there is no lock. A per-run
  path (`.seshat/pbi-mcp/runs/<id>.json`) would fix it.
- `docs/capabilities/capabilities.yaml` from `dbed103b` not audited; full-repo `seshat check`
  and `ruff` not re-run beyond the pbi-mcp files.
- Windows-only environment: `_contained_target`'s `is_relative_to` on case-insensitive paths and
  8.3 short names is untested (`C:\MODELS` vs `c:\models`).

## STRONGEST COUNTERARGUMENT

*The best case for this implementation*: the allowlist ships `targets: []`, refusing **every**
write, so nothing here is exploitable today — CRITICAL-1 requires an owner to first commit a
real target through review. The design is materially better than the `dagster_adapter` sibling
it was told to mirror: it reads HEAD instead of the worktree, wraps `yaml.safe_load`, carries
thirteen typed blockers instead of a generic failure, makes vacuous validation
*unrepresentable* in the type system, and the author found a sixth hole (path containment) by
attacking their own gate after building it. My own mutation testing proves the suite is not
decorative, and the one regression that reached history was caught **by that suite**, isolated
by bisect, and repaired within six minutes. On that reading the remaining items are hardening
on a sound gate, and REVISE understates how good the core is.

*Why REVISE and not APPROVE*: "the allowlist is empty" is a deployment accident, not a control —
the gate must be safe on the day someone fills it in, and that is precisely when CRITICAL-1
bites. Three surfaces currently describe enforcement the code does not perform (drift "gates",
config bypass "checked both ways", the approval authorizing an "approved definition"), and for
a governance feature the accuracy of its own self-report is load-bearing: a gate that
misdescribes its coverage stops the next reviewer from looking. Fix the backup-ref custody
check, wire or honestly re-label `config_state` and `drift.py`, unify the RUN-04 blocker, and
this is a straightforward APPROVE.
