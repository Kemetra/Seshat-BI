# Smart-Formatting Layer (Slice 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the DEFINE-side of a smart-formatting layer: a `formatting-plan.md` ledger schema, a new **DL7** lint that validates a filled ledger's well-formedness, and a `powerbi-dashboard-design` workflow that produces such a plan (theme + #4/#9/#13/#8) for one page — stopping at the ratify seam.

**Architecture:** The reasoning is a skill workflow (Opus, non-deterministic) that emits a git-reviewable ledger; the core's contribution is a deterministic lint (DL7) that checks the ledger's *shape* only (citations resolve, allow-list-only, no render-only citation claimed resolved, no score, `ratified_by` unset). The already-shipped `pbir-*` verbs apply a ratified ledger; no new apply code. Ships HELD/latent — proven on a fixture ledger; the real report page has no visuals yet.

**Tech Stack:** Python 3.13, stdlib only (`re`, `pathlib`) + the existing rule framework (`retail.core`, `retail.registry`); `pytest` (`@pytest.mark.unit`). Docs are Markdown.

## Global Constraints

- **DL7 is the rule id** (DL1–DL6 exist; confirm `DL7` absent from `EXPECTED_RULE_IDS` at build time).
- **stdlib-only core; no new dependency.** DL7 parses the ledger Markdown with `re`/string ops — no YAML/MD library.
- **No numeric score anywhere** (hard rule #9): DL7 ERRORs if the ledger contains a `score:`/`confidence:` key.
- **Never self-grant a pass; agent never fills `ratified_by`:** DL7 ERRORs if `ratified_by` is non-empty AND the ledger is not also human-signed per the existing gate (DL7 only checks it is *not agent-filled by shape* — see Task 2).
- **The workflow proposes only; it writes the ledger, never PBIR.** It stops at the ratify seam (`ask-before-firing`; never self-ratifies).
- **Honest ceiling:** the workflow's output claims "consistent / theme-conformant", never "brilliant". The word "brilliant"/"score" must not appear as a self-assessment.
- **Render-only anti-patterns (#1/#5/#6/#7) may never be cited as `resolved` by an applyable row** — DL7 enforces this category ban.
- **Generic (Principle VII):** template + fixtures carry no tenant/c086/retail_store_sales specifics; a real subject area is a cited example only.
- ASCII, UTF-8 no BOM, `\n`. Commit type prefix; `Co-Authored-By` trailer.
- Gate before push: `ruff format --check src tests` + `ruff check src tests` + `pytest -m unit` + `retail check`.

---

### Task 1: The `formatting-plan.md` ledger template

**Files:**
- Create: `templates/formatting-plan.md`
- Test: none (a doc template; its shape is exercised by Task 2's fixtures)

**Interfaces:**
- Produces: the ledger contract DL7 (Task 2) parses and the workflow (Task 3) fills. Columns (a Markdown table): `target | container | group | property | value | principle_cited | token_cited | apply_verb | status | rationale`. Footer keys: `readiness.status`, `blocking_reasons`, `ratification.ratified_by`.

- [ ] **Step 1: Write the template**

Create `templates/formatting-plan.md` with: the header explaining it is a GENERIC, copy-me ledger (surface: DEFINE-side dashboard formatting; the `pbir-*` verbs apply the applyable subset; a human ratifies + renders); the honest-ceiling paragraph (consistent/conformant, NOT brilliant-automatically; formats blind; cite `docs/powerbi/visual-qa.md`); a Principle-VII note (no tenant specifics); the column contract above with a one-line meaning per column; the apply-path partition (applyable #3/#4/#8/#9/#12/#13; detect-only #1/#5/#6/#7 → `handoff-only`; stop-upstream #2/#10/#11); an example row per `apply_verb` value using OBVIOUS placeholders; the footer with `readiness.status: warning`, `blocking_reasons: [not rendered -- screenshot-review pending]`, `ratification.ratified_by: ""` and the note that the agent is forbidden to fill it; and a "no `score:`/`confidence:` field exists by design (rule #9)" line. Mirror the prose style of `templates/theme-json-spec.md` / `templates/visual-spec.yaml`.

- [ ] **Step 2: Verify it renders + has no placeholders-of-the-forbidden-kind**

Run: `grep -nE 'TBD|TODO|FIXME' templates/formatting-plan.md` → expect no matches (obvious `<placeholder>` tokens in example rows are fine and expected).
Run: `grep -c 'score' templates/formatting-plan.md` → expect ≥1 (the "no score by design" line).

- [ ] **Step 3: Commit**

```bash
git add templates/formatting-plan.md
git commit -m "$(printf 'docs: formatting-plan.md ledger template (smart-formatting slice 1)\n\nThe DEFINE-side artifact: one row per formatting decision, each citing a\nvisual-qa.md anti-pattern + a token. Honest-ceiling + Principle-V footer\n(warning status, not-rendered blocker, ratified_by agent-forbidden, no\nscore by design).\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 2: The DL7 ledger-well-formedness lint

**Files:**
- Create: `src/seshat/rules/formatting_plan.py`
- Modify: `src/seshat/rules/__init__.py` (add `formatting_plan` to the import block ~line 30 and to `__all__` ~line 55, both alphabetically → after `date_spine`/before `dax` is wrong; it sorts after `design_*` — insert `formatting_plan` after `dax` and before `design_background`? No: alphabetical `f` > `design_*` and > `dax`, < `g6`. Insert `formatting_plan,` between `dax,`… actually between the `design_*` group and `g6`. Place it immediately before `g6` in both lists.)
- Modify: `tests/unit/test_rules_wiring.py` (add `"DL7",` to `EXPECTED_RULE_IDS` after `"DL6"`)
- Modify (regen, do not hand-edit): `docs/rules/rules-manifest.json`, `docs/rules/severity-posture.json`
- Modify: `docs/glossary.md` (DL family row: append DL7; bump the rule count) + `docs/quality/rule-count-claims.yaml` (anchor + count)
- Create: `tests/unit/test_formatting_plan.py`
- Create fixtures under `tests/fixtures/formatting_plan/`: `clean.md`, `bad_missing_principle.md`, `bad_unresolvable_principle.md`, `bad_render_only_resolved.md`, `bad_has_score.md`, `bad_agent_ratified.md`, `bad_out_of_allowlist.md`

**Interfaces:**
- Consumes: `retail.core.{Finding, RuleContext, Severity, is_test_path}`, `retail.registry.register`. The ledger template shape from Task 1.
- Produces: rule `DL7` via `@register("DL7", "Formatting-plan ledger is well-formed (citations resolve, allow-list-only, no score)")`, function `check_formatting_plan(ctx) -> Iterable[Finding]`. Discovers committed `**/formatting-plan.md` (not test-path, **and not under `templates/`** -- `templates/formatting-plan.md` is the generic copy-me template from Task 1: it intentionally carries backtick-wrapped placeholder cells, a `(none)` container, and ratify-forbidden prose that would trip DL7's row/footer checks by construction; DL7 validates *filled* ledgers only). ERROR per malformed row.

- [ ] **Step 1: Write the fixtures**

Create `tests/fixtures/formatting_plan/clean.md` — a minimal valid ledger: header line, a table with ONE applyable row (`page:overview | visualContainerObjects | title | show | true | #4 | typography.title | B | proposed | consistent title per #4`), and the footer (`readiness.status: warning`, `ratification.ratified_by: ` empty). Then the six `bad_*.md`, each identical to clean but with exactly one defect: missing `principle_cited` cell; a `principle_cited` of `#99` (no such anti-pattern); an applyable row citing `#7` (render-only) with `status: resolved`; a stray `score: 0.9` line; `ratification.ratified_by: agent`; a `container` of `query` (out of allow-list).

- [ ] **Step 2: Write the failing tests** — `tests/unit/test_formatting_plan.py`

```python
"""Unit tests for DL7 (formatting-plan ledger well-formedness)."""

from __future__ import annotations

from pathlib import Path

import pytest

from retail.core import RuleContext, Severity
from retail.rules.formatting_plan import RULE_ID, check_formatting_plan

pytestmark = pytest.mark.unit

FIXTURES = Path(__file__).parent.parent / "fixtures" / "formatting_plan"


def _ctx(name: str) -> RuleContext:
    return RuleContext(repo_root=FIXTURES, tracked_files=(name,))


def test_clean_ledger_passes() -> None:
    assert list(check_formatting_plan(_ctx("clean.md"))) == []


def test_missing_principle_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_missing_principle.md")))
    assert any(x.rule_id == RULE_ID for x in f)
    assert any("principle" in x.message.lower() for x in f)


def test_unresolvable_principle_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_unresolvable_principle.md")))
    assert any("#99" in x.message or "resolve" in x.message.lower() for x in f)


def test_render_only_cited_as_resolved_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_render_only_resolved.md")))
    assert any("render-only" in x.message.lower() for x in f)


def test_score_field_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_has_score.md")))
    assert any("score" in x.message.lower() for x in f)


def test_agent_ratified_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_agent_ratified.md")))
    assert any("ratif" in x.message.lower() for x in f)


def test_out_of_allowlist_container_fails() -> None:
    f = list(check_formatting_plan(_ctx("bad_out_of_allowlist.md")))
    assert any("allow-list" in x.message.lower() for x in f)


def test_severity_is_error() -> None:
    f = list(check_formatting_plan(_ctx("bad_has_score.md")))
    assert all(x.severity is Severity.ERROR for x in f)


def test_test_fixtures_are_exempt_when_under_tests_path() -> None:
    ctx = RuleContext(
        repo_root=FIXTURES,
        tracked_files=("tests/fixtures/formatting_plan/bad_has_score.md",),
    )
    assert list(check_formatting_plan(ctx)) == []
```

- [ ] **Step 3: Run → fail**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_formatting_plan.py -q --no-cov`
Expected: FAIL — `ModuleNotFoundError: No module named 'retail.rules.formatting_plan'`

- [ ] **Step 4: Write `src/seshat/rules/formatting_plan.py`**

```python
"""Design-lint rule DL7: formatting-plan ledger well-formedness.

DL7 validates the SHAPE of a committed ``formatting-plan.md`` ledger (the
smart-formatting layer's DEFINE-side artifact). It checks that the plan is
structurally honest -- it does NOT and cannot check that a formatting choice is
good (that needs a human render; the loop is open by design). Specifically, per
committed ledger row / footer it ERRORs when:

  * a row is missing its ``principle_cited`` or ``token_cited`` (every decision
    must trace to a rubric anti-pattern + a token, or it is vibes);
  * ``principle_cited`` does not resolve to a real anti-pattern number
    (1-13 per docs/powerbi/visual-qa.md);
  * an APPLYABLE row cites a RENDER-ONLY anti-pattern (#1/#5/#6/#7) as its
    resolved principle -- a category error (bolding a title does not establish
    hierarchy; that is geometry, handoff-only);
  * the ledger contains a ``score:``/``confidence:`` field (hard rule #9);
  * ``ratification.ratified_by`` is filled with an agent-shaped value (the agent
    is structurally forbidden to self-ratify -- Principle V);
  * a row's ``container`` is outside the adapter's formatting allow-list.

Read-only; stdlib only (re + string ops on the committed Markdown). Generic:
no tenant/example literal (Principle VII). Test fixtures exempted (is_test_path).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..core import Finding, RuleContext, Severity, is_test_path
from ..registry import register

RULE_ID = "DL7"

_LEDGER_SUFFIX = "formatting-plan.md"

# The 13 anti-patterns (docs/powerbi/visual-qa.md). Render-only = geometry/type,
# no property-level apply path; may not be cited as "resolved" by an applyable row.
_ALL_PRINCIPLES = frozenset(f"#{i}" for i in range(1, 14))
_RENDER_ONLY = frozenset({"#1", "#5", "#6", "#7"})

# The formatting containers the adapter may write (matches pbir_visual_format +
# pbir_page_background + pbir_theme_apply). A container outside this is off-limits.
_ALLOWED_CONTAINERS = frozenset(
    {"objects", "visualContainerObjects", "background", "themeCollection"}
)

_SCORE_RE = re.compile(r"\b(score|confidence)\s*:", re.IGNORECASE)
_RATIFIED_RE = re.compile(r"ratified_by\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
# an agent-shaped ratifier value (empty or a quoted-empty is OK; a bare token or
# anything containing 'agent'/'claude'/'llm' is a forbidden self-ratify).
_AGENT_RATIFIER_RE = re.compile(r"agent|claude|llm|assistant", re.IGNORECASE)


def _iter_ledgers(ctx: RuleContext) -> list[str]:
    return [
        p
        for p in ctx.tracked_files
        if p.endswith(_LEDGER_SUFFIX)
        and not is_test_path(p)
        and not p.startswith("templates/")
    ]


def _table_rows(text: str) -> list[list[str]]:
    """Return the data rows (list of cell-lists) of the first pipe-table found.

    Skips the header row and the ``---|---`` separator; ignores non-table lines.
    """
    rows: list[list[str]] = []
    seen_header = False
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not seen_header:
            seen_header = True  # first table line is the header
            continue
        if all(set(c) <= {"-", ":"} for c in cells):
            continue  # separator row
        rows.append(cells)
    return rows


# Column order per templates/formatting-plan.md (Task 1).
_COLS = (
    "target",
    "container",
    "group",
    "property",
    "value",
    "principle_cited",
    "token_cited",
    "apply_verb",
    "status",
    "rationale",
)


def _row(cells: list[str]) -> dict[str, str]:
    return {_COLS[i]: (cells[i] if i < len(cells) else "") for i in range(len(_COLS))}


@register(
    RULE_ID,
    "Formatting-plan ledger is well-formed (citations resolve, allow-list-only, no score)",
)
def check_formatting_plan(ctx: RuleContext) -> Iterable[Finding]:
    findings: list[Finding] = []
    for rel in _iter_ledgers(ctx):
        path = ctx.repo_root / rel
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            findings.append(
                Finding(RULE_ID, Severity.ERROR,
                        f"ledger could not be read ({exc.__class__.__name__})",
                        f"{rel}#/")
            )
            continue

        # footer-level checks (whole document)
        if _SCORE_RE.search(text) and "no `score:`" not in text and "no ``score:``" not in text:
            findings.append(
                Finding(RULE_ID, Severity.ERROR,
                        "ledger contains a score/confidence field; a formatting "
                        "plan is words-only, never a numeric score (rule #9)",
                        f"{rel}#score")
            )
        m = _RATIFIED_RE.search(text)
        if m:
            val = m.group(1).strip().strip("'\"`")
            if val and _AGENT_RATIFIER_RE.search(val):
                findings.append(
                    Finding(RULE_ID, Severity.ERROR,
                            f"ratification.ratified_by is agent-filled ({val!r}); "
                            f"the agent may not self-ratify (Principle V)",
                            f"{rel}#ratified_by")
                )

        # row-level checks
        for i, cells in enumerate(_table_rows(text)):
            r = _row(cells)
            loc = f"{rel}#row{i + 1}"
            principle = r["principle_cited"]
            if not principle:
                findings.append(Finding(RULE_ID, Severity.ERROR,
                    "row is missing principle_cited (every decision must cite a "
                    "visual-qa.md anti-pattern)", loc))
            elif principle not in _ALL_PRINCIPLES:
                findings.append(Finding(RULE_ID, Severity.ERROR,
                    f"principle_cited {principle!r} does not resolve to a real "
                    f"anti-pattern (#1-#13 in docs/powerbi/visual-qa.md)", loc))
            if not r["token_cited"]:
                findings.append(Finding(RULE_ID, Severity.ERROR,
                    "row is missing token_cited (every decision must draw from a "
                    "committed design token)", loc))
            # render-only anti-pattern cited as resolved by an applyable row
            applyable = r["apply_verb"] in ("A", "B", "C")
            resolved = r["status"].lower() in ("resolved", "proposed")
            if applyable and resolved and principle in _RENDER_ONLY:
                findings.append(Finding(RULE_ID, Severity.ERROR,
                    f"applyable row cites render-only anti-pattern {principle} as "
                    f"{r['status']}; #1/#5/#6/#7 are geometry -- handoff-only, an "
                    f"apply verb cannot resolve them", loc))
            # container allow-list (empty container = a page/theme-level row is ok
            # only when apply_verb is A/C; a B row must name an allowed container)
            cont = r["container"]
            if cont and cont not in _ALLOWED_CONTAINERS:
                findings.append(Finding(RULE_ID, Severity.ERROR,
                    f"container {cont!r} is not in the formatting allow-list "
                    f"{sorted(_ALLOWED_CONTAINERS)}", loc))
    return findings
```

- [ ] **Step 5: Wire DL7 into the registry (`__init__.py`)**

In `src/seshat/rules/__init__.py`, add `formatting_plan,` to the import block (immediately before `g6,`) and `"formatting_plan",` to `__all__` (immediately before `"g6",`).

- [ ] **Step 6: Add DL7 to `EXPECTED_RULE_IDS`**

In `tests/unit/test_rules_wiring.py`, add `"DL7",  # design-lint: formatting-plan ledger well-formedness` immediately after the `"DL6",` line.

- [ ] **Step 7: Run tests → pass**

Run: `PYTHONPATH=src python -m pytest tests/unit/test_formatting_plan.py tests/unit/test_rules_wiring.py -q --no-cov`
Expected: PASS (8 DL7 tests + wiring test with DL7 present).

- [ ] **Step 8: Regenerate the golden manifests**

Run:
```bash
PYTHONPATH=src python -c "from retail.cli import main; import sys; sys.exit(main(['manifest','--repo','.']))"
PYTHONPATH=src python -c "from retail.cli import main; import sys; sys.exit(main(['severity-posture','--repo','.']))"
```
Expected: both write their JSON.

- [ ] **Step 9: Fix the rule-count claim (SC2 will fail otherwise)**

The rule count went up by 1. In `docs/glossary.md`: bump the "Currently N rules in 22 families" line by 1 and append `; \`DL7\` formatting-plan ledger well-formedness` to the DL family row. In `docs/quality/rule-count-claims.yaml`: bump the `anchor` string and `claimed-count` to match. Verify the exact new count from the manifest:
```bash
PYTHONPATH=src python -c "import json;print(len(json.load(open('docs/rules/rules-manifest.json'))['rules']) if isinstance(json.load(open('docs/rules/rules-manifest.json')),dict) else 'inspect')"
```
(If the manifest shape differs, open it and count; set glossary + claim to that number.)

- [ ] **Step 10: Full gate → green, then commit**

Run: `ruff format src/seshat/rules/formatting_plan.py tests/unit/test_formatting_plan.py` then `ruff check src tests` then `PYTHONPATH=src python -m pytest -m unit -q --no-cov` then `retail check`.
Expected: all green (DL7 clean on its own clean fixture; SC2 count reconciled).

```bash
git add src/seshat/rules/formatting_plan.py src/seshat/rules/__init__.py tests/unit/test_formatting_plan.py tests/unit/test_rules_wiring.py tests/fixtures/formatting_plan/ docs/rules/rules-manifest.json docs/rules/severity-posture.json docs/glossary.md docs/quality/rule-count-claims.yaml
git commit -m "$(printf 'feat: DL7 formatting-plan ledger well-formedness lint\n\nValidates a committed formatting-plan.md shape: every row cites a\nresolvable visual-qa.md anti-pattern + a token; no applyable row claims a\nrender-only anti-pattern (#1/#5/#6/#7) resolved; no score field; the\nagent has not self-ratified; container is allow-listed. Read-only,\nstdlib-only. Wired into the registry + golden manifests; rule count bumped.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 3: The formatting-plan authoring workflow

**Files:**
- Create: `.claude/skills/powerbi-dashboard-design/workflows/formatting-plan.md`
- Modify: `.claude/skills/powerbi-dashboard-design/SKILL.md` (add a router row: "Propose a formatting plan for an approved page → `workflows/formatting-plan.md`")

**Interfaces:**
- Consumes: the DL7 ledger contract (Task 2), the ledger template (Task 1), `docs/powerbi/visual-qa.md`, `design/tokens/`, the subject's approved binding-map + visual-list.
- Produces: procedure text only (no code). A human runs it; it writes a filled `mappings/<subject>/design/formatting-plan.md`.

- [ ] **Step 1: Write the workflow**

Create `workflows/formatting-plan.md` documenting the procedure: (0) PRECONDITION — refuse unless the subject's `semantic_model_ready: pass` AND the visual-contract-binding-map is approved (cite `dashboard-ready.md`); (1) read the rubric + tokens + binding-map + each visual.json; (2) for each applyable anti-pattern (#4 number formats, #9 tooltip presence, #13 theme-inheritance, #8 category colors, #3 date-context via subtitle), emit ledger rows in the adapter's real `container/group/property/value` shape, each citing the principle + token; (3) #8 rows are `needs-owner-decision` unless a committed category-member enumeration exists; (4) emit #1/#5/#6/#7 as `handoff-only` notes (never applyable); (5) #2/#10/#11 → STOP and route upstream; (6) write the ledger at `readiness.status: warning`, `blocking_reasons: [not rendered]`, `ratified_by` EMPTY; (7) STOP at the ratify seam — print "run `retail check` (DL7) then have a named owner ratify + render + run screenshot-review; do not self-ratify, do not apply". Include the honest-ceiling statement (consistent/conformant, not brilliant) and the standing FORBIDDEN list (no binding, no metric, no score, no self-ratify, no PBIR write from this workflow — the `pbir-*` verbs apply only a ratified plan). Carry the same Principle-V STOP list as the design doc §"Principle-V STOPs".

- [ ] **Step 2: Add the router row to SKILL.md**

In `.claude/skills/powerbi-dashboard-design/SKILL.md`, in the "Router: request → workflow" table, add: `| Propose a formatting plan for an approved page | 1/3 | \`workflows/formatting-plan.md\` |`.

- [ ] **Step 3: Verify + gate + commit**

Run: `retail check` → expect exit 0 (the workflow is prose; it adds no rule and trips none).
Run: `grep -c "brilliant" .claude/skills/powerbi-dashboard-design/workflows/formatting-plan.md` → expect the only occurrences to be in the "NOT brilliant" honest-ceiling disclaimer (read them to confirm none is a self-claim).

```bash
git add .claude/skills/powerbi-dashboard-design/workflows/formatting-plan.md .claude/skills/powerbi-dashboard-design/SKILL.md
git commit -m "$(printf 'feat: formatting-plan authoring workflow (smart-formatting slice 1)\n\nThe Opus procedure that emits a formatting-plan.md ledger (theme + #4/#9/\n#13/#8 + #3-date-context) for an approved page, gated on semantic_model_\nready + an approved binding-map, stopping at the ratify seam. Honest\nopen loop; consistent-not-brilliant ceiling; Principle-V STOPs; no PBIR\nwrite (the pbir-* verbs apply only a ratified plan).\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 4: A committed clean example ledger + full-gate proof

**Files:**
- Create: `tests/fixtures/formatting_plan/example-slice1.md` (a fuller clean ledger covering #4/#9/#13/#8-needs-owner-decision) — a fixture, not a live subject artifact (the real report has no visuals; Principle VII keeps it generic).

**Interfaces:** none (proof).

- [ ] **Step 1: Write the fuller example ledger** covering one row per applyable anti-pattern (#4/#9/#13), an #8 row at `status: needs-owner-decision`, and a `handoff-only` #7 note row (which must NOT trip the render-only ban because its `apply_verb` is `handoff-only`, not A/B/C). Footer: `warning`, not-rendered blocker, empty `ratified_by`.

- [ ] **Step 2: Prove DL7 passes it**

Run: `PYTHONPATH=src python -c "from pathlib import Path; from retail.core import RuleContext; from retail.rules.formatting_plan import check_formatting_plan; print(list(check_formatting_plan(RuleContext(repo_root=Path('tests/fixtures/formatting_plan'), tracked_files=('example-slice1.md',)))))"`
Expected: `[]` (clean — including the `handoff-only #7` row NOT being flagged, proving the applyable-vs-handoff distinction works).

- [ ] **Step 3: Full CI gate**

Run: `ruff format --check src tests` + `ruff check src tests` + `PYTHONPATH=src python -m pytest -m unit -q --no-cov` + `retail check`. All green.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/formatting_plan/example-slice1.md
git commit -m "$(printf 'test: fuller clean formatting-plan example (DL7 dogfood)\n\nProves DL7 passes a realistic ledger and that a handoff-only #7 row is\nNOT flagged by the render-only-resolved ban (only applyable A/B/C rows\nare). Generic fixture (Principle VII).\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

## Self-Review

- **Spec coverage:** ledger template (T1) ✓; DL7 lint with all 6 checks — citations resolve, token cited, render-only ban, no score, no agent-ratify, allow-list (T2) ✓; wired into 6 places + manifests + count (T2 steps 5,6,8,9) ✓; the authoring workflow with precondition gate + apply-path partition + Principle-V STOPs + ratify seam (T3) ✓; honest open loop / consistent-ceiling (T1 prose + T3 prose) ✓; #8 needs-owner-decision (T3 step 1, T4 example) ✓; HELD/latent + generic fixtures (T4) ✓.
- **Placeholder scan:** none of the forbidden kind; the ledger template's `<placeholder>` example cells are intentional and expected.
- **Type consistency:** `check_formatting_plan(ctx) -> Iterable[Finding]`, `RULE_ID = "DL7"`, `_COLS`, `_ALLOWED_CONTAINERS`, `_RENDER_ONLY` used consistently across T2 code + T2 tests + T4 proof. Column order in `_COLS` matches the template contract (T1) and the fixtures (T2/T4).
- **Boundary check:** no task writes PBIR, defines a metric, self-ratifies, or emits a score. DL7 is read-only. The workflow writes only the ledger. Confirmed.
