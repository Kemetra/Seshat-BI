# Quickstart: verifying the Idea-Bank Memory Seam (IL1)

**Feature**: 052-idea-bank-memory-seam | **Date**: 2026-06-30

This seam has no live-DB or executor path, so it is verified by inspection + a guard test +
a manual labeling check.

## 1. Inspect the seeded ledger

Open `docs/roadmap/shipped-ideas.yaml`. Confirm:

- Each top-level key is an idea-id (backlog short-code).
- Each entry has `status` (`shipped`/`settled`), `pr_sha` (non-empty evidence), and `f_row`
  (an F-row label or `none`).
- No sample data / domain specifics appear (generic identifiers only).
- The seed covers the ideas currently in the prose "## SHIPPED / SETTLED" appendix
  (A1/B1/B2/F7/F8 shipped; F5/F6 settled).

## 2. Run the guard test

Run the ledger guard test (added by this feature). It MUST assert:

- the file is valid YAML and every entry has the required keys with in-domain `status`;
- the generic-identifiers-only invariant holds (no disallowed values);
- a malformed fixture fails loud, and an absent/empty fixture degrades gracefully.

Expected: the test passes against the committed ledger; the malformed/absent fixtures
exercise the fail-loud / graceful-fallback branches.

## 3. Manual labeling check (Memory stage)

Because the Memory stage is an LLM agent step (not a deterministic function), validate
behavior by reading the stage's prompt/input wiring:

- Confirm the Memory reader is given the ledger contents (resolved via `git rev-parse
  --show-toplevel`, no hard-coded machine path).
- Confirm the precedence rule: on a ledger-vs-prose conflict the ledger value is used and the
  disagreement is surfaced in `notes` (never silently rewritten).
- Confirm an id present in the ledger produces a `prior_ideas[]` entry with the right
  `current_state` and a `state_citation` built from `pr_sha`/`f_row`, so `renderMemoryLine`
  lists it under KNOWN HISTORY rather than letting it be re-proposed as new.

## 4. Confirm what did NOT change

- No roadmap F-row is written by any step (grep the engine output -- it never appends to
  `roadmap.md`).
- No new `EXPECTED_RULE_IDS` entry; no `src/retail/rules/` file added (optional rule deferred).
- Ground remains the only git reader; the Memory stage still does not re-read git.
