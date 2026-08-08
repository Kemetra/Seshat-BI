# Research: Spec Kit template fork removal

All findings measured on `main` at `766c0ee`, 2026-08-08. Nothing here is
inherited from the earlier ownership audit; every claim was re-derived.

## 1. The fork is real and still present

```
git diff 1eb0c98 HEAD -- .specify/templates/spec-template.md
 1 file changed, 11 insertions(+), 1 deletion(-)
```

Upstream baseline seeds:

```
**Status**: Draft
```

The tree carries:

```
**Status**: draft

<!-- One of: draft | ratified | implemented | superseded (ADR 0019).
     ... 8 more lines ... -->
```

Introduced by `f35612f`, "feat: close the spec status vocabulary and lock the
implemented claims". Deliberate, and backed by ADR-0019, which is owner-ratified
(Ahmed Shaaban, 2026-07-30).

## 2. Hash drift: one real, five artifacts

Recomputing SHA-256 for every file in `.specify/integrations/speckit.manifest.json`:

```
speckit: 10 tracked | drift=6 missing=0
  DRIFT: .specify/scripts/powershell/check-prerequisites.ps1
  DRIFT: .specify/scripts/powershell/common.ps1
  DRIFT: .specify/scripts/powershell/create-new-feature.ps1
  DRIFT: .specify/scripts/powershell/setup-plan.ps1
  DRIFT: .specify/scripts/powershell/setup-tasks.ps1
  DRIFT: .specify/templates/spec-template.md
```

Re-running with `\r\n` normalized to `\n` before hashing:

```
LF-NORMALIZED MATCH: check-prerequisites.ps1
LF-NORMALIZED MATCH: common.ps1
LF-NORMALIZED MATCH: create-new-feature.ps1
LF-NORMALIZED MATCH: setup-plan.ps1
LF-NORMALIZED MATCH: setup-tasks.ps1
REAL CONTENT DRIFT:  spec-template.md
```

**Five of six apparent drifts are CRLF checkout artifacts**, produced by this
repo's own `core.autocrlf=true`. A byte-comparison drift checker would report
83% false positives on a clean Windows checkout. Exactly one file has real
content drift, and it is the fork.

This is why FR-021 requires normalization before comparison. It is also why this
feature does not build a general drift framework: the useful part of that
framework is one line of normalization, and the rest is deferred scope.

`.specify/integrations/claude.manifest.json` (9 skill files) shows `drift=0`, so
the audit's narrower claim about those files remains true.

## 3. Nothing verifies the manifest

No file under `src/seshat/` reads `speckit.manifest.json`. The recorded hash for
the template has not matched the file since `f35612f`, and nothing noticed. The
`hashlib` code that does exist under `src/seshat/integrations/` verifies
downloaded npm/PyPI artifacts -- a different subsystem.

The manifest is therefore a record, not a gate. This feature reconciles the one
stale entry; making the manifest enforced is deferred scope.

## 4. The vocabulary exists in exactly one place in code, and it is a test

Grepping `src/seshat/` for `ratified` and `superseded` returns **zero** files.
The only code declaration is:

```python
# tests/unit/test_spec_status_vocabulary.py:27
VOCABULARY = ("draft", "ratified", "implemented", "superseded")
```

The same module reads the template and asserts the vocabulary block is present.
So today the test is simultaneously the policy author, the policy reader, and
the policy checker, and the artifact it validates is the artifact it derives
its expectation from. That circularity is the reason FR-004 exists.

The test is a genuine CI gate (`@pytest.mark.unit`; `.github/workflows/ci.yml:57`
runs `pytest -m unit`), so the enforcement is real -- it is the placement that is
wrong, not the strictness.

`src/seshat/rules/status_claims.py:54` declares
`_VALID_STATUS = frozenset({"built", "planned"})`. Different field, different
vocabulary, easy to conflate. SC1 never reads the template.

## 5. The two ratification grammars disagree, provably

`.claude/workflows/implement.js:24-26`:

```js
const H3_RATIFIED_RE = /^\s*-?\s*\*\*Status:?\*\*:?\s*Ratified \(.+?,\s*\d{4}-\d{2}-\d{2}\)/m
const H3_DRAFT_RE    = /^\s*-?\s*\*\*Status:?\*\*:?\s*Draft\b/mi
```

`H3_RATIFIED_RE` has no `i` flag and requires parentheses. ADR-0019 mandates
lowercase `ratified`. Executed against the merged
`specs/150-dbt-evidence-consumer/spec.md`:

```
ACTUAL LINE : "**Status**: ratified -- Ahmed Shaaban, 2026-08-08"
H3_RATIFIED matches? false
H3_DRAFT    matches? false
=> implement.js would REFUSE (H3)
```

A spec ratified exactly as the ADR instructs is refused by the workflow that
consumes ratification. The failure direction is safe -- it refuses rather than
proceeds -- but the two authorities were never reconciled against one grammar.
The comment above the regexes describes them as "two independent verifiers of
one disk string"; they are currently two verifiers of two different strings.

Any externalization that does not fix this gives the disagreement a permanent
home, which is why it is US3 rather than deferred scope.

## 6. What actually enforces ratification

`implement.js:220-228` gates implementation on H3 plus a git-blame provenance
check (`status_line_provenance.introduced_by_human`), so an agent cannot
self-ratify by writing the string. `idea-to-spec.js` is structurally forbidden
from emitting "Ratified" at all.

This lives in `.claude/workflows/`, one level above the Python package. It is
Seshat-owned harness content, not upstream Spec Kit content, so this feature may
edit it. No `seshat check` / `kit-lint` rule enforces spec status; ADR-0019 §3
says so explicitly.

## 7. The fences are unrelated

`src/seshat/fence.py` owns the SESHAT-KIT fence and is explicitly tested to
leave the adjacent SPECKIT fence byte-identical
(`tests/unit/test_fence.py:90-100`). The SPECKIT fence has no code writer at
all. Neither depends on the template. Out of scope, and must stay working.

## 8. The stale audit line

`docs/capabilities/ownership-audit.md:217-218`:

> it is unpaid today because the copy is
> provably unmodified, but nothing keeps it that way

False as of `f35612f`. Line 178's narrower claim -- "Hash-verified against
`.specify/integrations/claude.manifest.json`, zero local drift" -- is about the
nine skill files and remains true; it must NOT be edited. Only the 217-218
passage is wrong.

## Conclusion

The fork is real, singular, deliberate, and depended upon by exactly one test
that is also its own oracle. Removing it requires building the authority the
repository never built, reconciling a grammar conflict that predates this
feature, and restoring the template last. No general Spec Kit supply-chain work
is needed to accomplish that.
