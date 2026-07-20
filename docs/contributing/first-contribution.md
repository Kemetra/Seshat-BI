# Your first contribution

You need **three documents, total** — this page and two more:

1. This page (the path).
2. [`contribution-lanes.yaml`](./contribution-lanes.yaml) (pick a lane).
3. [`CONTRIBUTING.md`](../../CONTRIBUTING.md) (dev setup + PR mechanics).

You do **not** need the constitution, the roadmap, or the spec archive to
make a starter contribution. The lane you pick tells you everything it
expects.

## The path

1. **Pick a lane.** Open `contribution-lanes.yaml` and choose one of the
   five starter lanes (KPI templates, synthetic fixtures, dialect notes,
   accessibility checks, blocker wording). Each lane declares:
   - `owned_files` — where you may write,
   - `forbidden_scope` — where you may not,
   - `acceptance` — what "done" means,
   - `verification` — the exact commands to run,
   - `difficulty` — a label, not a score.
2. **Claim it.** Open a *Starter contribution claim* issue
   (`.github/ISSUE_TEMPLATE/starter.yml`), select the lane, and say in a
   sentence what you'll add. No approval wait is required to start —
   claiming just avoids duplicate work.
3. **Set up.** Follow the "Dev setup" section of `CONTRIBUTING.md`
   (Python 3.13, `pip install -e ".[dev]"`).
4. **Make the change** inside the lane's `owned_files` only, with synthetic
   data only.
5. **Verify.** Run the lane's `verification` commands; they must pass.
6. **Open the PR.** The pull-request template asks for the readiness stage
   touched, scope, tests, evidence, human decisions, and data safety —
   the lane gives you the answers.

## What to expect from maintainers

- A first reply on your issue or PR within **7 days**.
- A review of a passing PR within **14 days**.
- Reviews check the lane contract (scope, verification, safety), not style
  preferences beyond what `ruff` and `seshat check` enforce.

## Ground rules that always apply

- Statuses are evidence-backed; nothing in this repo emits a fabricated
  score, and neither should your change.
- Judgment calls (grain, PII, business meaning, approvals) belong to named
  humans; a contribution can surface one, never decide one.
- Secrets stay in `.env`; fixtures stay synthetic.
