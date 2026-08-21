# Contract: Decision Store write boundary (spec 140)

This is the security contract of spec 140. Everything else in the feature is UI over
it. Reviewers should read this file first.

## The claim this contract makes

**Writing a decision is not granting one.**

Studio may append a named human's answer to a Decision Store file in the working tree.
That act confers no authority. Authority is conferred by a human committing the file,
after which the static gate reads it at `HEAD`.

## Why the boundary sits exactly here

Two facts from the shipped tree:

1. `decision_store.approval_is_valid` is documented as "The ONE approval-validity
   predicate shared by DS2 and the gate."
2. `decision_store.store_files()` selects only from **tracked** paths, and
   `DECISION_STORE_CORPUS` is built with `any_tracked_file(*STORE_PATHS, ...)`.

So the gate's notion of a decision is a *committed* decision. Any component that could
both write the file and cause it to be trusted would be able to author its own
approval. Studio writes; Studio must not commit.

## Obligations

### O1 -- Reuse the shipped predicates

The write path MUST call `approval_is_valid` and `owner_shape_ok`. It MUST NOT
reimplement, wrap-and-relax, or shadow them, and MUST NOT introduce a second
approval-validity predicate anywhere in the codebase.

*Rationale*: a second predicate is a second trust path. The two would drift, and the
weaker one would become the real gate.

### O2 -- Validate before write, atomically

Order is: build entry -> validate -> append atomically. A rejected entry leaves the
file byte-identical. An interrupted write leaves the file byte-identical.

### O3 -- Append only

An existing decision entry is never mutated, reordered, or deleted by this path.
Unrelated entries and comments survive round-trip unchanged.

### O4 -- No server-supplied signer, authority, or answer

`signer`, `declared_authority`, and `answer` have **no default** and are never derived
from a proposal, a prior decision, config, environment, or the agent's own reasoning.
Absent means refuse.

*Rationale*: this is Principle V (`never_self_grant_approval`) expressed as a type
constraint rather than a policy note.

### O5 -- No git write

The write path MUST NOT run `git add`, `git commit`, or any equivalent, and MUST NOT
invoke a helper that does. Committing is a human act performed outside Studio.

### O6 -- The receipt cannot claim approval

`DecisionWriteReceipt.state` is a single-member enum (`pending_commit`). The
successful-write type has no `approved` member, so the false claim is unrepresentable
rather than merely discouraged.

### O7 -- Readiness reads HEAD

Readiness recomputation after a write MUST read committed state. A working-tree-only
decision advances nothing.

## Verification -- how a reviewer proves each obligation

Each must be proven by a test that FAILS if the guard is removed. An absence-assertion
alone (grepping that a string does not appear) is not sufficient.

| Obligation | Proof |
| --- | --- |
| O1 | Grep the repo for any second definition of an approval-validity predicate; assert the write path's call reaches the shipped function (e.g. monkeypatch it to reject and assert the write refuses). |
| O2 | Submit an entry that fails validation; assert the file's bytes are unchanged. Interrupt mid-write; assert unchanged. |
| O3 | Append to a file with two existing entries and a comment; assert both entries and the comment survive verbatim and the new entry is last. |
| O4 | POST with each of `signer`/`declared_authority`/`answer` omitted in turn; assert refusal and no write. Assert no code path assigns them a default (test fails if a default is added). |
| O5 | Assert no git-invoking call in the write path; and monkeypatch the git runner to raise, then assert a successful decision write still succeeds. |
| O6 | Assert `state` enum has exactly one member; a test that fails if `approved` is ever added. |
| O7 | Record a decision without committing; assert every readiness stage is byte-identical to before. Then commit and assert it moves. |

**The O7 test is the load-bearing one.** If it passes only because readiness happens
not to be recomputed at all, it is vacuous. It must be paired with the commit case
proving the stage *does* move once committed, so the test can distinguish "correctly
ignores uncommitted state" from "ignores everything".

## Explicit non-goals

- No cryptographic signer verification. The named-human declaration is a local
  attestation, and the UI must not imply stronger assurance (US5 acceptance 4).
- No new store path. The three existing `.seshat/` files remain canonical.
- No approval delegation, escalation, or expiry semantics.
