# Contract: Publication Authorization Boundary

**Contract ID**: `PAB-1`
**Requirements**: FR-032--FR-036, FR-039--FR-041, FR-048, SEC-004

## Principle

Repository validation proves facts; a named human grants authority. No agent, merge, check, generated file, environment, or previous decision may self-ratify a release action.

## Five lanes

| Lane | Examples | Planned artifact/evidence | Authority |
|---|---|---|---|
| 1. Repository implementation | metadata, exporter, generated bundles, tests, docs, inert workflow definitions | reviewed code/docs, CI and acceptance evidence | normal repository maintainers/reviewers; does not publish |
| 2. PyPI/GitHub configuration | protected `pypi` environment, named reviewers, Trusted Publisher binding, tag protection | settings screenshots/exports and identity tuple | eligible named repository/PyPI owner |
| 3. Claude publication | public GitHub marketplace availability; optional official-catalog submission | external Claude acceptance; listing/submission evidence | repository owner for Git distribution; separately eligible publisher for catalog |
| 4. Codex publication | repository catalog/plugin availability; OpenAI public plugin submission | external Codex acceptance; eligibility/listing/test/policy evidence | repository owner for Git distribution; separately verified eligible OpenAI publisher |
| 5. Irreversible release | version approval, tag, PyPI upload, GitHub Release, catalog submissions | candidate digest pack and action-scoped approval | named owner eligible for each exact action |

## Actions and gates

| Action | Minimum preconditions | Required approval |
|---|---|---|
| Merge repository implementation | normal review, all repository checks | repository merge approval only |
| Configure GitHub `pypi` environment | owner identity and reviewer plan | named repository owner |
| Register PyPI Trusted Publisher | confirmed project name/owner and exact repo/workflow/environment tuple | named PyPI/project owner |
| Approve release version | zero blockers, version history reconciled, complete evidence pack | named release owner bound to version/SHA/digests |
| Create `v{version}` tag | approved version and exact revision | explicit `create_release_tag` approval |
| Upload wheel/sdist | protected environment approval, exact validated digests, OIDC identity | explicit `publish_pypi` approval by named environment reviewer/owner |
| Publish GitHub Release | tag and public verification evidence as policy requires | explicit `publish_github_release` approval |
| Submit Claude public catalog | passing Claude acceptance and current submission evidence | explicit `submit_claude_catalog` approval |
| Submit through OpenAI's public plugin process | passing Codex acceptance, Apps Management Write, verified identity, complete listing/test/policy evidence | explicit `submit_openai_plugin` approval |
| Yank/withdraw/repoint public surface | defect evidence and rollback plan | named owner for affected external surface |

Each approval is action-specific. One row cannot authorize another.

## Protected PyPI workflow boundary

The planned workflow separates:

```text
unprivileged build -> unprivileged validation -> immutable artifact handoff
                                                    |
                                     protected `pypi` environment approval
                                                    |
                                publish job with `id-token: write` only
```

Rules:

- Build/test jobs have no package-index credential and no `id-token: write`.
- Publish job checks out no mutable source when it can consume validated artifacts directly.
- The job accepts only exact expected wheel/sdist files and verified digests.
- GitHub environment requires a named eligible reviewer; the workflow cannot approve itself.
- Trusted Publisher identity is bound to `ahmed-shaaban-94/Seshat_BI`, the exact release workflow filename, and environment name.
- No long-lived PyPI token is stored as a release secret.
- Forks, unprotected references, mismatched tags, or changed artifacts fail closed.

## Approval record

Before an owner-only action, evidence MUST record:

- named approver and eligibility;
- exact action;
- candidate version/full SHA;
- wheel/sdist and bundle manifest digests as relevant;
- evidence reviewed and unresolved blockers (must be none for publication);
- timestamp, scope, and any expiry/conditions.

“CI passed,” “approved,” a pull-request approval, or an agent recommendation without these bindings is insufficient.

## Staged availability

Python, repository Claude, repository Codex, Claude public catalog, and OpenAI's public plugin listing may become available at different times. Documentation and release status MUST name the actual state of every surface. A pass or approval for one surface never permits the others to be described as public.

## Rollback authority

- Automated tests may detect and report a defect but may not yank, withdraw, delete, move tags, or change public listings.
- A named owner authorizes containment per affected surface.
- Immutable artifacts/tags remain historical evidence; replacement uses a new approved version.
- A rollback approval does not authorize replacement publication.

## Forbidden shortcuts

- an agent setting version status to approved;
- a workflow creating a tag because tests passed without action-scoped approval;
- giving `id-token: write` to build/test jobs;
- storing a reusable PyPI token as convenience fallback;
- treating repository marketplace/catalog availability as OpenAI public plugin acceptance;
- reusing a Claude submission approval for Codex, or vice versa;
- deleting/moving evidence to make a failed release appear never to have occurred.
