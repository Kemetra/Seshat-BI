# Release-State Ledger — Spec 125 owner-only tasks vs actual public state

**Milestone**: RM-00B (Release Truth Reconciliation)
**Produced**: 2026-08-15
**Repository**: `Kemetra/Seshat-BI`
**Inspected main**: `94a64d87` (post `#647`)
**Method**: read-only inspection of live public surfaces + repository history.
No release action, no publication, no checkbox edit was performed by this
reconciliation.

---

## 1. Why this ledger exists

Spec 125 tasks **T073–T091** are all unchecked. They are also all `OWNER-ONLY`
publication actions. Meanwhile `v1.0.0` **is published** on every channel Spec 125
governs.

That combination is a trap, not a backlog. An agent instructed to "finish the open
tasks in Spec 125" would read 19 unchecked boxes and could re-run tag, PyPI, npm, or
catalog actions against a version that already shipped. Those actions are
irreversible: tags are immutable and PyPI forbids re-uploading a filename.

This ledger records what actually happened so the unchecked boxes can no longer be
misread as missing work. Per the roadmap it **appends**; it does not rewrite the
historical task ledger and does not tick the boxes. Only the named owner may do that.

---

## 2. Verified public state

Every row below was observed directly, not inferred from repository files.

| Surface | Observed | Evidence |
|---|---|---|
| Git tag `v1.0.0` | commit `adefa70f` | `git rev-parse v1.0.0` -> `85e1be38` (tag object) -> `adefa70f` |
| Tag's commit | `Merge pull request #624 from Kemetra/release/v1.0.0` | merge COMMIT, matching the coordinated-release rule that a release PR must never be squashed |
| Tag on main | yes | `git merge-base --is-ancestor` |
| Version at tag | `1.0.0` | `pyproject.toml` at `adefa70f` |
| GitHub Release | published `2026-08-13T11:57:09Z`, not draft, not prerelease, author `Kemetra`, 0 assets | `gh release view v1.0.0` |
| Release workflow | success, `sha=adefa70f`, `2026-08-13T11:54` | `gh run list --workflow=release.yml` |
| PyPI `seshat-bi` | `1.0.0` is latest | pypi.org JSON API |
| PyPI artifacts | `seshat_bi-1.0.0-py3-none-any.whl` (sha256 `3b3d5d5db3a8aa32473bc212…`), `seshat_bi-1.0.0.tar.gz` (sha256 `78b342c173fff56b63ade860…`), both uploaded `2026-08-13T11:55` | pypi.org JSON API |
| npm `@kemetra/seshat-bi` | `1.0.0` is latest | registry.npmjs.org |
| npm `seshat-bi` (alias) | `1.0.0` is latest | registry.npmjs.org |
| Clean public install (**Python leg only**) | PASS — `pip install seshat-bi==1.0.0` in a fresh venv, `importlib.metadata.version` -> `1.0.0`, `python -m seshat.cli --version` -> `seshat 1.0.0` | executed 2026-08-15 |

**Not re-verified by this reconciliation:** the Claude and Codex public-path checks.
T090 names three legs — Python, Claude, Codex — and only the Python leg was executed
here. See the T090 row in §3 and the caveat in §5.

**Ordering note.** Artifacts uploaded to PyPI at `11:55`, the GitHub Release published
at `11:57`. The publication sequence completed in order and no channel is missing.

---

## 3. Classification of T073–T091

Categories are the four the roadmap names. **No box is ticked by this document** —
classification records what is *true*, and the owner decides what to *mark*.

**The `basis` column is load-bearing.** `observed` means this reconciliation looked
directly at the artifact or API. `inferred` means the outcome implies it but the
required record was not read. An inferred row is not a weaker classification — it is a
statement about what a later reader may rely on without re-deriving it.

A note that constrains four rows below: **`docs/operations/release-acceptance-checklist.md`
contains no `1.0.0` record.** It is a template, and several tasks (T073 explicitly)
require recording their result *in the evidence it references*. Publication succeeding
does not prove that record was written.

### Phase: PyPI Trusted Publisher and release execution

| Task | Class | Basis | Evidence |
|---|---|---|---|
| T073 package identity | `completed-with-evidence` | **inferred** | `seshat-bi` is owned and serving 14 versions, `0.2.0` -> `1.0.0`. The task also requires recording the result in the release-acceptance evidence; **no `1.0.0` record found there** |
| T074 GitHub protection | `completed-with-evidence` | **inferred** | the release run consumed a `pypi` environment; tag protection settings were **not queried** |
| T075 Trusted Publisher | `completed-with-evidence` | **inferred (strong)** | publication succeeded with no API token — Trusted Publisher cannot succeed unregistered |
| T076 configuration verification | `completed-with-evidence` | **inferred** | superseded in effect by 14 successful publications across four channels |
| T084 version decision | `completed-with-evidence` | **observed** | `1.0.0` selected and projected; the tag's own commit is the `#624` release-PR merge |
| T085 version projection | `completed-with-evidence` | **observed** | `pyproject.toml`, `CHANGELOG.md` (`## [1.0.0] -- 2026-08-13`), `docs/releases/v1.0.md` all at `1.0.0` |
| T086 final candidate | `completed-with-evidence` | **observed** | release run succeeded on exactly `adefa70f` |
| T087 tag | `completed-with-evidence` | **observed** | immutable tag `v1.0.0` exists on `adefa70f` |
| T088 PyPI | `completed-with-evidence` | **observed** | both artifacts live with recorded sha256 digests |
| T089 GitHub Release | `completed-with-evidence` | **observed** | published `2026-08-13T11:57:09Z` |
| T090 public verification | **`partially-verified`** | **observed (Python leg only)** | T090 names **three** legs — Python, Claude, Codex. Clean-venv Python install re-verified 2026-08-15 (§2). **The Claude and Codex public-path checks were NOT re-run by this reconciliation.** |
| T091 containment | `not-applicable` | **observed** | no channel failed; nothing to contain |

### Phase: Claude repository + public catalog

| Task | Class | Basis | Evidence |
|---|---|---|---|
| T077 repository availability | **`still-open`** | **observed** | prerequisite acceptance tasks T044–T053 are `[X]` and the bundle ships, BUT `release-acceptance-checklist.md:77` still records "make Claude repository marketplace available — **not approved**". The approval this task asks for is not evidenced |
| T078 public catalog package | `still-open` — **deliberately deferred** | **observed** | owner deferred 2026-08-02; runbook `docs/operations/public-catalog-submission.md` verified ready |
| T079 submission decision | `still-open` — **deliberately deferred** | **observed** | same deferral |

### Phase: OpenAI/Codex repository + public plugin

| Task | Class | Basis | Evidence |
|---|---|---|---|
| T080 repository availability | **`still-open`** | **observed** | as T077: prerequisites `[X]` and both CLI/IDE bundles ship, but `release-acceptance-checklist.md:79` records "make Codex repository marketplace available — **not approved**" |
| T081 eligibility | `still-open` — **deliberately deferred** | **observed** | same deferral |
| T082 submission package | `still-open` — **deliberately deferred** | **observed** | same deferral |
| T083 submission decision | `still-open` — **deliberately deferred** | **observed** | same deferral |

**Totals:** 10 `completed-with-evidence` (4 of them inferred rather than observed),
1 `partially-verified` (T090), 1 `not-applicable`, 7 `still-open` — of which 5 are one
deferred catalog decision and 2 (T077, T080) are repository-availability approvals the
checklist still records as not approved.

**Revised from an earlier draft of this ledger.** T077 and T080 were first classified
`completed-with-evidence` on the reasoning that their prerequisites were done and the
bundles ship. That confused *the work being finished* with *the owner approval the task
actually asks for*, which `release-acceptance-checklist.md` still records as not
granted. Shipping artifacts is not an approval record.

**The deferral is a decision, not an oversight.** `docs/releases/v1.0.md` already
states it: "Public Claude/OpenAI catalog submission is a separate, deferred owner
action." Repository-marketplace availability already works and is unaffected; a public
catalog listing is purely discovery. Submission is a human action in each portal under
a verified identity — there is no CLI, workflow, or API for it by design.

---

## 4. Defect found: the published 1.0.0 wheel contains no Studio UI

This reconciliation was read-only, but verifying T090 surfaced a live public defect
that belongs in the release record.

```
pip download --no-deps seshat-bi==1.0.0
  seshat_bi-1.0.0-py3-none-any.whl
  studio/static entries: 0
  has index.html: False
```

**The published wheel ships zero Studio frontend assets.** A user installing
`seshat-bi[studio]==1.0.0` from PyPI today gets a launcher with no UI, which
fail-closes with "Studio frontend assets are missing."

This is issue **#623**, and the timing explains it exactly:

| Event | When |
|---|---|
| release PR `#624` merged — commit `adefa70f`, which the tag points at | 2026-08-13 14:50 +03:00 |
| PyPI artifacts uploaded / GitHub Release published | 2026-08-13 11:55 / 11:57 UTC |
| `#636` — build the Studio frontend before the release wheel | 2026-08-14 02:20 +03:00 |

(The first row is `adefa70f`'s commit timestamp, not the tag-creation time; the tag
object was not queried for its own date. The ~11-hour conclusion rests on the
publication times, which are observed.)

The fix landed roughly 11 hours **after** the tag. `#623` is closed and the fix is on
`main`, so the repository is correct — but **no published artifact carries it**. The
fix is real and unreleased.

`docs/releases/v1.0.md:38` already discloses this honestly ("usable from PyPI in this
release (issue #623)"), so the release notes are not lying. The point for this ledger
is narrower: the *only* remedy is a new release, and this is concrete evidence for
Release Train A rather than a reason to touch `v1.0.0`.

**Do not attempt to fix this by republishing `1.0.0`.** The tag is immutable and PyPI
rejects re-uploads of an existing filename. The correct path is a new owner-selected
version through the normal train.

---

## 5. What a later agent must not conclude

1. **Unchecked T073–T091 does NOT mean unpublished.** Ten of the nineteen are done with
   public evidence and one more is partially verified. Re-running them risks duplicate
   or failing irreversible actions.
2. **The five open catalog tasks are one deferred owner decision**, not five units of
   work, and not a gap to close proactively.
2b. **T090 was only partially re-verified here, and T077/T080 are genuinely open.**
   Do not read this ledger as "everything but the catalog is done": the Claude and
   Codex public-path checks were not re-run, and the two repository-availability
   approvals are still recorded as not approved.
3. **A green `main` is not a shipped fix.** `#623`, `#636`, `#642`, and `#647` are all
   on `main` and none of them are on PyPI. Check three places before claiming a fix
   reached users: `main`, the tag, and the installed artifact.
4. **Nothing here authorizes a release.** Version selection, tag, and each publication
   channel require exact named-owner authorization.

---

## 6. Standing verification commands

Re-runnable, read-only, no credentials:

```bash
# Tag -> commit -> ancestry
git rev-parse v1.0.0 && git log -1 --format=%H "$(git rev-parse v1.0.0)^{commit}"
git merge-base --is-ancestor "$(git rev-parse v1.0.0^{commit})" origin/main

# Published channels
gh release view v1.0.0 --json tagName,publishedAt,isDraft
curl -s https://pypi.org/pypi/seshat-bi/json | python -c "import json,sys;print(json.load(sys.stdin)['info']['version'])"
curl -s https://registry.npmjs.org/@kemetra/seshat-bi | python -c "import json,sys;print(json.load(sys.stdin)['dist-tags']['latest'])"

# Does the PUBLISHED wheel carry the UI? (currently: no)
pip download --no-deps --no-cache-dir seshat-bi==1.0.0
python -c "import zipfile,glob;z=zipfile.ZipFile(glob.glob('*.whl')[0]);print(len([n for n in z.namelist() if 'studio/static' in n]))"
```

---

## 7. Exit gate

One authoritative release-state ledger now exists. Later agents cannot mistake stale
checkboxes for missing publication work, and the one genuine public gap — a shipped
wheel with no Studio UI — is recorded as evidence for the next release rather than as
an invitation to re-publish an immutable version.

**Owner actions this ledger identifies (none performed):**

1. Decide whether to tick the ten `completed-with-evidence` rows given §3, or leave
   them as a historical record and rely on this superseding ledger. Note that four of
   them (T073–T076) rest on **inference from successful publication**, not on a read
   record — T073 in particular asks for a result recorded in
   `release-acceptance-checklist.md`, which holds no `1.0.0` entry.
2. **T077 / T080 (repository availability) are open, not done.** Their prerequisites
   pass and the bundles ship, but `release-acceptance-checklist.md:77,79` still record
   both as "not approved". These are separable from the deferred public-catalog
   decision and are the cheapest genuinely-open items here.
3. **T090 needs its Claude and Codex legs re-run** to be closable; only the Python leg
   was verified (2026-08-15).
4. Note §4 as a Release Train A input: the frontend fix exists only on `main`, so no
   installable artifact carries the Studio UI today.
