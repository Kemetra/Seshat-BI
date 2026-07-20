# Readiness decay -- raise / clear a stale-pass signal (checklist)

Planning (docs/templates; no runtime code) -- DESIGN ONLY, mirroring
`docs/checklists/source-drift.md`'s status. The ordered steps a human (or an
agent acting on their behalf, up to the human-only-reviewer boundary) follows
to raise a `stale_pass` signal by hand, per
`docs/patterns/readiness-decay.md`, and to clear it once a human has acted.
This adds NO new `seshat check` rule and NO new gate -- the existing Source
Ready / stage-approval review is the gate; this checklist only makes its
staleness discipline explicit and repeatable. ASCII only.

---

## 1. Confirm there is something to check

- [ ] The table has a committed `mappings/<table>/readiness-status.yaml`
      (ADR 0004). If NOT, STOP -- there is no committed state to compare;
      this checklist does not apply to a table that has not started.
- [ ] Read `stages.source_ready.status` and every downstream stage's
      `status` + `evidence[]` + `approvals[]` as currently committed.

## 2. Check for drift-triggered staleness (condition 1)

- [ ] Is `stages.source_ready.status` `warning` or `blocked`? If it is
      `not_started` or `pass`, condition 1 does not apply -- skip to step 3.
- [ ] If yes: list every OTHER stage currently recorded `pass`. Each one is
      a separate stale-pass signal -- name each stage individually; never
      collapse them into one "this table is stale" note.
- [ ] Do NOT edit `stages.source_ready.status` or any downstream stage's
      `status` to reflect this signal. Raising the signal is observation,
      not a status edit -- edit only Approvals / the source-drift review's
      own recorded outcome.

## 3. Check for approval-lag staleness (condition 2)

- [ ] For each approval-bearing stage (`mapping_ready`,
      `semantic_model_ready`, `dashboard_ready`, `publish_ready`, or a
      file-source `source_ready`) recorded `pass`:
  - [ ] Find its LATEST `approvals[]` entry (by `at` date) for that stage.
        If NO `approvals[].at` parses for that stage, record that as its
        own gap (do not guess a date, do not skip the stage silently).
  - [ ] For each `evidence[]` entry, determine whether it names an actual
        committed file path (a citation), a path-shaped token pointing
        into a real tracked directory but not to a real file there (a
        stale/broken citation), or plain prose (skip -- not a citation at
        all). See `docs/patterns/readiness-decay.md`'s "What counts as
        the evidence that changed" for the distinction.
  - [ ] For each real citation, find its last commit date. If that date is
        STRICTLY LATER (calendar-day granularity; a same-day tie is NOT
        stale) than the stage's latest approval date, this is an
        approval-lag staleness signal -- name the stage, the evidence
        path, the approval date, and the evidence's later commit date.
  - [ ] Mechanical stages (`silver_ready`, `gold_ready`) have no
        `approvals[]` concept -- skip this check for them; they are
        covered only by step 2 when applicable.

## 4. Decide how to clear each signal (human seam -- HARD STOP)

- [ ] For a drift-triggered signal (condition 1): the human either
      re-confirms the source (records the drift review's outcome and
      updates `stages.source_ready.status` accordingly) or demotes the
      affected downstream stage themselves. Never auto-demote; never
      silently re-pass.
- [ ] For an approval-lag signal (condition 2), the human chooses ONE of:
  - [ ] **Re-approve.** Record a fresh `approvals[]` entry for that stage
        dated on or after the evidence's commit date. This is a full
        re-approval, not a lighter reaffirmation.
  - [ ] **Reaffirm.** Record a `stale_review` entry naming the SAME
        `stage` and the SAME `evidence` path that triggered the signal,
        a shape-valid `reviewer` (`"Person Name (authority_class)"`), and
        an `at` date on or after the evidence's commit date. See
        `docs/patterns/readiness-decay.md` for the full entry shape.
- [ ] An agent MAY draft the `stage`, `evidence`, and `note` fields of a
      candidate `stale_review` entry. The agent MUST leave `reviewer` for
      the human to supply and MUST NOT record the entry without a
      human-supplied reviewer name (Principle V -- never self-grant).
- [ ] A `stale_review` entry dated BEFORE the evidence's triggering commit
      date does not clear anything -- it cannot reaffirm something that
      predates it. Re-date it or use the re-approve path instead.
- [ ] A `stale_review` entry naming a DIFFERENT evidence path than the one
      that triggered a given signal does not clear that signal. One entry
      clears one (stage, evidence) pair only.

## 5. Record no score

- [ ] Confirm neither the raised signal nor its clearing note contains a
      numeric decay/staleness/confidence/completeness value (hard rule
      #9). Record the four explicit statuses, the specific stage(s) and
      evidence path(s), and the dates -- nothing else.

## See also

- The concept + entry shape this checklist operationalizes:
  `../patterns/readiness-decay.md`.
- The prose rule being enforced: `../readiness/source-drift.md`
  ("Downstream-invalidation rule").
- The owner-shape discipline reused for `reviewer`:
  `../../templates/readiness-status.yaml`'s `approvals[]` comment block.
- The transcribe-never-author discipline a future recording surface for
  `stale_review` must follow: `../../.claude/skills/approval-console/SKILL.md`.
