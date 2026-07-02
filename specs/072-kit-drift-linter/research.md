# Phase 0 Research: Kit Drift Linter

## R1. Standalone step vs `retail check` core rule

**Decision**: Standalone `retail kit-lint` step (DEC-1), mirroring `retail
semantic-check` / `retail value-check`. NOT a `retail check` core rule.

**Rationale**: The linter parses `kit-source.yaml` (pyyaml) — the `retail check` static
core is stdlib-only and must never import yaml. Folding it in repeats the exact MAJOR-4
boundary violation the 070 skeptic caught. `distribution-ideas.md` (line 183) classes
the generator + drift linter as **Maintenance Automation** (CI-only), which agrees. The
`retail check` rule count stays 47.

**Alternatives**: *A new `@register` rule* — rejected (yaml in the stdlib-only core).

## R2. Source-vs-constitution check — CUT (deferred as a human-shaped slice)

**Decision**: An earlier draft proposed a third check: a maintained `hard_stop → anchor`
table verified structurally. It was **CUT** after the adversarial review.

**Rationale**: A table guard-tied to the source, checked only against the source, is a
**source-vs-source tautology** — it verifies nothing about the constitution. The anchor
*values* would never be resolved against any external document (that would reopen the
forbidden prose-parsing / fabricated-confidence question). And the four current
hard_stops don't share one constitutional home:

| source hard_stop | where its basis actually lives |
|---|---|
| `never_self_grant_approval` | constitution Principle V ✓ |
| `no_silver_before_mapping_cleared` | constitution Principle IV ✓ |
| `no_dashboard_before_metric_contracts` | **roadmap.md** rule 5 (not the constitution) |
| `never_fabricate_a_confidence_score` | **global hard-rule #9** (not the constitution) |

Only 2 of 4 have a constitutional-document home, so an "existence check against
constitution.md" would fail half of them on day one. Deciding what documents span
"governance" and whether each hard_stop has a home is a **human governance decision**,
not something to guess autonomously. It is DEFERRED as a human-shaped slice; 072 ships
the projection-drift half only and reads no constitution prose.

**Alternatives**: *Structural table (source↔table)* — rejected (tautology). *Resolve
anchors against constitution.md* — rejected (fails 2/4 anchors; needs a human governance
model). *NLP non-contradiction* — rejected (fabricated confidence, hard rule #9).

## R3. Reuse the 070 projection checks (anti-fork)

**Decision**: `kit_lint` calls `compass_project.check_yaml_drift` and, for prose,
`compass_project.check_prose_drift(load_source(repo), fence.read_fence_body(path))` per
governed file. It re-implements neither.

**Rationale**: 070 already ships single implementations of both; re-deriving them forks
the check. Anti-fork discipline (the dominant theme of 070/071).

## R4. Parse/shape errors are caught, not raw tracebacks

**Decision**: `lint(repo)` wraps `compass_project.load_source` in try/except: a YAML
parse error or a non-mapping source becomes a named failing `CheckResult` (exit 1),
not an uncaught traceback (FR-008).

**Rationale**: `load_source` raises `ValueError` on a non-mapping and lets `yaml`
propagate a parse exception. FR-008 promises actionable named output; a broken source
must fail loud WITH a message, so the linter catches and reports it.

## R5. Not-bootstrapped = exit 0 (absence is not drift)

**Decision**: If `.seshat/` (or the source) is absent, `kit-lint` reports "not
bootstrapped — run `retail init`" and exits 0 (FR-006, SC-003).

**Rationale**: A repo that hasn't run `retail init` has nothing to lint; failing there
would make CI red on every pre-bootstrap repo. Absence is the honest not-started state,
consistent with how the kit treats absent artifacts elsewhere.

## R6. CI wiring point

**Decision**: A `retail kit-lint` step in `.github/workflows/ci.yml` AFTER the `retail
semantic-check` step (FR-007).

**Rationale**: Mirrors how semantic-check is a separate step from `retail check` (both
run, independent exit codes). Placing it last keeps the ordering: static core → semantic
→ kit consistency. On this repo the committed substrate passes, so the step is green
(the dogfood, SC-007).
