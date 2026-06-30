# Phase 0 Research: DF1 Parked-On Map

## Template: SC1 is an almost-exact sibling

`src/retail/rules/status_claims.py` (SC1, shipped under spec 050) is the unambiguous
template. DF1 mirrors its structure decision-for-decision:

| SC1 (prose status claims) | DF1 (parked-on edges) |
|---|---|
| Manifest `docs/quality/status-claims.yaml`, key `claims:` | Manifest `docs/quality/parked-on.yaml`, key `edges:` |
| Lazy `import yaml` inside the rule body | Same (preserves stdlib-only core) |
| Manifest missing/untracked -> ERROR | Same |
| Malformed YAML / wrong shape / missing field -> ERROR | Same |
| `doc` must be tracked; `anchor` must be literally present in `doc` | Same |
| `claimed-artifact` + `claimed-status` (built/planned) | `evidence` (must be tracked) + optional `shipped_when_tracked` |
| `built`+absent -> false-built ERROR | `evidence` not tracked -> unresolved-blocker ERROR |
| `planned`+present -> stale-marker ERROR | `shipped_when_tracked` present -> parked-but-shipped ERROR |
| Categorical, no score; only checks listed claims | Same |
| Live-manifest-vs-real-repo guard test (zero findings) | Same |

The single deliberate divergence: SC1 resolves ONE artifact against a built/planned
flag. A parked-on edge has TWO distinct presence questions -- (a) does the blocker's
evidence (a tracked deferred-spec/spec) exist? and (b) has the blocked target shipped
(contradicting the park)? Encoding (a) as required `evidence` and (b) as OPTIONAL
`shipped_when_tracked` keeps each branch a pure tracked-files membership test, no
execution. See data-model.md.

## Confirmed seams (read against the repo, HEAD on this branch off main)

- **Rule contract**: `src/retail/core.py` exposes `RuleContext(repo_root: Path,
  tracked_files: tuple[str, ...])`, `Finding(rule_id, severity, message, locator)`,
  and `Severity` (ERROR is a member). DF1 is `(RuleContext) -> Iterable[Finding]`,
  identical to SC1.
- **Registry**: `src/retail/registry.py` `@register(id, title)` appends to a central
  list; `all_rules()` returns the tuple. DF1 registers via `@register("DF1", "...")`.
- **Discovery wiring**: `src/retail/rules/__init__.py` imports each submodule for its
  registration side effect and lists it in `__all__`. Adding `parked_on` there is the
  single discovery step (`test_all_submodules_importable` derives the list via
  `pkgutil`, so an unimported module is caught).
- **Drift guard**: `tests/unit/test_rules_wiring.py` `EXPECTED_RULE_IDS` is a frozenset
  of 37 ids today (verified by counting the set, not the comment). The count assertion
  is `len(registry.all_rules()) == len(EXPECTED_RULE_IDS)` -- derived, never hard-coded.
  Adding `"DF1"` moves it to 38.
- **Manifest snapshot**: `src/retail/manifest.py` renders `docs/rules/rules-manifest.json`
  from the live registry; `retail manifest` (`cli.py` `_run_manifest`) writes it. The
  rule-registry snapshot test guards that the committed JSON matches the live registry,
  so DF1 must appear there in the same change (37 -> 38 entries).

## Verified facts grounding the seed manifest

- **F016** is a verified-real, verified-parked shared blocker: named across ~15
  `docs/roadmap/roadmap.md` lines (e.g. the Tier-4 "SHIPPED (except F016)" section and
  the "F016 (Power BI execution adapter) -- gated by hard rule #6 (not startable...)"
  parked-features list). It has zero `src/` footprint by design.
- **Tracked evidence files for the v1 edges** (confirmed in `git ls-files`):
  - pbi-tools extract spike: `docs/superpowers/specs/2026-06-26-pbi-tools-extract-spike-deferred.md`
  - L3 new operators: `docs/superpowers/specs/2026-06-26-l3-new-operators-deferred.md`
  - F031: `specs/025-adapter-maintenance-policy/spec.md`
  - F032: `specs/026-adapter-compatibility-matrix/spec.md`
  - F033: `specs/027-release-maturity-management/spec.md`
- **No `shipped_when_tracked` artifact is present for any v1 edge** (all five targets
  remain parked), so the seeded manifest reconciles to zero findings -> ships GREEN.

## Decisions

- DF1 lives in its own submodule `parked_on.py` (focused module; different manifest +
  semantics from SC1).
- Manifest path `docs/quality/parked-on.yaml`, top-level key `edges:`.
- ERROR severity (spec Q1); categorical, no score (hard rule 9).
- v1 edge inventory = F016 -> {pbi-tools, L3-ops, F031, F032, F033} (spec Q3); F034
  built-page edge excluded (different blocker class).
- Present-but-empty manifest passes clean; only missing/malformed fails loud (spec Q4).
- No constitution amendment / new ADR; no readiness-stage advance (spec Q5).
