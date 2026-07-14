# Contracts: Shareable Seshat Proof (Showcase Bundle)

Two contract surfaces: the **library functions** (the reusable composition +
rendering layer) and the **skill** (the Option-B user-facing surface). No CLI-verb
contract is defined for the recommended default (Option B; FR-005). NOTE: the
delivery shape (skill vs CLI verb) is an open-for-human ratifier decision (FR-005
+ spec "Open for Human"); this contract documents the recommended skill default.
If the ratifier amends FR-005 to a CLI verb, the user-facing surface contract
changes accordingly while the library-function contract below is unaffected.

## Library function contract

### `build_showcase_bundle(repo_root, *, snapshots=None) -> dict`

- **Inputs**:
  - `repo_root: Path | str` -- workspace root (default `.`).
  - `snapshots: tuple[Path|str, Path|str] | None` -- optional pair of Passport snapshot files for the before/after section.
- **Behavior**: Reads `build_explorer_projection(repo_root)` (stages, evidence states, blockers, approvals, next actions, lineage). Derives the `badge` and the four-category `manifest`, applying portability normalization (abs-path -> repo-relative, private-URL stripped) to the composed content. If `snapshots` is supplied, computes `comparison` using Passport comparability (same `schema_version` + `scope`, differing `source_revision`) and the Passport verify vocabulary; otherwise `comparison` is `null`. THEN runs `scan_disclosure` over the FULL composed body (tables + enriched lineage + approvals + badge + manifest + comparison), merged with the base projection's invariant findings, and stores the result as `disclosure`. Pipeline order: compose -> normalize/redact -> scan full body. **Read-only**: no source artifact is written or mutated.
- **Output**: a `ShowcaseBundle` dict (see data-model.md). `disclosure` is the scan of the full composed body, NOT a carry-through of the Explorer projection's disclosure.
- **Errors**: propagates the projection's input-defect handling (never raises on a malformed readiness file -- it renders as an input defect). Raises only on programmer error (e.g. a non-path snapshot argument).

### `render_showcase_html(bundle, *, repo, rtl=False) -> str`

- **Inputs**:
  - `bundle: dict` -- the `build_showcase_bundle` output.
  - `repo: Path` -- workspace root (for the embedded brand asset only).
  - `rtl: bool` -- when true, render `dir="rtl"` with mirrored layout and Arabic-ready labels.
- **Behavior**: Renders a self-contained offline HTML string: landing page + badge/card + per-table detail + disclosure manifest + optional before/after. Inlines the showcase shell (`showcase.css` / `showcase.js`) and embeds the brand asset as a data URI. Does NOT read arbitrary repo files and does NOT touch `explorer.css` / `explorer.js`.
- **Output**: an HTML string; the caller writes it locally (fail-closed on disclosure).
- **Constraint**: makes no network request; every asset is inlined/embedded.

## Skill contract (`.claude/skills/showcase-build/SKILL.md`)

- **Trigger**: user asks for a shareable proof / showcase / project card of the workspace's readiness.
- **Inputs** (from the user / agent): workspace root; optional output path (must resolve inside `.seshat-output/`); optional `rtl` mode; optional two Passport snapshot paths.
- **Procedure**:
  1. Call `build_showcase_bundle(root, snapshots=...)`.
  2. If `bundle["disclosure"]["status"] != "pass"`: STOP fail-closed, print the findings, write nothing.
  3. Resolve the output path via `resolve_local_output(root, output)` (refuse an uncontained path, exit without writing).
  4. Write `render_showcase_html(bundle, repo=root, rtl=...)` plus any sidecar assets under the contained root.
  5. Print the written path and the reminder that the bundle is local/offline and that publishing is a separate explicit human action.
- **Outputs**: a written bundle path OR a fail-closed findings report. Never a publish, upload, or approval.
- **Refusals**: uncontained output path; blocking disclosure finding; a request to publish/upload (out of scope -- the skill only writes locally).

## Behavioral contract (acceptance-mapped)

| Contract clause | Spec FR | Test |
|-----------------|---------|------|
| Read-only over sources | FR-004 | integration: source artifacts + explorer assets byte-unchanged |
| No new CLI verb | FR-005 | unit: `_DISPATCH` has no `showcase` key |
| Local-only, contained output | FR-006 | integration: uncontained path refused, nothing written |
| Offline / no network | FR-007/008 | integration: bundle opens with assets inlined; no external ref |
| Fail-closed disclosure | FR-009/010 | integration: secret/DSN/PII/abs-path fixture blocks; nothing written |
| No approval / publish granted | FR-011 | unit: bundle records no approval; skill refuses publish |
| Truthful badge | FR-012/013/015 | unit: badge label has no %/grade; onboarding text when none pass |
| Offline badge render | FR-014 | integration: badge is inline SVG/data URI, no fetch |
| Four-category manifest, no silent drop | FR-016/017/018 | unit: coverage + disjointness on mixed-state fixture |
| Path/URL normalization -> redacted | FR-019 | unit: abs-path -> repo-relative + private-url listed under redacted |
| Before/after only when comparable | FR-020/021 | unit: comparable pair diffs; mismatched pair omitted with note |
| a11y / RTL shell | FR-022/023/024/025 | integration: spec-102 contrast/colorblind; dir=rtl; explorer assets untouched |
| No fabricated fact | FR-026/027 | integration: all-missing fixture renders truthful, no invented pass/score |
