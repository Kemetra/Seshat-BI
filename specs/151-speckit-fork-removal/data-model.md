# Data model: Spec Kit status governance authority

This feature adds no persisted artifact and no schema. It relocates a policy
that currently exists as prose in an upstream file plus a tuple in a test.

## Canonical source and derived representations

Today there is no canonical source; there are two independent restatements that
disagree (see `research.md` §5). The target:

```
CANONICAL: the Seshat status policy module (src/seshat/)
    |
    +--> tests/unit/test_spec_status_vocabulary.py   imports it (stops declaring VOCABULARY)
    +--> .claude/workflows/implement.js H3 grammar   contract-tested against it (FR-011)
    +--> ADR-0019                                    the DECISION; prose, not executable
    +--> docs                                        descriptive, drift-checked by the same test
```

`.specify/templates/spec-template.md` is deliberately absent from this graph
after the migration. It is upstream's file and holds no Seshat policy.

## The policy the authority owns

| Element | Value | Source today | Source after |
| --- | --- | --- | --- |
| Vocabulary | `draft`, `ratified`, `implemented`, `superseded` | test tuple + template comment | the authority |
| Canonical case | lowercase | template comment | the authority |
| Line prefix | `**Status**:` | test regex | the authority |
| `ratified` evidence | a named human and a date | template comment + H3 regex | the authority; H3 contract-tested against it |
| `implemented` evidence | a tracked artifact path + an SC1 claim | test regex + SC1 | unchanged (SC1 reused) |
| `superseded` evidence | the superseding spec id | template comment | the authority |
| History convention | previous value preserved on `**Status history**:` | template comment | the authority |

## What the authority is NOT

- Not a state machine. It does not model transitions between values, does not
  decide whether a change from `ratified` to `implemented` is permitted, and
  does not track history. It validates a line against a vocabulary and its
  evidence requirement.
- Not an approval authority. Whether a human really approved remains
  `implement.js`'s git-blame provenance check. The authority describes the shape
  of a ratified line; it does not certify that a human wrote it.
- Not a readiness surface. It has nothing to do with the seven-stage spine, and
  must not import it or be imported by it.
- Not a template reader. FR-004 forbids deriving policy from the artifact being
  validated.

## Vocabulary separation

Three vocabularies exist in this repository and are routinely conflated. The
authority owns exactly one:

| Vocabulary | Values | Owner | This feature |
| --- | --- | --- | --- |
| Spec status | `draft`, `ratified`, `implemented`, `superseded` | **the new authority** | relocated |
| SC1 claim status | `built`, `planned` | `rules/status_claims.py` | untouched |
| Readiness four-status | `not_started`, `blocked`, `warning`, `pass` | readiness spine | untouched |

## Comparison semantics for the manifest reconciliation

One narrow rule, and it is the whole of what this feature borrows from
drift-detection:

```
compare(file, recorded_hash):
    raw  = read_bytes(file)
    if sha256(raw) == recorded_hash:            -> MATCH
    if sha256(raw.replace(CRLF, LF)) == hash:   -> MATCH (line-ending artifact)
    otherwise                                    -> REAL CONTENT DIFFERENCE
```

Measured effect on the current tree: 6 raw differences collapse to 1 real one.
A checker without the second branch reports 83% false positives on a clean
Windows checkout of this repository.

This rule applies to the single manifest entry this feature reconciles. It does
not authorize a general drift framework (FR-021, Out of Scope).
