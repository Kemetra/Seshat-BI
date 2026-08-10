# Adversarial Plan Review: Spec 152

## Verdict

**PASS-WITH-NOTES**

The design is proportionate to two proven gaps and does not manufacture a new
architecture layer. Implementation remains unauthorized until named-human
ratification.

## Falsification attempts

### 1. Is the wrapper-delta guard duplicative?

No. The existing oracle protects only `seshat-adapter`. A constructed
upstream-backed `seshat-orchestrator` with no delta returns no violation. The
new condition extends the same detector and same fields rather than adding a
parallel authority.

### 2. Could the wrapper-delta guard create false positives?

The initial broad idea, "every Seshat capability needs a delta," would create
false positives and was rejected. The accepted predicate requires a nonblank
`upstream_project`; internal Seshat capabilities remain unaffected. Current
manifest evidence shows every matching entry already has a delta.

### 3. Is KF-2 only documentary debt?

No. A real one-file mutation passed both the generated-bundle check and all 68
relevant ownership/bundle tests. The gap is executable detection debt.

### 4. Does extending the Claude manifest falsify provenance?

No. Git history shows commit `1eb0c98`, authored by Ahmed Shaaban, added all
fourteen skills, both manifests, the Git extension, and init options in one
sanctioned Spec Kit initialization. The added hashes record existing outputs;
they do not claim a new install or upstream fetch.

### 5. Would a third manifest be cleaner?

No. It would create another byte authority and require deciding precedence.
The existing Claude manifest already covers nine sibling skill outputs and is
the smallest stable place for the remaining five.

### 6. Is a new runtime verifier needed?

No. These are repository architecture contracts. CI already runs the ownership
and contract test surfaces. A CLI or `seshat check` rule would expose internal
vendoring policy to adopters and duplicate enforcement.

### 7. Does the design weaken truth separation or approval?

No runtime/readiness/approval code changes. The package stays draft, tasks stay
unchecked, and the active feature fence stays null. The implement H3 gate still
requires named-human, git-blame-backed ratification on a feature branch.

### 8. Is the scope too small?

No. The user explicitly set a high bar for ADD and destructive cleanup. The
audit found no other architecture-critical gap whose representative regression
currently passes. Full extension-tree provenance is bounded debt, not required
to protect the declared fourteen-skill capability.

### 9. Is the scope too large?

No. Six implementation files, two existing authorities, no production module,
no dependencies, and no CI or route changes. Documentation updates occur only
after detection proof.

### 10. Can the implementation falsely report success?

The plan requires clean -> fail-on-two-seeded-violations -> restored clean, plus
focused official-delegation, readiness, approval, spec-status, bundle, and
static gates. Every command must be reported with its real exit code and
classification.

## Required ratifier decisions

A named human must explicitly accept both bounded decisions:

1. The delta predicate applies to every upstream-backed `seshat-*` owner, while
   the adapter-only rule remains.
2. The existing Claude integration manifest expands from nine to fourteen
   Spec Kit skill hashes; no third manifest is created.

## Review conclusion

The plan has detection value, uses the smallest existing enforcement points,
creates no duplicate source of truth, and preserves fail-closed approval. It is
ready for named-human ratification, not implementation.
