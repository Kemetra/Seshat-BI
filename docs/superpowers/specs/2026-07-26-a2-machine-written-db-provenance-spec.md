# A2 -- machine-written, server-echoed DB provenance -- spec (issue #485)

- **Date:** 2026-07-26
- **Status:** **SPEC ONLY -- DECIDES NOTHING, BUILDS NOTHING.** Written at owner
  direction under ruling R1. No field is added, no schema is edited, no rule is
  wired, and no code path is changed by this document. It exists so the owner can
  rule on a concrete write path rather than on a recommendation.
- **Issue:** #485 -- `seshat next` reports `terminal_pass` from committed
  `mappings/` evidence without cross-checking live DB identity. **Still open.**
- **Parent design note:**
  `docs/superpowers/specs/2026-07-25-live-db-provenance-design.md`, which
  enumerated options A1 / A2 / B / C. This spec details **A2 only**.
- **Already shipped, and NOT a resolution of #485:** option B, the honest
  caveat. `run_next._provenance_caveat` (commit `0095c39`) emits
  `unverified_db_provenance` on `next`, and the human-readable
  `status --format text` render now states the same limit. B says the tool
  *cannot* check provenance; A2 is what makes it *checkable*.

## What A2 is

Persist a **server-echoed** database identity at the moment live findings are
produced, then compare it -- offline -- against the configured DSN whenever
`next` / `status` report a stage that claims live materialization. On mismatch,
downgrade with a named blocker.

The load-bearing word is *server-echoed*. Option A1 (a hand-authored provenance
field) is **REJECTED** and this spec does not revisit it: the only writers of
`readiness-status.yaml` values today are agents and humans editing YAML, so a
digest computed from `.env` is forgeable without ever opening a socket. A field
that can be typed by the party claiming readiness is tool-formatted prose, and
strictly worse than today's honest silence. A2 exists precisely because the
value must come from a process that connected.

## The three seams A2 joins (all already in the tree)

1. **The writer that already connects and persists nothing.**
   `src/seshat/cli/commands/validate.py:93-112` opens the connection, prints
   findings, and sets an exit code. It writes no artifact. It is the only place a
   server-echoed identity is obtainable: `select current_database()` through the
   `QueryRunner` Protocol (`src/seshat/validate.py:34-37`). The database asserts
   its own name -- that is the property env-derived values cannot have.
2. **The emit-only module built for exactly this and never wired.**
   `src/seshat/readiness_evidence.py` is EMIT-only per FR-013 (see its
   docstring), returns a dict, writes nothing, and only tests call
   `build_gold_ready_block`. A dead seam waiting for this payload.
3. **The offline comparison helpers.** `seshat.validate.resolve_dsn(env)`
   (`validate.py:53-83`) is pure env -> string and explicitly driver-free
   (`validate.py:47`); `seshat.connection_env.connection_environment(repo_root)`
   (`connection_env.py:105-115`) overlays `.env` without mutating `os.environ`.
   So the *reader* side of A2 reads configuration only and opens no connection --
   the no-DB/no-network contracts of `agent_next.py:19-24`,
   `status_surface.py:9-11`, and `run_next.py:5-7` stay intact.

## Hard constraint -- a DIGEST, never a raw identity

The persisted value **must** be a stable salted-or-plain digest, e.g.
`sha256("<host>/<dbname>")`, truncated. It must **never** be a raw host or
database name.

`ANALYTICS_DB_NAME` is on this repo's own secret/redaction lists
(`src/seshat/dagster_adapter/redaction.py:53`,
`src/seshat/rules/git_meta.py:506,513`, `src/seshat/severity_posture.py:375`).
Committing a raw host or dbname into a tracked file would trade a correctness bug
for a secret-hygiene bug. A digest compares equal-or-not without disclosing the
target, which is all the gate needs. Any implementation must route DSN handling
through the single hardened decomposition in `redaction_core` rather than
hand-rolling a parser.

## The migration shape -- `source_kind`, not a new required field

Follow the house precedent exactly: `source_kind` (commit `64e3f88`, #120).

- **Optional field.** Absence carries a valid legacy meaning
  (`templates/readiness-status.yaml:56-59` documents the analogous case).
- **The gate fires ONLY when the field is present**
  (`src/seshat/rules/readiness_status.py:393-400` is the pattern).
- **Zero migration.** No committed artifact needs editing.

This is what makes A2 safe to add to a spine where no existing record carries
provenance. A *required* qualifier would fail every table at once; a
present-only qualifier fails exactly the tables that earned a check and then
diverged.

Adding the field to the YAML is **additive**: no schema in `schemas/` validates
`readiness-status.yaml` as an input file, and `status_surface.py:80-97` projects
a strict key whitelist that silently drops unknown input keys. It becomes a
contract change only if someone separately chooses to project it into
`schemas/agent-status.schema.json` (which is `additionalProperties: false`) --
severable, and not required by A2.

## Behavior to specify (the owner is choosing between shapes here, not ratifying one)

**Write side.** After a live `validate` run produces findings, persist
`{digest, captured_at, source: "server_echo"}` for the validated scope. Open
questions the owner must settle: which artifact (the readiness file's stage
block, or a sibling evidence file under `mappings/<table>/`), and whether the
write is atomic-create-only or may update an existing value.

**Read side.** When `next` / `status` report a live-materialization stage
(`silver_ready` / `gold_ready`, the set `run_next._LIVE_MATERIALIZATION_STAGES`
already names) as `pass`:

- field **absent** -> today's behavior plus the shipped B caveat. Never a
  blocker; this is the legacy path.
- field **present and matching** the configured DSN's digest -> the caveat is
  satisfied and drops.
- field **present and mismatching** -> **downgrade with a named blocker**
  identifying the disagreement, naming the owner who can resolve it. Never a
  fabricated pass and never a silent pass.
- configured DSN **absent** -> cannot compare; report that, do not treat absence
  as agreement.

## The one question to settle BEFORE any code

**May `seshat validate` write a committed artifact at all?** Today it
deliberately writes nothing. A2 is not a bug fix; it is a genuine feature that
adds a live-connection write path to a verb whose current contract is
read-and-report. That is an owner decision, not an implementation detail, and
every other choice in this spec is downstream of it.

Secondary questions, all deferrable: whether the digest is salted (and if so,
where the salt lives, given it must not itself be a secret in a tracked file);
whether `dbt/redaction.py:13-40` should stop discarding the host/dbname digest it
already holds at `dbt/project.py:30-38`; and whether the field is ever projected
into the output JSON contract.

## Explicit non-goals

- No hand-authored provenance field (A1 -- rejected, see above).
- No change to the no-DB/no-network contract of `agent_next.py`,
  `status_surface.py`, or `run_next.py`. The reader compares configuration only.
- No numeric score of any kind -- not a confidence, health, or maturity value
  (hard rule #9, Principle V).
- No approval self-granted, no readiness stage moved, nothing published.
- This spec closes no issue. #485 stays open until A2's writer exists.

## Relationship to #493

#493 (the git-ignored Dagster scratch being able to silence the
`[PENDING LIVE PROFILE]` caveat) was a *sibling* trust-boundary defect found
while investigating #485, and is fixed separately: a `verified` live state now
requires the committed `orchestration/dagster/run-evidence/<run-id>.md` to
reproduce the raw records, in ADDITION to every pre-existing scratch check
(commit sha, workspace-dirty, and per-input SHA-256 digests -- the committed
markdown records only a count of input artifacts and so can never grant
`verified` alone). That fix is about *reviewability of the record*; A2 is about
*identity of the database*. Neither substitutes for the other.
