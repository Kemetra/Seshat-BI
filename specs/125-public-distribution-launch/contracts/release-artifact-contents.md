# Contract: Release Artifact Contents

**Contract ID**: `RAC-1`
**Requirements**: FR-006--FR-012, FR-045, SEC-001, SEC-004, SEC-005

## Artifact set

One release candidate MUST produce and validate exactly:

1. one pure-Python wheel for `seshat-bi`;
2. one source distribution from the same immutable source;
3. one generated Claude plugin tree and manifest;
4. one generated Codex plugin tree and manifest; and
5. one evidence manifest recording source revision, version, filenames, SHA-256 digests, checks, and sanitized evidence references.

Only the wheel and sdist are uploaded to PyPI. Agent bundles are distributed from the canonical repository/plugin paths unless a separately approved public plugin process creates its own reviewed artifact.

## Python metadata requirements

Wheel and sdist metadata MUST agree on:

- normalized project name `seshat-bi`;
- owner-approved version;
- concise public summary and long description/readme content type;
- supported Python range;
- Apache-2.0 expression and included license/notice files;
- author/maintainer identity approved for public display;
- canonical repository, documentation, issue, and changelog URLs;
- runtime dependency declarations and optional extras; and
- both public console entry points, `seshat` and `retail`.

`twine check --strict` MUST pass for both files.

## Wheel contents

### Required

- importable `seshat` and compatibility `retail` packages needed by declared entry points;
- package metadata and license/readme metadata;
- the declared, sanitized demo/mapping/template assets needed for first success;
- no file required only from the source checkout.

### Prohibited

- tests, specs, CI/workflow files, contributor docs, build caches, bytecode, coverage, worktrees;
- `.env`, tokens, credentials, DSNs, real hosts, absolute local paths, local settings;
- client-specific data, raw PII, approval drafts, screenshots/evidence packs;
- database/browser/build/test packages bundled or declared as mandatory runtime dependencies;
- an agent plugin tree unless explicitly required by and added to this contract (not planned for Public Beta).

## Source distribution contents

### Required

- all source and build configuration needed to rebuild the same wheel in an isolated environment;
- public readme/license metadata;
- the same runtime package resources required by the wheel;
- contributor/build files only when genuinely required for isolated build.

### Prohibited

- untracked/local files relied upon by the build;
- generated distributions, environments, caches, coverage, secrets, client data, local settings;
- unrelated repository integration bundles or historical evidence unless deliberately required and reviewed.

## Agent bundle contents

Claude and Codex trees MUST match their generated-bundle contracts exactly. Every non-manifest output has reviewed template or allowlist provenance. Development-only root files and the other platform's manifest are prohibited.

## Validation sequence

1. Start from a clean immutable source checkout.
2. Clear/replace the isolated output directory without touching user files.
3. Build once and assert exactly one `.whl` and one `.tar.gz`.
4. Run strict Twine checks against both.
5. Parse and compare metadata.
6. Inventory archive paths, modes, sizes, and digests; apply required/prohibited policy.
7. Scan text content and filenames for secrets, PII/client markers, local paths, caches, and development material.
8. Build a new wheel from the sdist in a clean isolated environment.
9. Compare normalized wheel metadata and governed content with the original wheel; explain only allowed build-tool metadata variation.
10. Install the validated original wheel through pipx and run lifecycle acceptance.
11. Regenerate and validate both agent bundles.
12. Write the evidence manifest without credentials or machine-specific paths.

Any failed or missing step blocks publication.

## Python lifecycle matrix

| Step | Required evidence |
|---|---|
| Clean install | pipx/installer source is exact candidate wheel/public index; installed version matches. |
| Command discovery | `seshat` and `retail` resolve from isolated environment. |
| Dependency closure | Normal environment excludes every dev/test/browser/live-db/engine extra. |
| First success | Fresh project initializes and reports evidence-backed earliest action without a score. |
| Upgrade | Prior supported install moves to candidate; project data remains unchanged. |
| Uninstall | Package and both console commands are absent; project remains intact. |
| Windows | All lifecycle steps are blocking on supported Windows/Python combination. |
| Other OS | Support/blocking status is explicit and evidence-backed in policy. |

## Immutability

Once a wheel/sdist version is public, its bytes are immutable. A defect is contained through yank/status correction and a newly approved version; the artifact is never overwritten.
