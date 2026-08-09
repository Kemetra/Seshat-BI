# Research: Phase 11 Protection Audit

**Repository**: `Kemetra/Seshat-BI`

**Audited main**: `85d3e96`

**Date**: 2026-08-10

## Protection matrix

| Invariant | Existing enforcement | Negative/failure protection | Gap | Action |
| --- | --- | --- | --- | --- |
| Every capability has a valid owner | `capabilities.yaml`; O9 ownership oracle; real-manifest aggregate | Missing, blank, and unknown owner tokens fail; all 110 current entries are covered | None | ALREADY-PROTECTED |
| Public capabilities have one canonical owner | public surface + `references.public_skill` + canonical-source verifier | Missing owner, duplicate explicit owner, ambiguous fallback, stale link, generated/untracked/escaping source all fail | None | ALREADY-PROTECTED |
| Seshat wrappers state a concrete delta | O9 requires every `seshat-adapter` delta; family contract tests pin dbt, Dagster, and Power BI deltas | Missing adapter delta fails | Upstream-backed non-adapter Seshat owner with no delta currently passes | CLOSE-NOW in Spec 152 |
| Generic competence delegates upstream | integration catalog plus dbt/Dagster/Power BI ownership-routing contracts | Each family test pins official owner, pre-gate, executor, post-validation, and Seshat disclaimer | None in current families | ALREADY-PROTECTED |
| Knowledge routes resolve | A1 route resolver + A3 knowledge-map/route-id bijection | Missing, malformed, duplicate, stale-planned, and unresolved targets fail | None | ALREADY-PROTECTED |
| Public routing and ownership agree | public-skill owner reconciliation; official family routing contracts | Missing/ambiguous public owner and stale public links fail | `routes.yaml` declares knowledge navigation, not capability ownership; adding owners there would duplicate authority | ALREADY-PROTECTED; do not conflate registries |
| Canonical and generated trees are distinguishable | capability `canonical_source` rejects generated roots; bundle allowlist derives from capability manifest | Generated output cannot be a canonical source | None | ALREADY-PROTECTED |
| Generated bundle drift is detectable | `export_agent_bundles.py --check`; tree byte comparison; cross-target provenance | Hand edit, missing/unexpected file, source/output hash drift, and cross-target mismatch fail | None | ALREADY-PROTECTED |
| Execution is not validation/readiness/approval | derived-evidence-only schemas; dbt execution-state reader; Dagster execution vocabulary | Passing dbt evidence leaves blocked readiness and pending approval byte-identical; Dagster rejects readiness word `pass` as execution outcome | None | ALREADY-PROTECTED |
| Readiness pass requires evidence and ordered stages | RS1 readiness rule | malformed YAML, pass without evidence, blocked without reasons, and stage skipping fail | None | ALREADY-PROTECTED |
| Human approval is fail-closed | readiness owner-shape/authority checks; decision store; implement H3 git-blame gate | bare/invalid/ineligible owners fail; invalid owner cannot satisfy approval; agent identity fails; bot-authored ratification fails | None | ALREADY-PROTECTED |
| Active feature fence cannot authorize main/unratified work | `.specify/feature.json`; Spec Kit prerequisites; implement H1-H6 | null feature plus main cannot pass H6; incomplete/dirty artifacts or draft/bot-authored status fail | None | ALREADY-PROTECTED |
| Spec Kit upstream content has reproducible provenance | init options plus core and Claude manifests | Nine core Claude skills and ten core scripts/templates are hash-pinned | Five git-extension skills are in neither manifest; representative drift passed every relevant guard | CLOSE-NOW; KF-2 |

## Guard-by-guard duplication test

### G1 - Upstream-backed Seshat delta

1. **Exact regression that passes**: a capability declares
   `capability_owner: seshat-orchestrator` and `upstream_project`, but omits
   `seshat_delta`; `ownership_violations()` returns `[]`.
2. **Existing guard that should catch it**: O9, because it owns the capability
   ownership axis and already checks adapter deltas.
3. **Why it does not suffice**: its delta condition is hard-coded to
   `seshat-adapter`; it ignores other Seshat owner classes even when they wrap an
   upstream.
4. **Smallest stable enforcement point**: the existing delta helper inside the
   independent ownership oracle.
5. **New source of truth?** No. The guard derives Seshat owner tokens from the
   existing closed owner vocabulary and reads the existing fields.
6. **False-positive risk**: bounded by requiring a nonblank `upstream_project`;
   internal Seshat capabilities are unaffected. Official/vendored upstream
   entries are excluded.
7. **Detection proof**: constructed missing/blank inputs fail; all 110 real
   entries remain clean.

### G2 - Full Spec Kit skill provenance

1. **Exact regression that passes**: edit
   `.claude/skills/speckit-git-commit/SKILL.md` without touching either
   manifest. `export_agent_bundles.py --check` and 68 relevant tests pass.
2. **Existing guard that should catch it**: the existing Claude integration
   provenance manifest, which covers the other nine skills from the same init.
3. **Why it does not suffice**: its file map omits all five git-extension skill
   paths and no consumer verifies manifest closure against the capability.
4. **Smallest stable enforcement point**: extend the existing manifest, then add
   one CI-run contract that derives expected scope from the capability manifest.
5. **New source of truth?** No. Capability manifest owns scope; Claude manifest
   owns bytes; init options and manifests already own version claims.
6. **False-positive risk**: normalize line endings; validate path shape before
   filesystem access; do not cover the full extension tree.
7. **Detection proof**: clean -> pass; one missing entry -> fail; restore; one
   content drift -> fail; restore -> pass.

## Provenance disposition

**KF-2: CLOSE-NOW.** It is not stale and not already closed. The five files are
tracked, declared by the capability, created by the sanctioned Spec Kit 0.8.10
initialization in `1eb0c98`, and absent from both provenance manifests. Current
guards demonstrably miss their drift. Closing coverage is smaller than the risk
and requires no upstream fork or new subsystem.

## Alternatives rejected

- A new `seshat check` rule: duplicates test/oracle authority and exports
  repository-internal vendoring policy to adopters.
- A third Spec Kit manifest: creates parallel byte authority when the existing
  Claude manifest already covers the sibling nine skills.
- Hash constants directly in a test: duplicates the manifest and makes the test
  its own source of truth.
- Full `.specify/extensions/git/` provenance: a valid future enhancement, but
  not required to close the five-skill capability claim proven here.
- No action: rejected because both representative regressions pass today.

## State conclusion

The repository began this invocation in **STATE A**. The audit proves Phase 11
requires implementation, and Spec 152 is not human-ratified. After the complete
draft package is written, the legitimate state is **STATE B**. Final
Architecture Audit is premature until Spec 152 is ratified, implemented, and
validated.
