# Release rollback and containment

Rollback is an owner-authorized containment action for one affected surface. An
agent or workflow may detect a defect and prepare evidence, but may not yank,
withdraw, delete, move a tag, change a public listing, or authorize a replacement.

## Shared rules

1. Stop later release actions when public verification fails.
2. Mark the affected surface `blocked` with the concrete observation. Keep every
   unaffected surface's actual status; do not claim a coordinated launch.
3. Preserve the candidate SHA, tag, artifact digests, external acceptance, and
   defect evidence. Never rewrite history to hide a failed release.
4. Obtain a fresh named-owner approval whose action is the exact rollback for
   the exact candidate and surface. A publication approval cannot be reused.
5. Contain only that surface. Replacement always uses a new owner-approved
   version and the complete validation/approval cycle.

## Surface actions

| Surface | Owner-approved containment | Prohibited shortcut | Public verification after containment |
|---|---|---|---|
| PyPI `seshat-bi` | Yank the defective version and update truthful install guidance | overwrite/delete package files or reuse the version | fresh index lookup confirms yanked state; clean install selects only an intended usable version |
| GitHub Release | Amend truthful notes or withdraw the release presentation while retaining the immutable tag/evidence | move or recreate the tag at different source | tag still resolves to its original SHA and release status/notes match reality |
| Claude repository marketplace | Commit a reviewed pointer/content correction or revert through normal Git history | hand-edit generated bundle files or claim external catalog removal | fresh GitHub marketplace add/install resolves the intended reviewed revision |
| Claude public catalog | Ask the eligible publisher/platform to withdraw or correct only that listing | infer authority from repository rollback | public lookup records the actual listing state |
| Codex repository marketplace | Commit a reviewed catalog/plugin correction or revert through normal Git history | mutate a user's personal marketplace or call repository status a public listing | clean CLI and IDE sessions resolve the intended plugin and `$` skills |
| OpenAI public plugin listing | Ask the eligible verified publisher/platform to withdraw or correct only that submission/listing | treat repository catalog removal as public delisting | public lookup records the actual review/listing state |

## Rollback evidence

Record `rollback-<surface>.json` with the trigger, actor, exact action,
candidate, approval ID, factual status, blockers, and UTC timestamp. The approval
must match the rollback action and remain unused/unexpired. Do not include tokens,
real client data, raw PII, or machine paths.

After containment, rerun the relevant clean public-install verification. Keep
replacement status `unverified` until a new version passes every applicable gate
and receives new publication approvals.
