# 0012 -- P2 accepts the full Conventional-Commits type set plus `brand`, stays scope-free, and exempts automated `[name]` subjects

- **Date:** 2026-06-26
- **Status:** Accepted
- **Context:** P2 ("commit-message convention", `src/retail/rules/git_meta.py`)
  enforces the repo's commit-subject form. Its original type whitelist was the
  narrow core set `feat|fix|refactor|docs|chore`. That over-rejected legitimate
  Conventional-Commits types the project already uses in practice (e.g. `build`,
  `ci`, `perf`, `test`, `style`, `revert`) and had no concept of the
  project-specific visual-identity (`brand`) commits. Separately, squash-merging
  a bot-authored PR produces a subject the kit does not author and cannot reshape
  (e.g. a leading `[codex]` / `[bot]` tag), yet P2 flagged those as ERRORs. This
  ADR records the widened type set, the deliberately retained no-scope stance,
  and the new automation exemption.

## Decision

### 1. P2 accepts the standard Conventional-Commits types plus `brand`

The HUMAN-subject type whitelist (`_P2_TYPES`) is widened from
`feat|fix|refactor|docs|chore` to:

```
feat, fix, refactor, docs, chore, build, ci, perf, test, style, revert, brand
```

All but `brand` are standard Conventional-Commits types. `brand` is
project-specific -- it tags visual-identity / asset commits (logos, palettes,
report theming) that do not fit `feat`/`docs`/`chore` cleanly. A human subject
must still match `^<type>: <desc>`.

### 2. P2 remains DELIBERATELY SCOPE-FREE

A parenthesized scope -- `type(scope):`, e.g. `docs(018):` -- is still REJECTED.
This preserves the prior no-scope rule: speckit-chain branches carry numeric
feature scopes locally, but the squash-merge collapses them to a single
scope-free subject. Use `docs:`, never `docs(018):`. Widening the type set does
NOT relax this -- `SUBJECT_RE` admits a bare type followed by `: ` only.

### 3. NEW automation exemption: a leading `[name] ` subject is accepted as-is

A subject whose first token is a bracketed name -- matched by
`_BOT_PREFIX_RE = ^\[[A-Za-z0-9_-]+\] ` (e.g. `[codex] ...`, `[bot] ...`) -- is
treated as an automated / tool-generated commit and skipped before the
`<type>: <desc>` check. Rationale: such a subject arrives via a squash-merge of a
bot PR; the kit does not author it and cannot enforce a format it does not
control. The exemption is narrow -- only subjects with the leading bracket
prefix. Human subjects (no bracket prefix) must still be `<type>: <desc>`,
scope-free; the prefix is not a general escape hatch a human can opt into for a
malformed subject.

## Consequences

- Common, legitimate commit types no longer trip a false P2 ERROR; the project's
  `brand` convention is now first-class.
- The no-scope invariant is unchanged and still enforced -- the only relaxation
  is which bare types are admitted, not the structural form.
- Bot-PR squash merges pass P2 without weakening the human convention, because
  the exemption is keyed on a syntactic marker the kit can recognize but a
  careless human subject will not accidentally carry.
- The P2 ERROR message now states the full type list, that scopes are
  disallowed, and that `[bot] ...` subjects are exempt -- so a failing author
  sees the exact contract.

## Numbering note

ADR numbers 0008-0011 are RESERVED for the planned F024-F033 companion tier (see
`docs/roadmap/roadmap.md`). This decision therefore takes **0012** to avoid
colliding with that reserved block.

## See also

- The rule + types: `src/retail/rules/git_meta.py` (`_P2_TYPES`,
  `_BOT_PREFIX_RE`, `SUBJECT_RE`, `rule_p2_commit_subjects`).
- The tests: `tests/unit/test_git_meta.py`.
- The reserved-numbering source: `docs/roadmap/roadmap.md`.
