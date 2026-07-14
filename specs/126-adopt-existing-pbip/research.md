# Research: Governed Existing PBIP Adoption

## 1. Product boundary

**Decision**: Implement adoption as a thin composition surface over existing
PBIP readers, governance rules, committed readiness projections, blocker
explanations, and run-next logic.

**Rationale**: Seshat already owns these decisions. Adoption needs to make them
useful at the entry boundary, not create an eighth readiness stage or a second
gate.

**Alternatives considered**: A standalone adoption workflow/state machine was
rejected because it could disagree with the seven-stage readiness spine. Treating
PBIP existence as a semantic/dashboard pass was rejected because artifact
presence does not establish meaning, approval, or live correctness.

## 2. Command shape

**Decision**: Add one top-level verb group:
`seshat adopt-pbip assess --project PATH --format text|json` and
`seshat adopt-pbip scaffold --project PATH --accept-assessment SHA256 --format text|json`.

**Rationale**: Separate subcommands make the no-write assessment boundary
unambiguous and make the single mutation an explicit, auditable user action.

**Alternatives considered**: An interactive prompt was rejected because it is
harder for agents and CI to reproduce. A single command with `--write` was
rejected because accidental mutation would be too easy. Persisting an assessment
file by default was rejected by clarification.

## 3. Explicit acceptance and stale-input safety

**Decision**: Assessment computes a SHA-256 digest over canonical substantive
JSON (excluding the digest itself and non-authoritative timing metadata).
Scaffolding recomputes the assessment, requires an exact
`--accept-assessment` match, and refuses if any input or planned write changed.

**Rationale**: The digest binds consent to the facts, blockers, next step, and
declared write plan the analyst actually reviewed. It prevents a time-of-check /
time-of-use gap without persisting a report.

**Alternatives considered**: A boolean `--yes` cannot prove which assessment was
accepted. Reading a saved assessment file contradicts the stdout-only default and
introduces stale or forged input. A timestamp is non-deterministic and does not
bind content.

## 4. Scaffold artifact

**Decision**: The only v1 write is the new
`.seshat/adoption/pbip-adoption.yaml`. It records the accepted assessment digest,
safe project-relative component fingerprints, observations/proposals, concrete
blockers, an empty `approvals` list, and the canonical next-step projection. It
does not create a source map, decision-store record, metric contract, approval,
or `readiness-status.yaml`.

**Rationale**: One baseline manifest is the minimum durable seam needed for
change detection while keeping all business and readiness authority in existing
artifacts. It is Seshat-owned, reviewable in Git, and collision-safe.

**Alternatives considered**: Calling `seshat init` was rejected because it can
rewrite fenced regions and several substrate files, exceeding the declared
minimal write. Creating per-table readiness files was rejected because PBIP
structure cannot establish source identities or stage results. Creating the
three Decision Store files was rejected because empty files add no adopted fact
and inferred records could look authoritative.

## 5. PBIP discovery and parser reuse

**Decision**: Resolve one bounded target, inventory supported `.pbip`, TMDL, and
PBIR paths deterministically, then pass readable text to existing TMDL/PBIR
readers. Record unsupported schema/visual boundaries as
`unavailable_with_reason`; do not silently choose among ambiguous reports/models.

**Rationale**: Existing readers encode the formats Seshat has actually verified.
Project-relative locators keep evidence reviewable without exposing machine-local
paths.

**Alternatives considered**: A generic recursive JSON/TMDL parser would fork
shipped format knowledge. Opening Desktop or Fabric would cross the offline and
feature-016 boundaries. Selecting the first model/report would turn filesystem
order into an undisclosed business decision.

## 6. Governance and version-control boundary

**Decision**: In a Git worktree, build the existing rule context and collect the
existing rule identities in memory. Mark dirty/untracked governed inputs as
changed and ineligible for committed evidence. Outside Git, inventory still
runs, but governance/readiness evidence is unavailable and the single next step
is to initialize version control explicitly and reassess. Scaffold requires an
existing Git worktree and never initializes it.

**Rationale**: Existing checks define the authoritative static rule set and Git
defines reviewable evidence. This preserves useful read-only discovery without
pretending non-versioned files are committed facts.

**Alternatives considered**: Feeding every untracked file into the rule runner
would change its committed-files boundary. Automatically running `git init` was
rejected by clarification and because repository creation is user authority.

## 7. One project-level next step

**Decision**: Use `build_run_next_response` for every canonical table and select
the earliest unresolved stage by the existing stage order. If no readiness table
exists, reuse its Source Ready start action. A tie or ambiguous component scope
produces one project-level resolution action rather than silently selecting a
table. Version-control, unsafe-path, stale-acceptance, and unsupported-PBIX stops
take precedence because the canonical evidence cannot yet be evaluated safely.

**Rationale**: This is deterministic project-level coordination of existing
answers, not new readiness semantics. Exactly one action keeps the agent and
analyst on a safe path.

**Alternatives considered**: Returning one action per table violates the spec.
Choosing a table alphabetically would hide a scope judgment. Using stored
`next_action` strings alone would skip run-next's approval and malformed-input
checks.

## 8. Output parity and disclosure

**Decision**: Build one normalized assessment dictionary and one normalized
scaffold-result dictionary, validate/scan each before rendering, serialize them
directly for JSON, and derive text only from the matching normalized object.
Redact values during collection and run `scan_disclosure` fail-closed on the
final object. Emit no absolute root, raw values, source rows, credentials, or
connection strings.

**Rationale**: One model makes text/JSON equivalence testable and prevents a safe
JSON route from coexisting with a leaky human renderer.

**Alternatives considered**: Separate text and JSON collectors can drift. A
post-render regex-only scrub cannot reason about structured secret/PII fields.

## 9. Safe publication

**Decision**: Preflight the fixed target and every resolved parent, render the
complete UTF-8/LF manifest in memory, stage it in a same-filesystem temporary
location, publish only when the destination is still absent, and clean staging
on every handled failure. Any collision or path/symlink escape fails before the
governed target appears; existing files are never opened for writing.

**Rationale**: The one-file design minimizes transaction complexity while meeting
no-overwrite, containment, and no-partial-result requirements.

**Alternatives considered**: Direct `write_text` can leave a partial governed
file. `os.replace` can overwrite a racing destination. Multi-file scaffolding
adds rollback states without additional v1 value.

## 10. PBIX boundary and verification

**Decision**: Recognize a `.pbix` path only to return a terminal supported stop
with Power BI Desktop's PBIP-save conversion guidance. Test assessment byte
identity, secret absence, deterministic canonical output, text/JSON parity,
digest mismatch, Git prerequisite, collisions, simulated publication failure,
ambiguous/missing model references, unsupported schemas, and reassessment drift.

**Rationale**: Binary parsing is unsafe and out of scope; explicit boundary tests
make the promise durable.

**Alternatives considered**: ZIP probing or third-party extraction was rejected
because PBIX is not a supported v1 contract and would add dependencies and
mutation risk.

## 11. Agent and marketplace discovery

**Decision**: Extend the existing repository-local `pbip-workflow` skill with the
governed adoption entry path, add the route to the shared public `seshat-bi`
router, update the capability manifest, and regenerate both committed Claude and
Codex bundles through `scripts/export_agent_bundles.py`.

**Rationale**: Seshat BI is agent-first and the package, Claude marketplace, and
Codex plugin are already shipped surfaces on main. A CLI-only feature would be
harder for the target AI-assisted Power BI analyst to discover. One shared router
keeps the two public bundles behaviorally aligned.

**Alternatives considered**: A new standalone public skill was rejected for v1
because the existing Seshat router can select the installed command and preserve
the portable operating contract. Hand-editing generated integration bundles was
rejected because their provenance and deterministic regeneration are enforced by
contract tests.
