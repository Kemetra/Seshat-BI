# Quickstart: Studio Operations and Client Review (spec 141)

**This feature is not implemented.** This file describes the intended journeys so a
reviewer can judge the specification, and so implementers have an acceptance script.
Nothing here works today.

## Prerequisites

- Seshat installed with app extras (`pip install "seshat-bi[app]"`).
- Spec 140 shipped (it is: merged `421c8f4d`, accepted 2026-08-21), so proposals,
  decisions, apply and scoped review exist.
- Studio running: `seshat studio`.

## Journey 1 -- Diagnose why something cannot proceed (US1)

1. Open Operations. Seven components appear, each with its own state.
2. **No overall number anywhere.** If you see a percentage or a grade, that is a defect.
3. A component with no DSN configured reads **`deferred`**, not red. That distinction is
   the point: deferred means "legitimately unavailable", and colouring it as failure
   teaches technicians to ignore failures.
4. A component that could not be read reads `failed` with its reason -- never `healthy`.
5. Each state links to the rule ids that produced it, so you can check the diagnosis
   rather than trust it.
6. A recovery action is shown. **Clicking it does not repair anything** without the same
   technical approval any other mutation needs.

**Acceptance**: try the recovery action without approval and watch it refuse. Then grant
approval and watch it proceed — if it refuses both times, the refusal proves nothing.

## Journey 2 -- Read the run history (US2)

1. Open the history view. Recent governed runs list what was requested, which tools were
   proposed, who decided, which gates ran, and the categorical outcome.
2. Runs are labelled **ephemeral** or **durable**. A durable run cites its committed
   source; a run that cannot cite one is shown as ephemeral rather than promoted.
3. A decision still in `pending commit` appears as **pending**, not as a settled ruling.
4. Restart Studio. The ephemeral entries are gone; the durable ones remain.

**Acceptance**: step 4 is the test. If ephemeral entries survive a restart they were
persisted somewhere they should not be. If durable entries vanish, they were never durable.

## Journey 3 -- Prepare a client review (US3)

1. Select the approved metrics, decisions, evidence, blockers and next responsibilities.
2. Preview the narrative. It says only what your selection says -- no sentence appears that
   you did not select.
3. Pending and blocked items appear **as pending and blocked**, in their own section. They
   are never rewritten as progress.
4. Export. The artifact is self-contained: open it with the network disabled and it renders
   completely.
5. Search the export for a DSN, a password, an absolute path, or an internal command name.
   Find none.

**Acceptance**: step 5 on a workspace that genuinely contains those things. An export from
a clean workspace proves nothing.

## Journey 4 -- Let a client respond (US4)

1. As the client, acknowledge the result. This is recorded as an acknowledgement.
2. Check the decision store. **Nothing was written there** -- acknowledgement is not a
   ruling.
3. Request clarification, or decline. Both are always available.
4. To answer a scoped business question, use the Workbench's named-human decision form --
   the same one spec 140 shipped, not a second path.

**Acceptance**: step 2. If acknowledging wrote a decision entry, the two concepts have
collapsed.

## Journey 5 -- Assemble a support bundle (US5)

1. Export a support bundle from a workspace containing a `.env`, a DSN in a note, and
   absolute paths.
2. Open the archive. It contains none of them, and its manifest lists exactly which
   fields and files were allowlisted.
3. Now make the redaction scan fail (a residual secret). **No archive is produced at all**
   -- not a partial one.

**Acceptance**: step 3. A partially scrubbed bundle is worse than none, because whoever
receives it assumes it was scrubbed.

## What to check if you are reviewing this specification

Three questions, in order of how much damage a wrong answer does:

1. **Can any surface make a pending fact look settled?** See
   `contracts/export-boundary.md` O1.
2. **Can any export disclose a field nobody allowlisted?** See O2 -- and note the test
   adds an unexpected upstream field *without* changing export code.
3. **Can a diagnostic repair anything without approval?** See O4.
